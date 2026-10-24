"""Private fixture conversion, native edit proofs and shared authoring contracts."""
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from editor_model import EditorError,ProjectDocument,encoded
from chi_import import import_campaigns
from chi_spatial import (data,change,enable,find,move_town,projection,from_projection,
    resolved_jigsaw,paint_world_terrain,place_world_jigsaw,paint_world_tiles,erase_world)
from chi_resources import preview,detach,settings,put_settings,world_preview,grid
from authoring_service import apply_batch,revision
from art_editing import new_image


@unittest.skipUnless((ROOT/'build/btp-chi-spatial-tests').is_file() and (ROOT/'Original DOS/BTECH.EXE').is_file(),'Needs native build and private DOS data')
class ChiSpatialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary=tempfile.TemporaryDirectory(prefix='chi-spatial-tests-',dir=ROOT/'work');cls.root=Path(cls.temporary.name)
        cls.tool=ROOT/'build/btp-project';cls.proof=ROOT/'build/btp-chi-spatial-tests'
        import_campaigns(ROOT/'Original DOS',cls.root/'pair',validator=cls.tool)
    @classmethod
    def tearDownClass(cls):cls.temporary.cleanup()
    def setUp(self):
        folder=self.root/self.id().rsplit('.',1)[-1];shutil.copytree(self.root/'pair/original',folder)
        self.doc=ProjectDocument(folder,self.tool)
    def request(self,ops):
        return dict(api_version=1,request_id=self.id().rsplit('.',1)[-1],project_id=self.doc.manifest['package_id'],
            expected_revision=revision(self.doc),label='CHI native edit',scope=['*'],operations=ops)
    def check_native(self,kind):
        self.doc.save()
        run=subprocess.run([str(self.proof),'--proof',str(self.root/'pair/original'),str(self.doc.root),kind],capture_output=True,text=True,timeout=20)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
    def test_exact_projection_and_source_schemas(self):
        value=data(self.doc);self.assertEqual(value,from_projection(projection(value)));self.assertEqual(self.doc.files(),self.doc.snapshot)
        try:import jsonschema
        except ImportError:jsonschema=None
        if jsonschema:
            jsonschema.validate(value,json.loads((ROOT/'schemas/chi-spatial-v1.schema.json').read_bytes()))
            jsonschema.validate(settings(self.doc),json.loads((ROOT/'schemas/chi-presentation-v1.schema.json').read_bytes()))
        self.assertEqual(len(value['maps']),15);self.assertEqual(len(value['tiles']),1000)
    def test_paint_shared_batch_native_collision_and_history(self):
        before=revision(self.doc);raw=self.doc.files()['chi/MAP1.MTP']
        a=copy.deepcopy(self.doc.adventure);a['maps'][0]['rows'][12][34]='chi:land-85';self.doc.replace_adventure(a)
        self.doc.validate();self.assertNotEqual(before,revision(self.doc));self.doc.undo();self.assertEqual(before,revision(self.doc));self.doc.redo()
        self.check_native('block');self.assertEqual(self.doc.files()['chi/MAP1.MTP'],raw)
        reopened=ProjectDocument(self.doc.root,self.tool);self.assertEqual(self.doc.files(),reopened.files())
        self.assertEqual(data(ProjectDocument(self.root/'pair/original',self.tool))['maps'][0]['rows'][12][35],data(ProjectDocument(self.root/'pair/updated',self.tool))['maps'][0]['rows'][12][35])
    def test_door_and_npc_routes_headless_batch(self):
        door=data(self.doc)['maps'][0]['entrances'][3]
        request=self.request([dict(op='chi.update',section='entrance',id=door['id'],changes={'half':[34,44]}),
            dict(op='chi.update',section='npc',id='chi:map-01-npc-0',changes={'name':'Test walker','route':1})])
        apply_batch(self.doc,request);self.assertEqual(data(self.doc)['maps'][0]['npcs'][0]['route'],1);self.check_native('door')
    def test_town_and_citadel_coordinates(self):
        apply_batch(self.doc,self.request([dict(op='chi.town.move',map='chi:map-03',at=[832,512])]))
        self.check_native('town')
        change(self.doc,lambda v:move_town(v,'chi:map-01',704,768));self.check_native('citadel')
        self.assertEqual(data(self.doc)['maps'][10]['origin'],[704,768])
    def test_custom_16bit_jigsaw_uses_runtime_rule_map(self):
        a=copy.deepcopy(self.doc.adventure);art=copy.deepcopy(self.doc.art);im=new_image('test',art['images'],'Test wall');art['images'].append(im)
        a['tiles'].append(dict(id='test:wall',sheet='package:art',graphic=im['id'],terrain='wall',mini_color=7))
        a['jigsaws'].append(dict(id='test:join',name='Test join',rows=[['test:wall']*8 for _ in range(8)]));a['chi_native']['world']['joins']=['test:join']*17
        self.doc.replace_art(art,a);self.check_native('jigsaw')
        self.assertGreater(len(data(self.doc)['tiles']),256)
    def test_world_paint_reaches_native_queries_and_roundtrip(self):
        original=self.doc.files()
        def edit(v):
            v['world']['jigsaws'].append(dict(id='test:literal',name='Literal wall',mode='absolute',rows=[['chi:land-85']*8 for _ in range(8)]))
            paint_world_terrain(v,[(1,1),(0,1),(2,1),(1,0),(1,2)],0)
            place_world_jigsaw(v,[(2,2)],'test:literal',48)
            ox,oy=v['maps'][0]['origin']
            paint_world_tiles(v,[(8,8)],'chi:land-16')
            paint_world_tiles(v,[(17,16)],'chi:land-47')
            paint_world_tiles(v,[(ox+34,oy+12)],'chi:land-85')
        change(self.doc,edit);self.check_native('world-paint')
        reopened=ProjectDocument(self.doc.root,self.tool)
        self.assertEqual(data(reopened),data(self.doc));self.assertEqual(data(self.doc),from_projection(projection(data(self.doc))))
        self.doc.undo();self.assertEqual(self.doc.files(),original);self.doc.redo();self.check_native('world-paint')
    def test_world_native_validation_rejects_ambiguous_or_unbounded_edits(self):
        before=self.doc.files()
        bad=[dict(terrain=[dict(at=[128,0],level=32)]),dict(terrain=[dict(at=[1,1],level=17)]),
            dict(terrain=[dict(at=[1,1],level=0)]*2),dict(placements=[dict(at=[1,1],level=32,jigsaw='test:missing')]),
            dict(placements=[dict(at=[1,1],level=32,jigsaw='chi:jigsaw-00',flip=4)]),
            dict(patches=[dict(at=[1024,0],tile='chi:land-0')]),dict(patches=[dict(at=[1,1],tile='test:missing')]),
            dict(patches=[dict(at=[1,1],tile='chi:land-0')]*2),dict(terrain=[dict(at=[1,1],level=32,ignored=1)])]
        for fields in bad:
            with self.subTest(fields=fields),self.assertRaises(EditorError):change(self.doc,lambda v:v['world'].update(fields))
            self.assertEqual(self.doc.files(),before)
    def test_world_review_and_protection_include_hidden_levels_and_tinyland(self):
        from authoring_protection import world_region
        from world_review import changes,Surface
        def setup(v):
            v['world']['jigsaws'].append(dict(id='test:literal',name='Literal ground',mode='absolute',rows=[['chi:land-0']*8 for _ in range(8)]))
            place_world_jigsaw(v,[(1,1)],'test:literal',0)
        change(self.doc,setup);before=self.doc.worker_copy()
        rule=dict(id='native-ground',label='Depth',kind='world_region',world='chi:world',rect=[8,8,8,8])
        protected=world_region(before,rule)
        change(self.doc,lambda v:v['world']['placements'][0].update(level=32))
        self.assertEqual(Surface(before,'chi:world').row(8,8,8),Surface(self.doc,'chi:world').row(8,8,8))
        self.assertNotEqual(protected,world_region(self.doc,rule))
        result=changes(before,self.doc);self.assertGreaterEqual(result[0]['changed_tiles'],64);self.assertTrue(result[0]['areas'])
        # A changed TINYLAND sheet must trigger review even when the world
        # definition and every ordinary terrain tile are unchanged.
        self.doc.undo();change(self.doc,lambda v:erase_world(v,[(1,1)]))
        before=self.doc.worker_copy();protected=world_region(before,rule)
        image=detach(self.doc,'screen','TINYLAND.CMP');art=copy.deepcopy(self.doc.art)
        native=next(i for i in art['images'] if i['id']==image['id'])
        native['frames']=[['ff55ffff'*native['width'] for _ in range(native['height'])]]
        self.doc.replace_art(art)
        self.assertNotEqual(protected,world_region(self.doc,rule));result=changes(before,self.doc)
        self.assertGreater(result[0]['changed_tiles'],0);self.assertTrue(result[0]['areas'])
    def test_resolved_piece_equals_native_stamp_at_all_materials_and_flips(self):
        # The C grid is loaded by the native game adapter. This catches preview
        # arithmetic that looks plausible but paints different tiles in play.
        def edit(v):
            for n,level in enumerate(range(0,128,16)):
                for flip in range(4):place_world_jigsaw(v,[(40+flip,40+n)],'chi:jigsaw-07',level,flip)
        change(self.doc,edit);actual=grid(self.doc,underlay=True)
        value=data(self.doc);identities=[t['id'] for t in value['tiles']]
        for n,level in enumerate(range(0,128,16)):
            for flip in range(4):
                expected=resolved_jigsaw(value,'chi:jigsaw-07',level,flip)
                for y in range(8):
                    row=[identities[actual[((40+n)*8+y)*1024+(40+flip)*8+x]] for x in range(8)]
                    self.assertEqual(row,expected[y],(level,flip,y))
    def test_native_sprite_copy_and_origin_survive_cloning(self):
        im=detach(self.doc,'sprite','MECHSHAP.CMP',0,16);art=copy.deepcopy(self.doc.art)
        art['images'][0]['frames'][0][0]='ffffffff'+art['images'][0]['frames'][0][0][8:];self.doc.replace_art(art);self.check_native('sprite')
        from unit_library import closure
        # Origin metadata also travels when a unit/library refers to this art.
        self.assertIn(im['id'],json.loads(self.doc.metadata['EDITOR.json'])['tile_sources'])
    def test_film_pixels_and_timing_reach_native_startup(self):
        im=detach(self.doc,'animation','O.ANM',0);art=copy.deepcopy(self.doc.art)
        art['images'][0]['frames'][0][0]='ffffffff'+art['images'][0]['frames'][0][0][8:];self.doc.replace_art(art)
        value=settings(self.doc);value['bindings'][0]['units'][0]+=7;put_settings(self.doc,value);self.check_native('film')
    def test_title_font_and_audio_references(self):
        im=detach(self.doc,'screen','BTTITLE.CMP');art=copy.deepcopy(self.doc.art)
        art['images'][0]['frames'][0][0]='ffffffff'+art['images'][0]['frames'][0][0][8:];self.doc.replace_art(art);self.check_native('screen')
        font=detach(self.doc,'font','BTTA.FONT');art=copy.deepcopy(self.doc.art);im=next(i for i in art['images'] if i['id']==font['id'])
        row=im['frames'][0][32];im['frames'][0][32]=row[:8*8]+'ffffffff'*8+row[16*8:];self.doc.replace_art(art);self.check_native('font')
        value=settings(self.doc);value['sounds'][0]=2;value['sound_speed']=125;put_settings(self.doc,value);self.check_native('audio')
    def test_source_conversion_and_build_retains_native_ids(self):
        from campaign_source import convert,build
        convert(self.doc,self.root/'native-source');source=ProjectDocument(self.root/'native-source',self.tool)
        self.assertEqual(data(source),data(self.doc));self.assertIn('chi_spatial',source.source.index['sections'])
        change(source,lambda v:move_town(v,'chi:map-03',832,512));source.save();build(source,self.root/'native-build')
        self.assertEqual(data(ProjectDocument(self.root/'native-build',self.tool)),data(source))
    def test_bad_edits_and_new_event_vm_are_rejected_atomically(self):
        original=self.doc.files()
        for edit in [lambda v:v['world'].update(seed=0),lambda v:v['maps'][0].update(origin=[700,700]),
                     lambda v:v['maps'][0]['npcs'][0].update(route=99),lambda v:v['world']['joins'].__setitem__(0,'test:missing'),
                     lambda v:v['world']['flips'].__setitem__(95,255)]:
            with self.assertRaises(EditorError):change(self.doc,edit)
            self.assertEqual(self.doc.files(),original)
        a=copy.deepcopy(self.doc.adventure);a['events'][0]['text']='Should never be ignored';self.doc.replace_adventure(a)
        with self.assertRaises(EditorError):self.doc.validate()
        self.doc.undo();self.assertEqual(self.doc.files(),original)
    def test_clone_slot_and_native_scopes(self):
        from chi_spatial import clone_map
        source=data(self.doc)['maps'][2];target=data(self.doc)['maps'][3];origin=target['origin'];identities=[d['id'] for d in target['entrances']]
        change(self.doc,lambda v:clone_map(v,source['id'],target['id']))
        target=data(self.doc)['maps'][3];self.assertEqual(target['origin'],origin);self.assertEqual(target['rows'],source['rows'])
        self.assertEqual([d['id'] for d in target['entrances']],identities)
        self.doc.save();request=self.request([dict(op='chi.town.move',map='chi:map-03',at=[832,512])]);request['scope']=['chi.maps/chi:map-03']
        result=apply_batch(self.doc,request);self.assertTrue(result)
    def test_library_pixel_closures_keep_provenance(self):
        from map_patterns import save_pattern
        from construction_library import closure,preview_files
        from asset_provenance import check_files
        identity=save_pattern(self.doc,[['chi:cache-50']],'Cache tile pattern');bundle=closure(self.doc,identity)
        self.assertEqual(bundle['tiles'][0]['sheet'],'package:art');self.assertTrue(bundle['editing']['tile_sources'])
        with self.assertRaises(EditorError):check_files({name:encoded(value) for name,value in preview_files(bundle).items()})
        from unit_library import closure as unit_closure
        from unit_editing import assign_graphic
        doc=ProjectDocument(self.root/'pair/updated',self.tool);im=detach(doc,'sprite','MECHSHAP.CMP',0,16)
        content=copy.deepcopy(doc.content);unit=content['mechs'][0];assign_graphic(content,unit['id'],im['id']);doc.replace(content)
        exported=unit_closure(doc,unit['id']);self.assertIn(im['id'],exported['editing']['tile_sources'])
    def test_updated_portraits_use_the_same_pixel_editor(self):
        doc=ProjectDocument(self.root/'pair/updated',self.tool);image=detach(doc,'portrait','PORTRAITS',6)
        art=copy.deepcopy(doc.art);next(i for i in art['images'] if i['id']==image['id'])['frames'][0][0]='ff55ffff'+image['frames'][0][0][8:];doc.replace_art(art)
        actual=preview(doc,'portrait','PORTRAITS',6);self.assertEqual(actual['frames'][0][0][:8],'ff55ffff')
    def test_updated_broker_is_an_editable_service_marker(self):
        doc=ProjectDocument(self.root/'pair/updated',self.tool);value=data(doc);service=value['services']['broker']
        self.assertEqual(service['half'],[54,50]);self.assertTrue(any(d['id']=='chi:broker' for d in doc.adventure['maps'][1]['entrances']))
        a=copy.deepcopy(doc.adventure);d=next(d for d in a['maps'][1]['entrances'] if d['id']=='chi:broker');d['name']='Unit Exchange'
        doc.replace_adventure(a);doc.validate();self.assertEqual(data(doc)['services']['broker']['name'],'Unit Exchange')
    def test_old_import_enable_and_bounded_world_surface(self):
        manifest=json.loads((self.doc.root/'project.json').read_bytes());manifest.pop('chi_spatial');(self.doc.root/'project.json').write_bytes(encoded(manifest))
        old=ProjectDocument(self.doc.root,self.tool);self.assertIsNone(old.adventure);enable(old);old.validate();old.undo();self.assertIsNone(old.adventure);old.redo()
        self.assertEqual(len(grid(old)),1024*1024)
        from world_review import Surface,worlds
        surface=Surface(old,'chi:world');self.assertEqual(len(surface.row(768,768,4)),4);self.assertEqual(worlds(old)[0]['width'],1024)
    def test_generator_seed_and_protected_world_region(self):
        a=world_preview(self.doc);self.assertEqual(a,world_preview(self.doc))
        before=self.doc.worker_copy();change(self.doc,lambda v:v['world'].update(seed=1));self.assertNotEqual(a,world_preview(self.doc))
        from authoring_protection import world_region
        rule=dict(id='native-ground',label='Keep terrain',kind='world_region',world='chi:world',rect=[480,480,32,32])
        self.assertNotEqual(world_region(before,rule),world_region(self.doc,rule))

    def test_native_review_and_protection_include_rules_and_sheet_pixels(self):
        from world_review import changes,detail,tile_values
        from authoring_protection import region
        rule=dict(map='chi:map-01',rect=[34,12,1,1]);before=region(self.doc,rule)
        identity=data(self.doc)['maps'][0]['rows'][12][34]
        tile=find(data(self.doc)['tiles'],identity);signature=tile_values(self.doc)[identity]
        change(self.doc,lambda v:find(v['tiles'],identity).update(rule=1))
        self.assertNotEqual(before,region(self.doc,rule));self.doc.undo()
        self.assertEqual(signature,tile_values(self.doc)[identity])
        detach(self.doc,'tile','BTTLTECH.ICN',tile['graphic'])
        self.assertNotEqual(before,region(self.doc,rule));self.doc.undo()
        base=self.doc.worker_copy();change(self.doc,lambda v:move_town(v,'chi:map-03',832,512))
        result=changes(base,self.doc);self.assertEqual(len(result),1);self.assertGreater(result[0]['changed_tiles'],0)
        self.assertTrue(any(t['id']=='chi:map-03' and t['change']=='moved' for t in result[0]['towns']))
        output=self.root/'native-review.svg';rendered=detail(self.doc,result[0],output,[832,512,4,4])
        self.assertEqual(rendered['status'],'rendered');self.assertTrue(output.is_file())


if __name__=='__main__':unittest.main()
