"""Mission/campaign settings and stable unit roles in the shared workspace."""
import tkinter as tk
from tkinter import ttk
from chi_missions import catalogue,data,enable,update,unit
from editor_model import EditorError
from editor_session import scope_of,register,guard,apply_draft
from editor_workspace import view_window,open_view

class MissionView:
    def __init__(self,owner):
        owner.apply_form();self.owner=owner;self.scope=scope_of(owner);self.document=owner.document
        enable(self.document);self.catalog=catalogue(self.document);self.selected=None;self.initial=None;self.refreshing=False
        self.window=view_window(self,owner,'chi-missions','CHI missions and campaign')
        self.search=tk.StringVar();self.group=tk.StringVar(value='All settings');self.value=tk.StringVar();self.status=tk.StringVar()
        ttk.Label(self.window,text='Missions and campaign',style='Title.TLabel',padding=12).pack(anchor='w')
        intro=ttk.Label(self.window,text='Edit native missions, campaign settings and unit roles. Use Building scripts for dialogue, branches and story effects.',wraplength=500,padding=(12,0,12,8));intro.pack(fill='x')
        toolbar=ttk.Frame(self.window,padding=12);toolbar.pack(fill='x')
        groups=['All settings',*dict.fromkeys(p['group'] for p in self.catalog['parameters']),'Unit roles']
        ttk.Combobox(toolbar,textvariable=self.group,values=groups,state='readonly',width=26).pack(side='left',padx=(0,12))
        ttk.Label(toolbar,text='Find').pack(side='left');ttk.Entry(toolbar,textvariable=self.search,width=16).pack(side='left',fill='x',expand=True,padx=8)
        frame=ttk.Frame(self.window,padding=(12,0))
        self.table=ttk.Treeview(frame,columns=('value','description'),show='tree headings',selectmode='browse',height=8)
        for key,title,width in [('#0','Setting / role',260),('value','Value',100),('description','Description',250)]:self.table.heading(key,text=title);self.table.column(key,width=width,minwidth=80)
        frame.columnconfigure(0,weight=1);frame.rowconfigure(0,weight=1)
        scroll=ttk.Scrollbar(frame,command=self.table.yview);scroll.grid(row=0,column=1,sticky='ns')
        horizontal=ttk.Scrollbar(frame,command=self.table.xview,orient='horizontal');horizontal.grid(row=1,column=0,sticky='ew')
        self.table.configure(yscrollcommand=scroll.set,xscrollcommand=horizontal.set);self.table.grid(row=0,column=0,sticky='nsew')
        self.table.bind('<<TreeviewSelect>>',lambda _:guard(self,self.select))
        # Reserve editing controls before giving the table its remaining space.
        # A docked view can be much narrower/shorter than a separate window.
        status=ttk.Label(self.window,textvariable=self.status,wraplength=500,padding=8);status.pack(side='bottom',fill='x')
        self.details=ttk.Label(self.window,wraplength=500,padding=(12,0));self.details.pack(side='bottom',fill='x')
        row=ttk.Frame(self.window,padding=12);row.pack(side='bottom',fill='x')
        ttk.Label(row,text='Value').pack(side='left');self.entry=ttk.Combobox(row,textvariable=self.value,width=26);self.entry.pack(side='left',padx=8)
        for title,method in [('Apply',self.apply),('Restore default',self.reset),('Building scripts',self.scripts),('Native messages',self.messages)]:ttk.Button(row,text=title,command=lambda fn=method:guard(self,fn)).pack(side='left',padx=4)
        from editor_ui import flow_toolbar
        flow_toolbar(row);flow_toolbar(toolbar);frame.pack(fill='both',expand=True)
        def resize(event):
            if event.widget is self.window:
                for label in (intro,self.details,status):label.configure(wraplength=max(180,event.width-32))
        self.window.bind('<Configure>',resize,add='+')
        self.draft=register(self,pending=self.pending,apply=self.apply_pending,capture=self.capture_draft,restore=self.restore_draft,accept=self.accept_draft,priority=17)
        self.search.trace_add('write',lambda *_:guard(self,self.filter));self.group.trace_add('write',lambda *_:guard(self,self.filter));self.refresh()
    def capture_draft(self):return dict(selected=self.selected,value=self.value.get())
    def restore_draft(self,state):self.show_location(state.get('selected'));self.value.set(state['value'])
    def pending(self):return self.initial is not None and self.capture_draft()!=self.initial
    def apply_pending(self):
        if not self.selected or (self.initial and self.value.get()==self.initial['value']):return
        if self.selected.startswith('unit:'):unit(self.document,self.selected[5:],self.value.get())
        else:
            try:value=int(self.value.get())
            except ValueError as e:raise EditorError('Mission value must be an integer.') from e
            update(self.document,self.selected,value)
    def accept_draft(self):self.initial=self.capture_draft()
    def apply(self):apply_draft(self);self.refresh()
    def filter(self):
        if not self.refreshing:apply_draft(self);self.refresh()
    def reset(self):
        if not self.selected:return
        self.value.set('' if self.selected.startswith('unit:') else str(self.parameter()['default']));self.apply()
    def parameter(self):return next(p for p in self.catalog['parameters'] if p['id']==self.selected)
    def refresh(self):
        if self.refreshing:return
        self.refreshing=True
        try:
            self.table.delete(*self.table.get_children());v=data(self.document);query=self.search.get().casefold();group=self.group.get()
            for p in self.catalog['parameters']:
                if group not in ('All settings',p['group']) or query not in (p['id']+' '+p['label']+' '+p['group']).casefold():continue
                parent='group:'+p['group']
                if not self.table.exists(parent):self.table.insert('','end',iid=parent,text=p['group'],open=True)
                self.table.insert(parent,'end',iid=p['id'],text=p['id'],values=(v['parameters'].get(p['id'],p['default']),p['label']))
            if group in ('All settings','Unit roles'):
                parent='group:Unit roles';self.table.insert('','end',iid=parent,text='Unit roles',open=True)
                for u in self.catalog['units']:
                    if query not in (u['id']+' '+u['label']).casefold():continue
                    self.table.insert(parent,'end',iid='unit:'+u['id'],text=u['id'],values=(v.get('units',{}).get(u['id']) or u['default'],u['label']))
            if self.selected and self.table.exists(self.selected):self.table.selection_set(self.selected);self.fill()
            self.initial=self.capture_draft();self.status.set(f'{len(self.catalog["parameters"])} settings; {len(self.catalog["units"])} unit roles. Save and Play collect pending edits.')
        finally:self.refreshing=False
    def select(self):
        if self.refreshing:return
        selection=self.table.selection()
        if not selection or selection[0].startswith('group:') or selection[0]==self.selected:return
        try:apply_draft(self)
        except Exception:
            if self.selected:self.table.selection_set(self.selected)
            raise
        self.selected=selection[0];self.fill();self.initial=self.capture_draft()
    def fill(self):
        v=data(self.document)
        if self.selected.startswith('unit:'):
            role=self.selected[5:];u=next(u for u in self.catalog['units'] if u['id']==role)
            choices=['']+[f'native:{kind}.{i}' for kind,n in [('loan',3),('jenner',1),('commando',1),('encounter',3),('arena',11),('spectator',1),('urbanmech',1)] for i in range(n)]
            choices += [u['id'] for u in self.document.content.get('mechs',[]) if u.get('kind','mech')=='mech']
            self.entry.configure(values=choices);self.value.set(v.get('units',{}).get(role,''));self.details.configure(text=f'{u["label"]}. Empty keeps {u["default"]} (prison reward follows CHI services). Choose an original template or a mech from this project roster. Infantry missions use their own native person records.')
        else:
            p=self.parameter();self.entry.configure(values=list(range(p['minimum'],p['maximum']+1)) if p['maximum']-p['minimum']<=8 else [])
            self.value.set(str(v['parameters'].get(p['id'],p['default'])))
            self.details.configure(text=f'{p["label"]}. Range {p["minimum"]}–{p["maximum"]}; native default {p["default"]}. 0/1 switches mean off/on. Mission positions use half-tile movement coordinates; recovery/field cells use tiles. Text reference: {{mission:{p["id"]}}}.')
    def show_location(self,parameter):
        if parameter==self.selected and self.pending():
            if parameter and self.table.exists(parameter):self.table.see(parameter)
            return
        apply_draft(self);self.refreshing=True
        try:self.search.set('');self.group.set('Unit roles' if parameter and parameter.startswith('unit:') else 'All settings')
        finally:self.refreshing=False
        self.selected=parameter;self.refresh()
        if parameter and self.table.exists(parameter):self.table.see(parameter)
    def messages(self):
        from chi_editor import open_campaign
        self.apply();return open_campaign(self.owner)
    def scripts(self):
        from chi_bld_editor import open_scripts
        self.apply();return open_scripts(self.owner)
def open_missions(owner):return open_view(owner,'chi-missions',lambda:MissionView(owner))
