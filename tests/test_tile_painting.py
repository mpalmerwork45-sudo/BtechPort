"""Painting the displayed surface must agree with composed game terrain."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from adventure_editing import composite,paint,visible_layer
from world_editing import draw,fill
from map_patterns import paste


class VisiblePaintingTests(unittest.TestCase):
    def scene(self,lists=False):
        scene=dict(rows=['......']*5,overlays=[dict(at=[1,1],rows=['###','# #','###']),dict(at=[2,1],rows=['T ',' T'])])
        if lists:
            for layer in [scene,*scene['overlays']]:layer['rows']=[list(r) for r in layer['rows']]
        return scene

    def test_brush_crosses_base_roof_transparency_and_stacked_overlays(self):
        for lists in (False,True):
            with self.subTest(lists=lists):
                scene=self.scene(lists);before=copy.deepcopy(scene)
                draw(scene,-1,(0,1),(5,1),'w')
                self.assertEqual(composite(scene)[1],list('wwwwww'))
                self.assertEqual(scene['rows'][1][1:4],before['rows'][1][1:4])
                self.assertEqual(scene['overlays'][0]['rows'][0][1],'#')
                self.assertEqual(scene['overlays'][1]['rows'][0][0],'w')
                self.assertEqual(visible_layer(scene,2,2),0)
                paint(scene,-1,2,2,'w');self.assertEqual(scene['rows'][2][2],'w')

    def test_fill_follows_visible_water_boundary_and_never_leaks_below_roof(self):
        scene=dict(rows=['.....']*5,overlays=[dict(at=[1,1],rows=['###','# #','###'])])
        fill(scene,-1,0,0,'w')
        self.assertEqual(composite(scene)[0],list('wwwww'))
        self.assertEqual(scene['rows'][1][1:4],'...')
        self.assertEqual(composite(scene)[2][2],'.')
        fill(scene,-1,2,2,'w');self.assertEqual(composite(scene)[2][2],'w')
        fill(scene,-1,1,1,'d');self.assertEqual(scene['overlays'][0]['rows'][0],'ddd')
        self.assertEqual(composite(scene)[2],list('wdwdw'))

    def test_visible_eraser_reveals_next_surface_and_leaves_base_intact(self):
        scene=self.scene();paint(scene,-1,2,1,' ')
        self.assertEqual(composite(scene)[1][2],'#')
        paint(scene,-1,2,1,' ');self.assertEqual(composite(scene)[1][2],'.')
        before=copy.deepcopy(scene);paint(scene,-1,2,1,' ');self.assertEqual(scene,before)

    def test_explicit_layers_still_allow_underpainting(self):
        scene=self.scene();paint(scene,0,2,1,'w')
        self.assertEqual(scene['rows'][1][2],'w');self.assertEqual(composite(scene)[1][2],'T')
        paint(scene,1,2,1,'d');self.assertEqual(composite(scene)[1][2],'T')
        paint(scene,2,2,1,'w');self.assertEqual(composite(scene)[1][2],'w')

    def test_rectangle_and_pattern_paste_replace_visible_cells_across_layers(self):
        scene=self.scene();draw(scene,-1,(0,0),(3,3),'w','Rectangle')
        self.assertTrue(all(t=='w' for r in composite(scene)[:4] for t in r[:4]))
        a=dict(maps=[scene],tiles=[dict(id='test:road',key='d')])
        paste(a,0,-1,0,1,[['test:road']*5])
        self.assertEqual(composite(scene)[1][:5],list('ddddd'))
        self.assertEqual(scene['rows'][1][1:4],'...')


if __name__=='__main__':unittest.main()
