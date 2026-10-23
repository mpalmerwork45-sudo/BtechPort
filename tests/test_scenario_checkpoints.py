"""Pinned saved journeys, exact continuations and honest partial coverage."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from authoring_scenarios import run,run_suite,pin_checkpoint,SCHEMA
from authoring_contract import check,AuthoringError
from editor_model import ProjectDocument,encoded
from world_route_demo import create,journey
from checkpoint_demo import compare
from campaign_source import convert

TOOL=ROOT/'build/btp-project';RUNNER=Path(os.environ.get('BTP_CHECKPOINT_RUNNER',ROOT/'build/btp-author-playtest'))
SETTINGS={k:str(ROOT/v) for k,v in [('data','Original DOS'),('dialogue-data','work/talk-data.bin'),('combat-data','work/combat-data.bin'),('world-data','work/world-data.bin')]}


class CheckpointScenarios(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='btp-saved-journey-');self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.doc=create(self.root/'game',TOOL)

    def start(self):
        result=run(self.doc,dict(format='btp-author-scenario-v1',seed=197121,steps=[
            dict(op='walk',world='survey:aster',at=[54,64]),dict(op='checkpoint',name='departed')]),self.root/'prefix',RUNNER)
        self.assertEqual(result['status'],'passed',result)
        save=self.root/'prefix/checkpoint-departed.btp'
        scenario=dict(format='btp-author-scenario-v1',checkpoint=pin_checkpoint(save),steps=[dict(op='assert',world_at=[54,64]),dict(op='checkpoint',name='resumed')])
        return scenario,result

    def test_two_planets_match_full_journey_and_source_project(self):
        route=journey();split=next(i for i,s in enumerate(route['steps']) if s.get('world')=='survey:boreal' and s['op']=='walk')
        for name,doc in [('package',self.doc),('source',convert(self.doc,self.root/'sources'))]:
            before=doc.source_files() if doc.source else doc.files()
            result=compare(doc,route,split,self.root/name,RUNNER)
            self.assertTrue(result['exact_save_equality']);self.assertGreater(result['skipped_ticks'],100)
            self.assertEqual(doc.source_files() if doc.source else doc.files(),before)
            report=json.loads((self.root/name/'resumed/report.json').read_bytes())
            self.assertEqual(report['setup']['kind'],'saved_checkpoint');self.assertIsNone(report['seed'])
            self.assertNotIn('survey:outbound',report['coverage']['events']);self.assertIn('survey:homebound',report['coverage']['events'])
            self.assertIn('source_report',report['setup']);self.assertTrue((self.root/name/'resumed/initial-report.json').is_file())

    def test_input_copy_rng_hash_and_plain_replay_survive_missing_origin(self):
        scenario,prefix=self.start();result=run(self.doc,scenario,self.root/'resume',RUNNER)
        self.assertEqual(result['status'],'passed',result)
        self.assertEqual(result['result']['start_rng'],prefix['result']['state']['rng'])
        self.assertEqual(result['result']['start_tick'],prefix['result']['state']['tick'])
        self.assertEqual((self.root/'resume/initial.btp').read_bytes(),Path(scenario['checkpoint']['file']).read_bytes())
        Path(scenario['checkpoint']['file']).unlink()
        staged=json.loads((self.root/'resume/scenario.json').read_bytes())
        rerun=run(self.doc,staged,self.root/'reproduction',RUNNER,base_dir=self.root/'resume')
        self.assertEqual(rerun['result'],result['result'])
        p=subprocess.run([str(ROOT/'build/btech-headless'),'--project',str(self.doc.root),'--load',str(self.root/'resume/initial.btp'),
            '--replay',str(self.root/'resume/replay.actions'),'--save',str(self.root/'plain.btp')],capture_output=True,text=True,timeout=15)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual((self.root/'plain.btp').read_bytes(),(self.root/'resume'/result['result']['save']).read_bytes())

    def test_corrupt_stale_missing_and_hash_mismatch_fail_without_new_game(self):
        scenario,_=self.start();save=Path(scenario['checkpoint']['file'])
        wrong=copy.deepcopy(scenario);wrong['checkpoint']['sha256']='0'*64
        with self.assertRaises(AuthoringError) as error:run(self.doc,wrong,self.root/'hash',RUNNER)
        self.assertEqual(error.exception.diagnostic['code'],'checkpoint.hash_mismatch');self.assertFalse((self.root/'hash').exists())
        missing=copy.deepcopy(scenario);missing['checkpoint']['file']='missing.btp'
        with self.assertRaises(AuthoringError):run(self.doc,missing,self.root/'missing',RUNNER,base_dir=self.root)
        data=bytearray(save.read_bytes());data[-3]^=1;(self.root/'corrupt.btp').write_bytes(data)
        corrupt=dict(scenario,checkpoint=pin_checkpoint(self.root/'corrupt.btp'))
        result=run(self.doc,corrupt,self.root/'bad-crc',RUNNER)
        self.assertEqual(result['diagnostics'][0]['code'],'checkpoint.invalid');self.assertFalse(result['result'])
        self.assertFalse((self.root/'bad-crc/events.jsonl').exists())
        a=copy.deepcopy(self.doc.adventure);a['start']['credits']+=1;self.doc.replace_adventure(a)
        result=run(self.doc,scenario,self.root/'stale',RUNNER)
        self.assertEqual(result['status'],'failed');self.assertIn('exact saved content',result['diagnostics'][0]['message'])
        self.assertFalse((self.root/'stale/replay.actions').exists())

    def test_named_outputs_schema_seed_sweep_and_bounds(self):
        scenario,_=self.start()
        for request in [dict(scenario,seed=42),dict(scenario,steps=[dict(op='checkpoint',name='../escape')])]:
            with self.assertRaises(AuthoringError):check(request,SCHEMA)
        with self.assertRaises(AuthoringError):run(self.doc,dict(scenario,steps=[dict(op='checkpoint',name='same')]*2),self.root/'duplicate',RUNNER)
        (self.root/'case.json').write_bytes(encoded(scenario))
        suite=dict(format='btp-author-suite-v1',cases=[dict(id='saved',file='case.json',seeds=[42])])
        with self.assertRaises(AuthoringError):run_suite(self.doc,suite,self.root,self.root/'sweep',RUNNER)
        (self.root/'tiny.btp').write_bytes(b'BTG1')
        with self.assertRaises(AuthoringError):pin_checkpoint(self.root/'tiny.btp')

    def test_suite_and_cli_resolve_relative_to_scenario_not_cwd(self):
        scenario,_=self.start();case=self.root/'nested';case.mkdir()
        scenario['checkpoint']['file']='../prefix/checkpoint-departed.btp'
        (case/'case.json').write_bytes(encoded(scenario))
        suite=dict(format='btp-author-suite-v1',cases=[dict(id='saved',file='nested/case.json')])
        result=run_suite(self.doc,suite,self.root,self.root/'suite',RUNNER)
        self.assertEqual(result['status'],'passed');self.assertEqual(result['runs_completed'],1)
        report=json.loads(Path(result['report']).read_bytes());self.assertIsNone(report['runs'][0]['seed'])
        p=subprocess.run([sys.executable,str(ROOT/'tools/author.py'),'scenario',str(self.doc.root),'--file',str(case/'case.json'),
            '--output',str(self.root/'cli'),'--runner',str(RUNNER)],cwd=self.root,capture_output=True,text=True,timeout=20)
        self.assertEqual(p.returncode,0,p.stderr+p.stdout)
        self.assertEqual(json.loads(p.stdout)['status'],'passed')

    def test_native_independently_rejects_bad_pin_and_existing_named_output(self):
        scenario,_=self.start();scenario['checkpoint']['sha256']='0'*64
        source=self.root/'request.json';source.write_bytes(encoded(scenario))
        out=self.root/'native';out.mkdir()
        command=[str(RUNNER),'--project',str(self.doc.root),'--scenario',str(source)]
        p=subprocess.run(command,cwd=out,capture_output=True,text=True,timeout=15)
        self.assertNotEqual(p.returncode,0);self.assertIn('SHA-256 mismatch',p.stderr);self.assertFalse((out/'replay.actions').exists())
        scenario['checkpoint']=pin_checkpoint(self.root/'prefix/checkpoint-departed.btp');source.write_bytes(encoded(scenario))
        p=subprocess.run(command,cwd=out,capture_output=True,text=True,timeout=15);self.assertEqual(p.returncode,0,p.stderr)
        before=(out/'checkpoint-resumed.btp').read_bytes()
        p=subprocess.run(command,cwd=out,capture_output=True,text=True,timeout=15)
        self.assertNotEqual(p.returncode,0);self.assertIn('already exists',p.stdout)
        self.assertEqual((out/'checkpoint-resumed.btp').read_bytes(),before)

    def test_cancelled_resume_keeps_pin_without_launching_and_inspection(self):
        scenario,_=self.start()
        with patch('authoring_scenarios.subprocess.Popen') as launch:
            result=run(self.doc,scenario,self.root/'cancelled',RUNNER,cancelled=lambda:True)
            launch.assert_not_called();self.assertEqual(result['status'],'cancelled')
        report=json.loads(Path(result['report']).read_bytes());self.assertIsNone(report['setup']['initial_state'])
        self.assertEqual(hashlib.sha256((self.root/'cancelled/initial.btp').read_bytes()).hexdigest(),scenario['checkpoint']['sha256'])

    @unittest.skipUnless(all(Path(v).exists() for v in SETTINGS.values()),'CHI assets supplied locally')
    def test_late_contract_and_saved_battle_policy_and_metrics(self):
        doc=ProjectDocument(ROOT/'examples/cairn-passage',TOOL)
        for name,file,condition in [('contract','full-contract.json',lambda s:s.get('label')=='Begin escort'),
                                    ('battle','defence.json',lambda s:s.get('until_round')==3)]:
            route=json.loads((ROOT/'examples/authoring/cairn'/file).read_bytes())
            split=next(i for i,s in enumerate(route['steps']) if condition(s))
            compare(doc,route,split,self.root/name,RUNNER,SETTINGS)
        report=json.loads((self.root/'battle/resumed/report.json').read_bytes())
        self.assertEqual(report['combat'][0]['metric_basis'],'since_checkpoint');self.assertEqual(report['combat'][0]['start_round'],2)
        route=json.loads((self.root/'battle/continue.json').read_bytes());route['steps']=[dict(op='battle',control='hold')]
        bad=run(doc,route,self.root/'wrong-policy',RUNNER,SETTINGS,base_dir=self.root/'battle')
        self.assertEqual(bad['status'],'failed');self.assertIn('saved control',bad['result']['message']);self.assertEqual(bad['result']['ticks'],0)


if __name__=='__main__':unittest.main()
