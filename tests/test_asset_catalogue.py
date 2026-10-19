"""Discovery must choose the real asset and preserve authored data/history."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from asset_catalogue import catalogue,search,annotate,matches,parse_query,bundle_record
from authoring_contract import AuthoringError
from authoring_service import apply_batch,revision
from authoring_visuals import contact_sheet,animation_strip,map_svg,world_svg,event_graph,VisualSource,png
from editor_model import ProjectDocument,create_project
from editor_tiles import load_tiles
from event_editing import editor_data
from tile_editing import create_tile
from unit_library import closure,import_units

TOOL=ROOT/'build/btp-project'


class Discovery(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='btp-discovery-');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.doc=create_project(ROOT/'examples/beacon-demo',self.root/'game','discovery','Discovery',TOOL)
    def request(self,ops):
        return dict(api_version=1,project_id='discovery',request_id='annotate-1',expected_revision=revision(self.doc),
                    label='Describe art',scope=['editor.catalogue'],operations=ops)
    def test_unit_filters_and_explicit_derived_roles(self):
        doc=ProjectDocument(ROOT/'examples/relay-contract',TOOL);before=doc.files()
        result=search(catalogue(doc),'kind:mech class:light weapon:lrm walk>=6')
        self.assertEqual([r['id'] for r in result['items']],['workshop:kite'])
        item=result['items'][0];self.assertIn('missile-support',item['derived_roles']);self.assertIn('Heuristics',item['role_basis'])
        self.assertEqual(item['dependency_closure']['weapons'],['workshop:sky-lance'])
        self.assertEqual(search(catalogue(doc),'Trebuchet')['total'],1)
        self.assertEqual(before,doc.files())
        vehicle=ProjectDocument(ROOT/'examples/vehicle-lab',TOOL)
        self.assertGreater(search(catalogue(vehicle),'kind:vehicle movement:tracked')['total'],0)
    def test_metadata_batch_is_dry_runnable_undoable_and_persistent(self):
        tile=self.doc.adventure['tiles'][0]['id'];before=self.doc.files()
        req=self.request([dict(op='asset.annotate',id=tile,changes=dict(name='Factory floor',description='Fits the depot.',tags=['industrial','floor'],edges={'north':'paving'}))])
        apply_batch(self.doc,req,dry_run=True);self.assertEqual(before,self.doc.files())
        apply_batch(self.doc,req,save=True)
        record=search(catalogue(self.doc),'tag:industrial')['items'][0]
        self.assertEqual(record['id'],tile);self.assertEqual(record['edges'],{'north':'paving'})
        self.doc.undo();self.assertEqual(search(catalogue(self.doc),'tag:industrial')['total'],0)
        self.doc.redo();self.doc.save();self.assertEqual(search(catalogue(ProjectDocument(self.doc.root,TOOL)),'Factory')['total'],1)
    def test_query_errors_pagination_ids_and_finite_numbers(self):
        values=catalogue(self.doc);first=search(values,limit=1)
        self.assertEqual(first['next_offset'],1);self.assertEqual(search(values,offset=1,limit=1)['items'],values[1:2])
        identity=self.doc.content['mechs'][0]['id'];self.assertEqual(search(values,identity)['items'][0]['id'],identity)
        for query in ('mass>nan','walk>=oops','kind>=5','"unterminated'):
            with self.assertRaises(AuthoringError):search(values,query)
    def test_visual_manifest_uses_exact_shared_pixels_and_changes_hash(self):
        source=VisualSource(self.doc);tile=search(catalogue(self.doc),'kind:tile')['items'][0]
        before=revision(self.doc);result=contact_sheet(self.doc,[tile],self.root/'sheet.svg')
        self.assertEqual(result['artifact']['items'][0]['pixel_sha256'],hashlib.sha256(png(source.frames(tile)[0][0])).hexdigest())
        tree=ET.parse(self.root/'sheet.svg');self.assertIn(tile['key'],''.join(tree.getroot().itertext()))
        self.assertEqual(before,revision(self.doc));self.assertEqual(len(self.doc.undo_stack),0)
        with self.assertRaises(FileExistsError):contact_sheet(self.doc,[tile],self.root/'sheet.svg')
        with self.assertRaises(AuthoringError):contact_sheet(self.doc,[tile],self.doc.root/'bad.svg')
    def test_animated_clone_keeps_tags_frames_and_timing(self):
        original=self.doc.adventure['tiles'][0]
        tile_id=create_tile(self.doc,load_tiles(self.doc,{}),original,'Electric test')
        tile=next(t for t in self.doc.adventure['tiles'] if t['id']==tile_id);art=copy.deepcopy(self.doc.art)
        image=next(i for i in art['images'] if i['id']==tile['graphic']);image['frames'].append(['ff0000ff'*16]*16);image['frame_ticks']=5
        self.doc.replace_art(art);annotate(self.doc,tile_id,{'tags':['force-field'],'description':'Electric test'})
        cloned=create_tile(self.doc,load_tiles(self.doc,{}),tile,'Electric clone')
        result=search(catalogue(self.doc),'kind:tile tag:force-field animated:true')
        self.assertEqual(result['total'],2);item=next(r for r in result['items'] if r['id']==cloned)
        strip=animation_strip(self.doc,item,self.root/'strip.svg')
        self.assertEqual(strip['artifact']['frames_total'],2);self.assertEqual(strip['artifact']['frame_ticks'],5)
        self.assertEqual(VisualSource(self.doc).frames(item)[0][1][0][0],'#ff0000')
    def test_library_closure_and_annotations_survive_import(self):
        identity=self.doc.content['mechs'][0]['id'];annotate(self.doc,identity,{'tags':['test-design'],'description':'Human description'})
        bundle=closure(self.doc,identity);item=bundle_record(bundle)
        self.assertTrue(matches(item,'tag:test-design'));self.assertEqual(item['description'],'Human description')
        destination=create_project(ROOT/'examples/beacon-demo',self.root/'destination','destination','Destination',TOOL)
        imported=import_units(destination,[bundle],policy='variant')
        notes=editor_data(destination)['catalogue'][imported[0][1]];self.assertEqual(notes['description'],'Human description')
        destination.validate()
    def test_graph_and_map_overlays_are_read_only(self):
        before=revision(self.doc);identity=self.doc.adventure['maps'][0]['id']
        result=map_svg(self.doc,identity,self.root/'map.svg',overlays=['collision','entrances','formations','grid'])
        self.assertTrue(result['artifact']['markers'])
        graph=event_graph(self.doc,self.root/'graph.svg');self.assertEqual(graph['artifact']['events'],len(self.doc.adventure['events']))
        self.assertEqual(before,revision(self.doc));self.assertEqual(len(self.doc.undo_stack),0)
    def test_headless_imports_and_cli_json(self):
        code="import sys;sys.path.insert(0,'tools');import asset_catalogue,authoring_visuals;assert 'tkinter' not in sys.modules"
        subprocess.run([sys.executable,'-c',code],cwd=ROOT,check=True,timeout=10)
        result=subprocess.run([sys.executable,str(ROOT/'tools/author.py'),'catalogue',str(self.doc.root),'--query','kind:mech'],capture_output=True,text=True,check=True,timeout=10)
        self.assertGreater(json.loads(result.stdout)['data']['total'],0)
    def test_source_atlas_annotations_and_owned_image_identity(self):
        annotate(self.doc,'atlas:package-tiles-0',dict(tags=['industrial-floor']))
        values=catalogue(self.doc,'atlas',decoded=load_tiles(self.doc,{}))
        found=search(values,'tag:industrial-floor')['items'];self.assertEqual(len(found),1)
        self.assertEqual(found[0]['graphic'],0)
        original=next(t for t in self.doc.adventure['tiles'] if t['graphic']!=0);tile_id=create_tile(self.doc,load_tiles(self.doc,{}),original,'Owned tile')
        tile=next(t for t in self.doc.adventure['tiles'] if t['id']==tile_id)
        annotate(self.doc,tile['graphic'],dict(tags=['owned-test']))
        records=search(catalogue(self.doc),'tag:owned-test')['items']
        self.assertEqual({r['collection'] for r in records},{'images','tiles'})
        image_record=next(r for r in records if r['collection']=='images')
        self.assertEqual(VisualSource(self.doc).frames(image_record)[0][0],VisualSource(self.doc).frames(next(r for r in records if r['collection']=='tiles'))[0][0])
    def test_changed_artwork_invalidates_visual_hash(self):
        tile_id=create_tile(self.doc,load_tiles(self.doc,{}),self.doc.adventure['tiles'][0],'Hash test')
        item=next(r for r in catalogue(self.doc) if r['id']==tile_id)
        before=contact_sheet(self.doc,[item],self.root/'before.svg')['artifact']['items'][0]['pixel_sha256']
        art=copy.deepcopy(self.doc.art);image=next(i for i in art['images'] if i['id']==item['graphic']);image['frames'][0][0]='ff0000ff'*16
        self.doc.replace_art(art)
        after=contact_sheet(self.doc,[item],self.root/'after.svg')['artifact']['items'][0]['pixel_sha256']
        self.assertNotEqual(before,after)
    def test_directional_action_frames_and_per_frame_durations(self):
        from art_editing import new_image
        from action_tracks import set_track
        art=copy.deepcopy(self.doc.art);image=new_image('discovery',art['images'],'Directional sprite','sprite')
        image['frames']=[['%02x0000ff'%n*16]*16 for n in range(32)]
        set_track(image,'fire',[f'{d*4+1}:2 {d*4+3}:7' for d in range(8)],sound=5)
        art['images'].append(image);self.doc.replace_art(art)
        item=next(r for r in catalogue(self.doc) if r['id']==image['id'])
        result=animation_strip(self.doc,item,self.root/'action.svg',direction=2,action='fire')['artifact']
        self.assertEqual([(f['image'],f['ticks']) for f in result['frames']],[(8,2),(10,7)])
        self.assertEqual(result['sound'],5);self.assertIn('Right 1',result['frames'][0]['roles'])
        self.assertEqual(result['timing_basis'],'authored action durations')
    def test_world_city_overlay_and_focused_graph(self):
        from world_editing import create_world,assign_city,world_tile
        a=copy.deepcopy(self.doc.adventure);world=create_world(a,'discovery',8,8,'Discovery planet')
        city=a['maps'][0]['id'];assign_city(a,city,[8,8],True,world);self.doc.replace_adventure(a);self.doc.validate()
        before=revision(self.doc);result=world_svg(self.doc,world,self.root/'world.svg',rect=[6,6,36,28])
        self.assertEqual(result['artifact']['cities'],[city]);self.assertEqual(before,revision(self.doc))
        root=a['start']['event'];focused=event_graph(self.doc,self.root/'focused.svg',root,1)
        self.assertLess(focused['artifact']['events'],len(a['events']));self.assertEqual(focused['artifact']['root'],root)


if __name__=='__main__':unittest.main()
