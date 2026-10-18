"""Data-integrity journeys for shared undo, reference replacement and recovery."""
import copy
import sys
import tempfile
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from editor_model import ProjectDocument, EditorError, create_project
from editor_dependencies import usages, remove
from editor_recovery import pack,unpack,restore_document,conflicts


class SafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.doc=create_project(ROOT/'examples/beacon-demo',Path(self.temp.name)/'game','safety','Safety',ROOT/'build/btp-project')

    def test_grouped_history_and_failed_command(self):
        old=copy.deepcopy(self.doc.content)
        with self.doc.command('Rename and rebalance'):
            changed=copy.deepcopy(old);changed['mechs'][0]['name']='Renamed';self.doc.replace(changed)
            changed['mechs'][0]['price']+=100;self.doc.replace(changed)
        self.assertEqual(self.doc.undo_labels,['Rename and rebalance'])
        self.doc.undo();self.assertEqual(old,self.doc.content)
        self.doc.redo();self.assertEqual(changed,self.doc.content)
        with self.assertRaises(EditorError):
            with self.doc.command('Rejected operation'):
                self.doc.replace(old);raise EditorError('reject')
        self.assertEqual(changed,self.doc.content)
        self.assertEqual(self.doc.undo_labels,['Rename and rebalance'])

    def test_used_weapon_deletion_requires_valid_replacement(self):
        weapons=self.doc.content['weapons'];old=copy.deepcopy(self.doc.content)
        identity=weapons[0]['id'];replacement=weapons[1]['id']
        self.assertTrue(usages(self.doc,identity))
        with self.assertRaisesRegex(EditorError,'used in'):remove(self.doc,identity)
        self.assertEqual(old,self.doc.content)
        remove(self.doc,identity,replacement)
        self.assertFalse(usages(self.doc,identity))
        self.assertNotIn(identity,[w['id'] for w in self.doc.content['weapons']])
        self.doc.undo();self.assertEqual(old,self.doc.content)

    def test_recovery_never_overwrites_conflicting_files(self):
        record=dict(version=1,baseline=self.doc.snapshot,library=None,state={k:copy.deepcopy(getattr(self.doc,k)) for k in ('content','adventure','art','manifest','metadata')})
        record['state']['content']['mechs'][0]['name']='Recovered'
        record=unpack(pack(record));restore_document(record,self.doc)
        self.assertEqual('Recovered',self.doc.content['mechs'][0]['name'])
        self.assertTrue(self.doc.dirty)
        file=self.doc.root/self.doc.manifest['definitions'];file.write_bytes(file.read_bytes()+b'\n')
        reopened=ProjectDocument(self.doc.root,self.doc.validator)
        self.assertTrue(conflicts(record,reopened))
        before=file.read_bytes()
        with self.assertRaises(EditorError):restore_document(record,reopened)
        self.assertEqual(before,file.read_bytes())


if __name__=='__main__':unittest.main()
