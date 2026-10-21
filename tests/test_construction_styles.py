"""Reusable styles retain their art through new shapes, sharing and Undo."""
import copy
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from editor_model import create_project,ProjectDocument,EditorError
from construction_editing import new_profile,put_profile,preset,geometry,draw_road,part_name
from construction_styles import primitive_roles,coverage,complete_profile,tile_art,joined_art
from construction_library import closure,import_bundle
from map_construction import new_object,paint_footprint,projection,commit
from tile_editing import metadata
from authoring_service import apply_batch,revision
from asset_catalogue import catalogue


class StyleTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.doc=create_project(ROOT/'examples/beacon-demo',self.root/'game','styles','Styles',ROOT/'build/btp-project')

    def profile(self,identity):return next(p for p in metadata(self.doc)['construction_sets'] if p['id']==identity)

    def test_all_local_roof_masks_and_style_completion(self):
        seen=set()
        neighbours=[(x,y) for y in range(3) for x in range(3) if (x,y)!=(1,1)]
        for mask in range(256):
            rows=[[0]*3 for _ in range(3)];rows[1][1]=1
            for i,(x,y) in enumerate(neighbours):rows[y][x]=1 if mask&(1<<i) else 0
            origin,grid=geometry(dict(kind='Building',footprint=rows,parts={}),with_origin=True)
            seen.add(grid[1-origin[1]][1-origin[0]])
        self.assertEqual(seen,{r for r in primitive_roles('Building') if r.startswith('roof_')})
        self.assertEqual(len(seen),47)
        p=dict(id='styles:custom',name='Custom facade',kind='Building',footprint=[[1]],parts={})
        put_profile(self.doc,p);before=self.doc.files();report=complete_profile(self.doc,p['id'])
        self.assertEqual((report['assigned'],report['required']),(56,56));self.assertTrue(report['complete'])
        self.doc.validate();self.doc.undo();self.assertEqual(self.doc.files(),before);self.doc.redo()
        self.assertTrue(next(v for v in catalogue(self.doc) if v['id']==p['id'])['coverage']['complete'])

    def test_custom_faces_animated_joins_and_manual_overrides(self):
        identity=new_profile(self.doc);profile=self.profile(identity);art=copy.deepcopy(self.doc.art)
        for role,colors,ticks in [('east_top',['aa0000ff','00bb00ff'],3),('south_top',['0000ccff','dddd00ff','ee00eeff'],2)]:
            _,im=tile_art(self.doc.adventure,art,profile['parts'][role])
            im.update(frames=[[color*16]*16 for color in colors],frame_ticks=ticks)
        self.doc.replace_art(art);complete_profile(self.doc,identity);profile=self.profile(identity)
        role='join|east_top|south_top';_,joined=tile_art(self.doc.adventure,self.doc.art,profile['parts'][role])
        self.assertEqual((len(joined['frames']),joined['frame_ticks']),(6,1))
        self.assertEqual(joined['frames'][0][8], '0000ccff'*8+'aa0000ff'*8)
        self.assertEqual(joined['frames'][3][8], 'dddd00ff'*8+'00bb00ff'*8)
        # An artist's edit detaches just that join from automatic completion.
        art=copy.deepcopy(self.doc.art);_,manual=tile_art(self.doc.adventure,art,profile['parts'][role])
        manual['frames'][0][0]='123456ff'*16;self.doc.replace_art(art)
        complete_profile(self.doc,identity);after=self.profile(identity)
        self.assertEqual(after['parts'][role],profile['parts'][role]);self.assertNotIn(role,after['generated_joins'])
        _,saved=tile_art(self.doc.adventure,self.doc.art,after['parts'][role]);self.assertEqual(saved['frames'][0][0],'123456ff'*16)
        self.doc.validate()

    def test_join_bounds_and_no_implicit_original_copy(self):
        identity=new_profile(self.doc);p=self.profile(identity);art=copy.deepcopy(self.doc.art)
        for role,n,ticks in [('east_top',251,2),('south_top',253,3)]:
            _,im=tile_art(self.doc.adventure,art,p['parts'][role]);im.update(frames=im['frames']*n,frame_ticks=ticks)
        with self.assertRaisesRegex(EditorError,'256 animation'):joined_art(self.doc.adventure,art,p,'join|east_top|south_top')
        a=copy.deepcopy(self.doc.adventure);tile,_=tile_art(a,self.doc.art,p['parts']['east_top']);tile.update(sheet='chi:land',graphic=144)
        self.doc.replace_art(self.doc.art,a);before=self.doc.files()
        with self.assertRaisesRegex(EditorError,'Clone that part'):complete_profile(self.doc,identity)
        self.assertEqual(self.doc.files(),before)

    def test_all_four_t_junction_tiles_selected_by_road_brush(self):
        identity=new_profile(self.doc,'Road');p=self.profile(identity)
        for direction,mask,branch,main in [('north',11,(8,3),((4,8),(12,8))),('east',7,(13,8),((8,3),(8,13))),
                                          ('south',14,(8,13),((4,8),(12,8))),('west',13,(3,8),((8,3),(8,13)))]:
            with self.subTest(direction=direction):
                a=copy.deepcopy(self.doc.adventure)
                draw_road(a,0,0,*main,p);draw_road(a,0,0,(8,8),branch,p)
                self.assertEqual(a['maps'][0]['rows'][8][8],p['parts'][f'road_{mask}'])
                self.assertIn('branch '+direction,part_name(f'road_{mask}'))
                origin,preview=geometry(dict(p,footprint=preset('Road',5,5,1,'T '+direction)),with_origin=True)
                self.assertEqual(preview[2-origin[1]][2-origin[0]],f'road_{mask}')
        self.assertEqual(coverage(p)['assigned'],16)

    def test_roof_only_walls_mixed_levels_erase_save_and_library(self):
        identity=new_profile(self.doc,'Wall');p=self.profile(identity)
        self.assertIn(-1,[h for row in p['footprint'] for h in row])
        self.assertTrue(all(r==' ' or r.startswith('roof_') for row in geometry(p) for r in row))
        record=new_object(self.doc,0,p,0);paint_footprint(record,(3,3),(10,3),'Line',0)
        at,roles=projection(record);self.assertEqual(at,(3,3));self.assertEqual(len(roles),1);self.assertEqual(len(roles[0]),8)
        paint_footprint(record,(6,3),(6,3),'Brush',0,erase=True)
        self.assertEqual(len(record['cells']),7)
        commit(self.doc,0,record);self.doc.validate();self.doc.save()
        self.assertEqual(ProjectDocument(self.doc.root,self.doc.validator).files(),self.doc.files())
        bundle=closure(self.doc,identity)
        other=create_project(ROOT/'examples/beacon-demo',self.root/'other','other','Other',self.doc.validator)
        imported=import_bundle(other,bundle);self.assertEqual(metadata(other)['construction_sets'][0]['footprint'],p['footprint'])
        self.assertEqual(imported,identity)
        # Raising an existing roof-only section is still a height edit, never
        # reinterpret all older zero/empty footprint cells as occupied walls.
        paint_footprint(record,(9,3),(10,3),'Line',1);at,roles=projection(record)
        self.assertTrue(any('south_single' in r for row in roles for r in row))
        self.assertEqual(geometry(dict(kind='Wall',parts={},footprint=[[0,1,0]]))[0][0],'roof_15_0')

    def test_completion_command_and_shared_generated_style(self):
        identity=new_profile(self.doc)
        bundle=closure(self.doc,identity);other=create_project(ROOT/'examples/beacon-demo',self.root/'other','other','Other',self.doc.validator)
        imported=import_bundle(other,bundle);before=other.files()
        request=dict(api_version=1,request_id='complete-style',project_id='other',expected_revision=revision(other),label='Complete imported style',scope=['editor','adventure','art'],operations=[dict(op='construction.complete',style=imported)])
        apply_batch(other,request);other.validate()
        # No pixel/ID churn when the imported source faces have not changed.
        self.assertEqual(other.art['images'],self.doc.art['images'])
        other.undo();self.assertEqual({k:v for k,v in other.files().items() if k!='AUTHORING.json'},before)


if __name__=='__main__':unittest.main()
