"""Real pointer checks for visible tiles, construction details and marker tools."""
def run(env,work):
    import copy
    import os
    from pathlib import Path
    import tempfile
    import tkinter as tk
    from tkinter import messagebox
    from unittest.mock import patch
    from PIL import ImageGrab
    from editor_model import create_project,ProjectDocument
    from editor_workspace import Workspace
    from adventure_editing import composite,scene_markers
    from world_editing import upgrade,create_world,assign_city,patch_cells
    from tile_editing import metadata

    root=Path(__file__).resolve().parents[1];work=Path(work);os.environ['DISPLAY']=env['DISPLAY']
    with tempfile.TemporaryDirectory(prefix='editor-paint-',dir=work) as directory:
        tmp=Path(directory);tool=root/'build/btp-project'
        doc=create_project(root/'examples/beacon-demo',tmp/'game','paint-smoke','Paint smoke',tool)
        a=copy.deepcopy(doc.adventure);upgrade(a);scene=a['maps'][0]
        ground=next(t['id'] for t in a['tiles'] if t['terrain']=='clear');water=next(t['id'] for t in a['tiles'] if t['terrain']=='water')
        scene.update(rows=[[ground]*32 for _ in range(24)],overlays=[],entrances=[])
        a['start']['at']=[60,44]
        for event in a['events']:
            if event['op']=='transfer' and event['map']==scene['id']:event['at']=[60,44]
        doc.replace_adventure(a);doc.save()
        window=tk.Tk();workspace=None;errors=[];clock=10000
        def pump():
            window.update()
            if errors:raise errors.pop(0)
        def fail(title,message,**_):raise AssertionError(f'{title}: {message}')
        def event(canvas,sequence,x,y):
            nonlocal clock
            clock+=1000;canvas.event_generate(sequence,x=round(x),y=round(y),time=clock);pump()
        def gesture(view,start,end=None,release=True):
            end=end or start;canvas=view.canvas;size=int(view.zoom.get())
            region=list(map(float,canvas.cget('scrollregion').split()))
            canvas.xview_moveto(max(0,((start[0]+end[0]+1)*size/2-canvas.winfo_width()/2)/region[2]))
            canvas.yview_moveto(max(0,((start[1]+end[1]+1)*size/2-canvas.winfo_height()/2)/region[3]));view.draw();pump()
            def emit(sequence,point):
                x=(point[0]+.5)*size-canvas.canvasx(0);y=(point[1]+.5)*size-canvas.canvasy(0)
                assert 0<=x<canvas.winfo_width() and 0<=y<canvas.winfo_height()
                event(canvas,sequence,x,y)
            emit('<Button-1>',start)
            if end!=start:emit('<B1-Motion>',end)
            if release:emit('<ButtonRelease-1>',end)
        def brush(identity):
            index=next(i for i,t in enumerate(doc.adventure['tiles']) if t['id']==identity)
            maps.sidebar.select(0);maps.brush.see(str(index));pump();x,y,w,h=maps.brush.bbox(str(index))
            event(maps.brush,'<Button-1>',x+30,y+h/2);event(maps.brush,'<ButtonRelease-1>',x+30,y+h/2)
            assert maps.brush.curselection()==(index,)
        with patch.object(messagebox,'showerror',fail):
            try:
                workspace=Workspace(window,tool,tmp/'settings');window.geometry('1440x930+0+0')
                window.report_callback_exception=lambda kind,error,tb:errors.append(error)
                app=workspace.app;app.set_document(doc);app.edit_adventure();maps=app.map_editor;pump()
                maps.drawing_tools.buttons['Building'].invoke();pump();builder=workspace.current_view().controller
                builder.use();pump();construct=maps.construction_tools;construct.shape.set('Rectangle');construct.stories.set('1')
                maps.zoom_control.set(24);gesture(maps,(5,5),(9,9));assert construct.current_object()
                assert maps.layer_choice.get()=='Visible tiles'
                before=doc.files();brush(water);assert maps.tool.get()=='Paint'
                history=len(doc.undo_stack);gesture(maps,(6,6),release=False)
                assert doc.files()==before and maps.drag is None and composite(maps.stroke['maps'][0])[6][6]==water
                maps.finish_stroke();pump();after=doc.files()
                assert composite(maps.scene())[6][6]==water and maps.scene()['rows'][6][6]==ground
                assert construct.current_object()['details']==[[6,6,water]] and len(doc.undo_stack)==history+1
                workspace.edit_history(False);pump();assert doc.files()==before
                workspace.edit_history(True);pump();assert doc.files()==after
                gesture(maps,(4,7),(7,7));assert all(composite(maps.scene())[7][x]==water for x in range(4,8))
                maps.layer_choice.current(1);maps.change_paint_layer();old=composite(maps.scene())[5][5]
                gesture(maps,(5,5));assert maps.scene()['rows'][5][5]==water and composite(maps.scene())[5][5]==old
                workspace.edit_history(False);pump()
                maps.layer_choice.current(2);maps.change_paint_layer();before=doc.files();gesture(maps,(1,2))
                assert doc.files()==before and 'Outside the selected overlay' in maps.status.get()
                maps.layer_choice.current(0);maps.change_paint_layer();maps.drawing_tools.buttons['Fill'].invoke();pump()
                before=doc.files();gesture(maps,(2,2));assert composite(maps.scene())[2][2]==water and composite(maps.scene())[5][5]==old
                workspace.edit_history(False);pump();assert doc.files()==before
                print('PASS: palette exits construction mode; water paints visible roofs/ground, previews and commits once; explicit Base/Overlay and visible Fill behave correctly.',flush=True)

                maps.drawing_tools.buttons['Building'].invoke();pump();construct.shape.set('Rectangle');gesture(maps,(10,5),(12,9))
                assert composite(maps.scene())[6][6]==water and construct.current_object()['details']
                maps.drawing_tools.buttons['Select'].invoke();pump();gesture(maps,(6,6),(7,7));before=doc.files();maps.cut_selection();pump()
                assert composite(maps.scene())[6][6]==ground
                maps.drawing_tools.buttons['Paste'].invoke();pump();gesture(maps,(8,8));assert composite(maps.scene())[8][8]==water
                workspace.edit_history(False);workspace.edit_history(False);pump();assert doc.files()==before
                ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'editor-painted-building.png')
                print('PASS: painted building details survive footprint extension; visible Cut/Paste and Undo preserve construction metadata.',flush=True)

                # Cover a tile with a real marker label: the Paint tool must
                # paint that tile, never start a marker drag or open its form.
                a=copy.deepcopy(doc.adventure);door=dict(id='paint:door',name='Marker over terrain',at=[4,36],event='beacon:end')
                door['event']=next(e['id'] for e in a['events'] if e['op']=='end');a['maps'][0]['entrances']=[door];maps.commit(a)
                brush(water);maps.canvas.xview_moveto(0);maps.canvas.yview_moveto(.5);maps.draw();pump()
                ref=next(v['ref'] for v in scene_markers(doc.adventure,0) if v['ref'][0]=='entrance')
                tag=next(t for t,r in maps.canvas_marker_refs.items() if r==ref)
                item=next(i for i in maps.canvas.find_withtag(tag) if maps.canvas.type(i)=='text');box=maps.canvas.bbox(item)
                cx,cy=(box[0]+box[2])/2,(box[1]+box[3])/2;size=int(maps.zoom.get());tile=int(cx//size),int(cy//size)
                x,y=cx-maps.canvas.canvasx(0),cy-maps.canvas.canvasy(0);before=doc.files();start=copy.deepcopy(doc.adventure['start'])
                event(maps.canvas,'<Button-1>',x,y);assert maps.drag is None
                event(maps.canvas,'<ButtonRelease-1>',x,y)
                assert composite(maps.scene())[tile[1]][tile[0]]==water and maps.scene()['entrances'][0]['at']==[4,36]
                assert doc.adventure['start']==start and not maps.canvas.find_withtag('playtest-cursor')
                workspace.edit_history(False);pump();assert doc.files()==before
                maps.drawing_tools.buttons['Move markers'].invoke();pump()
                event(maps.canvas,'<Button-1>',x,y);assert maps.drag is not None
                event(maps.canvas,'<B1-Motion>',x+size/2,y);event(maps.canvas,'<ButtonRelease-1>',x+size/2,y)
                assert maps.scene()['entrances'][0]['at']==[5,36];workspace.edit_history(False);pump()
                maps.drawing_tools.buttons['Play here'].invoke();pump()
                assert any(maps.canvas.itemcget(i,'text')=='Playtest start' for i in maps.canvas.find_withtag('playtest-cursor') if maps.canvas.type(i)=='text')
                maps.drawing_tools.buttons['Paint'].invoke();pump();assert not maps.canvas.find_withtag('playtest-cursor')
                print('PASS: marker labels cannot steal paint strokes; Move markers still drags; Playtest start is clearly labelled and hidden during painting.',flush=True)

                a=copy.deepcopy(doc.adventure);create_world(a,'paint',32,32);assign_city(a,a['maps'][0]['id']);maps.commit(a);maps.edit_landscape();world=maps.world_editor;pump()
                world.tile_choice.current(next(i for i,t in enumerate(doc.adventure['tiles']) if t['id']==water));world.tile_choice.event_generate('<<ComboboxSelected>>');pump()
                assert world.tool.get()=='Tile';before=copy.deepcopy(doc.adventure['maps'])
                gesture(world,(62,65),(66,65));patches=patch_cells(world.current_world())
                assert patches[62,65]==patches[63,65]==water and (64,65) not in patches
                assert doc.adventure['maps']==before and 'City tiles were left unchanged' in world.info.get()
                app.save();pump();reopened=ProjectDocument(doc.root,tool)
                assert reopened.adventure==doc.adventure and metadata(reopened)==metadata(doc);doc.validate()
                print('PASS: world tile choice selects Tile; strokes skip city overlays with an explanation; painted maps/details save, validate and reopen.',flush=True)
            finally:
                if workspace:workspace.closing=True
                window.destroy()
            if errors:raise errors.pop(0)
