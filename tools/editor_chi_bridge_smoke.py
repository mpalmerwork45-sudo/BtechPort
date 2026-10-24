"""Exercise quest authoring beside native maps, with real workspace Save/Play."""
def run(env,work):
    import copy,json,subprocess,tempfile,time,tkinter as tk
    from pathlib import Path
    from PIL import ImageGrab
    from chi_import import import_campaigns
    from chi_bridge import events,data
    from chi_bridge_editor import open_quests
    from chi_bridge_evidence import nested
    from chi_bld_editor import open_scripts
    from editor_model import ProjectDocument,encoded,EditorError
    from editor_workspace import Workspace
    from editor_recovery import capture,open_route
    from editor_problems import navigate
    from authoring_contract import diagnostic
    root=Path(__file__).resolve().parents[1];tool=root/'build/btp-project'
    with tempfile.TemporaryDirectory(prefix='chi-bridge-gui-',dir=work) as temporary:
        folder=Path(temporary);import_campaigns(root/'Original DOS',folder/'pair',validator=tool)
        doc=ProjectDocument(folder/'pair/updated',tool)
        window=tk.Tk();workspace=Workspace(window,tool,folder/'state');app=workspace.app;app.set_document(doc)
        app.settings['player']=str(root/'build/btech-port');window.geometry('1100x780+0+0')
        errors=[];window.report_callback_exception=lambda kind,error,tb:errors.append(error)
        def pump(condition=lambda:True,timeout=30):
            deadline=time.monotonic()+timeout
            while True:
                window.update()
                if errors:raise errors.pop(0)
                if condition():return
                if time.monotonic()>deadline:raise AssertionError('Quest GUI timeout: '+workspace.status.get())
                time.sleep(.01)
        try:
            app.edit_adventure();maps=app.map_editor;pump()
            view=open_quests(app);pump();view.add_example();pump()
            assert data(doc)['entrances'][0]['event']=='bridge:welcome'
            view.show_location('bridge:cadet');view.event_text.delete('1.0','end');view.event_text.insert('1.0','The GUI quest is editable.');view.event_pending=True
            workspace.invoke('Save project');pump(lambda:not workspace.tasks.jobs)
            assert not doc.dirty and events(doc)['events'][2]['text']=='The GUI quest is editable.'
            workspace.invoke('Undo');pump();assert events(doc)['events'][2]['text']!='The GUI quest is editable.'
            workspace.invoke('Redo');pump();assert events(doc)['events'][2]['text']=='The GUI quest is editable.'
            # Native maps stay projected in their own editor while quest maps
            # keep ordinary terrain/events, backed by the same project history.
            assert maps.document is doc and view.document.base is doc
            assert len(maps.adventure['maps'])==15 and len(view.adventure['maps'])==1
            expected=copy.deepcopy(doc.adventure);a=view.adventure;a['maps'][0]['name']='Optional patrol field';view.commit(a);pump()
            assert doc.adventure==expected and view.scene()['name']=='Optional patrol field'
            f=view.bindings();pump();assert f.window.winfo_viewable();f.values['event'].set('bridge:cadet')
            saved=capture(app._editor_scope);draft=next(v for v in saved['drafts'] if v['view']['kind']=='form')
            assert draft['view']['owner']['kind']=='chi-quests';f.window.destroy();pump()
            restored=open_route(app._editor_scope,draft['view']);restored.restore_draft(draft['state']);pump()
            assert restored.values['event'].get()=='bridge:cadet';restored.values['event'].set('bridge:welcome');restored.apply_pending();restored.window.destroy();pump()
            f=view.calls();pump();f.values['return'].set('chi:comstar-02ce')
            before=doc.files()
            try:f.apply_pending()
            except EditorError as error:problem=dict(diagnostic(error),owner=app,scope=app._editor_scope,document=doc)
            else:raise AssertionError('Native receipt boundary was accepted before its wait.')
            assert doc.files()==before;f.window.destroy();pump();assert navigate(workspace,problem);pump()
            # Close the navigated adapter form after checking it belongs to
            # this quest view, not the roster or a hidden window.
            for draft in list(app._editor_scope.live()):
                form=draft.view
                if isinstance(getattr(form,'values',None),dict) and 'return' in form.values:form.window.destroy()
            pump();view.show_location('bridge:cadet');view.event_vars['next'].set('quest:missing');view.event_pending=True
            draft=next(v for v in capture(app._editor_scope)['drafts'] if v['view']['kind']=='chi-quests')
            view.restore_draft(draft['state']);assert view.event_vars['next'].get()=='quest:missing'
            problem=dict(message='chi-events.json: $.events[bridge:cadet].next: missing event',owner=app,scope=app._editor_scope,document=doc)
            assert navigate(workspace,problem) and view.event_vars['next'].get()=='quest:missing'
            view.event_vars['next'].set('bridge:choice');view.apply_event();pump()
            graph=view.event_graph();pump();graph.selected='bridge:bank-call';graph.edit();pump()
            assert maps.event_graph() is graph,'Native maps must open real quests, never execute their projection placeholders.'
            assert graph.document.adventure['events']==events(doc)['events']
            nested(doc);scripts=open_scripts(app);scripts.show_location('chi:bld-armor','test:quest-call');pump()
            assert scripts.fields['event'].get()=='test:menu' and scripts.fields['cancel'].get()=='test:cancel-label'
            scripts.fields['note'].set('Authored quest with native return labels.');scripts.apply();pump()
            workspace.invoke('Save project');pump(lambda:not workspace.tasks.jobs)
            assert not doc.dirty and ProjectDocument(doc.root,tool).files()==doc.files()
            from chi_coverage_editor import open_coverage
            actions=folder/'bank.actions';actions.write_text('right\nright\naccept\naccept\ndown\naccept\naccept\n1\naccept\naccept\ncancel\n')
            trace=folder/'bld.jsonl'
            result=subprocess.run([str(root/'build/btech-headless'),'--project',str(doc.root),'--play-here','chi:map-01','69','25','--replay',str(actions),'--bld-trace',str(trace)],capture_output=True,text=True,timeout=30)
            assert result.returncode==0,result.stderr
            coverage=open_coverage(app);coverage.load([trace]);pump(lambda:coverage.report is not None)
            rows=[child for building in coverage.table.get_children() for instruction in coverage.table.get_children(building) for child in coverage.table.get_children(instruction)]
            assert any(coverage.table.item(row,'text')=='Native adapter success' and str(coverage.table.item(row,'values')[-1])=='1' for row in rows)
            view.window.lift();view.show_location('bridge:cadet');pump()
            ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'chi-quest-editor.png')
            app.settings['data']=str(folder/'absent-dos');workspace.play_session.start(app._editor_scope);pump(lambda:not workspace.play_session.preparing)
            assert workspace.play_session.process and workspace.play_session.process.poll() is None,workspace.status.get()
            workspace.play_session.stop();pump(lambda:workspace.play_session.process is None)
            (work/'chi-bridge-gui.json').write_bytes(encoded(dict(status='passed',checks=['native/quest map separation','example and editable dialogue','Undo/Redo and pending Save','doorway/call draft recovery','receipt validation and problem navigation','event graph and typed BLD event call','Save/reopen','source-linked native adapter outcome counts','native Play without external DOS paths'])))
            print('PASS: mixed quest workspace, bindings, recovery, graph, BLD call, Undo/Save and native Play.',flush=True)
        finally:workspace.play_session.shutdown();workspace.tasks.shutdown();window.destroy()
