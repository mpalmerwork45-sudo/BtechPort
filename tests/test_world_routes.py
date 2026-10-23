"""World routes exercise ordinary inputs; no saves or game state are patched."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from world_route_demo import create,journey
from authoring_scenarios import run,SCHEMA
from authoring_analysis import analyze
from authoring_contract import check,AuthoringError
from editor_model import encoded
from editor_problems import target
from campaign_source import convert,build

TOOL=ROOT/'build/btp-project'
RUNNER=Path(os.environ.get('BTP_ROUTE_RUNNER',ROOT/'build/btp-author-playtest'))
ANALYZER=Path(os.environ.get('BTP_ROUTE_ANALYZER',ROOT/'build/btp-author-analyze'))


def step_mode(amount):
    return [dict(op='input',action=a) for a in ['menu','down','accept','accept']+['down']*{2:1,4:2}[amount]+['accept']]


class WorldRoutes(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='btp-world-routes-');self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.doc=create(self.root/'game',TOOL)

    def route(self,steps,name='route',ok=True):
        scenario=steps if isinstance(steps,dict) else dict(format='btp-author-scenario-v1',steps=steps)
        result=run(self.doc,scenario,self.root/name,RUNNER)
        self.assertEqual(result['status']=='passed',ok,result)
        return result,json.loads(Path(result['report']).read_bytes())

    def test_two_planets_all_members_checkpoints_and_plain_input_replay(self):
        before=self.doc.files();result,report=self.route(journey())
        self.assertEqual(self.doc.files(),before)
        state=result['result']['state'];self.assertEqual(state['world'],'survey:aster')
        self.assertEqual(len(state['units']),4);self.assertTrue(state['formation_compact'])
        self.assertEqual(sum(p['on_foot'] for p in state['party']),2)
        self.assertGreater(state['discovery']['survey:boreal']['seen_cells'],9)
        self.assertLess(state['discovery']['survey:aster']['seen_cells'],128)
        world_steps=[s for s in report['steps'] if s['state']['world_at']==[138,64]]
        self.assertTrue(any(s['state']['map']=='world:planet-1-sector-1-0' for s in world_steps))
        inputs=self.root/'route/replay.actions';replayed=self.root/'replayed.btp'
        p=subprocess.run([str(ROOT/'build/btech-headless'),'--project',str(self.doc.root),'--replay',str(inputs),'--save',str(replayed)],capture_output=True,text=True,timeout=15)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(replayed.read_bytes(),(self.root/'route'/result['result']['save']).read_bytes())

    def test_source_project_uses_same_world_routes(self):
        self.doc=convert(self.doc,self.root/'sources');before=self.doc.source_files()
        build(self.doc,self.root/'compiled')
        self.route(journey());self.assertEqual(self.doc.source_files(),before)

    def test_two_and_four_step_keys_across_sector_and_door(self):
        for steps in (2,4):
            route=journey();route['steps']=step_mode(steps)+route['steps']
            # Exact cursor targets must fit the chosen stride; the planner
            # never changes settings behind the caller's back.
            for s in route['steps']:
                for key in ('at','world_at'):
                    if key in s:s[key]=[4*((v+3)//4) for v in s[key]]
            self.route(route,str(steps))

    def test_city_tiles_override_water_for_vehicle_and_cross_sector_door(self):
        self.route([dict(op='walk',map='survey:port',at=[22,12]),
            dict(op='assert',world_at=[142,44],formation='compact'),
            dict(op='walk',entrance='survey:shuttle'),dict(op='checkpoint'),dict(op='enter'),
            dict(op='assert',world='survey:boreal',formation='compact')])

    def test_blocked_world_and_map_destinations_have_correct_diagnostic_locations(self):
        a=copy.deepcopy(self.doc.adventure)
        a['worlds'][0]['patches']=[dict(at=[50,20],rows=[['beacon:wall']*8 for _ in range(8)])]
        a['maps'][1]['rows'][5][10]='beacon:wall';self.doc.replace_adventure(a)
        result,_=self.route([dict(op='walk',world='survey:aster',at=[106,46])],ok=False)
        problem=result['diagnostics'][0];self.assertEqual(problem['code'],'route.unreachable')
        self.assertEqual(target(self.doc,problem)['world'],'survey:aster');self.assertEqual(problem['location']['at'],[106,46])
        result,_=self.route([dict(op='walk',map='survey:port',at=[20,12])],'city',ok=False)
        self.assertEqual(result['diagnostics'][0]['location'],dict(map='survey:port',at=[20,12],coordinate_space='movement'))

    def test_budgets_missing_targets_and_transfer_requirements_are_distinct(self):
        for name,step,code in [('budget',dict(world='survey:aster',at=[180,80],max_positions=1),'route.budget'),
                               ('planet',dict(entrance='survey:return'),'route.transfer_required'),
                               ('missing',dict(world='survey:missing',at=[50,50]),'route.target_missing'),
                               ('edge',dict(world='survey:aster',at=[600,600]),'route.invalid')]:
            with self.subTest(name=name):
                result,_=self.route([dict(op='walk',**step)],name,ok=False)
                self.assertEqual(result['diagnostics'][0]['code'],code);self.assertEqual(result['result']['ticks'],0)

    def test_outer_members_prevent_a_leader_only_route_through_narrow_gap(self):
        a=copy.deepcopy(self.doc.adventure)
        a['worlds'][0]['patches']=[dict(at=[48,0],rows=[['beacon:grass' if y==25 else 'beacon:wall'] for y in range(64)])]
        self.doc.replace_adventure(a)
        steps=[dict(op='walk',world='survey:aster',at=[112,52]),dict(op='assert',world_at=[112,52],formation='compact')]
        result,_=self.route(steps,ok=False);self.assertEqual(result['diagnostics'][0]['code'],'route.unreachable')
        a['start']['party']=a['start']['party'][:1];self.doc.replace_adventure(a)
        self.route(steps,'leader-only')

    def test_multi_step_collision_stops_before_outer_mech_hits_building(self):
        # Independent sample formation: third mech is at cursor+(4,-2).
        # Its second ground tile reaches world (21,25) on half-step four.
        a=copy.deepcopy(self.doc.adventure);a['maps'][0]['rows'][9][13]='beacon:wall';self.doc.replace_adventure(a)
        result,_=self.route(step_mode(4)+[dict(op='input',action='right'),
            dict(op='assert',world_at=[35,52],formation='compact'),dict(op='checkpoint'),
            dict(op='walk',world='survey:aster',at=[55,64]),dict(op='assert',world_at=[55,64],formation='compact')])
        self.assertEqual(result['result']['state']['world_at'],[55,64])

    def test_region_interrupt_does_not_acknowledge_or_teleport(self):
        a=copy.deepcopy(self.doc.adventure)
        a['events'].append(dict(id='survey:stop',op='say',text='Survey checkpoint.',next='survey:end'))
        a['regions']=[dict(id='survey:region',name='Survey line',map='survey:home',rect=[10,0,1,16],repeat='once',enter='survey:stop')]
        self.doc.replace_adventure(a)
        result,_=self.route([dict(op='walk',world='survey:aster',at=[50,52])],ok=False)
        self.assertEqual(result['diagnostics'][0]['code'],'route.interrupted')
        self.assertEqual(result['result']['state']['phase'],'text')
        self.assertEqual(result['diagnostics'][0]['location']['map'],'survey:home')
        self.assertLess(result['result']['state']['world_at'][0],50)

    def test_world_lint_crosses_town_edges_and_reports_sealed_entrance(self):
        before=self.doc.files();clean=analyze(self.doc,ANALYZER)
        self.assertEqual(clean['diagnostics'],[]);self.assertTrue(all(w['complete'] for w in clean['navigation']['worlds']))
        self.assertEqual(self.doc.files(),before)
        a=copy.deepcopy(self.doc.adventure);town=a['maps'][1]
        for y in range(6,15):
            for x in range(1,10):
                if x in (1,9) or y in (6,14):town['rows'][y][x]='beacon:wall'
        self.doc.replace_adventure(a);bad=analyze(self.doc,ANALYZER)
        p=next(p for p in bad['diagnostics'] if p.get('object_id')=='survey:shuttle')
        self.assertEqual(p['code'],'entrance.unreachable');self.assertEqual(p['location']['map'],'survey:port')

    def test_maximum_size_world_route_is_targeted_and_lint_budget_is_unknown(self):
        a=copy.deepcopy(self.doc.adventure);a['worlds']=a['worlds'][:1]
        a['worlds'][0]['pieces']=[['survey:plain']*128 for _ in range(128)]
        a['worlds'][0]['cities'].append('survey:landing');a['maps'][2]['origin']=[960,960]
        self.doc.replace_adventure(a)
        result,report=self.route([dict(op='walk',map='survey:landing',at=[16,20]),
            dict(op='assert',world='survey:aster',world_at=[1936,1940],formation='compact'),dict(op='checkpoint')])
        self.assertLess(report['steps'][0]['navigation']['examined'],10000)
        lint=analyze(self.doc,ANALYZER);self.assertIn('navigation.budget',{p['code'] for p in lint['diagnostics']})
        self.assertFalse(lint['navigation']['worlds'][0]['complete'])
        self.assertNotIn('entrance.unreachable',{p['code'] for p in lint['diagnostics']})

    def test_strict_scenario_schema_and_discovery_failure(self):
        for bad in [dict(op='walk',world='survey:aster',at=[1]),dict(op='walk',map='survey:port',world='survey:aster',at=[2,4]),
                    dict(op='walk',world='survey:aster',at=[1,2],max_positions=1048577),dict(op='walk',entrance='survey:shuttle',at=[1,2])]:
            with self.assertRaises(AuthoringError):check(dict(format='btp-author-scenario-v1',steps=[bad]),SCHEMA)
        result,_=self.route([dict(op='assert',discovered=dict(world='survey:boreal',at=[16,24],seen=1))],ok=False)
        self.assertIn('discovery assertion',result['result']['message'])


if __name__=='__main__':unittest.main()
