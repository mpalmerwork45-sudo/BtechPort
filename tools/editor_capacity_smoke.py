"""Exercise larger source campaigns with actual editor controls on private X11."""
def run(env,work):
    import copy,json,tempfile,time,tkinter as tk
    from pathlib import Path
    from PIL import ImageGrab
    from editor_model import ProjectDocument,create_project,encoded
    from editor_workspace import Workspace,existing_view
    from campaign_capacity import campaign
    from campaign_source import convert
    from authoring_service import revision
    root=Path(__file__).resolve().parents[1];tool=root/'build/btp-project'
    with tempfile.TemporaryDirectory(prefix='capacity-gui-',dir=work) as tmp:
        folder=Path(tmp);doc=create_project(root/'examples/beacon-demo',folder/'legacy','capacity-ui','Capacity UI',tool)
        window=tk.Tk();workspace=Workspace(window,tool,folder/'settings');window.geometry('1440x940+0+0');errors=[]
        window.report_callback_exception=lambda kind,error,tb:errors.append(error)
        timer=None;beats=[];measuring=False
        def pump(condition=lambda:True,timeout=30):
            deadline=time.monotonic()+timeout
            while True:
                window.update()
                if errors:raise errors.pop(0)
                if condition():return
                if time.monotonic()>deadline:raise AssertionError('Timed out: '+workspace.status.get())
                time.sleep(.01)
        def heartbeat():
            nonlocal timer
            beats.append(time.monotonic())
            if measuring:timer=window.after(10,heartbeat)
        try:
            app=workspace.app;app.set_document(doc);workspace.invoke('Campaign sources and build');pump()
            view=existing_view(app,'sources');old=copy.deepcopy(doc.adventure)
            view.buttons['Upgrade campaign limits'].invoke();pump()
            assert doc.adventure['schema_version']==3 and view.buttons['Upgrade campaign limits'].instate(['disabled'])
            workspace.edit_history(False);pump();assert doc.adventure==old
            workspace.edit_history(True);pump();assert doc.adventure['schema_version']==3
            workspace.invoke('Save project');pump(lambda:not workspace.tasks.jobs)
            assert ProjectDocument(doc.root,tool).adventure['schema_version']==3
            print('PASS: explicit campaign upgrade, format-aware limits, Undo/Redo and Save/reopen through workspace controls.',flush=True)

            doc.replace_adventure(campaign());doc.save();source=convert(doc,folder/'source')
            measuring=True;heartbeat();opened=time.monotonic();app.set_document(source);maps=workspace.map_view();pump()
            open_ms=round((time.monotonic()-opened)*1000,1)
            maps.map_choice.current(39);maps.change_map();maps.window.lift();pump()
            maps.zoom_control.set(24);maps.canvas.xview_moveto(0);maps.canvas.yview_moveto(0);pump()
            water=next(i for i,t in enumerate(source.adventure['tiles']) if t['id']=='beacon:water')
            maps.brush.selection_set(str(water));maps.select_brush();maps.tool.set('Paint')
            x=round(18.5*24-maps.canvas.canvasx(0));y=round(18.5*24-maps.canvas.canvasy(0))
            before=copy.deepcopy(source.adventure)
            maps.canvas.event_generate('<Button-1>',x=x,y=y);maps.canvas.event_generate('<ButtonRelease-1>',x=x,y=y);pump()
            assert source.adventure['maps'][39]!=before['maps'][39]
            workspace.invoke('Save project');pump(lambda:not workspace.tasks.jobs)
            assert ProjectDocument(source.root,tool).adventure==source.adventure
            workspace.open_world('capacity:planet-1');pump()
            assert maps.world_editor.world_id=='capacity:planet-1'
            workspace.invoke('Campaign sources and build');pump();view=existing_view(app,'sources')
            entry=next(k for k,v in view.records.items() if v['id']=='capacity:c20-brief')
            view.table.selection_set(entry);view.buttons['Open selected object'].invoke();pump()
            graph=maps.event_graph();assert graph.selected=='capacity:c20-brief'
            props=graph.properties;props.event_text.delete('1.0','end');props.event_text.insert('1.0','The last outpost needs your help. Survey its relay, then engage the patrol.')
            props.event_pending=True;workspace.invoke('Save project');pump(lambda:not workspace.tasks.jobs)
            assert not source.dirty and revision(source)==revision(ProjectDocument(source.root,tool))
            print('PASS: map 40 painting, second planet, event 383 inspector and source-owned Save/reopen.',flush=True)

            bad=copy.deepcopy(source.adventure);event=next(e for e in bad['events'] if e['id']=='capacity:c20-brief');event['next']='capacity:missing'
            source.replace_adventure(bad);workspace.invoke('Validate');pump(lambda:not workspace.tasks.jobs)
            problem=next(p for p in workspace.problems if not p.get('resolved') and p.get('source'))
            assert 'c20-brief' in problem['source']['file']
            workspace.problem_list.selection_set(str(workspace.problems.index(problem)));workspace.open_problem();pump()
            assert graph.selected=='capacity:c20-brief'
            workspace.edit_history(False);pump();workspace.invoke('Validate');pump(lambda:not workspace.tasks.jobs)
            assert problem.get('resolved')
            view.window.lift();pump();view.build(folder/'built');pump(lambda:not workspace.tasks.jobs)
            assert ProjectDocument(folder/'built',tool).adventure==source.adventure
            app.settings['player']=str(root/'build/btech-port');workspace.invoke('Play from start');pump(lambda:not workspace.play_session.preparing)
            process=workspace.play_session.process;assert process is not None
            deadline=time.monotonic()+.3;pump(lambda:time.monotonic()>deadline);assert process.poll() is None
            workspace.play_session.stop();pump(lambda:workspace.play_session.process is None)
            view.window.lift();pump();ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'editor-campaign-capacity.png')
            print('PASS: high event source diagnostic/navigation, repair, validated Build/export and normal SDL Play/Stop.',flush=True)
            measuring=False
            if timer:window.after_cancel(timer);timer=None
            memory={}
            if Path('/proc/self/status').exists():
                for line in Path('/proc/self/status').read_text().splitlines():
                    if line.startswith(('VmRSS:','VmHWM:')):memory[line.split(':')[0]]=int(line.split()[1])
            report=dict(maps=40,events=403,planets=2,source_files=len(source.source.disk),open_ms=open_ms,
                heartbeat_max_ms=round(max((b-a for a,b in zip(beats,beats[1:])),default=0)*1000,1),memory_kib=memory)
            (work/'editor-campaign-capacity.json').write_bytes(encoded(report));print(json.dumps(report),flush=True)
        finally:
            measuring=False
            if timer:window.after_cancel(timer)
            workspace.tasks.shutdown()
            process=workspace.play_session.process
            if process is not None and process.poll() is None:process.terminate();process.wait(timeout=5)
            window.destroy()
