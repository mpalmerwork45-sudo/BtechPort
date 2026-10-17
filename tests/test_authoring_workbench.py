"""Service authoring and real-player continuation checks, without GUI timing."""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from editor_model import ProjectDocument,EditorError
from building_templates import service_building
TOOL=Path(os.environ.get('BTP_PROJECT_TOOL',ROOT/'build/btp-project'))
PLAYER=Path(os.environ.get('BTP_HEADLESS',ROOT/'build/btech-headless'))

class AuthoringWorkbenchTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.project=self.root/'game';shutil.copytree(ROOT/'examples/beacon-demo',self.project)
        self.doc=ProjectDocument(self.project,TOOL)

    def run_game(self,actions='',load=None):
        replay=self.root/'replay.txt';replay.write_text(actions)
        args=[str(PLAYER),'--project',str(self.project),'--replay',str(replay),'--save',str(self.root/'save.btp')]
        if load:args+=['--load',str(load)]
        result=subprocess.run(args,check=True,capture_output=True,text=True,timeout=15)
        return json.loads(result.stdout)

    def test_service_building_roundtrip_once_only_salvage(self):
        before=copy.deepcopy(self.doc.adventure)
        menu=service_building(self.doc,'Full service depot','Workshop',{op:100 for op in ('repair','rearm','heal','salvage')},self.doc.content['mechs'][0]['id'])
        self.doc.validate();self.doc.undo();self.assertEqual(self.doc.adventure,before);self.doc.redo()
        a=copy.deepcopy(self.doc.adventure);a['start'].update(event=menu,credits=10000);self.doc.replace_adventure(a);self.doc.save()
        state=self.run_game('down\ndown\ndown\naccept\n');self.assertEqual(state['credits'],9900)
        state=self.run_game('accept\ndown\ndown\ndown\naccept\n',self.root/'save.btp')
        self.assertEqual(state['credits'],9900)
        node=self.doc.adventure['events'][state['authored_event']['node']]
        self.assertIn('no work',node['text'])
        # Healthy-party healing is a no-op: the dialogue branch is explicit
        # and the engine never charges the configured fee a second time.
        state=self.run_game('accept\ndown\ndown\naccept\n',self.root/'save.btp')
        self.assertEqual(state['credits'],9900)

    def test_service_validation_and_entrance_attachment(self):
        door=self.doc.adventure['maps'][0]['entrances'][0]['id']
        node=service_building(self.doc,'Clinic','Clinic',{'heal':20},door=door)
        self.assertEqual(self.doc.adventure['maps'][0]['entrances'][0]['event'],node);self.doc.validate()
        a=copy.deepcopy(self.doc.adventure);e=next(e for e in a['events'] if e['op']=='heal');e['slot']=8
        self.doc.replace_adventure(a)
        with self.assertRaises(EditorError):self.doc.save()

if __name__=='__main__':unittest.main()
