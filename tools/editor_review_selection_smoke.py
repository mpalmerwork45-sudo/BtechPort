"""Exercise retained scenario selection, explanations and native check reports."""
def run(env,work):
    import json,tempfile,time,tkinter as tk
    from pathlib import Path
    from PIL import ImageGrab
    from editor_model import encoded,ProjectDocument
    from editor_workspace import Workspace
    from editor_changes import open_changes
    from editor_tasks import snapshot
    from authoring_service import revision
    from review_selection_demo import create,request
    import authoring_review as review

    root=Path(__file__).resolve().parents[1];tool=root/'build/btp-project'
    with tempfile.TemporaryDirectory(prefix='review-selection-gui-',dir=work) as tmp:
        folder=Path(tmp);doc,suite=create(folder/'fixture',tool)
        window=tk.Tk();workspace=Workspace(window,tool,folder/'settings');window.geometry('1024x740+0+0');errors=[]
        window.report_callback_exception=lambda kind,error,tb:errors.append(error)
        def pump(condition=lambda:True,timeout=30):
            deadline=time.monotonic()+timeout
            while True:
                window.update()
                if errors:raise errors.pop(0)
                if condition():return
                if time.monotonic()>deadline:raise AssertionError('Timed out: '+workspace.status.get())
                time.sleep(.01)
        try:
            app=workspace.app;app.set_document(doc);scope=app._editor_scope;baseline=revision(snapshot(scope))
            view=open_changes(app);source=folder/'proposal.json';source.write_bytes(encoded(request(snapshot(scope))))
            view.load_file(source);pump(lambda:not workspace.tasks.jobs)
            assert view.record['status']=='ready',view.record
            view.detail.select(4);pane=view.review_checks
            pane.choose(suite);pump(lambda:not workspace.tasks.jobs)
            assert pane.chosen=={'yard'} and pane.impact['suggested']==['yard']
            assert 'survey:yard-welcome' in pane.details.get('1.0','end')
            assert pane.listing.set('range','result')=='Not run'
            pane.listing.focus_force();pane.listing.selection_set('range');pane.listing.event_generate('<space>');pump()
            assert pane.chosen=={'yard','range'}
            pane.suggested();pane.run_button.invoke();pump(lambda:not workspace.tasks.jobs)
            assert pane.listing.set('yard','result')=='Passed' and pane.listing.set('range','result')=='Not run'
            assert len(review.read(view.folder)['checks'])==1
            pane.none();pump();assert pane.run_button.instate(['disabled']) and not pane.full_button.instate(['disabled'])
            pane.full_button.invoke();pump(lambda:not workspace.tasks.jobs)
            assert all(pane.listing.set(c,'result')=='Passed' for c in ('yard','range','world'))
            pane.suggested();pane.run_button.invoke();pump(lambda:not workspace.tasks.jobs)
            assert pane.listing.set('range','result')=='Not run','An earlier full-suite pass must not impersonate the latest selected run.'
            assert revision(snapshot(scope))==baseline
            ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'review-selection-layout.png')
            assert pane.listing.winfo_height()>90,(pane.parent.winfo_height(),pane.listing.winfo_height())
            assert pane.full_button.winfo_viewable() and pane.run_button.winfo_viewable()
            ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'review-selection-cases.png')
            pane.listing.selection_set('yard');pane.pages.select(1);pump();assert pane.details.winfo_height()>100
            ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'review-selection-explanation.png')
            pane.pages.select(0)
            # Opaque control must be visible, with all cases suggested. Retain
            # that suite for review only; raw Space is not a declared success.
            scenario=json.loads((suite.parent/'yard.json').read_bytes());scenario['steps']=[dict(op='input',action='space')]
            (suite.parent/'yard.json').write_bytes(encoded(scenario));pane.choose(suite);pump(lambda:not workspace.tasks.jobs)
            assert pane.chosen=={'yard','range','world'} and 'unknown' in pane.note.get().lower()
            assert 'Raw input' in pane.details.get('1.0','end')
            ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'review-selection-unknown.png')
            # A completed worker for an old proposal must not repaint the new
            # proposal's case list. The retained old evidence remains available.
            pane.choose(suite)
            new=folder/'other';review.prepare(snapshot(scope),request(snapshot(scope),'tile'),new,visuals=False)
            pane.load(review.read(new),new);pump(lambda:not workspace.tasks.jobs)
            assert pane.identity[0]==str(new) and pane.impact is None
            pane.load(view.record,view.folder);pump()
            # The selection workflow never publishes candidate edits itself.
            view.apply();pump(lambda:not workspace.tasks.jobs)
            assert revision(snapshot(scope))!=baseline
            workspace.edit_history(False);pump();assert revision(snapshot(scope))==baseline
            workspace.edit_history(True);pump()
            workspace.invoke('Save project');pump(lambda:not workspace.tasks.jobs)
            reopened=ProjectDocument(doc.root,tool)
            assert next(e for e in reopened.adventure['events'] if e['id']=='survey:yard-welcome')['text']=='The yard is ready for inspection.'
            (work/'review-selection-gui.json').write_bytes(encoded(dict(status='passed',checks=[
                '1024x740 layout','explained suggestions','Space toggles case','selected native checks',
                'empty selection disabled','full suite','unselected cases reset to Not run',
                'opaque control full-suite fallback','stale worker discarded','no live mutation','validated apply / Undo / Redo / Save'])))
            print('PASS: explained case selection, native selected/full checks, unknown fallback, stale worker, apply/Undo/Save.',flush=True)
        finally:
            workspace.play_session.shutdown();workspace.tasks.shutdown();window.destroy()
