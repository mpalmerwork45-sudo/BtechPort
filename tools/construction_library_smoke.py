"""Export, reopen, import and draw shared constructions through the real GUI."""
def run(env,work):
    import copy
    import tempfile
    import time
    import tkinter as tk
    from pathlib import Path
    from PIL import ImageGrab
    from editor_model import create_project,ProjectDocument
    from editor_workspace import Workspace
    from construction_editing import new_profile,compile_rows
    from construction_library import ConstructionLibrary
    from tile_editing import metadata
    from map_patterns import save_pattern
    from map_construction import objects
    from world_editing import upgrade

    root=Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix='construction-library-gui-',dir=work) as temporary:
        folder=Path(temporary);tool=root/'build/btp-project'
        source=create_project(root/'examples/beacon-demo',folder/'source','shared-source','Construction source',tool)
        designs={kind:new_profile(source,kind) for kind in ('Building','Wall','Road')}
        style=next(p for p in metadata(source)['construction_sets'] if p['id']==designs['Building'])
        designs['Pattern']=save_pattern(source,compile_rows(style),'Saved courtyard block')
        source.save();before=source.files()
        target=create_project(root/'examples/beacon-demo',folder/'target','shared-target','Destination game',tool)
        a=copy.deepcopy(target.adventure);upgrade(a);ground=next(t['id'] for t in a['tiles'] if t['terrain']=='clear')
        a['maps'][0].update(overlays=[],entrances=[],rows=[[ground]*32 for _ in range(24)]);a['start']['at']=[60,44]
        for event in a['events']:
            if event['op']=='transfer' and event['map']==a['maps'][0]['id']:event['at']=[60,44]
        target.replace_adventure(a);target.save()
        window=tk.Tk();workspace=Workspace(window,tool,folder/'settings');window.geometry('1440x960+0+0')
        errors=[];window.report_callback_exception=lambda kind,error,tb:errors.append(error)
        def pump(condition=lambda:True,timeout=20):
            end=time.monotonic()+timeout
            while True:
                window.update()
                if errors:raise errors.pop(0)
                if condition():return
                if time.monotonic()>end:raise AssertionError('Timed out: '+workspace.status.get())
                time.sleep(.01)
        def settled():
            pump(lambda:not workspace.tasks.jobs)
            problems=[p['message'] for p in workspace.problems if not p.get('resolved')]
            assert not problems,problems
        try:
            app=workspace.app;app.settings['construction-library-root']=str(folder/'shared-library');app.set_document(source)
            app.edit_adventure();maps=app.map_editor;pump()
            for kind,identity in designs.items():
                if kind=='Pattern':editor=maps.patterns();editor.selected=identity;editor.refresh()
                else:editor=maps.construction(kind);editor.current=identity;editor.refresh()
                f=editor.save_library();pump();f.apply_button.invoke();settled()
                assert not f.window.winfo_exists(),f.error.get()
            library=ConstructionLibrary(folder/'shared-library',tool);assert len(library.entries())==4
            assert source.files()==before
            browser=maps.construction_library();settled()
            browser.kind.set('Building');browser.refresh();settled()
            assert len(browser.listing.get_children())==1 and browser.preview
            ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'construction-library-browser.png')
            browser.window.destroy();pump();browser=maps.construction_library();settled()
            assert len(browser.bundles)==4
            print('PASS: real designer and Pattern Library exports preserve the source; shared entries and previews survive closing/reopening.',flush=True)

            app.set_document(target,check=False);app.edit_adventure();maps=app.map_editor
            browser=maps.construction_library();settled()
            imported={}
            for kind in ('Building','Wall','Road','Pattern'):
                browser.window.lift();browser.kind.set(kind);browser.refresh();settled()
                previous=target.files();count=len(target.undo_stack)
                browser.buttons['Import and edit'].invoke();settled()
                assert len(target.undo_stack)==count+1
                collection='map_patterns' if kind=='Pattern' else 'construction_sets'
                imported[kind]=metadata(target)[collection][-1]['id']
                assert workspace.current_view().key[1]==('patterns' if kind=='Pattern' else 'construction')
                workspace.edit_history(False);pump();assert target.files()==previous
                workspace.edit_history(True);pump()
            # Draw a new footprint using the imported rules, not the demo block.
            editor=maps.construction('Building');editor.current=imported['Building'];editor.refresh();editor.use();pump()
            maps.zoom_control.set(16);maps.canvas.xview_moveto(0);maps.canvas.yview_moveto(0);pump()
            maps.construction_tools.shape.set('Courtyard');maps.construction_tools.stories.set('3')
            def event(sequence,x,y):
                maps.canvas.event_generate(sequence,x=round((x+.5)*16-maps.canvas.canvasx(0)),y=round((y+.5)*16-maps.canvas.canvasy(0)));pump()
            event('<Button-1>',3,3);event('<B1-Motion>',8,8);event('<ButtonRelease-1>',8,8)
            building=objects(target,maps.scene()['id'])[0]
            assert building['style']==imported['Building'] and all(c[2]==3 for c in building['cells'])
            assert len(building['cells'])<36
            target.validate();target.save()
            assert ProjectDocument(target.root,tool).files()==target.files()
            ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'construction-library-drawn.png')
            print('PASS: all four library types import into another game with one-step Undo/Redo; imported building rules draw a new three-storey courtyard and save/reopen.',flush=True)

            # Updating is explicit, uses the library revision, and does not
            # push changes into the first game which supplied the design.
            browser=maps.construction_library();browser.kind.set('Building');browser.refresh();settled()
            old=browser.current();f=browser.export_dialog(imported['Building']);pump()
            f.values['name'].set('Revised shared courtyard');f.values['save_as'].set('Update selected library entry')
            f.apply_button.invoke();settled()
            updated=next(b for b in library.entries() if b['entry_id']==old['entry_id'])
            assert updated['revision']==2 and updated['name']=='Revised shared courtyard'
            assert ProjectDocument(source.root,tool).files()==before
            f=browser.export_dialog(imported['Building']);pump();f.values['name'].set('An unfinished library export')
            workspace.recovery.write(app._editor_scope)
            record=workspace.recovery.read(workspace.recovery.path(app._editor_scope))
            f.window.destroy();pump();workspace.recovery.restore(app._editor_scope,record);settled()
            f=next(d.view for d in app._editor_scope.live() if isinstance(getattr(d.view,'values',None),dict)
                   and d.view.values.get('name') and d.view.values['name'].get()=='An unfinished library export')
            assert f.window.winfo_viewable() and window.grab_current() is f.window
            f.window.destroy();pump();browser.window.lift();pump()
            assert next(b for b in library.entries() if b['entry_id']==old['entry_id'])['revision']==2
            window.geometry('960x620+0+0');pump()
            assert browser.buttons['Import into project'].winfo_ismapped()
            assert browser.canvas.winfo_height()>=72
            ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'construction-library-small.png')
            print('PASS: explicit library update retains the source; recovery preserves an unfinished export without writing it; controls remain visible at 960x620.',flush=True)
        finally:
            workspace.play_session.shutdown();workspace.tasks.shutdown();workspace.closing=True
            window.destroy()
