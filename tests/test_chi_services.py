"""Native service contracts, editing, provenance and private gameplay proofs."""
import copy,json,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from editor_model import ProjectDocument,EditorError,encoded
from chi_services import data,catalogue,enable,update,stock

@unittest.skipUnless((ROOT/'build/btp-project').exists() and (ROOT/'Original DOS/BTECH.EXE').exists(),'Needs local originals/native tools')
class ServiceProjectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from chi_import import import_campaigns
        cls.temp=tempfile.TemporaryDirectory(prefix='chi-service-test-',dir=ROOT/'work');cls.root=Path(cls.temp.name);cls.tool=ROOT/'build/btp-project'
        import_campaigns(ROOT/'Original DOS',cls.root/'base',validator=cls.tool)
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def setUp(self):
        self.folder=self.root/self.id().rsplit('.',1)[-1];shutil.copytree(self.root/'base/updated',self.folder);self.doc=ProjectDocument(self.folder,self.tool)
    def test_registry_contexts_and_effective_defaults(self):
        from chi_bld import data as scripts
        c=catalogue(self.doc);expected={(p['building'],n['action']) for p in scripts(self.doc)['programs'] for n in p['nodes'] if n['op']=='native'}
        observed={(b,a['action']) for a in c['actions'] for b in a['buildings']};self.assertEqual(observed,expected);self.assertEqual(len(c['actions']),47)
        self.assertTrue(all(p['minimum']<=p['value']<=p['maximum'] for p in c['parameters']))
        self.assertTrue(all(a['consumer'] and a['requirements'] and a['outputs'] and a['yield'] and a['errors'] for a in c['actions']))
        self.assertEqual(data(self.doc)['parameters'],{p['id']:p['default'] for p in c['parameters']})
    def test_bound_prices_and_fee_operands_compile_exactly(self):
        from chi_bld import compiled
        for p in json.loads(self.doc.metadata['chi-scripts.json'])['programs']:
            self.assertEqual(bytes.fromhex(compiled(self.doc,p['id'])['encrypted']),self.doc.files()['chi/'+p['resource']])
        update(self.doc,'armour.price.4',12345)
        result=compiled(self.doc,'chi:bld-armor');self.assertIn(b'12,345',bytes(((v+41)&255)^233 for v in bytes.fromhex(result['encrypted'])[2:]))
        update(self.doc,'medical.facility_fee',37)
        result=compiled(self.doc,'chi:bld-hospital');node=next(n for n in result['nodes'] if n['id']=='chi:hospital-0378');raw=bytes.fromhex(result['encrypted'])[2:];raw=bytes(((v+41)&255)^233 for v in raw)
        self.assertEqual(raw[node['offset']+1:node['offset']+3],b'\x25\x00')
    def test_shared_history_scope_receipts_and_reopen(self):
        from authoring_service import apply_batch,revision
        from authoring_protection import value_at
        before=self.doc.files();r=dict(api_version=1,request_id='services-edit',project_id=self.doc.manifest['package_id'],expected_revision=revision(self.doc),label='Repair quote',scope=['chi.service_parameters/repair.armour'],operations=[dict(op='services.update',parameter='repair.armour',value=6)])
        apply_batch(self.doc,r);changed=self.doc.files();self.assertEqual(value_at(self.doc,'chi.service_parameters/repair.armour'),6)
        self.doc.undo();self.assertEqual({k:v for k,v in self.doc.files().items() if k!='AUTHORING.json'},before)
        self.doc.redo();self.assertEqual(changed,self.doc.files());self.doc.save();self.assertEqual(ProjectDocument(self.folder,self.tool).files(),self.doc.files())
    def test_bad_settings_roll_back_and_map_to_editor(self):
        from authoring_contract import diagnostic
        from editor_problems import target
        before=self.doc.files()
        for parameter,value in [('missing',1),('repair.armour',-1),('recruit.spy_chance',25),('prison.reward',3),('market.rate.0',0),('weapons.item.1',14),('repair.armour',True),('arena.prize',32768)]:
            with self.assertRaises(EditorError) as caught:update(self.doc,parameter,value)
            self.assertEqual(self.doc.files(),before)
            self.assertEqual(target(self.doc,diagnostic(caught.exception))['collection'],'native_services')
    def test_broker_stock_uses_stable_ids_and_rejects_missing(self):
        unit=self.doc.content['mechs'][0]['id'];stock(self.doc,[unit]);self.assertEqual(data(self.doc)['broker_stock'],[unit]);before=self.doc.files()
        for units in ([unit,unit],['missing:unit']):
            with self.assertRaises(EditorError):stock(self.doc,units)
            self.assertEqual(self.doc.files(),before)
        stock(self.doc,None);self.assertNotIn('broker_stock',data(self.doc))
    def test_source_modules_build_and_service_diagnostics(self):
        from campaign_source import convert,build
        target=self.root/'source';convert(self.doc,target);doc=ProjectDocument(target,self.tool);self.assertEqual(data(doc),data(self.doc));self.assertIn('chi_services',doc.source.index['sections'])
        update(doc,'repair.armour',7);doc.save();output=self.root/'built';build(doc,output);self.assertEqual(data(ProjectDocument(output,self.tool))['parameters']['repair.armour'],7)
    def test_named_actions_and_unknown_template_failures(self):
        from chi_bld import data as scripts,update as edit,compiled
        program=scripts(self.doc)['programs'][4];native=next(n for n in program['nodes'] if n['op']=='native' and n['action']==10)
        before=compiled(self.doc,program['id'])['encrypted'];edit(self.doc,program['id'],native['id'],dict(action='native.insert-credits'));self.assertEqual(compiled(self.doc,program['id'])['encrypted'],before)
        text=next(n for n in program['nodes'] if n['op']=='text')
        with self.assertRaises(EditorError):edit(self.doc,program['id'],text['id'],dict(text='{service:missing}'))
    def test_enable_older_project_is_one_reversible_change_and_preserves_custom_text(self):
        from chi_bld import extract
        manifest=copy.deepcopy(self.doc.manifest);manifest.pop('chi_services');meta=dict(self.doc.metadata);meta.pop('chi-services.json')
        sources=extract(self.doc.files());text=next(n for n in sources['programs'][3]['nodes'] if n['op']=='text');text['text']='Own shop description.'
        meta['chi-scripts.json']=encoded(sources);campaign=json.loads(meta['campaign.json']);campaign['dialogue_overrides']=[dict(index=241,text='Own repair message.')];meta['campaign.json']=encoded(campaign)
        self.doc.replace_all(self.doc.content,self.doc.adventure,self.doc.art,manifest,meta);self.doc.validate();before=self.doc.files();enable(self.doc)
        self.assertEqual(json.loads(self.doc.metadata['chi-scripts.json'])['programs'][3]['nodes'][sources['programs'][3]['nodes'].index(text)]['text'],'Own shop description.')
        self.assertEqual(next(v['text'] for v in json.loads(self.doc.metadata['campaign.json'])['dialogue_overrides'] if v['index']==241),'Own repair message.')
        self.doc.undo();self.assertEqual(self.doc.files(),before)

if __name__=='__main__':unittest.main()
