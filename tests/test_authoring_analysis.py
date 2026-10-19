"""Report broken missions using real collision, not only JSON references."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from authoring_analysis import analyze,graph_checks
from authoring_service import revision
from editor_model import ProjectDocument,create_project
from adventure_editing import paint
from world_editing import token
TOOL=ROOT/'build/btp-project';ANALYZER=ROOT/'build/btp-author-analyze'


class MissionChecks(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='btp-lint-');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.doc=create_project(ROOT/'examples/beacon-demo',self.root/'game','lint-test','Lint test',TOOL)
    def check(self):return analyze(self.doc,ANALYZER)
    def test_known_route_native_checks_are_read_only(self):
        before=self.doc.files();result=self.check()
        self.assertEqual(result['status'],'checked');self.assertIsNotNone(result['navigation'])
        self.assertEqual(result['navigation']['maps_checked'],2)
        self.assertGreater(result['navigation']['standable_positions_reached'],100)
        self.assertEqual(before,self.doc.files());self.assertEqual(len(self.doc.undo_stack),0)
    def test_closed_room_has_unreachable_door_with_location(self):
        a=copy.deepcopy(self.doc.adventure);scene=a['maps'][0]
        floor=token(next(t for t in a['tiles'] if t['terrain']=='clear'));wall=token(next(t for t in a['tiles'] if t['terrain']=='wall'))
        scene['rows']=[floor*32 for _ in range(24)];scene['overlays']=[]
        for y in range(4,11):
            for x in range(4,11):
                if x in (4,10) or y in (4,10):paint(scene,0,x,y,wall)
        end=next(e['id'] for e in a['events'] if e['op']=='end')
        scene['entrances'].append(dict(id='lint-test:sealed',name='Sealed depot',at=[14,14],event=end))
        self.doc.replace_adventure(a);self.doc.validate()
        result=self.check();p=next(p for p in result['diagnostics'] if p.get('object_id')=='lint-test:sealed')
        self.assertEqual(p['code'],'entrance.unreachable');self.assertEqual(p['location']['at'],[14,14])
        self.assertEqual(p['location']['coordinate_space'],'movement')
    def test_enemy_terrain_and_friendly_overlap_are_reported(self):
        a=copy.deepcopy(self.doc.adventure);battle=a['encounters'][0];scene=next(m for m in a['maps'] if m['id']==battle['map'])
        wall=token(next(t for t in a['tiles'] if t['terrain']=='wall'));ex,ey=battle['enemies'][0]['at']
        paint(scene,0,ex//2,ey//2,wall);self.doc.replace_adventure(a)
        result=self.check();self.assertTrue(any('enemy spawn blocked' in p['message'] for p in result['diagnostics']));self.assertEqual(result['status'],'failed')
        a=copy.deepcopy(a);battle=a['encounters'][0];battle['enemies'][0]['at']=[battle['party_at'][0],battle['party_at'][1]-2]
        self.doc.replace_adventure(a);self.doc.validate()
        self.assertIn('deployment.overlap',{p['code'] for p in self.check()['diagnostics']})
    def test_outer_member_blocks_compact_formation(self):
        # Only the second mech touches the new wall. The leader's two ground
        # tiles are clear, so a leader-only approximation would miss this.
        a=copy.deepcopy(self.doc.adventure);a['start']['party'].append(dict(person='beacon:mira',mech=a['start']['party'][0]['mech']))
        battle=a['encounters'][0];scene=next(m for m in a['maps'] if m['id']==battle['map'])
        floor=token(next(t for t in a['tiles'] if t['terrain']=='clear'));wall=token(next(t for t in a['tiles'] if t['terrain']=='wall'))
        scene['rows']=[floor*32 for _ in range(24)];scene['overlays']=[]
        from scene_tools import formation_data
        formation=formation_data(self.doc,{})['mechs'];x,y=battle['party_at'];dx,dy=formation[1]
        cx,cy=(x+dx)//2+1,(y+dy)//2
        first={(x+formation[0][0])//2,(x+formation[0][0])//2+1}
        self.assertNotIn(cx,first);paint(scene,0,cx,cy,wall);self.doc.replace_adventure(a);self.doc.validate()
        result=self.check();self.assertIn('deployment.blocked',{p['code'] for p in result['diagnostics']})
    def test_sync_cycle_and_unconnected_branch_are_distinguished(self):
        a=copy.deepcopy(self.doc.adventure);flag=a['flags'][0]
        a['events'] += [dict(id='lint-test:cycle-a',op='flag',flag=flag,value=1,next='lint-test:cycle-b'),
                        dict(id='lint-test:cycle-b',op='flag',flag=flag,value=0,next='lint-test:cycle-a'),
                        dict(id='lint-test:orphan',op='end')]
        a['start']['event']='lint-test:cycle-a';self.doc.replace_adventure(a)
        result=graph_checks(self.doc);codes={p['code'] for p in result['diagnostics']}
        self.assertIn('event.non_yielding_cycle',codes);self.assertIn('event.unreachable',codes)
        cycle=next(p for p in result['diagnostics'] if p['code']=='event.non_yielding_cycle')
        self.assertEqual(cycle['severity'],'error');self.assertEqual(cycle['events'],['lint-test:cycle-a','lint-test:cycle-b'])
    def test_objective_reports_its_only_sealed_completion_entrance(self):
        a=copy.deepcopy(self.doc.adventure);scene=a['maps'][0]
        # This fixture has only explicit flag writers. The template's optional
        # Lua node would correctly keep objective access classified unknown.
        a['events']=[dict(id=e['id'],op='end') if e['op']=='lua' else e for e in a['events']]
        floor=token(next(t for t in a['tiles'] if t['terrain']=='clear'));wall=token(next(t for t in a['tiles'] if t['terrain']=='wall'))
        scene['rows']=[floor*32 for _ in range(24)];scene['overlays']=[]
        for y in range(4,11):
            for x in range(4,11):
                if x in (4,10) or y in (4,10):paint(scene,0,x,y,wall)
        a['flags'].extend(['lint-test:active','lint-test:complete'])
        end=next(e['id'] for e in a['events'] if e['op']=='end')
        a['events'].append(dict(id='lint-test:goal',op='flag',flag='lint-test:complete',value=1,next=end))
        scene['entrances'].append(dict(id='lint-test:sealed-goal',name='Sealed goal',at=[14,14],event='lint-test:goal'))
        a.setdefault('objectives',[]).append(dict(id='lint-test:objective',title='Sealed objective',text='Reach the sealed room.',active='lint-test:active',complete='lint-test:complete'))
        self.doc.replace_adventure(a);result=self.check()
        finding=next(p for p in result['diagnostics'] if p['code']=='objective.inaccessible')
        self.assertEqual(finding['object_id'],'lint-test:objective');self.assertEqual(finding['blocked_entrances'],['lint-test:sealed-goal'])
    def test_static_only_and_missing_runtime_report_unchecked_navigation(self):
        static=analyze(self.doc,ANALYZER,navigation=False)
        self.assertIsNone(static['navigation']);self.assertIn('navigation.not_run',{p['code'] for p in static['diagnostics']})
        missing=analyze(self.doc,self.root/'missing-tool')
        self.assertIn('navigation.unavailable',{p['code'] for p in missing['diagnostics']})
    def test_reports_have_content_revision_and_preserve_existing_output(self):
        output=self.root/'lint.json';result=analyze(self.doc,ANALYZER,output=output)
        self.assertEqual(result['revision'],revision(self.doc));self.assertTrue(output.is_file())
        with self.assertRaises(FileExistsError):analyze(self.doc,ANALYZER,output=output)


if __name__=='__main__':unittest.main()
