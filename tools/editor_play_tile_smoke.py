"""Play retry and map tile editing journeys on a private display."""
def run(env,work):
    import copy
    import os
    import tempfile
    import time
    import threading
    from pathlib import Path
    import tkinter as tk
    from tkinter import messagebox
    from unittest.mock import patch
    from PIL import ImageGrab
    from editor_model import create_project,ProjectDocument
    from editor_workspace import Workspace
    from adventure_editing import move_marker,paint
    from world_editing import token

    root=Path(__file__).resolve().parents[1];work=Path(work);os.environ['DISPLAY']=env['DISPLAY']
    with tempfile.TemporaryDirectory(prefix='editor-play-tile-',dir=work) as directory:
        tmp=Path(directory);tool=root/'build/btp-project'
        doc=create_project(root/'examples/beacon-demo',tmp/'game','play-tile-smoke','Play and tiles',tool)
        window=tk.Tk();workspace=None;errors=[];event_time=10000
        def pump_until(condition,timeout=12):
            end=time.monotonic()+timeout
            while not condition():
                window.update()
                if errors:raise errors.pop(0)
                if time.monotonic()>end:raise AssertionError('Editor timed out: '+workspace.status.get())
                time.sleep(.01)
            window.update()
            if errors:raise errors.pop(0)
        def event(canvas,sequence,x,y):
            nonlocal event_time
            event_time+=1000;canvas.event_generate(sequence,x=round(x),y=round(y),time=event_time);window.update()
            if errors:raise errors.pop(0)
        def wait_player():
            pump_until(lambda:not workspace.play_session.preparing)
            process=workspace.play_session.process
            assert process is not None,workspace.status.get()
            until=time.monotonic()+.4;pump_until(lambda:time.monotonic()>=until)
            assert process.poll() is None,(workspace.play_session.folder/'player.log').read_text()[-2000:]
            return process
        def stop():
            workspace.play_session.stop();pump_until(lambda:workspace.play_session.process is None)
        message_patch=patch.object(messagebox,'showerror',lambda title,message,**_:errors.append(AssertionError(str(message))))
        message_patch.start()
        try:
            workspace=Workspace(window,tool,tmp/'settings');window.geometry('1440x930+0+0')
            window.report_callback_exception=lambda kind,error,tb:errors.append(error)
            app=workspace.app;app.set_document(doc);app.edit_adventure();maps=app.map_editor;window.update()
            app.settings['player']=str(root/'build/btech-port')
            a=copy.deepcopy(doc.adventure);scene=a['maps'][0];door=scene['entrances'][0]
            at=list(door['at']);wall=next(token(t) for t in a['tiles'] if t['terrain']=='wall')
            paint(scene,-1,(at[0]+1)//2,at[1]//2,wall);maps.commit(a)
            workspace.invoke('Play from start');pump_until(lambda:not workspace.tasks.jobs)
            assert not workspace.play_session.preparing and workspace.play_session.process is None
            assert any('entrance must be' in p['message'] for p in workspace.problems),workspace.status.get()
            a=copy.deepcopy(doc.adventure)
            move_marker(a,0,('entrance',scene['id'],door['id'],None),[24,32]);maps.commit(a)
            doc.validate()
            workspace.action_buttons['Play from start'].invoke();wait_player()
            assert not workspace.problem_list.get_children() and not app.error_label.winfo_ismapped()
            assert ProjectDocument(workspace.play_session.folder/'game',tool).adventure==doc.adventure
            assert ProjectDocument(doc.root,tool).adventure!=doc.adventure
            stop()
            print('PASS: blocked entrance fails Play; correction launches the unsaved draft from the toolbar and clears obsolete errors.',flush=True)

            # Reproduce fixing the entrance while the previous validation is
            # still in flight. A stale failure must not replace that correction.
            good=copy.deepcopy(doc.adventure);bad=copy.deepcopy(good);bad['maps'][0]['entrances'][0]['at']=at
            maps.commit(bad);gate=threading.Event();entered=threading.Event();original=ProjectDocument.export
            def slow_export(document,target):entered.set();gate.wait(8);return original(document,target)
            with patch.object(ProjectDocument,'export',slow_export):
                workspace.invoke('Play from start');pump_until(entered.is_set);maps.commit(good);gate.set();wait_player()
            assert ProjectDocument(workspace.play_session.folder/'game',tool).adventure==good
            assert not workspace.problem_list.get_children();stop()

            # Also reject a stale success: moving a marker onto a roof while
            # preparing must not run the earlier valid map.
            gate.clear();entered.clear()
            with patch.object(ProjectDocument,'export',slow_export):
                workspace.invoke('Play from start');pump_until(entered.is_set);maps.commit(bad);gate.set()
                pump_until(lambda:not workspace.tasks.jobs)
            assert workspace.play_session.process is None and not workspace.play_session.preparing
            assert workspace.problem_list.get_children();maps.commit(good)
            from editor_tasks import validate
            validate(workspace,app._editor_scope);pump_until(lambda:not workspace.tasks.jobs)
            assert not workspace.problem_list.get_children()
            print('PASS: Play rechecks edits made during both failing and successful validation; a normal Validate clears corrected issues.',flush=True)

            # Force the real player to reject its command, exercising surfaced
            # stderr rather than a synthetic Popen failure.
            original_command=ProjectDocument.play_command
            def bad_command(document,*args,**kwargs):return original_command(document,*args,**kwargs)+['--invalid-play-smoke-option']
            with patch.object(ProjectDocument,'play_command',bad_command):
                workspace.invoke('Play from start');pump_until(lambda:not workspace.tasks.jobs)
                pump_until(lambda:workspace.play_session.process is None)
            assert any('Playtest failed' in p['message'] for p in app._editor_scope.problems)
            workspace.invoke('Play from start');wait_player();assert not workspace.problem_list.get_children();stop()
            print('PASS: failed player startup surfaces its log; retry and Stop leave Play ready.',flush=True)

            # Use the actual right-click menu on a visible overlay tile.
            app.edit_adventure();maps.zoom_control.set(24);maps.canvas.xview_moveto(0);maps.canvas.yview_moveto(0)
            a=copy.deepcopy(doc.adventure);tile=token(a['tiles'][0])
            a['maps'][0]['overlays'].append(dict(at=[3,3],rows=[tile*3]*3 if a['schema_version']==1 else [[tile]*3 for _ in range(3)]))
            maps.commit(a);window.update();before=doc.files()
            event(maps.canvas,'<Button-3>',4.5*24-maps.canvas.canvasx(0),4.5*24-maps.canvas.canvasy(0))
            assert doc.files()==before;menu=maps.map_context_menu
            assert menu.entrycget(0,'label')=='Edit tile pixels...'
            menu.unpost();menu.invoke(0);window.update();editor=workspace.current_view().controller
            assert editor.map_context==dict(map=maps.scene()['id'],at=[4,4])
            assert editor.pixel_origin==(16,16) and len(editor.canvas.find_withtag('tile-neighbour'))==8
            assert editor.image['kind']=='tile';before=doc.files()
            def pixel(px,py):
                z=int(editor.zoom.get());return ((px+.5)*z-editor.canvas.canvasx(0),(py+.5)*z-editor.canvas.canvasy(0))
            event(editor.canvas,'<Button-1>',*pixel(3,3));event(editor.canvas,'<ButtonRelease-1>',*pixel(3,3))
            assert doc.files()==before,'A read-only neighbour changed the tile'
            editor.color.set('ff00ffff');event(editor.canvas,'<Button-1>',*pixel(16,16));event(editor.canvas,'<ButtonRelease-1>',*pixel(16,16))
            after=doc.files();assert after!=before
            assert editor.image['frames'][0][0][:8]=='ff00ffff'
            assert all(im.get(0,0)==(255,0,255) for im in editor.context_images)
            workspace.edit_history(False);window.update();assert doc.files()==before
            workspace.edit_history(True);window.update();assert doc.files()==after
            editor.zoom_control.set(12);editor.canvas.xview_moveto(.1);editor.canvas.yview_moveto(.1);editor.color.set('00ffffff')
            event(editor.canvas,'<Button-1>',*pixel(17,17));event(editor.canvas,'<ButtonRelease-1>',*pixel(17,17))
            assert editor.image['frames'][0][1][8:16]=='00ffffff'
            editor.zoom_control.set(8);editor.canvas.xview_moveto(0);editor.canvas.yview_moveto(0);window.update()
            ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'editor-tile-neighbours.png')
            state=workspace.view_state(editor.window);assert state['map_context']==editor.map_context
            editor.show_neighbours.set(False);editor.draw();assert editor.pixel_origin==(0,0)
            workspace.restore_view(editor.window,state);assert editor.pixel_origin==(16,16)
            doc.save();reopened=ProjectDocument(doc.root,tool)
            assert reopened.art==doc.art and reopened.adventure==doc.adventure
            print('PASS: right-click edits the visible tile with eight live read-only neighbours; scrolled/zoomed pixels, Undo/Redo and save/reopen preserve the edits.',flush=True)

            from tile_context import neighbours
            from tile_editing import tile
            for kind in ('Building','Wall','Road'):
                designer=maps.construction(kind);window.update()
                cells=[(x,y) for y,row in enumerate(designer.roles) for x,role in enumerate(row) if role!=' ']
                def nearby(point):
                    x,y=point
                    return sum(0<=yy<len(designer.roles) and 0<=xx<len(designer.roles[yy]) and designer.roles[yy][xx]!=' '
                        for yy in range(y-1,y+2) for xx in range(x-1,x+2))
                x,y=max(cells,key=nearby);size=designer.preview_size
                event(designer.preview,'<Button-3>',(x+.5)*size-designer.preview.canvasx(0),(y+.5)*size-designer.preview.canvasy(0))
                role=designer.selected_role;identity=designer.profile['parts'][role]
                expected=neighbours(doc,maps.graphics,dict(construction=designer.current,role=role,at=[x,y]))
                menu=designer.preview_tile_menu;menu.unpost();menu.invoke(3);window.update()
                editor=workspace.current_view().controller
                assert editor.map_context==dict(construction=designer.current,role=role,at=[x,y])
                assert editor.pixel_origin==(16,16)
                assert len(editor.context_images)==sum(c is not None for row in expected for c in row)-1
                before=doc.files();editor.color.set('fedcbaff')
                event(editor.canvas,'<Button-1>',*pixel(16,16));event(editor.canvas,'<ButtonRelease-1>',*pixel(16,16))
                after=doc.files();assert after!=before
                workspace.edit_history(False);window.update();assert doc.files()==before
                workspace.edit_history(True);window.update();assert doc.files()==after
                ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/f'editor-{kind.lower()}-tile-neighbours.png')
                source=copy.deepcopy(next(im for im in doc.art['images'] if im['id']==tile(doc,identity)['graphic']))
                designer.window.lift();designer.clone_part();window.update();editor=workspace.current_view().controller
                assert designer.profile['parts'][role]!=identity and editor.map_context['construction']==designer.current
                editor.color.set('123456ff');event(editor.canvas,'<Button-1>',*pixel(16,16));event(editor.canvas,'<ButtonRelease-1>',*pixel(16,16))
                assert next(im for im in doc.art['images'] if im['id']==source['id'])==source
                doc.validate()
            doc.save();assert ProjectDocument(doc.root,tool).metadata==doc.metadata
            print('PASS: Building/Wall/Road preview menus and Clone tile keep the clicked neighbourhood; pixel edits share Undo and persist without altering the source clone.',flush=True)
        finally:
            if workspace:
                workspace.play_session.shutdown();workspace.tasks.shutdown();workspace.closing=True
            window.destroy()
            message_patch.stop()
