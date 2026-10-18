"""Draw real footprints with Tk pointer events, then reopen and reshape them."""
def run(env,work):
    import copy,os,tempfile,subprocess,json
    from pathlib import Path
    import tkinter as tk
    from tkinter import messagebox
    from unittest.mock import patch
    from PIL import ImageGrab
    from editor_model import create_project,ProjectDocument
    from editor_workspace import Workspace
    from world_editing import upgrade
    from map_construction import objects
    from adventure_editing import composite
    from editor_recovery import identity as scope_identity
    root=Path(__file__).resolve().parents[1];work=Path(work);os.environ['DISPLAY']=env['DISPLAY']
    with tempfile.TemporaryDirectory(prefix='drawn-construction-',dir=work) as directory:
        directory=Path(directory);tool=root/'build/btp-project'
        doc=create_project(root/'examples/beacon-demo',directory/'game','drawn-ui','Drawn construction',tool)
        a=copy.deepcopy(doc.adventure);upgrade(a);ground=next(t['id'] for t in a['tiles'] if t['terrain']=='clear')
        a['maps'][0].update(overlays=[],entrances=[],rows=[[ground]*32 for _ in range(24)])
        a['start']['at']=[60,44]
        for event in a['events']:
            if event['op']=='transfer' and event['map']==a['maps'][0]['id']:event['at']=[60,44]
        doc.replace_adventure(a);doc.save()
        window=tk.Tk();workspace=None;errors=[];clock=10000
        def pump():
            window.update()
            if errors:raise errors.pop(0)
        def fail(title,message,**kwargs):raise AssertionError(title+': '+message)
        def gesture(start,end,button=1,release=True):
            nonlocal clock
            size=int(maps.zoom.get());canvas=maps.canvas
            canvas.xview_moveto(max(0,((start[0]+end[0]+1)*size/2-canvas.winfo_width()/2)/(32*size)))
            canvas.yview_moveto(max(0,((start[1]+end[1]+1)*size/2-canvas.winfo_height()/2)/(24*size)));pump()
            def emit(sequence,cell):
                nonlocal clock
                x=round(cell[0]*size+size//2-canvas.canvasx(0));y=round(cell[1]*size+size//2-canvas.canvasy(0))
                assert 0<=x<canvas.winfo_width() and 0<=y<canvas.winfo_height(),(cell,x,y,canvas.winfo_width(),canvas.winfo_height())
                clock+=1000;canvas.event_generate(sequence,x=x,y=y,time=clock);pump()
            emit(f'<ButtonPress-{button}>',start);emit(f'<B{button}-Motion>',end)
            if release:emit(f'<ButtonRelease-{button}>',end)
        def snapshot(name):pump();ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/('drawn-construction-'+name+'.png'))
        with patch.object(messagebox,'showerror',fail):
            try:
                workspace=Workspace(window,tool,directory/'settings');window.geometry('1000x740+0+0')
                window.report_callback_exception=lambda kind,error,tb:errors.append(error)
                app=workspace.app;app.set_document(doc);app.edit_adventure();maps=app.map_editor;maps.zoom.set('16');maps.draw();pump()
                construct=maps.construction_tools;construct.edit_button.invoke();pump();maps.window.lift();construct.place_button.invoke();pump()
                construct.shape.set('Rectangle');construct.stories.set('1')
                old=doc.files();gesture((2,2),(7,7),release=False)
                assert doc.files()==old and construct.stroke is not None;snapshot('box-preview')
                maps.finish_stroke();pump();box=construct.current_object();assert len(box['cells'])==36
                assert len(maps.scene()['overlays'])==1 and set(h for _,_,h in box['cells'])=={1}
                after=doc.files();workspace.edit_history(False);pump();assert doc.files()==old
                workspace.edit_history(True);pump();assert doc.files()==after
                construct.object_choice.current(1);construct.object_choice.event_generate('<<ComboboxSelected>>');pump()
                gesture((1,4),(9,5));assert len(construct.current_object()['cells'])==42
                gesture((4,4),(5,5),button=3)
                assert (4,4) not in {(x,y) for x,y,h in construct.current_object()['cells']}
                assert composite(maps.scene())[5][5]==ground
                construct.stories.set('3');gesture((2,2),(3,3));box=copy.deepcopy(construct.current_object())
                assert {h for x,y,h in box['cells']}=={1,3};snapshot('cross-and-heights')
                construct.new_button.invoke();construct.shape.set('Courtyard');construct.stories.set('3');construct.width.set('2');pump()
                gesture((12,2),(24,16));courtyard=construct.current_object()
                assert len(maps.scene()['overlays'])==2 and courtyard['id']!=box['id']
                assert composite(maps.scene())[11][20]==ground;doc.validate();snapshot('three-story-courtyard')
                construct.kind_choice.set('Wall');construct.kind_choice.event_generate('<<ComboboxSelected>>');construct.edit_button.invoke();pump()
                maps.window.lift();construct.place_button.invoke();construct.stories.set('3');construct.width.set('1');construct.shape.set('Line');pump()
                gesture((2,18),(8,18));gesture((8,18),(8,20))
                assert len(maps.scene()['overlays'])==3 and len(construct.current_object()['cells'])==9
                doc.validate();app.save();pump();snapshot('wall')
                original_objects=copy.deepcopy(objects(doc,maps.scene()['id']))
                # Preserve an unfinished map footprint in the same recovery
                # mechanism as tile strokes and designer footprint edits.
                gesture((8,20),(10,20),release=False)
                workspace.recovery.write(app._editor_scope);record=workspace.recovery.read(workspace.recovery.path(app._editor_scope))
                print('PASS: direct map rectangle, cross extension, right-drag courtyard, mixed heights, three-story courtyard and connected wall; preview has no committed side effects and strokes undo atomically.',flush=True)
            finally:
                if workspace:workspace.closing=True
                window.destroy()
            window=tk.Tk();workspace=Workspace(window,tool,directory/'settings')
            window.report_callback_exception=lambda kind,error,tb:errors.append(error)
            try:
                app=workspace.app;app.set_document(ProjectDocument(doc.root,tool));workspace.recovery.offered.add(scope_identity(app._editor_scope));pump()
                app.edit_adventure();maps=app.map_editor;maps.zoom.set('16');maps.draw();pump()
                assert objects(app.document,maps.scene()['id'])==original_objects
                workspace.recovery.restore(app._editor_scope,record);pump();construct=maps.construction_tools
                assert construct.stroke is not None and maps.tool.get()=='Wall'
                maps.finish_stroke();pump();assert len(construct.current_object()['cells'])==11
                construct.kind_choice.set('Building');construct.kind_choice.event_generate('<<ComboboxSelected>>');pump()
                construct.object_choice.current(1);construct.object_choice.event_generate('<<ComboboxSelected>>');pump()
                assert construct.current_object()['id']==box['id']
                construct.shape.set('Rectangle');construct.stories.set('1');construct.width.set('1')
                gesture((9,6),(10,7));app.save();pump();app.document.validate()
                assert len(maps.scene()['overlays'])==3 and len(construct.current_object()['cells'])>len(box['cells'])
                snapshot('reopened-and-reshaped')
                print('PASS: saved map footprints reopen independently of their tile-style demo; unfinished drawing recovers and existing buildings can be reshaped without adding duplicate overlays.',flush=True)
                from scene_tools import formation_data,formation_cells
                current=app.document;formation=formation_data(current,app.settings)
                candidates=[(x,y) for y in range(2,46) for x in range(2,62)
                    if not any(blocked for _,_,blocked in formation_cells(current,maps.scene_index,(x,y),formation))]
                x,y=min(candidates,key=lambda p:(p[0]-40)**2+(p[1]-22)**2)
                replay=directory/'frame.actions';replay.write_text('idle\n');held=directory/'drawn.btp'
                frame=work/'drawn-construction-player.ppm';headless=work/'drawn-construction-headless.ppm'
                native=subprocess.run([str(root/'build/btech-port'),'--project',str(current.root),'--play-here',maps.scene()['id'],str(x),str(y),
                    '--replay',str(replay),'--smoke-replay','--smoke-fast','--save',str(held),'--frame',str(frame)],
                    env=dict(env,SDL_AUDIODRIVER='dummy'),cwd=directory,capture_output=True,text=True,timeout=20,check=True)
                result=subprocess.run([str(root/'build/btech-headless'),'--project',str(current.root),'--load',str(held),'--frame',str(headless)],
                    cwd=directory,capture_output=True,text=True,timeout=20,check=True)
                assert frame.read_bytes()==headless.read_bytes() and bytes.fromhex('acb9bd') in frame.read_bytes()
                assert json.loads(native.stdout)['state_digest']==json.loads(result.stdout)['state_digest']
                print('PASS: the newly drawn courtyard renders with identical state and pixels in the SDL and headless game players.',flush=True)
            finally:workspace.closing=True;window.destroy()
