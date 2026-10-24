"""Fresh/offline import and failure recovery without changing reference inputs."""
import hashlib,json,os,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from chi_import import import_campaigns,read_source,interrupted_imports,SOURCE_FILES
from editor_model import ProjectDocument,EditorError,encoded

@unittest.skipUnless((ROOT/'build/btp-project').exists() and (ROOT/'Original DOS/BTECH.EXE').exists(),'Needs local original files and native build')
class SetupTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='CHI setup é 漢字 ',dir=ROOT/'work');self.root=Path(self.temp.name);self.tool=ROOT/'build/btp-project'
    def tearDown(self):self.temp.cleanup()
    def source(self):
        source=self.root/'Original files é 漢字';source.mkdir()
        for leaf in SOURCE_FILES:shutil.copyfile(ROOT/'Original DOS'/leaf,source/leaf)
        return source
    def test_missing_size_and_hash_errors_identify_the_resource(self):
        source=self.source();path=source/'MAP1.MTP';original=path.read_bytes();path.unlink()
        with self.assertRaisesRegex(EditorError,'Missing original file: MAP1'):read_source(source)
        path.write_bytes(original[:-1])
        with self.assertRaisesRegex(EditorError,'size.*MAP1'):read_source(source)
        changed=bytearray(original);changed[-1]^=1;path.write_bytes(changed)
        with self.assertRaisesRegex(EditorError,'SHA-256.*MAP1.*1.03'):read_source(source)
    def test_readonly_inputs_moved_pair_offline_and_unicode_saves(self):
        source=self.source()
        for path in source.iterdir():path.chmod(0o444)
        before={p.name:(hashlib.sha256(p.read_bytes()).hexdigest(),p.stat().st_mtime_ns,p.stat().st_mode) for p in source.iterdir()}
        destination=self.root/'Fresh campaigns é 漢字';import_campaigns(source,destination,validator=self.tool)
        self.assertEqual(before,{p.name:(hashlib.sha256(p.read_bytes()).hexdigest(),p.stat().st_mtime_ns,p.stat().st_mode) for p in source.iterdir()})
        moved=self.root/'Moved campaigns é 漢字';destination.rename(moved)
        source.rename(self.root/'Original installation no longer available')
        for edition in ('original','updated'):
            project=moved/edition;save=self.root/(edition+' sauvegarde 漢字.btp')
            command=[str(ROOT/'build/btech-headless'),'--project',str(project)]
            state=json.loads(subprocess.check_output([*command,'--save',str(save)],cwd=self.root,text=True,timeout=20))
            loaded=json.loads(subprocess.check_output([*command,'--load',str(save)],cwd=self.root,text=True,timeout=20))
            self.assertEqual(state,loaded);self.assertEqual(state.get('combat_rules','legacy'),'enhanced' if edition=='updated' else 'legacy')
            self.assertFalse((self.root/'work').exists())
    def test_interrupted_stage_is_readonly_and_retry_preserves_it(self):
        stage=self.root/'.chi-import-after-crash';stage.mkdir();marker=stage/'IMPORT-STAGING.json'
        marker.write_bytes(encoded(dict(format='btp-chi-import-staging-v1',output=str(self.root/'retry'),started=0,pid=0)))
        (stage/'partial').write_text('retained partial output')
        rows=interrupted_imports(self.root);self.assertEqual(len(rows),1)
        result=subprocess.run([sys.executable,str(ROOT/'tools/chi_import.py'),'--inspect-staging',str(self.root)],capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(json.loads(result.stdout)['interrupted'],rows)
        import_campaigns(ROOT/'Original DOS',self.root/'retry','original',self.tool)
        self.assertEqual((stage/'partial').read_text(),'retained partial output');self.assertEqual(interrupted_imports(self.root),rows)
    def test_unavailable_parent_and_simulated_denied_publication_preserve_outputs(self):
        with self.assertRaisesRegex(EditorError,'parent'):import_campaigns(ROOT/'Original DOS',self.root/'missing/child',validator=self.tool)
        destination=self.root/'denied'
        # Root/ACL configurations can permit writes to mode-0555 directories.
        # Inject the OS denial at the publication boundary reproducibly.
        with patch('chi_import.publish',side_effect=PermissionError('Permission denied: choose a writable output folder')):
            with self.assertRaisesRegex(PermissionError,'writable'):import_campaigns(ROOT/'Original DOS',destination,'original',self.tool)
        self.assertFalse(destination.exists());self.assertFalse(list(self.root.glob('.chi-import-*')))

if __name__=='__main__':unittest.main()
