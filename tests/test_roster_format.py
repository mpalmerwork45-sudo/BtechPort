"""Exercise the runtime parser, including changes requiring no C rebuild."""
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "build/btp-roster-check"


@unittest.skipUnless(CHECKER.exists(), "build btp-roster-check first")
class RosterFormat(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / "content/updated/roster.json").read_text())

    def read(self, data, success=True):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "roster.json"
            path.write_text(data if isinstance(data, str) else json.dumps(data))
            result = subprocess.run([CHECKER, path], capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode == 0, success, result.stderr)
        if success:
            return json.loads(result.stdout)
        self.assertTrue(result.stderr.strip())

    def test_semantic_identity(self):
        expected = self.read(self.data)
        self.data["mechs"].reverse()
        self.assertEqual(self.read(json.dumps(self.data, sort_keys=True, indent=4)), expected)
        self.data["mechs"][0]["price"] += 1
        self.assertNotEqual(self.read(self.data)["fingerprint"], expected["fingerprint"])

    def test_fourth_model_without_rebuild(self):
        extra = copy.deepcopy(self.data["mechs"][0])
        extra.update(id="chi-expanded:test-model", name="TEST MODEL", save_code=163, price=1000)
        self.data["mechs"].append(extra)
        self.assertEqual(self.read(self.data)["mechs"][-1]["id"], "chi-expanded:test-model")

    def test_rejected_definitions(self):
        changes = [("id", "outside:panther"), ("name", "X" * 16), ("save_code", 200),
                   ("walk", 0), ("jump", 13), ("price", -1), ("mass_tons", 101),
                   ("sprite", "missing"), ("external_heat_sinks", [255] * 8),
                   ("structure", [0] * 8), ("armor", [255] * 11), ("walk", True),
                   ("price", 42949672960), ("unknown", 1), ("name", "A\\B")]
        for key, value in changes:
            with self.subTest(key=key, value=value):
                data = copy.deepcopy(self.data)
                data["mechs"][0][key] = value
                self.read(data, False)
        for field in ("id", "save_code"):
            data = copy.deepcopy(self.data)
            data["mechs"][1][field] = data["mechs"][0][field]
            self.read(data, False)
        for field, value in (("weapon", "unknown"), ("location", "turret"), ("ammo", 1)):
            data = copy.deepcopy(self.data)
            data["mechs"][0]["loadout"][0][field] = value
            self.read(data, False)

    def test_malformed_inputs(self):
        raw = json.dumps(self.data)
        for text in ("", "{}", raw + "true", raw[:-1], raw.replace('"walk": 4', '"walk": 04'),
                     raw.replace('"walk": 4', '"walk": 4, "walk": 4'), " " * 65537,
                     raw.replace('"mechs": [', '"mechs": [,')):
            with self.subTest(text=text[:40]):
                self.read(text, False)


if __name__ == "__main__":
    unittest.main()
