"""Independent packages must play from their own declared, bounded inputs."""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
from editor_model import ProjectDocument,EditorError,create_project
from adventure_editing import paint,composite,event_template
TOOL=Path(os.environ.get("BTP_PROJECT_TOOL",ROOT/"build/btp-project"))
PLAYER=Path(os.environ.get("BTP_HEADLESS",ROOT/"build/btech-headless"))


class IndependentTools(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="btp-independent-");self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.game=self.root/"game"
        shutil.copytree(ROOT/"examples/beacon-demo",self.game)

    def edit(self,name,update):
        p=self.game/name;value=json.loads(p.read_text());update(value);p.write_text(json.dumps(value)+"\n")

    def play(self,*args,ok=True):
        result=subprocess.run([str(PLAYER),"--project",str(self.game),*map(str,args)],cwd=self.root,capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode==0,ok,result.stderr)
        return result

    def test_no_original_dependencies_and_strict_presentation_snapshot(self):
        state=json.loads(self.play("--save",self.root/"save.btp").stdout)
        self.assertEqual(state["mode"],"authored-event")
        self.assertEqual(state["combat_rules"],"enhanced")
        self.assertFalse((self.root/"Original DOS").exists())
        for name in ["presentation.json","contract.lua"]:
            p=self.game/name;old=p.read_bytes();p.write_bytes(old+b"\n")
            self.assertIn("exact saved content",self.play("--load",self.root/"save.btp",ok=False).stderr)
            p.write_bytes(old)
        self.play("--load",self.root/"save.btp")

    def test_missing_and_invalid_inputs_reject_without_fallback(self):
        p=self.game/"presentation.json";old=p.read_bytes();p.unlink()
        self.assertIn("missing reference",self.play(ok=False).stderr);p.write_bytes(old)
        for change in [lambda d:d["palette"].pop(),lambda d:d["tiles"][0].pop(),lambda d:d["font"].__setitem__(0,"ff"*7),lambda d:d["sounds"][0][0].__setitem__("ms",999999)]:
            p.write_bytes(old);self.edit("presentation.json",change);self.play(ok=False)
        p.write_bytes(old)
        self.edit("content.json",lambda d:d["presentations"][0].__setitem__("source","chi:locust"))
        self.assertIn("package sprite",self.play(ok=False).stderr)

    def test_play_here_is_new_and_checks_destination(self):
        state=json.loads(self.play("--play-here","beacon:wild",12,28).stdout)
        self.assertEqual((state["map"],state["x_half"],state["y_half"]),(17,12,28))
        self.assertEqual(state["mode"],"local-exploration")
        self.assertEqual(state["authored_event"]["flags"],[0,0,0])
        self.play("--play-here","missing:map",12,28,ok=False)
        self.play("--play-here","beacon:town",24,14,ok=False)
        self.play("--play-here","beacon:town",24,20,ok=False)
        self.play("--play-here","beacon:wild",12,28,"--load","absent.btp",ok=False)
        self.play("--intro-preview",ok=False)

    def test_lua_compile_references_and_path_bounds(self):
        (self.game/"contract.lua").write_text("if then bad end")
        self.assertIn("Lua",self.play(ok=False).stderr)
        (self.game/"contract.lua").write_text("return 1")
        self.edit("project.json",lambda d:d["scripts"][0].__setitem__("file","../elsewhere.lua"))
        self.assertIn("invalid path",self.play(ok=False).stderr)

    def test_lua_budget_and_no_libraries_have_no_effects(self):
        self.edit("adventure.json",lambda d:d["start"].__setitem__("event","beacon:office"))
        for source,reason in [("while true do end","instruction budget"),("return os.execute('bad')","nil"),("local s='x'; while true do s=s..s end","memory"),("return game.command('beacon:paid')","declared route")]:
            (self.game/"contract.lua").write_text(source)
            result=self.play();state=json.loads(result.stdout)
            self.assertIn(reason,result.stderr)
            self.assertEqual(state["credits"],2000)
            self.assertEqual(state["authored_event"]["node"],25)
            self.assertEqual(state["authored_event"]["flags"],[0,0,0])

    def test_editor_copies_exports_and_previews_every_declared_input(self):
        doc=create_project(self.game,self.root/"copy","my-beacon","My beacon",TOOL)
        self.assertTrue((doc.root/"contract.lua").exists())
        self.assertTrue((doc.root/"presentation.json").exists())
        a=copy.deepcopy(doc.adventure);a["maps"][0]["name"]="Edited town";doc.replace_adventure(a)
        content=copy.deepcopy(doc.content);content["mechs"][0]["name"]="Edited walker";doc.replace(content)
        doc.undo();self.assertEqual(doc.adventure["maps"][0]["name"],"Edited town")
        doc.redo();doc.save();self.assertFalse(doc.dirty)
        export=self.root/"export";doc.export(export)
        exported=ProjectDocument(export,TOOL)
        self.assertEqual(exported.snapshot,doc.snapshot)
        command=exported.play_command({"player":str(PLAYER)},self.root/"preview",here=("beacon:wild",12,28))
        self.assertNotIn("--data",command)
        state=json.loads(subprocess.run(command,cwd=self.root,capture_output=True,text=True,check=True,timeout=10).stdout)
        self.assertEqual(state["map"],17)

    def test_interrupted_multi_file_save_recovers_both_originals(self):
        doc=ProjectDocument(self.game,TOOL);before=dict(doc.snapshot)
        content=copy.deepcopy(doc.content);content["mechs"][0]["name"]="Interrupted edit";doc.replace(content)
        a=copy.deepcopy(doc.adventure);a["maps"][0]["name"]="Interrupted map";doc.replace_adventure(a)
        replace=ProjectDocument.atomic_file;count=0
        def interrupted(path,data):
            nonlocal count
            count+=1
            if count==2:raise SystemExit("simulated interruption")
            replace(path,data)
        with mock.patch.object(ProjectDocument,"atomic_file",side_effect=interrupted):
            with self.assertRaises(SystemExit):doc.save()
        self.assertTrue((self.game/".btp-editor-transaction.json").exists())
        recovered=ProjectDocument(self.game,TOOL)
        self.assertEqual(before,recovered.snapshot)
        self.assertFalse((self.game/".btp-editor-transaction.json").exists())

    def test_paint_and_event_edits_still_use_c_collision_validation(self):
        doc=ProjectDocument(self.game,TOOL);a=copy.deepcopy(doc.adventure)
        paint(a["maps"][0],1,9,5,"d")
        self.assertEqual(composite(a["maps"][0])[5][9],"d")
        paint(a["maps"][0],1,9,5," ")
        self.assertEqual(composite(a["maps"][0])[5][9],".")
        paint(a["maps"][0],0,12,14,"#");doc.replace_adventure(a)
        with self.assertRaises(EditorError):doc.save()
        doc.undo();e=event_template(doc,"say");a=copy.deepcopy(doc.adventure);a["events"].append(e);doc.replace_adventure(a);doc.save()


if __name__=="__main__":unittest.main()
