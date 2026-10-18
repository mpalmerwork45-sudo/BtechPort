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
    from graphics_editor import PixelEditor,open_image_editor
    from sprite_editor import SpriteEditor
    from world_editor import JigsawEditor
    from world_editing import create_world,assign_city,all_worlds
    from unit_editing import import_catalogue
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
                ImageGrab.grab(xdisplay=env['DISPLAY']).save(Path(work)/'pixel-editor.png')
                pixel.undo();assert pixels(pixel.image)[15][15]=='00000000'
                pixel.redo();pixel.add_frame();assert len(pixel.image['frames'])==2
                before=copy.deepcopy(pixel.image);pixel.transform('Flip X');assert pixels(pixel.image,1)[15][0]=='aa4400ff'
                pixel.undo();assert pixel.image==before;pixel.redo();pixel.undo();pixel.apply();pump()
                library.use_tile();pump();assert doc.adventure['schema_version']==2
                assert ed.tile_image('package:art',im['id'],16).get(15,15)==(170,68,0)
                # Palette artwork opens directly, and cloning the tile also
                # detaches its pixels instead of sharing the source image.
                opened=[]
                def image_dialog(*args):
                    value=open_image_editor(*args);opened.append(value);return value
                with patch('graphics_editor.open_image_editor',side_effect=image_dialog):ed.tile_menu.invoke(0)
                pump();assert opened[-1].image['id']==im['id'];opened[-1].window.destroy()
                with patch.object(ed,'edit_tile'):ed.duplicate_tile()
                pump();clone_id=doc.adventure['tiles'][-1]['graphic'];assert clone_id!=im['id']
                with patch('graphics_editor.open_image_editor',side_effect=image_dialog):ed.edit_tile_pixels()
                pump();opened[-1].transform('Clear');opened[-1].apply();pump()
                assert doc.art['images'][0]['frames'][0][0].startswith('aa4400ff')
                assert next(i for i in doc.art['images'] if i['id']==clone_id)['frames'][0][0]=='00000000'*16
                ed.undo();ed.undo();pump()
                ed.brush.selection_set(len(doc.adventure['tiles'])-1);ed.select_brush()
                # Hover outlines do not alter the document; clicking paints
                # that exact tile. Blinking updates only the overlay item.
                ed.window.lift();library.window.withdraw();pump();z=int(ed.zoom.get())
                before=copy.deepcopy(doc.adventure);ed.canvas.event_generate('<Motion>',x=z*2+2,y=z*12+2);pump()
                assert ed.hover==(2,12) and ed.canvas.find_withtag('brush-hover') and doc.adventure==before
                outline=ed.canvas.itemcget(ed.canvas.find_withtag('brush-hover')[0],'outline');ed.blink_hover()
                assert ed.canvas.itemcget(ed.canvas.find_withtag('brush-hover')[0],'outline')!=outline
                gesture(ed.canvas,(z*2+2,z*12+2),(z*2+2,z*12+2));assert doc.adventure['maps'][0]['rows'][12][2]==doc.adventure['tiles'][-1]['id']
                ed.undo();pump()
                a=copy.deepcopy(doc.adventure);create_world(a,'test',32,32);assign_city(a,'beacon:town');assign_city(a,'beacon:wild');ed.commit(a)
                ed.edit_landscape();world=ed.world_editor;world.window.geometry('1000x730+0+0');pump()
                j=JigsawEditor(world,world.selected_jigsaw());j.tile.set(doc.adventure['tiles'][-1]['id']);pump()
                gesture(j.canvas,(1,1),(281,281));assert j.jigsaw['rows'][7][7]==doc.adventure['tiles'][-1]['id'];j.apply();pump()
                world.tool.set('Jigsaw');gesture(world.canvas,(4,4),(68,4));pump()
                before=copy.deepcopy(doc.adventure);world.tool.set('Move city')
                # Drag the first city down, leaving its neighbour to the east.
                gesture(world.canvas,(270,270),(270,398));assert doc.adventure['maps'][0]['origin']==[64,96]
                ed.undo();pump();assert doc.adventure==before;ed.redo();pump()
                ImageGrab.grab(xdisplay=env['DISPLAY']).save(Path(work)/'world-art-editor.png')
                a=copy.deepcopy(doc.adventure);planet=create_world(a,'test',32,32,'Second planet');ed.commit(a);pump()
                world.planet.current(1);world.planet.event_generate('<<ComboboxSelected>>');pump();assert world.world_id==planet
                assert len(all_worlds(doc.adventure))==2
                # Exercise the actual roster context menu and direction-aware
                # sprite editor, including isolated staging and live refresh.
                app.vehicle_catalogue();pump()
                dialog=next(w for w in window.winfo_children() if isinstance(w,tk.Toplevel) and w.title()=='Add vehicles')
                next(d.view.apply_button for d in app._editor_scope.live() if d.view.window==dialog).invoke();pump()
                assert app.kind.get()=='Vehicles' and app.current=='vehicles:patton'
                window.lift();pump()
                assert len(app.sprite_photos)==32
                index=app.sprite_index;window.after(180,window.quit);window.mainloop();pump();assert app.sprite_index!=index
                with patch('graphics_editor.open_image_editor',side_effect=image_dialog):app.sprite_menu.invoke(0)
                pump();editor=opened[-1];assert isinstance(editor,SpriteEditor)
                initial=copy.deepcopy(editor.image);owned=copy.deepcopy(doc.art)
                editor.directions[2].invoke();pump();assert editor.frame.current()==8
                assert editor.description.get().startswith('Right - movement frame 1 of 4')
                editor.color.set('ef3210ff');gesture(editor.canvas,(1,1),(1,1));editor.copy_frame()
                editor.next.invoke();pump();assert editor.frame.current()==9;editor.paste()
                assert editor.image['frames'][9]==editor.image['frames'][8]
                editor.undo();assert editor.image['frames'][9]==initial['frames'][9]
                editor.redo();editor.color.set('0011ffff');gesture(editor.canvas,(1,1),(1,1))
                assert pixels(editor.image,8)[0][0]=='ef3210ff' and pixels(editor.image,9)[0][0]=='0011ffff'
                editor.previous.invoke();pump();assert editor.frame.current()==8
                editor.strip.event_generate('<Button-1>',x=241,y=36);pump();assert editor.frame.current()==11
                before=copy.deepcopy(editor.image);editor.onion.set(True);editor.draw();pump();assert editor.image==before
                # Preview advances independently and stays in this direction.
                editor.fps.set('12');editor.play_button.invoke();pump();phase=editor.preview_phase
                window.after(110,window.quit);window.mainloop();pump()
                assert editor.preview_phase!=phase and editor.frame.current()==11 and editor.frames()==(8,9,10,11)
                editor.play_button.invoke();pump();assert editor.preview_timer is None
                editor.previous.invoke();editor.previous.invoke();pump()
                assert editor.frame.current()==9 and doc.art==owned
                editor.window.geometry('960x740+0+0');editor.window.lift();pump()
                ImageGrab.grab(xdisplay=env['DISPLAY']).save(Path(work)/'sprite-editor.png')
                # The smallest supported window retains the direction/pose
                # controls and enough canvas height for a complete 32px pose.
                editor.window.geometry('900x730+0+0');pump()
                for widget in (editor.next,editor.play_button,editor.paste_button):
                    assert widget.winfo_rootx()+widget.winfo_width()<=editor.window.winfo_rootx()+editor.window.winfo_width()
                assert editor.canvas.winfo_height()>=256
                editor.play();assert editor.preview_timer is not None
                editor.apply();pump();assert editor.preview_timer is None
                assert app.sprite_source['frames'][8][0].startswith('ef3210ff')
                assert app.sprite_source['frames'][9][0].startswith('0011ffff')
                assert app.sprite_source['frames'][0]==initial['frames'][0]
                # The library uses the same dedicated sprite editor. Its
                # discard path must not commit a second staged edit.
                library.selected=editor.image['id'];before=copy.deepcopy(doc.art)
                discarded=library.edit();pump();assert isinstance(discarded,SpriteEditor)
                discarded.transform('Clear')
                with patch.object(messagebox,'askyesnocancel',return_value=False):discarded.close()
                pump();assert doc.art==before
                # Original characters share diagonal/cardinal images; the
                # editor must expose that aliasing instead of inventing poses.
                person=new_image('test',[],'Original sprite 166 copy','sprite',16,16,16)
                character=SpriteEditor(library,person);pump()
                assert character.view.get()=='Character movement'
                character.directions[2].invoke();assert character.frame.current()==4
                assert 'Up right, Down right' in character.note.get()
                character.next.invoke();assert character.frame.current()==5
                character.directions[1].invoke();assert character.frame.current()==5
                character.view.set('All images');character.change_view();character.select_phase(15);pump()
                assert character.frame.current()==15 and character.strip.xview()[0]>0
                character.next.invoke();assert character.frame.current()==0
                character.close();pump()
                app.sprite_menu.invoke(1);pump()
                dialogs=[w for w in window.winfo_children() if isinstance(w,tk.Toplevel) and w.title()=='Choose unit sprite']
                assert len(dialogs)==1;dialogs[0].destroy()
                world.window.withdraw();library.window.withdraw();ed.window.withdraw();window.lift();pump()
                ImageGrab.grab(xdisplay=env['DISPLAY']).save(Path(work)/'roster-vehicle-editor.png')
                # Long toolbars must still expose the last action at each
                # supported minimum size with the selected system font.
                for subject,size in [(world.window,'840x600'),(library.window,'720x500')]:
                    subject.deiconify();subject.geometry(size);subject.lift();pump()
                    bar=subject.winfo_children()[0]
                    for widget in bar.winfo_children():
                        assert widget.winfo_rootx()+widget.winfo_width()<=subject.winfo_rootx()+subject.winfo_width()
                doc.save();reopened=ProjectDocument(path/'game',tool);assert reopened.art==doc.art and reopened.adventure==doc.adventure
                print('PASS: pixels/undo/frames, hover painting, jigsaws/city dragging, planets, sprite direction/frame navigation, copy/paste/undo, isolated playback/onion skin, apply/discard and atomic save/reopen.',flush=True)
            finally:window.destroy()
