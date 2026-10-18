import copy,json,struct,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from editor_model import create_project,ProjectDocument,EditorError
from save_migration import compatible,migrate
from delivery import asset_report

class DeliveryTests(unittest.TestCase):
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
