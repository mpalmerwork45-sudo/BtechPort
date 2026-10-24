"""Real native saves survive repeated editor Play without crossing revisions."""
import copy,json,os,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from editor_model import ProjectDocument,create_project
from app_runtime import restore_playtest_saves,project_slot_name,game_command

class PlaySaveRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.tool=ROOT/'build/btp-project';self.player=ROOT/'build/btech-headless';self.state=self.root/'state'
        self.doc=create_project(ROOT/'examples/beacon-demo',self.root/'game','saved-play','Saved Play',self.tool)
        self.settings=dict(player=str(self.player));self.old=self.state/'play-snapshots/run-old';self.old.mkdir(parents=True)
    def save(self,path,extra=()):
        subprocess.run([str(self.player),'--project',str(self.doc.root),*map(str,extra),'--save',str(path)],check=True,capture_output=True,timeout=20)
    def paths(self):
        old=self.doc.play_command(self.settings,self.old);new=self.doc.play_command(self.settings,self.state)
        return Path(old[old.index('--save-file')+1]).parent,Path(new[new.index('--save-file')+1]).parent
    def test_all_six_slots_restore_once_and_keep_sources(self):
        old,target=self.paths();before={}
        for n in range(1,7):
            p=old/project_slot_name(self.doc,n);self.save(p);before[p]=(p.read_bytes(),p.stat().st_mtime_ns)
        restored=restore_playtest_saves(self.doc,self.state,target);self.assertEqual(len(restored),6)
        for source,destination in restored:
            self.assertEqual((destination.read_bytes(),destination.stat().st_mtime_ns),before[source])
            self.assertEqual((source.read_bytes(),source.stat().st_mtime_ns),before[source])
            r=subprocess.run([str(self.player),'--project',str(self.doc.root),'--load',str(destination)],capture_output=True,text=True,timeout=20)
            self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual(restore_playtest_saves(self.doc,self.state,target),[])
    def test_existing_progress_and_other_revisions_are_preserved(self):
        old,target=self.paths();source=old/project_slot_name(self.doc);self.save(source)
        destination=target/source.name;self.save(destination);before=destination.read_bytes()
        self.assertEqual(restore_playtest_saves(self.doc,self.state,target),[]);self.assertEqual(destination.read_bytes(),before)
        changed=copy.deepcopy(self.doc.adventure);changed['start']['credits']+=1;self.doc.replace_adventure(changed)
        new=self.doc.play_command(self.settings,self.state);new_target=Path(new[new.index('--save-file')+1]).parent
        self.assertNotEqual(new_target,target);self.assertEqual(restore_playtest_saves(self.doc,self.state,new_target),[])
        self.assertEqual(source.read_bytes(),before)
    def test_newest_valid_slot_wins_and_bad_crc_is_ignored(self):
        old,target=self.paths();source=old/project_slot_name(self.doc);self.save(source);os.utime(source,ns=(1,1))
        other=self.state/'play-snapshots/run-new/play'/self.doc.manifest['package_id']/target.name;other.mkdir(parents=True)
        latest=other/source.name;actions=self.root/'money.actions';actions.write_text('credit-10000\n');self.save(latest,('--replay',actions))
        newest=latest.read_bytes();restored=restore_playtest_saves(self.doc,self.state,target)
        self.assertEqual(restored[0][0],latest);self.assertEqual(restored[0][1].read_bytes(),newest)
        # Another slot has the correct identity/digest but a damaged payload.
        damaged=bytearray(newest);damaged[-1]^=1;(other/project_slot_name(self.doc,2)).write_bytes(damaged)
        self.assertEqual(restore_playtest_saves(self.doc,self.state,target),[])
    def test_launcher_resume_uses_the_native_empty_roster_filename(self):
        from chi_import import import_campaigns
        if not (ROOT/'Original DOS/BTECH.EXE').exists():self.skipTest('Local originals unavailable')
        import_campaigns(ROOT/'Original DOS',self.root/'original','original',self.tool)
        project=self.root/'original/original';doc=ProjectDocument(project,self.tool)
        command=game_command('My project',self.settings,self.state,project)
        slot=Path(command[command.index('--save-file')+1]);self.assertEqual(project_slot_name(doc),'game.btp')
        subprocess.run([str(self.player),'--project',str(project),'--save',str(slot)],check=True,capture_output=True,timeout=20)
        resume=game_command('My project',self.settings,self.state,project,resume=True)
        self.assertEqual(Path(resume[resume.index('--load')+1]),slot)
        result=subprocess.run(resume,capture_output=True,text=True,timeout=20);self.assertEqual(result.returncode,0,result.stderr)

if __name__=='__main__':unittest.main()
