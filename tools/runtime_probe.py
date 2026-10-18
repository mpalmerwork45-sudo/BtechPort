"""Bounded delivery check, runnable on a real Linux or Windows desktop."""
import json,os,subprocess,tempfile
from pathlib import Path
import tkinter as tk
from PIL import Image
from app_runtime import ROOT,binary
from launcher import Launcher
from editor_model import ProjectDocument
from editor_workspace import create_editor

def check():
    # The same code can be run on Windows with its packaged interpreter.
    # Importing Pillow alone misses native decoder/library loader failures.
    with tempfile.TemporaryDirectory(prefix='kit-runtime-') as tmp:
        tmp=Path(tmp);im=Image.new('RGBA',(8,8),(0,255,0,128));im.save(tmp/'probe.png')
        with Image.open(tmp/'probe.png') as read:assert read.getpixel((0,0))==(0,255,0,128)
        window=tk.Tk();errors=[];window.report_callback_exception=lambda kind,error,tb:errors.append(error)
        try:
            app=Launcher(window,tmp/'settings');window.update();assert window.title()=='BattleTech Construction Kit'
            editor=create_editor(tk.Toplevel(window),binary('btp-project'),tmp/'editor')
            doc=ProjectDocument(ROOT/'examples/beacon-demo',binary('btp-project'));editor.set_document(doc);window.update()
            editor.edit_adventure();window.update();assert editor.map_editor.canvas.winfo_width()>0
            if errors:raise errors[0]
            editor.close();window.update()
            (tmp/'actions').write_text('accept\nright\nleft\nmenu\ncancel\n')
            env=dict(os.environ,SDL_AUDIODRIVER='dummy')
            command=[str(binary('btech-port')),'--project',str(doc.root),'--smoke-replay','--smoke-fast','--replay',str(tmp/'actions'),'--frame',str(tmp/'frame.ppm')]
            result=subprocess.run(command,cwd=tmp,env=env,capture_output=True,text=True,timeout=20)
            if result.returncode:raise RuntimeError(result.stderr or result.stdout)
            assert (tmp/'frame.ppm').is_file()
        finally:window.destroy()
    print('PASS: packaged launcher, roster/map editor, PNG round trip, validator and SDL player.')

if __name__=='__main__':check()
