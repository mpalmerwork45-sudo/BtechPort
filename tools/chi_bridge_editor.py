"""Quests and native doorway/service bindings in the shared editor workspace."""
import copy
from tkinter import ttk
from adventure_editor import AdventureEditor,Form
from editor_model import EditorError
from editor_session import scope_of,guard
from editor_workspace import open_view
from editor_recovery import recoverable_forms
from chi_bridge import QuestDocument,enable,data,events,upsert,put,example

class Parent:
    def __init__(self,owner):self.owner=owner;self.document=QuestDocument(owner.document)
    def __getattr__(self,key):return getattr(self.owner,key)

@recoverable_forms
class QuestEditor(AdventureEditor):
    view_kind='chi-quests'
    view_title='CHI quests'
    def __init__(self,owner):
        owner.apply_form();enable(owner.document)
        super().__init__(Parent(owner))
        self.tabs.add(self.event_tab,text='Quest events')
        bar=ttk.Frame(self.window,padding=6);bar.pack(fill='x',before=self.tabs)
        for title,callback in [('Doorway bindings',self.bindings),('Native service calls',self.calls),('Add example quest',self.add_example),('Event graph',self.event_graph)]:
            ttk.Button(bar,text=title,command=lambda f=callback:guard(self,f)).pack(side='left',padx=3)
        self.status.set('Optional quests over the native campaign. Bind a native doorway or call from a BLD. Quest start settings are editor defaults; Play keeps the original crew and campaign.')
        self.tabs.select(self.event_tab)
    def play_here(self):
        raise EditorError('Enter this quest through its native doorway or BLD call. Play starts the native campaign and preserves its party and story.')
    def add_example(self):
        self.apply_pending();example(self.document.base);self.refresh()
    def bindings(self,identity=None):
        from chi_spatial import data as spatial
        b=data(self.document);maps=spatial(self.document.base)['maps'][:13];rows=b['entrances'];f=Form(self,'Quest doorway bindings')
        selected=next((v for v in rows if v['id']==identity),rows[0] if rows else dict(id='quest:door',map=maps[0]['id'],entrance=8,event=self.adventure['events'][0]['id']))
        f.field('binding',selected['id'],[v['id'] for v in rows]+['New'])
        f.field('id',selected['id']);f.field('map',selected['map'],[m['id'] for m in maps]);f.field('entrance',selected['entrance'],[str(i) for i in range(12)])
        f.field('event',selected['event'],[e['id'] for e in self.adventure['events']])
        def choose(*_):
            row=next((v for v in rows if v['id']==f.values['binding'].get()),None)
            if row:
                for key in ('id','map','entrance','event'):f.values[key].set(str(row[key]))
            else:f.values['id'].set('quest:new-door')
        f.values['binding'].trace_add('write',choose)
        def apply(v):upsert(self.document.base,'entrances',dict(id=v['id'],map=v['map'],entrance=int(v['entrance']),event=v['event']));self.refresh()
        f.submit(apply)
        ttk.Label(f.body,text='Place or activate the door in CHI maps first. Slot is the native Door slots number, not a tile coordinate. This binding replaces only that doorway’s BLD entry.',wraplength=450).grid(row=f.row,column=0,columnspan=2,padx=10,pady=10)
        def remove():
            value=data(self.document);value['entrances']=[v for v in value['entrances'] if v['id']!=f.values['binding'].get()];put(self.document.base,value);f.window.destroy();self.refresh()
        ttk.Button(f.footer,text='Remove binding',command=lambda:guard(self,remove)).pack(side='left',padx=8)
        return f
    def calls(self,identity=None):
        from chi_bld import data as sources,find
        p=find(sources(self.document),'chi:bld-comstar');labels=[n['id'] for n in p['nodes'] if n['op']!='data']
        entries=[n['id'] for n in p['nodes'] if n['op']=='native' and n['action'] in (7,8)]
        rows=data(self.document)['native_calls'];f=Form(self,'Native service calls')
        selected=next((v for v in rows if v['id']==identity),rows[0] if rows else dict(id='quest:bank',program=p['id'],entry=entries[0],**{'return':'chi:comstar-02cf'}))
        f.field('call',selected['id'],[v['id'] for v in rows]+['New']);f.field('id',selected['id'])
        f.field('program',selected['program'],[p['id']]);f.field('entry',selected['entry'],entries);f.field('return',selected['return'],labels)
        def choose(*_):
            row=next((v for v in rows if v['id']==f.values['call'].get()),None)
            if row:
                for key in ('id','program','entry','return'):f.values[key].set(row[key])
            else:f.values['id'].set('quest:new-call')
        f.values['call'].trace_add('write',choose)
        def apply(v):upsert(self.document.base,'native_calls',{k:v[k] for k in ('id','program','entry','return')});self.refresh()
        f.submit(apply)
        ttk.Label(f.body,text='Supported native adapters: ComStar buy/sell shares, including their original amount entry and receipt. Return after the receipt wait. For new repair/heal/rearm buildings use the authored service events. Training, arena, theft and cache retain their native scene contracts.',wraplength=460).grid(row=f.row,column=0,columnspan=2,padx=10,pady=10)
        def remove():
            value=data(self.document);value['native_calls']=[v for v in value['native_calls'] if v['id']!=f.values['call'].get()];put(self.document.base,value);f.window.destroy();self.refresh()
        ttk.Button(f.footer,text='Remove call',command=lambda:guard(self,remove)).pack(side='left',padx=8)
        return f
    def show_location(self,identity):
        if self.event_pending and self.event_id==identity:self.tabs.select(self.event_tab);self.window.lift();return
        self.apply_pending()
        if any(v['id']==identity for v in data(self.document)['entrances']):return self.bindings(identity)
        if any(v['id']==identity for v in data(self.document)['native_calls']):return self.calls(identity)
        e=next((e for e in self.adventure['events'] if e['id']==identity),None)
        if e:self.event_id=identity;self.refresh_events();self.render_event_form(copy.deepcopy(e));self.tabs.select(self.event_tab)
        m=next((i for i,m in enumerate(self.adventure['maps']) if m['id']==identity),None)
        if m is not None:self.scene_index=m;self.refresh();self.tabs.select(self.map_tab)

def open_quests(owner):
    scope=scope_of(owner)
    if scope is not None:owner=scope.owner
    return open_view(owner,'chi-quests',lambda:QuestEditor(owner))
