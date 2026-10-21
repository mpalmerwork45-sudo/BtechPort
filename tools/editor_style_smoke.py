"""Exercise style coverage and the shared graph/table/dropdown interactions."""
def run(env,work):
    import copy,tempfile,time,tkinter as tk
    from tkinter import ttk
    from pathlib import Path
    from PIL import ImageGrab
    from editor_model import create_project,ProjectDocument
    from editor_workspace import Workspace
    from construction_editing import geometry
    from tile_editing import metadata
    from map_construction import projection
    from event_editing import editor_data
    root=Path(__file__).resolve().parents[1];tool=root/'build/btp-project'
    with tempfile.TemporaryDirectory(prefix='style-ui-',dir=work) as tmp:
        folder=Path(tmp);doc=create_project(root/'examples/beacon-demo',folder/'game','style-ui','Style test',tool)
        window=tk.Tk();workspace=Workspace(window,tool,folder/'settings');window.geometry('1440x960+0+0');errors=[]
        window.report_callback_exception=lambda kind,error,tb:errors.append(error)
        def pump():
            for _ in range(4):window.update();time.sleep(.015)
            if errors:raise errors.pop(0)
        try:
            app=workspace.app;app.set_document(doc);app.edit_adventure();maps=app.map_editor;pump()
            road=maps.construction('Road');pump()
            for direction,mask in [('north',11),('east',7),('south',14),('west',13)]:
                f=road.reshape();f.values['shape'].set('T '+direction);f.apply_button.invoke();pump();assert not f.window.winfo_exists()
                assert f'road_{mask}' in {r for row in geometry(road.profile) for r in row}
                road.part.current(road.role_ids.index(f'road_{mask}'));road.part.event_generate('<<ComboboxSelected>>');pump()
                assert road.selected_role==f'road_{mask}' and 'T-junction' in road.part.get()
                picker=road.choose_part();pump();picker.window.destroy();pump()
            assert '16/16' in road.coverage_text.get()
            ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'style-road-junctions.png')
            wall=maps.construction('Wall');pump();assert wall.height.get()=='0'
            assert all(r==' ' or r.startswith('roof_') for row in geometry(wall.profile) for r in row)
            wall.use();pump();construct=maps.construction_tools;assert construct.stories.get()=='0'
            maps.zoom.set('16');maps.draw();maps.canvas.xview_moveto(0);maps.canvas.yview_moveto(0);pump()
            def point(x,y):return dict(x=round((x+.5)*16-maps.canvas.canvasx(0)),y=round((y+.5)*16-maps.canvas.canvasy(0)))
            maps.canvas.event_generate('<Button-1>',**point(3,3));maps.canvas.event_generate('<B1-Motion>',**point(9,3));maps.canvas.event_generate('<ButtonRelease-1>',**point(9,3));pump()
            record=construct.current_object();assert record and {h for _,_,h in record['cells']}=={0}
            at,roles=projection(record);assert at==(3,3) and len(roles)==1
            doc.validate();doc.save();assert ProjectDocument(doc.root,tool).files()==doc.files()
            ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'style-zero-wall.png')
            print('PASS: all four T-junction selectors/pickers, complete road style, zero-story wall brush and Save/reopen.',flush=True)

            # Descriptions are real author metadata, not changes to dialogue.
            beacon=create_project(root/'examples/battletech-demo',folder/'beacon','beacon-ui','Last Beacon graph',tool)
            app.set_document(beacon);app.edit_adventure();maps=app.map_editor;graph=maps.event_graph();graph.selected='beacon:offer';graph.draw();pump()
            assert len(editor_data(beacon)['event_descriptions'])==54
            before=copy.deepcopy(beacon.adventure);f=graph.describe();f.values['description'].set('Offer the road contract or tactical help.');f.apply_button.invoke();pump()
            assert beacon.adventure==before and 'tactical help' in editor_data(beacon)['event_descriptions']['beacon:offer']
            for zoom in ('.2','.75','1','1.75'):
                graph.zoom.set(zoom);graph.draw();pump()
                for event in beacon.adventure['events']:
                    tag='description:'+event['id'];items=graph.canvas.find_withtag(tag)
                    if not items:continue
                    bounds=graph.canvas.bbox(items[0]);x,y=graph.positions[event['id']];z=float(zoom)
                    assert bounds[3]<(y+123)*z,(zoom,event['id'],bounds)
            graph.zoom.set('1');graph.fit();pump();ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'style-event-descriptions.png')
            beacon.undo();assert editor_data(beacon)['event_descriptions']==metadata(ProjectDocument(root/'examples/battletech-demo',tool))['event_descriptions']
            print('PASS: Last Beacon descriptions, editable author notes, Undo and graph bounds at four zoom levels.',flush=True)

            panel=tk.Toplevel(window);panel.geometry('620x400+40+40')
            table=ttk.Treeview(panel,columns=('mass',),show='tree headings');table.heading('#0',text='Model');table.heading('mass',text='Tons');table.pack(fill='both',expand=True)
            rows=[('z','ZEUS','80'),('c','CATAPULT','65'),('a','ATLAS','100')]
            for identity,name,mass in rows:table.insert('','end',iid=identity,text=name,values=(mass,))
            table.selection_set('z');readonly=ttk.Combobox(panel,values=('ATLAS AS7-D','BANSHEE BNC-3E','CATAPULT CPLT-C1','ZEUS ZEU-6S'),state='readonly');readonly.pack()
            editable=ttk.Combobox(panel,values=('North','Northeast','South'));editable.pack();pump()
            def head(column):
                x=next(x for x in range(2,table.winfo_width()-2) if table.identify_region(x,10)=='heading' and table.identify_column(x)==column)
                table.event_generate('<Button-1>',x=x+4,y=10);table.event_generate('<ButtonRelease-1>',x=x+4,y=10);pump()
            head('#1');assert table.get_children()==('c','z','a') and table.heading('mass','text').endswith('↑')
            head('#1');assert table.get_children()==('a','z','c') and table.heading('mass','text').endswith('↓')
            head('#1');assert table.get_children()==('z','c','a') and table.heading('mass','text')=='Tons'
            head('#0');assert table.get_children()==('a','c','z') and table.selection()==('z',)
            # Deleting/repopulating is how real library search filters work.
            table.delete(*table.get_children())
            for identity,name,mass in rows:table.insert('','end',iid=identity,text=name,values=(mass,))
            pump();assert table.get_children()==('a','c','z')
            head('#0');head('#0');assert table.get_children()==('z','c','a')
            readonly.focus_force();pump()
            for key in ('c','a','t'):readonly.event_generate('<KeyPress>',keysym=key);readonly.event_generate('<KeyRelease>',keysym=key);pump()
            assert readonly.get()=='CATAPULT CPLT-C1',readonly.get()
            readonly._typeahead=('',0);readonly.tk.call('ttk::combobox::Post',readonly._w);pump()
            dropdown=readonly._w+'.popdown.f.l'
            for key in ('z','e','u'):readonly.tk.call('event','generate',dropdown,'<KeyPress>','-keysym',key);pump()
            assert tuple(map(int,readonly.tk.call(dropdown,'curselection')))==(3,)
            readonly.tk.call('event','generate',dropdown,'<KeyPress>','-keysym','Return');pump();assert readonly.get()=='ZEUS ZEU-6S'
            editable.focus_force();pump()
            for key in ('n','o','r'):editable.event_generate('<KeyPress>',keysym=key);editable.event_generate('<KeyRelease>',keysym=key);pump()
            assert editable.get()=='North',editable.get()
            ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'style-sort-completion.png');panel.destroy();pump()
            print('PASS: heading ascending/descending/original order, numeric sorting, refresh and selection retention; readonly and editable type-ahead.',flush=True)
        finally:
            workspace.play_session.shutdown();workspace.tasks.shutdown();workspace.closing=True;window.destroy()
