"""Authoring operations must remain playable, reversible and asset independent."""
import copy,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from editor_model import create_project,ProjectDocument,EditorError
from world_editing import create_world,world_size,assign_city
from tile_editing import create_tile,clone_sheet
from map_patterns import capture,cut,paste,save_pattern,export_pattern,import_pattern
from construction_editing import geometry,preset,new_profile,put_profile,compile_rows,prepare_road,draw_road
from tile_editing import metadata,source_definition


class ConstructionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.doc=create_project(ROOT/'examples/beacon-demo',self.root/'game','construction','Construction',ROOT/'build/btp-project')
    def test_original_world_default_and_loader(self):
        a=copy.deepcopy(self.doc.adventure);create_world(a,'construction');self.assertEqual(world_size(a),(1024,1024))
        for scene in a['maps']:assign_city(a,scene['id'])
        self.doc.replace_adventure(a);self.doc.validate()
    def test_bulk_clone_independent_pixels_and_atomic_undo(self):
        a=copy.deepcopy(self.doc.adventure);art=copy.deepcopy(self.doc.art)
        decoded={'test':[[['#112233']*16 for _ in range(16)],[['#445566']*16 for _ in range(16)]]}
        before=copy.deepcopy(decoded);ids=clone_sheet(self.doc,decoded,'test');self.assertEqual(len(ids),2)
        self.assertEqual(before,decoded);self.doc.validate();self.doc.undo();self.assertEqual(self.doc.adventure,a);self.assertEqual(self.doc.art,art)
        self.doc.redo();self.doc.save();self.assertEqual(self.doc.art,ProjectDocument(self.doc.root,self.doc.validator).art)
    def test_cut_paste_and_persistent_pattern(self):
        rect=(0,0,2,2);rows=capture(self.doc,0,rect);old=copy.deepcopy(self.doc.adventure)
        self.assertEqual(cut(self.doc,0,rect),rows);self.doc.undo();self.assertEqual(old,self.doc.adventure)
        pattern=save_pattern(self.doc,rows,'Ground patch');self.doc.save();reopened=ProjectDocument(self.doc.root,self.doc.validator)
        self.assertEqual(json.loads(reopened.metadata['EDITOR.json'])['map_patterns'][0]['id'],pattern)
        a=copy.deepcopy(self.doc.adventure);paste(a,0,0,10,10,rows);self.doc.replace_adventure(a);self.doc.validate()
        before=copy.deepcopy(a)
        with self.assertRaises(EditorError):paste(a,0,0,31,23,rows)
        self.assertEqual(a,before)
    def test_export_import_owned_pattern_is_one_undo(self):
        value=create_tile(self.doc,name='Owned tile');save_pattern(self.doc,[[value]],'Owned pattern')
        pattern=json.loads(self.doc.metadata['EDITOR.json'])['map_patterns'][0];path=self.root/'pattern.json';export_pattern(self.doc,pattern,path)
        other=create_project(ROOT/'examples/beacon-demo',self.root/'other','other','Other',self.doc.validator)
        before=copy.deepcopy(other.art);old=copy.deepcopy(other.adventure);import_pattern(other,path);other.validate();other.undo()
        self.assertEqual(before,other.art);self.assertEqual(old,other.adventure)

    def test_building_projection_cross_corners_and_stories(self):
        profile=dict(kind='Building',footprint=preset('Building',9,9,2,'Cross'),parts={})
        grid=geometry(profile);self.assertEqual((len(grid[0]),len(grid)),(11,11))
        self.assertEqual(grid[0][0],' ');self.assertTrue(grid[0][3].startswith('roof_'))
        self.assertTrue(any(p.startswith('roof_') and int(p.split('_')[2]) for row in grid for p in row))
        self.assertTrue(any('south_base' in p for row in grid for p in row))
        self.assertTrue(any('east_top' in p for row in grid for p in row))
        profile['footprint']=preset('Building',3,3,1,'Rectangle');one=geometry(profile)
        profile['footprint']=preset('Building',3,3,3,'Rectangle');three=geometry(profile)
        self.assertEqual((len(one),len(three)),(4,6))
        profile['kind']='Wall';profile['footprint'][1][1]=4
        with self.assertRaises(EditorError):geometry(profile)
        profile['footprint'][1][1]=1;self.assertTrue(geometry(profile))

    def test_construct_place_validate_and_replace_part(self):
        original=copy.deepcopy(self.doc.adventure);original_art=copy.deepcopy(self.doc.art)
        ident=new_profile(self.doc);profile=next(p for p in metadata(self.doc)['construction_sets'] if p['id']==ident)
        self.doc.validate();self.doc.undo();self.assertEqual(original,self.doc.adventure);self.assertEqual(original_art,self.doc.art);self.doc.redo()
        rows=compile_rows(profile);save_pattern(self.doc,rows,'Cross-shaped building')
        a=copy.deepcopy(self.doc.adventure);paste(a,0,0,1,1,rows);self.doc.replace_adventure(a);self.doc.validate()
        from editor_dependencies import remove,usages
        before=copy.deepcopy(metadata(self.doc));role=next(iter(profile['parts']));old=profile['parts'][role];replacement=create_tile(self.doc,name='Replacement wall',terrain='wall')
        self.assertTrue(any(u.section=='editor' for u in usages(self.doc,old)))
        with self.assertRaises(EditorError):remove(self.doc,old)
        remove(self.doc,old,replacement);self.doc.validate()
        data=metadata(self.doc);self.assertEqual(data['construction_sets'][0]['parts'][role],replacement)
        self.assertNotIn(old,[t for row in data['map_patterns'][0]['rows'] for t in row])
        self.doc.undo();self.assertEqual(metadata(self.doc)['construction_sets'],before['construction_sets'])

    def test_roads_connect_endpoints_junctions_and_respect_layers(self):
        ident=new_profile(self.doc,'Road');profile=prepare_road(self.doc,next(p for p in metadata(self.doc)['construction_sets'] if p['id']==ident))
        a=copy.deepcopy(self.doc.adventure);draw_road(a,0,0,(2,5),(8,5),profile);draw_road(a,0,0,(5,2),(5,8),profile)
        grid=a['maps'][0]['rows'];self.assertEqual(grid[5][5],profile['parts']['road_15']);self.assertEqual(grid[5][2],profile['parts']['road_2']);self.assertEqual(grid[2][5],profile['parts']['road_4'])
        old=copy.deepcopy(a)
        with self.assertRaises(EditorError):draw_road(a,0,0,(0,0),(64,0),profile)
        self.assertEqual(old,a)
        a['maps'][0]['overlays'].append(dict(at=[0,0],rows=[[' ']*10 for _ in range(10)]))
        draw_road(a,0,len(a['maps'][0]['overlays']),(4,4),(6,4),profile)
        self.assertEqual(a['maps'][0]['overlays'][-1]['rows'][4][5],profile['parts']['road_10']);self.assertEqual(a['maps'][0]['rows'],grid)
        self.doc.replace_adventure(a);self.doc.validate()

    def test_world_pattern_bounds_city_conflicts_and_round_trip(self):
        from map_patterns import world_capture,world_paste
        a=copy.deepcopy(self.doc.adventure);ident=create_world(a,'construction',16,16)
        for scene in a['maps']:assign_city(a,scene['id'],world_id=ident)
        self.doc.replace_adventure(a);rows=world_capture(self.doc,ident,(64,64,66,66));before=copy.deepcopy(a)
        with self.assertRaises(EditorError):world_paste(a,ident,64,64,rows)
        self.assertEqual(a,before)
        world_paste(a,ident,1,1,rows);self.doc.replace_adventure(a)
        self.assertEqual(rows,world_capture(self.doc,ident,(1,1,3,3)));self.doc.validate()

    def test_clone_preserves_authored_collision_and_sheet_defaults(self):
        existing=self.doc.adventure['tiles'][0]
        self.assertEqual(source_definition(self.doc,existing['sheet'],existing['graphic'])['terrain'],existing['terrain'])
        self.assertEqual(source_definition(self.doc,'chi:land',100)['terrain'],'wall')
        self.assertEqual(source_definition(self.doc,'chi:land',15)['terrain'],'water')

if __name__=='__main__':unittest.main()
