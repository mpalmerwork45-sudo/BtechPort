"""The authoring CLI and both players share the C loader, not a Python model."""
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "build/btp-project"
PLAYER = ROOT / "build/btech-headless"


class ProjectTools(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="btp-project-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / "project"
        shutil.copytree(ROOT / "examples/project-demo", self.project)
        self.content = json.loads((self.project / "content.json").read_text())
        self.manifest = json.loads((self.project / "project.json").read_text())

    def write(self):
        (self.project / "content.json").write_text(json.dumps(self.content))
        (self.project / "project.json").write_text(json.dumps(self.manifest))

    def run_tool(self, *args, ok=True):
        p = subprocess.run([str(TOOL), *map(str, args)], cwd=self.root,
                           capture_output=True, text=True, timeout=20)
        self.assertEqual(p.returncode == 0, ok, p.stdout + p.stderr)
        return p.stdout + p.stderr

    def play(self, *args, ok=True, dependencies=True):
        command = [str(PLAYER), "--project", str(self.project)]
        if dependencies:
            for option, path in [("--data", "Original DOS"),
                                 ("--dialogue-data", "work/talk-data.bin"),
                                 ("--combat-data", "work/combat-data.bin"),
                                 ("--world-data", "work/world-data.bin")]:
                command += [option, str(ROOT / path)]
        p = subprocess.run(command + list(map(str, args)), cwd=self.root,
                           capture_output=True, text=True, timeout=20)
        self.assertEqual(p.returncode == 0, ok, p.stdout + p.stderr)
        return p

    def rejected(self, fragment):
        self.write()
        message = self.run_tool("validate", self.project, ok=False)
        self.assertIn(fragment, message)

    def test_shared_loader_and_exact_fingerprint(self):
        result = self.run_tool("validate", self.project)
        h = hashlib.sha256()
        for filename in ["project.json", "content.json"]:
            b = (self.project / filename).read_bytes()
            h.update(b)
            h.update(len(b).to_bytes(8, "little"))
        self.assertIn(h.hexdigest(), result)
        self.run_tool("validate-content", self.project / "content.json")
        self.play()  # Foreign working directory: no repository fallback.

    def test_explicit_dependencies_required(self):
        self.assertIn("explicit --data", self.play(ok=False, dependencies=False).stderr)

    def test_roundtrip_and_edits_require_new_campaign(self):
        save = self.root / "campaign.btp"
        first = json.loads(self.play("--save", save).stdout)
        self.assertEqual(first, json.loads(self.play("--load", save).stdout))
        saved = save.read_bytes()
        self.content["weapons"][0]["damage"] = 8
        self.write()
        self.assertIn("exact saved content", self.play("--load", save, ok=False).stderr)
        self.assertIn("Cannot overwrite", self.play("--save", save, ok=False).stderr)
        self.assertEqual(saved, save.read_bytes())
        self.play("--save", self.root / "edited.btp")

    def test_wrong_package_and_unbound_save(self):
        save = self.root / "campaign.btp"
        self.play("--save", save)
        p = subprocess.run([str(PLAYER), "--load", str(save)], cwd=ROOT,
                           capture_output=True, text=True, timeout=20)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("requires --project", p.stderr)
        self.content["package_id"] = self.manifest["package_id"] = "other-project"
        self.write()
        self.assertIn("exact saved content", self.play("--load", save, ok=False).stderr)

    def test_catalogue_limit_and_long_names(self):
        base = self.content["mechs"][0]
        self.content["mechs"] = []
        for index in range(256):
            mech = copy.deepcopy(base)
            mech["id"] = f"workshop:mech-{index}"
            mech["name"] = "A full authoring name much longer than fifteen characters"
            self.content["mechs"].append(mech)
        self.write()
        self.assertIn("256 mechs", self.run_tool("validate", self.project))
        self.play()
        self.content["mechs"].append(copy.deepcopy(base))
        self.rejected("at most 256")

    def test_new_model_and_supported_weapon_without_c_changes(self):
        weapon = copy.deepcopy(self.content["weapons"][0])
        weapon.update(id="workshop:new-laser", name="New experimental laser", label="New Laser", damage=9)
        self.content["weapons"].append(weapon)
        mech = copy.deepcopy(self.content["mechs"][0])
        mech.update(id="workshop:new-model", name="New custom patrol mech", label="New Model")
        mech["loadout"][0]["weapon"] = weapon["id"]
        self.content["mechs"].append(mech)
        self.write()
        self.assertIn("3 mechs, 4 weapons", self.run_tool("validate", self.project))
        self.play("--save", self.root / "new-model.btp")

    def test_missing_reference_and_case(self):
        self.content["mechs"][0]["loadout"][0]["weapon"] = "workshop:missing"
        self.rejected("unresolved definition ID")
        self.manifest["definitions"] = "Content.json"
        self.rejected("case-sensitive")

    def test_unknown_fields_behaviors_duplicate_ids(self):
        original = copy.deepcopy(self.content)
        self.content["weapons"][0]["behavior"] = "gauss"
        self.rejected("unsupported weapon behavior")
        self.content = copy.deepcopy(original)
        self.content["weapons"][1]["id"] = self.content["weapons"][0]["id"]
        self.rejected("duplicate definition ID")
        self.content = copy.deepcopy(original)
        self.content["mechs"][0]["invisibility"] = 1
        self.rejected("invisibility")
        self.content = copy.deepcopy(original)
        self.content["mechs"][0]["movement"]["walk"] = 13
        self.rejected("movement.walk")

    def test_capacities_and_ammo(self):
        self.content["mechs"][0]["loadout"][0]["ammunition"] = 12
        self.rejected("ammunition capacity")
        self.content["mechs"][0]["loadout"][0]["ammunition"] = 0
        self.content["mechs"][0]["external_heat_sinks"]["left_arm"] = 7
        self.rejected("body location capacity")

    def test_duplicate_keys_and_syntax_limits(self):
        f = self.project / "content.json"
        for text in ['{"format": "btp-content-v1", "format": "btp-content-v1"}',
                     '[' * 30 + '0' + ']' * 30, '{"bad": -1}', '{"bad": 1.2}',
                     '{"bad": 00}', '{"bad": "\\u0000"}', '{"bad": [1,]}',
                     '{"bad": 1}\x00', 'x' * 1048577]:
            f.write_text(text)
            self.run_tool("validate-content", f, ok=False)

    def test_paths_assets_and_no_fallback(self):
        for path in ["../content.json", "/content.json", "a\\b.json", "CON.json", "content.json/", "missing.json"]:
            self.manifest["definitions"] = path
            self.rejected("")
        self.manifest["definitions"] = "content.json"
        self.manifest["assets"] = [{"id": "workshop:broker", "slot": "broker", "file": "missing.anm"}]
        self.rejected("missing reference")
        shutil.copyfile(ROOT / "content/updated/art/broker.anm", self.project / "broker.anm")
        self.manifest["assets"][0]["file"] = "broker.anm"
        self.write()
        self.run_tool("validate", self.project)
        (self.project / "broker.anm").write_bytes(b"broken")
        self.run_tool("validate", self.project, ok=False)

    @unittest.skipIf(os.name == "nt", "symlink permission varies on Windows")
    def test_symlink_escape(self):
        outside = self.root / "outside.json"
        shutil.copyfile(self.project / "content.json", outside)
        (self.project / "content.json").unlink()
        (self.project / "content.json").symlink_to(outside)
        self.assertIn("symlink", self.run_tool("validate", self.project, ok=False))

    def test_export_original_roster_art_and_no_overwrite(self):
        exported = self.root / "exported"
        command = ["export", exported, "--roster", ROOT / "content/updated/roster.json", "--combat-data", ROOT / "work/combat-data.bin"]
        self.run_tool(*command)
        self.assertIn("31 mechs", self.run_tool("validate", exported))
        manifest = json.loads((exported / "project.json").read_text())
        self.assertEqual(len(manifest["assets"]), 11)
        before = (exported / "content.json").read_bytes()
        self.run_tool(*command, ok=False)
        self.assertEqual(before, (exported / "content.json").read_bytes())


if __name__ == "__main__":
    unittest.main()
