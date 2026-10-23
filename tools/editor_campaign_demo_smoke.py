"""GUI edits followed by a scoped authoring revision of the AI8 campaign."""
def run(env,work):
    import copy,json,tempfile,time,tkinter as tk
    from pathlib import Path
    from PIL import ImageGrab
    from campaign_recipe import build,DEFAULT
    from editor_model import ProjectDocument,encoded
    from editor_workspace import Workspace
    from editor_changes import open_changes
    from editor_tasks import snapshot
    from authoring_service import revision
    from adventure_editing import composite

    root=Path(__file__).resolve().parents[1];tool=root/'build/btp-project'
    with tempfile.TemporaryDirectory(prefix='campaign GUI ',dir=work) as tmp:
        folder=Path(tmp);doc,_=build(json.loads(DEFAULT.read_bytes()),folder/'authored campaign',tool)
        window=tk.Tk();workspace=Workspace(window,tool,folder/'settings');window.geometry('1440x940+0+0');errors=[]
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
            app=workspace.app;app.set_document(doc);scope=app._editor_scope
            app.settings.update({'player':str(root/'build/btech-port'),'data':str(root/'Original DOS'),
                'dialogue-data':str(root/'work/talk-data.bin'),'combat-data':str(root/'work/combat-data.bin'),'world-data':str(root/'work/world-data.bin')})
            maps=workspace.map_view();pump();maps.zoom_control.set(24)
            maps.canvas.xview_moveto(0);maps.canvas.yview_moveto(0);pump()
            grass=next(i for i,t in enumerate(doc.adventure['tiles']) if t['id']=='frontier:grass')
            maps.brush.selection_clear(0,'end');maps.brush.selection_set(grass);maps.select_brush();maps.tool.set('Paint')
            x=round(2.5*24-maps.canvas.canvasx(0));y=round(2.5*24-maps.canvas.canvasy(0))
            maps.canvas.event_generate('<Button-1>',x=x,y=y);maps.canvas.event_generate('<ButtonRelease-1>',x=x,y=y);pump()
            assert composite(doc.adventure['maps'][0])[2][2]=='frontier:grass'
            graph=maps.event_graph();graph.selected='dispatch:welcome';graph.edit();pump()
            human='Human revision: Greybank needs a careful commander. Bring both pilots home.'
            graph.properties.event_text.delete('1.0','end');graph.properties.event_text.insert('1.0',human);pump()
            view=open_changes(app);pump()
            for rule in [dict(id='briefing',label='Human briefing',kind='fields',path='adventure.events/dispatch:welcome',fields='text'),
                         dict(id='paint',label='Human terrain',kind='map_region',map='relay:town',rect='2, 2, 1, 1')]:
                form=view.protection_form();pump()
                for key,value in rule.items():form.values[key].set(value)
                form.apply_button.invoke();pump()
                if form.window.winfo_exists():form.close();pump()
            manual=snapshot(scope);baseline=revision(manual);town=copy.deepcopy(manual.adventure['maps'][0])
            request=dict(api_version=1,request_id='ai8-gui-followup',project_id=doc.manifest['package_id'],expected_revision=baseline,
                label='Clarify the assault briefing',scope=['adventure.events/dispatch:assault-brief'],
                operations=[dict(op='object.patch',collection='events',id='dispatch:assault-brief',changes={'text':'Use the south road to reach the Jenner patrol. Protect the Trebuchet at long range. Return for payment and the convoy briefing.'})])
            file=folder/'followup.commands.json';file.write_bytes(encoded(request))
            view.load_file(file);pump(lambda:not workspace.tasks.jobs);view.refresh();pump()
            assert view.record and view.record['conflicts']==[]
            assert revision(snapshot(scope))==baseline
            view.apply_button.invoke();pump(lambda:not workspace.tasks.jobs)
            assert doc.adventure['maps'][0]==town
            assert next(e for e in doc.adventure['events'] if e['id']=='dispatch:welcome')['text']==human
            workspace.edit_history(False);pump();assert revision(doc)==baseline
            workspace.edit_history(True);pump();workspace.invoke('Save project');pump(lambda:not workspace.tasks.jobs)
            reopened=ProjectDocument(doc.root,tool);assert revision(reopened)==revision(doc)
            view.window.lift();pump();ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'ai8-gui-review.png')
            maps.window.lift();pump();ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'ai8-gui-depot.png')
            workspace.invoke('Play from start');pump(lambda:not workspace.play_session.preparing)
            process=workspace.play_session.process;assert process is not None
            deadline=time.monotonic()+.4;pump(lambda:time.monotonic()>deadline);assert process.poll() is None
            workspace.play_session.stop();pump(lambda:workspace.play_session.process is None)
            report=dict(status='passed',base_revision=baseline,result_revision=revision(doc),human_text=human,
                protected_tile=composite(doc.adventure['maps'][0])[2][2],followup=request,
                verified=['GUI paint and text drafts','protected scoped review','Undo/Redo','module Save/reopen','native Play/Stop'])
            (work/'ai8-gui-report.json').write_bytes(encoded(report))
            print('PASS: Greybank source GUI terrain/dialogue edits, protected authoring follow-up, Undo/Redo, Save/reopen and native Play/Stop.',flush=True)
        finally:
            workspace.tasks.shutdown()
            process=workspace.play_session.process
            if process is not None and process.poll() is None:process.terminate();process.wait(timeout=5)
            window.destroy()
