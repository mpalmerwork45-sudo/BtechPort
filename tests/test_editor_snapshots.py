"""Fast worker snapshots must not weaken draft/history or baseline isolation."""
import copy
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from editor_model import create_project,EditorError
from editor_session import EditorScope
from editor_tasks import snapshot
from event_editing import editor_data,editor_commit
from campaign_source import convert


class Snapshots(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);root=Path(self.temp.name)
        doc=create_project(ROOT/'examples/beacon-demo',root/'game','snapshot-test','Snapshot test',ROOT/'build/btp-project')
        self.doc=convert(doc,root/'source');self.owner=SimpleNamespace(document=self.doc);self.scope=EditorScope(self.owner)
        for i in range(20):data=editor_data(self.doc);data['note']=str(i);editor_commit(self.doc,data)

    def test_worker_copies_all_current_and_baseline_state_without_history(self):
        before=copy.deepcopy(self.doc.__dict__);candidate=snapshot(self.scope)
        self.assertFalse(candidate.undo_stack or candidate.redo_stack)
        for name in ('content','adventure','art','manifest','metadata','snapshot','saved','saved_adventure','saved_art','saved_manifest','saved_metadata'):
            self.assertEqual(getattr(candidate,name),getattr(self.doc,name))
            value=getattr(candidate,name)
            if isinstance(value,dict):value['snapshot_test']=True
        candidate.source.index['notes']={'private':True};candidate.source.disk['private']=b'private'
        candidate.source.values['adventure']['start']['credits']=999
        for key,value in before.items():
            if key!='source':self.assertEqual(getattr(self.doc,key),value,key)
        self.assertNotIn('notes',self.doc.source.index);self.assertNotIn('private',self.doc.source.disk)
        self.assertNotEqual(self.doc.source.values['adventure']['start']['credits'],999)

    def test_fast_field_flush_preserves_existing_undo_and_redo(self):
        self.doc.undo();before=copy.deepcopy(self.doc.__dict__);self.scope.apply_pending()
        for key in ('content','adventure','metadata','revision','undo_stack','redo_stack','undo_labels','redo_labels'):
            self.assertEqual(getattr(self.doc,key),before[key])
        candidate=snapshot(self.scope);self.assertFalse(candidate.redo_stack)
        self.doc.redo();self.assertEqual(editor_data(self.doc)['note'],'19')

    def test_transaction_rollback_keeps_even_direct_history_mutations_isolated(self):
        before=copy.deepcopy(self.doc.__dict__)
        def bad():
            self.doc.undo();self.doc.adventure['start']['credits']=999
            self.doc.undo_stack[0][1]['start']['credits']=123
            self.doc.source.index['notes']={'broken':True}
            raise EditorError('Invalid operation')
        with self.assertRaises(EditorError):self.scope.transact(bad)
        for key in ('adventure','metadata','revision','undo_stack','redo_stack','undo_labels','redo_labels'):
            self.assertEqual(getattr(self.doc,key),before[key])
        self.assertEqual(self.doc.source.index,before['source'].index)

    def test_pending_field_is_in_candidate_only_and_invalid_text_survives(self):
        values={'credits':'1234'};view=SimpleNamespace(window=SimpleNamespace(winfo_exists=lambda:True),owner=self.owner)
        old=self.doc.adventure['start']['credits'];history=copy.deepcopy(self.doc.undo_stack)
        def apply():
            a=copy.deepcopy(self.doc.adventure);a['start']['credits']=int(values['credits']);self.doc.replace_adventure(a)
        self.scope.register(view,lambda:True,apply,lambda:dict(values),lambda state:values.update(state))
        candidate=snapshot(self.scope)
        self.assertEqual(candidate.adventure['start']['credits'],1234);self.assertEqual(self.doc.adventure['start']['credits'],old)
        self.assertEqual(self.doc.undo_stack,history)
        values['credits']='bad'
        with self.assertRaises(ValueError):self.scope.apply_pending()
        self.assertEqual(values['credits'],'bad');self.assertEqual(self.doc.undo_stack,history)


if __name__=='__main__':unittest.main()
