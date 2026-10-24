"""Native traces must observe real branches without changing play or saves."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from editor_model import ProjectDocument,EditorError,encoded
from chi_import import import_campaigns
from chi_coverage import coverage


@unittest.skipUnless((ROOT/'build/btech-headless').is_file() and (ROOT/'Original DOS/BTECH.EXE').is_file(),'Needs native player and local original data')
class ChiCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary=tempfile.TemporaryDirectory(prefix='chi-coverage-',dir=ROOT/'work');cls.root=Path(cls.temporary.name)
        cls.validator=ROOT/'build/btp-project';cls.player=ROOT/'build/btech-headless'
        import_campaigns(ROOT/'Original DOS',cls.root/'pair',validator=cls.validator)
    @classmethod
    def tearDownClass(cls):cls.temporary.cleanup()
    def setUp(self):
        self.folder=self.root/self.id().rsplit('.',1)[-1];self.folder.mkdir()
    def play(self,project,actions,tag,trace=True,load=None):
        args=[str(self.player),'--project',str(project),'--replay',str(actions),'--save',str(self.folder/(tag+'.btp')),'--frame',str(self.folder/(tag+'.ppm'))]
        if trace:args+=['--bld-trace',str(self.folder/(tag+'.jsonl'))]
        if load:args+=['--load',str(load)]
        run=subprocess.run(args,cwd=ROOT,capture_output=True,text=True,timeout=30)
        self.assertEqual(run.returncode,0,run.stderr);return json.loads(run.stdout)
    def test_both_profiles_have_exact_uninstrumented_state_saves_and_pixels(self):
        for edition in ('original','updated'):
            project=self.root/'pair'/edition;fixture=ROOT/'tests/fixtures/reference-bank.actions'
            before=self.play(project,fixture,edition+'-plain',False);after=self.play(project,fixture,edition)
            self.assertEqual(before,after)
            for suffix in ('.btp','.ppm'):self.assertEqual((self.folder/(edition+suffix)).read_bytes(),(self.folder/(edition+'-plain'+suffix)).read_bytes())
            report=coverage(ProjectDocument(project,self.validator),[self.folder/(edition+'.jsonl')])
            self.assertEqual(len(report['programs']),26);self.assertGreater(report['observations'],50);self.assertEqual(report['faults'],[])
            self.assertGreater(sum(p['branches']['observed'] for p in report['programs']),0)
            actions=[n['native'] for p in report['programs'] for n in p['nodes'] if n.get('native')]
            self.assertTrue(any(n['entered'] and n['returned'] for n in actions))
            self.assertTrue(any(p['instructions']['observed']==0 for p in report['programs']))
    def test_bank_amount_continuation_emits_only_resumed_execution(self):
        project=self.root/'pair/original';actions=(ROOT/'tests/fixtures/reference-bank.actions').read_text().splitlines()
        fixture=json.loads((ROOT/'tests/fixtures/reference-bank.json').read_text())
        count=next(c['tick'] for c in fixture['checkpoints'] if c['label']=='bank-invest-amount')
        prefix=self.folder/'prefix.actions';suffix=self.folder/'suffix.actions'
        prefix.write_text('\n'.join(actions[:count])+'\n');suffix.write_text('\n'.join(actions[count:])+'\n')
        self.play(project,prefix,'prefix');self.play(project,suffix,'suffix',load=self.folder/'prefix.btp')
        self.play(project,ROOT/'tests/fixtures/reference-bank.actions','full')
        self.assertEqual((self.folder/'suffix.btp').read_bytes(),(self.folder/'full.btp').read_bytes())
        def rows(tag):return [json.loads(line) for line in (self.folder/(tag+'.jsonl')).read_text().splitlines()]
        full=rows('full');start=rows('prefix');end=rows('suffix')
        self.assertTrue(end[0]['continuation']);self.assertEqual(full[1:],start[1:]+end[1:])
        report=coverage(ProjectDocument(project,self.validator),[self.folder/'suffix.jsonl'])
        self.assertTrue(report['traces'][0]['continuation'])
    def test_old_import_resolves_original_offsets_without_upgrading(self):
        project=self.folder/'old';shutil.copytree(self.root/'pair/original',project)
        manifest=json.loads((project/'project.json').read_bytes());manifest.pop('chi_scripts');(project/'project.json').write_bytes(encoded(manifest))
        doc=ProjectDocument(project,self.validator);before=doc.files()
        self.play(project,ROOT/'tests/fixtures/reference-bank.actions','old')
        report=coverage(doc,[self.folder/'old.jsonl']);self.assertGreater(report['observations'],0)
        self.assertEqual(doc.files(),before);self.assertFalse(doc.dirty)
        from editor_problems import target
        node=next(n for p in report['programs'] for n in p['nodes'] if n['executions'])
        location=target(doc,dict(field_path=node['field_path'],message='Observed native instruction'))
        self.assertEqual(location['collection'],'native_scripts');self.assertEqual(location['label'],node['id'])
    def test_stale_trace_is_rejected_for_changed_content(self):
        project=self.folder/'edited';shutil.copytree(self.root/'pair/original',project)
        self.play(project,ROOT/'tests/fixtures/reference-bank.actions','old')
        doc=ProjectDocument(project,self.validator)
        from chi_bld import data,put
        value=data(doc);value['programs'][0]['nodes'][0]['note']='An explicitly different source revision';put(doc,value)
        with self.assertRaisesRegex(EditorError,'different content revision'):coverage(doc,[self.folder/'old.jsonl'])
    def test_invalid_source_labels_and_headers_are_rejected(self):
        project=self.root/'pair/original';self.play(project,ROOT/'tests/fixtures/reference-bank.actions','good')
        rows=[json.loads(line) for line in (self.folder/'good.jsonl').read_text().splitlines()]
        for value in ([],dict(format='not-a-trace'),rows[0]):
            damaged=copy.deepcopy(rows);damaged[0]=value
            if value==rows[0]:damaged[1]['node']='fake:instruction'
            path=self.folder/'bad.jsonl';path.write_text(''.join(json.dumps(row)+'\n' for row in damaged))
            with self.assertRaises(EditorError):coverage(ProjectDocument(project,self.validator),[path])

    def test_undeclared_branch_is_retained_as_unresolved_evidence(self):
        project=self.root/'pair/original';self.play(project,ROOT/'tests/fixtures/reference-bank.actions','branch')
        path=self.folder/'branch.jsonl';rows=[json.loads(line) for line in path.read_text().splitlines()]
        branch=next(row for row in rows if row.get('kind')=='branch');branch['detail']=255
        path.write_text(''.join(json.dumps(row)+'\n' for row in rows))
        report=coverage(ProjectDocument(project,self.validator),[path])
        self.assertEqual(report['unresolved_observations']['undeclared-branch'],1)
        self.assertEqual(len(report['unmapped_branches']),1)
        retained=report['unmapped_branches'][0]
        self.assertEqual((retained['node'],retained['choice'],retained['destination']),(branch['node'],255,branch['to']))


if __name__=='__main__':unittest.main()
