"""Modules must survive real editor transactions and native package/save loads."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from editor_model import ProjectDocument,EditorError,encoded
from campaign_source import CampaignSource,SourceError,convert,build,canonical
from authoring_contract import diagnostic
from authoring_service import apply_batch,revision
TOOL=Path(os.environ.get('BTP_PROJECT_TOOL',ROOT/'build/btp-project'))


class CampaignSources(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='btp-source-test-');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.legacy=ProjectDocument(ROOT/'examples/beacon-demo',TOOL)
        self.doc=convert(self.legacy,self.root/'source')

    def reopen(self):return ProjectDocument(self.doc.root,TOOL)

    def request(self):
        return dict(api_version=1,request_id='source-edit',project_id=self.doc.manifest['package_id'],
            expected_revision=revision(self.doc),label='Revise source briefing',scope=['adventure.events/beacon:welcome'],
            operations=[dict(op='object.patch',collection='events',id='beacon:welcome',changes={'text':'A revised briefing.'})])

    def test_conversion_builds_and_dependencies_are_deterministic(self):
        self.assertEqual(self.legacy.content,self.doc.content)
        self.assertEqual(self.legacy.adventure,self.doc.adventure)
        self.assertFalse((self.doc.root/'project.json').exists())
        before=self.doc.source.disk.copy()
        a=build(self.doc,self.root/'build a');b=build(self.doc,self.root/'build b')
        self.assertEqual(a['fingerprint'],b['fingerprint']);self.assertEqual(a['files'],b['files'])
        self.assertEqual(before,self.reopen().source.disk)
        self.assertTrue((self.root/'build a/contract.lua').is_file())
        self.assertEqual((self.root/'build a/CREDITS.md').read_bytes(),(self.legacy.root/'CREDITS.md').read_bytes())
        compiled=ProjectDocument(self.root/'build a',TOOL)
        self.assertIsNone(compiled.source);self.assertEqual(compiled.adventure,self.doc.adventure)
        with self.assertRaises(EditorError):build(self.doc,self.root/'build a')
        with self.assertRaises(EditorError):build(self.doc,self.doc.root/'nested-output')

    def test_commands_text_undo_save_reopen_and_idempotent_retry(self):
        before=revision(self.doc);request=self.request();preview=apply_batch(self.doc,request,dry_run=True)
        self.assertEqual(before,revision(self.doc))
        apply_batch(self.doc,request);self.assertEqual(preview['result_revision'],revision(self.doc))
        self.doc.undo();self.assertEqual(before,revision(self.doc));self.doc.redo();after=revision(self.doc)
        self.doc.save();reopened=self.reopen();self.assertEqual(after,revision(reopened))
        self.assertEqual(apply_batch(reopened,request)['status'],'already_applied')
        texts=json.loads((self.doc.root/'text/dialogue.json').read_bytes())
        self.assertEqual(texts['beacon:welcome.text'],'A revised briefing.')
        owner=next(v for v in self.doc.source.locations if v['id']=='beacon:welcome')
        self.assertEqual(json.loads((self.doc.root/owner['file']).read_bytes())[0]['text'],{'$text':'beacon:welcome.text'})

    def test_reordering_new_and_deleted_records_roundtrip(self):
        a=copy.deepcopy(self.doc.adventure)
        a['events'].append(dict(id='beacon:new-end',op='end'));a['events'].reverse()
        self.doc.replace_adventure(a);self.doc.save();self.assertEqual(self.reopen().adventure,a)
        a['events']=[v for v in a['events'] if v['id']!='beacon:new-end']
        self.doc.replace_adventure(a);self.doc.save();self.assertEqual(self.reopen().adventure,a)
        self.assertTrue(self.doc.source.index['order']['adventure.events'])

    def test_external_source_edits_and_metadata_protect_revision(self):
        before=revision(self.doc);name='text/dialogue.json';path=self.doc.root/name
        values=json.loads(path.read_bytes());values['beacon:welcome.text']='Outside edit.';path.write_bytes(encoded(values))
        with self.assertRaisesRegex(EditorError,'outside this editor'):self.doc.save()
        self.assertNotEqual(before,revision(self.reopen()))

    def test_source_diagnostics_name_event_module_and_field(self):
        a=copy.deepcopy(self.doc.adventure);event=next(v for v in a['events'] if v['id']=='beacon:welcome');event['next']='missing:event'
        self.doc.replace_adventure(a)
        with self.assertRaises(SourceError) as caught:self.doc.validate()
        result=diagnostic(caught.exception)
        self.assertIn('adventure/events/beacon-welcome',result['source']['file'])
        self.assertEqual(result['source']['field_path'],'$[0].next')
        self.assertEqual(result['field_path'],'$.events[beacon:welcome].next')

    def test_source_notes_and_formatting_do_not_change_save_identity(self):
        first=build(self.doc,self.root/'before')
        index=self.doc.source.index.copy();index['notes']={'brief':'Two planets and a courier.'}
        (self.doc.root/'SOURCE.json').write_text(json.dumps(index,separators=(',',':')))
        path=self.doc.root/'source/adventure.json';path.write_text(json.dumps(json.loads(path.read_bytes()),sort_keys=True))
        reopened=self.reopen();second=build(reopened,self.root/'after')
        self.assertEqual(first['fingerprint'],second['fingerprint'])
        self.assertNotEqual(revision(self.doc),revision(reopened))
        player=ROOT/'build/btech-headless';save=self.root/'campaign.btp'
        def play(package,*args,ok=True):
            p=subprocess.run([str(player),'--project',str(package),*map(str,args)],capture_output=True,text=True,timeout=20)
            self.assertEqual(p.returncode==0,ok,p.stderr);return p
        before=play(self.root/'before','--save',save)
        after=play(self.root/'after','--load',save)
        self.assertEqual(json.loads(before.stdout),json.loads(after.stdout))
        self.doc=reopened;apply_batch(self.doc,self.request(),save=True);build(self.doc,self.root/'changed')
        self.assertIn('exact saved content',play(self.root/'changed','--load',save,ok=False).stderr)

    def test_interrupted_multifile_save_rolls_back_all_source_and_receipts(self):
        before=self.doc.source.disk.copy();original=ProjectDocument.atomic_file;count=0
        def crash(path,data):
            nonlocal count
            count+=1
            if count==2:raise SystemExit('power loss')
            original(path,data)
        with patch.object(ProjectDocument,'atomic_file',side_effect=crash):
            with self.assertRaises(SystemExit):apply_batch(self.doc,self.request(),save=True)
        with self.assertRaisesRegex(EditorError,'Interrupted save'):ProjectDocument(self.doc.root,TOOL,recover=False)
        recovered=self.reopen();self.assertEqual(before,recovered.source.disk)
        self.assertEqual(recovered.adventure,self.legacy.adventure)

    def test_reject_bad_source_duplicate_id_path_missing_text_and_dual_truth(self):
        source=self.doc.source
        for change,expected in [('path','Unsafe'),('text','text reference'),('duplicate','Duplicate object'),('json','Duplicate field')]:
            with self.subTest(change=change):
                files=source.disk.copy();index=copy.deepcopy(source.index)
                if change=='path':index['sections']['content']='../escape.json';files['SOURCE.json']=encoded(index)
                if change=='text':files['text/dialogue.json']=encoded({})
                if change=='duplicate':
                    mod=index['modules'][0];items=json.loads(files[mod['file']]);files[mod['file']]=encoded(items+items)
                if change=='json':files['text/dialogue.json']=b'{"x":"a","x":"b"}'
                with self.assertRaisesRegex(EditorError,expected):CampaignSource(self.doc.root,files)
        (self.doc.root/'project.json').write_bytes(self.doc.files()['project.json'])
        with self.assertRaisesRegex(EditorError,'Both SOURCE'):self.reopen()

    def test_shared_text_conflicting_edits_are_refused(self):
        files=self.doc.source.disk.copy();index=self.doc.source.index
        mods=[m for m in index['modules'] if m['collection']=='events']
        owners=[]
        for mod in mods:
            values=json.loads(files[mod['file']])
            if values[0].get('op')=='say':
                values[0]['text']={'$text':'beacon:welcome.text'};files[mod['file']]=encoded(values);owners.append(values[0]['id'])
        source=CampaignSource(self.doc.root,files);package=source.package.copy();adventure=json.loads(package['adventure.json'])
        next(e for e in adventure['events'] if e['id']==owners[0])['text']='One diverges.'
        package['adventure.json']=canonical(adventure)
        with self.assertRaisesRegex(EditorError,'Shared text'):source.updated(package)

    def test_optional_new_graphics_section_and_metadata(self):
        from tile_editing import create_tile
        create_tile(self.doc,name='test tile')
        self.doc.save();reopened=self.reopen()
        self.assertEqual(self.doc.art,reopened.art)
        self.assertIn('art',reopened.source.index['sections'])
        expected=self.doc.art
        self.doc.undo();self.doc.save();self.assertNotIn('graphics',self.reopen().manifest)
        self.doc.redo();self.doc.save();self.assertEqual(self.reopen().art,expected)

    def test_cli_source_inspection_build_and_machine_diagnostic(self):
        def cli(*args,ok=True):
            p=subprocess.run([sys.executable,str(ROOT/'tools/author.py'),*map(str,args)],capture_output=True,text=True,timeout=20)
            self.assertEqual(p.returncode==0,ok,p.stdout+p.stderr);return json.loads(p.stdout)
        self.assertEqual(cli('inspect',self.doc.root)['data']['authoring']['mode'],'source')
        item=cli('source','locations',self.doc.root,'--id','beacon:welcome')['items'][0]
        built=cli('source','build',self.doc.root,'--output',self.root/'cli package');self.assertEqual(built['status'],'built')
        path=self.doc.root/item['file'];values=json.loads(path.read_bytes());values[0]['next']='missing:event';path.write_bytes(encoded(values))
        error=cli('validate',self.doc.root,ok=False)['diagnostics'][0]
        self.assertEqual(error['source']['file'],item['file']);self.assertEqual(error['source']['field_path'],'$[0].next')

    def test_source_conversion_keeps_legacy_saves_separate(self):
        player=ROOT/'build/btech-headless';save=self.root/'legacy.btp'
        subprocess.run([str(player),'--project',str(self.legacy.root),'--save',str(save)],check=True,capture_output=True,timeout=20)
        original=save.read_bytes();build(self.doc,self.root/'converted')
        p=subprocess.run([str(player),'--project',str(self.root/'converted'),'--load',str(save)],capture_output=True,text=True,timeout=20)
        self.assertNotEqual(p.returncode,0);self.assertIn('exact saved content',p.stderr);self.assertEqual(save.read_bytes(),original)

    def test_regrouping_modules_and_declared_source_budgets(self):
        files=self.doc.source.disk.copy();index=copy.deepcopy(self.doc.source.index)
        selected=[m for m in index['modules'] if m['section']=='adventure' and m['collection']=='events']
        combined=[]
        for module in selected:combined.extend(json.loads(files[module['file']]))
        first=selected[0];position=index['modules'].index(first)
        index['modules']=[m for m in index['modules'] if m not in selected]
        index['modules'].insert(position,dict(first,file='missions/relay.json'))
        files['missions/relay.json']=encoded(combined);files['SOURCE.json']=encoded(index)
        source=CampaignSource(self.doc.root,files)
        self.assertEqual(source.package,self.doc.source.package)
        package=source.package.copy();a=json.loads(package['adventure.json'])
        next(e for e in a['events'] if e['id']=='beacon:welcome')['text']='Grouped mission text.'
        package['adventure.json']=canonical(a)
        self.assertEqual(CampaignSource(self.doc.root,source.updated(package)).package,package)
        with patch('campaign_source.MAX_FILES',1):
            with self.assertRaises(SourceError):CampaignSource(self.doc.root,files)
        with patch('campaign_source.MAX_BYTES',10):
            with self.assertRaisesRegex(SourceError,'exceeds'):CampaignSource(self.doc.root,files)

    def test_review_preserves_source_identity_and_checks_exact_candidate(self):
        import authoring_review as review
        before=revision(self.doc);folder=self.root/'review'
        result=review.prepare(self.doc,self.request(),folder,visuals=False)
        self.assertEqual(result['status'],'ready');self.assertEqual(revision(self.doc),before)
        retained=ProjectDocument(folder/'after',TOOL)
        self.assertIsNotNone(retained.source);self.assertEqual(revision(retained),result['result_revision'])
        checked=review.check_candidate(folder,TOOL,analyzer=ROOT/'build/btp-author-analyze')
        self.assertNotEqual(checked['status'],'failed')
        review.apply(self.doc,folder,save=True)
        self.assertEqual(revision(self.reopen()),result['result_revision'])

    def test_launcher_compiles_source_and_resumes_same_content_after_notes(self):
        from app_runtime import game_command
        player=ROOT/'build/btech-headless';state=self.root/'desktop'
        command=game_command('My project',{'player':str(player)},state,self.doc.root)
        package=Path(command[command.index('--project')+1]);self.assertNotEqual(package,self.doc.root)
        self.assertTrue((package/'project.json').exists());self.assertFalse((package/'SOURCE.json').exists())
        save=Path(command[command.index('--save-file')+1]);save=save.with_name('game-project-'+self.doc.manifest['package_id']+'.btp')
        p=subprocess.run(command+['--save',str(save)],capture_output=True,text=True,timeout=20);self.assertEqual(p.returncode,0,p.stderr)
        index=copy.deepcopy(self.doc.source.index);index['notes']={'brief':'A revised author brief.'}
        (self.doc.root/'SOURCE.json').write_bytes(encoded(index))
        resumed=game_command('My project',{'player':str(player)},state,self.doc.root,resume=True)
        self.assertEqual(Path(resumed[resumed.index('--project')+1]),package)
        q=subprocess.run(resumed,capture_output=True,text=True,timeout=20);self.assertEqual(q.returncode,0,q.stderr)
        self.assertEqual(json.loads(p.stdout),json.loads(q.stdout))


if __name__=='__main__':unittest.main()
