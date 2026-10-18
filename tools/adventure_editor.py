"""Map painting and event forms sharing the roster editor's document/history."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

from editor_recovery import recoverable_forms
from editor_model import EditorError
from editor_session import guard, register, apply_draft, scope_of, visible_parent, FieldError
from editor_workspace import view_window,open_view
from adventure_editing import OPS, composite, paint, event_template, new_id, copy_adventure, scene_markers, move_marker
from editor_tiles import load_tiles, art_tiles
from world_editing import token, upgrade, graphic_tile, draw as draw_tiles, fill as fill_tiles


class TilePalette(ttk.Treeview):
    """Image rows with the small selection API used by the painting tools."""
    def curselection(self): return tuple(int(i) for i in self.selection())
    def size(self): return len(self.get_children())
    def selection_clear(self, *_): self.selection_remove(self.selection())


def scroll_frame(parent, width=660, height=590):
    shell=ttk.Frame(parent)
    canvas=tk.Canvas(shell,highlightthickness=0,width=width,height=height)
    bar=ttk.Scrollbar(shell,orient="vertical",command=canvas.yview)
    horizontal=ttk.Scrollbar(shell,orient='horizontal',command=canvas.xview)
    canvas.configure(yscrollcommand=bar.set,xscrollcommand=horizontal.set)
    horizontal.pack(side='bottom',fill='x')
    bar.pack(side="right",fill="y");canvas.pack(side="left",fill="both",expand=True)
    body=ttk.Frame(canvas,padding=8);item=canvas.create_window(0,0,window=body,anchor="nw")
    tag='EditorScroll'+str(id(canvas))
    def wheel(event):
        canvas.yview_scroll(-1 if getattr(event,'num',None)==4 or getattr(event,'delta',0)>0 else 1,'units');return 'break'
    for sequence in ('<MouseWheel>','<Button-4>','<Button-5>'):canvas.bind_class(tag,sequence,wheel)
    def layout(_=None):
        canvas.itemconfigure(item,width=max(canvas.winfo_width(),body.winfo_reqwidth()),height=max(canvas.winfo_height(),body.winfo_reqheight()))
        canvas.configure(scrollregion=canvas.bbox('all'))
        def attach(widget):
            if not isinstance(widget,(tk.Text,tk.Listbox,ttk.Treeview,ttk.Combobox)):
                if tag not in widget.bindtags():widget.bindtags((tag,*widget.bindtags()))
                for child in widget.winfo_children():attach(child)
        attach(body)
    body.bind('<Configure>',layout);canvas.bind('<Configure>',layout)
    return shell,body


class Form:
    def __init__(self, owner, title):
        self.owner = owner
        self.recovery_action=copy.deepcopy(getattr(owner,'_form_action',None))
        self.window = tk.Toplevel(owner.window)
        self.window.title(title)
        self.window.transient(visible_parent(owner))
        self.window.columnconfigure(1, weight=1)
        shell,self.body=scroll_frame(self.window)
        shell.pack(fill="both",expand=True)
        self.body.columnconfigure(1,weight=1)
        self.window.minsize(580,250)
        self.window.geometry("700x650")
        self.values = {};self.widgets={};self.integers=set();self.tracked=[]
        self.row = 0
        self.error=tk.StringVar()
        # Reserve actions before the expanding scroll body. Otherwise a short
        # form can hide Apply entirely at large fonts or on a small display.
        self.footer=ttk.Frame(self.window);self.footer.pack(side='bottom',fill='x',before=shell)
        ttk.Label(self.footer,textvariable=self.error,foreground='#a03030',wraplength=620,padding=8).pack(fill='x')
        self.window.bind("<Escape>", lambda _: self.close())
        self.window.protocol('WM_DELETE_WINDOW',self.close)
        self.previous_grab=self.window.grab_current()
        self.window.grab_set()
        def restore_grab(event):
            if event.widget==self.window:
                if getattr(self,'size_job',None):self.window.after_cancel(self.size_job)
                if self.previous_grab is not None and self.previous_grab.winfo_exists():self.previous_grab.grab_set()
        self.window.bind('<Destroy>',restore_grab,add='+')

    def field(self, key, value, choices=None, label=None):
        ttk.Label(self.body, text=label or key.replace("_", " ").title()).grid(row=self.row, column=0, sticky="w", padx=10, pady=4)
        var = tk.StringVar(value=str(value))
        from editor_pickers import ReferenceBox,pick_reference
        widget = ReferenceBox(self.body,self,var,choices,width=38) if choices is not None else ttk.Entry(self.body, textvariable=var, width=42)
        widget.grid(row=self.row, column=1, sticky="ew", padx=10, pady=4)
        self.values[key] = var
        self.widgets[key]=widget
        if choices and (len(choices)>8 or any(':' in str(v) for v in choices)):
            ttk.Button(self.body,text='Browse...',command=lambda:pick_reference(self,widget.ids,var,label or key)).grid(row=self.row,column=2,padx=(4,0))
        if isinstance(value,int):self.integers.add(key)
        self.row += 1
        return widget

    def submit(self, callback, label='Apply'):
        self.callback=callback;self.initial=self.capture_draft()
        self.draft=register(self,pending=lambda:self.capture_draft()!=self.initial,
            apply=self.apply_pending,capture=self.capture_draft,restore=self.restore_draft,
            accept=self.accept_draft,priority=100)
        # Keep Apply reachable while scrolling through a long party form.
        self.apply_button=ttk.Button(self.footer,text=label,command=lambda:guard(self,lambda:apply_draft(self)))
        self.apply_button.pack(side='right',pady=8,padx=12)
        ttk.Button(self.footer,text='Cancel',command=self.close).pack(side='right',pady=8)
        from editor_ui import size_form
        self.size_job=self.window.after_idle(lambda:size_form(self))

    def track(self,value):
        # Nested enemy/stock forms edit mutable lists in their parent draft.
        self.tracked.append(value)

    def capture_draft(self):return dict(values={k:v.get() for k,v in self.values.items()},tracked=copy.deepcopy(self.tracked))
    def restore_draft(self,state):
        for key,value in state['values'].items():self.values[key].set(value)
        for target,value in zip(self.tracked,state['tracked']):
            target.clear();target.update(value) if isinstance(target,dict) else target.extend(value)
    def apply_pending(self):
        values={k:v.get() for k,v in self.values.items()}
        for key in self.integers:
            try:int(values[key])
            except ValueError:raise FieldError(key.replace('_',' ').capitalize()+' must be a whole number.',key)
        self.callback(values)
    def accept_draft(self):self.window.destroy()
    def show_error(self,error):
        self.error.set(str(error));self.window.lift()
        key=getattr(error,'field',None)
        widget=self.widgets.get(key)
        if widget is not None:widget.focus_set();widget.state(['invalid'])
    def guard(self,operation):return guard(self,operation)
    def close(self):
        if hasattr(self,'initial') and self.capture_draft()!=self.initial:
            answer=messagebox.askyesnocancel('Unfinished form','Apply these changes before closing?',parent=self.window)
            if answer is None:return
            if answer:return guard(self,lambda:apply_draft(self))
        self.window.destroy()


@recoverable_forms
class AdventureEditor:
    def __init__(self, parent):
        self.parent = parent
        self.document = parent.document
        if self.document.adventure is None:
            raise EditorError("This project uses the CHI campaign. Open examples/beacon-demo or examples/adventure-demo for map/event editing.")
        self.window = view_window(self,parent,'maps','Maps and events')
        self.window.transient(parent.window)
        self.window.title("Maps and events" if hasattr(self.window,'workspace') else "BattleTech Construction Kit - Maps and events")
        self.window.geometry("1000x720")
        self.window.minsize(960, 650)
        self.scene_index = 0
        self.stroke = None
        self.drag = None
        self.paint_start = self.paint_last = None
        self.selection_rect = self.clipboard = None
        self.paste_as_overlay=False;self.paste_name='Pattern';self.road_profile=None;self.road_width=1
        self.world_editor = self.art_editor = None
        self.selected_marker = None
        self.cursor = tuple(self.document.adventure["start"]["at"])
        self.images = {}
        self.graphics = {}
        self.art_cache = None
        self.hover=None;self.hover_light=True
        self.formation_preview=None
        ttk.Style(self.window).configure("Tiles.Treeview",rowheight=40)
        bar = ttk.Frame(self.window, padding=6);bar.pack(fill="x")
        for label, action in [("Save", self.save), ("Validate", self.validate), ("Undo", self.undo), ("Redo", self.redo), ("Play", self.play), ("Play here", self.play_here), ("Export", parent.export_project)]:
            ttk.Button(bar, text=label, width=len(label), style='Toolbar.TButton', command=lambda cb=action: self.guard(cb)).pack(side="left", padx=3)
        ttk.Button(bar,text="World / jigsaws",width=15,style='Toolbar.TButton',command=lambda:self.guard(self.edit_landscape)).pack(side="left",padx=3)
        ttk.Button(bar,text="Graphics / sprites",width=18,style='Toolbar.TButton',command=lambda:self.guard(self.edit_graphics)).pack(side="left",padx=3)
        if hasattr(self.window,'workspace'):bar.pack_forget()
        self.tabs = ttk.Notebook(self.window);self.tabs.pack(fill="both", expand=True)
        self.map_tab = ttk.Frame(self.tabs);self.tabs.add(self.map_tab, text="Maps")
        self.event_tab = ttk.Frame(self.tabs);self.tabs.add(self.event_tab, text="Events")
        self.world_tab = ttk.Frame(self.tabs);self.tabs.add(self.world_tab, text="People, shops and start")
        self.status = tk.StringVar(value="Choose a tile to paint. Drag an existing marker to move it; Escape cancels a drag.")
        status_label=ttk.Label(self.window, textvariable=self.status, style="Status.TLabel",wraplength=960)
        if not hasattr(self.window,'workspace'):status_label.pack(side="bottom",fill="x")
        else:self.status.trace_add('write',lambda *_:self.window.workspace.status.set(self.status.get()) if self.window.winfo_exists() else None)
        # Reserve the status strip before the flexible notebook. Long marker
        # lists must scroll inside their pane rather than push controls away.
        self.tabs.pack_forget();self.tabs.pack(fill="both",expand=True)
        self.build_maps();self.build_events();self.build_world();self.reload_graphics()
        if hasattr(self.window,'workspace'):self.tabs.hide(self.event_tab)
        self.window.bind("<Control-s>", lambda _: self.guard(self.save))
        self.window.bind("<Control-z>", lambda _: self.guard(self.undo))
        self.window.bind("<Control-y>", lambda _: self.guard(self.redo))
        self.window.bind("<Escape>", lambda _: self.cancel_gesture())
        self.window.protocol("WM_DELETE_WINDOW",lambda:self.guard(self.close))
        self.tabs.bind("<<NotebookTabChanged>>",lambda _:self.guard(self.apply_pending))
        self.draft=register(self,pending=lambda:self.event_pending or self.stroke is not None or self.construction_tools.stroke is not None,
            apply=self.apply_pending,capture=self.capture_draft,restore=self.restore_draft,priority=20)

    def guard(self, action):
        return guard(self,action)

    def capture_draft(self):
        construction=getattr(self,'construction_tools',None)
        return dict(event_id=self.event_id,template=copy.deepcopy(getattr(self,'event_draft',None)),
            values={k:v.get() for k,v in self.event_vars.items()},pending=self.event_pending,
            text=self.event_text.get('1.0','end-1c') if self.event_text else None,stroke=copy.deepcopy(self.stroke),construction=construction.capture() if construction else None)
    def restore_draft(self,state):
        self.event_id=state['event_id'];self.stroke=state['stroke']
        if state['template']:
            self.render_event_form(state['template'])
            for k,v in state['values'].items():self.event_vars[k].set(v)
            if self.event_text and state['text'] is not None:self.event_text.delete('1.0','end');self.event_text.insert('1.0',state['text'])
        self.event_pending=state['pending']
        if state.get('construction') and hasattr(self,'construction_tools'):self.construction_tools.restore(state['construction'])

    @property
    def adventure(self): return self.document.adventure

    def commit(self, adventure):
        self.document.replace_adventure(adventure)
        self.status.set("Unsaved authoring edit. Validate checks the whole game with the C player.")
        self.refresh()

    def refresh(self):
        if not self.window.winfo_exists(): return
        if self.art_cache != self.document.art:
            self.art_cache=self.document.art
            self.graphics.pop("package:art",None);self.graphics.update(art_tiles(self.document))
            self.images={k:v for k,v in self.images.items() if k[0]!="package:art"}
        self.scene_index = min(self.scene_index, len(self.adventure["maps"])-1)
        scenes = [m["name"] for m in self.adventure["maps"]]
        self.map_choice.configure(values=scenes);self.map_choice.current(self.scene_index)
        selected_layer=self.layer_choice.current()
        self.layer_choice.configure(values=["Visible tiles","Base"] + [f"Overlay {i+1} at {v['at']}" for i,v in enumerate(self.scene()["overlays"])])
        self.layer_choice.current(selected_layer if 0<=selected_layer<len(self.scene()['overlays'])+2 else 0)
        brush = self.brush.curselection()
        self.brush.delete(*self.brush.get_children())
        for i,tile in enumerate(self.adventure["tiles"]):
            image=self.tile_image(tile["sheet"],tile["graphic"],32)
            self.brush.insert("","end",iid=str(i),text=f" {tile.get('key','')}  {tile['id'].split(':')[-1]}",image=image or "")
        self.brush.insert("","end",iid=str(len(self.adventure["tiles"])),text=" Erase overlay",image="")
        self.brush.selection_set(min(brush[0] if brush else 0,self.brush.size()-1))
        self.select_brush()
        self.construction_tools.refresh()
        self.draw();self.refresh_events();self.refresh_world();self.refresh_markers()
        if self.world_editor and self.world_editor.window.winfo_exists():self.world_editor.refresh()
        if self.art_editor and self.art_editor.window.winfo_exists():self.art_editor.refresh()

    def scene(self): return self.adventure["maps"][self.scene_index]

    def build_maps(self):
        top = ttk.Frame(self.map_tab,padding=6);top.pack(fill="x")
        ttk.Label(top,text="Map",style="Section.TLabel").pack(side="left",padx=(4,8))
        self.map_choice=ttk.Combobox(top,state="readonly",width=22);self.map_choice.pack(side="left")
        self.map_choice.bind("<<ComboboxSelected>>",lambda _:self.change_map())
        actions=ttk.Menubutton(top,text='Map actions');menu=tk.Menu(actions,tearoff=False);actions.configure(menu=menu);actions.pack(side='left',padx=6)
        for title,items in [('Map',[('New map',self.new_map),('Properties',self.map_properties),('Delete map',self.delete_map)]),
                            ('Layers',[('Add overlay',self.new_overlay),('Properties',self.layer_properties),('Move building',self.move_building),('Delete layer',self.delete_layer)]),
                            ('Construct',[('Building designer',lambda:self.construction('Building')),('Wall designer',lambda:self.construction('Wall')),('Road designer',lambda:self.construction('Road'))]),
                            ('Patterns',[('Pattern Library',self.patterns),('Copy selection',self.copy_selection),('Cut selection',self.cut_selection),('Paste',lambda:self.tool.set('Paste')),('Save selection',self.save_pattern)]),
                            ('Buildings and entrances',[('Save selection as stamp',self.capture_building),('Place stamp',self.place_building)])]:
            submenu=tk.Menu(menu,tearoff=False)
            for label,action in items:submenu.add_command(label=label,command=lambda cb=action:self.guard(cb))
            menu.add_cascade(label=title,menu=submenu)
        menu.add_separator();menu.add_command(label='Reload graphics',command=self.reload_graphics);menu.add_command(label='Player setup',command=self.parent.setup)
        ttk.Button(top,text='Pattern Library',command=lambda:self.guard(self.patterns)).pack(side='left',padx=3)
        controls=ttk.Frame(self.map_tab,padding=6);controls.pack(fill="x")
        ttk.Label(controls,text="Paint on").pack(side="left",padx=(4,8))
        self.layer_choice=ttk.Combobox(controls,state="readonly",width=16,values=["Visible tiles","Base"]);self.layer_choice.current(0);self.layer_choice.pack(side="left")
        self.layer_choice.bind("<<ComboboxSelected>>",lambda _:self.guard(self.change_paint_layer))
        from editor_ui import tooltip
        tooltip(self.layer_choice,'Visible tiles paints the surface you see, including buildings. Base paints underneath overlays. Choose an overlay to edit that layer explicitly.')
        self.tool=tk.StringVar(value="Paint")
        ttk.Label(controls,text='Active tool:').pack(side='left',padx=(12,4))
        ttk.Label(controls,textvariable=self.tool,style='Section.TLabel').pack(side='left',padx=(0,8))
        from editor_canvas import CanvasZoom,DrawingTools
        self.zoom=tk.StringVar(value="24")
        self.zoom_control=CanvasZoom(controls,self.zoom,self.draw);self.zoom_control.pack(side='left')
        self.terrain=tk.BooleanVar(value=False)
        self.footprints=tk.BooleanVar(value=False)
        om=tk.Menu(menu,tearoff=False);menu.add_cascade(label='Overlays',menu=om)
        om.add_checkbutton(label='Collision',variable=self.terrain,command=self.draw);om.add_checkbutton(label='Starting formation',variable=self.footprints,command=lambda:self.guard(self.toggle_footprints))
        from editor_ui import flow_toolbar
        flow_toolbar(top);flow_toolbar(controls)
        self.drawing_tools=DrawingTools(self.map_tab,self.tool,[
            ('Tiles', [('Paint','Paint','Drag to paint the selected tile.'),('Line','Line','Drag a straight line of tiles.'),
                       ('Rectangle','Rectangle','Drag a filled rectangle of tiles.'),('Fill','Fill','Fill a connected area with the selected tile.'),
                       ('Eyedropper','Pick tile','Pick a tile from the map.'),('Select','Select','Drag a block to copy, cut or save to the Pattern Library.'),
                       ('Paste','Paste','Click to paste the copied block or chosen pattern.')]),
            ('Construct', [('Building','Building','Draw a building footprint using a saved tile style; choose height and shape below.'),
                           ('Wall','Wall','Draw connected walls; choose height and width below.'),('Road','Road','Draw connected roads; choose width below.')]),
            ('Markers', [('Move markers','Move markers','Drag an existing entrance, person, encounter or start marker.'),
                         ('Entrance','Entrance','Click to add a building entrance.'),('NPC','NPC','Click to add a person.'),
                         ('Encounter','Encounter','Click to add an encounter.'),('Start','Start','Click to set the party starting position.'),
                         ('Play here','Play here','Click to playtest from this location.')])],lambda _:self.guard(self.choose_drawing_tool))
        self.drawing_tools.pack(fill='x')
        from construction_tools import MapConstructionTools
        self.tool_options=ttk.Frame(self.map_tab)
        self.construction_tools=MapConstructionTools(self,self.tool_options)
        self.graphics_note=tk.StringVar()
        self.graphics_label=ttk.Label(self.map_tab,textvariable=self.graphics_note,style="Muted.TLabel",padding=(12,2),wraplength=940)
        if not hasattr(self.window,'workspace'):self.graphics_label.pack(fill='x')
        else:
            from editor_ui import tooltip
            tooltip(actions,self.graphics_note.get)
        body=ttk.Panedwindow(self.map_tab,orient="horizontal");self.map_body=body;body.pack(fill="both",expand=True)
        sidebar=ttk.Notebook(body);self.sidebar=sidebar
        # Scroll the controls as a group on short/high-DPI displays instead of
        # shrinking the tile list to zero underneath its fixed-size buttons.
        tile_shell,side=scroll_frame(sidebar,width=254,height=300);sidebar.add(tile_shell,text='Tiles')
        marker_shell,marker_side=scroll_frame(sidebar,width=254,height=300);sidebar.add(marker_shell,text='Markers')
        view=ttk.Frame(body,padding=(0,8,8,8));body.add(sidebar,weight=1);body.add(view,weight=5)
        side.columnconfigure(0,weight=1);side.rowconfigure(1,weight=1)
        title=ttk.Frame(side);title.grid(row=0,column=0,sticky="ew",pady=(0,6))
        ttk.Label(title,text="TILES",style="Section.TLabel").pack(side="left")
        ttk.Button(title,text="Browse all...",command=lambda:self.guard(self.graphic_picker)).pack(side="right")
        palette=ttk.Frame(side);palette.grid(row=1,column=0,sticky="nsew")
        self.brush=TilePalette(palette,show="tree",selectmode="browse",height=4,style="Tiles.Treeview")
        self.brush.column("#0",width=218,minwidth=180,stretch=True)
        brush_scroll=ttk.Scrollbar(palette,command=self.brush.yview);self.brush.configure(yscrollcommand=brush_scroll.set)
        brush_scroll.pack(side="right",fill="y");self.brush.pack(side="left",fill="both",expand=True)
        self.brush.bind("<<TreeviewSelect>>",lambda _:self.select_brush())
        self.brush.bind('<ButtonRelease-1>',lambda e:self.guard(lambda:self.select_brush(user=True)) if self.brush.identify_row(e.y) else None)
        for sequence in ('<KeyRelease-Up>','<KeyRelease-Down>','<Return>','<space>'):
            self.brush.bind(sequence,lambda _:self.guard(lambda:self.select_brush(user=True)))
        self.brush_info=tk.StringVar();brush_info=ttk.Label(side,textvariable=self.brush_info,style="Muted.TLabel",wraplength=235,padding=(0,5))
        if not hasattr(self.window,'workspace'):brush_info.grid(row=2,column=0,sticky="ew")
        else:
            from editor_ui import tooltip
            tooltip(self.brush,self.brush_info.get)
        tile_buttons=ttk.Frame(side);tile_buttons.grid(row=3,column=0,sticky="ew",pady=(0,8))
        tile_buttons.columnconfigure((0,1,2),weight=1)
        tile_actions=ttk.Menubutton(tile_buttons,text='Tile actions');tile_actions.pack(fill='x')
        self.tile_menu=tk.Menu(self.brush,tearoff=False)
        tile_actions.configure(menu=self.tile_menu)
        for label,callback in [('Edit pixels',self.edit_tile_pixels),('Properties',self.edit_tile),('Clone tile',self.duplicate_tile)]:
            self.tile_menu.add_command(label=label,command=lambda cb=callback:self.guard(cb))
        self.brush.bind('<Button-3>',self.tile_context)
        self.brush.bind('<Double-1>',lambda _:self.guard(self.edit_tile_pixels))
        side=marker_side;side.columnconfigure(0,weight=1);side.rowconfigure(7,weight=1)
        ttk.Label(side,text="MARKERS",style="Section.TLabel",padding=(0,5)).grid(row=5,column=0,sticky="w")
        ttk.Label(side,text="Use Move markers to drag on map",style="Muted.TLabel").grid(row=6,column=0,sticky="w",pady=(0,5))
        marker_box=ttk.Frame(side);marker_box.grid(row=7,column=0,sticky="nsew")
        self.markers=tk.Listbox(marker_box,exportselection=False,height=3,relief="flat",borderwidth=0,highlightthickness=1,highlightbackground="#cfd8df",selectbackground="#dcebed",selectforeground="#163d44",font="TkDefaultFont")
        marker_scroll=ttk.Scrollbar(marker_box,command=self.markers.yview);self.markers.configure(yscrollcommand=marker_scroll.set)
        marker_scroll.pack(side="right",fill="y");self.markers.pack(side="left",fill="both",expand=True)
        self.markers.bind("<<ListboxSelect>>",lambda _:self.select_marker())
        self.markers.bind("<Double-Button-1>",lambda _:self.guard(self.edit_marker))
        ttk.Button(side,text="Delete selected marker",command=lambda:self.guard(self.delete_marker)).grid(row=8,column=0,sticky="ew",pady=(8,0))
        self.canvas=tk.Canvas(view,background="#263842",highlightthickness=1,highlightbackground="#cfd8df")
        sx=ttk.Scrollbar(view,orient="horizontal",command=self.canvas.xview);sy=ttk.Scrollbar(view,orient="vertical",command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=sx.set,yscrollcommand=sy.set)
        view.rowconfigure(0,weight=1);view.columnconfigure(0,weight=1)
        self.canvas.grid(row=0,column=0,sticky="nsew");sx.grid(row=1,column=0,sticky="ew");sy.grid(row=0,column=1,sticky="ns")
        self.canvas.bind("<Button-1>",lambda e:self.guard(lambda:self.pointer(e,True)))
        self.canvas.bind("<B1-Motion>",lambda e:self.guard(lambda:self.pointer(e,False)))
        self.canvas.bind("<ButtonRelease-1>",lambda _:self.guard(self.finish_stroke))
        self.canvas.bind("<Double-Button-1>",lambda e:self.guard(lambda:self.double_marker(e)) if self.tool.get()=='Move markers' else self.guard(lambda:self.pointer(e,True)))
        self.canvas.bind("<Button-3>",lambda e:self.guard(lambda:self.pointer(e,True,erase=True) if self.tool.get() in ('Building','Wall','Road') else self.sample_tile(e)))
        self.canvas.bind('<B3-Motion>',lambda e:self.guard(lambda:self.pointer(e,False,erase=True)) if self.tool.get() in ('Building','Wall','Road') else None)
        self.canvas.bind('<ButtonRelease-3>',lambda _:self.guard(self.finish_stroke) if self.tool.get() in ('Building','Wall','Road') else None)
        self.canvas.bind("<Control-c>",lambda _:self.guard(self.copy_selection))
        self.canvas.bind("<Control-x>",lambda _:self.guard(self.cut_selection))
        self.canvas.bind("<Control-v>",lambda _:self.tool.set("Paste"))
        self.canvas.bind('<Motion>',self.hover_move)
        self.canvas.bind('<Leave>',lambda _:self.clear_hover())
        self.hover_timer=self.canvas.after(380,self.blink_hover)
        self.canvas.bind('<Destroy>',self.stop_hover)
        self.zoom_control.attach(self.canvas)
        # The selected button follows keyboard shortcuts and pattern/designer
        # actions as well as clicks. Only construction's options are contextual;
        # the complete tool strip stays visible above the map at all times.
        trace=self.tool.trace_add('write',lambda *_:self.show_tool_options())
        self.drawing_tools.bind('<Destroy>',lambda e:self.tool.trace_remove('write',trace) if e.widget is self.drawing_tools else None,add='+')

    def choose_drawing_tool(self):
        self.finish_stroke();self.construction_tools.choose_tool();self.canvas.focus_set();self.draw()

    def show_tool_options(self):
        if self.tool.get() in self.construction_tools.kinds:self.tool_options.pack(fill='x',before=self.map_body)
        else:self.tool_options.pack_forget()
        if self.tool.get()!='Play here':self.canvas.delete('playtest-cursor')

    def paint_layer(self):return max(-1,self.layer_choice.current()-1)

    def change_paint_layer(self):
        self.finish_stroke();self.draw()
        self.status.set('Paint on '+self.layer_choice.get()+('. Edits replace the displayed tile.' if self.paint_layer()==-1 else '. Higher overlays can cover edits to this layer.'))

    def hover_move(self,event):
        size=int(self.zoom.get());point=(int(self.canvas.canvasx(event.x)//size),int(self.canvas.canvasy(event.y)//size))
        scene=self.scene()
        self.hover=point if 0<=point[0]<len(scene['rows'][0]) and 0<=point[1]<len(scene['rows']) else None
        self.draw_hover()

    def clear_hover(self):self.hover=None;self.canvas.delete('brush-hover')

    def draw_hover(self):
        self.canvas.delete('brush-hover')
        self.construction_tools.draw_preview()
        if self.hover is None:return
        x,y=self.hover;size=int(self.zoom.get())
        if self.tool.get()=='Paste' and self.clipboard:
            # Preview the whole block; red bounds make an invalid edge paste
            # visible before the click. Paste never silently crops a building.
            w,h=len(self.clipboard[0]),len(self.clipboard);scene=self.scene()
            valid=x+w<=len(scene['rows'][0]) and y+h<=len(scene['rows'])
            values={t['id']:t for t in self.adventure['tiles']}
            for yy,row in enumerate(self.clipboard):
                for xx,identity in enumerate(row):
                    value=values.get(identity)
                    if value and x+xx<len(scene['rows'][0]) and y+yy<len(scene['rows']):
                        im=self.tile_image(value['sheet'],value['graphic'],size)
                        if im:self.canvas.create_image((x+xx)*size,(y+yy)*size,image=im,anchor='nw',tags='brush-hover')
            self.canvas.create_rectangle(x*size,y*size,(x+w)*size,(y+h)*size,outline='#79ecc3' if valid else '#ff6472',width=3,tags='brush-hover')
        self.canvas.create_rectangle(x*size+1,y*size+1,(x+1)*size-1,(y+1)*size-1,
            outline='#ffffff' if self.hover_light else '#243641',width=2,tags='brush-hover')
        if self.footprints.get() and self.formation_preview:
            from scene_tools import formation_cells
            for cx,cy,blocked in formation_cells(self.document,self.scene_index,(x*2,y*2),self.formation_preview):
                self.canvas.create_rectangle(cx*size+2,cy*size+2,(cx+1)*size-2,(cy+1)*size-2,
                    outline='#ff6472' if blocked else '#65f3a7',width=3,tags='brush-hover')

    def toggle_footprints(self):
        from scene_tools import formation_data
        if self.footprints.get():self.formation_preview=formation_data(self.document,self.parent.settings)
        self.draw_hover()

    def blink_hover(self):
        if not self.canvas.winfo_exists():return
        if self.hover_timer is not None:self.canvas.after_cancel(self.hover_timer)
        self.hover_light=not self.hover_light;self.draw_hover();self.hover_timer=self.canvas.after(380,self.blink_hover)

    def stop_hover(self,event):
        if event.widget==self.canvas and self.hover_timer is not None:
            self.canvas.after_cancel(self.hover_timer);self.hover_timer=None

    def reload_graphics(self):
        self.cancel_gesture()
        self.images.clear()
        try:
            self.graphics=load_tiles(self.document,self.parent.settings)
            self.graphics_note.set("Graphics ready | original terrain colors" if self.document.manifest["requires"]!="none" else "Graphics ready | package artwork")
            if hasattr(self.window,'workspace'):self.graphics_label.pack_forget()
        except EditorError as exc:
            self.graphics=art_tiles(self.document);self.graphics_note.set(f"Graphics unavailable: {exc}  Use Player setup, then Reload graphics.")
            self.graphics_label.pack(fill='x',before=self.map_body)
        self.refresh()

    def tile_image(self,sheet,graphic,size):
        tiles=self.graphics.get(sheet,())
        if isinstance(tiles,dict):
            if graphic not in tiles:return None
        elif not isinstance(graphic,int) or not 0<=graphic<len(tiles):return None
        cache=(sheet,graphic,size)
        if cache not in self.images:
            source=tiles[graphic];im=tk.PhotoImage(master=self.window,width=size,height=size)
            im.put(" ".join("{"+" ".join(source[y*16//size][x*16//size] for x in range(size))+"}" for y in range(size)))
            self.images[cache]=im
        return self.images[cache]

    def select_brush(self,user=False):
        selected=self.brush.curselection()
        if not selected:return
        index=selected[0]
        if index<len(self.adventure["tiles"]):
            tile=self.adventure["tiles"][index]
            self.brush_info.set(f"{tile['terrain'].title()} | graphic {tile['graphic']} | {tile['sheet']}")
        else:self.brush_info.set("Erase the visible overlay tile, or the explicitly selected overlay. Base ground remains.")
        # Only an actual palette interaction changes tools. Refreshing the
        # thumbnail selection during a building stroke must not disarm it.
        if user and self.tool.get() not in ('Paint','Line','Rectangle','Fill'):
            self.finish_stroke();self.tool.set('Paint');self.draw()

    def change_map(self):
        index=self.map_choice.current();self.finish_stroke();self.scene_index=index;self.selected_marker=None;self.selection_rect=None;self.layer_choice.current(0);self.refresh()

    def draw(self):
        scene=self.construction_tools.preview_scene((self.stroke or self.adventure)["maps"][self.scene_index]);grid=composite(scene);size=int(self.zoom.get())
        self.canvas.delete("all");self.canvas.configure(scrollregion=(0,0,len(grid[0])*size,len(grid)*size))
        tiles={token(t):t for t in self.adventure["tiles"]}
        terrain_colors={"clear":"#28574d","rough":"#947b64","water":"#457caa","woods":"#397557","wall":"#b45a60"}
        for y,row in enumerate(grid):
            for x,key in enumerate(row):
                tile=tiles.get(key);color=terrain_colors.get(tile["terrain"],"#f00") if tile else "#f00"
                image=self.tile_image(tile["sheet"],tile["graphic"],size) if tile and not self.terrain.get() else None
                if image:
                    self.canvas.create_image(x*size,y*size,image=image,anchor="nw")
                else:
                    self.canvas.create_rectangle(x*size,y*size,(x+1)*size,(y+1)*size,fill=color,outline="#20303b")
                    if not self.terrain.get(): self.canvas.create_text(x*size+size/2,y*size+size/2,text=key[-2:],fill="white")
        if self.selection_rect:
            x0,y0,x1,y1=self.selection_rect
            self.canvas.create_rectangle(x0*size,y0*size,(x1+1)*size,(y1+1)*size,outline="#8ee4e8",width=3)
        if self.paint_layer()>0:
            layer=scene["overlays"][self.paint_layer()-1];ox,oy=layer["at"]
            self.canvas.create_rectangle(ox*size,oy*size,(ox+len(layer["rows"][0]))*size,(oy+len(layer["rows"]))*size,outline="#edcc75",width=3)
        self.canvas_marker_refs={}
        def marker(at,label,color,tag=None,selected=False):
            x,y=at[0]*size/2,at[1]*size/2
            tags=(tag,) if tag else ()
            if selected:self.canvas.create_oval(x-10,y-10,x+10,y+10,outline="white",width=2,tags=tags)
            self.canvas.create_oval(x-5,y-5,x+5,y+5,fill=color,outline="#10242b",width=2,tags=tags)
            left=x+9+len(label)*7>len(grid[0])*size
            label_item=self.canvas.create_text(x-9 if left else x+9,max(16,y-9),text=label,fill="#f6fbff",anchor="se" if left else "sw",font="TkHeadingFont",tags=tags)
            bounds=self.canvas.bbox(label_item)
            if bounds:
                bg=self.canvas.create_rectangle(bounds[0]-4,bounds[1]-2,bounds[2]+4,bounds[3]+2,fill="#20343e",outline="",tags=tags)
                self.canvas.tag_raise(label_item,bg)
        colors={"entrance":"#edcc75","npc":"#6abec0","party":"#a9bb70","enemy":"#ef8e85","start":"#f4f1de"}
        for i,value in enumerate(scene_markers(self.stroke or self.adventure,self.scene_index)):
            tag=f"marker-{i}";self.canvas_marker_refs[tag]=value["ref"]
            kind,_,identity,enemy=value["ref"];label=value["label"]
            if kind=="party":label="Party spawn"
            elif kind=="enemy":
                encounter=next(e for e in (self.stroke or self.adventure)["encounters"] if e["id"]==identity)
                unit=encounter["enemies"][enemy]
                catalog=self.document.content["mechs"] if unit["kind"]=="mech" else self.adventure["people"]
                label=next((e.get("name",e["id"].split(":")[-1]) for e in catalog if e["id"]==unit["definition"]),unit["definition"].split(":")[-1])
            label=label[:23]+"..." if len(label)>24 else label
            marker(value["at"],label,colors[kind],tag,value["ref"]==self.selected_marker)
        # This is an editor playtest origin, not a game object. Keep it out of
        # ordinary painting and give it an explicit name in the Play here tool.
        if self.tool.get()=='Play here':marker(self.cursor,'Playtest start','#bf91d5',tag='playtest-cursor')
        self.draw_hover()

    def hit_marker(self,px,py):
        size=int(self.zoom.get());values=scene_markers(self.stroke or self.adventure,self.scene_index)
        hits=[v["ref"] for v in values if (v["at"][0]*size/2-px)**2+(v["at"][1]*size/2-py)**2<=100]
        if not hits:
            for item in self.canvas.find_overlapping(px,py,px,py):
                for tag in self.canvas.gettags(item):
                    ref=self.canvas_marker_refs.get(tag)
                    if ref is not None and ref not in hits:hits.append(ref)
        return self.selected_marker if self.selected_marker in hits else hits[-1] if hits else None

    def pointer(self,event,first,erase=False):
        if first:self.canvas.focus_set()
        size=int(self.zoom.get());px=self.canvas.canvasx(event.x);py=self.canvas.canvasy(event.y)
        x,y=int(px//size),int(py//size)
        scene=self.scene()
        half=(int(px*2//size),int(py*2//size));self.cursor=half
        tool=self.tool.get()
        if tool in ('Building','Wall'):
            if 0<=y<len(scene['rows']) and 0<=x<len(scene['rows'][0]):self.construction_tools.pointer((x,y),first,erase)
            return
        if first and tool=='Move markers':
            ref=self.hit_marker(px,py)
            if ref is not None:
                marker=next(m for m in scene_markers(self.adventure,self.scene_index) if m["ref"]==ref)
                self.stroke=copy_adventure(self.document);self.selected_marker=ref
                self.drag=dict(ref=ref,pointer=(px,py),at=tuple(marker["at"]),scene=self.scene_index)
                self.refresh_markers();self.draw();self.status.set("Drag marker | snaps to half tiles | Escape cancels")
                if hasattr(self.window,'workspace'):self.window.workspace.update_inspector()
                return
        elif self.drag is not None:
            drag=self.drag
            # Keep the pointer offset so grabbing a label never makes its
            # marker jump. A draft is committed once, on mouse release.
            at=[drag["at"][0]+round((px-drag["pointer"][0])*2/size),drag["at"][1]+round((py-drag["pointer"][1])*2/size)]
            at=[max(0,min(2*len(scene["rows"][0])-1,at[0])),max(0,min(2*len(scene["rows"])-1,at[1]))]
            try:move_marker(self.stroke,self.scene_index,drag["ref"],at)
            except EditorError as exc:self.status.set(str(exc));return
            self.draw();self.status.set(f"Marker at half-tile {at[0]},{at[1]} | release to place | Escape cancels")
            return
        if not 0<=y<len(scene["rows"]) or not 0<=x<len(scene["rows"][0]): return
        if tool in ("Paint","Line","Rectangle","Fill","Paste","Road"):
            if first:
                self.stroke=copy_adventure(self.document);self.paint_start=self.paint_last=(x,y);self.road_erasing=erase
            if self.stroke is None: return
            index=self.brush.curselection()[0] if self.brush.curselection() else 0
            key=token(self.adventure["tiles"][index]) if index<len(self.adventure["tiles"]) else " "
            layer=self.paint_layer()
            if first and layer>0 and tool in ('Paint','Line','Rectangle','Fill'):
                overlay=scene['overlays'][layer-1];ox,oy=overlay['at']
                if not (ox<=x<ox+len(overlay['rows'][0]) and oy<=y<oy+len(overlay['rows'])):
                    self.stroke=None;self.status.set('Outside the selected overlay. Choose Paint on: Visible tiles to paint across the map.');return
            if tool in ("Line","Rectangle"):self.stroke=copy_adventure(self.document)
            target=self.stroke["maps"][self.scene_index]
            if tool=="Fill":
                if first:fill_tiles(target,layer,x,y,key)
            elif tool=='Paste':
                if first and self.clipboard:
                    from map_patterns import paste
                    try:
                        if self.paste_as_overlay:
                            w,h=len(self.clipboard[0]),len(self.clipboard)
                            if x+w>len(target['rows'][0]) or y+h>len(target['rows']):raise EditorError('The complete building must fit on the map. Move it inward.')
                            upgrade(self.stroke)
                            target['overlays'].append(dict(at=[x,y],rows=[[' ']*w for _ in range(h)]));layer=len(target['overlays'])
                        paste(self.stroke,self.scene_index,layer,x,y,self.clipboard)
                    except Exception:self.stroke=None;raise
            elif tool=='Road':
                from construction_editing import draw_road
                from tile_editing import metadata
                profile=next((p for p in metadata(self.document).get('construction_sets',[]) if p['id']==self.road_profile),None)
                if profile is None:
                    self.stroke=None;raise EditorError('Choose a saved Road design in the Construct row, then click Draw roads.')
                shape=self.construction_tools.shape.get();start=self.paint_last
                if shape in ('Line','Rectangle','Courtyard'):self.stroke=copy_adventure(self.document);start=self.paint_start
                try:draw_road(self.stroke,self.scene_index,layer,start,(x,y),profile,int(self.construction_tools.width.get()),shape,self.road_erasing or shape=='Erase')
                except Exception:self.stroke=None;raise
            else:draw_tiles(target,layer,self.paint_start if tool in ("Line","Rectangle") else self.paint_last,(x,y),key,tool)
            self.paint_last=(x,y);self.draw()
        elif tool=="Select":
            if first:self.paint_start=(x,y)
            if self.paint_start:
                x0,x1=sorted((self.paint_start[0],x));y0,y1=sorted((self.paint_start[1],y));self.selection_rect=(x0,y0,x1,y1);self.draw()
        elif first:
            if tool in ("Entrance","NPC"): self.entrance_dialog(at=half,npc=tool=="NPC")
            elif tool=="Encounter": self.encounter_dialog(at=half)
            elif tool=="Start":
                a=copy_adventure(self.document);a["start"].update(map=scene["id"],at=list(half));self.commit(a)
            elif tool=="Play here": self.play_here()
            elif tool=="Move markers":self.selected_marker=None;self.draw()
            elif tool=="Eyedropper":self.sample_tile(event)
        self.status.set(f"Tile {x},{y} | half-tile {half[0]},{half[1]} | {tool} | Paint on {self.layer_choice.get()}")

    def sample_tile(self,event):
        size=int(self.zoom.get());x=int(self.canvas.canvasx(event.x)//size);y=int(self.canvas.canvasy(event.y)//size)
        grid=composite(self.scene())
        if not 0<=y<len(grid) or not 0<=x<len(grid[0]):return
        index=next(i for i,t in enumerate(self.adventure["tiles"]) if token(t)==grid[y][x])
        self.brush.selection_set(str(index));self.brush.see(str(index));self.select_brush();self.tool.set("Paint")

    def copy_selection(self):
        if not self.selection_rect:raise EditorError("Use Select and drag a rectangle first. Ctrl+C copies; Ctrl+V chooses Paste.")
        from map_patterns import capture
        x0,y0,x1,y1=self.selection_rect;self.clipboard=capture(self.document,self.scene_index,self.selection_rect)
        self.paste_as_overlay=False
        self.status.set(f"Copied {x1-x0+1} x {y1-y0+1} tiles. Ctrl+V, then click to paste.")

    def cut_selection(self):
        if not self.selection_rect:raise EditorError('Use Select and drag a rectangle first. Cut uses the Paint on target.')
        from map_patterns import cut
        self.finish_stroke();self.clipboard=cut(self.document,self.scene_index,self.selection_rect,self.paint_layer());self.paste_as_overlay=False
        self.refresh();self.status.set('Cut selected layer. Ctrl+V and click to paste; Undo restores the cut.')

    def use_pattern(self,rows,name='Pattern',overlay=False):
        from map_patterns import check_rows
        check_rows(self.document,rows);self.clipboard=copy.deepcopy(rows);self.paste_as_overlay=overlay;self.paste_name=name
        self.tool.set('Paste');self.window.lift();self.tabs.select(self.map_tab);self.canvas.focus_set()
        self.status.set(name+': click to place; Escape cancels. '+('Each placement becomes a new overlay.' if overlay else 'Paints into the selected layer.'))

    def save_pattern(self):
        if not self.selection_rect:raise EditorError('Use Select and drag a rectangle first.')
        from map_patterns import capture,save_pattern
        rows=capture(self.document,self.scene_index,self.selection_rect)
        f=Form(self,'Save map pattern');f.field('name','Map pattern')
        f.submit(lambda v:save_pattern(self.document,rows,v['name']));return f

    def patterns(self):
        from pattern_library import PatternLibrary
        from editor_workspace import open_view
        view=open_view(self,'patterns',lambda:PatternLibrary(self));view.target=self;return view

    def construction(self,kind='Building'):
        from construction_editor import ConstructionEditor
        from editor_workspace import open_view
        return open_view(self,'construction',lambda:ConstructionEditor(self,kind),kind)

    def edit_landscape(self):
        self.apply_pending()
        if self.world_editor and self.world_editor.window.winfo_exists():self.world_editor.window.lift();return
        from world_editor import WorldEditor
        self.world_editor=WorldEditor(self)

    def edit_graphics(self):
        self.apply_pending()
        self.art_editor=self.parent.graphics_editor()

    def finish_stroke(self):
        if self.construction_tools.stroke is not None:self.construction_tools.finish();return
        if self.stroke is not None:
            a=self.stroke;drag=self.drag;self.stroke=None;self.drag=None
            if a==self.adventure:
                self.draw()
                if drag:self.status.set("Marker selected | drag to move or double-click to edit.")
            elif drag:self.commit(a)
            else:
                from map_construction import commit_tiles
                commit_tiles(self.document,a);self.refresh()

    def cancel_gesture(self):
        if self.construction_tools.stroke is not None:self.construction_tools.cancel()
        elif self.stroke is not None:
            self.stroke=None;self.drag=None
            self.draw();self.status.set("Move / paint stroke cancelled.")
        elif self.tool.get() in ('Paste','Building','Wall','Road'):self.tool.set('Select');self.draw_hover()

    def double_marker(self,event):
        self.cancel_gesture()
        ref=self.hit_marker(self.canvas.canvasx(event.x),self.canvas.canvasy(event.y))
        if ref is not None:
            self.selected_marker=ref;self.refresh_markers();self.edit_marker()

    def new_map(self):
        form=Form(self,"New map")
        for key,value in dict(id=new_id(self.document,"maps","map"),name="New map",width=32,height=24,origin_x=160,origin_y=64).items():form.field(key,value)
        def apply(v):
            w,h=int(v["width"]),int(v["height"])
            if not 16<=w<=64 or not 16<=h<=64: raise EditorError("Map dimensions are 16..64 tiles.")
            a=copy_adventure(self.document);key=token(a["tiles"][0]);row=key*w if a["schema_version"]==1 else [key]*w
            a["maps"].append(dict(id=v["id"],name=v["name"],origin=[int(v["origin_x"]),int(v["origin_y"])],rows=[copy.deepcopy(row) for _ in range(h)],overlays=[],entrances=[]))
            self.scene_index=len(a["maps"])-1;self.commit(a)
        form.submit(apply)

    def map_properties(self):
        m=self.scene();form=Form(self,"Map properties")
        for key,value in dict(name=m["name"],origin_x=m["origin"][0],origin_y=m["origin"][1],width=len(m["rows"][0]),height=len(m["rows"])).items():form.field(key,value)
        def apply(v):
            w,h=int(v["width"]),int(v["height"])
            if not 16<=w<=64 or not 16<=h<=64: raise EditorError("Map dimensions are 16..64 tiles.")
            a=copy_adventure(self.document);m=a["maps"][self.scene_index]
            if any(o["at"][0]+len(o["rows"][0])>w or o["at"][1]+len(o["rows"])>h for o in m["overlays"]):raise EditorError("Resize or remove overlays before shrinking across them.")
            key=token(a["tiles"][0]);row=key*w if a["schema_version"]==1 else [key]*w
            m.update(name=v["name"],origin=[int(v["origin_x"]),int(v["origin_y"])],rows=[(m["rows"][y]+row)[:w] if y<len(m["rows"]) else copy.deepcopy(row) for y in range(h)])
            self.commit(a)
        form.submit(apply)

    def delete_map(self):
        if len(self.adventure["maps"])==1:raise EditorError("Keep at least one map.")
        if hasattr(self.window,'workspace'):
            from editor_dependencies import dialog
            return dialog(self,self.scene()['id'],delete=True)
        a=copy_adventure(self.document);a["maps"].pop(self.scene_index);self.commit(a)

    def duplicate_tile(self):
        selected=self.brush.curselection()
        if not selected or selected[0]>=len(self.adventure["tiles"]):return
        a=copy_adventure(self.document);tile=copy.deepcopy(a["tiles"][selected[0]])
        if len(a["tiles"])>=4096:raise EditorError("The tile library is full (4096 definitions).")
        if a["schema_version"]==1 and len(a["tiles"])<64:
            used={t["key"] for t in a["tiles"]};tile["key"]=next(chr(c) for c in range(33,127) if chr(c) not in used)
        else:upgrade(a);tile.pop("key",None)
        tile["id"]=new_id(self.document,"tiles","tile");a["tiles"].append(tile)
        # A clone owns its pixels: editing it must not repaint its source.
        if tile['sheet']=='package:art':
            from art_editing import clone_image
            art=copy.deepcopy(self.document.art)
            source=next(i for i in art['images'] if i['id']==tile['graphic'])
            image=clone_image(source,self.document.content['package_id'],art['images'])
            art['images'].append(image);tile['graphic']=image['id']
            self.document.replace_art(art,a);self.refresh()
        else:self.commit(a)
        self.brush.selection_clear(0,"end");self.brush.selection_set(len(a["tiles"])-1);self.edit_tile()

    def tile_context(self,event):
        item=self.brush.identify_row(event.y)
        if not item:return
        self.brush.selection_set(item);self.select_brush()
        try:self.tile_menu.tk_popup(event.x_root,event.y_root)
        finally:self.tile_menu.grab_release()

    def edit_tile_pixels(self):
        self.edit_graphics();self.art_editor.edit_map_tile()

    def new_overlay(self): self.overlay_dialog()
    def layer_properties(self):
        if self.paint_layer()<1: return self.map_properties()
        self.overlay_dialog(self.paint_layer()-1)

    def capture_building(self):
        from scene_tools import capture_stamp
        if not self.selection_rect:raise EditorError('Use Select to mark a building rectangle, including its entrance.')
        f=Form(self,'Building stamp');f.field('name','Building')
        def apply(v):capture_stamp(self.document,self.scene_index,self.selection_rect,v['name']);self.status.set('Building stamp saved with its entrance and event references.')
        f.submit(apply)

    def place_building(self):
        from scene_tools import place_stamp
        from event_workbench import editor_data
        stamps=editor_data(self.document).get('building_stamps',[])
        if not stamps:raise EditorError('Save a building selection as a stamp first.')
        labels={s['name']+' | '+s['id']:s['id'] for s in stamps};f=Form(self,'Place building stamp')
        f.field('stamp',next(iter(labels)),list(labels));f.field('x',self.cursor[0]//2);f.field('y',self.cursor[1]//2)
        def apply(v):
            index=place_stamp(self.document,self.scene_index,labels[v['stamp']],int(v['x']),int(v['y']));self.refresh();self.layer_choice.current(index+1);self.draw()
        f.submit(apply)

    def move_building(self):
        from scene_tools import move_group
        index=self.paint_layer()-1
        if index<0:raise EditorError('Select a building overlay first.')
        old=self.scene()['overlays'][index];f=Form(self,'Move building and contained markers');f.field('x',old['at'][0]);f.field('y',old['at'][1])
        def apply(v):move_group(self.document,self.scene_index,index,int(v['x']),int(v['y']));self.refresh()
        f.submit(apply)

    def overlay_dialog(self,index=None):
        old=self.scene()["overlays"][index] if index is not None else dict(at=[0,0],rows=[" "*4]*4)
        form=Form(self,"Overlay bounds")
        for key,value in dict(x=old["at"][0],y=old["at"][1],width=len(old["rows"][0]),height=len(old["rows"])).items():form.field(key,value)
        def apply(v):
            x,y,w,h=(int(v[k]) for k in ("x","y","width","height"));scene=self.scene()
            if min(x,y)<0 or min(w,h)<1 or x+w>len(scene["rows"][0]) or y+h>len(scene["rows"]): raise EditorError("Overlay must fit within the map.")
            blank=" "*w if self.adventure["schema_version"]==1 else [" "]*w
            layer=dict(at=[x,y],rows=[(old["rows"][row]+blank)[:w] if row<len(old["rows"]) and isinstance(old["rows"][row],type(blank)) else copy.deepcopy(blank) for row in range(h)])
            a=copy_adventure(self.document);layers=a["maps"][self.scene_index]["overlays"]
            if index is None:layers.append(layer)
            else:layers[index]=layer
            self.commit(a);self.layer_choice.current(len(layers)+1 if index is None else index+2);self.draw()
        form.submit(apply)

    def delete_layer(self):
        index=self.paint_layer()-1
        if index>=0:
            a=copy_adventure(self.document);a["maps"][self.scene_index]["overlays"].pop(index);self.layer_choice.current(0);self.commit(a)

    def edit_tile(self):
        if not self.brush.curselection() or self.brush.curselection()[0]>=len(self.adventure["tiles"]):return
        index=self.brush.curselection()[0];tile=self.adventure["tiles"][index];form=Form(self,"Tile definition")
        form.field("id",tile["id"])
        if "key" in tile:form.field("key",tile["key"])
        form.field("graphic",str(tile["graphic"]))
        form.field("sheet",tile["sheet"],(["package:tiles"] if self.document.manifest["requires"]=="none" else ["chi:land","chi:destroyed"])+["package:art"])
        form.field("terrain",tile["terrain"],["clear","rough","water","woods","wall"]);form.field("mini_color",tile["mini_color"])
        preview=ttk.Label(form.body)
        ttk.Button(form.body,text="Choose graphic...",command=lambda:self.guard(lambda:self.graphic_picker(form))).grid(row=form.row,column=0,padx=10,pady=10,sticky="w")
        preview.grid(row=form.row,column=1,sticky="w",padx=10,pady=10);form.row+=1
        def show_preview(*_):
            try:graphic=form.values["graphic"].get() if form.values["sheet"].get()=="package:art" else int(form.values["graphic"].get())
            except ValueError:graphic=-1
            image=self.tile_image(form.values["sheet"].get(),graphic,64)
            preview.configure(image=image or "",text="Graphics unavailable" if image is None else "")
        form.values["graphic"].trace_add("write",show_preview);form.values["sheet"].trace_add("write",show_preview);show_preview()
        def apply(v):
            if v["id"]!=tile["id"]:raise EditorError("Existing tile IDs stay stable. Duplicate to create a new identity.")
            a=copy_adventure(self.document)
            if "key" in v:
                if len(v["key"])!=1 or v["key"]==" ":raise EditorError("A tile key is one non-space character.")
                old=a["tiles"][index]["key"]
                if any(t["key"]==v["key"] for i,t in enumerate(a["tiles"]) if i!=index):raise EditorError("Tile key already exists.")
                for m in a["maps"]:
                    for layer in [m,*m["overlays"]]:layer["rows"]=[row.replace(old,v["key"]) for row in layer["rows"]]
            if v["sheet"]=="package:art":upgrade(a);v.pop("key",None)
            else:v["graphic"]=int(v["graphic"])
            v["mini_color"]=int(v["mini_color"]);a["tiles"][index]=v;self.images.clear();self.commit(a)
        form.submit(apply)

    def graphic_picker(self,form=None,choose=None,selected=None):
        from tile_browser import TileBrowser
        return TileBrowser(self,form,choose,selected)

    def refresh_markers(self):
        self.marker_ids=[];self.markers.delete(0,"end")
        for value in scene_markers(self.adventure,self.scene_index):
            self.marker_ids.append(value["ref"])
            self.markers.insert("end",value["label"])
            if value["ref"]==self.selected_marker:self.markers.selection_set(len(self.marker_ids)-1)

    def select_marker(self):
        if self.markers.curselection():
            self.selected_marker=self.marker_ids[self.markers.curselection()[0]];self.draw()
            if hasattr(self.window,'workspace'):self.window.workspace.update_inspector()

    def edit_marker(self):
        if not self.markers.curselection():return
        kind,_,identity,enemy=self.marker_ids[self.markers.curselection()[0]]
        if kind in ("entrance","npc"):
            self.entrance_dialog(next(i for i,e in enumerate(self.scene()["entrances"]) if e["id"]==identity))
        elif kind=="start":self.start_dialog()
        else:self.encounter_dialog(next(i for i,e in enumerate(self.adventure["encounters"]) if e["id"]==identity),selected_enemy=enemy)

    def delete_marker(self):
        if self.markers.curselection():
            kind,_,identity,enemy=self.marker_ids[self.markers.curselection()[0]];a=copy_adventure(self.document)
            if kind=="start":raise EditorError("Move the start marker or change Start / party; a game needs its starting point.")
            if kind in ("entrance","npc"):
                values=a["maps"][self.scene_index]["entrances"];values.pop(next(i for i,e in enumerate(values) if e["id"]==identity))
            else:
                index=next(i for i,e in enumerate(a["encounters"]) if e["id"]==identity)
                if kind=="enemy":a["encounters"][index]["enemies"].pop(enemy)
                else:a["encounters"].pop(index)
            self.selected_marker=None;self.commit(a)

    def entrance_dialog(self,index=None,at=None,npc=False):
        doors=self.scene()["entrances"]
        old=doors[index] if index is not None else dict(id=f"{self.document.manifest['package_id']}:door-{self.scene_index+1}-{len(doors)+1}",name="Talk" if npc else "New entrance",at=list(at),event=self.adventure["events"][0]["id"])
        form=Form(self,"NPC / entrance")
        for key,value in dict(id=old["id"],name=old["name"],x=old["at"][0],y=old["at"][1]).items():form.field(key,value)
        form.field("event",old["event"],[e["id"] for e in self.adventure["events"]])
        form.field("person",old.get("person",self.adventure["people"][0]["id"] if npc else "none"),["none"]+[p["id"] for p in self.adventure["people"]])
        form.field("icon",old.get("icon","none"),["none"]+[im["id"] for im in self.document.art["images"] if im["width"]<=64 and im["height"]<=64],label="Map entrance / NPC graphic")
        def apply(v):
            d=dict(id=v["id"],name=v["name"],at=[int(v["x"]),int(v["y"])],event=v["event"])
            if v["person"]!="none":d["person"]=v["person"]
            a=copy_adventure(self.document);dest=a["maps"][self.scene_index]["entrances"]
            if v["icon"]!="none":upgrade(a);d["icon"]=v["icon"]
            if index is None:dest.append(d)
            else:dest[index]=d
            self.commit(a)
        form.submit(apply)

    def encounter_dialog(self,index=None,at=None,selected_enemy=None):
        old=copy.deepcopy(self.adventure["encounters"][index]) if index is not None else dict(id=new_id(self.document,"encounters","encounter"),map=self.scene()["id"],party_at=list(at),enemies=[])
        form=Form(self,"Encounter and enemy spawns");form.track(old)
        form.field("id",old["id"]);form.field("map",old["map"],[m["id"] for m in self.adventure["maps"]]);form.field("party_x",old["party_at"][0]);form.field("party_y",old["party_at"][1])
        listing=tk.Listbox(form.body,height=6,width=60,exportselection=False);listing.grid(row=form.row,column=0,columnspan=2,padx=10,sticky="ew");form.row+=1
        def refresh():
            listing.delete(0,"end")
            for enemy in old["enemies"]:listing.insert("end",f"{enemy['kind']} {enemy['definition']} at {enemy['at']}")
            if selected_enemy is not None and selected_enemy<len(old["enemies"]):listing.selection_set(selected_enemy)
        def enemy_dialog(edit=False,recovered_index=None):
            selected=listing.curselection()
            if recovered_index is not None:selected=(recovered_index,)
            if edit and not selected:return
            at_index=selected[0] if edit else None
            enemy=old["enemies"][at_index] if edit else dict(kind="mech",definition=self.document.content["mechs"][0]["id"],at=[min(120,old["party_at"][0]+8),old["party_at"][1]])
            dialog=Form(form,"Enemy placement");kind=dialog.field("kind",enemy["kind"],["mech","person"])
            dialog.recovery_action=dict(method='enemy',args=[edit,at_index])
            def choices():return [m["id"] for m in (self.document.content["mechs"] if dialog.values["kind"].get()=="mech" else self.adventure["people"])]
            definition=dialog.field("definition",enemy["definition"],choices())
            kind.bind("<<ComboboxSelected>>",lambda _: (definition.configure(values=choices()),dialog.values["definition"].set(choices()[0])))
            dialog.field("x",enemy["at"][0]);dialog.field("y",enemy["at"][1])
            def apply(v):
                enemy=dict(kind=v["kind"],definition=v["definition"],at=[int(v["x"]),int(v["y"])])
                if at_index is None:old["enemies"].append(enemy)
                else:old["enemies"][at_index]=enemy
                refresh()
            dialog.submit(apply)
        form.recovery_children={'enemy':enemy_dialog};form.on_restore=refresh
        buttons=ttk.Frame(form.body);buttons.grid(row=form.row,column=0,columnspan=2);form.row+=1
        ttk.Button(buttons,text="Add enemy",command=lambda:self.guard(enemy_dialog)).pack(side="left")
        ttk.Button(buttons,text="Edit enemy",command=lambda:self.guard(lambda:enemy_dialog(True))).pack(side="left")
        def remove():
            if listing.curselection():old["enemies"].pop(listing.curselection()[0]);refresh()
        ttk.Button(buttons,text="Remove",command=remove).pack(side="left");refresh()
        listing.bind("<Double-Button-1>",lambda _:self.guard(lambda:enemy_dialog(True)))
        def apply(v):
            old.update(id=v["id"],map=v["map"],party_at=[int(v["party_x"]),int(v["party_y"])])
            a=copy_adventure(self.document)
            if index is None:a["encounters"].append(old)
            else:a["encounters"][index]=old
            self.commit(a)
        form.submit(apply)

    def build_events(self):
        body=ttk.Panedwindow(self.event_tab,orient="horizontal");body.pack(fill="both",expand=True)
        left=ttk.Frame(body,width=280);event_shell,self.event_form=scroll_frame(body);body.add(left,weight=1);body.add(event_shell,weight=3)
        self.event_listing=tk.Listbox(left,exportselection=False);self.event_listing.pack(fill="both",expand=True,padx=6,pady=6)
        self.event_listing.bind("<<ListboxSelect>>",lambda _:self.guard(self.populate_event))
        buttons=ttk.Frame(left);buttons.pack(fill="x")
        for label,callback in [("New",self.new_event),("Duplicate",self.duplicate_event),("Delete",self.delete_event)]:ttk.Button(buttons,text=label,command=lambda cb=callback:self.guard(cb)).pack(side="left")
        ttk.Button(left,text='Service building...',command=lambda:self.guard(self.service_template)).pack(fill='x',padx=6,pady=6)
        ttk.Button(left,text='Event graph / quests...',command=lambda:self.guard(self.event_graph)).pack(fill='x',padx=6,pady=3)
        self.event_id=None;self.event_vars={};self.event_text=None;self.event_pending=False

    def event_graph(self):
        from event_workbench import EventGraph
        self.apply_pending();return open_view(self,'events',lambda:EventGraph(self))

    def service_template(self):
        from building_templates import PRESETS,service_building
        self.apply_pending();f=Form(self,'New service building')
        f.field('preset','Full service depot',list(PRESETS));f.field('name','Service depot')
        for op,cost in [('repair',500),('rearm',200),('heal',100),('salvage',1000)]:f.field(op,cost,label=op.title()+' price')
        f.field('mech',self.document.content['mechs'][0]['id'],[m['id'] for m in self.document.content['mechs']],label='Salvage chassis (once only)')
        f.field('door','None',['None']+[d['id'] for m in self.adventure['maps'] for d in m['entrances']],label='Attach to entrance')
        def apply(v):
            self.event_id=service_building(self.document,v['preset'],v['name'],{op:int(v[op]) for op in ('repair','rearm','heal','salvage')},v['mech'],None if v['door']=='None' else v['door'])
            self.refresh();self.populate_event()
        f.submit(apply)

    def refresh_events(self):
        self.event_listing.delete(0,"end")
        for e in self.adventure["events"]:self.event_listing.insert("end",f"{e['op']:8} {e['id']}")
        if self.event_id:
            at=next((i for i,e in enumerate(self.adventure["events"]) if e["id"]==self.event_id),None)
            if at is not None:self.event_listing.selection_set(at)

    def populate_event(self):
        if not self.event_listing.curselection():return
        index=self.event_listing.curselection()[0];identity=self.adventure["events"][index]["id"]
        if self.event_pending:
            self.apply_event()
            index=next(i for i,e in enumerate(self.adventure["events"]) if e["id"]==identity)
            self.event_listing.selection_clear(0,"end");self.event_listing.selection_set(index)
        e=self.adventure["events"][index];self.event_id=e["id"]
        self.render_event_form(copy.deepcopy(e))

    def render_event_form(self,e):
        for child in self.event_form.winfo_children():child.destroy()
        self.event_vars={};self.event_text=None;self.event_draft=e;self.event_pending=False;row=0
        events=[v["id"] for v in self.adventure["events"]]
        self.event_form.columnconfigure(1,weight=1)
        def field(key,value,choices=None):
            nonlocal row
            ttk.Label(self.event_form,text=key.replace("_"," ").title()).grid(row=row,column=0,sticky="w",pady=4,padx=4)
            var=tk.StringVar(value=str(value));self.event_vars[key]=var
            var.trace_add("write",lambda *_:setattr(self,"event_pending",True))
            control=ttk.Combobox(self.event_form,textvariable=var,values=choices,state="readonly",width=50) if choices is not None else ttk.Entry(self.event_form,textvariable=var,width=52)
            control.grid(row=row,column=1,sticky="ew",pady=4);row+=1;return control
        field("id",e["id"]);op=field("op",e["op"],list(OPS))
        def change(_):self.render_event_form(event_template(self.document,self.event_vars["op"].get(),self.event_id))
        op.bind("<<ComboboxSelected>>",lambda event:self.guard(lambda:change(event)))
        if "text" in e:
            ttk.Label(self.event_form,text="Dialogue").grid(row=row,column=0,sticky="nw",pady=5)
            self.event_text=tk.Text(self.event_form,height=7,width=48,wrap="word",undo=True);self.event_text.grid(row=row,column=1,sticky="ew");self.event_text.insert("1.0",e["text"]);row+=1
            self.event_text.edit_modified(False)
            def modified(_):
                if self.event_text and self.event_text.edit_modified():self.event_pending=True;self.event_text.edit_modified(False)
            self.event_text.bind("<<Modified>>",modified)
            field("portrait",e.get("portrait","none"),["none","broker","training"] if self.document.manifest["requires"]=="none" else ["none","broker","training","lounge","prison","inventor","cinema","hospital","comstar","clothes","video-hut","mayor"])
        if e["op"] in ("picture","say","choice","finish"):
            field("image",e.get("image","none"),(["none"] if e["op"]!="picture" else [])+[im["id"] for im in self.document.art["images"] if e["op"]=="picture" or (im["width"]<=88 and im["height"]<=88)])
        for key in ("next","failure","unchanged","then","else","cancel","win","loss","flee"):
            if key in e:field(key,e[key],events)
        for key,collection in [("flag","flags"),("person","people"),("map","maps"),("shop","shops"),("encounter","encounters")]:
            if key in e:field(key,e[key],[v if isinstance(v,str) else v["id"] for v in self.adventure[collection]])
        if 'mech' in e:field('mech',e['mech'],[v['id'] for v in self.document.content['mechs']])
        if e['op'] in ('repair','rearm','heal'):
            field('slot',str(e['slot']+1) if 'slot' in e else 'All',['All']+[str(i+1) for i in range(8 if e['op']=='heal' else 4)])
        for key in ("value","credits","cost"):
            if key in e:field(key,e[key])
        if "at" in e:field("x",e["at"][0]);field("y",e["at"][1])
        if e["op"]=="choice":
            field("choice_count",len(e["options"]),[str(i) for i in range(1,6)])
            for i in range(5):
                value=e["options"][i] if i<len(e["options"]) else dict(label="Choice",next=events[0])
                field(f"label_{i+1}",value["label"]);field(f"choice_{i+1}",value["next"],events)
        if e["op"]=="lua":
            field("script",e["script"],[v["id"] for v in self.document.manifest.get("scripts",[])])
            field("route_count",len(e["routes"]),[str(i) for i in range(1,6)])
            for i in range(5):field(f"route_{i+1}",e["routes"][i] if i<len(e["routes"]) else events[0],events)
        ttk.Button(self.event_form,text="Apply event",command=lambda:self.guard(self.apply_event)).grid(row=row,column=1,sticky="e",pady=10)
        ttk.Label(self.event_form,text="Apply adds an undo step. Save/Validate checks every reference and dialogue bound.",wraplength=540).grid(row=row+1,column=0,columnspan=2,sticky="w",pady=6)

    def apply_event(self):
        if not self.event_id:return
        e=copy.deepcopy(self.event_draft);values={k:v.get() for k,v in self.event_vars.items()}
        e.update({k:values[k] for k in e if k not in ("text","options","routes","at") and k in values})
        def integer(key):
            try:return int(values[key])
            except ValueError:raise FieldError(key.replace('_',' ').capitalize()+' must be a whole number.',key)
        for key in ("value","credits","cost"):
            if key in e:e[key]=integer(key)
        if e['op'] in ('repair','rearm','heal'):
            if values['slot']=='All':e.pop('slot',None)
            else:e['slot']=integer('slot')-1
        if self.event_text:e["text"]=" ".join(self.event_text.get("1.0","end-1c").split())
        if "at" in e:e["at"]=[integer('x'),integer('y')]
        if e["op"]=="choice":e["options"]=[dict(label=values[f"label_{i+1}"],next=values[f"choice_{i+1}"]) for i in range(int(values["choice_count"]))]
        if e["op"]=="lua":e["routes"]=[values[f"route_{i+1}"] for i in range(int(values["route_count"]))]
        a=copy_adventure(self.document);index=next(i for i,v in enumerate(a["events"]) if v["id"]==self.event_id)
        if "image" in values:
            if values["image"]!="none":upgrade(a);e["image"]=values["image"]
            else:e.pop("image",None)
        if e["id"]!=self.event_id:raise EditorError("Existing event IDs stay stable. Duplicate to create a new identity.")
        a["events"][index]=e;self.event_pending=False;self.commit(a)

    def new_event(self):
        a=copy_adventure(self.document);e=event_template(self.document,"say");a["events"].append(e);self.event_id=e["id"];self.commit(a);self.populate_event()
    def duplicate_event(self):
        if not self.event_id:return
        a=copy_adventure(self.document);e=copy.deepcopy(next(v for v in a["events"] if v["id"]==self.event_id));e["id"]=new_id(self.document,"events","event");a["events"].append(e);self.event_id=e["id"];self.commit(a);self.populate_event()
    def delete_event(self):
        if not self.event_id:return
        if hasattr(self.window,'workspace'):
            from editor_dependencies import dialog
            return dialog(self,self.event_id,delete=True)
        a=copy_adventure(self.document)
        if len(a["events"])==1:raise EditorError("Keep at least one event.")
        a["events"]=[v for v in a["events"] if v["id"]!=self.event_id];self.event_id=None;self.commit(a)
        for child in self.event_form.winfo_children():child.destroy()

    def build_world(self):
        bar=ttk.Frame(self.world_tab,padding=8);bar.pack(fill="x")
        for label,callback in [("Start / party",self.start_dialog),("New person",self.person_dialog),("New shop",self.shop_dialog),("Add flag",self.flag_dialog)]:ttk.Button(bar,text=label,command=lambda cb=callback:self.guard(cb)).pack(side="left",padx=4)
        self.world_listing=tk.Listbox(self.world_tab,exportselection=False);self.world_listing.pack(fill="both",expand=True,padx=8,pady=8)
        self.world_listing.bind("<Double-Button-1>",lambda _:self.guard(self.edit_world))
        ttk.Button(self.world_tab,text="Delete selected",command=lambda:self.guard(self.delete_world)).pack(anchor="e",padx=8,pady=8)

    def refresh_world(self):
        self.world_ids=[];self.world_listing.delete(0,"end")
        for key in ("people","shops","flags"):
            for i,value in enumerate(self.adventure[key]):
                self.world_ids.append((key,i));self.world_listing.insert("end",f"{key:8} {value if isinstance(value,str) else value['id']}"+(f"  {value.get('name','')}" if isinstance(value,dict) else ""))

    def edit_world(self):
        if self.world_listing.curselection():
            key,index=self.world_ids[self.world_listing.curselection()[0]]
            if key=="people":self.person_dialog(index)
            elif key=="shops":self.shop_dialog(index)
    def delete_world(self):
        if self.world_listing.curselection():
            if hasattr(self.window,'workspace'):
                from editor_dependencies import dialog
                key,index=self.world_ids[self.world_listing.curselection()[0]]
                item=self.adventure[key][index]
                return dialog(self,item['id'] if isinstance(item,dict) else item,delete=True)
            key,index=self.world_ids[self.world_listing.curselection()[0]];a=copy_adventure(self.document);a[key].pop(index);self.commit(a)

    def person_dialog(self,index=None):
        old=copy.deepcopy(self.adventure["people"][index]) if index is not None else dict(id=new_id(self.document,"people","person"),identity="actor:2" if self.document.manifest["requires"]=="none" else "chi:edward",name="New companion",attributes=[8,8,8],skills=[1,1,1,1,1,1,1],weapon=0,armor=0)
        form=Form(self,"Character template")
        form.field("id",old["id"]);form.field("name",old.get("name",""))
        form.field("identity",old["identity"],[f"actor:{i}" for i in range(10)] if self.document.manifest["requires"]=="none" else ["chi:jason","chi:rex","chi:edward","chi:russ","chi:rick","chi:zeke","chi:possum","chi:marco","chi:rusty","chi:hunter"])
        for i,label in enumerate(["strength","dexterity","intelligence"]):form.field(label,old["attributes"][i])
        for i,label in enumerate(["sidearms","rifles","heavy_arms","gunnery","piloting","technical","medical"]):form.field(label,old["skills"][i])
        form.field("weapon",old["weapon"]);form.field("armor",old["armor"])
        def apply(v):
            value=dict(id=v["id"],identity=v["identity"],attributes=[int(v[k]) for k in ("strength","dexterity","intelligence")],skills=[int(v[k]) for k in ("sidearms","rifles","heavy_arms","gunnery","piloting","technical","medical")],weapon=int(v["weapon"]),armor=int(v["armor"]))
            if v["name"]:value["name"]=v["name"]
            a=copy_adventure(self.document)
            if index is None:a["people"].append(value)
            else:a["people"][index]=value
            self.commit(a)
        form.submit(apply)

    def shop_dialog(self,index=None):
        old=self.adventure["shops"][index] if index is not None else dict(id=new_id(self.document,"shops","shop"),stock=[])
        form=Form(self,"Shop stock");form.field("id",old["id"])
        selected=tk.Listbox(form.body,selectmode="multiple",exportselection=False,height=14,width=60)
        selected.grid(row=form.row,column=0,columnspan=2,padx=10);form.row+=1
        for i,m in enumerate(self.document.content["mechs"]):
            selected.insert("end",m["name"])
            if m["id"] in old["stock"]:selected.selection_set(i)
        def apply(v):
            value=dict(id=v["id"],stock=[self.document.content["mechs"][i]["id"] for i in selected.curselection()]);a=copy_adventure(self.document)
            if index is None:a["shops"].append(value)
            else:a["shops"][index]=value
            self.commit(a)
        form.submit(apply)

    def flag_dialog(self):
        form=Form(self,"New flag");form.field("id",new_id(self.document,"flags","flag"))
        def apply(v):a=copy_adventure(self.document);a["flags"].append(v["id"]);self.commit(a)
        form.submit(apply)

    def start_dialog(self):
        old=self.adventure["start"];form=Form(self,"Start and initial party")
        form.field("map",old["map"],[m["id"] for m in self.adventure["maps"]]);form.field("x",old["at"][0]);form.field("y",old["at"][1]);form.field("credits",old["credits"]);form.field("event",old["event"],[e["id"] for e in self.adventure["events"]])
        form.field("party_count",len(old["party"]),[str(i) for i in range(1,9)])
        for i in range(8):
            member=old["party"][i] if i<len(old["party"]) else dict(person=self.adventure["people"][0]["id"],mech="none")
            form.field(f"person_{i+1}",member["person"],[p["id"] for p in self.adventure["people"]]);form.field(f"mech_{i+1}",member["mech"],["none"]+[m["id"] for m in self.document.content["mechs"]])
        def apply(v):
            a=copy_adventure(self.document);a["start"]=dict(map=v["map"],at=[int(v["x"]),int(v["y"])],credits=int(v["credits"]),event=v["event"],party=[dict(person=v[f"person_{i+1}"],mech=v[f"mech_{i+1}"]) for i in range(int(v["party_count"]))]);self.commit(a)
        form.submit(apply)

    def apply_pending(self):
        self.finish_stroke()
        if self.event_pending:self.apply_event()
    def save(self):self.parent.save();self.status.set(self.parent.status.get())
    def validate(self):self.parent.validate();self.status.set(self.parent.status.get())
    def undo(self):
        if self.stroke is not None or self.construction_tools.stroke is not None:
            self.cancel_gesture();return
        if self.event_pending:
            self.event_pending=False;self.populate_event();return
        self.parent.apply_form();self.document.undo();self.refresh();self.parent.refresh_list();self.populate_event()
    def redo(self):self.apply_pending();self.parent.apply_form();self.document.redo();self.refresh();self.parent.refresh_list();self.populate_event()
    def play(self):self.save();self.parent.launch_player()
    def play_here(self):self.save();self.parent.launch_player((self.scene()["id"],*self.cursor))
    def close(self):
        if hasattr(self.window,'workspace'):
            if not scope_of(self).confirm_view(self):return
            self.cancel_gesture();self.event_pending=False;self.populate_event();self.window.workspace.hide(self.window);return
        # Shared document edits remain in the parent even if this window closes.
        if not scope_of(self).confirm_close(self):return
        self.window.destroy();self.parent.map_editor=None
