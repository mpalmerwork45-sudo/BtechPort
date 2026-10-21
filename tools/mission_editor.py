"""Named mission state and map regions, using the ordinary document history."""
import copy
import tkinter as tk
from tkinter import ttk
from adventure_editing import new_id
from editor_model import EditorError
from editor_session import guard
from editor_recovery import recoverable_forms
from editor_workspace import view_window,open_view

STATES=('inactive','active','complete','failed')


@recoverable_forms
class MissionEditor:
    def __init__(self,owner):
        self.owner=owner;self.document=owner.document
        self.window=view_window(self,owner,'mission','Mission state')
        ttk.Label(self.window,text='Mission state, combat groups and timed hooks. Every definition shares project Save, Undo and validation.',
                  padding=12,wraplength=700).pack(fill='x')
        # Reserve actions before expandable lists so short workspaces keep
        # the journal and the last hook reachable.
        ttk.Button(self.window,text='Objectives and journal',command=lambda:owner.event_graph().objectives()).pack(side='bottom',anchor='w',padx=12,pady=8)
        self.tabs=ttk.Notebook(self.window);self.tabs.pack(fill='both',expand=True)
        self.listings={}
        for collection,title in (('regions','Regions'),('variables','Variables / counters'),('combat_groups','Combat groups / escorts'),('combat_hooks','Combat hooks / timers')):
            page=ttk.Frame(self.tabs,padding=10);self.tabs.add(page,text=title)
            table=ttk.Frame(page)
            listing=ttk.Treeview(table,columns=('name','detail'),show='headings',selectmode='browse')
            listing.heading('name',text='Name');listing.heading('detail',text='Definition')
            listing.column('name',width=190);listing.column('detail',width=430)
            scroll=ttk.Scrollbar(table,command=listing.yview);scroll.pack(side='right',fill='y')
            listing.configure(yscrollcommand=scroll.set)
            listing.pack(fill='both',expand=True);self.listings[collection]=listing
            listing.bind('<Double-1>',lambda _,c=collection:guard(self,lambda:self.edit(c)))
            bar=ttk.Frame(page,padding=(0,10));bar.pack(side='bottom',fill='x')
            table.pack(fill='both',expand=True)
            for label,callback in (
                ('New',lambda c=collection:self.edit(c,new=True)),
                ('Edit',lambda c=collection:self.edit(c)),
                ('Delete / usages',lambda c=collection:self.delete(c))):
                ttk.Button(bar,text=label,command=lambda f=callback:guard(self,f)).pack(side='left',padx=3)
            if collection=='regions':
                ttk.Button(bar,text='Show on map',command=lambda:guard(self,self.show_map)).pack(side='left',padx=3)
                ttk.Button(bar,text='Draw region',command=lambda:self.draw_region()).pack(side='left',padx=3)
        self.refresh()

    def refresh(self):
        for collection,listing in self.listings.items():
            selected=listing.selection();listing.delete(*listing.get_children())
            for value in self.document.adventure.get(collection,[]):
                from combat_mission_editor import description
                detail=(description(collection,value) if collection.startswith('combat_') else f"{value['map']}  {value['rect']}  {value['repeat']}" if collection=='regions' else
                        f"{value['type']}  initially {value['initial']}"+(f" / max {value['maximum']}" if value['type']=='counter' else ''))
                listing.insert('','end',iid=value['id'],values=(value.get('name',value['id']),detail))
            for identity in selected:
                if listing.exists(identity):listing.selection_set(identity)

    def edit(self,collection,new=False,rect=None,map_id=None,identity=None):
        if collection.startswith('combat_'):
            from combat_mission_editor import edit
            return edit(self,collection,new,identity)
        from adventure_editor import Form
        listing=self.listings[collection];a=self.document.adventure
        identity=identity or (listing.selection()[0] if listing.selection() else None)
        if not new and not identity:return
        old=next((v for v in a.get(collection,[]) if v['id']==identity),None) if not new else None
        if not new and old is None:raise EditorError('This mission object no longer exists.')
        record=old or dict(id=new_id(self.document,collection,'region' if collection=='regions' else 'variable'),name='New region' if collection=='regions' else 'New counter')
        f=Form(self,'Mission region' if collection=='regions' else 'Mission variable')
        f.field('id',record['id']);f.field('name',record['name'])
        if collection=='regions':
            f.field('map',record.get('map',map_id or self.owner.scene()['id']),[m['id'] for m in a['maps']])
            for key,value in zip(('x','y','width','height'),record.get('rect',rect or [0,0,1,1])):f.field(key,value)
            f.field('repeat',record.get('repeat','always'),['once','always'])
            for key in ('enter','leave'):f.field(key,record.get(key,'none'),['none']+[e['id'] for e in a['events']])
        else:
            f.field('type',record.get('type','counter'),['boolean','counter'])
            f.field('initial',record.get('initial',0));f.field('maximum',record.get('maximum',100),label='Counter maximum (ignored for boolean)')
        def apply(values):
            if old and values['id']!=old['id']:raise EditorError('Existing IDs stay stable. Create a new definition to use a different ID.')
            result={k:values[k] for k in ('id','name')}
            if collection=='regions':
                result.update(map=values['map'],rect=[int(values[k]) for k in ('x','y','width','height')],repeat=values['repeat'])
                result.update({k:values[k] for k in ('enter','leave') if values[k]!='none'})
            else:
                result.update(type=values['type'],initial=int(values['initial']))
                if values['type']=='counter':result['maximum']=int(values['maximum'])
            data=copy.deepcopy(self.document.adventure);items=data.setdefault(collection,[])
            if old:items[next(i for i,v in enumerate(items) if v['id']==old['id'])]=result
            else:items.append(result)
            # A failed bound/reference leaves the draft visible and rolls the
            # document back through the same transaction as other editor forms.
            self.document.replace_adventure(data);self.document.validate()
            self.owner.refresh();self.refresh();listing.selection_set(result['id'])
        f.submit(apply);return f

    def delete(self,collection):
        selected=self.listings[collection].selection()
        if selected:
            from editor_dependencies import dialog
            return dialog(self,selected[0],delete=True)

    def show_map(self):
        selected=self.listings['regions'].selection()
        if not selected:return
        region=next(r for r in self.document.adventure['regions'] if r['id']==selected[0])
        maps=self.owner;maps.map_choice.current(next(i for i,m in enumerate(maps.adventure['maps']) if m['id']==region['map']));maps.change_map()
        x,y,w,h=region['rect'];maps.selection_rect=(x,y,x+w-1,y+h-1)
        maps.tabs.select(maps.map_tab);maps.window.lift();maps.draw()
        size=int(maps.zoom.get());scene=maps.scene()
        maps.canvas.xview_moveto(max(0,(x*size-maps.canvas.winfo_width()/3)/(len(scene['rows'][0])*size)))
        maps.canvas.yview_moveto(max(0,(y*size-maps.canvas.winfo_height()/3)/(len(scene['rows'])*size)))

    def draw_region(self):
        self.owner.tabs.select(self.owner.map_tab);self.owner.window.lift();self.owner.tool.set('Region')


def open_missions(owner):
    return open_view(owner,'mission',lambda:MissionEditor(owner))
