"""Animated tiles retain pixels, timing and bank identity through authoring."""
import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from editor_model import ProjectDocument,EditorError
from editor_tiles import art_tiles,load_original_animations
from tile_animation import TileGraphics,TileLoop,copy_frames,tile_loop
from tile_editing import copy_graphic,clone_sheet
from art_editing import editable_tile,new_image


def colored_frames():
    return tuple(tuple(tuple(color for _ in range(16)) for _ in range(16)) for color in ('#ff0000','#00ff00','#0000ff'))


class TileAnimationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='btp-tile-loop-');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);shutil.copytree(ROOT/'examples/beacon-demo',self.root/'game')
        self.doc=ProjectDocument(self.root/'game',ROOT/'build/btp-project')
        frames=colored_frames()
        self.decoded=TileGraphics({'chi:land':{105:frames[0]},'chi:destroyed':{105:frames[2]}},
                                 {('chi:land',105):TileLoop(frames,4)})

    def test_original_clone_and_detach_keep_all_frames_and_speed(self):
        art=copy.deepcopy(self.doc.art)
        image=copy_graphic(art,'test',self.decoded,'chi:land',105)
        self.assertEqual(image['frame_ticks'],4);self.assertEqual(len(image['frames']),3)
        self.assertEqual(image['frames'][2][0],'0000ffff'*16)
        destroyed=copy_graphic(art,'test',self.decoded,'chi:destroyed',105)
        self.assertEqual(len(destroyed['frames']),1);self.assertNotIn('frame_ticks',destroyed)
        a=copy.deepcopy(self.doc.adventure);a['tiles'][0].update(sheet='chi:land',graphic=105)
        source=copy.deepcopy(self.decoded)
        detached=editable_tile(art,a,0,'test',self.decoded)
        self.assertEqual(detached['frames'],image['frames']);self.assertEqual(detached['frame_ticks'],4)
        self.assertEqual(self.decoded,source);self.assertEqual(self.decoded.animations,source.animations)
        self.doc.replace_art(art,a);self.doc.validate();self.doc.save()
        self.assertEqual(ProjectDocument(self.doc.root,self.doc.validator).art,art)

    def test_filtered_bulk_copy_is_one_undoable_animation_preserving_edit(self):
        before=self.doc.files()
        ids=clone_sheet(self.doc,self.decoded,'All tiles',[dict(sheet='chi:land',graphic=105)])
        self.assertEqual(len(ids),1);self.doc.validate()
        image=self.doc.art['images'][-1]
        self.assertEqual(len(image['frames']),3);self.assertEqual(image['frame_ticks'],4)
        self.assertEqual(self.doc.adventure['tiles'][-1]['terrain'],'wall')
        self.doc.undo();self.assertEqual(self.doc.files(),before)
        self.doc.redo();self.assertEqual(self.doc.art['images'][-1],image)

    def test_package_loops_default_and_cache_replacement(self):
        image=new_image('test',[],frames=3);image.update(copy_frames(self.decoded,'chi:land',105))
        doc=SimpleNamespace(art=dict(images=[image]))
        library=TileGraphics(self.decoded,self.decoded.animations);library.update(art_tiles(doc))
        self.assertEqual(tile_loop(library,'package:art',image['id']).ticks,4)
        image.pop('frame_ticks');library.update(art_tiles(doc))
        self.assertEqual(tile_loop(library,'package:art',image['id']).ticks,8)
        image['frames']=image['frames'][:1];library.update(art_tiles(doc))
        self.assertIsNone(tile_loop(library,'package:art',image['id']))
        self.assertIsNotNone(tile_loop(library,'chi:land',105))
        library.pop('package:art',None);self.assertNotIn('package:art',library)

    def test_shared_loader_validates_optional_tile_duration(self):
        art=copy.deepcopy(self.doc.art);image=new_image('test',[],frames=2);art['images'].append(image)
        self.doc.replace_art(art);self.doc.validate() # Existing packages omit the field.
        for ticks in (1,4,8,255):
            image['frame_ticks']=ticks;self.doc.replace_art(art);self.doc.validate()
        for ticks in (0,256,True,1.5,'4'):
            with self.subTest(ticks=ticks):
                image['frame_ticks']=ticks;self.doc.replace_art(art)
                with self.assertRaises(EditorError):self.doc.validate()
        image.update(frame_ticks=4,kind='sprite');self.doc.replace_art(art)
        with self.assertRaisesRegex(EditorError,'frame_ticks'):self.doc.validate()

    def test_animation_transport_rejects_invalid_metadata_and_pixels(self):
        good=dict(frame_ticks=4,tiles=[dict(graphic=105,frames=[['ffffffff'*16]*16]*3)])
        mutations=[lambda s:s.update(frame_ticks=0),lambda s:s.update(frame_ticks=True),
                   lambda s:s['tiles'][0].update(graphic=250),lambda s:s['tiles'][0].update(graphic='105'),
                   lambda s:s['tiles'][0].update(frames=[['bad']]),
                   lambda s:s['tiles'].append(copy.deepcopy(s['tiles'][0]))]
        for mutate in mutations:
            source=copy.deepcopy(good);mutate(source)
            with patch('editor_tiles._capture_preview',return_value=json.dumps(source).encode()):
                with self.assertRaisesRegex(EditorError,'invalid terrain animation'):load_original_animations(Path('tool'),Path('data'))


if __name__=='__main__':unittest.main()
