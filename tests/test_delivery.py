import copy,json,os,struct,subprocess,sys,tempfile,unittest
from unittest.mock import patch
from types import SimpleNamespace
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from editor_model import create_project,ProjectDocument,EditorError
from save_migration import compatible,migrate
from delivery import asset_report,write_launchers

class DeliveryTests(unittest.TestCase):
    def test_packaged_probe_rejects_missing_reports_and_preserves_old_evidence(self):
        from packaged_smoke import run
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);kit=root/'kit';kit.mkdir();(kit/'DISTRIBUTION.json').write_text('{}')
            proof=root/'proof'
            with patch('packaged_smoke.subprocess.run',return_value=SimpleNamespace(returncode=0)) as execute:
                with self.assertRaises(FileNotFoundError):run(kit,{},output=proof)
                self.assertEqual(json.loads((proof/'evidence.json').read_bytes())['status'],'failed')
                before=(proof/'evidence.json').read_bytes()
                with self.assertRaisesRegex(EditorError,'earlier proofs'):run(kit,{},output=proof)
                self.assertEqual((proof/'evidence.json').read_bytes(),before)
                self.assertEqual(execute.call_count,2)
            with self.assertRaisesRegex(EditorError,'outside original/reference'):run(kit,{},output=kit/'proof')
            self.assertFalse((kit/'proof').exists())

    def test_author_console_preserves_spaced_paths_status_and_stdout(self):
        # A tiny interpreter probe tests shell argument forwarding, environment
        # and exit status independently of this machine's bundled dependencies.
        with tempfile.TemporaryDirectory(prefix='CLI launcher ') as tmp:
            root=Path(tmp);kit=root/'Kit with spaces';kit.mkdir();(kit/'runtime/bin').mkdir(parents=True)
            probe=kit/'runtime/bin/python3'
            probe.write_text('#!/bin/sh\nprintf "%s\\n" "$PWD" "$PYTHONHOME" "$@"\nexit 23\n');probe.chmod(0o755)
            write_launchers(kit,'linux')
            result=subprocess.run([str(kit/'Author'),'recipe','build','--file','My recipe.json'],cwd=root,capture_output=True,text=True)
            self.assertEqual(result.returncode,23)
            self.assertEqual(result.stdout.splitlines(),[str(root),str(kit/'runtime'),str(kit/'tools/author.py'),'recipe','build','--file','My recipe.json'])
            write_launchers(kit,'windows');cmd=(kit/'Author.cmd').read_text()
            self.assertIn('%*',cmd);self.assertIn('exit /b %errorlevel%',cmd);self.assertNotIn('start ',cmd)

    def test_safe_migration_and_refusals(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);tool=ROOT/'build/btp-project';player=ROOT/'build/btech-headless'
            old=create_project(ROOT/'examples/beacon-demo',root/'old','migration-test','Test',tool)
            old.export(root/'new');new=ProjectDocument(root/'new',tool)
            save=root/'old.btp';result=subprocess.run([str(player),'--project',str(old.root),'--save',str(save)],capture_output=True,text=True);self.assertEqual(result.returncode,0,result.stderr)
            before=save.read_bytes();new.manifest['title']='Revised artwork';next(e for e in new.adventure['events'] if e['op']=='say')['text']='New opening words.'
            extra=copy.deepcopy(new.content['mechs'][0]);extra['id']='migration-test:new-unit';extra['name']='Added chassis';new.content['mechs'].append(extra)
            new.save();target=root/'new.btp';report=migrate(old,new,save,target,{'player':str(player)})
            self.assertEqual(before,save.read_bytes());self.assertEqual(before[160:],target.read_bytes()[160:]);self.assertEqual(report['tick'],0)
            with self.assertRaisesRegex(EditorError,'never overwrites'):migrate(old,new,save,target,{'player':str(player)})
            new.content['mechs'].reverse()
            with self.assertRaisesRegex(EditorError,'mechs'):compatible(old,new)
            new.content['mechs'].reverse();new.adventure['maps'][0]['entrances'][0]['at'][0]+=1
            with self.assertRaisesRegex(EditorError,'topology'):compatible(old,new)
            self.assertTrue(asset_report(old)['files']);self.assertEqual(asset_report(old)['requires'],'none')

if __name__=='__main__':unittest.main()
