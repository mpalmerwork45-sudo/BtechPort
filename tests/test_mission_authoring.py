"""AI6 mission definitions are shared by CLI, editor, schemas and C loader."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from editor_model import create_project,EditorError
from authoring_contract import check,AuthoringError,diagnostic
from authoring_service import apply_batch,revision
from authoring_inspect import summary,query
from authoring_analysis import graph_checks,objective_access
from editor_dependencies import usages,remove
from editor_problems import target
from adventure_editing import event_template
from mission_demo import build as build_demo,adventure as demo_adventure
TOOL=ROOT/'build/btp-project'


class MissionAuthoring(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.doc=create_project(ROOT/'examples/beacon-demo',Path(self.tmp.name)/'game','mission-test','Mission test',TOOL)
        a=copy.deepcopy(self.doc.adventure);end=next(e['id'] for e in a['events'] if e['op']=='end')
        a['variables']=[dict(id='mission-test:count',name='Data caches',type='counter',initial=0,maximum=2),
                        dict(id='mission-test:survey',name='Surveyed',type='boolean',initial=0)]
        a['regions']=[dict(id='mission-test:landing',name='Landing',map=a['maps'][0]['id'],rect=[2,2,3,3],repeat='always',enter='mission-test:check')]
        a['objectives']=[dict(id='mission-test:extract',title='Extract',text='Return with the data.',initial='active')]
        a['events'] += [
            dict(id='mission-test:check',op='check',match='all',conditions=[
                dict(kind='variable',id='mission-test:count',compare='ge',value=2),
                dict(kind='objective',id='mission-test:extract',compare='eq',value='active'),
                dict(kind='region',id='mission-test:landing',compare='eq',value=1)],then='mission-test:finish',**{'else':end}),
            dict(id='mission-test:finish',op='objective',objective='mission-test:extract',state='complete',next=end,failure=end)]
        self.doc.replace_adventure(a);self.doc.validate();self.base=copy.deepcopy(a)

    def test_schema_native_roundtrip_and_capacity(self):
        schema=json.loads((ROOT/'schemas/adventure-v1.schema.json').read_bytes());check(self.base,schema)
        self.doc.save();data=summary(self.doc,TOOL)
        self.assertEqual(data['capacity']['variables']['used'],2)
        self.assertEqual(data['capacity']['regions']['limit'],32)
        self.assertEqual(query(self.doc,'objects','regions')['items'][0]['id'],'mission-test:landing')
        template=event_template(self.doc,'variable');self.assertEqual(template['variable'],'mission-test:count')
        self.assertEqual(event_template(self.doc,'objective')['objective'],'mission-test:extract')
        self.assertEqual(event_template(self.doc,'check')['match'],'all')

    def test_invalid_types_bounds_and_references(self):
        def edit(collection,index,key,value):
            a=copy.deepcopy(self.base);a[collection][index][key]=value;return a
        cases=[
            edit('variables',0,'initial',3),edit('variables',0,'maximum',1000001),
            edit('variables',1,'initial',2),edit('variables',0,'type','string'),
            edit('regions',0,'rect',[31,23,3,3]),edit('regions',0,'rect',[1,1,0,2]),
            edit('regions',0,'rect',[1,1,2,2,2]),edit('regions',0,'repeat','sometimes'),
            edit('regions',0,'enter','mission-test:missing'),edit('regions',0,'map','mission-test:missing'),
            edit('objectives',0,'initial','finished')]
        for a in cases:
            with self.subTest(a=a.get('variables')):
                self.doc.replace_adventure(a)
                with self.assertRaises(EditorError):self.doc.validate()

    def test_bad_commands_and_conditions(self):
        end=self.base['events'][0]['id']
        cases=[
            dict(op='variable',variable='mission-test:survey',action='add',value=1,once=0,next=end,failure=end),
            dict(op='variable',variable='mission-test:count',action='add',value=3,once=0,next=end,failure=end),
            dict(op='variable',variable='mission-test:count',action='subtract',value=1,once=2,next=end,failure=end),
            dict(op='check',match='all',conditions=[],then=end,**{'else':end}),
            dict(op='check',match='all',conditions=[dict(kind='variable',id='mission-test:survey',compare='gt',value=0)],then=end,**{'else':end}),
            dict(op='check',match='all',conditions=[dict(kind='objective',id='mission-test:extract',compare='eq',value='broken')],then=end,**{'else':end}),
            dict(op='check',match='all',conditions=[dict(kind='region',id='missing:region',compare='eq',value=1)],then=end,**{'else':end})]
        for event in cases:
            with self.subTest(event=event):
                a=copy.deepcopy(self.base);a['events'].append(dict(id='mission-test:invalid',**event))
                self.doc.replace_adventure(a)
                with self.assertRaises(EditorError):self.doc.validate()

    def test_capacity_and_duplicate_ids_are_bounded(self):
        for collection in ('variables','regions'):
            for duplicate in (False,True):
                a=copy.deepcopy(self.base)
                if duplicate:a[collection].append(copy.deepcopy(a[collection][0]))
                else:a[collection]=[dict(a[collection][0],id=f'mission-test:item-{i}') for i in range(33)]
                self.doc.replace_adventure(a)
                with self.assertRaises(EditorError):self.doc.validate()

    def test_condition_references_protect_deletion(self):
        refs=usages(self.doc,'mission-test:count')
        self.assertTrue(any(r.path[-1]=='id' and r.asset=='mission-test:check' for r in refs))
        with self.assertRaisesRegex(EditorError,'used in'):remove(self.doc,'mission-test:count')
        with self.assertRaisesRegex(EditorError,'used in'):remove(self.doc,'mission-test:extract')
        self.assertEqual(self.doc.adventure,self.base)

    def test_commands_are_atomic_and_undoable(self):
        request=dict(api_version=1,request_id='mission-state-change',project_id='mission-test',expected_revision=revision(self.doc),
                     label='Expand cache objective',scope=['adventure.variables'],operations=[
                         dict(op='object.patch',collection='variables',id='mission-test:count',changes={'maximum':3})])
        apply_batch(self.doc,request);self.assertEqual(self.doc.adventure['variables'][0]['maximum'],3)
        self.doc.undo();self.assertEqual(self.doc.adventure,self.base)
        request.update(request_id='bad-count',expected_revision=revision(self.doc))
        request['operations'][0]['changes']['maximum']=0
        with self.assertRaises(EditorError):apply_batch(self.doc,request)
        self.assertEqual(self.doc.adventure,self.base)

    def test_region_roots_and_explicit_objective_analysis(self):
        findings=graph_checks(self.doc)['diagnostics']
        self.assertFalse(any(d.get('object_id') in ('mission-test:check','mission-test:finish','mission-test:extract') for d in findings))
        self.assertEqual(objective_access(self.doc,[]),[])
        a=copy.deepcopy(self.base);a['events'][-1]['state']='failed';self.doc.replace_adventure(a)
        self.assertIn('objective.completion_missing',{d['code'] for d in graph_checks(self.doc)['diagnostics']})

    def test_error_navigation_chooses_entrance_not_outer_map(self):
        scene=self.base['maps'][1];door=scene['entrances'][0]
        message=f"/tmp/validation/adventure.json: $.maps[{scene['id']}].entrances[{door['id']}]: entrance must be on accessible ground in front of the building"
        problem=diagnostic(Exception(message));result=target(self.doc,problem)
        self.assertEqual(result['collection'],'entrances');self.assertEqual(result['id'],door['id'])
        self.assertEqual(result['map'],scene['id']);self.assertEqual(result['at'],door['at'])
        self.assertIsNone(target(self.doc,dict(message='Unknown free-text error')))

    def test_mixed_legacy_and_state_objectives(self):
        a=copy.deepcopy(self.base)
        a['objectives'].append(dict(id='mission-test:legacy',title='Legacy',text='Uses flags.',active=a['flags'][0],complete=a['flags'][1]))
        self.doc.replace_adventure(a);self.doc.validate()
        e=event_template(self.doc,'objective');e.update(objective='mission-test:legacy')
        a['events'].append(e);self.doc.replace_adventure(a)
        with self.assertRaisesRegex(EditorError,'state-based objective'):self.doc.validate()

    def test_reproducible_example(self):
        generated=build_demo(Path(self.tmp.name)/'reproduced',TOOL)
        expected=json.loads((ROOT/'examples/argent-recovery/adventure.json').read_bytes())
        self.assertEqual(generated.adventure,expected)
        check(expected,json.loads((ROOT/'schemas/adventure-v2.schema.json').read_bytes()))
        with self.assertRaisesRegex(ValueError,'new directory'):build_demo(generated.root,TOOL)


if __name__=='__main__':unittest.main()
