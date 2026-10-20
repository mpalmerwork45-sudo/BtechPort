"""Shared styles/patterns retain dependencies across unrelated projects."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from editor_model import ProjectDocument,EditorError,encoded,create_project
from construction_editing import new_profile,compile_rows
from construction_library import ConstructionLibrary,closure,import_bundle,validate,check_bundle,summary
from map_patterns import save_pattern
from tile_editing import metadata
from authoring_service import apply_batch,revision


class ConstructionLibraryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='construction-library-test-')
        self.root=Path(self.tmp.name);self.tool=ROOT/'build/btp-project'
        self.source=create_project(ROOT/'examples/beacon-demo',self.root/'source','source','Source project',self.tool)
        self.target=create_project(ROOT/'examples/beacon-demo',self.root/'target','target','Target project',self.tool)
        self.library=ConstructionLibrary(self.root/'library',self.tool)
    def tearDown(self):self.tmp.cleanup()
    def style(self,kind='Building'):
        identity=new_profile(self.source,kind)
        return identity,closure(self.source,identity)

    def test_all_styles_keep_parts_and_editable_footprint(self):
        for kind in ('Building','Wall','Road'):
            identity,bundle=self.style(kind);source_before=self.source.files()
            saved=self.library.save(bundle);check_bundle(saved);new=import_bundle(self.target,saved)
            design=next(p for p in metadata(self.target)['construction_sets'] if p['id']==new)
            self.assertEqual(design['footprint'],bundle['design']['footprint'])
            self.assertEqual(set(design['parts']),set(bundle['design']['parts']))
            self.assertEqual(len(compile_rows(design)),len(compile_rows(bundle['design'])))
            self.assertEqual(self.source.files(),source_before)
        self.target.save();self.assertEqual(ProjectDocument(self.target.root,self.tool).files(),self.target.files())

    def test_animated_tiles_layers_and_credits_roundtrip(self):
        identity,bundle=self.style()
        im=self.source.art['images'][0];art=copy.deepcopy(self.source.art)
        art['images'][0]['frames'].append(['ff0000ff'*16]*16);art['images'][0]['frame_ticks']=3
        from pixel_tools import begin_layers,export_layers
        _,layers=export_layers(begin_layers(art['images'][0]))
        data=metadata(self.source);data['pixel_layers']={im['id']:layers}
        data['catalogue']={identity:dict(tags=['industrial'],description='Factory roof and faces')}
        meta=dict(self.source.metadata);meta['EDITOR.json']=encoded(data)
        meta['LIBRARY-SOURCES.json']=encoded([dict(provenance=dict(documents={'CREDITS.md':'Author credit survives sharing.'}))])
        self.source.replace_art(art,metadata=meta);bundle=closure(self.source,identity);validate(bundle,self.tool)
        imported=import_bundle(self.target,bundle)
        incoming=next(i for i in self.target.art['images'] if i['id']==im['id'])
        self.assertEqual(incoming,art['images'][0])
        self.assertEqual(metadata(self.target)['pixel_layers'][im['id']],layers)
        again=closure(self.target,imported)
        self.assertEqual(again['provenance']['documents']['CREDITS.md'],'Author credit survives sharing.')
        self.assertEqual(again['editing']['catalogue'][imported]['tags'],['industrial'])

    def test_pattern_materializes_indexed_pixels_and_keeps_empty_cells(self):
        a=self.source.adventure;tile=a['tiles'][0]
        pattern=save_pattern(self.source,[[tile['id'],' '],[tile['id'],tile['id']]],'Pad')
        bundle=closure(self.source,pattern);self.assertEqual(bundle['kind'],'Pattern')
        self.assertEqual(bundle['tiles'][0]['sheet'],'package:art')
        validate(bundle,self.tool);imported=import_bundle(self.target,bundle)
        design=next(p for p in metadata(self.target)['map_patterns'] if p['id']==imported)
        self.assertEqual(design['rows'][0][1],' ')
        from editor_tiles import _package_tiles
        frame=bundle['images'][0]['frames'][0]
        self.assertEqual(frame[0],''.join(c[1:]+'ff' for c in _package_tiles(self.source)[tile['graphic']][0]))
        self.assertEqual(closure(self.target,imported)['images'],bundle['images'])

    def test_conflicts_remap_without_overwriting_and_undo_is_one_step(self):
        identity,bundle=self.style();import_bundle(self.target,bundle)
        before=self.target.files();history=len(self.target.undo_stack)
        revised=copy.deepcopy(bundle);revised['images'][0]['frames'][0][0]='00ff00ff'*16
        revised['tiles'][0]['terrain']='rough'
        new=import_bundle(self.target,revised)
        self.assertNotEqual(new,identity);self.assertEqual(len(self.target.undo_stack),history+1)
        old={im['id']:im for im in bundle['images']}
        for im in self.target.art['images']:
            if im['id'] in old:self.assertEqual(im,old[im['id']])
        self.target.undo();self.assertEqual(self.target.files(),before)
        self.target.redo();self.target.validate()

    def test_invalid_input_and_runtime_failure_leave_document_unchanged(self):
        _,bundle=self.style();before=self.target.files()
        for mutate in (lambda b:b['tiles'].pop(),
                       lambda b:b['images'][0].update(width=32),
                       lambda b:b['design'].update(footprint=[[100]])):
            broken=copy.deepcopy(bundle);mutate(broken)
            with self.assertRaises(EditorError):import_bundle(self.target,broken)
            self.assertEqual(self.target.files(),before)
        with patch.object(self.target,'validate',side_effect=EditorError('Rejected by native validator')):
            with self.assertRaises(EditorError):import_bundle(self.target,bundle)
        self.assertEqual(self.target.files(),before);self.assertFalse(self.target.undo_stack)

    def test_original_references_are_external_and_require_compatible_project(self):
        from editor_model import encoded
        original=create_project(ROOT/'examples/relay-contract',self.root/'original','original','Original resources',self.tool)
        tile=original.adventure['tiles'][0]
        pattern=save_pattern(original,[[tile['id']]],'CHI grass');bundle=closure(original,pattern)
        self.assertFalse(bundle['images']);validate(bundle,self.tool)
        before=self.target.files()
        with self.assertRaisesRegex(EditorError,'original CHI'):import_bundle(self.target,bundle)
        self.assertEqual(self.target.files(),before)
        import_bundle(original,bundle);original.validate()

    def test_library_persistence_revision_and_stale_failure(self):
        _,bundle=self.style();saved=self.library.save(bundle);path=self.library.path(saved['entry_id'])
        updated=copy.deepcopy(saved);updated['name']='New name';updated['design']['name']='New name'
        second=self.library.save(updated,expected=saved);self.assertEqual(second['revision'],2)
        with self.assertRaises(EditorError):self.library.save(updated,expected=saved)
        self.assertEqual(json.loads(path.read_bytes()),second)
        variant=self.library.save(second,variant=True)
        self.assertNotEqual(variant['entry_id'],saved['entry_id'])
        self.assertEqual(len(ConstructionLibrary(self.library.root,self.tool).entries()),2)

    def test_catalogue_and_preview_are_readonly(self):
        from asset_catalogue import catalogue,search
        from authoring_visuals import contact_sheet
        _,bundle=self.style();saved=self.library.save(bundle);before=self.target.files()
        values=catalogue(self.target,'construction-library',construction_library=self.library.root)
        self.assertEqual(search(values,'construction_kind:Building')['total'],1)
        artifact=contact_sheet(self.target,values,self.root/'preview.svg')
        self.assertNotIn('diagnostic',artifact['artifact']['items'][0])
        self.assertEqual(self.target.files(),before)
        absent=self.root/'missing'
        self.assertEqual(catalogue(self.target,'construction-library',construction_library=absent),[])
        self.assertFalse(absent.exists())

    def test_command_import_draw_and_retained_review(self):
        from authoring_review import prepare,apply
        from authoring_contract import read_json
        _,bundle=self.style('Road');path=self.root/'road.construction.json';path.write_bytes(encoded(bundle))
        request=dict(api_version=1,request_id='road-style',project_id='target',expected_revision=revision(self.target),
            label='Import a premade road',scope=['*'],operations=[
                dict(op='construction.import',file=path.name,id='target:library-road'),
                dict(op='road.draw',map=self.target.adventure['maps'][0]['id'],style='target:library-road',start=[2,20],end=[8,20])])
        review=self.root/'review';prepare(self.target,request,review,base_dir=self.root)
        path.write_text('{}')  # Acceptance must use the reviewed bytes.
        before=self.target.files();before_revision=revision(self.target);apply(self.target,review)
        self.assertNotEqual(self.target.files(),before)
        self.assertIn('target:library-road',{s['id'] for s in metadata(self.target)['construction_sets']})
        self.target.undo();self.assertEqual(revision(self.target),before_revision)

    def test_cli_export_search_and_pattern_import(self):
        identity,_=self.style();self.source.save()
        def cli(*args):
            proc=subprocess.run([sys.executable,str(ROOT/'tools/author.py'),*map(str,args)],capture_output=True,text=True)
            self.assertEqual(proc.returncode,0,proc.stderr+proc.stdout);return json.loads(proc.stdout)
        result=cli('construction-export',self.source.root,'--id',identity,'--construction-library',self.library.root)
        exported=result['data'];self.assertTrue(Path(exported['file']).exists())
        result=cli('catalogue',self.target.root,'--source','construction-library','--construction-library',self.library.root)
        self.assertEqual(result['data']['total'],1)
        result=cli('construction-export',self.source.root,'--id',identity,'--entry',exported['id'],
            '--expected-revision',1,'--construction-library',self.library.root)
        self.assertEqual(result['data']['revision'],2)


if __name__=='__main__':unittest.main()
