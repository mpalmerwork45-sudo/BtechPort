"""The Updated frontend defaults apply before a player makes a rule choice."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
PLAYER=Path(os.environ.get("BTP_HEADLESS",ROOT/"build/btech-headless"))


class UpdatedDefaults(unittest.TestCase):
    def play(self,*args):
        result=subprocess.run([str(PLAYER),"--data",str(ROOT/"Original DOS"),
            "--dialogue-data",str(ROOT/"work/talk-data.bin"),"--combat-data",str(ROOT/"work/combat-data.bin"),
            "--world-data",str(ROOT/"work/world-data.bin"),"--roster",str(ROOT/"content/updated/roster.json"),
            *map(str,args)],cwd=ROOT,capture_output=True,text=True,check=True,timeout=15)
        return json.loads(result.stdout)

    def test_fresh_updated_enhanced_original_legacy(self):
        self.assertEqual(self.play("--edition","updated")["combat_rules"],"enhanced")
        self.assertNotIn("combat_rules",self.play("--edition","original"))

    def test_dos_and_original_internal_import_receive_updated_default(self):
        with tempfile.TemporaryDirectory(prefix="btp-import-default-") as directory:
            original=Path(directory)/"original.btp"
            state=self.play("--edition","original","--load",ROOT/"Original DOS/GAME3","--save",original)
            self.assertNotIn("combat_rules",state)
            for source in [ROOT/"Original DOS/GAME3",original]:
                with self.subTest(source=source):
                    self.assertEqual(self.play("--edition","updated","--load",source)["combat_rules"],"enhanced")


if __name__=="__main__":unittest.main()
