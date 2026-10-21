"""Campaign save recovery preserves slot identities and existing player progress."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import app_runtime


class CampaignSaveRecoveryTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(prefix='campaign-save-recovery-')
        self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name)
        self.source=self.root/'work';self.source.mkdir()
        self.state=self.root/'desktop'

    def test_both_editions_keep_slot_numbers_and_sources(self):
        originals={}
        for edition in ('','-updated'):
            for slot in range(1,7):
                suffix='' if slot==1 else '-'+str(slot)
                path=self.source/('player-save'+edition+suffix+'.btp')
                path.write_bytes(('saved '+edition+' '+str(slot)).encode())
                originals[path]=(path.read_bytes(),path.stat().st_mtime_ns)
        # Unrelated scratch saves must not be assigned to an empty campaign slot.
        (self.source/'test-save.btp').write_bytes(b'unrelated')
        for choice,edition in (('Original',''),('Updated','-updated')):
            restored=app_runtime.restore_legacy_campaign_saves(choice,self.state,self.source)
            self.assertEqual(len(restored),6)
            for source,target in restored:
                self.assertEqual(target.parent,self.state/'games'/choice.lower())
                self.assertEqual(target.name,source.name.replace('player-save','game'))
                self.assertEqual((target.read_bytes(),target.stat().st_mtime_ns),originals[source])
                self.assertEqual((source.read_bytes(),source.stat().st_mtime_ns),originals[source])
            self.assertEqual(app_runtime.restore_legacy_campaign_saves(choice,self.state,self.source),[])

    def test_existing_slots_and_missing_slots_are_preserved(self):
        (self.source/'player-save-updated.btp').write_bytes(b'older quicksave')
        (self.source/'player-save-updated-5.btp').write_bytes(b'old slot five')
        target=self.state/'games/updated/game-updated.btp';target.parent.mkdir(parents=True)
        target.write_bytes(b'new desktop progress');before=target.stat().st_mtime_ns
        restored=app_runtime.restore_legacy_campaign_saves('Updated',self.state,self.source)
        self.assertEqual([destination.name for _,destination in restored],['game-updated-5.btp'])
        self.assertEqual((target.read_bytes(),target.stat().st_mtime_ns),(b'new desktop progress',before))
        self.assertFalse((target.parent/'game-updated-2.btp').exists())
        self.assertEqual(app_runtime.restore_legacy_campaign_saves('My project',self.state,self.source),[])

    def test_default_launcher_resumes_recovered_campaigns(self):
        paths=app_runtime.default_settings()
        paths['player']=str(Path(os.environ.get('BTP_HEADLESS',ROOT/'build/btech-headless')).resolve())
        for choice,edition in (('Original',''),('Updated','-updated')):
            source=self.source/('player-save'+edition+'.btp')
            creation=subprocess.run([paths['player'],'--edition',choice.lower(),'--save',str(source)],
                                    cwd=ROOT,capture_output=True,text=True,timeout=20)
            self.assertEqual(creation.returncode,0,creation.stderr)
            before=json.loads(creation.stdout)['state_digest']
            with patch.object(app_runtime,'STATE',self.state),patch.object(app_runtime,'ROOT',self.root):
                command=app_runtime.game_command(choice,paths,self.state,resume=True)
                # Explicit private launch states remain isolated from recovery.
                private=self.root/'private'
                app_runtime.game_command(choice,paths,private)
                self.assertEqual(list(private.rglob('*.btp')),[])
            load=Path(command[command.index('--load')+1])
            self.assertEqual(load,self.state/'games'/choice.lower()/('game'+edition+'.btp'))
            result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(result.stdout)['state_digest'],before)
            self.assertEqual(load.read_bytes(),source.read_bytes())


if __name__=='__main__':unittest.main()
