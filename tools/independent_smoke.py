"""Independent package and visual map/event editor checks on a private display."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]


def fixtures(work, directory):
    package=directory/"game"
    shutil.copytree(ROOT/"examples/beacon-demo",package)
    prefix=directory/"held"
    subprocess.run([str(ROOT/"build/btp-independent-tests"),str(package),str(prefix)],cwd=directory,check=True,capture_output=True,text=True,timeout=30)
    return package,prefix


def run(env,work):
    from reference_session import WindowKeys
    env=dict(env,SDL_AUDIODRIVER="dummy")
    with tempfile.TemporaryDirectory(prefix="beacon-ui-",dir=work) as directory:
        tmp=Path(directory);project,prefix=fixtures(work,tmp)
        # No original directory, cache paths, roster or art directory exists
        # in this working directory. Only the declared package is supplied.
        for label in ["welcome","town","npc","choice","recruit","wilderness","combat","victory","ending"]:
            slot=tmp/f"{label}.btp";final=tmp/f"{label}-final.btp";frame=work/f"beacon-{label}.ppm"
            process=subprocess.Popen([str(ROOT/"build/btech-port"),"--project",str(project),"--load",f"{prefix}-{label}.btp","--save-file",str(slot),"--save",str(final),"--frame",str(frame)],cwd=tmp,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            keys=WindowKeys()
            try:
                window=None
                for _ in range(240):
                    window=next((w for w,title in keys.windows() if title=="Last Beacon"),None)
                    if window:break
                    if process.poll() is not None:raise RuntimeError(process.communicate()[1])
                    time.sleep(.025)
                assert window,"Independent player did not appear"
                keys.key(window,"F5");keys.key(window,"F9");keys.key(window,"Ctrl+Shift+Escape")
                out,err=process.communicate(timeout=20)
                assert process.returncode==0 and not err,err
                assert slot.with_name(slot.stem+"-project-last-beacon.btp").read_bytes()[:4]==b"BTG1"
                restored=tmp/"restored.ppm"
                result=subprocess.run([str(ROOT/"build/btech-headless"),"--project",str(project),"--load",str(final),"--frame",str(restored)],cwd=tmp,capture_output=True,text=True,check=True,timeout=15)
                assert json.loads(out)["state_digest"]==json.loads(result.stdout)["state_digest"],label
                assert frame.read_bytes()==restored.read_bytes(),label
                print(f"PASS: independent {label}, SDL F5/F9, same headless state/pixels, no original inputs.",flush=True)
            finally:
                keys.x.XCloseDisplay(keys.display)
                if process.poll() is None:process.terminate();process.wait(timeout=5)
        # Execute the full recorded ordinary-input quest through SDL as well.
        result=subprocess.run([str(ROOT/"build/btech-port"),"--project",str(project),"--smoke-replay","--smoke-fast","--replay",str(prefix)+".actions"],cwd=tmp,env=env,capture_output=True,text=True,timeout=60)
        assert result.returncode==0,result.stderr
        state=json.loads(result.stdout);assert state["mode"]=="ending" and state["credits"]==4500 and state["authored_event"]["flags"]==[1,1,1],state
        print("PASS: complete independent quest through real SDL input, including Lua, combat and ending.",flush=True)


def editor(env,work):
    import tkinter as tk
    from tkinter import messagebox
    from unittest.mock import patch
    from PIL import ImageGrab
    from editor_model import ProjectDocument,create_project
    from roster_editor import RosterEditor
    os.environ["DISPLAY"]=env["DISPLAY"]
    def children(widget):
        for child in widget.winfo_children():
            yield child
            yield from children(child)
    with tempfile.TemporaryDirectory(prefix="map-editor-ui-",dir=work) as directory:
        tmp=Path(directory);tool=ROOT/"build/btp-project"
        doc=create_project(ROOT/"examples/beacon-demo",tmp/"game","map-editor-smoke","Map editor smoke",tool)
        window=tk.Tk()
        def error(title,message,**kwargs):raise AssertionError(message)
        with patch.object(messagebox,"showerror",error):
            try:
                app=RosterEditor(window,tool,tmp/"settings");app.set_document(doc);window.update();app.edit_adventure();ed=app.map_editor
                window.update()
                def dialog(title):
                    return next(w for w in children(window) if isinstance(w,tk.Toplevel) and w.title()==title)
                def field(title,key,value):
                    d=dialog(title);label=next(w for w in children(d) if w.winfo_class()=="TLabel" and str(w.cget("text"))==key.replace("_"," ").title())
                    row=label.grid_info()["row"];control=next(w for w in label.master.winfo_children() if w.grid_info().get("row")==row and w.grid_info().get("column")==1)
                    if control.winfo_class()=="TCombobox":control.set(str(value));control.event_generate("<<ComboboxSelected>>")
                    else:control.delete(0,"end");control.insert(0,str(value))
                def button(title,label="Apply"):
                    w=next(w for w in children(dialog(title)) if w.winfo_class()=="TButton" and str(w.cget("text"))==label);w.invoke();window.update()
                ed.new_map()
                for key,value in dict(id="smoke:map",name="Painted test map",width=16,height=16,origin_x=160,origin_y=64).items():field("New map",key,value)
                button("New map");assert ed.scene()["id"]=="smoke:map"
                ed.brush.selection_clear(0,"end");ed.brush.selection_set(4)
                ed.canvas.event_generate("<Button-1>",x=100,y=100);ed.canvas.event_generate("<ButtonRelease-1>",x=100,y=100);window.update()
                assert ed.scene()["rows"][4][4]=="#"
                ed.undo();assert ed.scene()["rows"][4][4]=="."
                ed.redo();assert ed.scene()["rows"][4][4]=="#"
                ed.new_overlay()
                for key,value in dict(x=2,y=2,width=3,height=3).items():field("Overlay bounds",key,value)
                button("Overlay bounds")
                ed.brush.selection_clear(0,"end");ed.brush.selection_set(1)
                ed.canvas.event_generate("<Button-1>",x=52,y=52);ed.canvas.event_generate("<ButtonRelease-1>",x=52,y=52);window.update()
                assert ed.scene()["overlays"][-1]["rows"][0][0]=="d"
                ed.tabs.select(1);ed.new_event();window.update()
                event_id=ed.event_id
                ed.event_text.delete("1.0","end");ed.event_text.insert("1.0","This dialogue was written with the event form.")
                ed.apply_event();ed.save();assert next(e for e in doc.adventure["events"] if e["id"]==event_id)["text"].startswith("This dialogue")
                # Change the same event into a branching choice using its type control.
                ed.event_vars["op"].set("choice")
                combo=next(w for w in ed.event_form.winfo_children() if w.winfo_class()=="TCombobox" and str(w.cget("textvariable"))==str(ed.event_vars["op"]))
                combo.event_generate("<<ComboboxSelected>>");window.update()
                ed.event_vars["label_1"].set("Investigate");ed.event_vars["choice_1"].set("beacon:end");ed.apply_event()
                ed.window.lift();window.update();ImageGrab.grab(xdisplay=env["DISPLAY"]).save(work/"event-editor.png")
                ed.tabs.select(0);window.update()
                ed.entrance_dialog(at=(14,14),npc=True)
                for key,value in dict(id="smoke:npc",name="Survey officer",person="beacon:mira",event=event_id).items():field("NPC / entrance",key,value)
                button("NPC / entrance")
                ed.encounter_dialog(at=(12,12));button("Encounter and enemy spawns","Add enemy");button("Enemy placement");button("Encounter and enemy spawns")
                # A roster edit and adventure edit are validated and saved together.
                app.variables[("name",)][0].set("GUI-authored patrol walker")
                ed.save();reopened=ProjectDocument(doc.root,tool)
                assert reopened.content["mechs"][0]["name"]=="GUI-authored patrol walker"
                assert reopened.adventure["maps"][-1]["entrances"][0]["person"]=="beacon:mira"
                assert reopened.adventure["encounters"][-1]["map"]=="smoke:map"
                exported=tmp/"export";doc.export(exported);ProjectDocument(exported,tool)
                ed.cursor=(12,12);ed.window.lift();window.update();ImageGrab.grab(xdisplay=env["DISPLAY"]).save(work/"map-editor.png")
                app.settings={"player":str(ROOT/"build/btech-port")};ed.play_here()
                from reference_session import WindowKeys
                keys=WindowKeys()
                try:
                    found=None
                    for _ in range(240):
                        found=next((w for w,title in keys.windows() if title=="Map editor smoke"),None)
                        if found:break
                        time.sleep(.025)
                    assert found,(tmp/"settings/player.log").read_text()
                    keys.key(found,"Ctrl+Shift+Escape");time.sleep(.1)
                finally:keys.x.XCloseDisplay(keys.display)
                print("PASS: real map painting, overlay, undo/redo, event/choice forms, NPC, encounter, combined save/reopen, export and Play here.",flush=True)
            finally:window.destroy()
