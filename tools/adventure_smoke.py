"""Held authored scenes through real SDL input and the shared save codec."""
import json
from pathlib import Path
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def run(env, work, battletech=False):
    from reference_session import WindowKeys
    env = dict(env, SDL_AUDIODRIVER="dummy")
    with tempfile.TemporaryDirectory(prefix="adventure-ui-", dir=work) as directory:
        tmp = Path(directory)
        prefix = tmp / "fixture"
        inputs = [ROOT / "Original DOS", work / "talk-data.bin", work / "combat-data.bin", work / "world-data.bin"]
        project = ROOT / ("examples/battletech-demo" if battletech else "examples/adventure-demo")
        title = "BattleTech - Last Beacon" if battletech else "Frontier authoring demo"
        package = "battletech-beacon" if battletech else "frontier"
        test = "btp-battletech-demo-tests" if battletech else "btp-adventure-tests"
        subprocess.run([str(ROOT / "build" / test), *map(str, inputs), str(project), str(prefix)],
                       cwd=tmp, check=True, capture_output=True, text=True, timeout=30)
        args = ["--project", project, *[arg for key, value in zip(["data", "dialogue-data", "combat-data", "world-data"], inputs) for arg in ("--" + key, value)]]
        labels = (["welcome", "town", "broker", "recruit", "overview", "road-enemies", "road-combat", "road-victory", "second-contract", "relay-enemies", "relay-combat", "ending"]
                  if battletech else ["welcome", "map", "entrance", "choices", "broker", "purchase", "recruit", "combat", "victory", "overview"])
        for label in labels:
            slot, final, frame = tmp / f"{label}.btp", tmp / f"{label}-final.btp", work / f"adventure-{label}.ppm"
            process = subprocess.Popen([str(ROOT / "build/btech-port"), *map(str, args), "--load", f"{prefix}-{label}.btp",
                "--save-file", str(slot), "--save", str(final), "--frame", str(frame)], cwd=tmp, env=env,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            keys = WindowKeys()
            try:
                window = None
                for _ in range(200):
                    matches = [w for w, window_title in keys.windows() if title == window_title]
                    if len(matches) == 1:
                        window = matches[0]
                        break
                    if process.poll() is not None:
                        raise RuntimeError(process.communicate()[1])
                    time.sleep(.025)
                if window is None:
                    raise RuntimeError("Authored player window did not appear")
                keys.key(window, "F5")
                keys.key(window, "F9")
                keys.key(window, "Ctrl+Shift+Escape")
                out, err = process.communicate(timeout=15)
                assert process.returncode == 0 and not err, err
                assert slot.with_name(slot.stem + "-project-" + package + ".btp").read_bytes()[:4] == b"BTG1"
                restored = tmp / "restored.ppm"
                headless = subprocess.run([str(ROOT / "build/btech-headless"), *map(str, args), "--load", str(final), "--frame", str(restored)],
                    cwd=tmp, capture_output=True, text=True, check=True, timeout=10)
                assert json.loads(out)["state_digest"] == json.loads(headless.stdout)["state_digest"], label
                assert frame.read_bytes() == restored.read_bytes(), label
                print(f"PASS: authored {label}, F5/F9, same SDL/headless state and pixels.", flush=True)
            finally:
                keys.x.XCloseDisplay(keys.display)
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=5)
        if battletech:
            replay = subprocess.run([str(ROOT / "build/btech-port"), *map(str, args),
                "--smoke-replay", "--smoke-fast", "--replay", str(prefix) + ".actions"],
                cwd=tmp, env=env, capture_output=True, text=True, timeout=60)
            assert replay.returncode == 0, replay.stderr
            state = json.loads(replay.stdout)
            assert state["mode"] == "ending" and state["credits"] == 41000, state
            assert state["authored_event"]["flags"] == [1, 0, 1, 1, 1, 1, 1], state
            print("PASS: complete BattleTech contract route through real SDL, both battles and final payment.", flush=True)


def editor(env, work):
    import os
    import tkinter as tk
    from PIL import ImageGrab
    from editor_model import ProjectDocument, create_project
    from roster_editor import RosterEditor
    os.environ["DISPLAY"] = env["DISPLAY"]
    with tempfile.TemporaryDirectory(prefix="editor-ui-", dir=work) as directory:
        tmp = Path(directory)
        tool = ROOT / "build/btp-project"
        document = create_project(ROOT / "examples/adventure-demo", tmp / "project", "editor-smoke", "Editor smoke", tool)
        window = tk.Tk()
        try:
            app = RosterEditor(window, tool, tmp / "settings")
            app.set_document(document)
            window.update()
            app.variables[("name",)][0].set("Editor patrol model")
            app.variables[("movement", "walk")][0].set("6")
            app.save()
            assert ProjectDocument(document.root, tool).content["mechs"][0]["name"] == "Editor patrol model"
            app.duplicate()
            assert len(app.document.content["mechs"]) == 3
            app.undo()
            assert len(app.document.content["mechs"]) == 2
            app.redo()
            app.save()
            app.kind.set("Weapons")
            app.change_kind()
            app.variables[("damage",)][0].set("8")
            app.save()
            assert app.document.content["weapons"][0]["damage"] == 8
            app.kind.set("Mechs")
            app.change_kind()
            window.update()
            ImageGrab.grab(xdisplay=env["DISPLAY"]).save(work / "roster-editor.png")
            app.notebook.select(4)
            window.update()
            app.mounts.selection_set("0")
            app.mount_dialog(False)
            window.update()
            dialog = next(w for w in window.winfo_children() if isinstance(w, tk.Toplevel))
            weapon_box = next(w for w in dialog.winfo_children() if w.winfo_class() == "TCombobox")
            weapon_box.set(app.document.content["weapons"][1]["id"])
            next(w for w in dialog.winfo_children() if w.winfo_class() == "TButton").invoke()
            app.save()
            assert app.item()["loadout"][0]["weapon"] == app.document.content["weapons"][1]["id"]
            app.notebook.select(4)
            window.update()
            ImageGrab.grab(xdisplay=env["DISPLAY"]).save(work / "roster-editor-loadout.png")
            # Launch the actual SDL player using the button's launch path.
            app.play()
            from reference_session import WindowKeys
            keys = WindowKeys()
            try:
                found = None
                for _ in range(200):
                    found = next((w for w, title in keys.windows() if title == "Editor smoke"), None)
                    if found:
                        break
                    time.sleep(.025)
                assert found, (tmp / "settings/player.log").read_text()
                keys.key(found, "Ctrl+Shift+Escape")
                time.sleep(.1)
            finally:
                keys.x.XCloseDisplay(keys.display)
            print("PASS: desktop forms, edits, duplicate, undo/redo, validation, save/reopen and Play launch.", flush=True)
        finally:
            window.destroy()
