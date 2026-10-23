"""Suggestions are conservative evidence about dependencies, never test passes."""
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
from authoring_contract import AuthoringError
from authoring_service import detached,revision
from authoring_impact import analyse,capture_suite,verify_inputs
from authoring_scenarios import run_suite
from editor_model import ProjectDocument,encoded
from review_selection_demo import create,request,build
import authoring_review as review

TOOL=Path(os.environ.get('BTP_PROJECT_TOOL',ROOT/'build/btp-project'))
RUNNER=ROOT/'build/btp-author-playtest'


class ReviewSelection(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='btp-selection-');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.doc,self.suite=create(self.root/'fixture',TOOL)
        self.before=revision(self.doc)

    def prepare(self,kind='local',name='review'):
        folder=self.root/name
        record=review.prepare(self.doc,request(self.doc,kind),folder,visuals=False)
        self.assertEqual(record['status'],'ready',record)
        return folder

    def suggest(self,kind='local'):
        folder=self.prepare(kind)
        return folder,review.suggest_cases(folder,TOOL,self.suite)

    def test_local_shared_tiles_units_and_town_move(self):
        for kind,expected in [('local',['yard']),('tile',['range','world']),('unit',['yard','range','world']),('world',['world'])]:
            folder=self.prepare(kind,kind);result=review.suggest_cases(folder,TOOL,self.suite)
            self.assertEqual(result['suggested'],expected)
            self.assertFalse(result['full_suite_recommended'])
            self.assertTrue(all(c['test_status']=='not_run' for c in result['cases']))
            for case in result['cases']:
                if case['id'] in expected:self.assertTrue(case['reasons'])
            self.assertEqual(review.read_selection(folder,result['report'])['suggested'],expected)
        self.assertEqual(self.before,revision(self.doc));self.assertFalse(self.doc.dirty)

    def test_before_and_after_graphs_cover_removed_and_added_references(self):
        before=detached(self.doc);after=detached(self.doc)
        # A previously reachable object is still a dependency after a redirect.
        a=after.adventure
        a['maps'][-2]['entrances']=[dict(id='survey:extra',name='Extra',at=[18,18],event='survey:range-welcome')]
        result=analyse(before,after,json.loads(self.suite.read_bytes()),self.suite.parent)
        self.assertEqual(result['suggested'],['yard'])
        result=analyse(after,before,json.loads(self.suite.read_bytes()),self.suite.parent)
        self.assertEqual(result['suggested'],['yard'])
        yard=result['cases'][0]
        self.assertIn('adventure.events/survey:range-welcome',yard['dependencies'])

    def test_implicit_map_triggers_battle_hooks_and_image_dependencies(self):
        from authoring_impact import Graph
        doc=detached(self.doc);a=doc.adventure
        a['regions']=[dict(id='survey:zone',map='survey:yard',enter='survey:trigger')]
        a['events'].append(dict(id='survey:trigger',op='battle',encounter='survey:fight'))
        a['encounters']=[dict(id='survey:fight',map='survey:yard',enemies=[dict(definition='workshop:rook')])]
        a['combat_hooks']=[dict(id='survey:hook',encounter='survey:fight',event='survey:hook-event')]
        a['combat_groups']=[dict(id='survey:group',encounter='survey:fight',units=[dict(definition='survey:carrier')])]
        a['events'].append(dict(id='survey:hook-event',op='say',text='Hook text',next='survey:end'))
        doc.art['images']=[dict(id='survey:grass-image',frames=['not scanned as IDs'])]
        a['tiles'][-1]['sheet']='package:survey:grass-image'
        graph=Graph(doc);fixture=json.loads((self.suite.parent/'yard.commands.json').read_bytes())
        parents,unknown=graph.walk(json.loads((self.suite.parent/'yard.json').read_bytes()),fixture)
        self.assertFalse(unknown)
        for path in ('adventure.regions/survey:zone','adventure.combat_hooks/survey:hook','adventure.events/survey:hook-event',
                     'adventure.combat_groups/survey:group','content.mechs/survey:carrier','art.images/survey:grass-image'):
            self.assertIn(path,parents)

    def test_legacy_single_world_and_character_tiles_are_dependencies(self):
        from authoring_impact import Graph
        doc=detached(self.doc);a=doc.adventure
        a['schema_version']=1;a['tiles'][0]['key']='.'
        a['maps'][0]['rows']=['.'*16 for _ in range(16)]
        a['world']=a.pop('worlds')[0]
        parents,_=Graph(doc).walk(dict(steps=[dict(op='checkpoint')]),None)
        self.assertIn('adventure.world',parents);self.assertIn('adventure.tiles/beacon:grass',parents)

    def test_opaque_control_explicitly_recommends_full_suite(self):
        # Every opaque form is intentionally a fallback, not a guessed route.
        original=json.loads((self.suite.parent/'yard.json').read_bytes())
        for scenario in [dict(original,steps=[dict(op='input',action='space')]),
                         dict(original,checkpoint=dict(file='unused.btp',sha256='0'*64)),
                         dict(original,expected_revision='0'*64)]:
            (self.suite.parent/'yard.json').write_bytes(encoded(scenario))
            result=analyse(self.doc,self.doc,json.loads(self.suite.read_bytes()),self.suite.parent)
            self.assertTrue(result['full_suite_recommended']);self.assertEqual(len(result['suggested']),3)
            self.assertEqual(result['cases'][0]['classification'],'unknown')
        (self.suite.parent/'yard.json').write_bytes(encoded(original))
        a=detached(self.doc);a.adventure['events'][-2].update(op='lua',script='beacon:contract')
        result=analyse(a,a,json.loads(self.suite.read_bytes()),self.suite.parent)
        self.assertTrue(result['full_suite_recommended']);self.assertTrue(any('Lua' in u for u in result['cases'][0]['unknown']))
        fixture=json.loads((self.suite.parent/'yard.commands.json').read_bytes())
        fixture['operations'].append(dict(op='object.patch',collection='maps',id='survey:yard',changes=dict(name='Yard changed')))
        (self.suite.parent/'yard.commands.json').write_bytes(encoded(fixture))
        result=analyse(self.doc,self.doc,json.loads(self.suite.read_bytes()),self.suite.parent)
        self.assertIn('Fixture',result['cases'][0]['unknown'][0])

    def test_graph_budget_falls_back_to_full_suite(self):
        with patch('authoring_impact.MAX_EDGES',1):
            result=analyse(self.doc,self.doc,json.loads(self.suite.read_bytes()),self.suite.parent)
        self.assertTrue(result['full_suite_recommended']);self.assertEqual(len(result['suggested']),3)
        self.assertTrue(all(c['classification']=='unknown' for c in result['cases']))

    def test_actual_diffs_ignore_editor_only_but_include_shared_configuration(self):
        after=detached(self.doc);after.metadata['EDITOR.json']=encoded(dict(notes='new note'))
        result=analyse(self.doc,after,json.loads(self.suite.read_bytes()),self.suite.parent)
        self.assertEqual(result['suggested'],[]);self.assertEqual(result['editor_only_changes'],['editor.notes'])
        after.content['rules']['minimum_range']+=1
        result=analyse(self.doc,after,json.loads(self.suite.read_bytes()),self.suite.parent)
        self.assertEqual(len(result['suggested']),3)
        self.assertEqual(result['cases'][0]['reasons'][0]['path'],'content.rules')

    def test_retained_inputs_survive_external_edits_and_reject_tampering(self):
        folder,result=self.suggest()
        (self.suite.parent/'yard.json').write_bytes(b'not JSON any more')
        checked=review.check_candidate(folder,TOOL,runner=RUNNER,selection=result['report'],suggested=True)
        self.assertEqual(checked['status'],'passed');self.assertEqual(checked['runs_completed'],2)
        self.assertEqual(checked['unselected_cases'],['range','world'])
        data=json.loads(Path(checked['report']).read_bytes())
        self.assertEqual([r['seed'] for r in data['runs']],[11223583,2026])
        self.assertEqual(review.read(folder)['checks'][0]['revision'],result['revision'])
        retained=Path(result['report']).parent/'inputs/cases/yard/scenario.json'
        retained.write_bytes(encoded(dict(format='btp-author-scenario-v1',steps=[dict(op='checkpoint')])))
        with self.assertRaisesRegex(AuthoringError,'Retained suite input changed'):
            review.check_candidate(folder,TOOL,runner=RUNNER,selection=result['report'])

    def test_inputs_capture_imports_and_keep_basename(self):
        path=self.suite.parent/'a.lua';path.write_text('return "done"')
        fixture_path=self.suite.parent/'yard.commands.json';fixture=json.loads(fixture_path.read_bytes())
        fixture['operations'].append(dict(op='script.import',id='survey:script',file='a.lua',target='a.lua'))
        fixture_path.write_bytes(encoded(fixture))
        inputs=capture_suite(self.suite,self.root/'inputs');path.write_text('changed')
        verify_inputs(self.root,inputs)
        fixture=json.loads((self.root/'inputs/cases/yard/fixture.json').read_bytes())
        imported=self.root/'inputs/cases/yard'/fixture['operations'][-1]['file']
        self.assertEqual(imported.name,'a.lua');self.assertEqual(imported.read_text(),'return "done"')

    def test_reject_stale_candidate_base_selection_and_empty_subset(self):
        folder,result=self.suggest()
        other=self.prepare('tile','other')
        with self.assertRaisesRegex(AuthoringError,'exact proposal'):review.check_candidate(other,TOOL,runner=RUNNER,selection=result['report'])
        with self.assertRaisesRegex(AuthoringError,'No cases selected'):review.check_candidate(folder,TOOL,runner=RUNNER,selection=result['report'],case_ids=[])
        with self.assertRaisesRegex(AuthoringError,'empty selection'):
            run_suite(self.doc,json.loads(self.suite.read_bytes()),self.suite.parent,self.root/'empty',RUNNER,case_ids=[])
        for side in ('before','after'):
            path=folder/side/'adventure.json';data=path.read_bytes();changed=json.loads(data);changed['start']['credits']+=1
            path.write_bytes(encoded(changed))
            with self.assertRaisesRegex(AuthoringError,'changed'):review.check_candidate(folder,TOOL,runner=RUNNER,selection=result['report'])
            path.write_bytes(data)
        path=Path(result['report']);data=json.loads(path.read_bytes());data['suggested']=['world'];path.write_bytes(encoded(data))
        with self.assertRaisesRegex(AuthoringError,'selection changed'):review.check_candidate(folder,TOOL,runner=RUNNER,selection=path)

    def test_cancellation_retains_partial_suite_without_claiming_pass(self):
        folder,result=self.suggest()
        checked=review.check_candidate(folder,TOOL,runner=RUNNER,selection=result['report'],cancelled=lambda:True)
        self.assertEqual(checked['status'],'cancelled');self.assertEqual(checked['runs_completed'],0)
        self.assertEqual(review.read(folder)['checks'][0]['result']['status'],'cancelled')
        previous=len(review.read(folder)['selections'])
        with self.assertRaisesRegex(AuthoringError,'cancelled'):review.suggest_cases(folder,TOOL,self.suite,cancelled=lambda:True)
        self.assertEqual(len(review.read(folder)['selections']),previous)

    def test_full_and_selected_native_results_save_and_replay_match(self):
        result=build(self.root/'demonstration',TOOL,RUNNER)
        self.assertEqual(result['status'],'passed');self.assertEqual(result['full']['runs_completed'],5)
        self.assertEqual(result['selected']['runs_completed'],2)
        self.assertIsInstance(result['seconds_saved'],float)

    def test_cli_suggest_and_retained_explicit_selection(self):
        folder=self.prepare()
        command=[sys.executable,str(ROOT/'tools/author.py'),'review']
        p=subprocess.run([*command,'suggest',str(folder),'--suite',str(self.suite),'--validator',str(TOOL)],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr);result=json.loads(p.stdout)
        p=subprocess.run([*command,'check',str(folder),'--selection',os.path.relpath(result['report']),'--case','range','--validator',str(TOOL),'--runner',str(RUNNER)],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr);checked=json.loads(p.stdout)
        self.assertEqual(checked['selected_cases'],['range']);self.assertEqual(checked['unselected_cases'],['yard','world'])

    def test_modular_source_review_runs_fixture_cases_at_retained_revision(self):
        from campaign_source import convert
        convert(self.doc,self.root/'source')
        source=ProjectDocument(self.root/'source',TOOL);folder=self.root/'source-review'
        record=review.prepare(source,request(source),folder,visuals=False)
        self.assertEqual(record['status'],'ready',record)
        result=review.suggest_cases(folder,TOOL,self.suite)
        self.assertEqual(result['suggested'],['yard'])
        checked=review.check_candidate(folder,TOOL,runner=RUNNER,selection=result['report'],suggested=True)
        self.assertEqual(checked['status'],'passed');self.assertEqual(checked['revision'],record['result_revision'])
        self.assertEqual(revision(ProjectDocument(self.root/'source',TOOL)),record['base_revision'])

    def test_input_capture_has_no_reserved_case_names_and_rejects_duplicate_seeds(self):
        suite=json.loads(self.suite.read_bytes());suite['cases'][0]['id']='source'
        self.suite.write_bytes(encoded(suite));inputs=capture_suite(self.suite,self.root/'inputs');verify_inputs(self.root,inputs)
        suite['cases'][0]['seeds']=[1,1];self.suite.write_bytes(encoded(suite))
        with self.assertRaisesRegex(AuthoringError,'repeats a seed'):capture_suite(self.suite,self.root/'duplicate-seeds')


if __name__=='__main__':unittest.main()
