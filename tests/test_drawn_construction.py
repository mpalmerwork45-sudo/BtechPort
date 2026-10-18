"""Drawn footprints must rebuild safely and survive as editable game content."""
import copy,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from editor_model import create_project,ProjectDocument,EditorError
from construction_editing import new_profile,prepare_road,draw_road
from tile_editing import metadata
from map_construction import new_object,paint_footprint,projection,commit,objects,overlay_index,commit_tiles
from adventure_editing import composite,paint


class DrawnConstructionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.doc=create_project(ROOT/'examples/beacon-demo',Path(self.tmp.name)/'game','drawn','Drawn',ROOT/'build/btp-project')
        from world_editing import upgrade
        # A blank authoring fixture avoids intentionally covering a template
        # doorway while testing arbitrary footprints.
        a=copy.deepcopy(self.doc.adventure);upgrade(a);scene=a['maps'][0]
        ground=next(t['id'] for t in a['tiles'] if t['terrain']=='clear')
        scene.update(overlays=[],entrances=[],rows=[[ground]*32 for _ in range(24)])
        a['start']['at']=[60,44]
        for event in a['events']:
            if event['op']=='transfer' and event['map']==scene['id']:event['at']=[60,44]
        self.doc.replace_adventure(a)
        identity=new_profile(self.doc)
        self.style=next(p for p in metadata(self.doc)['construction_sets'] if p['id']==identity)

    def record(self,identity):return next(o for o in objects(self.doc,self.doc.adventure['maps'][0]['id']) if o['id']==identity)

    def test_box_extend_cross_erase_hole_raise_and_atomic_history(self):
        record=new_object(self.doc,0,self.style,1)
        paint_footprint(record,(4,4),(12,12),'Rectangle',1)
        old=copy.deepcopy(self.doc.adventure);old_art=copy.deepcopy(self.doc.art);old_meta=copy.deepcopy(self.doc.metadata)
        history=len(self.doc.undo_stack);identity=commit(self.doc,0,record)
        self.assertEqual(len(self.doc.undo_stack),history+1);self.doc.validate()
        self.doc.undo();self.assertEqual(self.doc.adventure,old);self.assertEqual(self.doc.art,old_art);self.assertEqual(self.doc.metadata,old_meta)
        self.doc.redo();record=copy.deepcopy(self.record(identity))
        paint_footprint(record,(1,7),(16,9),'Rectangle',1);commit(self.doc,0,record)
        self.assertEqual(len(self.doc.adventure['maps'][0]['overlays']),len(old['maps'][0]['overlays'])+1)
        record=copy.deepcopy(self.record(identity));paint_footprint(record,(6,6),(10,10),'Rectangle',1,erase=True);commit(self.doc,0,record)
        scene=self.doc.adventure['maps'][0];self.assertEqual(composite(scene)[9][9],composite(old['maps'][0])[9][9])
        record=copy.deepcopy(self.record(identity));paint_footprint(record,(4,4),(5,5),'Rectangle',3);commit(self.doc,0,record)
        heights={(x,y):h for x,y,h in self.record(identity)['cells']};self.assertEqual(heights[4,4],3);self.assertEqual(heights[12,12],1)
        self.doc.validate();self.doc.save();reopened=ProjectDocument(self.doc.root,self.doc.validator)
        self.assertEqual(metadata(reopened)['map_constructions'],metadata(self.doc)['map_constructions'])
        self.assertEqual(next(p for p in metadata(self.doc)['construction_sets'] if p['id']==self.style['id'])['footprint'],self.style['footprint'])

    def test_three_story_courtyard_reveals_ground_and_keeps_inner_faces(self):
        record=new_object(self.doc,0,self.style,3)
        paint_footprint(record,(2,2),(18,18),'Rectangle',3)
        paint_footprint(record,(2,2),(18,18),'Courtyard',3,2)
        cells={(x,y):h for x,y,h in record['cells']};self.assertNotIn((10,10),cells)
        self.assertEqual(cells[2,2],3);at,roles=projection(record)
        self.assertEqual(at,(2,2));self.assertEqual(roles[8][8],' ')
        self.assertTrue(any('south_middle' in r or 'east_middle' in r for row in roles for r in row))
        base=composite(self.doc.adventure['maps'][0]);commit(self.doc,0,record);self.doc.validate()
        self.assertEqual(composite(self.doc.adventure['maps'][0])[10][10],base[10][10])
        tall=new_object(self.doc,0,self.style,32);paint_footprint(tall,(1,1),(1,1),'Brush',32)
        _,tall_roles=projection(tall);self.assertEqual((len(tall_roles),len(tall_roles[0])),(33,33))
        with self.assertRaises(EditorError):paint_footprint(tall,(1,1),(1,1),'Brush',33)

    def test_failed_bounds_and_hand_painted_layer_do_not_overwrite(self):
        record=new_object(self.doc,0,self.style,3);paint_footprint(record,(30,22),(31,23),'Rectangle',3)
        before=self.doc.files();history=len(self.doc.undo_stack)
        with self.assertRaises(EditorError):commit(self.doc,0,record)
        self.assertEqual(self.doc.files(),before);self.assertEqual(len(self.doc.undo_stack),history)
        record=new_object(self.doc,0,self.style,1);paint_footprint(record,(4,4),(6,6),'Rectangle',1);identity=commit(self.doc,0,record)
        record=copy.deepcopy(self.record(identity));a=copy.deepcopy(self.doc.adventure)
        a['maps'][0]['overlays'][record['overlay']]['rows'][0][0]=a['tiles'][0]['id'];self.doc.replace_adventure(a)
        before=self.doc.files();paint_footprint(record,(7,4),(8,6),'Rectangle',1)
        with self.assertRaises(EditorError):commit(self.doc,0,record)
        self.assertEqual(self.doc.files(),before)

    def test_overlays_reorder_and_whole_footprint_erasure(self):
        record=new_object(self.doc,0,self.style,1);paint_footprint(record,(4,4),(6,6),'Rectangle',1);identity=commit(self.doc,0,record)
        a=copy.deepcopy(self.doc.adventure);a['maps'][0]['overlays'].reverse();self.doc.replace_adventure(a)
        record=copy.deepcopy(self.record(identity));index=overlay_index(a['maps'][0],record)
        untouched=[o for i,o in enumerate(a['maps'][0]['overlays']) if i!=index]
        paint_footprint(record,(0,0),(31,23),'Rectangle',1,erase=True);self.assertIsNone(commit(self.doc,0,record))
        self.assertEqual(self.doc.adventure['maps'][0]['overlays'],untouched)
        self.assertFalse(objects(self.doc,a['maps'][0]['id']));self.doc.undo();self.assertTrue(self.record(identity))

    def test_painted_water_details_survive_reshape_save_and_atomic_undo(self):
        record=new_object(self.doc,0,self.style,1);paint_footprint(record,(4,4),(10,10),'Rectangle',1)
        identity=commit(self.doc,0,record);before=self.doc.files();history=len(self.doc.undo_stack)
        water=next(t['id'] for t in self.doc.adventure['tiles'] if t['terrain']=='water')
        a=copy.deepcopy(self.doc.adventure);paint(a['maps'][0],-1,6,6,water);commit_tiles(self.doc,a)
        self.assertEqual(composite(self.doc.adventure['maps'][0])[6][6],water)
        self.assertEqual(self.record(identity)['details'],[[6,6,water]])
        self.assertEqual(len(self.doc.undo_stack),history+1);after=self.doc.files()
        self.doc.undo();self.assertEqual(self.doc.files(),before);self.doc.redo();self.assertEqual(self.doc.files(),after)
        record=copy.deepcopy(self.record(identity));paint_footprint(record,(2,4),(3,6),'Rectangle',1);commit(self.doc,0,record)
        self.assertEqual(composite(self.doc.adventure['maps'][0])[6][6],water)
        self.doc.save();loaded=ProjectDocument(self.doc.root,self.doc.validator)
        self.assertEqual(metadata(loaded),metadata(self.doc))
        record=copy.deepcopy(self.record(identity));paint_footprint(record,(4,4),(9,9),'Rectangle',1,erase=True);commit(self.doc,0,record)
        self.assertNotEqual(composite(self.doc.adventure['maps'][0])[6][6],water)
        self.assertFalse(self.record(identity)['details']);self.doc.validate()

    def test_walls_and_roads_connect_and_erase_recomputes_junctions(self):
        ident=new_profile(self.doc,'Wall');wall=next(p for p in metadata(self.doc)['construction_sets'] if p['id']==ident)
        record=new_object(self.doc,0,wall,3);paint_footprint(record,(3,3),(8,8),'Line',3)
        self.assertEqual(len(record['cells']),11);commit(self.doc,0,record);self.doc.validate()
        with self.assertRaises(EditorError):paint_footprint(record,(3,3),(3,3),'Brush',4)
        ident=new_profile(self.doc,'Road');road=prepare_road(self.doc,next(p for p in metadata(self.doc)['construction_sets'] if p['id']==ident))
        a=copy.deepcopy(self.doc.adventure);draw_road(a,0,0,(3,15),(13,21),road,1,'Courtyard')
        self.assertEqual(a['maps'][0]['rows'][15][3],road['parts']['road_6'])
        draw_road(a,0,0,(3,16),(3,20),road,1,'Line',True)
        self.assertEqual(a['maps'][0]['rows'][15][3],road['parts']['road_2'])
        self.doc.replace_adventure(a);self.doc.validate()

if __name__=='__main__':unittest.main()
