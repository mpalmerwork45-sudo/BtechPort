"""Round trips preserve edited native content without exporting original bases."""
import copy,json,shutil,subprocess,sys,tempfile,unittest
from unittest.mock import patch as mock_patch
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from editor_model import ProjectDocument,EditorError,encoded
from chi_recipe import diff,patch,export_recipe,build_recipe,runtime_files,fingerprint,check_recipe,base_index,references_only,resolve_references

class RecipePatchTests(unittest.TestCase):
    def test_insert_clone_reorder_and_text_splices(self):
        original=dict(nodes=[dict(id='test:a',op='text',text='A long original sentence which must remain a baseline reference.',origin=0,original_size=63),dict(id='test:b',op='end')])
        edited=copy.deepcopy(original);edited['nodes'].insert(1,dict(id='test:clone',op='text',text=original['nodes'][0]['text']))
        edited['nodes'][0]['text']=edited['nodes'][0]['text'].replace('sentence','description')
        changes=diff(original,edited);self.assertEqual(patch(original,changes),edited)
        self.assertNotIn(original['nodes'][0]['text'],json.dumps(changes));self.assertTrue(any(c['op']=='copy' for c in changes))
        bad=copy.deepcopy(changes);bad[0]['before']='0'*64
        with self.assertRaises(EditorError):patch(original,bad)

    def test_modified_copied_text_uses_spans_and_checks_bounds(self):
        original='Synthetic reference speech with enough characters to exercise copied spans safely.'
        files={'speech.json':encoded({'text':original})};index=base_index(files)
        for edited in (original+'!', 'Prefix: '+original, original[:40]+'EDIT'+original[40:], original[7:-3]):
            protected=references_only(edited,index)
            self.assertIsInstance(protected,dict)
            self.assertEqual(resolve_references(protected,files),edited)
            self.assertNotIn(original,json.dumps(protected))
        malformed={'$chi_text':[dict(source=dict(file='speech.json',path=['text']),at=0,length=len(original)+1)]}
        with self.assertRaisesRegex(EditorError,'out of range'):resolve_references(malformed,files)

    def test_original_spans_are_protected_before_positional_string_diff(self):
        original='A distinct synthetic reference speech used to test insertion ahead of unrelated native overrides.'
        files={'speech.json':encoded({'text':original})};index=base_index(files)
        old=[{'index':100,'text':'An unrelated old record with a different message.'}]
        new=[{'index':55,'text':original+'!'},*old]
        changes=diff(old,new,text_index=index)
        protected=references_only(changes,index)
        self.assertNotIn(original,json.dumps(protected))
        self.assertEqual(patch(old,resolve_references(protected,files)),new)

