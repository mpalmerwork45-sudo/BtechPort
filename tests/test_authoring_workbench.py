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
from event_workbench import connect,dialogue_branch,edges,editor_commit,editor_data
from playtest_workbench import make_checkpoint
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

    def test_connected_dialogue_and_layout_undo(self):
        menu=service_building(self.doc,'Clinic','Clinic',{'heal':20})
        branch=dialogue_branch(self.doc,menu,'Ask about work','Come back when you need assistance.')
        connect(self.doc,branch,'next',menu);self.doc.validate()
        self.assertEqual(dict(edges(next(e for e in self.doc.adventure['events'] if e['id']==branch)))['next'],menu)
        editor_commit(self.doc,{'event_layout':{menu:[100,200]}});self.doc.undo();self.assertEqual(editor_data(self.doc),{})
        self.doc.redo();self.doc.save();reopened=ProjectDocument(self.project,TOOL)
        self.assertEqual(editor_data(reopened)['event_layout'][menu],[100,200])

    def test_objectives_journal_trace_and_snapshot_checkpoint(self):
        a=copy.deepcopy(self.doc.adventure);active,complete=a['flags'][:2]
        a['objectives']=[dict(id='beacon:objective',title='Recover the beacon',text='Find and recover the missing beacon.',active=active,complete=complete)]
        start=a['start']['event'];a['events'].append(dict(id='beacon:activate',op='flag',flag=active,value=1,next=start));a['start']['event']='beacon:activate'
        self.doc.replace_adventure(a);self.doc.save();settings={'player':str(PLAYER)}
        first=make_checkpoint(self.doc,settings,self.root/'checkpoints','journal','accept\nmenu\nup\nup\naccept\n')
        state=json.loads((first/'state.json').read_bytes());self.assertEqual(state['authored_event']['flags'][0],1)
        trace=[json.loads(line) for line in (first/'events.jsonl').read_text().splitlines()]
        self.assertEqual(trace[0]['event'],'beacon:activate');self.assertEqual(trace[1]['flags'][active],1)
        # The saved journal is a real validated continuation, and later edits
        # cannot silently change its project definitions or flag meanings.
        self.doc.content['mechs'][0]['name']='A later working revision'
        second=make_checkpoint(self.doc,settings,self.root/'checkpoints','resume','accept\n',first)
        self.assertEqual((second/'game/content.json').read_bytes(),(first/'game/content.json').read_bytes())
        self.assertEqual((second/'events.jsonl').read_text(),'')
        with self.assertRaises(EditorError):make_checkpoint(self.doc,settings,self.root/'checkpoints','resume','')

if __name__=='__main__':unittest.main()
