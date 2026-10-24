"""Only the two appended endgame strings may change in a native save update."""
import json,shutil,struct,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from editor_model import ProjectDocument,EditorError
from chi_import import import_campaigns
from save_migration import compatible,migrate

def earlier_cache(data):
    count=struct.unpack_from('<H',data,6)[0];base=72+4*count
    offset,size=struct.unpack_from('<HH',data,72+4*372);length=offset+size+1
    return b'BTTA'+struct.pack('<HH',length,373)+data[8:72+4*373]+data[base:base+length]+data[-2048:]

@unittest.skipUnless((ROOT/'Original DOS/BTECH.EXE').exists(),'Requires local originals')
class NativeDialogueMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'work');cls.root=Path(cls.temp.name);cls.tool=ROOT/'build/btp-project';cls.player=ROOT/'build/btech-headless'
        import_campaigns(ROOT/'Original DOS',cls.root/'pair',validator=cls.tool)
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def test_both_native_editions_keep_the_entire_payload_and_progress(self):
        for edition in ('original','updated'):
            new=ProjectDocument(self.root/'pair'/edition,self.tool);old_path=self.root/('old-'+edition);shutil.copytree(new.root,old_path)
            path=old_path/'chi/talk-data.bin';path.write_bytes(earlier_cache(path.read_bytes()));old=ProjectDocument(old_path,self.tool)
            source=self.root/(edition+'-before.btp');target=self.root/(edition+'-after.btp')
            before=json.loads(subprocess.check_output([str(self.player),'--project',str(old_path),'--save',str(source)],text=True));data=source.read_bytes()
            result=migrate(old,new,source,target,dict(player=str(self.player)))
            after=json.loads(subprocess.check_output([str(self.player),'--project',str(new.root),'--load',str(target)],text=True))
            self.assertEqual(before,after);self.assertEqual(source.read_bytes(),data);self.assertEqual(target.read_bytes()[160:],data[160:]);self.assertEqual(result['tick'],before['tick'])
            with self.assertRaises(EditorError):migrate(old,new,source,target,dict(player=str(self.player)))
    def test_existing_text_font_and_map_changes_are_rejected(self):
        new_path=self.root/'pair/original';old_path=self.root/'reject-old';shutil.copytree(new_path,old_path)
        p=old_path/'chi/talk-data.bin';p.write_bytes(earlier_cache(p.read_bytes()));old=ProjectDocument(old_path,self.tool)
        for name in ('text','font','map'):
            path=self.root/('reject-'+name);shutil.copytree(new_path,path)
            p=path/('chi/MAP2.MTP' if name=='map' else 'chi/talk-data.bin');data=bytearray(p.read_bytes())
            at=72+4*375 if name=='text' else -1;data[at]^=1;p.write_bytes(data)
            candidate=ProjectDocument(path,self.tool)
            with self.assertRaises(EditorError):compatible(old,candidate)
    def test_copy_update_and_save_preserve_the_old_project(self):
        from chi_dialogue_update import update
        source=self.root/'utility-old';shutil.copytree(self.root/'pair/updated',source)
        p=source/'chi/talk-data.bin';p.write_bytes(earlier_cache(p.read_bytes()));before=p.read_bytes()
        save=self.root/'utility.btp';subprocess.run([str(self.player),'--project',str(source),'--save',str(save)],check=True,capture_output=True,timeout=20);payload=save.read_bytes()
        output=self.root/'updated copy';report=update(source,ROOT/'Original DOS',output,self.tool,save,self.player)
        self.assertEqual((output/'recovered-save.btp').read_bytes()[160:],payload[160:]);self.assertEqual(p.read_bytes(),before);self.assertEqual(save.read_bytes(),payload)
        self.assertEqual(report['status'],'updated')
        with self.assertRaises(EditorError):update(source,ROOT/'Original DOS',output,self.tool,save,self.player)

if __name__=='__main__':unittest.main()
