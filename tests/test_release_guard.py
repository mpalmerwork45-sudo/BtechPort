import hashlib,io,json,sys,tarfile,tempfile,unittest,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from editor_model import EditorError,encoded
from release_guard import inspect_files,directory,archive,check_payload

class ReleaseGuardTests(unittest.TestCase):
    def test_renamed_caches_and_private_documents_reject(self):
        for name,data in [('picture.dat',b'BTCCoriginal'),('source.json',encoded(dict(format='btp-chi-scripts-v1',programs=[]))),('nested.json',encoded(dict(other=dict(origin='unknown',frames=[]))))]:
            with self.subTest(name=name):
                with self.assertRaises(EditorError):inspect_files({name:data})
        self.assertEqual(inspect_files({'note.md':b'Independently written documentation.'})['status'],'passed')
    def test_known_raw_file_hash_rejects_renaming(self):
        source=ROOT/'Original DOS/MAP1.MTP'
        if not source.exists():self.skipTest('Needs local originals')
        with self.assertRaises(EditorError):check_payload('renamed.dat',source.read_bytes())
    def test_folder_and_archive_inventory_and_traversal(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp);data=b'permitted content';(p/'readme.md').write_bytes(data)
            report=dict(files=[dict(path='readme.md',bytes=len(data),sha256=hashlib.sha256(data).hexdigest())]);(p/'DISTRIBUTION.json').write_bytes(encoded(report))
            self.assertEqual(directory(p)['status'],'passed')
            bundle=p.parent/(p.name+'.zip')
            try:
                with zipfile.ZipFile(bundle,'x') as z:
                    for name in ('readme.md','DISTRIBUTION.json'):z.write(p/name,'Kit/'+name)
                self.assertEqual(archive(bundle)['status'],'passed')
                with zipfile.ZipFile(bundle,'a') as z:z.writestr('../escape',b'bad')
                with self.assertRaises(EditorError):archive(bundle)
            finally:bundle.unlink(missing_ok=True)
            (p/'readme.md').write_bytes(b'changed')
            with self.assertRaisesRegex(EditorError,'mismatch'):directory(p)

if __name__=='__main__':unittest.main()
