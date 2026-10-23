"""Comparable GUI-thread measurements with a realistic accumulated Undo stack.

Timing samples exclude the separate cProfile pass. This fixture also checks
draft isolation, rollback, cancellation and edits made while work is running.
"""
def run(env,work):
    import copy,cProfile,io,json,os,pstats,statistics,tempfile,threading,time,tkinter as tk
    from pathlib import Path
    from types import SimpleNamespace
    from editor_model import ProjectDocument,create_project,EditorError,encoded
    from editor_workspace import Workspace
    from editor_sources import open_sources
    from editor_tasks import snapshot,validate
    from editor_session import register
    from campaign_capacity import campaign
    from campaign_source import convert
    from event_editing import editor_data,editor_commit
    root=Path(__file__).resolve().parents[1];tool=root/'build/btp-project'
    label=os.environ.get('BTP_RESPONSE_LABEL','latest')
    if label not in ('before','after','latest'):raise ValueError('BTP_RESPONSE_LABEL must be before, after or latest.')
    with tempfile.TemporaryDirectory(prefix='responsive-gui-',dir=work) as tmp:
        folder=Path(tmp);doc=create_project(root/'examples/beacon-demo',folder/'package','responsiveness','Responsiveness',tool)
        doc.replace_adventure(campaign());doc.save();doc=convert(doc,folder/'source')
        window=tk.Tk();workspace=Workspace(window,tool,folder/'settings');window.geometry('1024x740+0+0');errors=[];timer=None;beats=[];measuring=False
        window.report_callback_exception=lambda kind,error,tb:errors.append(error)
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
            if measuring:beats.append(time.monotonic())
            timer=window.after(10,heartbeat)
        samples={};profile=cProfile.Profile()
        def measure(name,operation):
            nonlocal measuring
            values=[]
            for _ in range(3):
                measuring=True;beats.append(time.monotonic());start=time.monotonic();operation();values.append((time.monotonic()-start)*1000);pump();measuring=False
            samples[name]=dict(median_ms=round(statistics.median(values),2),samples_ms=[round(t,2) for t in values])
            # Profile only one extra execution, so profiler overhead cannot
            # inflate the latency measurement being compared across versions.
            profile.runcall(operation);pump();print(name+': '+str(samples[name]),flush=True)
        try:
            app=workspace.app;app.set_document(doc);scope=app._editor_scope;sources=open_sources(app);pump();heartbeat()
            for i in range(20):
                data=editor_data(doc);data['benchmark_note']=str(i);editor_commit(doc,data)
            pump();assert len(doc.undo_stack)==20
            measure('snapshot_with_20_undo',lambda:snapshot(scope))
            measure('preview_transaction',lambda:scope.transact(lambda:None,preview=True))
            measure('source_view_refresh',sources.refresh)
            def metadata_edit():
                data=editor_data(doc);data['benchmark_note']+='.';editor_commit(doc,data)
            measure('metadata_edit',metadata_edit)
            measure('undo_redo',lambda:(workspace.edit_history(False),workspace.edit_history(True)))
            def inventory_and_tables():
                # Ownership caching is presentational. Structural edits must still
                # rebuild the inventory, including removal and Undo restoration.
                a=copy.deepcopy(doc.adventure);a['events'].append(dict(id='capacity:new-event',op='end'));doc.replace_adventure(a);sources.refresh()
                record=next(r for r in sources.records.values() if r['id']=='capacity:new-event');assert record['file']
                workspace.edit_history(False);assert not any(r['id']=='capacity:new-event' for r in sources.records.values())
                workspace.edit_history(True);assert any(r['id']=='capacity:new-event' for r in sources.records.values())
                workspace.edit_history(False)
                # Bulk refresh, natural order, numeric sorting, child rows and
                # detach/reinsert exercise the shared table proxy after its change.
                from tkinter import ttk
                from editor_lists import TableOrder
                table=ttk.Treeview(window,columns=('number',),show='tree headings');table.pack();pump()
                order=getattr(table,'table_order',None) or TableOrder(table)
                for i in range(1000):table.insert('','end',iid='row'+str(i),text='Row '+str(i),values=(1000-i,))
                table.insert('row0','end',iid='child',text='Child',values=(0,));natural=list(table.get_children())
                order.click('number');assert table.get_children()[0]=='row999'
                order.click('number');assert table.get_children()[0]=='row0'
                order.click('number');assert list(table.get_children())==natural
                table.detach('row3');table.move('row3','','end');order.click('number');order.click('number');order.click('number')
                assert table.get_children()[-1]=='row3' and table.parent('child')=='row0'
                table.destroy();pump()
            # A pending field is part of a worker snapshot, but remains pending
            # and leaves current history unchanged until the user applies it.
            draft_window=tk.Toplevel(window);draft_owner=SimpleNamespace(window=draft_window,owner=app)
            field={'credits':1234};initial=doc.adventure['start']['credits'];history=len(doc.undo_stack)
            def apply_field():
                a=copy.deepcopy(doc.adventure);a['start']['credits']=int(field['credits']);doc.replace_adventure(a)
            register(draft_owner,pending=lambda:True,apply=apply_field,capture=lambda:dict(field),restore=lambda s:field.update(s))
            candidate=snapshot(scope);assert candidate.adventure['start']['credits']==1234
            assert doc.adventure['start']['credits']==initial and len(doc.undo_stack)==history
            measure('snapshot_with_pending_field',lambda:snapshot(scope))
            field['credits']='invalid'
            try:scope.transact(lambda:None)
            except ValueError:pass
            else:raise AssertionError('Invalid draft should fail')
            assert field['credits']=='invalid' and doc.adventure['start']['credits']==initial
            draft_window.destroy();scope.live();inventory_and_tables()
            # Cancellation is delivered to a real worker while normal edits
            # and Undo still run. A worker completion cannot publish old data.
            started=threading.Event();finished=threading.Event();published=[];failures=[]
            def background(cancel):
                started.set();cancel.wait(3);finished.set();return 'obsolete'
            job=workspace.tasks.submit('Cancellation probe',app,background,published.append,failures.append)
            pump(started.is_set);metadata_edit();after=editor_data(doc);workspace.edit_history(False);workspace.edit_history(True)
            assert editor_data(doc)==after
            job.cancelled.set();pump(lambda:finished.is_set() and not workspace.tasks.jobs)
            assert not published and failures
            validate(workspace,scope);metadata_edit();pump(lambda:not workspace.tasks.jobs)
            assert doc.dirty
            workspace.invoke('Save project');pump(lambda:not workspace.tasks.jobs)
            assert ProjectDocument(doc.root,tool).metadata==doc.metadata and not doc.dirty
            stream=io.StringIO();pstats.Stats(profile,stream=stream).strip_dirs().sort_stats('cumulative').print_stats(35)
            (work/('responsiveness-'+label+'-profile.txt')).write_text(stream.getvalue());profile.dump_stats(str(work/('responsiveness-'+label+'.prof')))
            memory={}
            for line in Path('/proc/self/status').read_text().splitlines():
                if line.startswith(('VmRSS:','VmHWM:')):memory[line.split(':')[0]]=int(line.split()[1])
            result=dict(fixture=dict(maps=40,events=403,planets=2,undo_states=20,source_files=len(doc.source.disk)),samples=samples,memory_kib=memory,
                timing_basis='Three GUI-thread operation samples, plus separate untimed cProfile runs; same fixture and interpreter. Local measurements, not a universal speed claim.',
                checks=['pending draft isolation','invalid field rollback','background cancellation','editing and Undo during worker','stale validation','source Save/reopen',
                        'source membership cache invalidation','1,000-row three-state sorting','child rows and detach/reparent'])
            (work/('responsiveness-'+label+'.json')).write_bytes(encoded(result));print(json.dumps(result),flush=True)
        finally:
            if timer:window.after_cancel(timer)
            workspace.play_session.shutdown();workspace.tasks.shutdown();window.destroy()
