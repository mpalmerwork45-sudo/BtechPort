"""Marker drags preserve authored identities and use one document undo step."""
import copy
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from adventure_editing import move_marker, scene_markers
from editor_model import EditorError, ProjectDocument

TOOL = Path(os.environ.get("BTP_PROJECT_TOOL", ROOT / "build/btp-project"))


def adventure_fixture():
    return dict(
        maps=[dict(id="game:town", name="Town", rows=["." * 16] * 16,
                   overlays=[], entrances=[
                       dict(id="game:door", name="Office", at=[4, 6], event="game:office"),
                       dict(id="game:npc", name="Pilot", at=[8, 10], event="game:hire", person="game:pilot")]),
              dict(id="game:field", name="Field", rows=["." * 16] * 16,
                   overlays=[], entrances=[])],
        encounters=[dict(id="game:ambush", map="game:town", party_at=[12, 14], enemies=[
            dict(kind="mech", definition="game:locust", at=[16, 18]),
            dict(kind="person", definition="game:guard", at=[20, 22])]),
            dict(id="game:other", map="game:field", party_at=[2, 2], enemies=[])],
        start=dict(map="game:town", at=[2, 2], event="game:start", credits=3000,
                   party=[dict(person="game:pilot", mech="game:locust")]))


class MarkerEditingTests(unittest.TestCase):
    def setUp(self):
        self.adventure = adventure_fixture()

    def marker(self, kind, enemy_index=None):
        return next(m for m in scene_markers(self.adventure, 0)
                    if m["ref"][0] == kind and m["ref"][3] == enemy_index)

    def test_enumeration_covers_markers_once_in_stable_order(self):
        markers = scene_markers(self.adventure, 0)
        self.assertEqual([m["ref"][0] for m in markers],
                         ["entrance", "npc", "party", "enemy", "enemy", "start"])
        self.assertEqual([m["ref"][3] for m in markers], [None, None, None, 0, 1, None])
        self.assertEqual(markers[-1]["ref"], ("start", "game:town", "start", None))
        self.assertTrue(all(m["label"] for m in markers))
        self.assertEqual([m["ref"][2] for m in scene_markers(self.adventure, 1)], ["game:other"])

    def test_descriptions_do_not_expose_document_coordinates(self):
        markers = scene_markers(self.adventure, 0)
        before = copy.deepcopy(self.adventure)
        for marker in markers:
            marker["at"][0] = 99
            marker["label"] = "Edited preview"
        self.assertEqual(self.adventure, before)

    def test_only_selected_coordinate_changes_for_every_kind(self):
        for kind, enemy_index in [("entrance", None), ("npc", None), ("party", None),
                                  ("enemy", 0), ("enemy", 1), ("start", None)]:
            with self.subTest(kind=kind, enemy_index=enemy_index):
                self.adventure = adventure_fixture()
                before = copy.deepcopy(self.adventure)
                selected = self.marker(kind, enemy_index)
                self.assertTrue(move_marker(self.adventure, 0, selected["ref"], [24, 26]))
                self.assertEqual(next(m["at"] for m in scene_markers(self.adventure, 0)
                                      if m["ref"] == selected["ref"]), [24, 26])
                # Moving back makes the complete structure byte-for-byte equivalent.
                move_marker(self.adventure, 0, selected["ref"], selected["at"])
                self.assertEqual(self.adventure, before)

    def test_party_and_each_enemy_move_independently(self):
        encounter = self.adventure["encounters"][0]
        move_marker(self.adventure, 0, self.marker("enemy", 1)["ref"], [21, 23])
        self.assertEqual(encounter["party_at"], [12, 14])
        self.assertEqual(encounter["enemies"][0]["at"], [16, 18])
        self.assertEqual(encounter["enemies"][1]["at"], [21, 23])
        move_marker(self.adventure, 0, self.marker("party")["ref"], [10, 12])
        self.assertEqual(encounter["enemies"][1]["at"], [21, 23])

    def test_refs_survive_door_and_encounter_reordering(self):
        door = self.marker("entrance")["ref"]
        enemy = self.marker("enemy", 1)["ref"]
        self.adventure["maps"][0]["entrances"].reverse()
        self.adventure["encounters"].reverse()
        move_marker(self.adventure, 0, door, [5, 7])
        move_marker(self.adventure, 0, enemy, [21, 23])
        self.assertEqual(self.adventure["maps"][0]["entrances"][1]["at"], [5, 7])
        self.assertEqual(self.adventure["encounters"][1]["enemies"][1]["at"], [21, 23])

    def test_halfstep_snapping_and_edges(self):
        ref = self.marker("start")["ref"]
        move_marker(self.adventure, 0, ref, [12.49, 13.5])
        self.assertEqual(self.adventure["start"]["at"], [12, 14])
        move_marker(self.adventure, 0, ref, [0, 31])
        self.assertEqual(self.adventure["start"]["at"], [0, 31])

    def test_out_of_bounds_or_invalid_coordinates_preserve_data(self):
        ref = self.marker("start")["ref"]
        for at in ([-1, 2], [32, 2], [2, -1], [2, 32], [float("nan"), 2],
                   [float("inf"), 2], ["3", 2], [True, 2], [2], None):
            with self.subTest(at=at):
                before = copy.deepcopy(self.adventure)
                with self.assertRaises(EditorError):
                    move_marker(self.adventure, 0, ref, at)
                self.assertEqual(self.adventure, before)

    def test_door_and_npc_overlap_is_rejected_but_spawn_overlap_is_not(self):
        before = copy.deepcopy(self.adventure)
        with self.assertRaisesRegex(EditorError, "already occupies"):
            move_marker(self.adventure, 0, self.marker("entrance")["ref"], [8, 10])
        self.assertEqual(self.adventure, before)
        # Do not reimplement the game's terrain/formation validator in the editor.
        move_marker(self.adventure, 0, self.marker("enemy", 0)["ref"], [8, 10])
        self.assertEqual(self.adventure["encounters"][0]["enemies"][0]["at"], [8, 10])

    def test_cross_map_deleted_and_malformed_refs_are_safe(self):
        ref = self.marker("enemy", 1)["ref"]
        self.adventure["encounters"][0]["enemies"].pop()
        stale_refs = [ref, ("npc", "game:town", "game:missing", None),
                      ("start", "game:town", "wrong-start", None),
                      ("enemy", "game:town", "game:ambush", False), (), None]
        for stale in stale_refs:
            with self.subTest(stale=stale):
                before = copy.deepcopy(self.adventure)
                with self.assertRaises(EditorError):
                    move_marker(self.adventure, 0, stale, [10, 12])
                self.assertEqual(self.adventure, before)
        with self.assertRaisesRegex(EditorError, "different map"):
            move_marker(self.adventure, 1, self.marker("entrance")["ref"], [10, 12])
        for index in (-1, 2, True, None):
            with self.assertRaises(EditorError):
                scene_markers(self.adventure, index)

    def test_no_op_returns_false(self):
        marker = self.marker("entrance")
        before = copy.deepcopy(self.adventure)
        self.assertFalse(move_marker(self.adventure, 0, marker["ref"], marker["at"]))
        self.assertEqual(self.adventure, before)

    @unittest.skipUnless(TOOL.is_file(), "Build btp-project for document integration")
    def test_complete_drag_is_one_undo_step_without_rewriting_package(self):
        doc = ProjectDocument(ROOT / "examples/beacon-demo", TOOL)
        before = copy.deepcopy(doc.adventure)
        draft = copy.deepcopy(before)
        ref = next(m["ref"] for m in scene_markers(draft, 0) if m["ref"][0] == "start")
        for at in ([25, 28], [26, 28], [27, 28], [28, 28]):
            move_marker(draft, 0, ref, at)
        doc.replace_adventure(draft)
        self.assertEqual(len(doc.undo_stack), 1)
        self.assertTrue(doc.dirty)
        doc.undo()
        self.assertEqual(doc.adventure, before)
        self.assertFalse(doc.dirty)
        doc.redo()
        self.assertEqual(doc.adventure, draft)
        doc.replace_adventure(copy.deepcopy(draft))
        self.assertEqual(len(doc.undo_stack), 1)
        # The normal document disk snapshot has never been written by this test.
        doc.unchanged_on_disk()


if __name__ == "__main__":
    unittest.main()
