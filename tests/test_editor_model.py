"""Real editor document transactions use the player/validator, without a GUI."""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from editor_model import EditorError, ProjectDocument, create_project

TOOL = Path(os.environ.get("BTP_PROJECT_TOOL", ROOT / "build/btp-project"))
PLAYER = Path(os.environ.get("BTP_HEADLESS", ROOT / "build/btech-headless"))


class EditorDocumentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="btp-editor-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / "project"
        shutil.copytree(ROOT / "examples/adventure-demo", self.project)
        self.doc = ProjectDocument(self.project, TOOL)

    def test_edit_undo_redo_save_and_player(self):
        before = (self.project / "content.json").read_bytes()
        content = copy.deepcopy(self.doc.content)
        content["mechs"][0]["name"] = "Edited patrol model"
        content["mechs"][0]["movement"]["walk"] = 6
        content["mechs"][0]["armor"]["left_arm"] = 10
        self.doc.replace(content)
        self.assertTrue(self.doc.dirty)
        self.assertEqual(before, (self.project / "content.json").read_bytes())
        self.doc.undo()
        self.assertFalse(self.doc.dirty)
        self.doc.redo()
        self.assertTrue(self.doc.dirty)
        self.doc.save()
        self.assertFalse(self.doc.dirty)
        reopened = ProjectDocument(self.project, TOOL)
        self.assertEqual(reopened.content, content)
        settings = {"player": str(PLAYER), "data": str(ROOT / "Original DOS"),
                    "dialogue-data": str(ROOT / "work/talk-data.bin"),
                    "combat-data": str(ROOT / "work/combat-data.bin"),
                    "world-data": str(ROOT / "work/world-data.bin")}
        command = reopened.play_command(settings, self.root / "editor-state")
        result = subprocess.run(command, cwd=self.root, check=True, capture_output=True, text=True, timeout=15)
        state = json.loads(result.stdout)
        self.assertEqual(state["map"], 16)
        self.assertEqual(state["authored_event"]["phase"], 2)
        self.assertIn("editor-state", command[-1])

    def test_invalid_edit_never_overwrites_disk(self):
        before = {p.name: p.read_bytes() for p in self.project.iterdir() if p.is_file()}
        content = copy.deepcopy(self.doc.content)
        content["mechs"][0]["movement"]["walk"] = 99
        self.doc.replace(content)
        with self.assertRaisesRegex(EditorError, "movement.walk"):
            self.doc.save()
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.project.iterdir() if p.is_file()})
        self.assertTrue(self.doc.dirty)

    def test_map_references_protect_deleted_roster_items(self):
        content = copy.deepcopy(self.doc.content)
        content["mechs"].pop()
        self.doc.replace(content)
        with self.assertRaisesRegex(EditorError, "unresolved ID"):
            self.doc.save()
        self.doc.undo()
        self.doc.validate()

    def test_duplicate_stable_ids_and_weapon_changes(self):
        mech = self.doc.duplicate("mechs", 0)
        weapon = self.doc.duplicate("weapons", 0)
        content = copy.deepcopy(self.doc.content)
        content["weapons"][-1]["damage"] = 8
        content["mechs"][-1]["loadout"][0]["weapon"] = weapon
        self.doc.replace(content)
        self.doc.save()
        self.assertEqual(mech, self.doc.content["mechs"][-1]["id"])
        self.assertEqual(len({w["id"] for w in self.doc.content["weapons"]}), 4)

    def test_external_content_and_map_edits_are_preserved(self):
        for name in ["content.json", "adventure.json", "project.json"]:
            doc = ProjectDocument(self.project, TOOL)
            data = (self.project / name).read_bytes() + b"\n"
            (self.project / name).write_bytes(data)
            with self.assertRaisesRegex(EditorError, "changed outside"):
                doc.save()
            self.assertEqual(data, (self.project / name).read_bytes())

    def test_noop_save_preserves_exact_package(self):
        before = (self.project / "content.json").read_bytes()
        result = self.doc.save()
        self.assertEqual(before, (self.project / "content.json").read_bytes())
        actual = subprocess.run([str(TOOL), "validate", str(self.project)], capture_output=True, text=True, check=True).stdout.strip()
        self.assertEqual(result, actual)

    def test_create_project_is_valid_and_copies_no_saves(self):
        (self.project / "private-save.btp").write_bytes(b"not a package input")
        target = self.root / "new project"
        doc = create_project(self.project, target, "new-project", "My new project", TOOL)
        self.assertEqual(doc.manifest["package_id"], "new-project")
        self.assertTrue((target / "adventure.json").exists())
        self.assertFalse((target / "private-save.btp").exists())
        with self.assertRaises(EditorError):
            create_project(self.project, target, "new-project", "Never overwrite", TOOL)
        bad = self.root / "bad"
        with self.assertRaises(EditorError):
            create_project(self.project, bad, "BAD ID", "Rejected", TOOL)
        self.assertFalse(bad.exists())


if __name__ == "__main__":
    unittest.main()
