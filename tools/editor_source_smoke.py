"""Exercise modular projects through the real Construction Kit controls."""
def run(env,work):
    import copy,json,tempfile,time,tkinter as tk
    from pathlib import Path
    from unittest.mock import patch
    from PIL import ImageGrab
    from editor_model import ProjectDocument,create_project
    from editor_workspace import Workspace,existing_view
    from editor_recovery import capture,restore_document,conflicts
    from authoring_service import revision
    root=Path(__file__).resolve().parents[1];tool=root/'build/btp-project'
    with tempfile.TemporaryDirectory(prefix='source-gui-',dir=work) as tmp:
        folder=Path(tmp);legacy=create_project(root/'examples/beacon-demo',folder/'legacy','source-ui','Source UI',tool)
        window=tk.Tk();workspace=Workspace(window,tool,folder/'settings');window.geometry('1440x940+0+0');errors=[]
        window.report_callback_exception=lambda kind,error,tb:errors.append(error)
        def pump(condition=lambda:True,timeout=20):
            deadline=time.monotonic()+timeout
            while True:
                window.update()
                if errors:raise errors.pop(0)
                if condition():return
                if time.monotonic()>deadline:raise AssertionError('Timed out: '+workspace.status.get())
                time.sleep(.01)
        try:
            app=workspace.app;app.set_document(legacy);workspace.invoke('Campaign sources and build');pump()
            view=existing_view(app,'sources');assert view is not None
            with patch('editor_sources.filedialog.askdirectory',return_value=str(folder)),patch('editor_sources.simpledialog.askstring',return_value='modules'):
                view.buttons['Create source copy...'].invoke()
            pump(lambda:not workspace.tasks.jobs)
            assert app.document is legacy and (folder/'modules/SOURCE.json').exists()
            source=ProjectDocument(folder/'modules',tool);app.set_document(source);workspace.invoke('Campaign sources and build');pump()
            view=existing_view(app,'sources');assert view.table.get_children()
            assert view.buttons['Create source copy...'].instate(['disabled'])
            entry=next(k for k,v in view.records.items() if v['id']=='beacon:welcome')
            view.table.selection_set(entry);view.buttons['Open selected object'].invoke();pump()
            graph=app.map_editor.event_graph();assert graph.selected=='beacon:welcome'
            props=graph.properties;props.event_text.delete('1.0','end');props.event_text.insert('1.0','Edited in the source project inspector.')
            props.event_pending=True
            workspace.invoke('Save project');pump(lambda:not workspace.tasks.jobs)
            assert not source.dirty
            text=json.loads((source.root/'text/dialogue.json').read_bytes())
            assert text['beacon:welcome.text']=='Edited in the source project inspector.'
            assert revision(source)==revision(ProjectDocument(source.root,tool))
            workspace.edit_history(False);pump();workspace.edit_history(True);pump()
            assert next(e for e in source.adventure['events'] if e['id']=='beacon:welcome')['text'].startswith('Edited in')
            print('PASS: source conversion menu preserves the open package; ordinary event inspector, background Save, source text ownership, Undo/Redo and reopen.',flush=True)

            # Mouse painting still edits the same map object. Recovery captures
            # the raw source baseline as well as the compiled game snapshot.
            maps=app.map_editor;maps.window.lift();maps.zoom_control.set(24);maps.canvas.xview_moveto(0);maps.canvas.yview_moveto(0);pump()
            water=next(i for i,t in enumerate(source.adventure['tiles']) if t['id']=='beacon:water')
            maps.brush.selection_set(str(water));maps.select_brush();maps.tool.set('Paint')
            before=copy.deepcopy(source.adventure)
            x=round(22.5*24-maps.canvas.canvasx(0));y=round(19.5*24-maps.canvas.canvasy(0))
            maps.canvas.event_generate('<Button-1>',x=x,y=y);maps.canvas.event_generate('<ButtonRelease-1>',x=x,y=y);pump()
            assert source.adventure!=before
            record=capture(app._editor_scope);reopened=ProjectDocument(source.root,tool)
            assert not conflicts(record,reopened);restore_document(record,reopened);assert reopened.adventure==source.adventure
            workspace.invoke('Save project');pump(lambda:not workspace.tasks.jobs)
            assert ProjectDocument(source.root,tool).adventure==source.adventure,(workspace.status.get(),app.status.get(),source.dirty,app._editor_scope.saving,workspace.problems)
            view.window.lift();view.refresh();pump()
            ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'editor-campaign-sources.png')

            bad=copy.deepcopy(source.adventure);next(e for e in bad['events'] if e['id']=='beacon:welcome')['next']='missing:event'
            source.replace_adventure(bad);workspace.invoke('Validate');pump(lambda:not workspace.tasks.jobs)
            problem=next(p for p in workspace.problems if not p.get('resolved') and p.get('source'))
            assert 'beacon-welcome' in problem['source']['file']
            workspace.problem_list.selection_set(str(workspace.problems.index(problem)));workspace.open_problem();pump()
            assert graph.selected=='beacon:welcome'
            workspace.edit_history(False);pump();workspace.invoke('Validate');pump(lambda:not workspace.tasks.jobs)
            assert problem.get('resolved')
            print('PASS: source map painting, recovery/reopen, precise source-file diagnostic and navigation to the broken event.',flush=True)

            view.window.lift();pump()
            with patch('editor_sources.filedialog.askdirectory',return_value=str(folder)),patch('editor_sources.simpledialog.askstring',return_value='built'):
                view.buttons['Build playable package...'].invoke()
            pump(lambda:not workspace.tasks.jobs)
            built=ProjectDocument(folder/'built',tool);assert built.adventure==source.adventure
            assert (folder/'built/SOURCE-MAP.json').exists()
            app.settings['player']=str(root/'build/btech-port')
            workspace.invoke('Play from start');pump(lambda:not workspace.play_session.preparing)
            process=workspace.play_session.process;assert process is not None
            deadline=time.monotonic()+.4;pump(lambda:time.monotonic()>deadline)
            assert process.poll() is None,(workspace.play_session.folder/'player.log').read_text()
            workspace.play_session.stop();pump(lambda:workspace.play_session.process is None)
            assert not [p for p in workspace.problems if not p.get('resolved')],workspace.problems
            print('PASS: Build exports a validated playable package and source map; normal SDL Play and Stop work from modular sources.',flush=True)
            import authoring_session as protocol
            session=workspace.authoring.start(app._editor_scope,allowed_scope=['adventure.events'])
            job=protocol.submit(session,'snapshot',job_id='source-snapshot')
            job_path=protocol.job_folder(session,job['id'])/'job.json'
            pump(lambda:json.loads(job_path.read_bytes())['status']=='completed')
            result=json.loads(job_path.read_bytes())['result']
            retained=ProjectDocument(Path(result['snapshot']),tool)
            assert retained.source is not None and revision(retained)==result['revision']
            workspace.authoring.stop(app._editor_scope)
            print('PASS: local authoring session snapshot preserves editable modules and the exact advertised source revision.',flush=True)
        finally:
            workspace.tasks.shutdown()
            process=workspace.play_session.process
            if process and process.poll() is None:process.terminate();process.wait(timeout=5)
            window.destroy()
