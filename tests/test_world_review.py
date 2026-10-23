"""World preservation includes indirect changes and exact composed previews."""
import copy
import json
import os
import subprocess
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from world_review_demo import create,request
from world_review import Surface,changes,overview
from world_editing import world_tile,get_world
from authoring_protection import edit_rule,conflicts,rules,world_region
from authoring_service import apply_batch,revision
from authoring_contract import AuthoringError
from editor_model import ProjectDocument,EditorError,encoded
from campaign_source import convert
import authoring_review as review

TOOL=Path(os.environ.get('BTP_PROJECT_TOOL',ROOT/'build/btp-project'))


class WorldReview(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='btp-world-review-');self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.doc=create(self.root/'game',TOOL)

    def candidate(self,fn):
        doc=copy.deepcopy(self.doc);a=copy.deepcopy(doc.adventure);fn(a);doc.replace_adventure(a);return doc

    def test_composed_rows_match_existing_city_patch_jigsaw_rules(self):
        surface=Surface(self.doc,'survey:aster')
        for y in (12,16,20,24,40):
            actual=surface.row(y)
            for x in range(128):self.assertEqual(actual[x],world_tile(self.doc.adventure,x,y,world_id='survey:aster'))
        self.assertEqual(surface.row(-1,100,4),[None]*4)
        self.assertEqual(surface.row(8,126,4)[2:],[None]*2)
        with self.assertRaises(AuthoringError):Surface(self.doc,'survey:absent')

    def test_protected_ground_and_town_layers_cannot_be_bypassed(self):
        for change in [lambda a:get_world(a,'survey:aster')['patches'].clear(),
                       lambda a:next(t for t in a['tiles'] if t['id']=='beacon:water').update(terrain='clear')]:
            other=self.candidate(change);self.assertEqual(conflicts(self.doc,other)[0]['world'],'survey:aster')
        # Editing a shared jigsaw changes protected ground even without an
        # edit to the world object. A different planet's patch stays allowed.
        edit_rule(self.doc,dict(id='ground',label='Survey ground',kind='world_region',world='survey:aster',rect=[40,40,3,3]))
        other=self.candidate(lambda a:next(j for j in a['jigsaws'] if j['id']=='survey:plain')['rows'][0].__setitem__(0,'beacon:water'))
        self.assertIn('ground',[c['rule'] for c in conflicts(self.doc,other)])
        other=self.candidate(lambda a:get_world(a,'survey:boreal')['patches'].append(dict(at=[44,12],rows=[['beacon:water']])) )
        self.assertEqual(conflicts(self.doc,other),[])
        edit_rule(self.doc,dict(id='town',label='Town roof',kind='world_region',world='survey:aster',rect=[62,18,2,2]))
        for change in [lambda a:a['maps'][1]['overlays'].append(dict(at=[2,2],rows=[['beacon:wall']])),
                       lambda a:a['maps'][1].update(origin=[61,16])]:
            self.assertIn('town',[c['rule'] for c in conflicts(self.doc,self.candidate(change))])

    def test_shared_art_is_protected_but_unrelated_names_and_metadata_are_allowed(self):
        from art_editing import new_image
        art=copy.deepcopy(self.doc.art);a=copy.deepcopy(self.doc.adventure)
        image=new_image('survey',art['images'],'Water pixels');art['images'].append(image)
        next(t for t in a['tiles'] if t['id']=='beacon:water').update(sheet='package:art',graphic=image['id'])
        self.doc.replace_art(art,adventure=a)
        tile=next(t for t in self.doc.adventure['tiles'] if t['id']=='beacon:water')
        other=copy.deepcopy(self.doc);art=copy.deepcopy(other.art)
        image=next(i for i in art['images'] if i['id']==tile['graphic']);image['frame_ticks']=image.get('frame_ticks',8)+1
        other.replace_art(art);self.assertTrue(conflicts(self.doc,other))
        other=self.candidate(lambda a:get_world(a,'survey:aster').update(name='Human planet name'))
        self.assertEqual(conflicts(self.doc,other),[])

    def test_removed_planet_never_falls_back_and_bounds_are_explicit(self):
        other=self.candidate(lambda a:a['worlds'].pop(0))
        self.assertTrue(conflicts(self.doc,other));self.assertIsNone(world_region(other,rules(self.doc)[0]))
        for value in [dict(world='survey:absent',rect=[0,0,1,1]),dict(world='survey:aster',rect=[127,0,2,1]),
                      dict(world='survey:aster',rect=[0,0,0,1]),dict(world='survey:aster',rect=[0,0,1,1],map='survey:home')]:
            with self.assertRaises(AuthoringError):edit_rule(self.doc,dict(id='bad',label='Bad rule',kind='world_region',**value))

    def test_review_conflicts_narrowing_artifacts_crop_and_one_undo(self):
        before=self.doc.files();baseline=revision(self.doc);report=review.prepare(self.doc,request(self.doc),self.root/'review')
        self.assertEqual(report['status'],'conflicts',report)
        with self.assertRaises(AuthoringError):review.apply(self.doc,self.root/'review')
        self.assertEqual(self.doc.files(),before)
        self.assertEqual({w['id'] for w in report['world_changes']},{'survey:aster','survey:boreal'})
        self.assertEqual(len([a for a in report['artifacts'] if a['kind']=='world']),4)
        after=ProjectDocument(self.root/'review/after',TOOL)
        for item in report['artifacts']:
            if item['kind']=='world':
                self.assertLessEqual(max(item['artifact']['rect'][2:])*item['artifact']['pixels_per_tile'],1024)
                self.assertIn('data:image/png;base64,',Path(item['artifact']['path']).read_text())
        chosen=review.recheck(self.doc,self.root/'review',self.root/'narrowed',['port','boreal'])
        self.assertEqual(chosen['status'],'ready',chosen)
        cropped=review.world_crop(self.root/'narrowed','survey:aster',[56,12,32,32],TOOL)
        self.assertEqual(len(cropped),2);self.assertEqual(cropped[0]['artifact']['pixels_per_tile'],16)
        self.assertEqual(review.world_crop(self.root/'narrowed','survey:aster',[56,12,32,32],TOOL),cropped)
        # Durable request receipts intentionally survive Undo, preventing an
        # external retry from resurrecting the edit the human just undid.
        review.apply(self.doc,self.root/'narrowed');self.doc.undo();self.assertEqual(revision(self.doc),baseline)
        self.doc.redo();self.doc.save();self.assertEqual(ProjectDocument(self.doc.root,TOOL).files(),self.doc.files())

    def test_source_projects_and_named_override_keep_policy(self):
        self.doc=convert(self.doc,self.root/'source');before=copy.deepcopy(self.doc.adventure);policy=rules(self.doc)
        command=request(self.doc);report=review.prepare(self.doc,command,self.root/'review')
        self.assertEqual(report['status'],'conflicts',report)
        review.world_crop(self.root/'review','survey:boreal',[80,0,32,32],TOOL)
        review.apply(self.doc,self.root/'review',overrides=['painted-pond'],save=True)
        self.assertEqual(rules(self.doc)[0]['id'],'painted-pond')
        self.assertEqual(review.read(self.root/'review')['approved_overrides'],['painted-pond'])
        # Saving source modules normalizes their JSON key order; Undo restores
        # authored content, while request receipts and that formatting persist.
        self.doc.undo();self.assertEqual(self.doc.adventure,before);self.assertEqual(rules(self.doc),policy)

    def test_presentation_pixels_and_palette_are_dependencies(self):
        other=copy.deepcopy(self.doc);name=other.manifest['presentation'];art=json.loads(other.snapshot[name])
        tile=next(t for t in other.adventure['tiles'] if t['id']=='beacon:water')
        index=int(art['tiles'][tile['graphic']][0][0],16);art['palette'][index]='ff00ff'
        other.snapshot[name]=encoded(art)
        self.assertTrue(conflicts(self.doc,other))
        self.assertTrue(changes(self.doc,other))

    def test_legacy_single_world_and_created_removed_planets(self):
        a=copy.deepcopy(self.doc.adventure);a['world']=a.pop('worlds')[0];self.doc.replace_adventure(a)
        self.doc.validate()
        self.assertEqual(Surface(self.doc,'survey:aster').width,128)
        other=self.candidate(lambda a:a['world'].update(name='New planet name'))
        self.assertEqual(changes(self.doc,other)[0]['changed_tiles'],0)
        added=copy.deepcopy(other);a=copy.deepcopy(other.adventure);a['worlds']=[a.pop('world')]
        a['worlds'].append(dict(a['worlds'][0],id='survey:moon',name='Moon',cities=[],patches=[]));added.replace_adventure(a)
        new=next(c for c in changes(other,added) if c['id']=='survey:moon')
        self.assertIsNone(new['before']);self.assertEqual(new['changed_tiles'],128*64)
        removed=next(c for c in changes(added,other) if c['id']=='survey:moon')
        self.assertIsNone(removed['after'])

    def test_cli_pair_capabilities_and_crop_budget(self):
        from authoring_inspect import capabilities
        cap=capabilities(TOOL)
        self.assertIn('world_region',cap['collaboration']['protection_kinds'])
        report=review.prepare(self.doc,request(self.doc),self.root/'review',visuals=False)
        self.assertEqual(len(report['world_changes']),2)
        command=[sys.executable,str(ROOT/'tools/author.py'),'review','world',str(self.root/'review'),
                 '--validator',str(TOOL),'--world','survey:aster','--rect','0','0','1','1']
        run=subprocess.run(command,capture_output=True,text=True,timeout=20)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        result=json.loads(run.stdout);self.assertEqual(len(result['artifacts']),2)
        for x in range(1,64):review.world_crop(self.root/'review','survey:aster',[x,0,1,1],TOOL)
        with self.assertRaisesRegex(AuthoringError,'64 detail crops'):review.world_crop(self.root/'review','survey:aster',[64,0,1,1],TOOL)
        cached=review.world_crop(self.root/'review','survey:aster',[0,0,1,1],TOOL)
        self.assertEqual(cached,result['artifacts'])
        Path(cached[0]['artifact']['path']).write_text('changed art')
        with self.assertRaisesRegex(AuthoringError,'preview changed'):review.world_crop(self.root/'review','survey:aster',[0,0,1,1],TOOL)

    def test_cancelled_and_invalid_detail_does_not_publish(self):
        review.prepare(self.doc,request(self.doc),self.root/'review',visuals=False)
        for rect in ([0,0,65,1],[-1,0,1,1],[0,0,0,1],[500,500,1,1]):
            with self.assertRaises(AuthoringError):review.world_crop(self.root/'review','survey:aster',rect,TOOL)
        with self.assertRaises(AuthoringError):review.world_crop(self.root/'review','survey:aster',[0,0,16,16],TOOL,cancelled=lambda:True)
        self.assertEqual(list((self.root/'review/world-crops').glob('*.json')),[])

    def test_invalid_references_fail_native_validation_before_composition(self):
        command=request(self.doc);command.pop('groups');command['scope']=['*']
        command['operations']=[dict(op='object.remove',collection='jigsaws',id='survey:plain')]
        before=revision(self.doc)
        with self.assertRaises(EditorError) as error:apply_batch(self.doc,command)
        self.assertIn('$.worlds[survey:aster].pieces[0][0]: unresolved id',str(error.exception).lower())
        self.assertEqual(revision(self.doc),before)

    def test_shared_tile_change_marks_worlds_without_world_object_edits(self):
        other=self.candidate(lambda a:next(t for t in a['tiles'] if t['id']=='beacon:grass').update(mini_color=4))
        changed=changes(self.doc,other)
        self.assertEqual(len(changed),2);self.assertTrue(all(w['changed_tiles']>7000 for w in changed))
        self.assertEqual([w['towns'] for w in changed],[[],[]])

    def test_large_rectangles_stay_bounded_and_cancellation_does_not_publish(self):
        # A full-sized planet is supported without per-cell tuple dictionaries.
        a=copy.deepcopy(self.doc.adventure);a['worlds']=a['worlds'][:1]
        a['maps'][2]['origin']=[128,16];a['worlds'][0]['cities'].append('survey:landing')
        a['worlds'][0]['pieces']=[['survey:plain']*128 for _ in range(128)];self.doc.replace_adventure(a)
        self.doc.validate()
        rule=dict(id='whole',label='Whole planet',kind='world_region',world='survey:aster',rect=[0,0,1024,1024])
        edit_rule(self.doc,rule);value=world_region(self.doc,rule);self.assertEqual(len(value['ground']),64)
        for i in range(2):edit_rule(self.doc,dict(rule,id='whole-'+str(i)))
        with self.assertRaises(AuthoringError):edit_rule(self.doc,dict(rule,id='over-budget'))
        with self.assertRaises(AuthoringError):conflicts(self.doc,self.doc,cancelled=lambda:True)
        other=self.candidate(lambda a:get_world(a,'survey:aster')['patches'].append(dict(at=[1023,1023],rows=[['beacon:water']])))
        change=changes(self.doc,other)[0];self.assertEqual(change['changed_tiles'],1);self.assertEqual(change['areas'][0]['rect'],[1023,1023,1,1])
        with self.assertRaises(AuthoringError):overview(self.doc,change,self.root/'cancelled.svg',cancelled=lambda:True)
        self.assertFalse((self.root/'cancelled.svg').exists())

    def test_stale_snapshot_refuses_detail_and_stale_live_refuses_apply(self):
        review.prepare(self.doc,request(self.doc),self.root/'review')
        candidate=ProjectDocument(self.root/'review/after',TOOL);a=copy.deepcopy(candidate.adventure);a['start']['credits']+=1;candidate.replace_adventure(a);candidate.save()
        with self.assertRaisesRegex(AuthoringError,'snapshot changed'):review.world_crop(self.root/'review','survey:aster',[0,0,32,32],TOOL)
        a=copy.deepcopy(self.doc.adventure);a['start']['credits']+=1;self.doc.replace_adventure(a)
        with self.assertRaises(AuthoringError):review.apply(self.doc,self.root/'review',overrides=['painted-pond'])


if __name__=='__main__':unittest.main()
