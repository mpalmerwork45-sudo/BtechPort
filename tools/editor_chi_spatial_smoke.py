"""Real GUI test of imported maps through the regular authoring tools."""
def run(env,work):
    import copy,json,tempfile,time,tkinter as tk
    from pathlib import Path
    from PIL import ImageGrab
    from chi_import import import_campaigns
    from chi_spatial import data,change,find,move_town
    from editor_model import ProjectDocument,encoded
    from editor_workspace import Workspace
    from chi_resource_editor import open_resources
    root=Path(__file__).resolve().parents[1];tool=root/'build/btp-project'
    with tempfile.TemporaryDirectory(prefix='chi-spatial-gui-',dir=work) as temporary:
        folder=Path(temporary);result=import_campaigns(root/'Original DOS',folder/'pair',validator=tool)
        document=ProjectDocument(Path(result['projects'][0]['path']),tool)
        window=tk.Tk();workspace=Workspace(window,tool,folder/'state');app=workspace.app;app.set_document(document)
        app.settings.update(player=str(root/'build/btech-port'))
        errors=[];window.report_callback_exception=lambda kind,error,tb:errors.append(error)
        window.geometry('1024x740+0+0')
        def pump(condition=lambda:True,timeout=30):
            deadline=time.monotonic()+timeout
            while True:
                window.update()
                if errors:raise errors.pop(0)
                if condition():return
                if time.monotonic()>deadline:raise AssertionError('Timed out CHI map GUI journey: '+workspace.status.get())
                time.sleep(.01)
        try:
            app.edit_adventure();maps=app.map_editor;pump()
            assert len(maps.adventure['maps'])==15 and len(maps.adventure['tiles'])==1000
            assert set(maps.graphics)>={'chi:land','chi:destroyed','chi:cache','chi:maproom'}
            maps.zoom.set('16');maps.draw();maps.canvas.xview_moveto(0);maps.canvas.yview_moveto(0);pump()
            old=copy.deepcopy(document.adventure);maps.brush.selection_set(85);maps.select_brush();maps.tool.set('Paint')
            maps.canvas.event_generate('<Button-1>',x=8*16+8,y=8*16+8);maps.canvas.event_generate('<ButtonRelease-1>');pump()
            assert data(document)['maps'][0]['rows'][8][8]=='chi:land-85'
            workspace.invoke('Undo');pump();assert document.adventure==old
            workspace.invoke('Redo');pump();assert document.adventure!=old
            world=maps.edit_landscape();pump(lambda:not workspace.tasks.jobs);assert world.image is not None
            change(document,lambda v:move_town(v,'chi:map-03',832,512));maps.refresh();pump(lambda:not workspace.tasks.jobs)
            assert data(document)['maps'][2]['origin']==[832,512]
            world.listing.selection_set('chi:jigsaw-15');jigsaw=world.edit_jigsaw();pump()
            jigsaw.tile.set('chi:land-67');jigsaw.paint(type('Event',(),dict(x=20,y=20))(),True);jigsaw.finish();jigsaw.apply();pump(lambda:not workspace.tasks.jobs)
            assert data(document)['world']['jigsaws'][15]['rows'][0][0]=='chi:land-67'
            ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'chi-world-editor.png')
            resource=open_resources(maps);pump(lambda:resource.decoded is not None and not workspace.tasks.jobs)
            sprite=next(str(i) for i,r in enumerate(resource.rows) if r['kind']=='sprite');resource.table.selection_set(sprite);resource.select();pump(lambda:resource.decoded is not None and not workspace.tasks.jobs)
            pixel=resource.edit();pump();assert pixel.image['kind']=='sprite' and len(pixel.image['frames'])==16
            pixel.image['frames'][0][0]='ffffffff'+pixel.image['frames'][0][0][8:];pixel.apply();pump()
            assert document.art['images']
            ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'chi-resource-editor.png')
            workspace.invoke('Save project');pump(lambda:not workspace.tasks.jobs)
            assert not document.dirty,workspace.status.get()
            reopened=ProjectDocument(document.root,tool);assert reopened.files()==document.files()
            app.settings['data']=str(folder/'missing-original');workspace.play_session.start(app._editor_scope);pump(lambda:not workspace.play_session.preparing)
            assert workspace.play_session.process and workspace.play_session.process.poll() is None,workspace.status.get()
            workspace.play_session.stop();pump(lambda:workspace.play_session.process is None)
            (work/'chi-spatial-gui.json').write_bytes(encoded(dict(status='passed',checks=['normal map painting','all 15 maps and four banks','Undo/Redo','moved town overview','normal jigsaw drawing','native sprite copy/edit','shared Save/reopen','Play without external resources'])))
            print('PASS: native maps, world, jigsaws, sprite editing, Undo/Save/reopen and native Play.',flush=True)
        finally:
            workspace.play_session.shutdown();workspace.tasks.shutdown();window.destroy()
