"""Exercise native world painting in the real workspace on a private display."""
def run(env,work):
    import copy,json,tempfile,time,tkinter as tk
    from pathlib import Path
    from tkinter import messagebox
    from unittest.mock import patch
    from PIL import ImageGrab
    from chi_import import import_campaigns
    from chi_spatial import data,resolved_jigsaw,find
    from editor_model import ProjectDocument,encoded
    from editor_workspace import Workspace
    from tile_context import neighbours

    root=Path(__file__).resolve().parents[1];tool=root/'build/btp-project';work=Path(work)
    with tempfile.TemporaryDirectory(prefix='world-paint-gui-',dir=work) as temporary:
        folder=Path(temporary);result=import_campaigns(root/'Original DOS',folder/'campaigns',edition='original',validator=tool)
        document=ProjectDocument(Path(result['projects'][0]['path']),tool)
        window=tk.Tk();workspace=None;errors=[];checks=[]
        window.report_callback_exception=lambda kind,error,tb:errors.append(error)
        def pump(condition=lambda:True,timeout=30):
            deadline=time.monotonic()+timeout
            while True:
                window.update()
                if errors:raise errors.pop(0)
                if condition():return
                if time.monotonic()>deadline:raise AssertionError('World GUI timeout: '+workspace.status.get())
                time.sleep(.01)
        def settled():pump(lambda:not workspace.tasks.jobs)
        def fail(title,text,**kwargs):raise AssertionError(title+': '+text)
        def screenshot(name):pump();ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/name)
        def show(world,x=0,y=0,z=8,view='Detailed tiles'):
            world.window.lift();world.view.set(view);world.zoom_control.set(z);pump()
            world.canvas.xview_moveto(x/1024);world.canvas.yview_moveto(y/1024);world.draw();pump()
        def position(canvas,z,p):return [round((p[i]+.5)*z-(canvas.canvasx(0) if i==0 else canvas.canvasy(0))) for i in range(2)]
        input_clock=1000
        def gesture(world,start,end=None,release=True):
            nonlocal input_clock
            input_clock+=1000
            a=position(world.canvas,int(world.zoom.get()),start);b=position(world.canvas,int(world.zoom.get()),end or start)
            world.canvas.event_generate('<Button-1>',x=a[0],y=a[1],time=input_clock);pump()
            if end is not None:world.canvas.event_generate('<B1-Motion>',x=b[0],y=b[1],time=input_clock+100);pump()
            if release:world.canvas.event_generate('<ButtonRelease-1>',x=b[0],y=b[1],time=input_clock+200);settled()
        def brush(world,name):world.tools.buttons[name].invoke();pump();assert world.tool.get()==name
        try:
            with patch.object(messagebox,'showerror',fail):
                workspace=Workspace(window,tool,folder/'settings');window.geometry('1440x930+0+0')
                app=workspace.app;app.set_document(document);app.edit_adventure();maps=app.map_editor;settled()
                world=maps.edit_landscape();settled();assert world.image and world.mini.size==(1024,1024)
                assert [int(v.split(' ',1)[0]) for v in world.level_choice.cget('values')]==[0,16,32,48,64]
                world.level.set('80');assert world.level_choice.get()=='80 (advanced)';world.level.set('32')
                screenshot('world-paint-tinyland.png');checks.append('Actual native TINYLAND overview and indexed detailed tiles')
                show(world);world.level.set('48');world.shape.set('Line');brush(world,'Terrain')
                gesture(world,(1,1),(25,1));assert {tuple(v['at']) for v in data(document)['world']['terrain']}=={(0,0),(1,0),(2,0),(3,0)}
                assert all(v['level']==48 for v in data(document)['world']['terrain'])
                before=copy.deepcopy(document.adventure);world.shape.set('Rectangle');world.level.set('32')
                gesture(world,(1,9),(17,17));assert len(data(document)['world']['terrain'])==10
                workspace.invoke('Undo');settled();assert document.adventure==before
                workspace.invoke('Redo');settled();assert len(data(document)['world']['terrain'])==10
                checks.append('Brush/line/rectangle native terrain edits and shared Undo/Redo')

                before=document.files();world.shape.set('Brush');gesture(world,(40,40),release=False)
                draft=world.capture_draft();assert draft['stroke']['points']
                world.canvas.focus_force();world.canvas.event_generate('<Escape>');pump();assert document.files()==before and world.stroke is None
                world.restore_draft(draft);assert world.stroke;world.cancel();pump();assert document.files()==before
                checks.append('Unfinished stroke capture/restore and Escape cancellation')

                brush(world,'Tile');world.tile_id.set('chi:land-85');gesture(world,(2,2));assert data(document)['world']['patches'][0]['tile']=='chi:land-85'
                brush(world,'Jigsaw');world.listing.selection_set('chi:jigsaw-15');world.flip.set('3');gesture(world,(1,1))
                current=data(document)['world'];assert not current.get('patches');assert current['placements'][0]==dict(at=[0,0],jigsaw='chi:jigsaw-15',level=32,flip=3)
                expected=resolved_jigsaw(data(document),'chi:jigsaw-15',32,3)
                assert all(world.value['tiles'][world.image['grid'][y*1024+x]]['id']==expected[y][x] for y in range(8) for x in range(8))
                brush(world,'Erase');gesture(world,(1,1));assert not any(v['at']==[0,0] for key in ('terrain','placements','patches') for v in data(document)['world'].get(key,[]))
                checks.append('Fine tiles, oriented jigsaw stamps, patch replacement and restore generated terrain')

                original=data(document)['maps'][0]['origin'];show(world,max(0,original[0]-72),max(0,original[1]-8),z=4)
                brush(world,'Terrain');before=document.files();gesture(world,(original[0]+4,original[1]+4));assert document.files()==before
                brush(world,'Move town');gesture(world,(original[0]+4,original[1]+4),(original[0]-60,original[1]+4))
                assert data(document)['maps'][0]['origin']==[original[0]-64,original[1]]
                assert data(document)['maps'][10]['origin']==data(document)['maps'][0]['origin']
                workspace.invoke('Undo');settled();assert data(document)['maps'][0]['origin']==original
                checks.append('Town painting is skipped, aligned town drag and linked ruined Citadel move')

                world.listing.selection_set('chi:jigsaw-03');jigsaw=world.edit_jigsaw();pump()
                jigsaw.preview_level.set('48');jigsaw.preview_flip.set('3');jigsaw.draw();pump()
                expected=resolved_jigsaw(data(document),jigsaw.jigsaw['id'],48,3);assert jigsaw.displayed_rows()==expected
                jigsaw.tool.set('Line');jigsaw.tile.set('chi:land-85')
                jigsaw.canvas.event_generate('<Button-1>',x=20,y=20);jigsaw.canvas.event_generate('<B1-Motion>',x=60,y=20);pump()
                assert jigsaw.jigsaw['rows'][1:]==expected[1:],'Line conversion lost the selected orientation'
                assert jigsaw.jigsaw['rows'][0][:2]==['chi:land-85']*2
                jigsaw.cancel();pump();assert jigsaw.preview_flip.get()=='3' and jigsaw.displayed_rows()==expected
                screenshot('world-paint-relative-jigsaw.png');jigsaw.window.destroy();world.window.lift();pump()
                world.clone_jigsaw();settled();clone=world.selected_jigsaw();assert clone['id']!='chi:jigsaw-03'
                jigsaw=world.edit_jigsaw();pump();jigsaw.preview_level.set('48');jigsaw.preview_flip.set('2');jigsaw.draw();pump()
                old_rows=jigsaw.displayed_rows();jigsaw.tile.set('chi:land-85')
                jigsaw.canvas.event_generate('<Button-1>',x=20,y=20);jigsaw.canvas.event_generate('<ButtonRelease-1>',x=20,y=20);pump()
                assert jigsaw.jigsaw['mode']=='absolute' and jigsaw.jigsaw['rows'][0][0]=='chi:land-85'
                assert jigsaw.jigsaw['rows'][1:]==old_rows[1:];jigsaw.apply();settled()
                assert find(data(document)['world']['jigsaws'],clone['id'])['mode']=='absolute'
                new=world.new_jigsaw();pump();assert new.jigsaw['mode']=='absolute';new.tile.set('chi:land-67')
                new.canvas.event_generate('<Button-1>',x=60,y=60);new.canvas.event_generate('<ButtonRelease-1>',x=60,y=60);pump()
                new.apply();settled();checks.append('Relative preview levels/orientation, clone, automatic exact conversion and new exact pieces')

                show(world,0,0);brush(world,'Tile');world.tile_id.set('chi:land-67');gesture(world,(10,10))
                px,py=position(world.canvas,int(world.zoom.get()),(10,10))
                world.canvas.event_generate('<Button-3>',x=px,y=py);pump();menu=world.preview_tile_menu
                assert menu.winfo_ismapped();menu.activate(3);menu.focus_force();menu.event_generate('<Return>');pump();settled()
                assert not menu.winfo_ismapped(),'Selecting a tile command left its context menu posted'
                pixel=next(v.controller for v in workspace.views.values() if v.key[1]=='pixels' and v.controller.map_context)
                assert pixel.map_context['at']==[1,1] and len(pixel.map_context['world_neighbourhood'])==3
                adjacent=neighbours(document,maps.graphics,pixel.map_context);assert all(all(v is not None for v in row) for row in adjacent)
                screenshot('world-paint-tile-neighbours.png');pixel.window.destroy();world.window.lift();settled()
                checks.append('Right-click pixel editing uses all eight resolved neighbours')

                workspace.invoke('Save project');settled();assert not document.dirty,workspace.status.get()
                reopened=ProjectDocument(document.root,tool);assert reopened.files()==document.files()
                checks.append('Native edit validation and Save/reopen with assets retained privately')
                world.window.lift();show(world,0,0,z=8);screenshot('world-paint-detailed.png')
                window.geometry('1024x740+0+0');pump()
                side_canvas=next(w for w in world.side_shell.winfo_children() if isinstance(w,tk.Canvas))
                side_canvas.yview_moveto(1);pump()
                assert world.towns.winfo_rooty()>=side_canvas.winfo_rooty()
                assert world.towns.winfo_rooty()+world.towns.winfo_height()<=side_canvas.winfo_rooty()+side_canvas.winfo_height()
                for button in world.tools.buttons.values():
                    assert button.winfo_ismapped() and button.winfo_rootx()+button.winfo_width()<=world.window.winfo_rootx()+world.window.winfo_width()
                checks.append('All world tools and scrollable town/jigsaw controls remain reachable at 1024 by 740')
                screenshot('world-paint-small-window.png')
                (work/'world-paint-gui.json').write_bytes(encoded(dict(status='passed',checks=checks)))
                print('PASS: native world TINYLAND/detail painting, stamps, town placement, exact jigsaws, tile neighbours, Undo/Save/reopen.',flush=True)
        finally:
            if workspace:workspace.play_session.shutdown();workspace.tasks.shutdown()
            window.destroy()
