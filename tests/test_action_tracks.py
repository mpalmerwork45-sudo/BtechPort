import copy,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from editor_model import ProjectDocument,EditorError
from editor_model import create_project
from art_editing import new_image
from action_tracks import set_track,parse_sequence
from unit_library import closure,import_units
from construction_guidance import report

class ActionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.doc=create_project(ROOT/'examples/beacon-demo',self.root/'game','actions-test','Action test',ROOT/'build/btp-project')
    def tearDown(self):self.tmp.cleanup()
    def test_action_parse_and_person_library(self):
        im=new_image('actions-test',[],'Actions','sprite',8,8,64)
        set_track(im,'fire',['1:4 64:10']*8,3);set_track(im,'idle',['2:4 3:2'])
        art=copy.deepcopy(self.doc.art);art['images'].append(im)
        a=copy.deepcopy(self.doc.adventure);a['people'][0]['image']=im['id']
        self.doc.replace_art(art,a);self.doc.validate();self.doc.save()
        bundle=closure(self.doc,a['people'][0]['id'],'Infantry')
        self.assertEqual(bundle['graphics']['images'][0]['animations'],im['animations'])
        other=create_project(ROOT/'examples/beacon-demo',self.root/'other','actions-other','Other',ROOT/'build/btp-project')
        import_units(other,[bundle],policy='variant');other.validate()
        self.assertEqual(other.adventure['people'][-1]['image'],im['id'])
        broken=copy.deepcopy(art);broken['images'][-1]['animations']['fire']['directions'][0][0]['frame']=64
        self.doc.replace_art(broken)
        with self.assertRaises(EditorError):self.doc.validate()
        with self.assertRaises(EditorError):parse_sequence('1:255 2:1',64)
        with self.assertRaises(EditorError):set_track(im,'walk',['1:2'],3)
    def test_equipment_and_guidance(self):
        c=copy.deepcopy(self.doc.content);u=c['mechs'][0]
        c.setdefault('equipment',[]).extend([dict(id='actions-test:sink',name='Engine sink',label='Engine sink',behavior='engine_heat_sink'),dict(id='actions-test:plate',name='Plating',label='Plating',behavior='armor_plating')])
        u['equipment']=[dict(definition='actions-test:sink',location='center_torso',quantity=2),dict(definition='actions-test:plate',location='left_arm',quantity=1)]
        u['armor']['left_arm']=1
        self.doc.replace(c);self.doc.validate()
        self.assertIn(f"Cooling {u['engine_heat_sinks']+sum(u['external_heat_sinks'].values())+2}/30",report(c,u))
        bad=copy.deepcopy(c);bad['mechs'][0]['equipment'][0]['location']='head';self.doc.replace(bad)
        with self.assertRaisesRegex(EditorError,'center_torso'):self.doc.validate()

if __name__=='__main__':unittest.main()
