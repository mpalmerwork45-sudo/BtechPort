"""Native CHI adapter for the normal map, pixel, structure and pattern tools."""
from __future__ import annotations
import copy
import tkinter as tk
from tkinter import ttk
from adventure_editor import AdventureEditor,Form
from editor_model import EditorError
from editor_session import guard
from chi_spatial import enable,data,change,find,move_town,clone_map


class ChiMapEditor(AdventureEditor):
    def __init__(self,parent):
        enable(parent.document)
        super().__init__(parent)
        self.tabs.hide(self.event_tab);self.tabs.hide(self.world_tab)
        bar=ttk.Frame(self.map_tab,padding=(8,3));bar.pack(fill='x',before=self.map_body)
        for label,cb in [('World, towns and jigsaws',self.edit_landscape),('Native map properties',self.native_properties),
                         ('Door slots',self.door_slots),('NPC routes',self.npc_routes),('Art, films, font and audio',self.resources),('Clone into map slot',self.clone_slot)]:
            ttk.Button(bar,text=label,command=lambda fn=cb:guard(self,fn)).pack(side='left',padx=3)
        from editor_ui import flow_toolbar
        flow_toolbar(bar)
        self.status.set('Native CHI maps. Paint, structures, patterns and pixel edits use the shared Save/Undo. Doors call the existing BLD programs.')

    def new_map(self):return self.clone_slot()
    def delete_map(self):raise EditorError('Native CHI retains 15 fixed map slots. Rename, move or replace a slot; unrestricted map creation belongs to authored games.')
    def map_properties(self):return self.native_properties()
    def missions(self):
        from chi_missions_editor import open_missions
        return open_missions(self.parent)
    def event_graph(self):
        from chi_bridge_editor import open_quests
        return open_quests(self.parent).event_graph()
    def person_dialog(self,index=None):return self.npc_routes()
    def entrance_dialog(self,index=None,at=None,npc=False):
        if npc:return self.npc_routes()
        return super().entrance_dialog(index,at,npc)
    def edit_landscape(self):
        from chi_world_editor import open_world
        return open_world(self)
    def resources(self):
        from chi_resource_editor import open_resources
        return open_resources(self)
    def clone_slot(self):
        value=data(self.document);f=Form(self,'Clone town into an existing map slot')
        f.field('source',self.scene()['id'],[m['id'] for m in value['maps'] if m['slot']<14])
        f.field('target','chi:map-03',[m['id'] for m in value['maps'] if m['slot']<14])
        def apply(v):
            if v['source']==v['target']:raise EditorError('Choose a different destination slot.')
            change(self.document,lambda a:clone_map(a,v['source'],v['target']),'Clone CHI map into slot');self.refresh()
        f.submit(apply)
        ttk.Label(f.body,text='Copies terrain, door geometry and NPC routes into the target slot. Target origin and stable IDs survive. Undo restores it.',wraplength=460).grid(row=f.row,column=0,columnspan=2,padx=10,pady=10)
        return f
    def native_properties(self):
        value=data(self.document);scene=find(value['maps'],self.scene()['id']);f=Form(self,'Native map properties')
        f.field('name',scene['name']);f.field('origin_x',scene['origin'][0]);f.field('origin_y',scene['origin'][1])
        def apply(v):
            def edit(a):
                m=find(a['maps'],scene['id']);m['name']=v['name']
                if m['origin']!=[int(v['origin_x']),int(v['origin_y'])]:move_town(a,m['id'],int(v['origin_x']),int(v['origin_y']))
            change(self.document,edit,'Edit CHI town');self.refresh()
        f.submit(apply);return f
    def door_slots(self,index=0):
        from chi_audit import BUILDINGS
        scene=find(data(self.document)['maps'],self.scene()['id']);door=scene['entrances'][index];f=Form(self,'Native building entrance slots')
        f.field('slot',index,list(map(str,range(16))))
        f.field('name',door['name']);f.field('x',door['half'][0]);f.field('y',door['half'][1]);f.field('active',door['active'],['0','1'])
        choices=[f'{i} {name}' for i,name in enumerate(BUILDINGS)]+['255 Unassigned']
        f.field('room',choices[door['room']] if door['room']<26 else choices[-1],choices)
        def select(*_):
            d=scene['entrances'][int(f.values['slot'].get())]
            for k,v in dict(name=d['name'],x=d['half'][0],y=d['half'][1],active=d['active'],room=choices[d['room']] if d['room']<26 else choices[-1]).items():f.values[k].set(str(v))
        f.values['slot'].trace_add('write',select)
        def apply(v):
            def edit(a):
                d=find(a['maps'],scene['id'])['entrances'][int(v['slot'])]
                d.update(name=v['name'],half=[int(v['x']),int(v['y'])],active=int(v['active']),room=int(v['room'].split()[0]))
                if not d['active']:d['packed']=[0,0]
            change(self.document,edit,'Edit CHI building entrance');self.refresh()
        f.submit(apply);return f
    def npc_routes(self,index=0):
        value=data(self.document);scene=find(value['maps'],self.scene()['id']);f=Form(self,'Native town NPC routes')
        f.field('slot',index,list(map(str,range(8))))
        f.field('name',scene['npcs'][index]['name']);f.field('destination',scene['npcs'][index]['route'],list(map(str,range(8))))
        def select(*_):
            n=scene['npcs'][int(f.values['slot'].get())];f.values['name'].set(n['name']);f.values['destination'].set(str(n['route']))
        f.values['slot'].trace_add('write',select)
        def apply(v):
            def edit(a):
                n=find(a['maps'],scene['id'])['npcs'][int(v['slot'])];n.update(name=v['name'],route=int(v['destination']))
            change(self.document,edit,'Edit CHI NPC route');self.refresh()
        f.submit(apply)
        ttk.Label(f.body,text='The eight walkers travel between door slots 0–7. Route selects the next doorway after arriving. Citadel ruins and cache interiors have no roaming actors.',wraplength=450).grid(row=f.row,column=0,columnspan=2,padx=10,pady=8)
        return f
