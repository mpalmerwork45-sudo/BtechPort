"""Shared-loader and ordinary-input checks for mission combat authoring."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from editor_model import ProjectDocument,create_project,EditorError
from authoring_contract import check
from authoring_service import apply_batch,revision
from authoring_inspect import summary
from authoring_analysis import graph_checks
from authoring_scenarios import run
from editor_dependencies import remove,usages
from combat_mission_demo import build
from adventure_editing import event_template

TOOL=ROOT/'build/btp-project';PLAYER=ROOT/'build/btp-author-playtest'
SETTINGS={k:ROOT/p for k,p in [('data','Original DOS'),('dialogue-data','work/talk-data.bin'),('combat-data','work/combat-data.bin'),('world-data','work/world-data.bin')]}


class CombatMissions(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.doc=create_project(ROOT/'examples/cairn-passage',self.root/'game','combat-test','Combat tests',TOOL)
        self.base=copy.deepcopy(self.doc.adventure)

    def tearDown(self):self.tmp.cleanup()

    def test_loader_schema_capabilities_and_templates(self):
        self.doc.validate();check(self.base,json.loads((ROOT/'schemas/adventure-v2.schema.json').read_bytes()))
        capacities=summary(self.doc,TOOL)['capacity']
        self.assertEqual(capacities['combat_groups']['limit'],16);self.assertEqual(capacities['combat_hooks']['limit'],32)
        self.assertEqual(event_template(self.doc,'reinforce')['radius'],2)
        self.assertEqual(event_template(self.doc,'battle_end')['result'],'win')

    def test_limits_references_and_hook_routes(self):
        cases=[]
        def change(collection,index,key,value):
            a=copy.deepcopy(self.base);a[collection][index][key]=value;cases.append(a)
        change('combat_groups',0,'encounter','absent:encounter')
        change('combat_groups',0,'affiliation','maybe')
        change('combat_groups',0,'reserve',2)
        change('combat_groups',0,'units',[])
        change('combat_groups',0,'units',[copy.deepcopy(self.base['combat_groups'][0]['units'][0]) for _ in range(12)])
        change('combat_hooks',1,'round',0)
        change('combat_hooks',1,'every',65536)
        change('combat_hooks',0,'when','tick')
        change('combat_hooks',0,'event','cairn:escort-battle')
        change('combat_hooks',3,'group','cairn:transport')
        for collection,limit in [('combat_groups',16),('combat_hooks',32)]:
            a=copy.deepcopy(self.base);a[collection]=[dict(a[collection][0],id=f'test:entry-{i}') for i in range(limit+1)];cases.append(a)
        for a in cases:
            with self.subTest(a=a):
                self.doc.replace_adventure(a)
                with self.assertRaises(EditorError):self.doc.validate()

    def test_vehicle_waypoint_and_terrain_validation(self):
        for points in ([[40,24]],[[255,0]],[[20,30] for _ in range(17)]):
            a=copy.deepcopy(self.base);a['combat_groups'][3]['units'][0]['waypoints']=points
            self.doc.replace_adventure(a)
            with self.assertRaises(EditorError):self.doc.validate()
        a=copy.deepcopy(self.base);a['tiles'].append(dict(id='test:water',sheet='chi:land',graphic=0,terrain='water',mini_color=1))
        for y in range(6,10):
            for x in range(26,31):a['maps'][2]['rows'][y][x]='test:water'
        a['combat_groups'][3]['units'][0]['waypoints']=[[56,14]];self.doc.replace_adventure(a)
        with self.assertRaisesRegex(EditorError,'terrain'):self.doc.validate()
        a['combat_groups'][3]['units'][0]['definition']='vehicles:pegasus';self.doc.replace_adventure(a);self.doc.validate()

    def test_survival_condition_schema_and_graph_roots(self):
        warnings=graph_checks(self.doc)['diagnostics']
        ids={'cairn:defence-start','cairn:incoming','cairn:transport-death','cairn:transport-arrived'}
        self.assertFalse(any(d.get('object_id') in ids and d['code']=='event.unreachable' for d in warnings))
        self.assertTrue(any(u.asset=='cairn:transport-arrived' for u in usages(self.doc,'cairn:transport')))
        with self.assertRaisesRegex(EditorError,'used in'):remove(self.doc,'cairn:transport')

    def test_atomic_commands_and_undo(self):
        request=dict(api_version=1,request_id='change-timer',project_id='combat-test',expected_revision=revision(self.doc),
            label='Change defence timer',scope=['adventure.combat_hooks'],operations=[dict(op='object.patch',collection='combat_hooks',id='cairn:relay-timer',changes={'round':6})])
        apply_batch(self.doc,request);self.assertEqual(self.doc.adventure['combat_hooks'][4]['round'],6)
        self.doc.undo();self.assertEqual(self.doc.adventure,self.base)
        request.update(request_id='bad-timer',expected_revision=revision(self.doc));request['operations'][0]['changes']['round']=0
        with self.assertRaises(EditorError):apply_batch(self.doc,request)
        self.assertEqual(self.doc.adventure,self.base)

    def test_tracked_wheeled_hover_routes(self):
        scenario=json.loads((ROOT/'examples/authoring/cairn/escort.json').read_bytes())
        for vehicle in ('galleon','skulker','pegasus'):
            a=copy.deepcopy(self.base);a['combat_groups'][3]['units'][0]['definition']='vehicles:'+vehicle
            self.doc.replace_adventure(a);self.doc.save()
            result=run(self.doc,scenario,self.root/vehicle,PLAYER,SETTINGS)
            self.assertEqual(result['status'],'passed',result)
            report=json.loads(Path(result['report']).read_bytes())
            self.assertEqual(report['result']['state']['combat_groups']['cairn:transport']['arrived'],1)

    def test_reproducible_game(self):
        doc=build(self.root/'reproduced',TOOL)
        expected=ProjectDocument(ROOT/'examples/cairn-passage',TOOL)
        self.assertEqual(doc.adventure,expected.adventure);self.assertEqual(doc.content['mechs'],expected.content['mechs'])
        with self.assertRaisesRegex(ValueError,'new directory'):build(doc.root,TOOL)


if __name__=='__main__':unittest.main()
