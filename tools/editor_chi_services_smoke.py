"""Real workspace service edits, recovery and native recipient transaction."""
def run(env,work):
    import json,subprocess,tempfile,time,tkinter as tk
    from pathlib import Path
    from PIL import ImageGrab
    from chi_import import import_campaigns
    from chi_services import data
    from chi_service_evidence import purchase
    from chi_services_editor import open_services
    from editor_model import ProjectDocument,EditorError,encoded
    from editor_workspace import Workspace
    from editor_recovery import capture
    from editor_problems import navigate
    from authoring_contract import diagnostic
    root=Path(__file__).resolve().parents[1];tool=root/'build/btp-project'
    with tempfile.TemporaryDirectory(prefix='chi-services-gui-',dir=work) as temporary:
        folder=Path(temporary);import_campaigns(root/'Original DOS',folder/'pair',validator=tool)
        doc=ProjectDocument(folder/'pair/updated',tool);purchase(doc);doc.save()
        window=tk.Tk();workspace=Workspace(window,tool,folder/'state');app=workspace.app;app.set_document(doc);app.settings['player']=str(root/'build/btech-port');window.geometry('1180x820+0+0')
        errors=[];window.report_callback_exception=lambda kind,error,tb:errors.append(error)
        def pump(condition=lambda:True,timeout=30):
            deadline=time.monotonic()+timeout
            while True:
                window.update()
                if errors:raise errors.pop(0)
                if condition():return
                if time.monotonic()>deadline:raise AssertionError('Service GUI timeout: '+workspace.status.get())
                time.sleep(.01)
        try:
            view=open_services(app);pump();view.show_location('armour.price.1');pump();view.value.set('73');view.apply();pump();assert data(doc)['parameters']['armour.price.1']==73
            workspace.invoke('Undo');pump();assert data(doc)['parameters']['armour.price.1']==50
            workspace.invoke('Redo');pump();assert data(doc)['parameters']['armour.price.1']==73
            view.show_location('repair.armour');view.value.set('-1');before=doc.files()
            draft=capture(app._editor_scope);assert any(d['view']['kind']=='chi-services' for d in draft['drafts'])
            try:view.apply()
            except EditorError as error:problem=dict(diagnostic(error),owner=app,scope=app._editor_scope,document=doc)
            else:raise AssertionError('Invalid service cost accepted')
            assert doc.files()==before and view.value.get()=='-1'
            assert navigate(workspace,problem) and view.value.get()=='-1'
            view.value.set('6');view.apply();pump()
            view.pages.select(2);view.all_stock.set(False);view.units.selection_set(0);view.apply_stock();pump();assert len(data(doc)['broker_stock'])==1
            problem=dict(message='Broker stock error',field_path='$.broker_stock[0]',owner=app,scope=app._editor_scope,document=doc)
            assert navigate(workspace,problem) and view.pages.index(view.pages.select())==2
            view.pages.select(1);view.action_table.selection_set('native.repair-mech');view.show_action();pump()
            ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'chi-service-editor.png')
            # Save collects a still-pending service field before native Play.
            view.pages.select(0);view.show_location('armour.price.1');view.value.set('74')
            workspace.invoke('Save project');pump(lambda:not workspace.tasks.jobs);assert not doc.dirty and data(doc)['parameters']['armour.price.1']==74
            assert ProjectDocument(doc.root,tool).files()==doc.files()
            r=subprocess.run([str(root/'build/btp-chi-service-native-tests'),'--purchase',str(doc.root),str(folder/'held.btp')],capture_output=True,text=True,timeout=30);assert r.returncode==0,r.stdout+r.stderr
            app.settings['data']=str(folder/'absent-dos');workspace.play_session.start(app._editor_scope);pump(lambda:not workspace.play_session.preparing)
            assert workspace.play_session.process and workspace.play_session.process.poll() is None,workspace.status.get()
            workspace.play_session.stop();pump(lambda:workspace.play_session.process is None)
            (work/'chi-services-gui.json').write_bytes(encoded(dict(status='passed',checks=['typed cost and broker-stock edits','Undo/Redo','invalid draft recovery/rollback and problem navigation','native action catalogue','Save pending fields/reopen','native recipient transaction and held saves','Play without external DOS paths'])))
            print('PASS: service editor parameters, broker stock, action registry, drafts, Undo/Save and native recipient transaction.',flush=True)
        finally:workspace.play_session.shutdown();workspace.tasks.shutdown();window.destroy()
