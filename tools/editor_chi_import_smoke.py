"""Bounded real-GUI import, edit, Save/reopen and native Play journey."""
def run(env,work):
    import json,tempfile,time,tkinter as tk
    from pathlib import Path
    from PIL import ImageGrab
    from launcher import Launcher
    from chi_editor import open_campaign,open_import
    from editor_model import ProjectDocument,encoded
    root=Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix='chi-import-gui-',dir=work) as temporary:
        folder=Path(temporary);window=tk.Tk();launcher=Launcher(window,folder/'launcher');errors=[]
        window.report_callback_exception=lambda kind,error,tb:errors.append(error)
        def pump(condition=lambda:True,timeout=30):
            deadline=time.monotonic()+timeout
            while True:
                window.update()
                if errors:raise errors.pop(0)
                if condition():return
                if time.monotonic()>deadline:raise AssertionError('Timed out GUI import journey')
                time.sleep(.01)
        try:
            view=launcher.import_chi();app=view.owner;workspace=view.workspace
            app.window.winfo_toplevel().geometry('1024x740+0+0');pump()
            view.source.set(str(root/'Original DOS'));view.target.set(str(folder/'campaigns'))
            view.start_button.invoke();pump(lambda:view.cancel_event is None and not workspace.tasks.jobs)
            assert view.result,view.status.get();assert len(view.result['projects'])==2
            assert len(launcher.user_projects)==2
            from app_runtime import imported_projects
            assert len(imported_projects(launcher.state_dir))==2
            window.lower(app.window.winfo_toplevel());app.window.winfo_toplevel().lift();pump()
            ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'chi-import-wizard.png')
            original=view.result['projects'][0];view.edit(original);pump()
            assert app.document.manifest['requires']=='chi-local-dos-1.03'
            editor=open_campaign(app);editor.table.selection_set('87');editor.table.see('87');editor.select();pump()
            editor.text.delete('1.0','end');editor.text.insert('1.0','Computer control\nfor imported game?')
            editor.apply();pump();assert app.document.dirty
            actions=next(child for child in editor.text.master.winfo_children() if child.winfo_class()=='TFrame')
            assert all(child.winfo_rooty()+child.winfo_height()<=editor.window.winfo_rooty()+editor.window.winfo_height() for child in actions.winfo_children())
            workspace.invoke('Undo');pump();assert not app.document.dirty
            workspace.invoke('Redo');pump();assert app.document.dirty
            workspace.invoke('Save project');pump(lambda:not workspace.tasks.jobs)
            reopened=ProjectDocument(Path(original['path']),app.validator)
            assert json.loads(reopened.metadata['campaign.json'])['dialogue_overrides'][0]['index']==87
            assert json.loads(reopened.metadata['campaign.json'])['dialogue_overrides'][0]['text']=='Computer control\rfor imported game?'
            app.window.winfo_toplevel().lift();pump()
            ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'chi-import-dialogue.png')
            # No external original setup is needed for the self-contained import.
            app.settings.update(player=str(root/'build/btech-port'),data=str(folder/'missing-original'))
            workspace.play_session.start(app._editor_scope)
            pump(lambda:not workspace.play_session.preparing)
            assert workspace.play_session.process is not None,'No native player: '+workspace.status.get()
            assert workspace.play_session.process.poll() is None
            workspace.play_session.stop();pump(lambda:workspace.play_session.process is None)
            cancel=open_import(app);cancel.source.set(str(root/'Original DOS'));cancel.target.set(str(folder/'cancelled'))
            cancel.start_button.invoke();cancel.cancel();pump(lambda:cancel.cancel_event is None and not workspace.tasks.jobs)
            assert not (folder/'cancelled').exists();assert 'cancel' in cancel.status.get().lower(),cancel.status.get()
            (work/'chi-import-gui.json').write_bytes(encoded(dict(status='passed',checks=[
                'launcher import button','both-profile wizard','visible progress/completion',
                'open imported campaign','native text edit','Undo/Redo','Save/reopen',
                'native Play without external originals','Stop test','cancel leaves no published project'])))
            print('PASS: CHI import wizard, text editing, Save/reopen, native Play and cancellation.',flush=True)
        finally:
            for app in launcher.editors:
                workspace=app.window.workspace;workspace.play_session.shutdown();workspace.tasks.shutdown()
            window.destroy()
