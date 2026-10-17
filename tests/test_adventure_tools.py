"""Authored map/event format boundaries and saved continuation corruption."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[1]
TOOL = Path(os.environ.get("BTP_PROJECT_TOOL", ROOT / "build/btp-project"))
PLAYER = Path(os.environ.get("BTP_HEADLESS", ROOT / "build/btech-headless"))


class AdventureTools(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="btp-adventure-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / "project"
        shutil.copytree(ROOT / "examples/adventure-demo", self.project)
        self.path = self.project / "adventure.json"
        self.adventure = json.loads(self.path.read_bytes())

    def write(self):
        self.path.write_text(json.dumps(self.adventure), encoding="ascii")

    def validate(self, ok=True):
        p = subprocess.run([str(TOOL), "validate", str(self.project)], capture_output=True, text=True, timeout=15)
        self.assertEqual(p.returncode == 0, ok, p.stdout + p.stderr)
        return p.stdout + p.stderr

    def play(self, *args, ok=True):
        p = subprocess.run([str(PLAYER), "--project", str(self.project), "--data", str(ROOT / "Original DOS"),
            "--dialogue-data", str(ROOT / "work/talk-data.bin"), "--combat-data", str(ROOT / "work/combat-data.bin"),
            "--world-data", str(ROOT / "work/world-data.bin"), *map(str, args)],
            cwd=self.root, capture_output=True, text=True, timeout=15)
        self.assertEqual(p.returncode == 0, ok, p.stdout + p.stderr)
        return json.loads(p.stdout) if ok else p.stderr

    def test_fingerprint_includes_map_and_event_snapshot(self):
        digest = hashlib.sha256()
        for name in ["project.json", "content.json", "adventure.json"]:
            digest.update(hashlib.sha256((self.project / name).read_bytes()).digest())
        self.assertIn(digest.hexdigest(), self.validate())
        save = self.root / "game.btp"
        before = self.play("--save", save)
        self.assertEqual(before, self.play("--load", save))
        self.adventure["events"][1]["text"] += " Changed."
        self.write()
        self.assertIn("exact saved content", self.play("--load", save, ok=False))

    def test_missing_duplicate_and_unknown_references(self):
        edits = [lambda a: a["maps"][0]["entrances"][0].update(event="missing:node"),
                 lambda a: a["events"][1].update(next="missing:node"),
                 lambda a: a["events"][1].update(op="execute_shell"),
                 lambda a: a["events"][1].update(unrecognized=1),
                 lambda a: a["shops"][0]["stock"].append("missing:mech"),
                 lambda a: a["events"].append(dict(a["events"][0])),
                 lambda a: a["flags"].append(a["flags"][0])]
        original = self.path.read_text()
        for edit in edits:
            self.adventure = json.loads(original)
            edit(self.adventure)
            self.write()
            self.validate(ok=False)

    def test_map_rectangles_overlays_collision_and_spawns(self):
        edits = [lambda a: a["maps"][0]["rows"].append("."),
                 lambda a: a["maps"][0]["rows"].__setitem__(0, "?" * 32),
                 lambda a: a["maps"][1].update(origin=[64, 64]),
                 lambda a: a["maps"][0]["overlays"][0].update(at=[63, 63]),
                 lambda a: a["maps"][0]["entrances"][0].update(at=[24, 16]),
                 lambda a: a["encounters"][0]["enemies"][0].update(at=[127, 127]),
                 lambda a: a["start"].update(at=[127, 127]),
                 lambda a: a["tiles"][1].update(key=".")]
        original = self.path.read_text()
        for edit in edits:
            self.adventure = json.loads(original)
            edit(self.adventure)
            self.write()
            self.validate(ok=False)

    def test_bounded_cycles_pause_and_paginated_dialogue(self):
        self.adventure["events"][1]["text"] = "A long briefing. " * 55
        self.write()
        self.validate()
        save = self.root / "long.btp"
        first = self.play("--save", save)
        action = self.root / "accept.actions"
        action.write_text("accept\n")
        later = self.play("--load", save, "--replay", action, "--save", save)
        self.assertEqual(later["authored_event"]["page"], 1)
        self.assertEqual(later, self.play("--load", save))
        self.assertEqual(first["authored_event"]["node"], later["authored_event"]["node"])
        self.adventure["events"][1] = dict(id="frontier:welcome", op="flag", flag="frontier:hired", value=0, next="frontier:welcome")
        self.write()
        self.assertEqual(self.play()["authored_event"]["phase"], 6)

    def test_saved_node_flag_receipt_and_mode_rejected(self):
        save = self.root / "game.btp"
        self.play("--save", save)
        good = save.read_bytes()
        for offset, value in [(20059, 255), (20065 + 63, 1), (20057, 0), (20058, 5), (20062, 3), (20184, 1)]:
            bad = bytearray(good)
            bad[160 + offset] = value
            struct.pack_into("<I", bad, 8, zlib.crc32(bad[16:]))
            save.write_bytes(bad)
            self.assertIn("invalid", self.play("--load", save, ok=False))

    def test_choice_layout_and_long_word_pages(self):
        choice = self.adventure["events"][2]
        choice["text"] = "abcdefghijklm " * 17
        choice["options"] += [dict(label="Fourth", next="frontier:end"), dict(label="Fifth", next="frontier:end")]
        self.write()
        self.assertIn("text/choices", self.validate(ok=False))
        self.adventure = json.loads((ROOT / "examples/adventure-demo/adventure.json").read_bytes())
        self.adventure["events"][1]["text"] = "abcdefghijklm " * 73
        self.write()
        save = self.root / "pages.btp"
        self.play("--save", save)
        action = self.root / "accept.actions"
        action.write_text("accept\n")
        for expected in [1, 2, 3]:
            state = self.play("--load", save, "--replay", action, "--save", save)
            self.assertEqual(state["authored_event"]["page"], expected)
        self.assertEqual(self.play("--load", save, "--replay", action)["mode"], "local-exploration")


if __name__ == "__main__":
    unittest.main()
