"""Real tile chooser, live map images and editable loops on a private display."""
def run(env,work):
    import copy
    import os
    from pathlib import Path
    import tempfile
    import time
    import tkinter as tk
    from tkinter import messagebox
    from unittest.mock import patch
    from PIL import ImageGrab
    from editor_model import create_project,ProjectDocument
    from editor_workspace import Workspace
    from tile_browser import TileBrowser
    from tile_editing import ensure_tile,select_tile,tile
    from tile_animation import tile_loop
    from editor_session import apply_draft
    from adventure_editing import paint
    from world_editing import token

    root=Path(__file__).resolve().parents[1];work=Path(work);os.environ['DISPLAY']=env['DISPLAY']
    with tempfile.TemporaryDirectory(prefix='editor-tile-animation-',dir=work) as directory:
        tmp=Path(directory);tool=root/'build/btp-project'
        doc=create_project(root/'examples/adventure-demo',tmp/'game','tile-animation-smoke','Animated terrain',tool)
        window=tk.Tk();workspace=None;errors=[]
        window.report_callback_exception=lambda kind,error,tb:errors.append(error)
        def pump():
            window.update()
            if errors:raise errors.pop(0)
        def wait(seconds):
            until=time.monotonic()+seconds
            while time.monotonic()<until:pump();time.sleep(.008)
        def rgb(image):return tuple(tuple(image.get(x,y) for x in range(16)) for y in range(16))
        def reject(title,message,**_):raise AssertionError(str(message))
        with patch.object(messagebox,'showerror',reject):
            try:
                workspace=Workspace(window,tool,tmp/'settings');window.geometry('1440x930+0+0')
                app=workspace.app;app.settings['data']=str(root/'Original DOS');app.set_document(doc);app.edit_adventure()
                maps=app.map_editor;pump()
                source=ensure_tile(doc,'chi:land',105)
                a=copy.deepcopy(doc.adventure)
                for y in range(3,6):
                    for x in range(3,9):paint(a['maps'][0],-1,x,y,token(tile(doc,source)))
                maps.commit(a);maps.zoom_control.set(48);pump()
                picture=maps.tile_image('chi:land',105,16);static=maps.tile_image('chi:destroyed',105,16)
                before,revision=doc.files(),doc.revision;still=rgb(static)
                seen=[]
                for phase in range(3):
                    maps.tile_animation.refresh(phase*.128+.001);seen.append(rgb(picture))
                assert len(set(seen))==3 and rgb(static)==still
                assert doc.files()==before and doc.revision==revision
                automatic=set();deadline=time.monotonic()+1.2
                while len(automatic)<3 and time.monotonic()<deadline:
                    pump();automatic.add(rgb(picture));time.sleep(.01)
                assert automatic==set(seen)
                maps.tile_animation.enabled.set(False);maps.tile_animation.refresh();paused=rgb(picture);wait(.2)
                assert rgb(picture)==paused==seen[0]
                maps.tile_animation.enabled.set(True);maps.tile_animation.refresh();pump()
                ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'editor-animated-map.png')
                print('PASS: original force-field map/thumbnail cycles through three frames; destroyed bank stays static, Pause freezes and preview leaves history clean.',flush=True)

                chooser=TileBrowser(maps);chooser.sheet.set('All tiles');chooser.animated_only.set(True);chooser.refresh();pump()
                assert set(chooser.keys)=={('chi:land',n) for n in (87,88,89,90,91,105,106,107,111,113)}
                assert len(chooser.canvas.find_withtag('animated-badge'))==10
                chooser.select(('chi:land',105));assert '128 ms/frame' in chooser.status.get()
                ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'editor-animated-tile-picker.png')
                chooser.clone();pump();cloned=chooser.source();image_id=cloned['graphic'];identity=cloned['id']
                owned=next(im for im in doc.art['images'] if im['id']==image_id)
                assert len(owned['frames'])==3 and owned['frame_ticks']==4
                chooser.close();chooser=TileBrowser(maps);pump()
                assert chooser.animated_only.get() and chooser.selected==identity
                chooser.close();select_tile(maps,identity)
                editor=maps.edit_tile_pixels(dict(map=maps.scene()['id'],at=[4,4]));pump()
                assert editor.frame_time.get()=='128 ms' and len(editor.frame['values'])==3
                editor.frame_time.set('64 ms');editor.change_frame_time();editor.add_frame();apply_draft(editor);pump()
                assert len(tile_loop(maps.graphics,'package:art',image_id).frames)==4
                assert tile_loop(maps.graphics,'package:art',image_id).ticks==2
                doc.validate();doc.save();assert ProjectDocument(doc.root,tool).art==doc.art
                editor.play();wait(.15);editor.play();pump()
                assert editor.animation_job is None
                print('PASS: Animated only selects original electric tiles; Clone retains frames/timing, chooser remembers its filter, custom frame count/duration edit and save/reopen succeed.',flush=True)

                # All designers share the same cached PhotoImage. They update
                # in place without redrawing (which would reset scroll/editing).
                for kind in ('Building','Wall','Road'):
                    designer=maps.construction(kind);designer.assign(identity);pump()
                    key=('package:art',image_id,designer.preview_size)
                    preview=maps.images[key]
                    assert any(designer.preview.itemcget(item,'image')==str(preview) for item in designer.preview.find_all() if designer.preview.type(item)=='image')
                    items=designer.preview.find_all();unchanged=doc.files()
                    maps.tile_animation.refresh(.001);first=preview.get(0,0)
                    maps.tile_animation.refresh(.065)
                    assert preview.get(0,0)!=first or tile_loop(maps.graphics,'package:art',image_id).frames[0][0][0]==tile_loop(maps.graphics,'package:art',image_id).frames[1][0][0]
                    assert designer.preview.find_all()==items and doc.files()==unchanged
                    assert len(tile_loop(maps.graphics,'package:art',image_id).frames)==4
                print('PASS: building, wall and road designers display the same live tile frames without changing preview geometry or project data.',flush=True)
                clock=maps.tile_animation
            finally:
                if workspace:workspace.play_session.shutdown();workspace.tasks.shutdown();workspace.closing=True
                window.destroy()
            assert clock.job is None
            print('PASS: closing the workspace cancels the terrain animation clock.',flush=True)
