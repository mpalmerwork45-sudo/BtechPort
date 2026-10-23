"""Two planets: protect a human edit, inspect proposals, narrow, Undo and save."""
def run(env,work):
    import copy,json,tempfile,time,tkinter as tk
    from pathlib import Path
    from PIL import ImageGrab
    from world_review_demo import create,request
    from authoring_protection import edit_rule,rules
    from authoring_service import revision
    from editor_model import encoded,ProjectDocument
    from editor_workspace import Workspace
    from editor_changes import open_changes
    from editor_tasks import snapshot
    from world_editing import get_world
    root=Path(__file__).resolve().parents[1];tool=root/'build/btp-project'
    with tempfile.TemporaryDirectory(prefix='world-review-gui-',dir=work) as tmp:
        folder=Path(tmp);doc=create(folder/'game',tool);edit_rule(doc,remove='painted-pond');doc.save()
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
            app=workspace.app;app.set_document(doc);scope=app._editor_scope
            app.settings['player']=str(root/'build/btech-port')
            maps=workspace.map_view();maps.edit_landscape();world=maps.world_editor;pump()
            world.tool.set('Select');world.canvas.xview_moveto(0);world.canvas.yview_moveto(0);pump()
            def point(x,y):return dict(x=round(x*4-world.canvas.canvasx(0)),y=round(y*4-world.canvas.canvasy(0)))
            world.canvas.event_generate('<Button-1>',**point(44.5,12.5))
            world.canvas.event_generate('<B1-Motion>',**point(45.5,13.5))
            world.canvas.event_generate('<ButtonRelease-1>',**point(45.5,13.5));pump()
            assert world.selection_rect==(44,12,45,13)
            form=world.protect_selection();pump()
            assert form.values['world'].get()=='survey:aster' and form.values['rect'].get()=='44, 12, 2, 2'
            form.values['id'].set('painted-pond');form.values['label'].set('Hand-painted pond');form.apply_button.invoke();pump()
            if form.window.winfo_exists():form.close();pump()
            assert rules(doc)[0]['kind']=='world_region'
            workspace.invoke('Save project');pump(lambda:not workspace.tasks.jobs)
            baseline=revision(snapshot(scope));original=copy.deepcopy(doc.adventure)
            world.refresh();assert world.canvas.find_withtag('protected-region')
            view=open_changes(app);file=folder/'proposal.json';file.write_bytes(encoded(request(snapshot(scope))))
            view.pages.select(view.review_page);view.load_file(file);pump(lambda:not workspace.tasks.jobs)
            assert view.record['status']=='conflicts',view.record
            assert revision(snapshot(scope))==baseline
            view.detail.select(view.worlds_page);pump();pane=view.world_review
            assert pane.change['id']=='survey:aster' and len(pane.photos)==2
            assert all(c.find_withtag('protections') for c in pane.canvases.values())
            pane.listing.selection_set('0');pump();assert pane.selected()['kind']=='town'
            pane.detail();pump(lambda:not workspace.tasks.jobs);assert pane.mode=='detail' and len(pane.photos)==2
            assert all(a['artifact']['pixels_per_tile']==16 for a in pane.items)
            ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'world-review-town.png')
            assert pane.canvases['after'].winfo_height()>60,'Review canvases must remain visible at 1024x740.'
            pane.controls['after'].combo.focus_force();pump();pane.controls['after'].combo.set('150%');pane.controls['after'].combo.event_generate('<Return>');pump()
            assert pane.scales['after'].get()=='3'
            pane.canvases['after'].event_generate('<Control-Button-5>',x=50,y=50);pump();assert pane.scales['after'].get()=='2'
            pane.open_town();pump();assert maps.scene()['id']=='survey:port'
            pane.open_location();pump();assert world.world_id=='survey:aster' and world.problem_location==('survey:aster',70,24)
            # Old completions must not repaint the newly selected planet.
            view.window.lift();pane.detail();pane.choice.current(1);pane.choose();pump(lambda:not workspace.tasks.jobs)
            assert pane.change['id']=='survey:boreal' and pane.mode=='overview'
            pane.listing.selection_set('0');pump();pane.detail();pump(lambda:not workspace.tasks.jobs)
            pane.open_location();pump();assert world.world_id=='survey:boreal'
            view.window.lift();view.detail.select(view.worlds_page);pump()
            ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'world-review-terrain.png')
            view.detail.select(0);view.groups.selection_clear(0,'end');view.groups.selection_set(0,1)
            view.recheck();pump(lambda:not workspace.tasks.jobs);assert view.record['status']=='ready',view.record
            assert not view.record['conflicts'] and not view.overrides.curselection()
            view.apply();pump(lambda:not workspace.tasks.jobs)
            assert get_world(doc.adventure,'survey:aster')['patches']==get_world(original,'survey:aster')['patches']
            assert doc.adventure['maps'][1]['origin']==[62,16]
            accepted=copy.deepcopy(doc.adventure)
            workspace.edit_history(False);pump();assert doc.adventure==original
            workspace.edit_history(True);pump();assert doc.adventure==accepted
            workspace.invoke('Save project');pump(lambda:not workspace.tasks.jobs)
            reopened=ProjectDocument(doc.root,tool);assert reopened.adventure==accepted and rules(reopened)==rules(doc)
            assert not doc.dirty
            # Play an ordinary SDL snapshot after the accepted edits. Native
            # cross-planet travel assertions live in world_review_demo.py.
            workspace.play_session.start(scope);pump(lambda:workspace.play_session.process is not None)
            assert workspace.play_session.process.poll() is None
            workspace.play_session.stop();pump(lambda:workspace.play_session.process is None)
            (work/'world-review-gui.json').write_bytes(encoded(dict(status='passed',checks=[
                'mouse selection and world protection form','1024x740 layout','paired overview and town crop',
                'editable zoom and Ctrl-wheel','town and world navigation','stale worker discarded','Boreal terrain crop',
                'narrow groups without exception','one Undo/Redo','Save/reopen','ordinary SDL Play'])))
            print('PASS: protected pond, paired planet/town reviews, zoom, navigation, narrowed acceptance, Undo/Redo, Save/reopen and SDL Play.',flush=True)
        finally:
            workspace.play_session.shutdown();workspace.tasks.shutdown();window.destroy()
