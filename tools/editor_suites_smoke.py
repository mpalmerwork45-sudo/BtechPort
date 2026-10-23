"""Use real workspace forms, retained native reports and diagnostic navigation."""
def run(env,work):
    import copy,json,tempfile,time,tkinter as tk
    from pathlib import Path
    from PIL import ImageGrab
    from editor_model import ProjectDocument,encoded
    from editor_workspace import Workspace
    from editor_suites import open_suites
    from editor_tasks import snapshot
    from editor_recovery import capture,open_route
    from review_selection_demo import create
    from campaign_source import convert
    import suite_authoring as model
    root=Path(__file__).resolve().parents[1];tool=root/'build/btp-project'
    with tempfile.TemporaryDirectory(prefix='suite-gui-',dir=work) as tmp:
        folder=Path(tmp);doc,path=create(folder/'fixture',tool);doc=convert(doc,folder/'source')
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
        def apply(form,values):
            for k,v in values.items():form.values[k].set(str(v))
            form.apply_button.invoke();pump();assert not form.window.winfo_exists(),form.error.get();view.refresh();pump()
        try:
            app=workspace.app;app.set_document(doc);scope=app._editor_scope;view=open_suites(app);pump()
            apply(view.suite_form(),dict(id='authored',name='Authored routes'))
            apply(view.case_form(),dict(id='walk',starter='world',target='survey:aster',x=54,y=64,seeds='42, 2026'))
            assert len(view.case()['scenario']['steps'])==4
            view.run_selected(inspect=True);pump(lambda:view.job is None)
            assert view.inventory['cases'][0]['status']=='not_run' and not any(e['observed'] for e in view.inventory['events'])
            view.pages.select(1);view.steps.selection_set('1')
            form=view.step_form(True);form.values['x'].set('90');pump()
            saved=capture(scope);draft=next(d for d in saved['drafts'] if d['view']['kind']=='form')
            assert draft['view']['action']['method']=='step_form'
            candidate=snapshot(scope);assert model.suites(candidate)[0]['cases'][0]['scenario']['steps'][1]['at']==[90,64]
            assert view.case()['scenario']['steps'][1]['at']==[54,64],'Preview consumed the live draft'
            form.window.destroy();restored=open_route(scope,draft['view']);restored.restore_draft(draft['state'])
            assert restored.values['x'].get()=='90';apply(restored,dict(x=54))
            view.window.lift();workspace.edit_history(False);pump();workspace.edit_history(True);pump()
            view.run_selected(True);pump(lambda:view.job is None)
            assert view.inventory['cases'][0]['status']=='passed',view.inventory['cases'][0]
            workspace.invoke('Save project');pump(lambda:not workspace.tasks.jobs)
            reopened=ProjectDocument(doc.root,tool);assert model.suites(reopened)[0]['cases'][0]['seeds']==[42,2026]
            view.import_file(path);pump();view.refresh();view.run_selected(True);pump(lambda:view.job is None)
            assert all(c['status']=='passed' for c in view.inventory['cases']),view.inventory
            view.current_case='yard';view.cases.selection_set('yard');view.run_selected();pump(lambda:view.job is None)
            assert [c['status'] for c in view.inventory['cases']]==['passed','not_run','not_run']
            assert any(b['observed'] for b in view.inventory['branches'])
            ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'suite-authoring-cases.png')
            # A valid definition containing an impossible destination produces
            # retained native evidence and opens the actual map on double-click.
            suite=view.suite();suite['cases'][0]['scenario']['steps'][1]['at']=[400,400]
            model.put(doc,suite,suite['id']);view.refresh();view.run_selected();pump(lambda:view.job is None)
            assert view.inventory['cases'][0]['status']=='failed'
            view.pages.select(2);pump()
            problem=next((key for key,d in view.targets.items() if d.get('location')),None);assert problem,view.inventory
            view.coverage.item(view.coverage.parent(problem),open=True);view.coverage.selection_set(problem);view.navigate();pump()
            assert workspace.current_view().key[1]=='maps'
            assert app.map_editor.scene()['id']=='survey:yard'
            view.window.lift();pump();ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'suite-authoring-coverage.png')
            # Changed drafts remain visibly historical; an export cannot
            # consume or save their pending fields.
            form=view.suite_form(True);form.values['name'].set('Pending suite name');before=model.suites(doc)
            view.export(folder);pump(lambda:not workspace.tasks.jobs)
            assert model.suites(doc)==before and form.window.winfo_exists()
            form.window.destroy();view.cancel();workspace.invoke('Save project');pump(lambda:not workspace.tasks.jobs)
            view.run_selected(True);view.cancel();pump(lambda:view.job is None)
            assert 'cancel' in view.status.get().lower()
            (work/'suite-authoring-gui.json').write_bytes(encoded(dict(status='passed',checks=[
                '1024x740 workspace controls','owned suite/case/steps forms','source project Save/reopen','two-seed native test',
                'form snapshot without consumption','recover step draft','Undo/Redo','suite import/export','selected/full native runs',
                'unselected stays Not run','observed branch inventory','native failure map navigation','export preserves pending form'])))
            print('PASS: suite authoring, source Save/reopen, draft recovery, selected/full native checks and coverage navigation.',flush=True)
        finally:
            workspace.play_session.shutdown();workspace.tasks.shutdown();window.destroy()
