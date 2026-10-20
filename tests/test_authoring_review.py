"""Preserved human edits, exact review proposals and dependency-complete subsets."""
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from editor_model import create_project,ProjectDocument,EditorError,encoded
from authoring_contract import AuthoringError,check_batch
from authoring_service import revision,apply_batch
from authoring_protection import edit_rule,rules,conflicts
import authoring_review as review

TOOL=Path(os.environ.get('BTP_PROJECT_TOOL',ROOT/'build/btp-project'))


class AuthoringReview(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='btp-review-');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.doc=create_project(ROOT/'examples/beacon-demo',self.root/'game','review-test','Review test',TOOL)

    def request(self,ops=None,**extra):
        return dict(api_version=1,request_id='review-request',project_id='review-test',expected_revision=revision(self.doc),
            label='Revise a mission',scope=['*'],operations=ops or [dict(op='object.patch',collection='events',id='beacon:welcome',changes={'text':'Revised briefing.'})],**extra)

    def protect_dialogue(self):
        edit_rule(self.doc,dict(id='dialogue',label='Hand-written briefing',kind='fields',path='adventure.events/beacon:welcome',fields=['text']))

    def test_review_is_read_only_and_retains_before_after(self):
        before=self.doc.files();history=len(self.doc.undo_stack)
        report=review.prepare(self.doc,self.request(),self.root/'review')
        self.assertEqual(report['status'],'ready',report)
        self.assertEqual(self.doc.files(),before);self.assertEqual(len(self.doc.undo_stack),history)
        self.assertTrue(report['artifacts'])
        self.assertEqual(report['changes'][0]['path'],'adventure.events/beacon:welcome')
        self.assertNotEqual(report['changes'][0]['before'],report['changes'][0]['after'])
        self.assertEqual(ProjectDocument(self.root/'review/before',TOOL).files(),before)
        review.apply(self.doc,self.root/'review',save=True)
        after=revision(self.doc);self.doc.undo();self.assertNotEqual(after,revision(self.doc))
        self.doc.redo();self.assertEqual(after,revision(self.doc))
        self.assertEqual(review.apply(self.doc,self.root/'review')['status'],'already_applied')

    def test_fields_conflict_requires_explicit_named_override(self):
        self.protect_dialogue();before=revision(self.doc);request=self.request()
        with self.assertRaisesRegex(AuthoringError,'Protected content'):apply_batch(self.doc,request)
        report=review.prepare(self.doc,request,self.root/'review')
        self.assertEqual(report['status'],'conflicts');self.assertEqual(report['conflicts'][0]['rule'],'dialogue')
        with self.assertRaises(AuthoringError):review.apply(self.doc,self.root/'review')
        self.assertEqual(before,revision(self.doc))
        review.apply(self.doc,self.root/'review',overrides=['dialogue'],save=True)
        self.assertEqual(rules(ProjectDocument(self.doc.root,TOOL)),rules(self.doc))
        self.assertEqual(review.read(self.root/'review')['approved_overrides'],['dialogue'])

    def test_map_region_also_protects_referenced_tile_properties(self):
        scene=self.doc.adventure['maps'][0];token=scene['rows'][4][4]
        tile=next(t for t in self.doc.adventure['tiles'] if t.get('key',t['id'])==token)
        edit_rule(self.doc,dict(id='roof',label='Roof detail',kind='map_region',map=scene['id'],rect=[4,4,1,1]))
        ops=[dict(op='object.patch',collection='tiles',id=tile['id'],changes={'mini_color':(tile['mini_color']+1)%16})]
        with self.assertRaisesRegex(AuthoringError,'Protected content'):apply_batch(self.doc,self.request(ops))
        other=copy.deepcopy(self.doc);a=copy.deepcopy(other.adventure);a['maps'][0]['name']='New town name';other.replace_adventure(a)
        self.assertEqual(conflicts(self.doc,other),[])

    def test_whole_object_and_entrance_field_protection(self):
        scene=self.doc.adventure['maps'][0];door=scene['entrances'][0]
        edit_rule(self.doc,dict(id='door',label='Moved doorway',kind='fields',path='adventure.entrances/'+door['id'],fields=['at']))
        op=dict(op='marker.move',map=scene['id'],kind='entrance',id=door['id'],at=[door['at'][0]+1,door['at'][1]])
        with self.assertRaises(AuthoringError):apply_batch(self.doc,self.request([op]))
        edit_rule(self.doc,dict(id='event',label='Keep this event',kind='object',path='adventure.events/beacon:welcome'))
        with self.assertRaises(AuthoringError):apply_batch(self.doc,self.request())

    def test_partial_groups_include_dependencies_and_validate_combination(self):
        ops=[dict(op='object.put',collection='events',value={'id':'review-test:end','op':'end'}),
             dict(op='object.patch',collection='events',id='beacon:welcome',changes={'next':'review-test:end'}),
             dict(op='object.patch',collection='maps',id='beacon:town',changes={'name':'Optional renamed town'})]
        request=self.request(ops,groups=[dict(id='target',label='Target event',operations=[0]),
            dict(id='route',label='New route',operations=[1],requires=['target']),dict(id='name',label='Town name',operations=[2])])
        report=review.prepare(self.doc,request,self.root/'partial',selected=['route'])
        self.assertEqual(set(report['selected']),{'route','target'});self.assertEqual(report['status'],'ready',report)
        review.apply(self.doc,self.root/'partial');self.assertNotEqual(self.doc.adventure['maps'][0]['name'],'Optional renamed town')
        self.doc.undo()
        # An undeclared dependency is still caught by the shared C validator.
        request['groups'][1].pop('requires')
        report=review.prepare(self.doc,request,self.root/'invalid',selected=['route'])
        self.assertEqual(report['status'],'failed')
        self.assertNotEqual(next(e for e in self.doc.adventure['events'] if e['id']=='beacon:welcome')['next'],'review-test:end')

    def test_selected_groups_cannot_duplicate_or_drop_operations(self):
        request=self.request(groups=[dict(id='wrong',label='Incomplete',operations=[0,0])])
        with self.assertRaises(AuthoringError):check_batch(request)

    def test_stale_live_and_stale_prepared_result_refused(self):
        review.prepare(self.doc,self.request(),self.root/'review');prepared=review.prepare_apply(self.doc,self.root/'review')
        a=copy.deepcopy(self.doc.adventure);a['maps'][0]['name']='New human edit';self.doc.replace_adventure(a)
        with self.assertRaises(AuthoringError):review.publish(self.doc,self.root/'review',prepared)
        with self.assertRaises(AuthoringError):review.apply(self.doc,self.root/'review')
        self.assertEqual(self.doc.adventure['maps'][0]['name'],'New human edit')

    def test_session_scope_and_cancellation_preserve_live_document(self):
        before=self.doc.files()
        report=review.prepare(self.doc,self.request(),self.root/'scope',allowed_scope=['adventure.maps'])
        self.assertEqual(report['status'],'failed');self.assertEqual(report['diagnostics'][0]['code'],'scope.denied')
        report=review.prepare(self.doc,self.request(),self.root/'cancel',cancelled=lambda:True)
        self.assertEqual(report['status'],'cancelled');self.assertEqual(before,self.doc.files())

    def test_discard_and_narrower_revision_are_retained(self):
        review.prepare(self.doc,self.request(),self.root/'review')
        report=review.decide(self.root/'review','request_changes','Keep the opening sentence.')
        self.assertEqual(report['status'],'changes_requested');self.assertEqual(report['history'][-1]['note'],'Keep the opening sentence.')
        with self.assertRaises(AuthoringError):review.apply(self.doc,self.root/'review')
        review.decide(self.root/'review','discard');self.assertTrue((self.root/'review/after/project.json').is_file())

    def test_interrupted_save_recovers_and_review_can_retry(self):
        self.doc.save();before=self.doc.files();review.prepare(self.doc,self.request(),self.root/'review')
        atomic=ProjectDocument.atomic_file;count=0
        def crash(path,payload):
            nonlocal count
            if Path(path).is_relative_to(self.doc.root):
                count+=1
                if count==2:raise SystemExit('simulated interruption')
            atomic(path,payload)
        with patch.object(ProjectDocument,'atomic_file',side_effect=crash):
            with self.assertRaises(SystemExit):review.apply(self.doc,self.root/'review',save=True)
        reopened=ProjectDocument(self.doc.root,TOOL)
        self.assertEqual(reopened.files(),before)
        self.assertEqual(review.read(self.root/'review')['status'],'applying')
        review.apply(reopened,self.root/'review',save=True)
        self.assertEqual(review.read(self.root/'review')['status'],'applied')

    def test_captured_imports_survive_source_change_and_tampering_is_refused(self):
        source=self.root/'route.lua';source.write_text('return "next"')
        request=self.request([dict(op='script.import',id='review-test:script',file='route.lua',target='route.lua')])
        report=review.prepare(self.doc,request,self.root/'review',base_dir=self.root)
        self.assertEqual(report['status'],'ready',report)
        source.write_text('this is no longer Lua')
        review.apply(self.doc,self.root/'review')
        self.assertEqual(self.doc.metadata['route.lua'],b'return "next"')
        captured=next(iter(report['imports'].values()))['file'];(self.root/'review'/captured).write_text('tampered')
        with self.assertRaisesRegex(AuthoringError,'retained import'):review.apply(self.doc,self.root/'review')

    def test_review_cannot_be_applied_to_another_editing_scope(self):
        review.prepare(self.doc,self.request(),self.root/'review')
        other_root=self.root/'library-edit';other_root.mkdir();self.doc.stage(other_root)
        other=ProjectDocument(other_root,TOOL)
        # Even identical package IDs/content cannot confuse game and library.
        with self.assertRaisesRegex(AuthoringError,'editing scope'):review.apply(other,self.root/'review')

    def test_partial_request_identity_stays_within_contract_limit(self):
        request=self.request([
            dict(op='object.patch',collection='maps',id='beacon:town',changes={'name':'Town'}),
            dict(op='object.patch',collection='events',id='beacon:welcome',changes={'text':'Text'})],
            groups=[dict(id='a',label='Map',operations=[0]),dict(id='b',label='Dialogue',operations=[1])])
        request['request_id']='r'*96
        selected,_=review.selected_request(request,['a']);check_batch(selected)
        self.assertEqual(len(selected['request_id']),96)

    def test_proposal_check_attaches_exact_candidate_and_refuses_tampering(self):
        self.doc.save();before=self.doc.files()
        record=review.prepare(self.doc,self.request(),self.root/'review')
        report=review.check_candidate(self.root/'review',TOOL,analyzer=ROOT/'build/btp-author-analyze')
        check=review.read(self.root/'review')['checks'][0]
        self.assertEqual(check['revision'],record['result_revision']);self.assertEqual(check['result'],report)
        self.assertEqual(before,self.doc.files())
        candidate=ProjectDocument(self.root/'review/after',TOOL);a=copy.deepcopy(candidate.adventure)
        a['maps'][0]['name']='Changed after review';candidate.replace_adventure(a);candidate.save()
        with self.assertRaisesRegex(AuthoringError,'Retained candidate changed'):
            review.check_candidate(self.root/'review',TOOL,analyzer=ROOT/'build/btp-author-analyze')

    def test_reshaping_reports_displaced_human_details(self):
        ops=[dict(op='construction.style',value=dict(id='review-test:building',name='Depot',kind='Building',footprint=[[1,1],[1,1]],parts={})),
             dict(op='construction.draw',id='review-test:depot',map='beacon:wild',style='review-test:building',start=[3,3],end=[5,5],shape='Rectangle',stories=1),
             dict(op='map.paint',map='beacon:wild',tile='beacon:grass',start=[4,4])]
        apply_batch(self.doc,self.request(ops))
        request=self.request([dict(op='construction.draw',id='review-test:depot',map='beacon:wild',
            style='review-test:building',start=[3,3],end=[5,5],shape='Rectangle',stories=1,erase=True)])
        request['request_id']='remove-building'
        report=review.prepare(self.doc,request,self.root/'review')
        self.assertEqual(report['status'],'ready',report)
        self.assertTrue(any(item['at']==[4,4] and item['tile']=='beacon:grass' for item in report['displaced_details']))

    def test_malformed_saved_protection_is_a_diagnostic(self):
        self.doc.metadata['EDITOR.json']=encoded({'authoring_protection':[dict(id='bad',label='Bad region',kind='map_region')]})
        with self.assertRaisesRegex(AuthoringError,'missing or unrelated'):rules(self.doc)


if __name__=='__main__':unittest.main()
