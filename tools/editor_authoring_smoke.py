"""Human paint, command-file application, conflict refusal and normal Play."""
def run(env,work):
    import copy,json,os,tempfile,time
    from pathlib import Path
    import tkinter as tk
    from unittest.mock import patch
    from PIL import ImageGrab
    from editor_model import create_project,ProjectDocument,encoded
    from editor_workspace import Workspace
    from editor_authoring import apply_file,export_summary
    from authoring_service import revision
    from event_editing import editor_data
    from world_editing import token
    from adventure_editing import composite

    root=Path(__file__).resolve().parents[1];work=Path(work);os.environ['DISPLAY']=env['DISPLAY']
    with tempfile.TemporaryDirectory(prefix='authoring-gui-',dir=work) as temp:
        folder=Path(temp);doc=create_project(root/'examples/relay-contract',folder/'game','author-gui','Authoring GUI',root/'build/btp-project')
        window=tk.Tk();errors=[];workspace=Workspace(window,doc.validator,folder/'settings');window.geometry('1440x930+0+0')
        window.report_callback_exception=lambda kind,error,tb:errors.append(error)
        def pump(condition=lambda:True,timeout=15):
            end=time.monotonic()+timeout
            while True:
                window.update()
                if errors:raise errors.pop(0)
                if condition():return
                if time.monotonic()>end:raise AssertionError('Timed out: '+workspace.status.get())
                time.sleep(.01)
        def batch(identity,text):
            return dict(api_version=1,request_id=identity,project_id=doc.manifest['package_id'],expected_revision=revision(doc),
                label='Revise mission briefing',scope=['adventure.events/relay:briefing'],
                operations=[dict(op='object.patch',collection='events',id='relay:briefing',changes={'text':text})])
        try:
            app=workspace.app;app.set_document(doc);app.edit_adventure();pump();maps=app.map_editor
            maps.zoom_control.set(24);maps.canvas.xview_moveto(0);maps.canvas.yview_moveto(0);pump()
            # Paint through the actual mouse event path, including construction
            # detail metadata. The green roof pixel is intentional test evidence.
            grass=next(t for t in doc.adventure['tiles'] if t['id']=='frontier:grass')
            before=copy.deepcopy(doc.adventure)
            # Use the visible tile-selection variable used by the map toolbar.
            maps.brush.selection_set(str(doc.adventure['tiles'].index(grass)));maps.select_brush()
            maps.tool.set('Paint')
            x,y=12.5*24-maps.canvas.canvasx(0),4.5*24-maps.canvas.canvasy(0)
            maps.canvas.event_generate('<Button-1>',x=round(x),y=round(y));pump()
            maps.canvas.event_generate('<ButtonRelease-1>',x=round(x),y=round(y));pump()
            assert doc.adventure!=before,'GUI paint did not reach the map'
            manual=copy.deepcopy(doc.adventure['maps']);metadata=copy.deepcopy(editor_data(doc));doc.save()
            assert composite(doc.adventure['maps'][0])[4][12]==token(grass)
            summary=folder/'summary.json';export_summary(workspace,summary);pump(lambda:not workspace.tasks.jobs)
            assert json.loads(summary.read_bytes())['revision']==revision(doc)
            request=folder/'commands.json';request.write_bytes(encoded(batch('gui-batch-1','A revised briefing; the hand-painted roof stays intact.')))
            # Invoke the real menu action, with only its file chooser supplied.
            with patch('editor_authoring.filedialog.askopenfilename',return_value=str(request)):
                workspace.invoke('Apply authoring command file')
            pump(lambda:not workspace.tasks.jobs)
            assert not workspace.problems,workspace.problems
            assert doc.adventure['maps']==manual and editor_data(doc)==metadata
            updated=next(e for e in doc.adventure['events'] if e['id']=='relay:briefing')['text']
            assert updated.startswith('A revised briefing')
            workspace.edit_history(False);pump()
            assert doc.adventure['maps']==manual and not next(e for e in doc.adventure['events'] if e['id']=='relay:briefing')['text'].startswith('A revised briefing')
            workspace.edit_history(True);pump();assert doc.adventure['maps']==manual
            doc.save();reopened=ProjectDocument(doc.root,doc.validator)
            assert reopened.adventure==doc.adventure and reopened.art==doc.art
            # A command prepared before a second human edit is refused visibly.
            stale=batch('gui-stale','This must not replace newer work.')
            a=copy.deepcopy(doc.adventure);a['maps'][0]['name']='Human-named depot';maps.commit(a);request.write_bytes(encoded(stale))
            apply_file(workspace,request);pump(lambda:not workspace.tasks.jobs)
            assert any('changed since' in p['message'] for p in workspace.problems),workspace.problems
            assert next(e for e in doc.adventure['events'] if e['id']=='relay:briefing')['text']==updated
            app.settings.update({'player':str(root/'build/btech-port'),'data':str(root/'Original DOS'),
                'dialogue-data':str(root/'work/talk-data.bin'),'combat-data':str(root/'work/combat-data.bin'),'world-data':str(root/'work/world-data.bin')})
            workspace.invoke('Content catalogue');pump()
            from editor_workspace import existing_view
            catalogue=existing_view(app,'catalogue');assert catalogue is not None
            catalogue.query.set('kind:mech weapon:lrm');catalogue.refresh();pump()
            assert any(r['name']=='Trebuchet TBT-5N' for r in catalogue.records.values())
            assert catalogue.photos,'Catalogue did not decode the selected unit sprite'
            catalogue.query.set('kind:tile id:frontier:grass');catalogue.refresh();pump()
            catalogue.listing.selection_set('project/frontier:grass');pump()
            form=catalogue.edit();pump();form.values['tags'].set('grassland, human-edited')
            for widget in form.footer.winfo_children():
                if widget.winfo_class()=='TButton' and widget.cget('text')=='Apply':widget.invoke();break
            pump();assert 'human-edited' in editor_data(doc)['catalogue']['frontier:grass']['tags']
            catalogue.query.set('tag:human-edited');catalogue.refresh();pump()
            assert list(catalogue.records)==['project/frontier:grass']
            catalogue.use();pump();assert maps.tool.get()=='Paint'
            # Search the normal tile picker through the same catalogue tags.
            from tile_browser import TileBrowser
            picker=TileBrowser(maps,selected='frontier:grass');picker.query.set('tag:human-edited');picker.refresh();pump()
            assert picker.keys==['frontier:grass'];picker.close();pump()
            print('PASS: shared catalogue numeric/weapon search, original sprite preview, metadata form and tagged tile picker.',flush=True)
            workspace.invoke('Play from start');pump(lambda:not workspace.play_session.preparing)
            process=workspace.play_session.process;assert process is not None
            deadline=time.monotonic()+.3;pump(lambda:time.monotonic()>deadline)
            assert process.poll() is None,(workspace.play_session.folder/'player.log').read_text()
            workspace.play_session.stop();pump(lambda:workspace.play_session.process is None)
            app.edit_adventure();maps.window.lift();pump()
            ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'editor-authoring.png')
            print('PASS: real GUI paint, exported revision, command-file application, one-step Undo/Redo, stale refusal, save/reopen and normal Play.',flush=True)
        finally:
            workspace.tasks.shutdown()
            process=workspace.play_session.process
            if process and process.poll() is None:process.terminate();process.wait(timeout=5)
            window.destroy()
