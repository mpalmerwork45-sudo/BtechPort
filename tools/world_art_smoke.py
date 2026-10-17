"""Private-display exercise of the real world and graphics editor widgets."""
def run(env,work):
    import copy
    import os
    from pathlib import Path
    import tempfile
    import tkinter as tk
    from tkinter import messagebox
    from unittest.mock import patch
    from PIL import ImageGrab
    from editor_model import create_project,ProjectDocument
    from roster_editor import RosterEditor
    from graphics_editor import PixelEditor
    from world_editor import JigsawEditor
    from world_editing import create_world,assign_city
    from art_editing import new_image,pixels
    root=Path(__file__).resolve().parents[1];os.environ['DISPLAY']=env['DISPLAY']
    with tempfile.TemporaryDirectory(prefix='world-art-ui-',dir=work) as temp:
        path=Path(temp);tool=root/'build/btp-project'
        doc=create_project(root/'examples/beacon-demo',path/'game','world-art-ui','World and art test',tool)
        window=tk.Tk();errors=[];window.report_callback_exception=lambda kind,error,tb:errors.append(error)
        def pump():
            window.update()
            if errors:raise errors.pop(0)
        def no_error(title,text,**kwargs):raise AssertionError(f'{title}: {text}')
        def gesture(canvas,start,end):
            canvas.event_generate('<ButtonPress-1>',x=start[0],y=start[1]);pump()
            canvas.event_generate('<B1-Motion>',x=end[0],y=end[1]);pump()
            canvas.event_generate('<ButtonRelease-1>',x=end[0],y=end[1]);pump()
        with patch.object(messagebox,'showerror',no_error):
            try:
                app=RosterEditor(window,tool,path/'settings');app.set_document(doc);app.edit_adventure();ed=app.map_editor;pump()
                ed.edit_graphics();library=ed.art_editor;pump()
                im=new_image('test',[]);library.put(im);pixel=PixelEditor(library,im);pump()
                pixel.color.set('aa4400ff');z=int(pixel.zoom.get());gesture(pixel.canvas,(1,1),(15*z+1,15*z+1))
                assert pixels(pixel.image)[15][15]=='aa4400ff'
                pixel.undo();assert pixels(pixel.image)[15][15]=='00000000'
                pixel.redo();pixel.add_frame();assert len(pixel.image['frames'])==2;pixel.apply();pump()
                library.use_tile();pump();assert doc.adventure['schema_version']==2
                assert ed.tile_image('package:art',im['id'],16).get(15,15)==(170,68,0)
                a=copy.deepcopy(doc.adventure);create_world(a,'test');assign_city(a,'beacon:town');assign_city(a,'beacon:wild');ed.commit(a)
                ed.edit_landscape();world=ed.world_editor;world.window.geometry('1040x760+0+0');pump()
                j=JigsawEditor(world,world.selected_jigsaw());j.tile.set(doc.adventure['tiles'][-1]['id']);pump()
                gesture(j.canvas,(1,1),(281,281));assert j.jigsaw['rows'][7][7]==doc.adventure['tiles'][-1]['id'];j.apply();pump()
                world.tool.set('Jigsaw');gesture(world.canvas,(4,4),(68,4));pump()
                before=copy.deepcopy(doc.adventure);world.tool.set('Move city')
                # Drag the first city down, leaving its neighbour to the east.
                gesture(world.canvas,(270,270),(270,398));assert doc.adventure['maps'][0]['origin']==[64,96]
                ed.undo();pump();assert doc.adventure==before;ed.redo();pump()
                ImageGrab.grab(xdisplay=env['DISPLAY']).save(Path(work)/'world-art-editor.png')
                doc.save();reopened=ProjectDocument(path/'game',tool);assert reopened.art==doc.art and reopened.adventure==doc.adventure
                print('PASS: pixel strokes/undo/frames, shared tile preview, jigsaw editing, world painting, city dragging, undo/redo and atomic save/reopen.',flush=True)
            finally:window.destroy()
