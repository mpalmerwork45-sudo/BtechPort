"""Real workspace edits, shared history/drafts and native BLD gameplay proof."""
def run(env,work):
    import copy,subprocess,tempfile,time,tkinter as tk
    from pathlib import Path
    from PIL import ImageGrab
    from chi_import import import_campaigns
    from chi_bld import data,find
    from chi_bld_evidence import story_setup
    from chi_bld_editor import open_scripts
    from editor_model import ProjectDocument,encoded,EditorError
    from editor_workspace import Workspace
    from editor_recovery import capture
    from editor_problems import navigate
    root=Path(__file__).resolve().parents[1];tool=root/'build/btp-project'
    with tempfile.TemporaryDirectory(prefix='chi-bld-gui-',dir=work) as temporary:
        folder=Path(temporary);import_campaigns(root/'Original DOS',folder/'pair',validator=tool)
        doc=ProjectDocument(folder/'pair/original',tool);story_setup(doc);doc.save()
        window=tk.Tk();workspace=Workspace(window,tool,folder/'state');app=workspace.app;app.set_document(doc)
        app.settings['player']=str(root/'build/btech-port');window.geometry('1100x780+0+0')
        errors=[];window.report_callback_exception=lambda kind,error,tb:errors.append(error)
        def pump(condition=lambda:True,timeout=30):
            deadline=time.monotonic()+timeout
            while True:
                window.update()
                if errors:raise errors.pop(0)
                if condition():return
                if time.monotonic()>deadline:raise AssertionError('BLD GUI timed out: '+workspace.status.get())
                time.sleep(.01)
        try:
            view=open_scripts(app);pump();view.show_location('chi:bld-armor','edit:text');pump()
            view.text.delete('1.0','end');view.text.insert('1.0','C4.1 edited building dialogue.\n');view.apply();pump()
            workspace.invoke('Undo');pump();assert find(data(doc),'chi:bld-armor','edit:text')['text']=='Before the edit.'
            workspace.invoke('Redo');pump();assert 'C4.1' in find(data(doc),'chi:bld-armor','edit:text')['text']
            view.show_location('chi:bld-armor','edit:condition');pump();view.fields['index'].set('100')
            draft=capture(app._editor_scope);assert any(d['view']['kind']=='chi-bld' for d in draft['drafts'])
            before=doc.files()
            try:view.apply()
            except EditorError as error:
                from authoring_contract import diagnostic
                problem=dict(diagnostic(error),owner=app,scope=app._editor_scope,document=doc)
            else:raise AssertionError('Invalid story index accepted')
            assert doc.files()==before and view.fields['index'].get()=='100'
            assert navigate(workspace,problem);assert view.selected=='edit:condition'
            view.fields['index'].set('83');view.apply();pump()
            view.show_location('chi:bld-armor','edit:hop');view.fields['target'].set('edit:cash');view.apply();pump()
            view.show_location('chi:bld-armor','edit:menu');view.targets[0].set('edit:pass');view.apply();pump()
            view.resize_targets(1)
            try:view.apply()
            except EditorError:pass
            else:raise AssertionError('Wrong menu destination count accepted')
            assert len(view.targets)==3
            state=view.capture_draft();view.restore_draft(state);assert len(view.targets)==3
            view.resize_targets(-1);view.apply();pump()
            view.show_location('chi:bld-armor','edit:cash');view.fields['action'].set('10');view.apply();pump()
            ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'chi-bld-editor.png')
            workspace.invoke('Save project');pump(lambda:not workspace.tasks.jobs);assert not doc.dirty
            assert ProjectDocument(doc.root,tool).files()==doc.files()
            result=subprocess.run([str(root/'build/btp-chi-bld-tests'),'--story',str(doc.root),str(folder/'held.btp')],capture_output=True,text=True,timeout=30)
            assert result.returncode==0,result.stdout+result.stderr
            app.settings['data']=str(folder/'absent-dos');workspace.play_session.start(app._editor_scope);pump(lambda:not workspace.play_session.preparing)
            assert workspace.play_session.process and workspace.play_session.process.poll() is None,workspace.status.get()
            workspace.play_session.stop();pump(lambda:workspace.play_session.process is None)
            (work/'chi-bld-gui.json').write_bytes(encoded(dict(status='passed',checks=['typed dialogue/condition/branch/menu/native edits','Undo/Redo',
                'invalid draft recovery/rollback','source-label problem navigation','Save/reopen','native building entry and held saves','Play without external resources'])))
            print('PASS: BLD editor text, condition, branch, menu/action edits, drafts, source diagnostics, Undo/Save and native play.',flush=True)
        finally:
            workspace.play_session.shutdown();workspace.tasks.shutdown();window.destroy()
