"""Shared mission edits, source round trips and native validation contracts."""
import copy,json,shutil,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from editor_model import ProjectDocument,EditorError,encoded
from chi_missions import data,catalogue,enable,update,unit,put

@unittest.skipUnless((ROOT/'build/btp-project').exists() and (ROOT/'Original DOS/BTECH.EXE').exists(),'Needs local originals/native tools')
class MissionProjectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from chi_import import import_campaigns
        cls.temp=tempfile.TemporaryDirectory(prefix='chi-mission-test-',dir=ROOT/'work');cls.root=Path(cls.temp.name);cls.tool=ROOT/'build/btp-project'
        import_campaigns(ROOT/'Original DOS',cls.root/'base',validator=cls.tool)
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def setUp(self):
        self.folder=self.root/self.id().rsplit('.',1)[-1];shutil.copytree(self.root/'base/updated',self.folder);self.doc=ProjectDocument(self.folder,self.tool)
    def test_catalogue_effective_defaults_and_runtime_schemas(self):
        c=catalogue(self.doc);self.assertGreater(len(c['parameters']),700);self.assertEqual(len(c['units']),65)
        self.assertTrue(all(p['minimum']<=p['value']<=p['maximum'] for p in c['parameters']))
        self.assertEqual(data(self.doc)['parameters'],{p['id']:p['default'] for p in c['parameters']})
        from make_chi_missions import PARAMETERS
        self.assertEqual([p['id'] for p in c['parameters']],[p['id'] for p in PARAMETERS])
    def test_all_programs_still_compile_byte_exactly(self):
        from chi_bld import compiled
        for profile in ('original','updated'):
            doc=ProjectDocument(self.root/'base'/profile,self.tool)
            for p in json.loads(doc.metadata['chi-scripts.json'])['programs']:
                self.assertEqual(bytes.fromhex(compiled(doc,p['id'])['encrypted']),doc.files()['chi/'+p['resource']])
    def test_scoped_edit_undo_save_reopen_and_protection(self):
        from authoring_service import apply_batch,revision
        from authoring_protection import value_at
        before=self.doc.files();request=dict(api_version=1,request_id='mission-edit',project_id=self.doc.manifest['package_id'],expected_revision=revision(self.doc),label='Change duel',scope=['chi.mission_parameters/training.4.enemy_count','chi.mission_units/training.4.enemy.0'],operations=[dict(op='missions.update',parameter='training.4.enemy_count',value=2),dict(op='missions.unit',role='training.4.enemy.0',definition='native:jenner.0')])
        apply_batch(self.doc,request);changed=self.doc.files();self.assertEqual(value_at(self.doc,'chi.mission_parameters/training.4.enemy_count'),2)
        self.assertEqual(value_at(self.doc,'chi.mission_units/training.4.enemy.0'),'native:jenner.0')
        self.doc.undo();self.assertEqual({k:v for k,v in self.doc.files().items() if k!='AUTHORING.json'},before)
        self.doc.redo();self.assertEqual(self.doc.files(),changed);self.doc.save();self.assertEqual(ProjectDocument(self.folder,self.tool).files(),changed)
    def test_bad_settings_rollback_and_navigate_to_missions_not_services(self):
        from authoring_contract import diagnostic
        from editor_problems import target
        before=self.doc.files()
        for parameter,value in [('unknown',1),('training.4.enemy_count',7),('quiz.rounds',0),('cache.door.0.x',3),('start.credits',True),('training.4.return_y_min',100),('arena.escape_min',1400),('training.0.invasion',2)]:
            with self.assertRaises(EditorError) as caught:update(self.doc,parameter,value)
            self.assertEqual(self.doc.files(),before);self.assertEqual(target(self.doc,diagnostic(caught.exception))['collection'],'native_missions')
    def test_invalid_references_are_rejected_and_units_are_owned(self):
        chosen=self.doc.content['mechs'][0]['id'];unit(self.doc,'training.4.enemy.0',chosen);self.assertEqual(data(self.doc)['units']['training.4.enemy.0'],chosen)
        before=self.doc.files()
        for role,definition in [('unknown','native:jenner.0'),('training.4.enemy.0','missing:unit'),('training.4.enemy.0','native:jenner.1')]:
            with self.assertRaises(EditorError):unit(self.doc,role,definition)
            self.assertEqual(self.doc.files(),before)
        unit(self.doc,'training.4.enemy.0','');self.assertEqual(data(self.doc)['units']['training.4.enemy.0'],'')
    def test_source_build_preserves_settings_and_role(self):
        from campaign_source import convert,build
        source=self.root/'source';convert(self.doc,source);doc=ProjectDocument(source,self.tool);self.assertIn('chi_missions',doc.source.index['sections'])
        update(doc,'encounter.cash_base',31);unit(doc,'arena.loan','native:commando.0');doc.save();output=self.root/'built';build(doc,output)
        self.assertEqual(data(ProjectDocument(output,self.tool)),data(doc))
    def test_older_project_enabling_is_one_reversible_change(self):
        manifest=copy.deepcopy(self.doc.manifest);manifest.pop('chi_missions');meta=dict(self.doc.metadata);meta.pop('chi-missions.json')
        self.doc.replace_all(self.doc.content,self.doc.adventure,self.doc.art,manifest,meta);self.doc.validate();before=self.doc.files();enable(self.doc)
        self.doc.undo();self.assertEqual(self.doc.files(),before);self.doc.redo();self.assertEqual(data(self.doc)['parameters']['invasion.enemy_count'],4)
    def test_mission_text_and_fee_references(self):
        from chi_bld import data as programs,compiled,update as edit
        p=programs(self.doc)['programs'][4];text=next(n for n in p['nodes'] if n['op']=='text')
        edit(self.doc,p['id'],text['id'],dict(text='Mission fee {mission:start.credits}.'));update(self.doc,'start.credits',91)
        raw=bytes.fromhex(compiled(self.doc,p['id'])['encrypted']);plain=bytes(((v+41)&255)^233 for v in raw[2:]);self.assertIn(b'Mission fee 91.',plain)
        with self.assertRaises(EditorError):edit(self.doc,p['id'],text['id'],dict(text='{mission:missing}'))
    def test_combined_bounds_are_transactional(self):
        before=self.doc.files();v=data(self.doc);v['parameters'].update({'training.4.enemy_count':5,'training.4.count_mask':3})
        with self.assertRaises(EditorError):put(self.doc,v)
        self.assertEqual(self.doc.files(),before)
        v=data(self.doc);v['parameters']['cache.password.1']=v['parameters']['cache.password.0']
        with self.assertRaises(EditorError):put(self.doc,v)
        self.assertEqual(self.doc.files(),before)
        with self.assertRaises(EditorError):update(self.doc,'arena.rental_roll_base',10)
        self.assertEqual(self.doc.files(),before)
if __name__=='__main__':unittest.main()
