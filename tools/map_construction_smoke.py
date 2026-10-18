"""Exercise construction, tile management and terrain patterns on private Tk."""
def run(env,work):
    import copy,os,tempfile,subprocess,json
    from pathlib import Path
    from types import SimpleNamespace
    import tkinter as tk
    from tkinter import messagebox
    from unittest.mock import patch
    from PIL import ImageGrab
    from editor_model import create_project,ProjectDocument,EditorError
    from editor_workspace import Workspace
    from editor_session import guard,apply_draft
    from editor_history import refresh_scope
    from tile_editing import metadata
    from construction_editing import compile_rows
    from world_editing import world_size
    from map_patterns import capture,export_pattern,import_pattern
    root=Path(__file__).resolve().parents[1];work=Path(work);os.environ['DISPLAY']=env['DISPLAY']
    with tempfile.TemporaryDirectory(prefix='map-construction-ui-',dir=work) as directory:
        directory=Path(directory);tool=root/'build/btp-project'
        doc=create_project(root/'examples/beacon-demo',directory/'game','construction-ui','Construction UI',tool)
        window=tk.Tk();workspace=None;errors=[]
        def pump():
            window.update()
            if errors:raise errors.pop(0)
        def fail(title,message,**kwargs):raise AssertionError(title+': '+message)
        def visible(widget):
            pump();top=widget.winfo_toplevel()
            assert widget.winfo_ismapped(),str(widget)
            assert widget.winfo_rooty()+widget.winfo_height()<=top.winfo_rooty()+top.winfo_height(),str(widget)
            assert widget.winfo_rootx()+widget.winfo_width()<=top.winfo_rootx()+top.winfo_width(),str(widget)
        def gesture(canvas,start,end):
            canvas.event_generate('<ButtonPress-1>',x=start[0],y=start[1],time=10000);pump()
            canvas.event_generate('<B1-Motion>',x=end[0],y=end[1],time=10100);pump()
            canvas.event_generate('<ButtonRelease-1>',x=end[0],y=end[1],time=10200);pump()
        def snap(name):pump();ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/('map-construction-'+name+'.png'))
        with patch.object(messagebox,'showerror',fail):
            try:
                workspace=Workspace(window,tool,directory/'settings');window.geometry('1000x740+0+0')
                window.report_callback_exception=lambda kind,error,tb:errors.append(error)
                app=workspace.app;app.set_document(doc);app.edit_adventure();maps=app.map_editor;pump()
                maps.edit_landscape();world=maps.world_editor;pump()
                f=world.new_world();pump();assert f.values['width'].get()==f.values['height'].get()=='128'
                for percent in (100,150,200):
                    workspace.scale(percent);pump();visible(f.apply_button)
                workspace.scale(100);pump();visible(f.apply_button);snap('create-world');f.apply_button.invoke();pump()
                assert not f.window.winfo_exists() and world_size(doc.adventure)==(1024,1024);doc.validate()
                # The same reserved footer must survive a long, enlarged form.
                from adventure_editor import Form
                f=Form(world,'Tall form check')
                for i in range(40):f.field('field_'+str(i),i)
                f.submit(lambda _:None);f.window.geometry('700x300+0+0');pump();visible(f.apply_button)
                f.window.destroy()
                print('PASS: visible Create world button, original 1024×1024 default, placed cities and a scrollable long form.',flush=True)

                builder=maps.construction('Building');pump();assert maps.construction('Building') is builder
                snap('building');old=copy.deepcopy(builder.profile);builder.height.set('3')
                gesture(builder.footprint,(3*24+12,3*24+12),(4*24+12,3*24+12))
                assert builder.profile['footprint'][3][3:5]==[3,3];assert builder.profile!=old
                workspace.edit_history(False);pump();assert builder.profile==old
                workspace.edit_history(True);pump();assert builder.profile['footprint'][3][3]==3
                # Right-click a preview cell and invoke the real Clone action.
                role=builder.roles[0][3];builder.selected_role=role;old_tile=builder.profile['parts'][role]
                menus=[]
                with patch.object(tk.Menu,'tk_popup',lambda menu,*args:menus.append(menu)):
                    builder.context(SimpleNamespace(x=3*builder.preview_size+2,y=2,x_root=0,y_root=0))
                menus[-1].invoke(2);pump()
                assert builder.profile['parts'][role]!=old_tile
                pixel=workspace.current_view().controller
                assert workspace.current_view().key[1]=='pixels';pixel.color.set('ff4466ff')
                point=tuple(v*int(pixel.zoom.get())+1 for v in pixel.pixel_origin)
                gesture(pixel.canvas,point,point);pump()
                new_tile=next(t for t in doc.adventure['tiles'] if t['id']==builder.profile['parts'][role])
                assert next(i for i in doc.art['images'] if i['id']==new_tile['graphic'])['frames'][0][0].startswith('ff4466ff')
                maps.window.lift();maps.refresh();pump();construct=maps.construction_tools
                maps.drawing_tools.buttons['Building'].invoke();pump()
                visible(construct.place_button);visible(construct.edit_button);assert construct.profile()['id']==builder.current
                # Pattern stamping remains available as a separate workflow;
                # the construction brush below draws new footprints instead.
                maps.use_pattern(compile_rows(builder.profile),builder.profile['name'],overlay=True);pump()
                maps.zoom.set('16');maps.canvas.xview_moveto(0);maps.canvas.yview_moveto(0);maps.draw();pump();snap('map-tools')
                n=len(maps.scene()['overlays']);gesture(maps.canvas,(2*16+2,2*16+2),(2*16+2,2*16+2))
                assert len(maps.scene()['overlays'])==n+1;doc.validate()
                before=copy.deepcopy(doc.adventure)
                try:maps.pointer(SimpleNamespace(x=31*16+2,y=23*16+2),True)
                except EditorError:pass
                else:raise AssertionError('An out-of-bounds building placement was accepted')
                maps.finish_stroke();assert doc.adventure==before
                builder.save_pattern();library=maps.patterns();pump();assert library.current();snap('patterns')
                path=directory/'building.pattern.json';export_pattern(doc,library.current(),path)
                print('PASS: cross-shaped and stepped building, gesture Undo/Redo, clone/edit preview tile, whole-building placement and pattern persistence.',flush=True)

                wall=maps.construction('Wall');f=wall.reshape();f.values['shape'].set('L shape');f.values['width'].set('6');f.values['height'].set('6');f.values['stories'].set('3');f.apply_button.invoke();pump();snap('wall')
                assert max(map(max,wall.profile['footprint']))==3
                maps.window.lift();construct.kind_choice.set('Wall');construct.kind_choice.event_generate('<<ComboboxSelected>>');pump()
                construct.place_button.invoke();construct.stories.set('3');pump();assert maps.tool.get()=='Wall'
                before=copy.deepcopy(doc.adventure);history=len(doc.undo_stack)
                gesture(maps.canvas,(20*16+2,3*16+2),(20*16+2,3*16+2))
                assert len(maps.scene()['overlays'])==len(before['maps'][maps.scene_index]['overlays'])+1
                assert len(doc.undo_stack)==history+1
                after=copy.deepcopy(doc.adventure);workspace.edit_history(False);pump();assert doc.adventure==before
                workspace.edit_history(True);pump();assert doc.adventure==after
                maps.cancel_gesture();assert maps.tool.get()=='Select'
                construct.kind_choice.set('Road');construct.kind_choice.event_generate('<<ComboboxSelected>>');pump()
                assert construct.edit_button.cget('text')=='Create style...'
                construct.edit_button.invoke();pump();road=workspace.current_view().controller
                assert road.kind=='Road';maps.window.lift();construct.place_button.invoke();pump()
                assert maps.tool.get()=='Road';maps.layer_choice.current(0);maps.zoom.set('16');maps.draw();pump()
                gesture(maps.canvas,(2*16+2,18*16+2),(10*16+2,18*16+2))
                gesture(maps.canvas,(6*16+2,15*16+2),(6*16+2,21*16+2))
                profile=next(p for p in metadata(doc)['construction_sets'] if p['id']==road.current)
                assert maps.scene()['rows'][18][6]==profile['parts']['road_15'];doc.validate();snap('roads')
                maps.selection_rect=(2,18,4,18);maps.copy_selection();rows=copy.deepcopy(maps.clipboard);old=copy.deepcopy(doc.adventure)
                maps.cut_selection();assert doc.adventure!=old;workspace.edit_history(False);pump();assert doc.adventure==old
                maps.use_pattern(rows,'Road block');gesture(maps.canvas,(16*16+2,18*16+2),(16*16+2,18*16+2))
                assert capture(doc,maps.scene_index,(16,18,18,18))==rows
                print('PASS: three-storey wall, connected road junctions, selection cut/Undo/paste.',flush=True)

                world.window.lift();world.refresh();jigsaw=world.edit_jigsaw();pump()
                jigsaw.tile.set(profile['parts']['road_10']);jigsaw.tool.set('Line');gesture(jigsaw.canvas,(1,1),(281,281))
                assert jigsaw.jigsaw['rows'][7][7]==profile['parts']['road_10']
                menus=[]
                with patch.object(tk.Menu,'tk_popup',lambda menu,*args:menus.append(menu)):
                    jigsaw.context(SimpleNamespace(x=41,y=1,x_root=0,y_root=0))
                count=len(doc.adventure['tiles']);menus[-1].invoke(1);pump();assert len(doc.adventure['tiles'])==count+1
                assert jigsaw.jigsaw['rows'][0][1]==doc.adventure['tiles'][-1]['id']
                jigsaw.window.lift();f=jigsaw.save_pattern();f.apply_button.invoke();pump();snap('jigsaw')
                world.window.lift();world.tool.set('Select');world.zoom.set('16');world.canvas.xview_moveto(0);world.canvas.yview_moveto(0);world.draw();pump()
                gesture(world.canvas,(1,1),(33,33));world.copy_selection();world.cut_selection();world.use_pattern(world.clipboard);gesture(world.canvas,(80,80),(80,80));doc.validate()
                print('PASS: jigsaw Line drawing and context New tile, saved jigsaw pattern, world terrain selection/cut/paste.',flush=True)

                maps.window.lift();browser=maps.graphic_picker();browser.sheet.set('package:tiles');browser.refresh();pump()
                before=len(doc.adventure['tiles']);count=len(browser.keys);browser.clone_all();pump()
                assert len(doc.adventure['tiles'])==before+count and browser.sheet.get()=='Project tiles'
                snap('tile-browser');browser.clone();pump();identity=browser.selected
                browser.remove();pump();f=[d.view for d in app._editor_scope.live() if hasattr(d.view,'apply_button')][-1];visible(f.apply_button)
                if 'scripts_reviewed' in f.values:f.values['scripts_reviewed'].set('Yes')
                f.apply_button.invoke();pump()
                assert not any(t['id']==identity for t in doc.adventure['tiles']);doc.validate()
                app.save();pump();reopened=ProjectDocument(doc.root,tool)
                assert reopened.art==doc.art and metadata(reopened)['construction_sets']==metadata(doc)['construction_sets']
                assert metadata(reopened)['map_patterns']==metadata(doc)['map_patterns']
                workspace.persist_layout();snap('saved')
                print('PASS: Clone ALL sheet tiles, individual clone/removal, full player validation and project save/reopen.',flush=True)
                # Render this edited package in the actual player. Both SDL
                # and headless must compose its new building tiles identically.
                frame=work/'map-construction-player.ppm';headless=work/'map-construction-headless.ppm'
                replay=directory/'frame.actions';replay.write_text('idle\n')
                from scene_tools import formation_data,formation_cells
                formation=formation_data(doc,app.settings)
                candidates=[(x,y) for y in range(2,2*len(maps.scene()['rows'])-2) for x in range(2,2*len(maps.scene()['rows'][0])-2)
                    if not any(blocked for _,_,blocked in formation_cells(doc,maps.scene_index,(x,y),formation))]
                x,y=min(candidates,key=lambda p:(p[0]-28)**2+(p[1]-25)**2)
                common=['--project',str(doc.root),'--play-here',maps.scene()['id'],str(x),str(y),'--replay',str(replay)]
                held=directory/'constructed.btp'
                native=subprocess.run([str(root/'build/btech-port'),*common,'--smoke-replay','--smoke-fast','--save',str(held),'--frame',str(frame)],env=dict(env,SDL_AUDIODRIVER='dummy'),cwd=directory,capture_output=True,text=True,timeout=20)
                assert native.returncode==0,native.stderr
                result=subprocess.run([str(root/'build/btech-headless'),'--project',str(doc.root),'--load',str(held),'--frame',str(headless)],cwd=directory,capture_output=True,text=True,timeout=20,check=True)
                assert frame.read_bytes()==headless.read_bytes()
                assert bytes.fromhex('acb9bd') in frame.read_bytes(),'The playtest view missed the constructed building.'
                assert json.loads(native.stdout)['state_digest']==json.loads(result.stdout)['state_digest']
                print('PASS: the constructed game renders the same state and pixels in SDL and headless players.',flush=True)
                builder=maps.construction('Building');builder.height.set('4');pump()
                builder.paint(SimpleNamespace(x=3*24+12,y=3*24+12),True)
                f=builder.reshape();f.values['width'].set('unfinished width');pump()
                workspace.recovery.write(app._editor_scope);record=workspace.recovery.read(workspace.recovery.path(app._editor_scope))
            finally:
                if workspace:workspace.closing=True
                window.destroy()
            # Recreate all Tk objects, restoring an unfinished construction
            # gesture and invalid form input from the crash record.
            from editor_recovery import identity as scope_identity
            window=tk.Tk();workspace=Workspace(window,tool,directory/'settings')
            window.report_callback_exception=lambda kind,error,tb:errors.append(error)
            try:
                app=workspace.app;app.set_document(ProjectDocument(doc.root,tool));workspace.recovery.offered.add(scope_identity(app._editor_scope));pump()
                workspace.recovery.restore(app._editor_scope,record);pump()
                assert not getattr(app._editor_scope,'unrestored_recovery',False)
                builder=app.map_editor.construction('Building');assert builder.stroke is not None and builder.profile['footprint'][3][3]==4
                f=next(d.view for d in app._editor_scope.live() if isinstance(getattr(d.view,'values',None),dict) and d.view.values.get('width') and d.view.values['width'].get()=='unfinished width')
                f.window.destroy();builder.finish();app.save();pump();app.document.validate()
                maps=app.map_editor;maps.window.lift();maps.refresh();pump();construct=maps.construction_tools
                for kind in ('Building','Wall','Road'):
                    construct.kind_choice.set(kind);construct.kind_choice.event_generate('<<ComboboxSelected>>');pump()
                    assert construct.profile()['kind']==kind and construct.place_button.instate(['!disabled'])
                    assert construct.profile() in metadata(app.document)['construction_sets']
                # Selecting the construction tool directly also arms its saved
                # design; no detour through a designer window is required.
                maps.drawing_tools.buttons['Building'].invoke();pump()
                assert maps.tool.get()=='Building' and construct.active_id==construct.profile()['id']
                maps.drawing_tools.buttons['Road'].invoke();pump()
                assert maps.road_profile==construct.profile()['id'] and maps.tool.get()=='Road'
                print('PASS: fresh workspace restores construction tabs, unfinished height painting and invalid footprint fields, then saves corrected work.',flush=True)
                print('PASS: visible map construction controls draw walls with Undo, draw connected roads, and reload all three tile styles after reopening.',flush=True)
            finally:workspace.closing=True;window.destroy()
    from drawn_construction_smoke import run as drawn_journey
    drawn_journey(env,work)
