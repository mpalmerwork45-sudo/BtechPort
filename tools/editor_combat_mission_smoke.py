"""Real editor groups, waypoints, timers, recovery and playable launch."""
def run(env,work):
    import copy
    import tempfile
    import time
    import tkinter as tk
    from pathlib import Path
    from PIL import ImageGrab
    from editor_model import create_project,ProjectDocument
    from editor_workspace import Workspace

    root=Path(__file__).resolve().parents[1];tool=root/'build/btp-project'
    with tempfile.TemporaryDirectory(prefix='editor-combat-mission-',dir=work) as temporary:
        folder=Path(temporary);doc=create_project(root/'examples/cairn-passage',folder/'game','combat-editor','Combat editor',tool)
        window=tk.Tk();workspace=Workspace(window,tool,folder/'settings');window.geometry('1440x960+0+0');errors=[]
        window.report_callback_exception=lambda kind,error,tb:errors.append(error)
        def pump(condition=lambda:True,timeout=20):
            deadline=time.monotonic()+timeout
            while True:
                window.update()
                if errors:raise errors.pop(0)
                if condition():return
                if time.monotonic()>deadline:raise AssertionError(workspace.status.get())
                time.sleep(.01)
        def apply(form):
            form.apply_button.invoke();pump();assert not form.window.winfo_exists(),form.error.get()
        try:
            app=workspace.app;app.set_document(doc)
            app.settings.update({'player':str(root/'build/btech-port'),'data':str(root/'Original DOS'),
                'dialogue-data':str(root/'work/talk-data.bin'),'combat-data':str(root/'work/combat-data.bin'),'world-data':str(root/'work/world-data.bin')})
            app.edit_adventure();maps=app.map_editor;mission=maps.missions();mission.tabs.select(2);pump()
            before=copy.deepcopy(doc.adventure);f=mission.edit('combat_groups',new=True);pump()
            for key,value in dict(id='test:escort',name='Additional convoy',encounter='cairn:escort',affiliation='friendly',reserve='1').items():f.values[key].set(value)
            child=f.recovery_children['actor']();pump()
            for key,value in dict(definition='vehicles:galleon',x='16',y='42',movement='walk',waypoints='16,48; 26,48').items():child.values[key].set(value)
            apply(child);apply(f);assert doc.adventure['combat_groups'][-1]['units'][0]['waypoints']==[[16,48],[26,48]]
            after=copy.deepcopy(doc.adventure);workspace.edit_history(False);pump();assert doc.adventure==before
            workspace.edit_history(True);pump();assert doc.adventure==after
            f=mission.edit('combat_hooks',new=True);pump()
            for key,value in dict(id='test:round-timer',encounter='cairn:escort',when='round_end',repeat='always',round='2',every='-1',event='cairn:end').items():f.values[key].set(value)
            f.apply_button.invoke();pump();assert f.window.winfo_exists() and f.error.get()
            assert window.grab_current() is f.window and doc.adventure==after
            f.values['every'].set('2');apply(f);doc.validate()
            mission.tabs.select(3);pump();ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'editor-combat-hooks.png')
            print('PASS: actor, route and round-hook forms; invalid bounds stay visible; correction and atomic Undo/Redo.',flush=True)
            maps.tabs.select(maps.event_tab);maps.window.lift();pump()
            identity='cairn:retry-wave';maps.event_listing.selection_clear(0,'end')
            maps.event_listing.selection_set(next(i for i,e in enumerate(doc.adventure['events']) if e['id']==identity));maps.populate_event();pump()
            maps.event_vars['condition_1_kind'].set('combat_round');maps.event_vars['condition_1_value'].set('3');maps.apply_event();doc.validate()
            assert 'id' not in next(e for e in doc.adventure['events'] if e['id']==identity)['conditions'][0]
            workspace.edit_history(False);pump()
            # Recovery restores both the group form and its staged nested units.
            mission=maps.missions();mission.tabs.select(2);f=mission.edit('combat_groups',new=True);pump()
            f.values['name'].set('Recover this convoy')
            child=f.recovery_children['actor']();pump();child.values['definition'].set('vehicles:pegasus');child.values['waypoints'].set('30,34; 34,34');apply(child)
            workspace.recovery.write(app._editor_scope);saved=workspace.recovery.read(workspace.recovery.path(app._editor_scope));f.window.destroy();pump()
            workspace.recovery.restore(app._editor_scope,saved);pump()
            f=next(d.view for d in app._editor_scope.live() if isinstance(getattr(d.view,'values',None),dict) and d.view.values.get('name') and d.view.values['name'].get()=='Recover this convoy')
            child=f.recovery_children['actor'](True,0);pump();assert child.values['waypoints'].get()=='30,34; 34,34'
            child.window.destroy();f.window.destroy();pump()
            window.geometry('960x620+0+0');pump()
            f=mission.edit('combat_hooks',identity='test:round-timer');pump()
            assert f.apply_button.winfo_viewable() and f.apply_button.winfo_rooty()+f.apply_button.winfo_height()<=window.winfo_screenheight()
            ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'editor-combat-small.png');f.window.destroy();pump()
            doc.save();assert ProjectDocument(doc.root,tool).adventure==doc.adventure
            print('PASS: combat conditions, nested actor draft recovery, small-window actions and Save/reopen.',flush=True)
            workspace.invoke('Play from start');pump(lambda:not workspace.play_session.preparing)
            process=workspace.play_session.process;assert process is not None,workspace.status.get()
            deadline=time.monotonic()+.4;pump(lambda:time.monotonic()>deadline);assert process.poll() is None
            workspace.play_session.stop();pump(lambda:workspace.play_session.process is None)
            print('PASS: edited defence-and-escort project launches in the ordinary SDL player.',flush=True)
        finally:
            workspace.play_session.shutdown();workspace.tasks.shutdown();workspace.closing=True;window.destroy()
