"""Real workspace mission editing, recovery, navigation, Save and Play journey."""
def run(env,work):
    import subprocess,tempfile,time,tkinter as tk
    from pathlib import Path
    from PIL import ImageGrab
    from chi_import import import_campaigns
    from chi_missions import data
    from chi_mission_evidence import configure,training
    from chi_missions_editor import open_missions
    from editor_model import ProjectDocument,EditorError,encoded
    from editor_workspace import Workspace
    from editor_recovery import capture
    from editor_problems import navigate
    from authoring_contract import diagnostic
    root=Path(__file__).resolve().parents[1];tool=root/'build/btp-project'
    with tempfile.TemporaryDirectory(prefix='chi-missions-gui-',dir=work) as temporary:
        folder=Path(temporary);import_campaigns(root/'Original DOS',folder/'pair',validator=tool)
        doc=ProjectDocument(folder/'pair/updated',tool)
        configure(doc,{'training.4.start_x':68,'training.4.return_x':70,'training.4.control_prompt':1,'training.4.pass_on_retreat':1})
        training(doc);doc.save()
        window=tk.Tk();workspace=Workspace(window,tool,folder/'state');app=workspace.app;app.set_document(doc);app.settings['player']=str(root/'build/btech-port');window.geometry('1000x730+0+0')
        errors=[];window.report_callback_exception=lambda kind,error,tb:errors.append(error)
        def pump(condition=lambda:True,timeout=30):
            deadline=time.monotonic()+timeout
            while True:
                window.update()
                if errors:raise errors.pop(0)
                if condition():return
                if time.monotonic()>deadline:raise AssertionError('Mission GUI timeout: '+workspace.status.get())
                time.sleep(.01)
        try:
            view=open_missions(app);pump();view.show_location('training.4.enemy_count');pump();view.value.set('2');view.apply();pump()
            assert data(doc)['parameters']['training.4.enemy_count']==2
            workspace.invoke('Undo');pump();assert data(doc)['parameters']['training.4.enemy_count']==1
            workspace.invoke('Redo');pump();assert data(doc)['parameters']['training.4.enemy_count']==2
            view.show_location('training.4.enemy_count');view.value.set('7');before=doc.files()
            draft=capture(app._editor_scope);assert any(d['view']['kind']=='chi-missions' for d in draft['drafts'])
            try:view.apply()
            except EditorError as error:problem=dict(diagnostic(error),owner=app,scope=app._editor_scope,document=doc)
            else:raise AssertionError('Invalid mission enemy count accepted')
            assert doc.files()==before and navigate(workspace,problem) and view.value.get()=='7'
            view.value.set('2');view.apply();pump()
            view.show_location('unit:training.4.enemy.0');view.value.set('native:jenner.0');view.apply();pump()
            assert data(doc)['units']['training.4.enemy.0']=='native:jenner.0'
            view.show_location('unit:training.4.enemy.1');view.value.set('native:commando.0');view.apply();pump()
            view.group.set('Training 4: duel');pump();view.show_location('training.4.return_x');view.value.set('71')
            workspace.invoke('Save project');pump(lambda:not workspace.tasks.jobs);assert not doc.dirty and data(doc)['parameters']['training.4.return_x']==71
            assert ProjectDocument(doc.root,tool).files()==doc.files()
            pump()
            assert view.entry.winfo_viewable() and view.entry.winfo_rooty()+view.entry.winfo_height()<=view.window.winfo_rooty()+view.window.winfo_height()
            assert view.table.winfo_height()>90,'Editing controls must leave a usable map/settings table.'
            ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'chi-mission-editor.png')
            result=subprocess.run([str(root/'build/btp-chi-mission-native-tests'),'--training',str(doc.root),str(folder/'held.btp')],capture_output=True,text=True,timeout=30)
            assert result.returncode==0,result.stdout+result.stderr
            app.settings['data']=str(folder/'absent-dos');workspace.play_session.start(app._editor_scope);pump(lambda:not workspace.play_session.preparing)
            assert workspace.play_session.process and workspace.play_session.process.poll() is None,workspace.status.get()
            workspace.play_session.stop();pump(lambda:workspace.play_session.process is None)
            (work/'chi-missions-gui.json').write_bytes(encoded(dict(status='passed',checks=['typed mission settings and unit selection','Undo/Redo','invalid draft recovery/rollback and correct problem navigation','group/search navigation','Save pending fields/reopen','edited native training and held saves','Play without external DOS paths'])))
            print('PASS: mission editor settings, unit roles, drafts, Undo/Save, native training continuation and Play.',flush=True)
        finally:workspace.play_session.shutdown();workspace.tasks.shutdown();window.destroy()
