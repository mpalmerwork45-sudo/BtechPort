"""World authoring previews retain native joins, palettes and editable handles."""
import array
import copy
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from editor_model import EditorError,ProjectDocument
from editor_tiles import _capture_preview
from chi_import import ImportCancelled,import_campaigns
from chi_resources import (WORLD_PREVIEW_BYTES,decode_world_editor_preview,
                           world_editor_preview,grid,preview,detach,settings)
from chi_spatial import data,change


class WorldPreviewTransportTests(unittest.TestCase):
    def test_bounded_binary_protocol_preserves_handles_and_palette(self):
        raw=bytearray(WORLD_PREVIEW_BYTES);raw[:4]=b'BWE1';raw[4:10]=bytes([10,20,30,40,50,60])
        raw[52+17]=48;raw[52+16384+17]=9;raw[52+32768+17]=11
        offset=52+3*16384
        raw[offset:offset+6]=bytes([255,255,0,1,42,0]);raw[-1]=15
        result=decode_world_editor_preview(bytes(raw))
        self.assertIsInstance(result['grid'],array.array)
        self.assertEqual(result['grid'][:3].tolist(),[65535,256,42])
        self.assertEqual((result['levels'][17],result['joins'][17],result['towns'][17]),(48,9,11))
        self.assertEqual(result['mini']['palette'][:2],['0a141e','28323c'])
        self.assertEqual(result['mini']['palette_bytes'][:6],bytes([10,20,30,40,50,60]))
        self.assertEqual(result['mini']['pixels'][-1],15)

    def test_rejects_truncation_excess_and_invalid_index_metadata(self):
        raw=bytearray(WORLD_PREVIEW_BYTES);raw[:4]=b'BWE1'
        for value in (bytes(raw[:-1]),bytes(raw)+b'x',b'BWE2'+bytes(raw[4:])):
            with self.assertRaises(EditorError):decode_world_editor_preview(value)
        for offset in (52+16384,52+2*16384,len(raw)-1):
            bad=bytearray(raw);bad[offset]=255
            with self.assertRaises(EditorError):decode_world_editor_preview(bytes(bad))

    def test_cancel_stops_native_preview_process(self):
        cancelled=threading.Event();cancelled.set();started=time.monotonic()
        with self.assertRaises(ImportCancelled):
            _capture_preview([sys.executable,'-c','import time; time.sleep(20)'],cancel=cancelled)
        self.assertLess(time.monotonic()-started,3)


@unittest.skipUnless((ROOT/'build/btp-project').is_file() and (ROOT/'Original DOS/BTECH.EXE').is_file(),
                     'Needs native build and private DOS resources')
class NativeWorldPreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='chi-world-preview-',dir=ROOT/'work')
        cls.root=Path(cls.temp.name);cls.tool=ROOT/'build/btp-project'
        import_campaigns(ROOT/'Original DOS',cls.root/'campaigns',edition='original',validator=cls.tool)
        cls.document=ProjectDocument(cls.root/'campaigns/original',cls.tool)

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def test_exact_native_grid_and_all_tinyland_pixels_use_game_palette(self):
        doc=self.document;result=world_editor_preview(doc);self.assertEqual(result['grid'],grid(doc))
        image=preview(doc,'screen','TINYLAND.CMP')['frames'][0]
        palette=result['mini']['palette'];pixels=result['mini']['pixels'];seen=set()
        # Every terrain block is compared with the decoded native sheet,
        # including its eight-by-eight internal geometry, not a flat tint.
        for at,level in enumerate(result['levels']):
            if result['towns'][at]:continue
            index=64 if level==16 else ((level-16 if level>=32 else level)|result['joins'][at])
            if index>=66:continue
            bx,by=at%128,at//128
            for dy in range(8):
                row=image[(index//40)*8+dy]
                expected=[row[(index%40*8+dx)*8:(index%40*8+dx)*8+6] for dx in range(8)]
                actual=[palette[pixels[(by*8+dy)*1024+bx*8+dx]] for dx in range(8)]
                self.assertEqual(actual,expected)
            seen.add(index)
        self.assertGreater(len(seen),32)

    def test_towns_ruins_and_underlay_use_effective_native_cells(self):
        doc=self.document;normal=world_editor_preview(doc);ruined=world_editor_preview(doc,True)
        underlay=world_editor_preview(doc,underlay=True);value=data(doc)
        self.assertEqual(underlay['grid'],grid(doc,underlay=True))
        self.assertFalse(any(underlay['towns']))
        citadel=value['maps'][0];x,y=citadel['origin'];self.assertEqual(normal['towns'][(y//8)*128+x//8],1)
        self.assertEqual(ruined['towns'][(y//8)*128+x//8],11)
        self.assertNotEqual(normal['grid'],ruined['grid'])
        for tx,ty in ((x,y),(x+34,y+12),(x+63,y+63)):
            tile=value['tiles'][normal['grid'][ty*1024+tx]]
            color=tile.get('mini_color',value['world']['mini_colors'][tile['rule']])
            self.assertEqual(normal['mini']['pixels'][ty*1024+tx],color)

    def test_unsaved_level_stamp_patch_and_town_priority(self):
        doc=self.document.worker_copy();before=self.document.files();value=data(doc)
        change(doc,lambda v:v['world'].update(terrain=[dict(at=[0,0],level=16)],
            patches=[dict(at=[1,1],tile='chi:land-85'),dict(at=list(v['maps'][0]['origin']),tile='chi:land-85')]))
        result=world_editor_preview(doc);underlay=world_editor_preview(doc,underlay=True)
        self.assertEqual(result['levels'][0],16)
        self.assertEqual(value['tiles'][result['grid'][1025]]['id'],'chi:land-85')
        self.assertEqual(result['mini']['pixels'][1025],value['world']['mini_colors'][85])
        x,y=value['maps'][0]['origin'];self.assertEqual(value['tiles'][underlay['grid'][y*1024+x]]['id'],'chi:land-85')
        self.assertEqual(value['tiles'][result['grid'][y*1024+x]]['id'],value['maps'][0]['rows'][0][0])
        self.assertEqual(self.document.files(),before)

    def test_editing_tinyland_art_reaches_native_world_miniature(self):
        doc=self.document.worker_copy();im=detach(doc,'screen','TINYLAND.CMP')
        self.assertEqual(settings(doc)['bindings'][0]['palette'],'sprite')
        art=copy.deepcopy(doc.art);frame=next(v for v in art['images'] if v['id']==im['id'])['frames'][0]
        # Place a red registration pixel in each real glyph, then prove the
        # unsaved replacement is used by the native world renderer itself.
        for index in range(66):
            x,y=index%40*8,index//40*8;row=frame[y];frame[y]=row[:x*8]+'aa0000ff'+row[(x+1)*8:]
        doc.replace_art(art);result=world_editor_preview(doc);checked=0
        for at,level in enumerate(result['levels']):
            index=64 if level==16 else ((level-16 if level>=32 else level)|result['joins'][at])
            if result['towns'][at] or index>=66:continue
            bx,by=at%128,at//128
            self.assertEqual(result['mini']['palette'][result['mini']['pixels'][by*8*1024+bx*8]],'aa0000')
            checked+=1
        self.assertGreater(checked,10000)


if __name__=='__main__':unittest.main()
