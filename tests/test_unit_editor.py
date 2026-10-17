"""Author new definitions through the editor model and validate with C."""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from editor_model import ProjectDocument,EditorError
from unit_editing import add_unit,add_weapon,add_equipment,assign_graphic,import_catalogue
from art_editing import new_image
from world_editing import create_world,assign_city,upgrade,get_world,all_worlds
TOOL=Path(os.environ.get('BTP_PROJECT_TOOL',ROOT/'build/btp-project'))
PLAYER=Path(os.environ.get('BTP_HEADLESS',ROOT/'build/btech-headless'))


class UnitEditorTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='btp-unit-editor-');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.project=self.root/'game';shutil.copytree(ROOT/'examples/beacon-demo',self.project)
        self.doc=ProjectDocument(self.project,TOOL)

    def test_catalogue_reimport_and_individual_graphic(self):
        ids=import_catalogue(self.doc,ROOT/'content/catalogues/vehicles');self.assertEqual(len(ids),10)
        self.doc.save();c=copy.deepcopy(self.doc.content);unit=c['mechs'][-10];unit['price']=12345;old=c['mechs'][-9]['presentation']
        assign_graphic(c,unit['id'],self.doc.art['images'][-1]['id']);self.doc.replace(c)
        import_catalogue(self.doc,ROOT/'content/catalogues/vehicles');self.assertEqual(len(self.doc.content['mechs']),13)
        self.assertEqual(self.doc.content['mechs'][-10]['price'],12345);self.assertEqual(self.doc.content['mechs'][-9]['presentation'],old)
        self.doc.save();self.doc.export(self.root/'export');self.assertEqual(ProjectDocument(self.root/'export',TOOL).art,self.doc.art)

    def test_new_mech_weapon_and_equipment(self):
        c=copy.deepcopy(self.doc.content);weapon=add_weapon(c,'srm6','Custom SRM');unit=add_unit(c)
        sink=add_equipment(c);jet=add_equipment(c,'jump_jet','Jump jet')
        model=c['mechs'][-1];model['loadout'].append(dict(weapon=weapon,location='left_arm',ammunition=15))
        model['equipment']=[dict(definition=sink,location='right_torso',quantity=2),dict(definition=jet,location='left_leg',quantity=3)]
        a=copy.deepcopy(self.doc.adventure);a['start']['party'][0]['mech']=unit;self.doc.replace_both(c,a);self.doc.save()
        result=subprocess.run([str(PLAYER),'--project',str(self.project),'--save',str(self.root/'new.btp')],capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)
        self.doc.undo();self.doc.redo();self.assertEqual(self.doc.content['mechs'][-1],model)
        c['equipment'][0]['behavior']='unsupported_ecm';self.doc.replace(c)
        with self.assertRaisesRegex(EditorError,'supported equipment'):self.doc.validate()

    def test_vehicle_limits_and_missing_sprite(self):
        import_catalogue(self.doc,ROOT/'content/catalogues/vehicles', ['vehicles:patton']);good=copy.deepcopy(self.doc.content)
        c=copy.deepcopy(good);c['mechs'][-1]['movement']['jump']=1;self.doc.replace(c)
        with self.assertRaises(EditorError):self.doc.validate()
        c=copy.deepcopy(good);c['presentations'][-1]['image']='missing:sprite';self.doc.replace(c)
        with self.assertRaisesRegex(EditorError,'sprite'):self.doc.validate()

    def test_planets_overlap_transfer_and_capacity(self):
        a=copy.deepcopy(self.doc.adventure);first=create_world(a,'test',32,32,'First');assign_city(a,'beacon:town',world_id=first)
        second=create_world(a,'test',32,32,'Second');assign_city(a,'beacon:wild',(64,64),world_id=second)
        self.doc.replace_adventure(a);self.doc.save()
        result=subprocess.run([str(PLAYER),'--project',str(self.project),'--play-here','world:planet-2-sector-1-1','24','38','--save',str(self.root/'planet.btp')],capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stderr);state=json.loads(result.stdout);self.assertEqual(state['authored_event']['planet'],2)
        loaded=subprocess.run([str(PLAYER),'--project',str(self.project),'--load',str(self.root/'planet.btp')],capture_output=True,text=True,timeout=20)
        self.assertEqual(loaded.returncode,0,loaded.stderr);self.assertEqual(state['authored_event'],json.loads(loaded.stdout)['authored_event'])
        with self.assertRaisesRegex(EditorError,'another'):assign_city(a,'beacon:town',world_id=second)
        # C catches invalid hand-edited overlap within one planet too.
        get_world(a,second)['cities']=[];get_world(a,first)['cities'].append('beacon:wild');self.doc.replace_adventure(a)
        with self.assertRaisesRegex(EditorError,'overlap'):self.doc.validate()

    def test_owned_art_file_can_be_reused_after_undo_save(self):
        art=copy.deepcopy(self.doc.art);art['images'].append(new_image('test',[]));self.doc.replace_art(art);self.doc.save()
        self.doc.undo();self.doc.save();self.assertNotIn('graphics',self.doc.manifest)
        art=copy.deepcopy(self.doc.art);art['images'].append(new_image('test',[],'Another tile'));self.doc.replace_art(art);self.doc.save()
        self.assertEqual(ProjectDocument(self.project,TOOL).art,self.doc.art)


if __name__=='__main__':unittest.main()
