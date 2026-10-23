"""Native route failures navigate to the source town or planet in the GUI."""
def run(env,work):
    import copy,json,tempfile,time,tkinter as tk
    from pathlib import Path
    from PIL import ImageGrab
    from world_route_demo import create
    from authoring_scenarios import run as scenario
    from editor_model import encoded,ProjectDocument
    from editor_workspace import Workspace
    from editor_tasks import snapshot
    root=Path(__file__).resolve().parents[1];tool=root/'build/btp-project'
    with tempfile.TemporaryDirectory(prefix='world-route-gui-',dir=work) as tmp:
        folder=Path(tmp);doc=create(folder/'game',tool)
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
        def open_problem(problem):
            index=workspace.problems.index(problem);workspace.problem_list.selection_set(str(index))
            workspace.problem_list.see(str(index));workspace.problem_list.focus_set();pump()
            workspace.problem_list.event_generate('<Return>');pump()
        try:
            app=workspace.app;app.set_document(doc);scope=app._editor_scope;maps=workspace.map_view();pump()
            a=copy.deepcopy(doc.adventure);town=a['maps'][1]
            for y in range(6,15):
                for x in range(1,10):
                    if x in (1,9) or y in (6,14):town['rows'][y][x]='beacon:wall'
            maps.commit(a);workspace.invoke('Check mission');pump(lambda:not workspace.tasks.jobs)
            problem=next(p for p in workspace.problems if p.get('object_id')=='survey:shuttle')
            open_problem(problem)
            assert maps.scene()['id']=='survey:port' and maps.cursor==(10,20)
            assert maps.selected_marker is not None
            ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'world-routes-town.png')
            print('PASS: native world connectivity finding opens its source town and selects the correct entrance.',flush=True)
            workspace.edit_history(False);pump();workspace.invoke('Check mission');pump(lambda:not workspace.tasks.jobs)
            assert problem.get('resolved')

            failed=scenario(snapshot(scope),dict(format='btp-author-scenario-v1',steps=[dict(op='walk',world='survey:aster',at=[180,80],max_positions=1)]),folder/'budget',root/'build/btp-author-playtest')
            assert failed['diagnostics'][0]['code']=='route.budget'
            problem=dict(failed['diagnostics'][0],owner=app,field=None,category='route-test')
            scope.problems.append(problem);workspace.problem(scope,problem);open_problem(problem)
            world=maps.world_editor
            assert world.world_id=='survey:aster' and world.problem_location==('survey:aster',90.,40.)
            assert len(world.canvas.find_withtag('problem-location'))==3
            world.zoom_control.set(8);pump();assert len(world.canvas.find_withtag('problem-location'))==3
            ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'world-routes-planet.png')
            # The diagnostic marker never becomes a terrain edit, and source
            # city IDs survive saving/reopening the project.
            workspace.invoke('Save project');pump(lambda:not workspace.tasks.jobs)
            assert ProjectDocument(doc.root,tool).adventure==doc.adventure
            assert not doc.dirty
            (work/'world-routes-gui.json').write_bytes(encoded(dict(status='passed',checks=[
                'native Check mission','source-town entrance navigation','Undo repair and recheck',
                'world route diagnostic','half-tile coordinate conversion','marker survives zoom','Save/reopen'])))
            print('PASS: route error opens the right planet, highlights movement coordinates, survives zoom and leaves terrain unchanged.',flush=True)
        finally:
            workspace.tasks.shutdown();window.destroy()
