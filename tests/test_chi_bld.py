"""BLD sources, native compilation, safe editing and source locations."""
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
from chi_bld import data,find,put,update,enable,compiled,decode,schema,remove,insert


class BldCodecTests(unittest.TestCase):
    def test_synthetic_unreachable_bytes_and_signed_operands(self):
        payload=bytes([0xf4,0,255,0xf1,0,1,0xff,0xaa,0xbb])
        raw=len(payload).to_bytes(2,'little')+bytes(((b^233)-41)&255 for b in payload)
        p=decode(raw,'TRAINING');self.assertEqual(p['nodes'][0]['value'],255)
        self.assertEqual(p['nodes'][-1]['op'],'data');self.assertEqual(p['nodes'][-1]['bytes'],'aabb')
    def test_truncated_unknown_and_branch_into_operand(self):
        for payload in (b'\xf4',b'\xe7\0\0\0\0',b'\xf8\x01\x00\xff'):
            raw=len(payload).to_bytes(2,'little')+bytes(((b^233)-41)&255 for b in payload)
            with self.assertRaises((EditorError,ValueError,IndexError)):decode(raw,'TRAINING')


@unittest.skipUnless((ROOT/'build/btp-chi-bld-tests').exists() and (ROOT/'Original DOS/BTECH.EXE').exists(),'Needs native build and local private originals')
class BldProjectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from chi_import import import_campaigns
        cls.temp=tempfile.TemporaryDirectory(prefix='chi-bld-test-',dir=ROOT/'work');cls.root=Path(cls.temp.name);cls.tool=ROOT/'build/btp-project'
        import_campaigns(ROOT/'Original DOS',cls.root/'base',validator=cls.tool)
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def setUp(self):
        folder=self.root/self.id().rsplit('.',1)[-1];shutil.copytree(self.root/'base/original',folder);self.doc=ProjectDocument(folder,self.tool)
    def test_all_programs_roundtrip_exact_and_schema(self):
        value=data(self.doc)
        try:import jsonschema
        except ImportError:jsonschema=None
        if jsonschema:jsonschema.validate(value,schema())
        self.assertEqual(len(value['programs']),26)
        for p in value['programs']:
            result=compiled(self.doc,p['id']);self.assertEqual(bytes.fromhex(result['encrypted']),self.doc.files()['chi/'+p['resource']])
            self.assertTrue(all(n['offset']==n['origin'] and n['length']==n['original_size'] for n in result['nodes']))
    def test_five_scoped_edits_affect_real_native_play_and_history(self):
        from chi_bld_evidence import story_setup,story_request
        from authoring_service import apply_batch
        story_setup(self.doc);before=self.doc.files();apply_batch(self.doc,story_request(self.doc));changed=self.doc.files()
        self.doc.undo();self.assertEqual({k:v for k,v in self.doc.files().items() if k!='AUTHORING.json'},before)
        self.doc.redo();self.assertEqual(self.doc.files(),changed)
        self.doc.save();reopened=ProjectDocument(self.doc.root,self.tool);self.assertEqual(reopened.files(),self.doc.files())
        r=subprocess.run([str(ROOT/'build/btp-chi-bld-tests'),'--story',str(self.doc.root),str(self.root/'story.btp')],capture_output=True,text=True,timeout=30)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        r=subprocess.run([str(ROOT/'build/btp-chi-bld-tests'),'--reject',str(self.root/'base/original'),str(self.root/'story.btp')],capture_output=True,text=True,timeout=30)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
    def test_bad_edits_rollback_and_diagnostics_identify_source_label(self):
        from authoring_contract import diagnostic
        p=data(self.doc)['programs'][0];node=next(n for n in p['nodes'] if n['op']=='if');before=self.doc.files()
        for changes in (dict(index=100),dict(target='edit:missing'),dict(op='call'),dict(unknown=0)):
            with self.assertRaises(EditorError) as caught:update(self.doc,p['id'],node['id'],changes)
            self.assertIn(node['id'],diagnostic(caught.exception)['field_path']);self.assertEqual(self.doc.files(),before)
        native=next(n for n in p['nodes'] if n['op']=='native')
        with self.assertRaises(EditorError):update(self.doc,p['id'],native['id'],dict(action=47))
        text=next(n for n in p['nodes'] if n['op']=='text')
        for bad in ('a'*4097,'bad\0text','bad\ntext','caf\u00e9'):
            with self.assertRaises(EditorError):update(self.doc,p['id'],text['id'],dict(text=bad))
    def test_preserved_bytes_origin_ranges_and_budgets(self):
        before=self.doc.files();value=data(self.doc)
        for edit in (lambda p:p['nodes'].pop(),lambda p:p['nodes'][-1].update(bytes='ffff'),lambda p:p['nodes'][0].update(original_size=1),
                     lambda p:p.update(baseline_sha256='0'*64),lambda p:p['nodes'][0].update(id=p['nodes'][1]['id']),
                     lambda p:p['nodes'].__setitem__(slice(0,0),[dict(id='edit:loop',op='jump',target='edit:loop')])):
            candidate=copy.deepcopy(value);edit(candidate['programs'][0])
            with self.assertRaises(EditorError):put(self.doc,candidate)
            self.assertEqual(self.doc.files(),before)
        for p in value['programs']:
            for n in p['nodes']:
                if n['op']=='text':n['text']='a'*1000
        with self.assertRaises(EditorError):put(self.doc,value)
    def test_menu_selector_count_and_inserted_instruction_removal(self):
        p=data(self.doc)['programs'][0];menu=next(n for n in p['nodes'] if n['op']=='menu')
        with self.assertRaises(EditorError):update(self.doc,p['id'],menu['id'],dict(targets=menu['targets'][:-1]))
        with self.assertRaises(EditorError):remove(self.doc,p['id'],menu['id'])
        before=self.doc.files();insert(self.doc,p['id'],p['nodes'][0]['id'],dict(id='edit:new',op='set',index=99,value=0))
        remove(self.doc,p['id'],'edit:new');self.assertEqual(self.doc.files(),before)
    def test_source_modules_build_and_error_mapping(self):
        from campaign_source import convert,build
        folder=self.root/'source';convert(self.doc,folder);source=ProjectDocument(folder,self.tool)
        self.assertEqual(data(self.doc),data(source));self.assertIn('chi_scripts',source.source.index['sections'])
        p=data(source)['programs'][1];text=next(n for n in p['nodes'] if n['op']=='text')
        update(source,p['id'],text['id'],dict(text=text['text']+' '));source.save();build(source,self.root/'built')
        self.assertEqual(data(source),data(ProjectDocument(self.root/'built',self.tool)))
        with self.assertRaises(EditorError) as error:update(source,p['id'],text['id'],dict(text='bad\n'))
        self.assertIn('chi_scripts/programs/',str(error.exception))
    def test_old_project_enable_undo_and_untouched_raw_resources(self):
        manifest=copy.deepcopy(self.doc.manifest);manifest.pop('chi_scripts');(self.doc.root/'project.json').write_bytes(encoded(manifest))
        old=ProjectDocument(self.doc.root,self.tool);raw={k:v for k,v in old.files().items() if k.startswith('chi/')};enable(old)
        old.undo();self.assertNotIn('chi_scripts',old.manifest);old.redo();old.validate()
        self.assertEqual(raw,{k:v for k,v in old.files().items() if k.startswith('chi/')})
    def test_protection_and_problem_navigation(self):
        from authoring_protection import value_at
        from editor_problems import target
        p=data(self.doc)['programs'][0];node=next(n for n in p['nodes'] if n['op']=='text')
        self.assertEqual(value_at(self.doc,'chi.programs/'+p['id']),p)
        location=target(self.doc,dict(message='bad BLD',field_path='$.programs['+p['id']+'].nodes['+node['id']+'].text'))
        self.assertEqual(location['program'],p['id']);self.assertEqual(location['label'],node['id'])


if __name__=='__main__':unittest.main()
