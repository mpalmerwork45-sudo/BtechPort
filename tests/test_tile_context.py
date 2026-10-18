"""The art view uses visible map tiles and never writes to neighbouring cells."""
import copy
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from art_editing import new_image,brush,display_rows
from tile_context import neighbours,context_grid
from construction_editing import geometry,compile_rows,preset
from editor_model import encoded


class TileContextTests(unittest.TestCase):
    def fixture(self,modern):
        tiles=[dict(id='test:'+key,graphic=i,sheet='package:tiles') for i,key in enumerate('abc')]
        for tile,key in zip(tiles,'abc'):
            if not modern:tile['key']=key
        rows=[['a','b','c'],['c','a','b'],['b','c','a']]
        overlay=[[' ','c'],['b',' ']]
        convert=lambda row:['test:'+v if v!=' ' else ' ' for v in row] if modern else ''.join(row)
        scene=dict(id='test:map',name='Map',rows=[convert(r) for r in rows],overlays=[dict(at=[0,0],rows=[convert(r) for r in overlay])])
        doc=SimpleNamespace(adventure=dict(maps=[scene],tiles=tiles),art=dict(images=[]))
        colors=[tuple(tuple([color]*16) for _ in range(16)) for color in ('#112233','#445566','#778899')]
        return doc,dict(**{'package:tiles':colors})

    def test_composited_neighbours_both_map_formats(self):
        for modern in (False,True):
            with self.subTest(modern=modern):
                doc,decoded=self.fixture(modern);before=copy.deepcopy(doc.__dict__)
                result=neighbours(doc,decoded,dict(map='test:map',at=[1,1]))
                self.assertEqual([[c['tile'] for c in row] for row in result],
                    [['test:a','test:c','test:c'],['test:b','test:a','test:b'],['test:b','test:c','test:a']])
                self.assertEqual(result[0][1]['rows'][0][0],'#778899')
                self.assertEqual(doc.__dict__,before)

    def test_map_edge_has_no_wrapped_or_invented_tiles(self):
        doc,decoded=self.fixture(True);result=neighbours(doc,decoded,dict(map='test:map',at=[0,0]))
        self.assertEqual(result[0],[None]*3)
        self.assertTrue(all(row[0] is None for row in result))
        self.assertEqual(result[1][1]['tile'],'test:a')

    def test_live_art_updates_every_shared_placement_without_mutation(self):
        doc,decoded=self.fixture(True);image=new_image('test',[],'Tile')
        doc.art['images']=[image];doc.adventure['tiles'][0].update(sheet='package:art',graphic=image['id'])
        draft=copy.deepcopy(image);brush(draft,0,(0,0),(15,15),'ab12c3ff','Rectangle')
        result=neighbours(doc,decoded,dict(map='test:map',at=[1,1]),draft)
        self.assertEqual(result[0][0]['rows'],display_rows(draft))
        self.assertEqual(result[1][1]['rows'],result[2][2]['rows'])
        self.assertNotEqual(result[0][0]['rows'],display_rows(image))
        self.assertEqual(result[0][1]['rows'],decoded['package:tiles'][2])

    def test_construction_context_uses_the_clicked_projected_cell(self):
        for kind in ('Building','Wall','Road'):
            with self.subTest(kind=kind):
                doc,decoded=self.fixture(True)
                profile=dict(id='test:style',name=kind,kind=kind,footprint=preset(kind,9,9,2,'Cross'),parts={})
                roles=geometry(profile)
                profile['parts']={role:'test:'+'abc'[i%3] for i,role in enumerate(sorted({v for row in roles for v in row if v!=' '}))}
                doc.metadata={'EDITOR.json':encoded(dict(construction_sets=[profile]))}
                rows=compile_rows(profile)
                for y,row in enumerate(roles):
                    for x,role in enumerate(row):
                        if role==' ':continue
                        context=dict(construction=profile['id'],role=role,at=[x,y])
                        result=neighbours(doc,decoded,context)
                        self.assertEqual(context_grid(doc,context)[2],[x,y])
                        for dy in (-1,0,1):
                            for dx in (-1,0,1):
                                tx,ty=x+dx,y+dy;cell=result[dy+1][dx+1]
                                expected=rows[ty][tx] if 0<=ty<len(rows) and 0<=tx<len(rows[ty]) else ' '
                                self.assertEqual(cell['tile'] if cell else ' ',expected)

    def test_jigsaw_edges_and_unused_or_removed_preview(self):
        doc,decoded=self.fixture(True)
        doc.adventure['jigsaws']=[dict(id='test:jigsaw',name='Jigsaw',rows=[['test:a']*8 for _ in range(8)])]
        result=neighbours(doc,decoded,dict(jigsaw='test:jigsaw',at=[7,7]))
        self.assertEqual(result[2],[None]*3);self.assertEqual(result[1][1]['tile'],'test:a')
        profile=dict(id='test:style',name='Empty building',kind='Building',footprint=[[0]],parts=dict(roof_0_0='test:b'))
        doc.metadata={'EDITOR.json':encoded(dict(construction_sets=[profile]))}
        context=dict(construction='test:style',role='roof_0_0',at=None)
        result=neighbours(doc,decoded,context)
        self.assertEqual(sum(c is not None for row in result for c in row),1)
        self.assertEqual(result[1][1]['tile'],'test:b')
        self.assertIn('unused',context_grid(doc,context)[0])
        doc.metadata={};self.assertIsNone(neighbours(doc,decoded,context))


if __name__=='__main__':unittest.main()
