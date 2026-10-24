"""Bounded real-GUI import, edit, Save/reopen and native Play journey."""
def run(env,work):
    import json,tempfile,time,tkinter as tk,subprocess
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
            view.source.set(str(folder/'missing-install'));view.target.set(str(folder/'Campaigns é 漢字'))
            view.start_button.invoke();pump(lambda:view.cancel_event is None and not workspace.tasks.jobs)
            assert not view.result and 'Missing original file' in view.status.get(),view.status.get()
            assert view.start_button.cget('text')=='Retry import'
            view.source.set(str(root/'Original DOS'))
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
            # Export includes the current valid unsaved revision without
            # saving/resetting the working campaign. Reconstruction is exact.
            editor.text.delete('1.0','end');editor.text.insert('1.0','Reconstructed control?');editor.apply()
            from chi_recipe_editor import open_recipes
            from chi_recipe import fingerprint,runtime_files
            recipe=open_recipes(app);recipe.source.set(str(root/'Original DOS'));recipe.recipe.set(str(folder/'changes é 漢字.json'))
            recipe.output.set(str(folder/'Reconstructed é 漢字'));recipe.export();pump(lambda:not workspace.tasks.jobs)
            assert Path(recipe.recipe.get()).is_file(),recipe.status.get()
            assert app.document.dirty and json.loads(ProjectDocument(Path(original['path']),app.validator).metadata['campaign.json'])['dialogue_overrides'][0]['text']=='Computer control\rfor imported game?'
            recipe.export();pump(lambda:not workspace.tasks.jobs)
            assert 'preserved' in recipe.status.get(),recipe.status.get()
            recipe.build();pump(lambda:not workspace.tasks.jobs)
            assert recipe.result,recipe.status.get()
            assert fingerprint(runtime_files(app.document))==fingerprint(runtime_files(ProjectDocument(Path(recipe.result['project']),app.validator)))
            workspace.invoke('Save project');pump(lambda:not workspace.tasks.jobs)
            app.window.winfo_toplevel().lift();pump()
            ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'chi-import-dialogue.png')
            # No external original setup is needed for the self-contained import.
            app.settings.update(player=str(root/'build/btech-port'),data=str(folder/'missing-original'))
            workspace.play_session.start(app._editor_scope)
            pump(lambda:not workspace.play_session.preparing)
            assert workspace.play_session.process is not None,'No native player: '+workspace.status.get()
            assert workspace.play_session.process.poll() is None
            from reference_session import WindowKeys
            keys=WindowKeys()
            try:
                title=app.document.manifest['title']
                def player_window():return next((w for w,n in keys.windows() if n==title),None)
                pump(lambda:player_window() is not None)
                native=player_window();keys.key(native,'F5')
                run=workspace.play_session.folder
                pump(lambda:workspace.play_session.save_slot.exists())
                save=workspace.play_session.save_slot
                state=json.loads(subprocess.run([str(root/'build/btech-headless'),'--project',str(run/'game'),'--load',str(save)],
                    check=True,capture_output=True,text=True,timeout=20).stdout)
                assert state['mode']=='logos',state['mode']
                ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'chi-import-play-logo.png')
            finally:keys.x.XCloseDisplay(keys.display)
            workspace.play_session.stop();pump(lambda:workspace.play_session.process is None)
            assert (run/'bld.jsonl').is_file()
            original_slot=save;original_bytes=save.read_bytes()
            workspace.play_session.start(app._editor_scope);pump(lambda:not workspace.play_session.preparing)
            assert workspace.play_session.save_slot==original_slot and original_slot.read_bytes()==original_bytes
            workspace.play_session.stop();pump(lambda:workspace.play_session.process is None)
            view.edit(view.result['projects'][1]);pump()
            workspace.play_session.start(app._editor_scope);pump(lambda:not workspace.play_session.preparing)
            assert workspace.play_session.process is not None and workspace.play_session.process.poll() is None
            keys=WindowKeys()
            try:
                title=app.document.manifest['title'];pump(lambda:player_window() is not None)
                keys.key(player_window(),'F5');updated_run=workspace.play_session.folder
                pump(lambda:workspace.play_session.save_slot.exists())
                save=workspace.play_session.save_slot
                updated=json.loads(subprocess.check_output([str(root/'build/btech-headless'),'--project',str(updated_run/'game'),'--load',str(save)],text=True,timeout=20))
                assert updated['mode']=='logos' and updated['combat_rules']=='enhanced'
            finally:keys.x.XCloseDisplay(keys.display)
            workspace.play_session.stop();pump(lambda:workspace.play_session.process is None)
            # Load an actual, fingerprinted bank journey and navigate an
            # observed instruction back to its BLD editor, within one tab set.
            trace=folder/'bank.jsonl'
            subprocess.run([str(root/'build/btech-headless'),'--project',str(app.document.root),
                '--replay',str(root/'tests/fixtures/reference-bank.actions'),'--bld-trace',str(trace)],
                check=True,capture_output=True,text=True,timeout=20)
            from chi_coverage_editor import open_coverage
            coverage=open_coverage(app);coverage.load([trace]);pump(lambda:not workspace.tasks.jobs)
            assert coverage.report and len(coverage.table.get_children())==26
            chosen=next(item for item,(program,node) in coverage.targets.items() if node and program=='chi:bld-comstar')
            program,node=coverage.targets[chosen];coverage.table.selection_set(chosen);coverage.source();pump()
            from chi_bld_editor import open_scripts
            source=open_scripts(app);assert source.program.get()==program and source.selected==node
            coverage.window.lift();pump();ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'chi-script-coverage.png')
            cancel=open_import(app);cancel.source.set(str(root/'Original DOS'));cancel.target.set(str(folder/'cancelled'))
            cancel.start_button.invoke();cancel.cancel();pump(lambda:cancel.cancel_event is None and not workspace.tasks.jobs)
            assert not (folder/'cancelled').exists();assert 'cancel' in cancel.status.get().lower(),cancel.status.get()
            (work/'chi-import-gui.json').write_bytes(encoded(dict(status='passed',checks=[
                'launcher import button','missing-source error and Retry','Unicode/spaced import paths','both-profile wizard','visible progress/completion',
                'open imported campaign','native text edit','Undo/Redo','Save/reopen',
                'unsaved exact recipe export/reconstruct','occupied recipe retry preserves edits',
                'both native profiles Play without external originals','Updated Enhanced default','ordinary Play starts on Infocom/Westwood logo','native coverage/source navigation','Stop test','cancel leaves no published project'])))
            print('PASS: CHI import wizard, text editing, Save/reopen, native Play and cancellation.',flush=True)
        finally:
            for app in launcher.editors:
                workspace=app.window.workspace;workspace.play_session.shutdown();workspace.tasks.shutdown()
            window.destroy()
