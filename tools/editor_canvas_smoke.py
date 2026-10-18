"""Exercise zoom input, canvas coordinates and visible tools on a private display."""
def run(env,work):
    import copy
    import os
    from pathlib import Path
    import tempfile
    import tkinter as tk
    from tkinter import messagebox
    from unittest.mock import patch
    from PIL import ImageGrab
    from editor_model import create_project
    from editor_workspace import Workspace
    from art_editing import new_image,pixels
    from graphics_editor import open_image_editor
    from construction_editing import new_profile
    from world_editing import create_world,assign_city
    from world_editor import JigsawEditor
    from event_workbench import editor_data

    root=Path(__file__).resolve().parents[1];work=Path(work);os.environ['DISPLAY']=env['DISPLAY']
    with tempfile.TemporaryDirectory(prefix='editor-canvas-',dir=work) as directory:
        tmp=Path(directory);tool=root/'build/btp-project'
        doc=create_project(root/'examples/beacon-demo',tmp/'game','canvas-smoke','Canvas smoke',tool)
        window=tk.Tk();errors=[];workspace=None
        def pump():
            window.update()
            if errors:raise errors.pop(0)
        def fail(title,message,**_):raise AssertionError(f'{title}: {message}')
        def visible(widget):
            assert widget.winfo_ismapped(),str(widget)
            x,y=widget.winfo_rootx(),widget.winfo_rooty()
            assert x>=window.winfo_rootx() and y>=window.winfo_rooty()
            assert x+widget.winfo_width()<=window.winfo_rootx()+window.winfo_width(),str(widget)
            assert y+widget.winfo_height()<=window.winfo_rooty()+window.winfo_height(),str(widget)
        def entry(control,text):
            pump();control.combo.focus_force();pump();control.combo.delete(0,'end');control.combo.insert(0,text)
            control.combo.event_generate('<Return>');pump()
        def zoom_check(view,control=None,canvas=None,anchor=True):
            view.window.lift();pump();control=control or view.zoom_control;canvas=canvas or view.canvas
            before=doc.files();revision=doc.revision
            original=control.variable.get();x,y=80,60
            canvas.xview_moveto(.15);canvas.yview_moveto(.15);view.draw();pump()
            old=control.scale();point=canvas.canvasx(x)/old,canvas.canvasy(y)/old
            canvas.event_generate('<Control-Button-4>',x=x,y=y);pump()
            new=control.scale();assert new>old,(type(view).__name__,old,new)
            if anchor:
                after=canvas.canvasx(x)/new,canvas.canvasy(y)/new
                assert max(abs(a-b) for a,b in zip(point,after))<=1/new+.01,(type(view).__name__,point,after,new)
            canvas.event_generate('<Control-MouseWheel>',x=x,y=y,delta=-120);pump()
            assert control.scale()==old,(type(view).__name__,control.scale(),old)
            assert control.combo.get()==control.format(old)
            # High-resolution deltas accumulate; unmodified wheel input does
            # not change zoom. No wheel binding may dispatch a paint stroke.
            canvas.event_generate('<Control-MouseWheel>',x=x,y=y,delta=60);pump();assert control.scale()==old
            canvas.event_generate('<Control-MouseWheel>',x=x,y=y,delta=60);pump();assert control.scale()>old
            canvas.event_generate('<Control-Button-5>',x=x,y=y);pump();assert control.scale()==old
            control.set(old);pump()
            canvas.event_generate('<Button-4>',x=x,y=y);pump();assert control.scale()==old
            for invalid in ('','nonsense','0','-1','nan','inf'):
                entry(control,invalid);assert control.scale()==old and control.combo.get()==control.format(old)
            entry(control,'175%');expected=int(1.75*control.base+.5) if control.integer else 1.75*control.base
            expected=max(control.steps[0],min(control.steps[-1],expected));assert control.scale()==expected
            control.variable.set(original);view.draw();pump();assert control.combo.get()==control.format(old)
            assert doc.files()==before and doc.revision==revision,'Zoom changed game data or editing metadata'
            return control
        def click_cell(canvas,scale,x,y):
            px=round((x+.5)*scale-canvas.canvasx(0));py=round((y+.5)*scale-canvas.canvasy(0))
            canvas.event_generate('<Button-1>',x=px,y=py);canvas.event_generate('<ButtonRelease-1>',x=px,y=py);pump()

        with patch.object(messagebox,'showerror',fail):
            try:
                workspace=Workspace(window,tool,tmp/'settings');window.geometry('1440x930+0+0')
                window.report_callback_exception=lambda kind,error,tb:errors.append(error)
                app=workspace.app;app.set_document(doc);app.edit_adventure();maps=app.map_editor;pump()
                # Real buttons, including construction, activate the same tools
                # as keyboard/pattern actions and expose a single selected state.
                for kind in ('Building','Wall','Road'):new_profile(doc,kind)
                maps.refresh();pump()
                for name,button in maps.drawing_tools.buttons.items():
                    visible(button);button.invoke();pump();assert maps.tool.get()==name
                    assert [key for key,b in maps.drawing_tools.buttons.items() if b.instate(['selected'])]==[name]
                    assert bool(maps.tool_options.winfo_ismapped())==(name in ('Building','Wall','Road'))
                maps.tool.set('Paste');pump();assert maps.drawing_tools.buttons['Paste'].instate(['selected'])
                maps.drawing_tools.buttons['Paint'].invoke();pump()
                zoom_check(maps)
                entry(maps.zoom_control,'200%');maps.canvas.xview_moveto(.1);maps.canvas.yview_moveto(.1);pump()
                maps.drawing_tools.buttons['Select'].invoke();pump()
                x=int(maps.canvas.canvasx(25)//32);y=int(maps.canvas.canvasy(25)//32)
                click_cell(maps.canvas,32,x,y);assert maps.selection_rect==(x,y,x,y)
                entry(maps.zoom_control,'999999%');assert maps.zoom.get()=='96'
                entry(maps.zoom_control,'0.001%');assert maps.zoom.get()=='4'
                entry(maps.zoom_control,'150%')
                maps.zoom_control.combo.set('125%');maps.zoom_control.combo.event_generate('<FocusOut>');pump();assert maps.zoom.get()=='20'
                maps.zoom_control.combo.focus_force();pump();maps.zoom_control.combo.set('150%');maps.zoom_control.combo.event_generate('<KP_Enter>');pump();assert maps.zoom.get()=='24'
                # Unfinished entry text cannot reach the map's blinking timer.
                maps.zoom_control.combo.delete(0,'end');maps.blink_hover();pump();assert maps.zoom.get()=='24'
                maps.zoom_control.combo.event_generate('<Escape>');pump();assert maps.zoom_control.combo.get()=='150%'
                for size in ('1024x768+0+0','1440x930+0+0'):
                    window.geometry(size);pump()
                    for button in maps.drawing_tools.buttons.values():visible(button)
                    visible(maps.zoom_control.combo);assert maps.canvas.winfo_height()>100
                for percent in (150,200,100):
                    workspace.scale(percent);pump()
                    for button in maps.drawing_tools.buttons.values():visible(button)
                    visible(maps.zoom_control.combo);assert maps.canvas.winfo_height()>100
                ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'editor-canvas-map.png')
                print('PASS: visible map tools, selected states, contextual options, editable zoom, bounds and pointer anchoring.',flush=True)

                graph=maps.event_graph();graph.view_mode.set('All events');graph.draw();pump();zoom_check(graph)
                entry(graph.zoom_control,'75%');graph.canvas.xview_moveto(0);graph.canvas.yview_moveto(0);pump()
                key=min(graph.positions,key=lambda k:sum(graph.positions[k]));x,y=graph.positions[key];z=.75
                px=round((x+30)*z-graph.canvas.canvasx(0));py=round((y+20)*z-graph.canvas.canvasy(0))
                graph.canvas.event_generate('<Button-1>',x=px,y=py);pump()
                graph.canvas.event_generate('<B1-Motion>',x=px+30,y=py+15);pump()
                graph.canvas.event_generate('<ButtonRelease-1>',x=px+30,y=py+15);pump()
                assert max(abs(a-b) for a,b in zip(editor_data(doc)['event_layout'][key],[x+40,y+20]))<.01
                graph.fit();pump();assert graph.zoom_control.combo.get()==graph.zoom_control.format(float(graph.zoom.get()))
                print('PASS: graph wheel/manual/Fit synchronization and node dragging at 75%.',flush=True)

                maps.window.lift();a=copy.deepcopy(doc.adventure);create_world(a,'canvas',32,32);assign_city(a,a['maps'][0]['id']);maps.commit(a)
                maps.edit_landscape();world=maps.world_editor;pump();zoom_check(world)
                assert world.canvas.find_all(),'World redraw after anchored scrolling is empty'
                for button in world.drawing_tools.buttons.values():visible(button)
                jigsaw=JigsawEditor(world,world.selected_jigsaw());pump();zoom_check(jigsaw,anchor=False)
                entry(jigsaw.zoom_control,'300%');jigsaw.canvas.xview_moveto(0);jigsaw.canvas.yview_moveto(0);pump()
                jigsaw.tile.current(len(doc.adventure['tiles'])-1);click_cell(jigsaw.canvas,48,2,3)
                assert jigsaw.jigsaw['rows'][3][2]==jigsaw.tile.get();jigsaw.undo();pump()
                builder=maps.construction('Building');pump();builder.zoom.set('24');builder.draw();pump()
                zoom_check(builder,canvas=builder.preview,anchor=False)
                zoom_check(builder,control=builder.footprint_zoom_control,canvas=builder.footprint,anchor=False)
                entry(builder.zoom_control,'Fit');assert builder.zoom.get()=='Fit'
                old=builder.preview_size;builder.preview.event_generate('<Control-Button-4>',x=20,y=20);pump();assert int(builder.zoom.get())>old
                entry(builder.footprint_zoom_control,'200%');builder.footprint.xview_moveto(0);builder.footprint.yview_moveto(0)
                builder.height.set('3');click_cell(builder.footprint,32,2,2);assert builder.profile['footprint'][2][2]==3
                state=workspace.view_state(builder.window);entry(builder.footprint_zoom_control,'300%');workspace.restore_view(builder.window,state);pump()
                assert builder.footprint_zoom_control.combo.get()=='200%'
                print('PASS: world viewport redraw, jigsaw painting, construction preview/Fit and footprint painting after zoom.',flush=True)

                maps.edit_graphics();art=maps.art_editor;pump()
                for kind in ('tile','sprite'):
                    image=new_image('canvas',doc.art['images'],kind=kind,frames=32 if kind=='sprite' else 1)
                    art.put(image);pixel=open_image_editor(art,image);pump();zoom_check(pixel,anchor=False)
                    entry(pixel.zoom_control,'1200%');pixel.canvas.xview_moveto(0);pixel.canvas.yview_moveto(0);pump()
                    pixel.color.set('123456ff');click_cell(pixel.canvas,12,2,3)
                    assert pixels(pixel.image,max(0,pixel.frame.current()))[3][2]=='123456ff'
                    pixel.undo();pump();assert pixels(pixel.image,max(0,pixel.frame.current()))[3][2]=='00000000'
                print('PASS: tile/sprite zoom leaves art unchanged and pixel coordinates/Undo stay correct.',flush=True)
                maps.window.lift();entry(maps.zoom_control,'125%');state=workspace.view_state(maps.window)
                entry(maps.zoom_control,'300%');workspace.restore_view(maps.window,state);pump()
                assert maps.zoom.get()=='20' and maps.zoom_control.combo.get()=='125%',(state,maps.zoom.get(),maps.zoom_control.combo.get())
                app.save();pump();doc.validate()
                print('PASS: workspace zoom restoration, saved project validation and clean callback teardown.',flush=True)
            finally:
                if workspace:workspace.closing=True
                window.destroy()
            if errors:raise errors.pop(0)
