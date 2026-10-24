"""Shared workshop edits retain revisions, source credits and isolated trials."""
import copy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from construction_library import ConstructionLibrary,closure,import_bundle,check_bundle
from construction_workshop import WorkshopContext
from construction_editing import new_profile,put_profile
from editor_model import ProjectDocument,EditorError,encoded,create_project
from tile_editing import metadata,create_tile
from map_patterns import save_pattern


class ConstructionWorkshopTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='shared-workshop-');self.root=Path(self.temp.name)
        self.validator=ROOT/'build/btp-project'
        self.doc=create_project(ROOT/'examples/beacon-demo',self.root/'game','workshop-test','Untouched game',self.validator)
        self.library=ConstructionLibrary(self.root/'library',self.validator)
        self.contexts=[]
    def tearDown(self):
        for c in self.contexts:c.temp.cleanup()
        self.temp.cleanup()
    def open(self,bundle):
        c=WorkshopContext(SimpleNamespace(library=self.library),bundle,self.root);self.contexts.append(c)
        return c,ProjectDocument(Path(c.temp.name),self.validator)

    def test_shared_tile_import_retains_animation_sources_and_undo(self):
        identity=create_tile(self.doc,name='Shared electricity')
        art=copy.deepcopy(self.doc.art);image=art['images'][-1]
        image['frames'].append(['ffcc00ff'*16]*16);image['frame_ticks']=2
        data=metadata(self.doc);data['tile_sources']={image['id']:dict(sheet='chi:land',graphic=86)}
        meta=dict(self.doc.metadata);meta['EDITOR.json']=encoded(data)
        self.doc.replace_art(art,metadata=meta)
        bundle=self.library.save(closure(self.doc,identity));check_bundle(bundle)
        self.assertEqual(bundle['kind'],'Tile')
        target=create_project(ROOT/'examples/beacon-demo',self.root/'other','other','Destination',self.validator)
        before=target.files();history=len(target.undo_stack);new=import_bundle(target,bundle)
        self.assertEqual(len(target.undo_stack),history+1)
        self.assertEqual(closure(target,new)['images'],bundle['images'])
        self.assertEqual(closure(target,new)['editing']['tile_sources'],bundle['editing']['tile_sources'])
        self.assertFalse(metadata(target).get('construction_sets'))
        target.undo();self.assertEqual(target.files(),before)
        target.redo();target.validate()

    def test_saved_workshop_reopens_canvas_but_imports_only_definition(self):
        identity=new_profile(self.doc,'Building');bundle=closure(self.doc,identity)
        bundle['provenance']['documents']['CREDITS.md']='Original artist credit.'
        saved=self.library.save(bundle);original=self.doc.files()
        context,doc=self.open(saved)
        style=copy.deepcopy(metadata(doc)['construction_sets'][0]);style['footprint'][0][0]=3
        put_profile(doc,style);trial=create_tile(doc,name='Test-only terrain')
        a=copy.deepcopy(doc.adventure);a['maps'][0]['rows'][20][20]=trial
        doc.replace_adventure(a);doc.validate()
        revised=context.export_document(doc)
        self.assertEqual(revised['entry_id'],saved['entry_id']);self.assertEqual(revised['revision'],2)
        self.assertEqual(revised['provenance']['documents']['CREDITS.md'],'Original artist credit.')
        self.assertNotIn(trial,{t['id'] for t in revised['tiles']})
        _,reopened=self.open(revised)
        self.assertEqual(reopened.files(),doc.files())
        import_bundle(self.doc,revised)
        self.assertNotIn(trial,{t['id'] for t in self.doc.adventure['tiles']})
        self.doc.undo();self.assertEqual(self.doc.files(),original)

    def test_stale_edit_rejected_and_variant_and_discard_are_isolated(self):
        identity=new_profile(self.doc,'Road');saved=self.library.save(closure(self.doc,identity))
        context,doc=self.open(saved);stale,other=self.open(saved)
        style=copy.deepcopy(metadata(doc)['construction_sets'][0]);style['name']='Changed road'
        put_profile(doc,style);expected=doc.files();doc.undo();self.assertNotEqual(doc.files(),expected)
        doc.redo();self.assertEqual(doc.files(),expected)
        revised=context.export_document(doc);entry=self.library.path(saved['entry_id']).read_bytes()
        with self.assertRaises(EditorError):stale.export_document(other)
        self.assertEqual(self.library.path(saved['entry_id']).read_bytes(),entry)
        variant=stale.export_document(other,variant=True)
        self.assertNotEqual(variant['entry_id'],saved['entry_id']);self.assertEqual(variant['revision'],1)
        _,reopened=self.open(revised)
        self.assertEqual(metadata(reopened)['construction_sets'][0]['name'],'Changed road')
        put_profile(other,{**metadata(other)['construction_sets'][0],'name':'Discarded draft'})
        stale.temp.cleanup()
        self.assertEqual(self.library.path(saved['entry_id']).read_bytes(),entry)

    def test_pattern_recapture_preserves_new_tiles_and_pixel_changes(self):
        tile=create_tile(self.doc,name='Map block ground')
        pattern=save_pattern(self.doc,[[tile]],'Shared block')
        saved=self.library.save(closure(self.doc,pattern));context,doc=self.open(saved)
        new=create_tile(doc,name='Map block detail')
        save_pattern(doc,[[tile,new],[' ',tile]],'Edited shared block',pattern)
        art=copy.deepcopy(doc.art);next(im for im in art['images'] if im['id']==next(t['graphic'] for t in doc.adventure['tiles'] if t['id']==new))['frames'][0][0]='bb9900ff'*16
        doc.replace_art(art);revised=context.export_document(doc)
        self.assertEqual({t['id'] for t in revised['tiles']},{tile,new})
        self.assertEqual(revised['design']['rows'][1][0],' ')
        _,reopened=self.open(revised);self.assertEqual(closure(reopened,pattern)['images'],revised['images'])

    def test_tile_catalogue_and_authoring_import_use_requested_id(self):
        from asset_catalogue import catalogue,search
        from authoring_service import apply_batch,revision
        identity=create_tile(self.doc,name='Shared paving');saved=self.library.save(closure(self.doc,identity))
        records=catalogue(self.doc,'construction-library',construction_library=self.library.root)
        self.assertEqual(search(records,'kind:tile')['total'],1)
        before=self.doc.files()
        request=dict(api_version=1,request_id='shared-paving',project_id='workshop-test',expected_revision=revision(self.doc),
            label='Use a shared tile',scope=['*'],operations=[
                dict(op='construction.import',file=str(self.library.path(saved['entry_id'])),id='workshop-test:paving'),
                dict(op='map.paint',map=self.doc.adventure['maps'][0]['id'],tile='workshop-test:paving',start=[2,20])])
        apply_batch(self.doc,request,base_dir=self.root)
        self.assertIn('workshop-test:paving',{t['id'] for t in self.doc.adventure['tiles']})
        self.doc.validate();self.doc.undo();self.assertEqual({k:v for k,v in self.doc.files().items() if k!='AUTHORING.json'},before)


if __name__=='__main__':unittest.main()
