import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from editor_model import EditorError,ProjectDocument,encoded
from chi_import import import_campaigns,ImportCancelled,SOURCE_FILES
from chi_editor import set_dialogue,native_dialogue
from asset_provenance import check_files,public_files,reconstruct,export_public,derived_images


@unittest.skipUnless((ROOT/'build/btp-project').is_file() and (ROOT/'Original DOS/BTECH.EXE').is_file(),'Needs native build and local original data')
class ChiImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary=tempfile.TemporaryDirectory(prefix='chi-tests-',dir=ROOT/'work')
        cls.root=Path(cls.temporary.name);cls.tool=ROOT/'build/btp-project';cls.source=ROOT/'Original DOS'
        cls.result=import_campaigns(cls.source,cls.root/'both',validator=cls.tool)

    @classmethod
    def tearDownClass(cls):cls.temporary.cleanup()

    def document(self,edition='original'):
        return ProjectDocument(self.root/'both'/edition,self.tool)

    def copy_source(self,name):
        target=self.root/name;target.mkdir()
        for leaf in SOURCE_FILES:shutil.copyfile(self.source/leaf,target/leaf)
        return target

    def test_imported_profiles_own_resources_and_need_no_setup(self):
        from app_runtime import game_command
        for profile in ('original','updated'):
            doc=self.document(profile)
            self.assertEqual(len(list((doc.root/'chi').iterdir())),79)
            self.assertFalse(any(p.suffix.lower()=='.exe' or p.name.startswith('GAME') for p in (doc.root/'chi').iterdir()))
            command=game_command('My project',{'player':str(ROOT/'build/btech-headless')},self.root/'launcher',doc.root)
            self.assertNotIn('--data',command)
            result=subprocess.run(command,capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stderr)
        self.assertNotEqual(self.document().manifest['package_id'],self.document('updated').manifest['package_id'])
        updated=self.document('updated');content=copy.deepcopy(updated.content);content['mechs']=[]
        updated.replace(content);empty=self.root/'updated-empty';updated.export(empty)
        run=subprocess.run([str(ROOT/'build/btp-chi-import-tests'),'--settings-proof',str(empty),str(self.root/'empty-settings.btp')],capture_output=True,text=True,timeout=20)
        self.assertEqual(run.returncode,0,run.stderr)

    def test_reimport_gets_new_identity_without_changing_existing_project(self):
        from app_runtime import register_imported_projects,imported_projects
        before=self.document().files()
        result=import_campaigns(self.source,self.root/'reimport','original',self.tool)
        self.assertNotEqual(result['projects'][0]['package_id'],self.document().manifest['package_id'])
        self.assertEqual(self.document().files(),before)
        register_imported_projects(self.root/'registrations',self.result['projects'])
        register_imported_projects(self.root/'registrations',result['projects'])
        self.assertEqual(len(imported_projects(self.root/'registrations')),3)
        broken=self.root/'registrations/imported-projects.json';broken.write_text('{')
        with self.assertRaises(EditorError):register_imported_projects(self.root/'registrations',result['projects'])
        self.assertEqual(broken.read_text(),'{')

    def test_editor_start_preserves_native_intro_and_preview_is_explicit(self):
        for profile in ('original','updated'):
            doc=self.document(profile)
            command=doc.play_command({'player':str(ROOT/'build/btech-port')},self.root/'intro-preview'/profile)
            self.assertNotIn('--replay',command)
            self.assertNotIn('--play-here',command)
            here=doc.play_command({'player':str(ROOT/'build/btech-port')},self.root/'intro-preview'/profile,('chi:map-01',69,25))
            self.assertEqual(here[here.index('--play-here')+1:here.index('--play-here')+4],['chi:map-01','69','25'])
            self.assertNotIn('--replay',here)

    def test_occupied_source_symlink_and_bad_fingerprint(self):
        existing=self.root/'occupied';existing.mkdir();(existing/'keep').write_text('preserved')
        with self.assertRaises(EditorError):import_campaigns(self.source,existing,validator=self.tool)
        self.assertEqual((existing/'keep').read_text(),'preserved')
        if os.name!='nt':
            link=self.root/'source-link';link.symlink_to(self.source,target_is_directory=True)
            with self.assertRaises(EditorError):import_campaigns(link,self.root/'link-output',validator=self.tool)
        source=self.copy_source('wrong-version');(source/'MAP1.MTP').write_bytes(b'broken')
        with self.assertRaisesRegex(EditorError,'MAP1.MTP'):import_campaigns(source,self.root/'bad-output',validator=self.tool)
        self.assertFalse((self.root/'bad-output').exists())

    def test_cancel_after_first_profile_publishes_neither(self):
        cancel=threading.Event();target=self.root/'cancelled'
        def progress(message):
            if message=='Creating updated campaign':cancel.set()
        with self.assertRaises(ImportCancelled):import_campaigns(self.source,target,validator=self.tool,cancel=cancel,progress=progress)
        self.assertFalse(target.exists());self.assertFalse(list(self.root.glob('.chi-import-*')))

    def test_source_changes_and_destination_race_preserve_existing_work(self):
        source=self.copy_source('changing-source');target=self.root/'changed-output'
        def change(message):
            if message=='Rechecking original files before publication':(source/'WWOODBT.SIF').write_bytes(b'changed')
        with self.assertRaises(EditorError):import_campaigns(source,target,'original',self.tool,progress=change)
        self.assertFalse(target.exists())
        target=self.root/'raced-output'
        def race(message):
            if message=='Rechecking original files before publication':target.mkdir();(target/'keep').write_text('race winner')
        with self.assertRaises(EditorError):import_campaigns(self.source,target,'original',self.tool,progress=race)
        self.assertEqual((target/'keep').read_text(),'race winner')
        self.assertFalse(list(self.root.glob('.chi-import-*')))

    def test_text_edits_undo_reopen_build_and_native_pixels(self):
        from campaign_source import convert
        doc=self.document();original=doc.files();other=self.document('updated').files()
        self.assertEqual(len(native_dialogue(doc)),373)
        set_dialogue(doc,87,'Imported control prompt')
        self.assertTrue(doc.dirty);doc.undo();self.assertEqual(doc.files(),original)
        doc.redo();edited=self.root/'edited';doc.export(edited)
        run=subprocess.run([str(ROOT/'build/btp-chi-import-tests'),'--text-proof',str(doc.root),str(edited),str(self.root/'edited.ppm')],capture_output=True,text=True,timeout=20)
        self.assertEqual(run.returncode,0,run.stderr)
        source=convert(ProjectDocument(edited,self.tool),self.root/'source')
        set_dialogue(source,87,'Modular campaign prompt');source.save()
        reopened=ProjectDocument(source.root,self.tool);reopened.export(self.root/'built')
        self.assertEqual(json.loads(reopened.metadata['campaign.json'])['dialogue_overrides'][0]['text'],'Modular campaign prompt')
        self.assertEqual(self.document().files(),original);self.assertEqual(self.document('updated').files(),other)
        multiline='First line\rSecond line\x06colour\x0f'
        set_dialogue(doc,87,multiline);doc.export(self.root/'multiline')
        self.assertEqual(json.loads(ProjectDocument(self.root/'multiline',self.tool).metadata['campaign.json'])['dialogue_overrides'][0]['text'],multiline)
        run=subprocess.run([str(ROOT/'build/btp-chi-import-tests'),'--text-proof',str(doc.root),str(self.root/'multiline'),str(self.root/'multiline.ppm'),multiline.encode('ascii').hex()],capture_output=True,text=True,timeout=20)
        self.assertEqual(run.returncode,0,run.stderr)

    def test_invalid_text_and_unknown_fields_fail_without_consuming_edits(self):
        doc=self.document();before=doc.files()
        for index,text in [(373,'bad'),(0,'\x06bad'),(87,'x'*513),(87,'bad\nline'),(87,'snowman \u2603'),(87,'left\0right')]:
            with self.subTest(index=index,text=repr(text[:15])):
                with self.assertRaises(EditorError):set_dialogue(doc,index,text)
                self.assertEqual(doc.files(),before)
        candidate=doc.worker_copy();value=json.loads(candidate.metadata['campaign.json']);value['unused']=1
        candidate.metadata['campaign.json']=encoded(value)
        with self.assertRaises(EditorError):candidate.validate()
        candidate=doc.worker_copy();value=json.loads(candidate.metadata['campaign.json'])
        value['dialogue_overrides']=[dict(index=i,text='A'*512) for i in range(373)]
        candidate.metadata['campaign.json']=encoded(value)
        with self.assertRaisesRegex(EditorError,'budget'):candidate.validate()

    def test_resource_change_invalidates_save_even_with_provenance_removed(self):
        doc=self.document();target=self.root/'resource-change';doc.export(target)
        save=self.root/'exact-content.btp';player=ROOT/'build/btech-headless'
        run=subprocess.run([str(player),'--project',str(target),'--save',str(save)],capture_output=True,timeout=20)
        self.assertEqual(run.returncode,0,run.stderr)
        before=save.read_bytes();path=target/'chi/MAP2.MTP';raw=bytearray(path.read_bytes());raw[-1]=0 if raw[-1] else 1;path.write_bytes(raw)
        (target/'IMPORT.json').unlink()
        candidate=ProjectDocument(target,self.tool)
        with self.assertRaises(EditorError):check_files(candidate.files())
        rejected=subprocess.run([str(player),'--project',str(target),'--load',str(save)],capture_output=True,timeout=20)
        self.assertNotEqual(rejected.returncode,0);self.assertEqual(save.read_bytes(),before)

    def test_public_export_rejects_imports_caches_and_declared_unknown_text(self):
        with self.assertRaises(EditorError):export_public(self.document(),self.root/'unsafe-public')
        base=ProjectDocument(ROOT/'examples/beacon-demo',self.tool).files()
        self.assertTrue(check_files(base))
        for name,data in [('converted.bin',b'BTTAcopied'),('converted.json',encoded({'nested':[{'origin':'original-derived','text':'copied text'}]})),('unknown.json',encoded({'origin':'unknown','text':'unresolved'}))]:
            with self.subTest(name=name):
                with self.assertRaises(EditorError):check_files(dict(base,**{name:data}))

    def test_beacon_public_recipe_preserves_local_art_and_reconstructs_base(self):
        from editor_model import references,METADATA_FILES
        prefix='examples/battletech-demo/'
        owner={name:(ROOT/prefix/name).read_bytes() for name in ('EDITOR.json','adventure.json','graphics.json')}
        manifest=json.loads(subprocess.check_output(['git','show',':'+prefix+'project.json'],cwd=ROOT))
        fixture=self.root/'beacon-baseline';fixture.mkdir()
        tracked=subprocess.check_output(['git','ls-files'],cwd=ROOT,text=True).splitlines()
        for leaf in [*references(manifest),*METADATA_FILES]:
            if prefix+leaf not in tracked:continue
            path=fixture/leaf;path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(subprocess.check_output(['git','show',':'+prefix+leaf],cwd=ROOT))
        if not (fixture/'CHI-TILES.json').exists():(fixture/'CHI-TILES.json').write_bytes((ROOT/prefix/'CHI-TILES.json').read_bytes())
        doc=ProjectDocument(fixture,self.tool);before=doc.files()
        clean=public_files(before);self.assertTrue(check_files(clean));self.assertFalse(derived_images(clean))
        target=self.root/'public-beacon';export_public(doc,target)
        restored=self.root/'restored-beacon';reconstruct(ProjectDocument(target,self.tool),restored,self.source)
        rebuilt=ProjectDocument(restored,self.tool)
        self.assertTrue(derived_images(rebuilt.files()))
        from asset_provenance import local_project
        public=ProjectDocument(target,self.tool)
        cached=local_project(public,{'data':str(self.source)},self.root/'cache')
        again=local_project(public,{'data':str(self.source)},self.root/'cache')
        self.assertEqual(cached.root,again.root)
        self.assertTrue(derived_images(cached.files()))
        changed=copy.deepcopy(cached.art);changed['images'][0]['name']='Locally edited cache'
        cached.replace_art(changed);cached.save()
        with self.assertRaises(EditorError):local_project(public,{'data':str(self.source)},self.root/'cache')
        self.assertEqual(doc.files(),before)
        self.assertTrue(all((ROOT/prefix/name).read_bytes()==value for name,value in owner.items()))


if __name__=='__main__':unittest.main()
