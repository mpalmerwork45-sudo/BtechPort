"""Mission authoring through real editor gestures on an isolated display."""
def run(env,work):
    import copy
    import tempfile
    import time
    import tkinter as tk
    from pathlib import Path
    from PIL import ImageGrab
    from editor_model import create_project,ProjectDocument
    from editor_workspace import Workspace

    root=Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix='editor-mission-',dir=work) as temporary:
        folder=Path(temporary);tool=root/'build/btp-project'
        doc=create_project(root/'examples/argent-recovery',folder/'game','mission-editor-test','Mission editor test',tool)
        window=tk.Tk();workspace=Workspace(window,tool,folder/'settings');window.geometry('1440x960+0+0')
        errors=[];window.report_callback_exception=lambda kind,error,tb:errors.append(error)
        def pump(condition=lambda:True,timeout=15):
            until=time.monotonic()+timeout
            while True:
                window.update()
                if errors:raise errors.pop(0)
                if condition():return
                if time.monotonic()>until:raise AssertionError('Editor timed out: '+workspace.status.get())
                time.sleep(.01)
        def form():
            return next(d.view for d in reversed(app._editor_scope.live()) if isinstance(getattr(d.view,'values',None),dict))
        def apply(f):
            f.apply_button.invoke();pump()
            assert not f.window.winfo_exists(),f.error.get()
        try:
            app=workspace.app;app.set_document(doc)
            app.settings.update({'player':str(root/'build/btech-port'),'data':str(root/'Original DOS'),
                'dialogue-data':str(root/'work/talk-data.bin'),'combat-data':str(root/'work/combat-data.bin'),'world-data':str(root/'work/world-data.bin')})
            app.edit_adventure();maps=app.map_editor;pump()
            maps.zoom_control.set(24);maps.canvas.xview_moveto(0);maps.canvas.yview_moveto(0);pump()
            before=copy.deepcopy(doc.adventure)
            maps.drawing_tools.buttons['Region'].invoke();pump()
            def point(x,y):return dict(x=round((x+.5)*24-maps.canvas.canvasx(0)),y=round((y+.5)*24-maps.canvas.canvasy(0)))
            maps.canvas.event_generate('<Button-1>',**point(8,4));pump()
            maps.canvas.event_generate('<B1-Motion>',**point(11,6));pump()
            maps.canvas.event_generate('<ButtonRelease-1>',**point(11,6));pump()
            f=form()
            assert [f.values[k].get() for k in ('x','y','width','height')]==['8','4','4','3']
            f.values['id'].set('test:drawn-region');f.values['name'].set('Drawn survey region')
            f.values['width'].set('0');f.apply_button.invoke();pump()
            assert f.window.winfo_exists() and f.error.get() and doc.adventure==before
            assert window.grab_current() is f.window
            f.values['width'].set('4');apply(f)
            assert doc.adventure['regions'][-1]['rect']==[8,4,4,3]
            after=copy.deepcopy(doc.adventure)
            workspace.edit_history(False);pump();assert doc.adventure==before
            workspace.edit_history(True);pump();assert doc.adventure==after
            missions=maps.missions();missions.listings['regions'].selection_set('test:drawn-region')
            missions.show_map();pump()
            assert maps.selection_rect==(8,4,11,6)
            ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'editor-mission-regions.png')
            print('PASS: drag a rectangular region; invalid bounds retain the draft; correction, Undo/Redo and Show on map.',flush=True)

            missions=maps.missions();f=missions.edit('variables',new=True);pump()
            for key,value in dict(id='test:supplies',name='Supplies',type='counter',initial='2',maximum='7').items():f.values[key].set(value)
            apply(f)
            f=missions.edit('variables',new=True);pump()
            for key,value in dict(id='test:radio',name='Radio enabled',type='boolean',initial='1').items():f.values[key].set(value)
            apply(f)
            assert 'maximum' not in doc.adventure['variables'][-1]
            objectives=maps.event_graph().objectives();objectives.edit(True);pump();f=form()
            for key,value in dict(id='test:optional',title='Optional survey',text='Survey the northern grid.',initial='active').items():f.values[key].set(value)
            apply(f)
            assert doc.adventure['objectives'][-1]['initial']=='active'
            # The shared event inspector saves compound conditions and actions.
            maps.window.lift();maps.tabs.select(maps.event_tab);pump()
            def edit(identity):
                maps.event_listing.selection_clear(0,'end')
                maps.event_listing.selection_set(next(i for i,e in enumerate(doc.adventure['events']) if e['id']==identity))
                maps.populate_event();pump()
            identity=next(e['id'] for e in doc.adventure['events'] if e['op']=='check')
            edit(identity)
            maps.event_vars['condition_count'].set('2')
            for key,value in dict(match='any',condition_1_kind='variable',condition_1_id='test:supplies',condition_1_compare='ge',
                                  condition_1_value='2',condition_2_kind='objective',condition_2_id='test:optional',
                                  condition_2_compare='eq',condition_2_value='active').items():maps.event_vars[key].set(value)
            maps.apply_event();pump();doc.validate()
            saved=next(e for e in doc.adventure['events'] if e['id']==identity)
            assert saved['conditions'][0]['value']==2 and saved['conditions'][1]['value']=='active'
            # Keep the playable mission's route unchanged after proving the form.
            workspace.edit_history(False);pump();doc.validate()
            missions=maps.missions();missions.tabs.select(1);pump()
            ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'editor-mission-variables.png')
            f=missions.edit('variables',new=True);pump()
            f.values['name'].set('Retain this unfinished counter')
            workspace.recovery.write(app._editor_scope)
            record=workspace.recovery.read(workspace.recovery.path(app._editor_scope))
            f.window.destroy();pump()
            workspace.recovery.restore(app._editor_scope,record);pump()
            f=next(d.view for d in app._editor_scope.live() if isinstance(getattr(d.view,'values',None),dict) and 'name' in d.view.values
                   and d.view.values['name'].get()=='Retain this unfinished counter')
            assert f.window.winfo_viewable() and window.grab_current() is f.window
            f.window.destroy();pump()
            doc.save();reopened=ProjectDocument(doc.root,tool);assert reopened.adventure==doc.adventure
            print('PASS: typed counter/boolean, explicit objective, compound event form, unfinished form recovery and save/reopen.',flush=True)

            workspace.invoke('Play from start');pump(lambda:not workspace.play_session.preparing)
            process=workspace.play_session.process;assert process is not None,workspace.status.get()
            until=time.monotonic()+.5;pump(lambda:time.monotonic()>=until)
            assert process.poll() is None,(workspace.play_session.folder/'player.log').read_text()
            ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'editor-mission-play.png')
            workspace.play_session.stop();pump(lambda:workspace.play_session.process is None)
            print('PASS: edited extraction mission starts in the ordinary SDL player; Stop returns control to the editor.',flush=True)
        finally:
            workspace.play_session.shutdown();workspace.tasks.shutdown();workspace.closing=True
            window.destroy()
