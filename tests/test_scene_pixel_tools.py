import copy
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from editor_model import ProjectDocument,EditorError
from art_editing import new_image,brush,import_image
from pixel_tools import begin_layers,target,flatten,export_layers,add_layer,selected_pixels,paste_selection,resize_canvas,export_sheet
from scene_tools import capture_stamp,place_stamp,move_group,generate_world,formation_data,formation_cells
from event_workbench import editor_data
from world_editing import create_world,add_jigsaw,get_world
from unit_library import closure,stage_preview
TOOL=Path(os.environ.get('BTP_PROJECT_TOOL',ROOT/'build/btp-project'))

class ScenePixelTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        shutil.copytree(ROOT/'examples/beacon-demo',self.root/'game');self.doc=ProjectDocument(self.root/'game',TOOL)

    def test_layers_selection_crop_export_roundtrip(self):
        image=begin_layers(new_image('test',[],'Sprite','sprite',8,6,4));brush(target(image),0,(0,0),(7,5),'ff0000ff','Rectangle');flatten(image)
        add_layer(image,'Highlights');brush(target(image),0,(1,1),(1,1),'0000ff80');flatten(image)
        self.assertEqual(image['frames'][0][1][8:16],'7f0080ff')
        clip=selected_pixels(image,0,(1,1,1,1));paste_selection(image,1,clip,3,3)
        self.assertEqual(image['frames'][1][3][24:32],'0000ff80')
        resize_canvas(image,4,4,1,1);self.assertEqual(image['frames'][0][0][:8],'7f0080ff')
        clean,layers=export_layers(image);reopened=begin_layers(clean,layers);self.assertEqual(reopened,image)
        export_sheet(image,self.root/'sheet.png',2);restored=import_image(self.root/'sheet.png','test',[],'sprite',4,4)
        self.assertEqual(restored['frames'],image['frames'])
        image['_layers'][1]['visible']=False;flatten(image);self.assertEqual(image['frames'][0][0][:8],'ff0000ff')
        tile=begin_layers(new_image('test',[]));old=copy.deepcopy(tile)
        with self.assertRaises(EditorError):resize_canvas(tile,8,8)
        self.assertEqual(tile,old)

    def test_building_capture_group_and_single_undo(self):
        scene=self.doc.adventure['maps'][0];door=scene['entrances'][0];x,y=[v//2 for v in door['at']]
        stamp=capture_stamp(self.doc,0,(x,y,x+1,y+1),'Depot');index=place_stamp(self.doc,0,stamp,24,18)-1
        before=copy.deepcopy(self.doc.adventure);created=before['maps'][0]['entrances'][-1]
        move_group(self.doc,0,index,26,21);moved=self.doc.adventure['maps'][0]['entrances'][-1]
        self.assertEqual(moved['at'],[created['at'][0]+4,created['at'][1]+6]);self.assertEqual(moved['event'],door['event'])
        self.doc.undo();self.assertEqual(self.doc.adventure,before);self.doc.redo();self.doc.validate();self.doc.save()
        self.assertEqual(editor_data(ProjectDocument(self.root/'game',TOOL)),editor_data(self.doc))

    def test_seeded_world_and_starting_footprints(self):
        a=copy.deepcopy(self.doc.adventure);world=create_world(a,'beacon',8,8);second=add_jigsaw(a,'beacon',name='Other clear ground');self.doc.replace_adventure(a)
        weights={j['id']:i+1 for i,j in enumerate(a['jigsaws'])}
        generate_world(self.doc,world,42,weights);first=copy.deepcopy(get_world(self.doc.adventure,world)['pieces'])
        generate_world(self.doc,world,42,weights);self.assertEqual(get_world(self.doc.adventure,world)['pieces'],first)
        self.assertEqual(set(p for row in first for p in row),set(weights));self.doc.validate()
        formation=formation_data(self.doc,{})
        cells=formation_cells(self.doc,0,self.doc.adventure['start']['at'],formation)
        self.assertTrue(cells);self.assertFalse(any(blocked for x,y,blocked in cells))

if __name__=='__main__':unittest.main()
