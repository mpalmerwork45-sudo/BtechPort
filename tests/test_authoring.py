"""The public authoring contract must preserve human work and game semantics."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from authoring_contract import AuthoringError,check,OPERATIONS,diagnostic
from authoring_service import apply_batch,revision,changed_objects
from authoring_inspect import summary,query,capabilities
from editor_model import ProjectDocument,create_project,EditorError,AUTHORING_RECEIPTS
from adventure_editing import paint
from map_construction import commit_tiles
TOOL=Path(os.environ.get('BTP_PROJECT_TOOL',ROOT/'build/btp-project'))


class Authoring(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='btp-author-');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.doc=create_project(ROOT/'examples/beacon-demo',self.root/'game','author-test','Author test',TOOL)

    def request(self,ops=None,identity='test-1',scope=None):
        return dict(api_version=1,request_id=identity,project_id=self.doc.manifest['package_id'],expected_revision=revision(self.doc),
                    label='Authoring test',scope=scope or ['*'],operations=ops or [dict(op='object.patch',collection='events',id='beacon:welcome',changes={'text':'A human-readable mission briefing.'})])

    def test_query_does_not_write_or_import_gui(self):
        before=self.doc.files();data=summary(self.doc,TOOL)
        self.assertEqual(data['capacity']['maps']['used'],2)
        self.assertEqual(data['start'],self.doc.adventure['start'])
        self.assertEqual(query(self.doc,'objects','mechs',limit=1)['next_offset'],1)
        self.assertEqual(len(query(self.doc,'map',identity='beacon:town',rect=[2,2,4,3])['rows']),3)
        self.assertEqual(before,self.doc.files())
        code="import sys; sys.path.insert(0,'tools'); import authoring_service, scene_tools; assert 'tkinter' not in sys.modules"
        subprocess.run([sys.executable,'-c',code],cwd=ROOT,check=True,timeout=10)
        self.assertFalse((self.doc.root/'.btp-writer.lock').exists())

    def test_batch_dry_run_undo_redo_and_durable_retry(self):
        before=revision(self.doc);request=self.request()
        preview=apply_batch(self.doc,request,dry_run=True)
        self.assertEqual(before,revision(self.doc));self.assertEqual(len(self.doc.undo_stack),0)
        result=apply_batch(self.doc,request)
        self.assertEqual(preview['changes'],result['changes']);self.assertEqual(len(self.doc.undo_stack),1)
        self.assertEqual(preview['result_revision'],revision(self.doc))
        after=revision(self.doc);self.doc.undo();self.assertEqual(before,revision(self.doc))
        self.assertEqual(apply_batch(self.doc,request)['status'],'already_applied')
        self.doc.redo();self.assertEqual(after,revision(self.doc));self.doc.save()
        reopened=ProjectDocument(self.doc.root,TOOL)
        self.assertEqual(apply_batch(reopened,request)['status'],'already_applied')
        request['operations'][0]['changes']['text']='Different request under the same ID'
        with self.assertRaisesRegex(AuthoringError,'different content'):apply_batch(reopened,request)

    def test_human_changes_and_stale_revisions(self):
        request=self.request();a=copy.deepcopy(self.doc.adventure)
        a['maps'][0]['name']='Human town name';paint(a['maps'][0],0,3,3,'w');commit_tiles(self.doc,a)
        with self.assertRaisesRegex(AuthoringError,'changed since'):apply_batch(self.doc,request)
        request['expected_revision']=revision(self.doc);apply_batch(self.doc,request,save=True)
        self.assertEqual(self.doc.adventure['maps'],a['maps'])
        self.assertEqual(ProjectDocument(self.doc.root,TOOL).adventure['maps'],a['maps'])

    def test_connected_batch_validates_once_and_failure_is_atomic(self):
        ops=[dict(op='object.put',collection='events',value={'id':'author-test:hello','op':'say','text':'Hello.','next':'author-test:end'}),
             dict(op='start.set',changes={'event':'author-test:hello'}),
             dict(op='object.put',collection='events',value={'id':'author-test:end','op':'end'})]
        apply_batch(self.doc,self.request(ops),save=True)
        before=copy.deepcopy(self.doc.__dict__);bad=self.request([dict(op='object.patch',collection='events',id='author-test:hello',changes={'next':'missing:end'})],identity='bad')
        with self.assertRaises(EditorError):apply_batch(self.doc,bad,save=True)
        self.assertEqual(self.doc.__dict__,before)
        self.assertEqual(self.doc.files(),ProjectDocument(self.doc.root,TOOL).files())

    def test_scope_cancel_external_changes_and_new_metadata(self):
        before=revision(self.doc)
        with self.assertRaisesRegex(AuthoringError,'outside its declared scope'):
            apply_batch(self.doc,self.request(scope=['adventure.maps']))
        with self.assertRaisesRegex(AuthoringError,'cancelled'):apply_batch(self.doc,self.request(),cancelled=lambda:True)
        self.assertEqual(before,revision(self.doc))
        other=ProjectDocument(self.doc.root,TOOL)
        apply_batch(other,self.request(),save=True)
        with self.assertRaises(EditorError):apply_batch(self.doc,self.request(identity='after-external'))

    def test_interrupted_save_rolls_back_receipt_and_content(self):
        request=self.request();before=self.doc.files();original=ProjectDocument.atomic_file;count=0
        def crash(path,data):
            nonlocal count
            count+=1
            if count==2:raise SystemExit('interruption')
            original(path,data)
        with patch.object(ProjectDocument,'atomic_file',side_effect=crash):
            with self.assertRaises(SystemExit):apply_batch(self.doc,request,save=True)
        with self.assertRaisesRegex(EditorError,'Interrupted save'):
            ProjectDocument(self.doc.root,TOOL,recover=False)
        recovered=ProjectDocument(self.doc.root,TOOL)
        self.assertEqual(before,recovered.files())
        apply_batch(recovered,request,save=True)
        self.assertEqual(apply_batch(ProjectDocument(self.doc.root,TOOL),request)['status'],'already_applied')

    def test_capacity_bad_coordinates_and_descriptors(self):
        for descriptor in OPERATIONS.values():check(descriptor['example'],descriptor['schema'])
        before=revision(self.doc)
        ops=[dict(op='object.put',collection='events',value=dict(id=f'author-test:end-{i}',op='end')) for i in range(256)]
        with self.assertRaises(EditorError):apply_batch(self.doc,self.request(ops))
        with self.assertRaises(AuthoringError):apply_batch(self.doc,self.request([dict(op='map.paint',map='beacon:town',tile='beacon:grass',start=[100,100])]))
        self.assertEqual(before,revision(self.doc))

    def test_schema_and_loader_conformance_for_examples_and_animations(self):
        for folder in (ROOT/'examples').iterdir():
            if not (folder/'project.json').exists():continue
            manifest=json.loads((folder/'project.json').read_bytes())
            for key,schema in [('manifest','project-v1'),('definitions','content-v1'),('adventure','adventure-v1'),('graphics','art-v1'),('presentation','presentation-v1')]:
                if key!='manifest' and key not in manifest:continue
                value=json.loads((folder/('project.json' if key=='manifest' else manifest[key])).read_bytes())
                if key=='adventure':schema='adventure-v'+str(value['schema_version'])
                check(value,json.loads((ROOT/'schemas'/f'{schema}.schema.json').read_bytes()))
        image=dict(id='author-test:sprite',name='Animated sprite',kind='sprite',width=1,height=1,frames=[['ffffffff']],
                   animations={'walk':{'directions':[[{'frame':0,'ticks':4}]]}})
        schema=json.loads((ROOT/'schemas/art-v1.schema.json').read_bytes())['properties']['images']['items']
        check(image,schema)
        apply_batch(self.doc,self.request([dict(op='object.put',collection='images',value=image)]),save=True)
        for change in ({'kind':'icon'},{'frames':[['FFFFFFFF']]},{'animations':{'walk':{'directions':[[{'frame':0,'ticks':4}]]*2}}}):
            bad=dict(image,**change)
            with self.assertRaises(AuthoringError):check(bad,schema)
            with self.assertRaises(EditorError):apply_batch(self.doc,self.request([dict(op='object.put',collection='images',value=bad,mode='replace')],identity='invalid'))

    def test_creating_a_project_does_not_inherit_receipts(self):
        apply_batch(self.doc,self.request(),save=True)
        other=create_project(self.doc.root,self.root/'copy','new-author','New',TOOL)
        self.assertNotIn(AUTHORING_RECEIPTS,other.metadata)

    def test_construction_world_and_art_operations_share_editor_metadata(self):
        from event_editing import editor_data
        from world_editing import token
        from adventure_editing import composite
        from PIL import Image
        source=self.root/'tile.png';Image.new('RGBA',(16,16),(12,34,56,255)).save(source)
        ops=[dict(op='construction.style',value=dict(id='author-test:building',name='Depot',kind='Building',footprint=[[1,1],[1,1]],parts={})),
             dict(op='construction.draw',id='author-test:depot',map='beacon:wild',style='author-test:building',start=[3,3],end=[5,5],shape='Rectangle',stories=1),
             dict(op='map.paint',map='beacon:wild',tile='beacon:grass',start=[4,4]),
             dict(op='pattern.capture',map='beacon:wild',rect=[3,3,6,6],name='Depot block'),
             dict(op='world.create',name='Planet',width=8,height=8),
             dict(op='city.place',world='author-test:world',map='beacon:wild',at=[0,0]),
             dict(op='world.patch',world='author-test:world',at=[50,50],rows=[['beacon:water']]),
             dict(op='art.import',file=str(source),kind='tile',id='author-test:tile'),
             dict(op='art.clone',source='author-test:tile',id='author-test:tile-copy')]
        apply_batch(self.doc,self.request(ops),save=True)
        data=editor_data(self.doc);self.assertEqual(len(data['map_constructions']),1)
        self.assertEqual(len(data['map_patterns']),1)
        self.assertEqual(composite(self.doc.adventure['maps'][1])[4][4],'beacon:grass')
        apply_batch(self.doc,self.request([dict(op='construction.draw',id='author-test:depot',map='beacon:wild',style='author-test:building',start=[5,5],end=[6,5],stories=1)],identity='extend'))
        self.assertEqual(composite(self.doc.adventure['maps'][1])[4][4],'beacon:grass')
        images={i['id']:i for i in self.doc.art['images']}
        self.assertEqual(images['author-test:tile']['frames'],images['author-test:tile-copy']['frames'])

    def test_lua_import_forward_routes_and_input_hashes(self):
        source=self.root/'choice.lua';source.write_text("return game.command('author-test:done')\n")
        ops=[dict(op='script.import',id='author-test:script',file=str(source),target='choice.lua'),
             dict(op='object.put',collection='events',value=dict(id='author-test:lua',op='lua',script='author-test:script',routes=['author-test:done'],failure='author-test:done')),
             dict(op='object.put',collection='events',value=dict(id='author-test:done',op='end'))]
        request=self.request(ops);apply_batch(self.doc,request,save=True)
        self.assertEqual(revision(self.doc),revision(ProjectDocument(self.doc.root,TOOL)))
        source.write_text("return game.command('author-test:done') -- changed\n")
        with self.assertRaisesRegex(AuthoringError,'different content'):apply_batch(self.doc,request)

    def test_cli_create_stdin_and_exclusive_output(self):
        def cli(*args,input=None):
            result=subprocess.run([sys.executable,str(ROOT/'tools/author.py'),*map(str,args)],input=input,capture_output=True,text=True,timeout=20)
            return result.returncode,json.loads(result.stdout)
        request=self.request();code,result=cli('apply',self.doc.root,'--request','-','--dry-run',input=json.dumps(request))
        self.assertEqual(code,0,result);self.assertFalse(self.doc.dirty)
        request['expected_revision']='new';path=self.root/'new.commands.json';path.write_text(json.dumps(request))
        code,result=cli('create',self.root/'created','--template',self.doc.root,'--id','author-test','--title','Author test','--request',path)
        self.assertEqual(code,0,result)
        code,result=cli('create',self.root/'created','--id','author-test','--title','Author test')
        self.assertEqual(code,1);self.assertEqual(result['diagnostics'][0]['code'],'project.exists')

    def test_scenario_reports_real_assertion_failures_and_save_reload(self):
        from authoring_scenarios import run
        good=dict(format='btp-author-scenario-v1',steps=[dict(op='pages'),dict(op='checkpoint'),dict(op='assert',credits=2000,phase='exploration'),dict(op='capture')])
        result=run(self.doc,good,self.root/'route',ROOT/'build/btp-author-playtest')
        self.assertEqual(result['status'],'passed',result)
        bad=copy.deepcopy(good);bad['steps'][2]['credits']=999
        result=run(self.doc,bad,self.root/'broken',ROOT/'build/btp-author-playtest')
        self.assertEqual(result['status'],'failed');self.assertIn('Credit',result['diagnostics'][0]['message'])
        self.assertTrue((self.root/'broken/final.ppm').exists())
        with self.assertRaises(AuthoringError):run(self.doc,dict(good,expected_revision='0'*64),self.root/'stale',ROOT/'build/btp-author-playtest')

    def test_recorded_recipe_reproduces_the_playable_package(self):
        from author import parser,dispatch
        args=parser().parse_args(['create',str(self.root/'relay'),'--template',str(ROOT/'examples/adventure-demo'),
            '--id','relay-contract','--title','BattleTech - Relay Contract','--request',str(ROOT/'examples/authoring/relay-contract.commands.json')])
        result=dispatch(args);self.assertEqual(result['status'],'created')
        fresh=ProjectDocument(self.root/'relay',TOOL);shipped=ProjectDocument(ROOT/'examples/relay-contract',TOOL)
        self.assertEqual(revision(fresh),revision(shipped))
        self.assertEqual(fresh.adventure,shipped.adventure);self.assertEqual(fresh.art,shipped.art)


if __name__=='__main__':unittest.main()
