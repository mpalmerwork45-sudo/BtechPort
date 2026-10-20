"""A human edits Last Beacon, then a live author proposes a constrained revision."""
def run(env,work):
    import copy,hashlib,json,os,subprocess,sys,tempfile,threading,time
    from pathlib import Path
    import tkinter as tk
    from unittest.mock import patch
    from PIL import ImageGrab
    from editor_model import ProjectDocument,create_project,encoded
    from editor_workspace import Workspace
    from editor_changes import open_changes
    from editor_tasks import snapshot
    from editor_session import apply_draft
    from authoring_service import revision
    from authoring_contract import AuthoringError
    from authoring_protection import rules,edit_rule
    import authoring_session as session
    import authoring_review as review
    from event_editing import editor_data
    from adventure_editing import composite

    root=Path(__file__).resolve().parents[1];work=Path(work);os.environ['DISPLAY']=env['DISPLAY']
    original={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'examples/battletech-demo').iterdir() if p.is_file()}
    with tempfile.TemporaryDirectory(prefix='collaboration-gui-',dir=work) as temporary:
        folder=Path(temporary);doc=create_project(root/'examples/battletech-demo',folder/'game','collaboration-test','Collaborative Last Beacon',root/'build/btp-project')
        window=tk.Tk();workspace=Workspace(window,doc.validator,folder/'settings');window.geometry('1440x980+0+0');errors=[]
        previous_hook=sys.unraisablehook;sys.unraisablehook=lambda unraisable:errors.append(unraisable.exc_value)
        window.report_callback_exception=lambda kind,error,tb:errors.append(error)
        def pump(condition=lambda:True,timeout=30):
            end=time.monotonic()+timeout
            while True:
                window.update()
                if errors:raise errors.pop(0)
                if condition():return
                if time.monotonic()>end:raise AssertionError('Timed out: '+workspace.status.get())
                time.sleep(.01)
        def job_done(connection,identity):return session.wait(connection,identity,0)['status'] not in ('queued','running')
        def request(identity,ops):
            return dict(api_version=1,request_id=identity,project_id=doc.manifest['package_id'],expected_revision=revision(snapshot(scope)),
                label='Revise the road encounter',brief='Adjust the checkpoint and road; keep human dialogue, roof and doorway.',
                scope=['adventure.maps/beacon:road','adventure.encounters/beacon:roadblock'],operations=ops,
                groups=[dict(id='encounter',label='Move the raider',operations=[0]),dict(id='road',label='Extend the road',operations=[1])] if len(ops)==2 else [])
        try:
            app=workspace.app;app.set_document(doc);scope=app._editor_scope
            app.settings.update({'player':str(root/'build/btech-port'),'data':str(root/'Original DOS'),
                'dialogue-data':str(root/'work/talk-data.bin'),'combat-data':str(root/'work/combat-data.bin'),'world-data':str(root/'work/world-data.bin')})
            app.edit_adventure();pump();maps=app.map_editor;maps.zoom_control.set(24);pump()
            # Paint one actual generated roof cell using the normal mouse path.
            maps.canvas.xview_moveto(0);maps.canvas.yview_moveto(0);grass=next(i for i,t in enumerate(doc.adventure['tiles']) if t['id']=='beacon:grass-detail')
            maps.brush.selection_clear(0,'end');maps.brush.selection_set(grass);maps.select_brush();maps.tool.set('Paint');pump()
            x,y=6.5*24-maps.canvas.canvasx(0),6.5*24-maps.canvas.canvasy(0)
            maps.canvas.event_generate('<Button-1>',x=round(x),y=round(y));maps.canvas.event_generate('<ButtonRelease-1>',x=round(x),y=round(y));pump()
            assert composite(doc.adventure['maps'][0])[6][6]=='beacon:grass-detail'
            # Move the exchange doorway through the real drag gesture.
            door=copy.deepcopy(doc.adventure['maps'][0]['entrances'][0]);maps.tool.set('Move markers');pump()
            x,y=door['at'][0]*12-maps.canvas.canvasx(0),door['at'][1]*12-maps.canvas.canvasy(0)
            maps.canvas.event_generate('<Button-1>',x=round(x),y=round(y));pump()
            maps.canvas.event_generate('<B1-Motion>',x=round(x+12),y=round(y));pump()
            maps.canvas.event_generate('<ButtonRelease-1>',x=round(x+12),y=round(y));pump()
            assert doc.adventure['maps'][0]['entrances'][0]['at']==[door['at'][0]+1,door['at'][1]]
            # Leave human dialogue as a valid, unsaved inspector draft. The
            # session snapshot must include it, and Undo must later retain it.
            graph=maps.event_graph();graph.selected='beacon:welcome';graph.edit();pump();props=graph.properties
            props.event_text.delete('1.0','end');props.event_text.insert('1.0','Human briefing: protect Grayhaven and bring everyone home.');pump()
            view=open_changes(app);pump()
            for rule in [dict(id='briefing',label='Human briefing',kind='fields',path='adventure.events/beacon:welcome',fields=['text']),
                         dict(id='roof',label='Painted roof',kind='map_region',map='beacon:town',rect=[6,6,1,1]),
                         dict(id='door',label='Moved exchange door',kind='fields',path='adventure.entrances/'+door['id'],fields=['at'])]:
                # Exercise the actual preservation form for all three kinds.
                form=view.protection_form();pump()
                for key,value in rule.items():
                    if key=='rect':value=', '.join(map(str,value))
                    if key=='fields':value=', '.join(value)
                    form.values[key].set(value)
                form.apply_button.invoke();pump()
                if form.window.winfo_exists():form.close();pump()
            assert len(rules(doc))==3
            # Make another pending text edit after protection registration.
            graph.selected='beacon:welcome';graph.edit();pump();props.event_text.insert('end',' Keep this sentence.');pump()
            view.window.lift();view.pages.select(view.session_page);pump()
            view.session_values['brief'].insert('1.0','Revise this mission while preserving the human changes.')
            view.session_values['scope'].delete('1.0','end');view.session_values['scope'].insert('1.0','adventure.maps/beacon:road\nadventure.encounters/beacon:roadblock')
            connection=view.start_session();pump()
            cli=subprocess.run([sys.executable,str(root/'tools/author.py'),'session','snapshot',str(connection),'--job-id','snapshot'],capture_output=True,text=True,timeout=15)
            assert cli.returncode==0,cli.stderr
            item=json.loads(cli.stdout);pump(lambda:job_done(connection,item['id']))
            result=session.wait(connection,item['id'],0);assert result['status']=='completed',result
            staged=ProjectDocument(Path(result['result']['snapshot']),doc.validator)
            assert next(e for e in staged.adventure['events'] if e['id']=='beacon:welcome')['text'].endswith('Keep this sentence.')
            manual=snapshot(scope);baseline=revision(manual);town=copy.deepcopy(manual.adventure['maps'][0]);notes=copy.deepcopy(editor_data(manual))
            enemy=copy.deepcopy(doc.adventure['encounters'][0]['enemies']);enemy[0]['at'][0]+=2
            ops=[dict(op='object.patch',collection='encounters',id='beacon:roadblock',changes={'enemies':enemy}),
                 dict(op='map.paint',map='beacon:road',tile='beacon:road',start=[7,17],end=[13,17],tool='Rectangle')]
            command=request('live-proposal',ops)
            command_file=folder/'live-proposal.json';command_file.write_bytes(encoded(command))
            cli=subprocess.run([sys.executable,str(root/'tools/author.py'),'session','propose',str(connection),'--request',str(command_file),'--job-id','proposal'],capture_output=True,text=True,timeout=15)
            assert cli.returncode==0,cli.stderr
            item=json.loads(cli.stdout);pump(lambda:job_done(connection,item['id']))
            result=session.wait(connection,item['id'],0);assert result['status']=='ready',result
            assert revision(snapshot(scope))==baseline,'Review modified the live document'
            view.open_saved(result['review']);view.pages.select(view.review_page);pump()
            assert view.record['conflicts']==[] and view.photos
            view.detail.select(2);pump();ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'editor-collaboration-maps.png')
            view.check();pump(lambda:not workspace.tasks.jobs)
            assert review.read(view.folder)['checks'][0]['revision']==view.record['result_revision']
            assert revision(snapshot(scope))==baseline
            view.apply();pump(lambda:not workspace.tasks.jobs)
            assert doc.adventure['maps'][0]==town and editor_data(doc)==notes
            assert doc.adventure['encounters'][0]['enemies']==enemy
            workspace.edit_history(False);pump();assert revision(doc)==baseline,'Undo discarded prior human drafts'
            workspace.edit_history(True);pump();doc.save();assert ProjectDocument(doc.root,doc.validator).adventure==doc.adventure
            print('PASS: Last Beacon GUI dialogue, roof paint and doorway drag; live snapshot, protected proposal, maps, application and one-step Undo/save.',flush=True)
            # Explicit partial acceptance must be revalidated before Apply.
            second=request('partial-proposal',ops);second['operations'][0]['changes']['enemies'][0]['at'][0]+=2
            second['operations'][1]['end']=[14,17]
            file=folder/'partial.json';file.write_bytes(encoded(second));view.load_file(file);pump(lambda:not workspace.tasks.jobs);view.refresh()
            view.groups.selection_clear(0,'end');view.groups.selection_set(0)
            try:view.apply();raise AssertionError('Unchecked partial selection applied')
            except AuthoringError:pass
            old_road=copy.deepcopy(doc.adventure['maps'][1]);view.recheck();pump(lambda:not workspace.tasks.jobs);view.refresh();view.apply();pump(lambda:not workspace.tasks.jobs)
            assert doc.adventure['maps'][1]==old_road
            accepted_folder=view.folder
            # A live session can never expand its allowed scope.
            denied=request('outside-scope',[dict(op='object.patch',collection='events',id='beacon:welcome',changes={'text':'Overwrite human work'})]);denied.pop('groups',None);denied['scope']=['*']
            item=session.submit(connection,'propose',request=denied,job_id='denied');pump(lambda:job_done(connection,item['id']))
            result=session.wait(connection,item['id'],0);assert result['status']=='failed',result
            assert result['result']['diagnostics'][0]['code']=='scope.denied'
            # An invalid pending GUI field stays visible and blocks a snapshot.
            app.window.lift();app.kind.set('Mechs');app.change_kind();pump();price=app.variables[('price',)][0];original_price=price.get();price.set('invalid-number')
            item=session.submit(connection,'snapshot',job_id='invalid-draft');pump(lambda:job_done(connection,item['id']))
            assert session.wait(connection,item['id'],0)['status']=='failed'
            assert price.get()=='invalid-number'
            price.set(original_price);app.form_dirty=False;app.refresh_list();pump()
            item=session.submit(connection,'snapshot',job_id='cancelled');session.cancel(connection,item['id']);pump(lambda:job_done(connection,item['id']))
            assert session.wait(connection,item['id'],0)['status']=='cancelled'
            # Hold a real worker at a known boundary while the user edits or
            # cancels. This exercises races without relying on machine speed.
            original_prepare=review.prepare
            for mode in ('stale','cancel-running'):
                entered=threading.Event();release=threading.Event()
                def held(*args,**kwargs):
                    entered.set()
                    if not release.wait(10):raise AssertionError('Worker gate timed out')
                    return original_prepare(*args,**kwargs)
                command=request(mode,[dict(op='object.patch',collection='maps',id='beacon:road',changes={'name':'Revised road'})])
                command.pop('groups',None)
                with patch.object(review,'prepare',side_effect=held):
                    try:
                        item=session.submit(connection,'propose',request=command,job_id=mode)
                        pump(entered.is_set)
                        if mode=='stale':
                            adventure=copy.deepcopy(doc.adventure);adventure['maps'][0]['name']='Human town title during generation';doc.replace_adventure(adventure)
                        else:session.cancel(connection,item['id']);workspace.authoring.poll()
                        preserved=revision(snapshot(scope));release.set();pump(lambda:job_done(connection,item['id']))
                    finally:release.set()
                result=session.wait(connection,item['id'],0)
                assert result['status']==('stale' if mode=='stale' else 'cancelled'),result
                assert revision(snapshot(scope))==preserved
            # Automation is opt-in and still observes scope and protections.
            view.policy.set('Apply within declared scope');connection=view.start_session()
            auto=request('automatic',[dict(op='object.patch',collection='maps',id='beacon:road',changes={'name':'Reviewed road'})]);auto.pop('groups',None)
            item=session.submit(connection,'propose',request=auto,job_id='automatic');pump(lambda:job_done(connection,item['id']))
            assert session.wait(connection,item['id'],0)['status']=='applied'
            assert doc.adventure['maps'][1]['name']=='Reviewed road'
            view.stop_session()
            view.session_values['scope'].delete('1.0','end');view.session_values['scope'].insert('1.0','*');connection=view.start_session()
            denied['expected_revision']=revision(snapshot(scope));denied['request_id']='protected-automatic'
            item=session.submit(connection,'propose',request=denied,job_id='protected-automatic');pump(lambda:job_done(connection,item['id']))
            assert session.wait(connection,item['id'],0)['status']=='conflicts'
            assert next(e for e in doc.adventure['events'] if e['id']=='beacon:welcome')['text'].endswith('Keep this sentence.')
            view.open_saved(accepted_folder)
            # Closing the tab retains the proposal and session; reopening shows
            # both. Stopping the session leaves ordinary Save and Play usable.
            saved=view.folder;view.window.destroy();pump();view=open_changes(app);pump();view.open_saved(saved)
            assert view.record['status']=='applied';assert session.info(connection)['connected']
            view.stop_session();pump();assert not session.info(connection)['connected']
            view.pages.select(view.review_page);view.detail.select(0);pump();ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'editor-collaboration-review.png')
            window.geometry('960x620+0+0');pump()
            view.summary_scroll.yview_moveto(1);pump()
            for widget in (view.apply_button,view.overrides):
                assert widget.winfo_ismapped() and widget.winfo_rooty()+widget.winfo_height()<=window.winfo_rooty()+window.winfo_height(),str(widget)
            ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'editor-collaboration-small.png')
            window.geometry('1440x980+0+0');pump()
            # Retain a runnable copy and actual review artifacts as local
            # verification evidence, outside the user's source project.
            doc.save()
            retained=work/'collaboration-lab';retained.mkdir(exist_ok=True)
            destination=retained/('game-'+str(time.time_ns()));destination.mkdir();doc.stage(destination)
            evidence={'project':str(destination),'dialogue':'beacon:welcome','roof':[6,6],
                      'door':doc.adventure['maps'][0]['entrances'][0],'revision':revision(doc),
                      'preserved_user_files':original}
            import shutil
            shutil.copytree(accepted_folder, destination.parent/(destination.name+'-review'))
            (retained/'latest.json').write_bytes(encoded(evidence))
            workspace.invoke('Play from start');pump(lambda:not workspace.play_session.preparing)
            assert workspace.play_session.process is not None
            workspace.play_session.stop();pump(lambda:workspace.play_session.process is None)
            # A project replacement stops its local connection immediately.
            connection=view.start_session();replacement=create_project(root/'examples/beacon-demo',folder/'other','other-game','Other game',doc.validator)
            app.set_document(replacement,check=False);pump();assert not session.info(connection)['connected']
            print('PASS: partial acceptance, scope refusal, invalid drafts, running edits/cancellation, opt-in application, protected conflicts, tab recovery, ordinary Play and project replacement.',flush=True)
            # Reopen the workspace with its retained review index. Unfinished
            # human edits use the existing recovery path, including Changes.
            workspace.authoring.stop();pump(lambda:not workspace.tasks.jobs)
            workspace.tasks.shutdown();window.destroy()
            window=tk.Tk();workspace=Workspace(window,doc.validator,folder/'settings');window.geometry('1440x980+0+0')
            window.report_callback_exception=lambda kind,error,tb:errors.append(error)
            app=workspace.app;app.set_document(ProjectDocument(doc.root,doc.validator));scope=app._editor_scope;pump()
            view=open_changes(app);view.open_saved(accepted_folder);pump()
            assert view.record['status']=='applied' and len(rules(app.document))==3
            assert not session.info(connection)['connected']
            # The protection form joins the normal draft recovery mechanism.
            form=view.protection_form();form.values['id'].set('unfinished');form.values['label'].set('Retain my unfinished rule');pump()
            workspace.recovery.write(scope);recovery=workspace.recovery.read(workspace.recovery.path(scope))
            form.window.destroy();pump();workspace.recovery.restore(scope,recovery);pump()
            recovered=next(d.view for d in scope.live() if isinstance(getattr(d.view,'values',None),dict) and d.view.values.get('id') and d.view.values['id'].get()=='unfinished')
            assert recovered.values['label'].get()=='Retain my unfinished rule'
            recovered.window.destroy();scope.document.save();workspace.recovery.clear(scope);pump()
            print('PASS: reopened editor retains proposals and protections, with old sessions stopped.',flush=True)
            # A library design has its own document/history and Save target,
            # even when its stable unit ID is also present in the open game.
            from unit_library import UnitLibrary
            from editor_tasks import save
            library=UnitLibrary(folder/'library',doc.validator);unit=app.document.content['mechs'][0]['id']
            bundle=library.export_unit(app.document,unit,'Mechs');project_before=revision(app.document)
            app.settings['library-root']=str(library.root);app.open_library();pump(lambda:not workspace.tasks.jobs)
            browser=app.unit_library_window;browser.refresh(bundle['entry_id']);editor=browser.edit();pump()
            library_scope=editor._editor_scope
            connection=workspace.authoring.start(library_scope,allowed_scope=['content.mechs/'+unit],policy='apply_within_scope')
            assert session.info(connection)['scope_kind']=='library'
            new_price=editor.document.content['mechs'][0]['price']+1
            library_request=dict(api_version=1,request_id='library-price',project_id=editor.document.manifest['package_id'],
                expected_revision=revision(snapshot(library_scope)),label='Adjust library price',scope=['content.mechs/'+unit],
                operations=[dict(op='object.patch',collection='mechs',id=unit,changes={'price':new_price})])
            item=session.submit(connection,'propose',request=library_request,job_id='library');pump(lambda:job_done(connection,item['id']))
            assert session.wait(connection,item['id'],0)['status']=='applied'
            save(workspace,library_scope);pump(lambda:not workspace.tasks.jobs)
            assert next(b for b in library.entries() if b['entry_id']==bundle['entry_id'])['content']['mechs'][0]['price']==new_price
            assert revision(app.document)==project_before
            workspace.close_scope(library_scope);pump();assert not session.info(connection)['connected']
            print('PASS: explicit Unit Library authoring and Save leave the game with the same unit ID unchanged.',flush=True)
        finally:
            workspace.authoring.stop();workspace.tasks.shutdown()
            if workspace.play_session.process and workspace.play_session.process.poll() is None:
                workspace.play_session.process.terminate();workspace.play_session.process.wait(timeout=5)
            window.destroy()
            sys.unraisablehook=previous_hook
    assert original=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'examples/battletech-demo').iterdir() if p.is_file()}