@unittest.skipUnless((ROOT/'build/btp-project').exists() and (ROOT/'Original DOS/BTECH.EXE').exists(),'Needs local originals/native validator')
class ChiRecipeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from chi_import import import_campaigns
        cls.temp=tempfile.TemporaryDirectory(prefix='chi-recipe-test-',dir=ROOT/'work');cls.root=Path(cls.temp.name);cls.tool=ROOT/'build/btp-project'
        import_campaigns(ROOT/'Original DOS',cls.root/'pair',validator=cls.tool)
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def roundtrip(self,edition,edit,tag):
        doc=ProjectDocument(self.root/'pair'/edition,self.tool);before=doc.files();edit(doc)
        recipe=self.root/(tag+'.json');export_recipe(doc,ROOT/'Original DOS',recipe)
        value=json.loads(recipe.read_bytes());check_recipe(value)
        from release_guard import check_payload
        check_payload(recipe.name,recipe.read_bytes())
        result=self.root/(tag+' rebuilt é 漢字');build_recipe(value,ROOT/'Original DOS',result,self.tool)
        rebuilt=ProjectDocument(result,self.tool);self.assertEqual(fingerprint(runtime_files(doc)),fingerprint(runtime_files(rebuilt)))
        self.assertTrue(doc.dirty);self.assertEqual(ProjectDocument(doc.root,self.tool).files(),before)
        self.assertEqual(doc.validate().split('SHA-256 ')[-1],rebuilt.validate().split('SHA-256 ')[-1])
        return doc,value,result
    def test_both_editions_quest_service_map_and_dialogue(self):
        from chi_bridge import example
        from chi_services import update
        from chi_bld import data,put
        def edit(d):
            example(d);update(d,'repair.armour',9)
            source=data(d);node=next(n for n in source['programs'][3]['nodes'] if n['op']=='text');node['text']=node['text'].replace('e','E',1);put(d,source)
        for edition in ('original','updated'):self.roundtrip(edition,edit,'quest-'+edition)
    def test_original_sprite_and_tile_edits_reconstruct_from_refs(self):
        from chi_resources import detach
        from chi_spatial import enable
        def edit(d):
            enable(d);detach(d,'sprite','MECHSHAP.CMP',0,2)
            art=copy.deepcopy(d.art);image=art['images'][-1];image['frames'][0][0]='ffffffff'+image['frames'][0][0][8:];d.replace_art(art)
        self.roundtrip('original',edit,'sprite')

    def test_cloned_edited_bld_and_native_dialogue_keep_original_text_local(self):
        from chi_bld import data,insert
        from chi_editor import native_dialogue,set_dialogue
        copied=[]
        def edit(d):
            program=next(p for p in data(d)['programs'] if any(n['op']=='text' and len(n['text'])>200 for n in p['nodes']))
            original=next(n for n in program['nodes'] if n['op']=='text' and len(n['text'])>200)
            cloned=copy.deepcopy(original);cloned.pop('origin',None);cloned.pop('original_size',None)
            cloned['id']='test:modified-clone';cloned['text']+='!';copied.append(original['text'])
            insert(d,program['id'],original['id'],cloned)
            for i in (55,373):
                text=native_dialogue(d)[i];copied.append(text);set_dialogue(d,i,text+'!')
        _,recipe,_=self.roundtrip('original',edit,'modified-original-dialogue')
        payload=json.dumps(recipe)
        for text in copied:
            # Check meaningful retained spans, including text that would have
            # been fragmented by a diff against an unrelated shifted record.
            for at in range(0,len(text)-31,16):self.assertNotIn(json.dumps(text[at:at+32])[1:-1],payload)
        self.assertIn('$chi_text',payload)
        self.assertIn('chi/talk-data.bin',payload)

    def test_recipe_outputs_preserve_fixed_references_with_another_source(self):
        doc=ProjectDocument(self.root/'pair/original',self.tool)
        path=self.root/'path-guard.recipe.json';export_recipe(doc,ROOT/'Original DOS',path)
        recipe=json.loads(path.read_bytes());fake=self.root/'fake-checkout';fake.mkdir()
        with mock_patch('chi_import.ROOT',fake):
            for reference in ('Original DOS','UnBattletech'):
                protected=fake/reference;protected.mkdir();target=protected/'must-not-exist'
                with self.assertRaisesRegex(EditorError,'outside original/reference'):build_recipe(recipe,ROOT/'Original DOS',target,self.tool)
                with self.assertRaisesRegex(EditorError,'outside original/reference'):export_recipe(doc,ROOT/'Original DOS',target)
                self.assertEqual(list(protected.iterdir()),[])
    def test_rejects_raw_resource_changes_and_preserves_existing_outputs(self):
        doc=ProjectDocument(self.root/'pair/original',self.tool);recipe=self.root/'keep.json';recipe.write_text('preserved')
        with self.assertRaisesRegex(EditorError,'exists'):export_recipe(doc,ROOT/'Original DOS',recipe)
        self.assertEqual(recipe.read_text(),'preserved')
        destination=self.root/'occupied';destination.mkdir();(destination/'keep').write_text('keep')
        new=self.root/'base.json';export_recipe(doc,ROOT/'Original DOS',new);value=json.loads(new.read_bytes())
        with self.assertRaises(EditorError):build_recipe(value,ROOT/'Original DOS',destination,self.tool)
        self.assertEqual((destination/'keep').read_text(),'keep')
        bad=copy.deepcopy(value);bad['base_digest']='0'*64
        with self.assertRaisesRegex(EditorError,'baseline'):build_recipe(bad,ROOT/'Original DOS',self.root/'bad',self.tool)
        self.assertFalse((self.root/'bad').exists());self.assertFalse(list(self.root.glob('.chi-recipe-*')))
        # A structurally valid raw terrain edit must go through a source-aware
        # editor before it can become an asset-free reconstruction recipe.
        raw=self.root/'raw-resource';doc.export(raw)
        path=raw/'chi/MAP2.MTP';data=bytearray(path.read_bytes());data[-1]^=1;path.write_bytes(data)
        with self.assertRaisesRegex(EditorError,'binary resource'):
            export_recipe(ProjectDocument(raw,self.tool),ROOT/'Original DOS',self.root/'raw.json')
        self.assertFalse((self.root/'raw.json').exists())
    def test_cancel_never_publishes_a_partial_recipe(self):
        import threading
        from chi_import import ImportCancelled
        doc=ProjectDocument(self.root/'pair/original',self.tool);cancel=threading.Event();cancel.set()
        with self.assertRaises(ImportCancelled):export_recipe(doc,ROOT/'Original DOS',self.root/'cancel.json',cancel)
        self.assertFalse((self.root/'cancel.json').exists());self.assertFalse(list(self.root.glob('.chi-recipe-*')))
    def test_traversal_unknown_operation_and_extraneous_payload_rejected(self):
        doc=ProjectDocument(self.root/'pair/original',self.tool);p=self.root/'safe.json';export_recipe(doc,ROOT/'Original DOS',p);value=json.loads(p.read_bytes())
        for row in (dict(file='../escape.json',changes=[dict(op='set',path=[],before='0'*64,value={})]),
                    dict(file='chi/BTECH.EXE',changes=[dict(op='set',path=[],before='0'*64,value='binary')]),
                    dict(file='campaign.json',changes=[dict(op='order',path=[],ids=[],value='hidden payload')])):
            bad=copy.deepcopy(value);bad['files']=[row]
            with self.assertRaises(EditorError):check_recipe(bad)
        self.assertFalse((self.root.parent/'escape.json').exists())

if __name__=='__main__':unittest.main()
