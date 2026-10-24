"""Saved-game actions preserve progress, occupied slots and exact revisions."""
import copy,json,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from editor_model import create_project,ProjectDocument,EditorError
from save_catalogue import SaveCatalogue,retain_revision,inspect,revision_key
from app_runtime import project_slot_name,game_command


class SaveCatalogueTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='saved-games-');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.state=self.root/'state';self.tool=ROOT/'build/btp-project';self.player=ROOT/'build/btech-headless'
        self.doc=create_project(ROOT/'examples/beacon-demo',self.root/'Game é 漢字','save-browser','Save Browser',self.tool)
        self.paths=dict(player=str(self.player));self.model=SaveCatalogue(self.state,self.paths,document=self.doc,location='Editor',validator=self.tool)

    def save(self,slot=1,folder=None):
        folder=folder or self.model.directory();folder.mkdir(parents=True,exist_ok=True)
        path=folder/project_slot_name(self.doc,slot)
        subprocess.run([str(self.player),'--project',str(self.doc.root),'--save',str(path)],capture_output=True,check=True,timeout=20)
        return path

    def edit(self):
        value=copy.deepcopy(self.doc.adventure);value['start']['credits']+=123;self.doc.replace_adventure(value);self.doc.save()

    def test_six_slots_dates_and_native_continue(self):
        for slot in range(1,7):self.save(slot)
        rows=self.model.scan();self.assertEqual(len(rows),6);self.assertEqual([r.slot for r in rows],list(range(1,7)))
        self.assertTrue(all(r.mtime and r.current and r.status=='Current revision' for r in rows))
        original=rows[2].path.read_bytes();command,state=self.model.resume(rows[2])
        result=json.loads(subprocess.check_output(command,text=True));self.assertEqual(result,state)
        self.assertEqual(rows[2].path.read_bytes(),original)
        self.assertTrue(list((self.state/'save-backups').glob('*/*/*.btp')))

    def test_older_revision_resumes_after_working_project_changes(self):
        source=self.save();before=source.read_bytes();root=retain_revision(self.doc,self.state);self.edit()
        rows=self.model.scan();old=next(r for r in rows if r.path==source)
        self.assertFalse(old.current);self.assertEqual(old.project,root)
        command,state=self.model.resume(old);self.assertEqual(state['credits']+123,self.doc.adventure['start']['credits'])
        self.assertEqual(json.loads(subprocess.check_output(command,text=True))['credits'],state['credits'])
        self.assertEqual(source.read_bytes(),before)

    def test_recover_uses_empty_slots_and_never_replaces_progress(self):
        source=self.save();row=next(r for r in self.model.scan() if r.path==source);before=source.read_bytes()
        with self.assertRaises(EditorError):self.model.recover(row,1)
        target=self.model.recover(row,6);self.assertEqual(target.read_bytes(),before);self.assertEqual(source.read_bytes(),before)
        with self.assertRaises(EditorError):self.model.recover(row,6)
        self.assertEqual(target.read_bytes(),before)

    def test_corrupt_and_foreign_saves_cannot_continue(self):
        source=self.save();data=bytearray(source.read_bytes());data[-1]^=1;source.write_bytes(data)
        row=next(r for r in self.model.scan() if r.path==source);self.assertIn('Damaged',row.error)
        with self.assertRaises(EditorError):self.model.resume(row)
        with self.assertRaises(EditorError):self.model.recover(row,2)
        self.assertEqual(source.read_bytes(),data)

    def test_normal_original_and_updated_six_slots_stay_separate(self):
        from app_runtime import default_settings
        if not (ROOT/'Original DOS/BTECH.EXE').exists():self.skipTest('Requires local originals')
        paths=default_settings();paths['player']=str(self.player)
        for choice in ('Original','Updated'):
            model=SaveCatalogue(self.state,paths,choice,validator=self.tool);model.directory().mkdir(parents=True)
            for slot in range(1,7):
                command=[str(self.player),'--edition',choice.lower()]
                for key in ('data','dialogue-data','combat-data','world-data'):command+=['--'+key,paths[key]]
                subprocess.run([*command,'--save',str(model.directory()/model.leaf(slot))],check=True,capture_output=True,timeout=20)
            rows=model.scan();self.assertEqual(len(rows),6);self.assertTrue(all(not r.error for r in rows))
            command,state=model.resume(rows[4]);self.assertEqual(json.loads(subprocess.check_output(command,text=True)),state)
        original=SaveCatalogue(self.state,paths,'Original',validator=self.tool)
        foreign=self.state/'games/updated/game-updated.btp';target=original.directory()/original.leaf(4);target.write_bytes(foreign.read_bytes())
        row=next(r for r in original.scan() if r.slot==4 and r.location=='Launcher')
        self.assertIn('another edition',row.error)
        with self.assertRaises(EditorError):original.resume(row)

    def test_retained_editor_runs_and_missing_revision_are_visible(self):
        run=self.state/'play-snapshots/run-retained';self.doc.export(run/'game')
        source=self.save(folder=run/'play'/self.doc.manifest['package_id']/revision_key(self.doc)[:20]);self.edit()
        row=next(r for r in self.model.scan() if r.path==source);self.assertEqual(row.location,'Earlier editor run');self.assertEqual(row.project,run/'game')
        shutil.rmtree(run/'game');row=next(r for r in self.model.scan() if r.path==source)
        self.assertIsNone(row.project)
        with self.assertRaises(EditorError):self.model.resume(row)

    def test_locate_requires_the_selected_saves_exact_revision(self):
        source=self.save();row=next(r for r in self.model.scan() if r.path==source)
        previous=self.root/'old-copy';self.doc.export(previous);self.edit()
        with self.assertRaises(EditorError):self.model.locate(self.doc.root,row.signature)
        target=self.model.locate(previous,row.signature);self.assertTrue(target.is_dir())
        old=next(r for r in self.model.scan() if r.path==source);self.assertEqual(old.project,target)

    def test_draft_changes_get_their_own_save_directory(self):
        before=self.model.directory();value=copy.deepcopy(self.doc.adventure);value['start']['credits']+=1;self.doc.replace_adventure(value)
        self.assertNotEqual(self.model.directory(),before)
        retained=retain_revision(self.doc,self.state);self.assertEqual(ProjectDocument(retained,self.tool).adventure['start']['credits'],value['start']['credits'])

    def test_launcher_keeps_a_playable_revision_before_edits(self):
        command=game_command('My project',self.paths,self.state,self.doc.root)
        retained=Path(command[command.index('--project')+1]);self.assertTrue(retained.is_relative_to(self.state/'save-revisions'))
        self.edit();self.assertNotEqual(ProjectDocument(retained,self.tool).adventure['start']['credits'],self.doc.adventure['start']['credits'])

    def test_modified_retained_revision_is_not_silently_replaced(self):
        source=self.save();before=source.read_bytes();root=retain_revision(self.doc,self.state)
        retained=ProjectDocument(root,self.tool);value=copy.deepcopy(retained.adventure);value['start']['credits']+=4;retained.replace_adventure(value);retained.save()
        with self.assertRaises(EditorError):retain_revision(self.doc,self.state)
        self.assertEqual(source.read_bytes(),before)

    def test_failed_new_copy_is_removed_without_touching_source(self):
        from unittest.mock import patch
        from save_catalogue import copy_exclusive
        source=self.save();before=source.read_bytes();target=self.root/'new-copy.btp'
        with patch('save_catalogue.shutil.copystat',side_effect=OSError('denied')):
            with self.assertRaises(OSError):copy_exclusive(source,target)
        self.assertFalse(target.exists());self.assertEqual(source.read_bytes(),before)

    def test_concurrent_launches_share_one_valid_retained_revision(self):
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=2) as pool:
            jobs=[pool.submit(retain_revision,self.doc.worker_copy(),self.state) for _ in range(2)]
            paths=[job.result() for job in jobs]
        self.assertEqual(paths[0],paths[1]);ProjectDocument(paths[0],self.tool).validate()


if __name__=='__main__':unittest.main()
