"""Mixed CHI quests use shared transactions, source modules and validation."""
import copy,json,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from editor_model import ProjectDocument,EditorError,encoded
from chi_bridge import enable,example,events,data,put,upsert,QuestDocument,schema

@unittest.skipUnless((ROOT/'build/btp-project').exists() and (ROOT/'Original DOS/BTECH.EXE').exists(),'Needs local originals/native tools')
class ChiBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from chi_import import import_campaigns
        cls.temp=tempfile.TemporaryDirectory(prefix='chi-bridge-test-',dir=ROOT/'work');cls.root=Path(cls.temp.name);cls.tool=ROOT/'build/btp-project'
        import_campaigns(ROOT/'Original DOS',cls.root/'base',validator=cls.tool)
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def setUp(self):
        self.folder=self.root/self.id().rsplit('.',1)[-1];shutil.copytree(self.root/'base/updated',self.folder)
        self.doc=ProjectDocument(self.folder,self.tool)
    def request(self,operations,scope=None):
        from authoring_service import revision
        self.request_number=getattr(self,'request_number',0)+1
        return dict(api_version=1,request_id='bridge-test-'+str(self.request_number),project_id=self.doc.manifest['package_id'],expected_revision=revision(self.doc),label='Quest edit',scope=scope or ['*'],operations=operations)
    def test_enable_history_and_native_projection_are_separate(self):
        before=self.doc.files();native=copy.deepcopy(self.doc.adventure);enable(self.doc)
        self.assertTrue(self.doc.adventure['chi_native']);self.assertEqual(self.doc.adventure,native)
        self.assertNotEqual(QuestDocument(self.doc).adventure,self.doc.adventure)
        self.doc.undo();self.assertEqual(before,self.doc.files());self.doc.redo();self.doc.save()
        self.assertEqual(self.doc.files(),ProjectDocument(self.folder,self.tool).files())
    def test_recipe_cli_and_gui_model_are_identical(self):
        from authoring_service import apply_batch
        other=self.root/'batch';shutil.copytree(self.folder,other);batch=ProjectDocument(other,self.tool)
        request=self.request([dict(op='bridge.example')]);example(self.doc);apply_batch(batch,request)
        self.assertEqual(self.doc.files(),{k:v for k,v in batch.files().items() if k!='AUTHORING.json'})
        self.doc.save();result=subprocess.run([sys.executable,str(ROOT/'tools/chi_bridge.py'),'--project',str(self.folder),'list'],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(json.loads(result.stdout)['quest'],events(self.doc))
    def test_proxy_edit_scope_and_protection(self):
        from authoring_service import apply_batch
        from authoring_protection import value_at
        from authoring_contract import AuthoringError
        example(self.doc);native=copy.deepcopy(self.doc.adventure);before=self.doc.files()
        operation=dict(op='quest.patch',collection='events',id='bridge:cadet',changes=dict(text='An edited contract.'))
        with self.assertRaisesRegex(AuthoringError,'outside its declared scope'):
            apply_batch(self.doc,self.request([operation],['adventure.events']))
        self.assertEqual(self.doc.files(),before)
        apply_batch(self.doc,self.request([operation],['quest.events/bridge:cadet']))
        self.assertEqual(value_at(self.doc,'quest.events/bridge:cadet')['text'],'An edited contract.')
        self.assertEqual(self.doc.adventure,native)
        self.doc.undo();self.assertEqual({k:v for k,v in self.doc.files().items() if k!='AUTHORING.json'},before)
        meta=dict(self.doc.metadata);editor=json.loads(meta.get('EDITOR.json',b'{}'))
        editor['authoring_protection']=[dict(id='keep-quest',label='Keep contract',kind='object',path='quest.events/bridge:cadet')]
        meta['EDITOR.json']=encoded(editor);self.doc.replace_all(self.doc.content,self.doc.adventure,self.doc.art,self.doc.manifest,meta)
        with self.assertRaisesRegex(AuthoringError,'protect|Protect|preserv'):apply_batch(self.doc,self.request([operation]))
    def test_native_call_and_binding_validation_roll_back(self):
        from editor_problems import target
        from authoring_contract import diagnostic
        example(self.doc);before=self.doc.files();b=data(self.doc)
        variants=[dict(b['native_calls'][0],entry='chi:comstar-0000'),dict(b['native_calls'][0],**{'return':'chi:comstar-02ce'}),
                  dict(b['native_calls'][0],program='chi:bld-armor',entry='chi:armor-0000')]
        for value in variants:
            with self.assertRaises(EditorError) as error:upsert(self.doc,'native_calls',value)
            self.assertEqual(before,self.doc.files());self.assertEqual(target(self.doc,diagnostic(error.exception))['collection'],'chi_quests')
        for fields in (dict(entrance=15),dict(map='chi:map-15'),dict(event='quest:missing')):
            with self.assertRaises(EditorError):upsert(self.doc,'entrances',dict(b['entrances'][0],**fields))
            self.assertEqual(before,self.doc.files())
    def test_missing_targets_and_unsupported_finish_rejected(self):
        example(self.doc);before=self.doc.files()
        for node in (dict(id='test:missing',op='call',event='none:missing',next='quest:end',failure='quest:end',cancel='quest:end'),
                     dict(id='test:finish',op='finish',text='Do not end the original campaign.')):
            a=events(self.doc);a['events'].append(node)
            with self.assertRaises(EditorError):put(self.doc,quest=a)
            self.assertEqual(self.doc.files(),before)
    def test_source_modules_round_trip(self):
        from campaign_source import convert,build
        example(self.doc);source=self.root/'source';convert(self.doc,source);doc=ProjectDocument(source,self.tool)
        self.assertEqual(events(doc),events(self.doc));self.assertEqual(data(doc),data(self.doc))
        a=events(doc);a['events'][2]['text']='An authored source change.';put(doc,quest=a);doc.save()
        output=self.root/'built';build(doc,output);self.assertEqual(events(ProjectDocument(output,self.tool)),a)
    def test_schemas_summary_and_call_edges(self):
        from authoring_contract import check
        from authoring_inspect import summary,records
        from event_editing import edges
        from chi_coverage import edges as bld_edges
        example(self.doc);check(data(self.doc),schema())
        check(events(self.doc),json.loads((ROOT/'schemas/adventure-v3.schema.json').read_bytes()))
        report=summary(self.doc,self.tool);self.assertEqual(report['native_quests']['entrances'],1)
        self.assertEqual(len(records(self.doc,'quest-events')),len(events(self.doc)['events']))
        call=dict(id='test:call',op='call',event='quest:end',next='quest:end',failure='quest:end',cancel='quest:end')
        self.assertIn(('event','quest:end'),edges(call))
        call['op']='event';self.assertEqual(len(bld_edges(dict(nodes=[call]),call)),3)
    def test_bridge_events_rejected_in_ordinary_project(self):
        from adventure_editing import copy_adventure
        doc=ProjectDocument(ROOT/'examples/beacon-demo',self.tool)
        a=copy_adventure(doc);a['events'].append(dict(id='test:return',op='return',result='success'))
        with self.assertRaisesRegex(EditorError,'bridge'):doc.replace_adventure(a);doc.validate()
    def test_live_native_continuations_and_observations(self):
        from chi_bridge_evidence import prepare,verify
        from chi_coverage import coverage
        output=self.root/'continuations';prepare(self.root/'base',output,self.tool);report=verify(output)
        self.assertEqual(len(report['journeys']),4)
        project=output/'original-nested';prefix=output/'linux-original-nested'
        actions=output/'bank.actions';actions.write_text('accept\naccept\n2\naccept\naccept\n')
        bld,event=output/'native.jsonl',output/'event.jsonl';saved=output/'result.btp'
        command=[str(ROOT/'build/btech-headless'),'--project',str(project),'--load',str(prefix)+'-bld-choice.btp',
                 '--replay',str(actions),'--bld-trace',str(bld),'--event-trace',str(event),'--save',str(saved)]
        result=subprocess.run(command,capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)
        doc=ProjectDocument(project,self.tool);measured=coverage(doc,[bld])
        call=next(n for p in measured['programs'] for n in p['nodes'] if n['id']=='test:quest-call')
        self.assertEqual(call['quest']['returns']['success'],1);self.assertEqual(call['branches'][0]['executions'],1)
        self.assertTrue(any(n.get('native',{}).get('bridge_outcomes',{}).get('success')==1 for p in measured['programs'] for n in p['nodes']))
        self.assertEqual(measured['unresolved_observations'],{})
        observed=[json.loads(line) for line in event.read_text().splitlines()]
        self.assertTrue(any(row['bridge']['depth']==1 for row in observed))
        # Runtime identity pins every continuation to these quest definitions.
        a=events(doc);a['events'][2]['text']='Different revision';put(doc,quest=a);doc.save()
        stale=subprocess.run(command,capture_output=True,text=True,timeout=30)
        self.assertNotEqual(stale.returncode,0);self.assertIn('content',stale.stderr.lower())

if __name__=='__main__':unittest.main()
