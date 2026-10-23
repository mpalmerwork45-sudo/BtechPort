"""Suite definitions are ordinary authoring data; only native runs prove passes."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import suite_authoring as model
from authoring_contract import AuthoringError,read_json
from authoring_service import revision,check_metadata
from authoring_impact import verify_inputs
from editor_model import ProjectDocument,encoded
from review_selection_demo import create

TOOL=ROOT/'build/btp-project';RUNNER=ROOT/'build/btp-author-playtest'


class SuiteAuthoring(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='btp-suites-');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.doc,self.path=create(self.root/'fixture',TOOL);self.value=model.import_suite(self.path,'regression')

    def test_edit_undo_save_and_source_roundtrip(self):
        before=revision(self.doc);model.put(self.doc,self.value);check_metadata(self.doc)
        self.assertNotEqual(before,revision(self.doc));self.doc.undo();self.assertEqual(before,revision(self.doc));self.doc.redo()
        self.doc.save();reopened=ProjectDocument(self.doc.root,TOOL);self.assertEqual(model.suites(reopened),[self.value])
        from campaign_source import convert
        source=convert(reopened,self.root/'source');self.assertEqual(model.suites(source),[self.value])
        edited=copy.deepcopy(self.value);edited['name']='Source tests';model.put(source,edited,'regression');source.save()
        self.assertEqual(model.suites(ProjectDocument(source.root,TOOL)),[edited])

    def test_invalid_cases_and_limits(self):
        variants=[]
        for mutate in [lambda s:s['cases'].append(copy.deepcopy(s['cases'][0])),
                       lambda s:s['cases'][0].update(seeds=[1,1]),
                       lambda s:s.update(id='../escape'),lambda s:s.update(max_seconds=301),
                       lambda s:s['cases'][0].update(file='and-owned.json'),
                       lambda s:s['cases'][0]['scenario'].update(steps=[]),
                       lambda s:s['cases'][0]['fixture_commands'].update(expected_revision='a'*64),
                       lambda s:s['cases'][0]['scenario'].update(unknown=True)]:
            value=copy.deepcopy(self.value);mutate(value);variants.append(value)
        for value in variants:
            with self.assertRaises(AuthoringError):model.put(self.doc,value)
        self.assertFalse(model.suites(self.doc))
        model.put(self.doc,dict(id='draft',name='Draft',cases=[]))
        with self.assertRaises(AuthoringError):model.export_suite(self.doc,model.suites(self.doc)[0],self.root/'empty')

    def test_export_is_portable_pinned_and_non_destructive(self):
        output=self.root/'export';inputs=model.export_suite(self.doc,self.value,output);path=verify_inputs(output,inputs)
        self.path.unlink();(self.path.parent/'yard.json').unlink();(self.path.parent/'yard.commands.json').unlink()
        imported=model.import_suite(path,'again');self.assertEqual(imported['cases'][0]['scenario'],self.value['cases'][0]['scenario'])
        with self.assertRaises(FileExistsError):model.export_suite(self.doc,self.value,output)
        with self.assertRaises(AuthoringError):model.export_suite(self.doc,self.value,self.doc.root/'tests')
        path.write_bytes(b'{}')
        with self.assertRaises(AuthoringError):verify_inputs(output,inputs)

    def test_selected_full_observation_and_unrun(self):
        model.put(self.doc,self.value);full=model.run(self.doc,self.value,self.root/'full',RUNNER)
        self.assertEqual(full['status'],'passed');self.assertEqual(full['runs_completed'],5)
        partial=model.run(self.doc,self.value,self.root/'partial',RUNNER,case_ids=['yard']);coverage=partial['inventory']
        self.assertEqual([c['status'] for c in coverage['cases']],['passed','not_run','not_run'])
        self.assertIn('survey:yard-welcome',coverage['cases'][0]['observed_events'])
        self.assertTrue(any(b['observed'] for b in coverage['branches']))
        self.assertFalse(next(e for e in coverage['events'] if e['id']=='survey:range-welcome')['observed'])
        self.assertTrue(next(e for e in coverage['events'] if e['id']=='survey:range-welcome')['declared'])
        for actual in read_json(Path(partial['report']))['runs']:
            expected=next(r for r in read_json(Path(full['report']))['runs'] if r['case']==actual['case'] and r['seed']==actual['seed'])
            self.assertEqual(read_json(Path(actual['report']))['result'],read_json(Path(expected['report']))['result'])

    def test_unknowns_and_stale_reports_do_not_imply_passes(self):
        self.value['cases'][0]['scenario']['steps'].insert(0,dict(op='input',action='wait'))
        out=self.root/'export';model.export_suite(self.doc,self.value,out);path=out/'inputs/suite.json';suite=read_json(path)
        inventory=model.coverage(self.doc,suite,path.parent)
        self.assertTrue(inventory['cases'][0]['unknown']);self.assertTrue(all(c['status']=='not_run' for c in inventory['cases']))
        fake=dict(revision='0'*64,coverage=dict(events=['survey:end']),case_results={'yard':dict(status='passed')})
        inventory=model.coverage(self.doc,suite,path.parent,fake)
        self.assertTrue(inventory['historical']);self.assertFalse(any(e['observed'] for e in inventory['events']))

    def test_starters_and_objective_are_honest(self):
        for kind,target,at in [('start',None,None),('entrance','survey:shuttle',None),('map','survey:home',[16,20]),('world','survey:aster',[54,64])]:
            scenario=model.scaffold(self.doc,kind,target,at);value=dict(id='starter',name='Starter',cases=[dict(id=kind,scenario=scenario)])
            result=model.run(self.doc,value,self.root/kind,RUNNER);self.assertEqual(result['status'],'passed',result)
        # A declared but unachieved objective must fail its native assertion.
        doc=self.doc;a=copy.deepcopy(doc.adventure)
        a['objectives']=[dict(id='survey:goal',title='Goal',text='Reach the goal.',initial='active')];doc.replace_adventure(a)
        objective=doc.adventure['objectives'][0]['id'];scenario=model.scaffold(doc,'objective',objective)
        self.assertEqual([s['op'] for s in scenario['steps']],['pages','assert','checkpoint'])
        result=model.run(doc,dict(id='objective',name='Objective',cases=[dict(id='objective',scenario=scenario)]),self.root/'objective',RUNNER)
        self.assertEqual(result['status'],'failed');self.assertTrue(result['inventory']['cases'][0]['diagnostics'])
        with self.assertRaises(AuthoringError):model.scaffold(self.doc,'entrance','survey:missing')

    def test_pinned_checkpoint_cannot_sweep_seeds(self):
        first=model.run(self.doc,self.value,self.root/'first',RUNNER,case_ids=['world']);run=read_json(Path(first['report']))['runs'][0]
        detail=read_json(Path(run['report']));save=Path(run['report']).parent/detail['result']['save']
        scenario=model.scaffold(self.doc,'start',checkpoint=save)
        value=dict(id='continuation',name='Continuation',cases=[dict(id='resume',scenario=scenario)])
        result=model.run(self.doc,value,self.root/'resume',RUNNER);self.assertEqual(result['status'],'passed')
        self.assertTrue(result['inventory']['cases'][0]['unknown'])
        value['cases'][0]['seeds']=[1]
        with self.assertRaises(AuthoringError):model.validate_suite(value)

    def test_external_reference_and_cancelled_export(self):
        self.value['cases'][0].pop('scenario');self.value['cases'][0]['file']=str(self.path.parent/'yard.json')
        result=model.run(self.doc,self.value,self.root/'reference',RUNNER,case_ids=['yard']);self.assertEqual(result['status'],'passed')
        with self.assertRaises(AuthoringError):model.export_suite(self.doc,self.value,self.root/'cancel',lambda:True)
        self.assertFalse(model.suites(self.doc));self.assertTrue(self.path.exists())

    def test_cancelled_native_suite_retains_partial_evidence(self):
        import authoring_scenarios
        original=authoring_scenarios.run;stopped=False
        def one(*args,**kwargs):
            nonlocal stopped
            result=original(*args,**kwargs);stopped=True;return result
        with patch('authoring_scenarios.run',side_effect=one):
            result=model.run(self.doc,self.value,self.root/'partial-cancel',RUNNER,cancelled=lambda:stopped)
        self.assertEqual(result['status'],'cancelled');self.assertEqual(result['runs_completed'],1)
        self.assertEqual([c['status'] for c in result['inventory']['cases']],['incomplete','not_run','not_run'])
        self.assertTrue(Path(result['coverage']).exists())

    def test_cli_starter_and_inventory(self):
        output=self.root/'starter.json'
        result=subprocess.run([sys.executable,str(ROOT/'tools/author.py'),'scenario-scaffold',str(self.doc.root),'--kind','entrance','--target','survey:shuttle','--output',str(output)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr);self.assertFalse(json.loads(result.stdout)['verified'])
        result=subprocess.run([sys.executable,str(ROOT/'tools/author.py'),'coverage',str(self.doc.root),'--suite',str(self.path),'--output',str(self.root/'inventory.json')],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertTrue(all(c['status']=='not_run' for c in read_json(self.root/'inventory.json')['cases']))


if __name__=='__main__':unittest.main()
