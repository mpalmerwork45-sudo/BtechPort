"""Saved construction designs, directly available beside the map paint tools."""
import tkinter as tk
from tkinter import ttk
from editor_model import EditorError
from tile_editing import metadata
from construction_editing import compile_rows,prepare_road


class MapConstructionTools:
    kinds=('Building','Wall','Road')

    def __init__(self,maps,parent):
        self.maps=maps;self.selected={};self.profiles=[];self.active_id=None
        self.kind=tk.StringVar(value='Building')
        self.frame=ttk.Frame(parent,padding=(6,0,6,6));self.frame.pack(fill='x')
        ttk.Label(self.frame,text='Construct',style='Section.TLabel').pack(side='left',padx=(4,8))
        self.kind_choice=ttk.Combobox(self.frame,textvariable=self.kind,values=self.kinds,state='readonly',width=9)
        self.kind_choice.pack(side='left',padx=3)
        self.kind_choice.bind('<<ComboboxSelected>>',lambda _:maps.guard(self.change_kind))
        self.choice=ttk.Combobox(self.frame,state='readonly',width=20);self.choice.pack(side='left',padx=3)
        self.choice.bind('<<ComboboxSelected>>',lambda _:maps.guard(self.change_design))
        self.place_button=ttk.Button(self.frame,text='Place building',command=lambda:maps.guard(self.use))
        self.place_button.pack(side='left',padx=3)
        self.edit_button=ttk.Button(self.frame,text='Edit design...',command=lambda:maps.guard(self.edit))
        self.edit_button.pack(side='left',padx=3)
        from editor_ui import flow_toolbar,tooltip
        flow_toolbar(self.frame)
        tooltip(self.choice,'Saved project designs. Edit a design to change its shape, height or tiles.')
        tooltip(self.place_button,'Buildings and walls: click to place the preview. Roads: drag to draw connected roads. Escape cancels.')

    def profile(self):
        return next((p for p in self.profiles if p['id']==self.selected.get(self.kind.get())),None)

    def refresh(self):
        designs=metadata(self.maps.document).get('construction_sets',[])
        kind=self.kind.get();self.profiles=[p for p in designs if p['kind']==kind]
        self.choice.configure(values=[p['name'] for p in self.profiles])
        if self.profiles:
            current=self.profile() or self.profiles[0];self.selected[kind]=current['id']
            self.choice.current(self.profiles.index(current));self.choice.state(['!disabled'])
        else:self.choice.set('No saved designs');self.choice.state(['disabled'])
        self.place_button.configure(text='Draw roads' if kind=='Road' else 'Place '+kind.lower(),state='normal' if self.profiles else 'disabled')
        self.edit_button.configure(text='Edit design...' if self.profiles else 'Create design...')
        # A design is saved separately from its placed tiles. Update an active
        # placement preview after editing/Undo, without changing old placements.
        if self.active_id and self.maps.tool.get() in self.kinds:
            active=next((p for p in designs if p['id']==self.active_id),None)
            if active is None:self.active_id=None;self.maps.tool.set('Select')
            elif active['kind']!='Road':self.maps.clipboard=compile_rows(active);self.maps.paste_name=active['name']

    def change_kind(self):
        self.refresh()
        if self.maps.tool.get() in self.kinds:
            if self.profile():self.use()
            else:self.maps.tool.set('Select');self.maps.draw_hover()

    def change_design(self):
        index=self.choice.current()
        if 0<=index<len(self.profiles):self.selected[self.kind.get()]=self.profiles[index]['id']
        if self.maps.tool.get() in self.kinds:self.use()

    def edit(self):
        current=self.profile();designer=self.maps.construction(self.kind.get())
        if current:designer.current=current['id'];designer.refresh()
        return designer

    def use(self):
        profile=self.profile()
        if not profile:raise EditorError('Create a design first, then choose Place or Draw roads.')
        self.activate(profile)

    def choose_tool(self):
        kind=self.maps.tool.get()
        if kind not in self.kinds:self.maps.draw_hover();return
        self.kind.set(kind);self.refresh()
        if self.profile():self.use()
        else:self.maps.tool.set('Select');self.edit()

    def activate(self,profile,connect=True):
        maps=self.maps;maps.finish_stroke();kind=profile['kind']
        self.kind.set(kind);self.selected[kind]=profile['id'];self.active_id=profile['id']
        if kind=='Road' and connect:
            profile=prepare_road(maps.document,profile)
            maps.road_profile=profile['id'];maps.road_width=1;maps.tool.set('Road');maps.refresh()
            maps.window.lift();maps.tabs.select(maps.map_tab);maps.canvas.focus_set()
            maps.status.set(profile['name']+': drag to draw connected roads in the selected layer; Escape cancels. One stroke is one Undo.')
        else:
            maps.use_pattern(compile_rows(profile),profile['name'],overlay=kind!='Road')
            if kind!='Road':maps.tool.set(kind)
        self.refresh();maps.draw_hover()
