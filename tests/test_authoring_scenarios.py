"""Real routes, RNG entry, combat cleanup, checkpoint and suite evidence."""
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from authoring_scenarios import run,run_suite,SCHEMA,SUITE_SCHEMA,DEFAULT_SEED
from authoring_contract import check,AuthoringError
from authoring_service import revision
from editor_model import create_project,ProjectDocument,encoded

TOOL=ROOT/'build/btp-project';RUNNER=ROOT/'build/btp-author-playtest'
SETTINGS={k:str(ROOT/p) for k,p in [('data','Original DOS'),('dialogue-data','work/talk-data.bin'),('combat-data','work/combat-data.bin'),('world-data','work/world-data.bin')]}
HAS_CHI=all(Path(p).exists() for p in SETTINGS.values())


class Scenarios(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='btp-scenarios-');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.doc=create_project(ROOT/'examples/beacon-demo',self.root/'game','scenario-test','Scenario test',TOOL)
    def scenario(self,steps,**fields):return dict(format='btp-author-scenario-v1',steps=steps,**fields)
    def execute(self,scenario,name='route',**options):
        result=run(self.doc,scenario,self.root/name,RUNNER,**options)
        return result,json.loads(Path(result['report']).read_bytes())
    def test_seed_is_observed_before_start_event_and_default_is_unchanged(self):
        basic=self.scenario([dict(op='assert',credits=2000),dict(op='checkpoint')])
        _,ordinary=self.execute(basic,'normal')
        _,explicit=self.execute(dict(basic,seed=DEFAULT_SEED),'explicit')
        self.assertEqual(ordinary['result']['state'],explicit['result']['state'])
        _,seeded=self.execute(dict(basic,seed=197121),'seeded')
        first=json.loads((self.root/'seeded/events.jsonl').read_text().splitlines()[0])
        self.assertEqual(first['rng'],[1,2,3]);self.assertEqual(seeded['result']['state']['rng'],[1,2,3])
        self.assertEqual(seeded['setup']['kind'],'ordinary_new_game')
    def test_tick_failure_has_reproduction_step_and_artifacts(self):
        result,report=self.execute(self.scenario([dict(op='input',action='idle',repeat=3)],max_ticks=1))
        self.assertEqual(result['status'],'failed');self.assertEqual(report['reproduction']['failed_step'],1)
        self.assertIn('tick budget',report['result']['message'])
        self.assertTrue((self.root/'route/final.ppm').exists());self.assertTrue((self.root/'route/replay.actions').exists())
    def test_assertion_errors_and_revision_mismatch_are_explicit(self):
        result,report=self.execute(self.scenario([dict(op='assert',credits=123)]))
        self.assertEqual(result['status'],'failed');self.assertEqual(report['result']['state']['credits'],2000)
        with self.assertRaises(AuthoringError):self.execute(self.scenario([dict(op='checkpoint')],expected_revision='0'*64),'stale')
        self.assertFalse((self.root/'stale').exists())
    def test_cancellation_and_wall_budget_do_not_launch_a_player(self):
        scenario=self.scenario([dict(op='checkpoint')])
        with patch('authoring_scenarios.subprocess.Popen') as launch:
            result,report=self.execute(scenario,'cancel',cancelled=lambda:True)
            self.assertEqual(result['status'],'cancelled');self.assertEqual(report['diagnostics'][0]['code'],'job.cancelled');launch.assert_not_called()
            result,report=self.execute(scenario,'timeout',timeout_seconds=0)
            self.assertEqual(result['status'],'failed');self.assertEqual(report['diagnostics'][0]['code'],'scenario.timeout');launch.assert_not_called()
    def test_suite_fixture_is_labelled_and_preserves_source(self):
        before=self.doc.files();base=revision(self.doc)
        (self.root/'normal.json').write_bytes(encoded(self.scenario([dict(op='assert',credits=2000)])))
        (self.root/'poor.json').write_bytes(encoded(self.scenario([dict(op='assert',credits=7),dict(op='checkpoint')])))
        request=dict(api_version=1,request_id='poor-fixture',project_id='scenario-test',expected_revision='new',label='Low funds fixture',
            scope=['adventure.start'],operations=[dict(op='start.set',changes={'credits':7})])
        (self.root/'poor.commands.json').write_bytes(encoded(request))
        suite=dict(format='btp-author-suite-v1',cases=[dict(id='normal',file='normal.json',seeds=[42,1979]),
            dict(id='poor',file='poor.json',fixture='poor.commands.json')])
        result=run_suite(self.doc,suite,self.root,self.root/'suite',RUNNER)
        report=json.loads(Path(result['report']).read_bytes())
        self.assertEqual(result['status'],'passed');self.assertEqual(result['runs_completed'],3)
        self.assertEqual(report['runs'][-1]['setup']['kind'],'validated_fixture')
        self.assertEqual(report['runs'][-1]['setup']['source_revision'],base)
        self.assertEqual(self.doc.files(),before)
    def test_failed_fixture_keeps_prior_case_report(self):
        (self.root/'ok.json').write_bytes(encoded(self.scenario([dict(op='checkpoint')])))
        suite=dict(format='btp-author-suite-v1',cases=[dict(id='ok',file='ok.json'),dict(id='bad',file='ok.json',fixture='missing.json')])
        result=run_suite(self.doc,suite,self.root,self.root/'suite',RUNNER)
        report=json.loads(Path(result['report']).read_bytes())
        self.assertEqual(result['status'],'failed');self.assertEqual(report['stopped'],'setup_failed')
        self.assertTrue(Path(report['runs'][0]['report']).is_file())
    def test_suite_bounds_and_invalid_fields_are_rejected(self):
        (self.root/'ok.json').write_bytes(encoded(self.scenario([dict(op='checkpoint')])))
        suite=dict(format='btp-author-suite-v1',cases=[dict(id='same',file='ok.json'),dict(id='same',file='ok.json')])
        with self.assertRaises(AuthoringError):run_suite(self.doc,suite,self.root,self.root/'bad',RUNNER)
        self.assertFalse((self.root/'bad').exists())
        for scenario in [self.scenario([dict(op='assert',health_min=1)]),self.scenario([dict(op='battle',control='force-win')]),self.scenario([dict(op='checkpoint')],seed=0)]:
            with self.assertRaises(AuthoringError):check(scenario,SCHEMA)
    def test_rerun_only_selected_cases(self):
        (self.root/'ok.json').write_bytes(encoded(self.scenario([dict(op='checkpoint')])))
        suite=dict(format='btp-author-suite-v1',cases=[dict(id='ok',file='ok.json'),dict(id='unrelated',file='not-needed.json')])
        result=run_suite(self.doc,suite,self.root,self.root/'selected',RUNNER,case_ids=['ok'])
        self.assertEqual(result['status'],'passed');self.assertEqual(result['runs_completed'],1)
        with self.assertRaises(AuthoringError):run_suite(self.doc,suite,self.root,self.root/'bad',RUNNER,case_ids=['unknown'])
    @unittest.skipUnless(HAS_CHI,'CHI data/caches are supplied locally')
    def test_recorded_branches_and_combat_reports(self):
        doc=ProjectDocument(ROOT/'examples/relay-contract',TOOL)
        folder=ROOT/'examples/authoring/scenarios';suite=json.loads((folder/'relay.suite.json').read_text())
        result=run_suite(doc,suite,folder,self.root/'relay-suite',RUNNER,SETTINGS)
        self.assertEqual(result['status'],'passed');self.assertEqual(result['runs_completed'],10)
        report=json.loads(Path(result['report']).read_bytes());samples={s['case']:s for s in report['combat_samples']}
        self.assertEqual(samples['victory']['wins'],3);self.assertEqual(samples['retreat']['retreats'],1)
        self.assertEqual(samples['defeat']['losses'],1);self.assertEqual(samples['defeat']['friendly_mechs_lost'],1)
        self.assertEqual(samples['retreat']['mean_armor_reduction'],0)
        win=json.loads(Path(report['runs'][0]['report']).read_bytes())
        self.assertEqual(win['result']['state']['credits'],9000);self.assertEqual(win['combat'][0]['ammunition_reduction'],6)
        self.assertTrue(any(s['state']['phase']=='battle' and s['state']['battle']['round']>=1 for s in win['steps']))
        events=[json.loads(line) for line in (Path(report['runs'][0]['report']).parent/'events.jsonl').read_text().splitlines()]
        self.assertEqual(sum(e['event']=='relay:pay' for e in events),1)


if __name__=='__main__':unittest.main()
