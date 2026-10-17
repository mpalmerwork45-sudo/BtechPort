"""Shared C validation, image transactions and ordinary world traversal."""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import struct
import zlib
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from editor_model import ProjectDocument, EditorError
from world_editing import upgrade, create_world, add_jigsaw, assign_city, graphic_tile, world_tile, set_patch
from art_editing import new_image, clone_image, brush, pixels, import_tiles, transform, editable_tile

TOOL=Path(os.environ.get('BTP_PROJECT_TOOL',ROOT/'build/btp-project'))
PLAYER=Path(os.environ.get('BTP_HEADLESS',ROOT/'build/btech-headless'))


class WorldArtTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='btp-world-art-');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.project=self.root/'game';shutil.copytree(ROOT/'examples/beacon-demo',self.project)
        self.doc=ProjectDocument(self.project,TOOL)
    def art(self):
        art=copy.deepcopy(self.doc.art);im=new_image('test',art['images']);brush(im,0,(0,0),(15,15),'ff0000ff','Rectangle');art['images'].append(im)
        a=copy.deepcopy(self.doc.adventure);graphic_tile(a,'test','package:art',im['id']);self.doc.replace_art(art,a);return im
    def world(self,size=32):
        a=copy.deepcopy(self.doc.adventure);create_world(a,'test',size,size);assign_city(a,'beacon:town');assign_city(a,'beacon:wild');self.doc.replace_adventure(a)
        return a
    def run_player(self,args=(),actions=''):
        replay=self.root/'input.actions';replay.write_text(actions)
        result=subprocess.run([str(PLAYER),'--project',str(self.project),'--replay',str(replay),*map(str,args)],capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)
        return json.loads(result.stdout)
    def test_large_libraries_world_and_save(self):
        self.art();a=self.world(128)
        for i in range(300):
            tile=copy.deepcopy(a['tiles'][0]);tile.update(id=f'test:many-tile-{i}');a['tiles'].append(tile)
            add_jigsaw(a,'test',[[tile['id']]*8 for _ in range(8)])
        a['world']['pieces'][-1][-1]=a['jigsaws'][-1]['id'];self.doc.replace_adventure(a);self.doc.save()
        self.assertEqual(world_tile(a,1023,1023),'test:many-tile-299')
        # Cross a sector on ordinary input, then round-trip a scene handle
        # beyond the old 8-bit map field (last world row/column).
        saved=self.root/'world.btp'
        start=self.run_player(['--play-here','world:sector-14-15',126,64])
        state=self.run_player(['--play-here','world:sector-14-15',126,64,'--save',saved],'right\nright\nright\n')
        self.assertNotEqual(start['campaign']['world'],state['campaign']['world'])
        loaded=self.run_player(['--load',saved])
        self.assertEqual(state['campaign']['world'],loaded['campaign']['world']);self.assertEqual(state['authored_event'],loaded['authored_event'])
    def test_composition_and_validation(self):
        a=self.world();t=a['tiles'][-1]['id'];set_patch(a['world'],{(2,3):t,(65,65):t})
        self.assertEqual(world_tile(a,2,3),t)
        self.assertEqual(world_tile(a,65,65),a['maps'][0]['rows'][1][1])
        a['world']['pieces'][0][0]='missing:jigsaw';self.doc.replace_adventure(a)
        with self.assertRaisesRegex(EditorError,'world.pieces'):self.doc.validate()
    def test_formation_touches_entrance_across_world_sector(self):
        a=copy.deepcopy(self.doc.adventure);create_world(a,'test',32,32)
        town=a['maps'][0];town['origin']=[128,64];town['overlays']=[]
        town['rows']=[['beacon:grass']*32 for _ in range(24)]
        door=copy.deepcopy(town['entrances'][0]);door.update(at=[0,36]);town['entrances']=[door]
        assign_city(a,town['id']);self.doc.replace_adventure(a);self.doc.save()
        # The lead mech's right footprint touches the next sector while the
        # cursor remains on this one. Save the door's sector with the prompt.
        before=self.run_player(['--play-here','world:sector-1-1',125,38])
        self.assertEqual(before['authored_event']['phase'],0)
        saved=self.root/'door.btp'
        state=self.run_player(['--play-here','world:sector-1-1',125,38,'--save',saved],'right\nright\n')
        self.assertEqual(state['authored_event']['phase'],1)
        loaded=self.run_player(['--load',saved]);self.assertEqual(state['authored_event'],loaded['authored_event'])
        entered=self.run_player(['--load',saved],'accept\n')
        self.assertNotEqual(entered['authored_event']['phase'],0)
    def test_early_single_world_save_migration(self):
        self.world();self.doc.save();saved=self.root/'new.btp'
        state=self.run_player(['--save',saved]);data=bytearray(saved.read_bytes());base=160
        compact=data[base+16384:base+18432];legacy=bytearray(2048)
        for y in range(32):
            for x in range(32):
                bit=y*32+x
                if compact[bit//8]&(128>>(bit%8)):legacy[y*16+x//8]|=128>>(x%8)
        data[base+16384:base+18432]=legacy;data[base+20057+117:base+20057+127]=bytes(10);data[base+20057+127]=1
        struct.pack_into('<I',data,8,zlib.crc32(data[16:]));old=self.root/'old.btp';old.write_bytes(data)
        loaded=self.run_player(['--load',old]);self.assertEqual(state['explored_digest'],loaded['explored_digest'])
        self.assertEqual(state['authored_event'],loaded['authored_event'])
    def test_unplaced_local_map_has_separate_discovery(self):
        a=copy.deepcopy(self.doc.adventure);create_world(a,'test',32,32);assign_city(a,'beacon:town')
        a['start'].update(map='beacon:wild',at=[24,38]);self.doc.replace_adventure(a);self.doc.save()
        saved=self.root/'local.btp';state=self.run_player(['--save',saved]);self.assertEqual(state['authored_event']['planet'],0)
        data=saved.read_bytes()[160+16384:160+18432]
        self.assertEqual(data[:128],bytes(128));self.assertTrue(any(data[128:]))
    def test_art_undo_atomic_save_and_external_conflict(self):
        original=copy.deepcopy(self.doc.adventure);self.art();self.doc.undo()
        self.assertEqual(self.doc.adventure,original);self.assertNotIn('graphics',self.doc.manifest)
        self.doc.redo();self.doc.validate()
        before={p.name:p.read_bytes() for p in self.project.iterdir() if p.is_file()}
        real=self.doc.atomic_file;calls=0
        def fail_later(path,data):
            nonlocal calls
            calls+=1
            if calls==3:raise OSError('interrupted save')
            real(path,data)
        with patch.object(self.doc,'atomic_file',fail_later):
            with self.assertRaisesRegex(OSError,'interrupted'):self.doc.save()
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.project.iterdir() if p.is_file()})
        self.doc.save();reopened=ProjectDocument(self.project,TOOL)
        self.assertEqual(reopened.art,self.doc.art)
        self.doc.undo();self.doc.save();self.doc.redo();self.doc.save()
        self.assertEqual(ProjectDocument(self.project,TOOL).art,reopened.art)
    def test_pixels_clone_and_large_tile_import(self):
        im=new_image('test',[]);brush(im,0,(0,0),(15,15),'aabbcc80')
        clone=clone_image(im,'test',[im]);brush(clone,0,(0,0),(15,0),'112233ff')
        self.assertEqual(pixels(im)[0][0],'aabbcc80');self.assertNotEqual(pixels(im),pixels(clone))
        from PIL import Image
        path=self.root/'tiles.png';Image.new('RGBA',(16*20,16*15),(12,34,56,78)).save(path)
        tiles=import_tiles(path,'test',[]);self.assertEqual(len(tiles),300);self.assertEqual(len({i['id'] for i in tiles}),300)
        self.assertEqual(pixels(tiles[-1])[15][15],'0c22384e')
    def test_pixel_transformations_preserve_alpha_and_animation(self):
        im=new_image('test',[],'Sprite','sprite',3,2,2)
        im['frames'][0]=['0102038004050600070809ff','101112ff1314158016171800']
        before=copy.deepcopy(im)
        transform(im,'Flip X');self.assertEqual(pixels(im)[0],pixels(before)[0][::-1])
        self.assertEqual(im['frames'][1],before['frames'][1]);transform(im,'Flip X');self.assertEqual(im,before)
        transform(im,'Flip Y');self.assertEqual(pixels(im)[0],pixels(before)[1]);transform(im,'Flip Y')
        with self.assertRaisesRegex(EditorError,'All frames'):transform(im,'Rotate right')
        self.assertEqual(im,before)
        transform(im,'Rotate right',all_frames=True);self.assertEqual((im['width'],im['height']),(2,3))
        self.assertEqual(pixels(im)[0],['101112ff','01020380'])
        transform(im,'Rotate left',all_frames=True);self.assertEqual(im,before)
        transform(im,'Nudge left',wrap=True);self.assertEqual(pixels(im)[0],['04050600','070809ff','01020380'])
        transform(im,'Nudge right',wrap=True);self.assertEqual(im,before)
        transform(im,'Nudge down');self.assertEqual(pixels(im)[0],['00000000']*3)
        self.assertEqual(pixels(im)[1],pixels(before)[0]);transform(im,'Clear',all_frames=True)
        self.assertEqual(im['frames'],new_image('test',[],'Sprite','sprite',3,2,2)['frames'])
    def test_editing_indexed_tile_detaches_pixels_and_undo_restores_map(self):
        a=copy.deepcopy(self.doc.adventure);art=copy.deepcopy(self.doc.art)
        original=copy.deepcopy(a);tile=a['tiles'][0];key=tile['key']
        sheets={tile['sheet']:{tile['graphic']:[['#123456']*16 for _ in range(16)]}}
        decoded=copy.deepcopy(sheets);im=editable_tile(art,a,0,'test',sheets)
        self.assertEqual(pixels(im)[0][0],'123456ff');self.assertEqual(sheets,decoded)
        self.assertEqual(a['tiles'][0]['sheet'],'package:art');self.assertEqual(a['tiles'][0]['id'],original['tiles'][0]['id'])
        for y,row in enumerate(original['maps'][0]['rows']):
            for x,value in enumerate(row):
                if value==key:self.assertEqual(a['maps'][0]['rows'][y][x],tile['id'])
        self.assertIs(editable_tile(art,a,0,'test',{}),im);self.assertEqual(len(art['images']),1)
        self.doc.replace_art(art,a);self.doc.validate();self.doc.undo()
        self.assertEqual(self.doc.adventure,original);self.doc.redo();self.doc.save()
        self.assertEqual(ProjectDocument(self.project,TOOL).art,art)
    def test_picture_and_missing_image(self):
        art=copy.deepcopy(self.doc.art);im=new_image('test',[],'Screen','screen',320,200)
        brush(im,0,(0,0),(319,199),'445566ff','Rectangle');art['images'].append(im)
        a=copy.deepcopy(self.doc.adventure);upgrade(a)
        a['events'].append(dict(id='test:picture',op='picture',image=im['id'],next='beacon:end'));a['start']['event']='test:picture'
        self.doc.replace_art(art,a);self.doc.save()
        frame=self.root/'picture.ppm';s=self.run_player(['--frame',frame]);self.assertEqual(s['authored_event']['phase'],2)
        self.assertIn(bytes.fromhex('445566')*320,frame.read_bytes())
        ended=self.run_player(actions='accept\n');self.assertEqual(ended['authored_event']['phase'],0)
        a['events'][-1]['image']='missing:image';self.doc.replace_adventure(a)
        with self.assertRaisesRegex(EditorError,'image'):self.doc.validate()


if __name__=='__main__':unittest.main()
