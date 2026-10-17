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

    def test_another_model_without_rebuild(self):
        extra = copy.deepcopy(self.data["mechs"][0])
        extra.update(id="chi-expanded:test-model", name="TEST MODEL", save_code=191, price=1000)
        self.data["mechs"].append(extra)
        self.assertEqual(self.read(self.data)["mechs"][-1]["id"], "chi-expanded:test-model")

    def test_original_three_unchanged(self):
        previous = json.loads((ROOT / "content/updated/versions/0.1.0.json").read_text())
        self.assertEqual(self.read(previous)["fingerprint"], 4022610150)
        self.assertEqual(self.data["mechs"][:3], previous["mechs"])

    def test_released_seventeen_unchanged(self):
        previous = json.loads((ROOT / "content/updated/versions/0.2.0.json").read_text())
        self.assertEqual(self.read(previous)["fingerprint"], 751321522)
        self.assertEqual(self.data["mechs"][:17], previous["mechs"])

    def test_new_ammunition_preserved(self):
        # Capacities from the cited MTF bins, including shared ammo split among
        # weapons in CHI. Do not silently multiply shared MG/LRM/SRM reserves.
        expected = {
            "phoenix-hawk-pxh-1": {"machine_gun": (2, 200)},
            "dragon-drg-1n": {"ac5": (1, 40), "lrm10": (1, 24)},
            "grasshopper-ghr-5h": {"lrm5": (1, 24)},
            "highlander-hgn-733": {"ac10": (1, 20), "lrm20": (1, 18), "srm6": (1, 30)},
            "stalker-stk-3f": {"lrm10": (2, 24), "srm6": (2, 30)},
            "jenner-jr7-d": {"srm4": (1, 25)},
            "javelin-jvn-10n": {"srm6": (2, 30)},
            "clint-clnt-2-3t": {"ac5": (1, 20)},
            "hermes-ii-her-2s": {"ac5": (1, 20)},
            "whitworth-wth-1": {"lrm10": (2, 24)},
            "urbanmech-um-r60": {"ac10": (1, 10)},
            "ostroc-osr-2c": {"srm4": (1, 25)},
        }
        for suffix, counts in expected.items():
            mech = next(m for m in self.data["mechs"] if m["id"] == "chi-expanded:" + suffix)
            for weapon, (count, rounds) in counts.items():
                with self.subTest(model=suffix, weapon=weapon):
                    mounts = [m for m in mech["loadout"] if m["weapon"] == weapon]
                    self.assertEqual((len(mounts), sum(m["ammo"] for m in mounts)), (count, rounds))

    def test_released_twenty_three_unchanged(self):
        previous = json.loads((ROOT / "content/updated/versions/0.3.0.json").read_text())
        self.assertEqual(self.data["mechs"][:23], previous["mechs"])
        self.assertEqual(self.read(previous)["fingerprint"], 1754795853)

    def test_shared_missile_ammunition_preserved(self):
        # Source CRD-3R has one 15-salvo SRM bin shared by two launchers;
        # Bear has three shared bins (45 salvos) across four launchers.
        for suffix, counts in (("crusader-crd-3r", {"srm6": (2, 15), "lrm15": (2, 16)}),
                               ("crusader-crd-3r-bear", {"srm6": (4, 45)})):
            mech = next(m for m in self.data["mechs"] if m["id"] == "chi-expanded:" + suffix)
            for weapon, (count, rounds) in counts.items():
                mounts = [m for m in mech["loadout"] if m["weapon"] == weapon]
                self.assertEqual((len(mounts), sum(m["ammo"] for m in mounts)), (count, rounds))
            self.assertEqual(sum(m["ammo"] for m in mech["loadout"] if m["weapon"] == "machine_gun"), 200)

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
