"""Native service settings and audited actions in the shared editor workspace."""
import copy
import tkinter as tk
from tkinter import ttk
from chi_services import catalogue,data,enable,update,stock
from editor_model import EditorError
from editor_session import scope_of,register,guard,apply_draft
from editor_workspace import view_window,open_view

class ServiceView:
    def __init__(self,owner):
        owner.apply_form();self.owner=owner;self.scope=scope_of(owner);self.document=owner.document
        enable(self.document);self.catalog=catalogue(self.document);self.selected=None;self.initial=None;self.refreshing=False
        self.window=view_window(self,owner,'chi-services','CHI services')
        self.search=tk.StringVar();self.value=tk.StringVar();self.status=tk.StringVar()
        ttk.Label(self.window,text='Native services',style='Title.TLabel',padding=12).pack(anchor='w')
        ttk.Label(self.window,text='Content settings retain native menus, transactions and saved continuations. Price tokens keep original text and payment linked. Custom dialogue remains yours to edit.',wraplength=780,padding=(12,0,12,8)).pack(fill='x')
        self.pages=ttk.Notebook(self.window);self.pages.pack(fill='both',expand=True,padx=12)
        settings=ttk.Frame(self.pages,padding=8);actions=ttk.Frame(self.pages,padding=8);broker=ttk.Frame(self.pages,padding=8)
        self.pages.add(settings,text='Service content');self.pages.add(actions,text='Native actions');self.pages.add(broker,text='Broker inventory')
        ttk.Entry(settings,textvariable=self.search).pack(fill='x',pady=(0,8))
        self.table=ttk.Treeview(settings,columns=('value','description'),show='tree headings',selectmode='browse',height=13)
        for key,title,width in [('#0','Setting',240),('value','Value',80),('description','Description',360)]:self.table.heading(key,text=title);self.table.column(key,width=width)
        scroll=ttk.Scrollbar(settings,command=self.table.yview);scroll.pack(side='right',fill='y');self.table.configure(yscrollcommand=scroll.set);self.table.pack(fill='both',expand=True)
        self.table.bind('<<TreeviewSelect>>',lambda _:guard(self,self.select))
        row=ttk.Frame(settings);row.pack(fill='x',pady=8);ttk.Label(row,text='Value').pack(side='left');ttk.Entry(row,textvariable=self.value,width=15).pack(side='left',padx=8)
        for title,method in [('Apply',self.apply),('Restore default',self.reset),('Edit native messages',self.messages),('Edit building scripts',self.scripts)]:ttk.Button(row,text=title,command=lambda fn=method:guard(self,fn)).pack(side='left',padx=4)
        from editor_ui import flow_toolbar
        flow_toolbar(row)
        self.details=ttk.Label(settings,wraplength=760);self.details.pack(fill='x')
        self.action_table=ttk.Treeview(actions,columns=('context','description'),show='headings',height=12)
        self.action_table.heading('context',text='Building slots');self.action_table.heading('description',text='Operation');self.action_table.column('context',width=150);self.action_table.column('description',width=600)
        self.action_table.pack(fill='both',expand=True);self.action_details=ttk.Label(actions,wraplength=780,padding=8);self.action_details.pack(fill='x')
        for a in self.catalog['actions']:self.action_table.insert('','end',iid=a['id'],values=(', '.join(map(str,a['buildings'])),str(a['action'])+' · '+a['name']))
        self.action_table.bind('<<TreeviewSelect>>',lambda _:self.show_action())
        ttk.Label(broker,text='Choose the units offered by the Updated broker. All units is the original Updated catalogue behavior. Prices and unit definitions remain in the roster editor.',wraplength=760).pack(fill='x',pady=(0,8))
        self.all_stock=tk.BooleanVar();ttk.Checkbutton(broker,text='All roster units',variable=self.all_stock).pack(anchor='w')
        self.units=tk.Listbox(broker,selectmode='extended',exportselection=False,height=14);self.units.pack(fill='both',expand=True,pady=8)
        self.unit_ids=[]
        for unit in self.document.content.get('mechs',[]):self.unit_ids.append(unit['id']);self.units.insert('end',unit.get('name',unit.get('label',unit['id'])))
        ttk.Button(broker,text='Apply broker inventory',command=lambda:guard(self,self.apply_stock)).pack(anchor='w')
        ttk.Label(self.window,textvariable=self.status,wraplength=780,padding=12).pack(fill='x')
        self.draft=register(self,pending=self.pending,apply=self.apply_pending,capture=self.capture_draft,restore=self.restore_draft,accept=self.accept_draft,priority=16)
        self.search.trace_add('write',lambda *_:guard(self,self.filter));self.refresh()

    def capture_draft(self):return dict(selected=self.selected,value=self.value.get(),all_stock=self.all_stock.get(),stock=list(self.units.curselection()))
    def restore_draft(self,state):
        self.show_location(state.get('selected'));self.value.set(state['value']);self.all_stock.set(state['all_stock']);self.units.selection_clear(0,'end')
        for i in state['stock']:self.units.selection_set(i)
    def pending(self):return self.initial is not None and self.capture_draft()!=self.initial
    def apply_pending(self):
        state=self.capture_draft()
        if self.selected and (not self.initial or state['value']!=self.initial['value']):
            try:value=int(self.value.get())
            except ValueError as e:raise EditorError('Service value must be an integer.') from e
            update(self.document,self.selected,value)
        if self.initial and (state['all_stock'],state['stock'])!=(self.initial['all_stock'],self.initial['stock']):stock(self.document,None if self.all_stock.get() else [self.unit_ids[i] for i in state['stock']])
    def accept_draft(self):self.initial=self.capture_draft()
    def apply(self):apply_draft(self);self.refresh()
    def filter(self):
        if not self.refreshing:apply_draft(self);self.refresh()
    def apply_stock(self):self.apply()
    def reset(self):
        if not self.selected:return
        self.value.set(str(next(p['default'] for p in self.catalog['parameters'] if p['id']==self.selected)));self.apply()
    def refresh(self):
        if self.refreshing:return
        self.refreshing=True
        try:
            self.table.delete(*self.table.get_children());v=data(self.document);query=self.search.get().casefold()
            for p in self.catalog['parameters']:
                if query not in (p['id']+' '+p['label']+' '+p['group']).casefold():continue
                group='group:'+p['group']
                if not self.table.exists(group):self.table.insert('','end',iid=group,text=p['group'],open=True)
                self.table.insert(group,'end',iid=p['id'],text=p['id'],values=(v['parameters'].get(p['id'],p['default']),p['label']))
            if self.selected and self.table.exists(self.selected):self.table.selection_set(self.selected);self.fill()
            self.all_stock.set('broker_stock' not in v);self.units.delete(0,'end');self.unit_ids=[]
            for unit in self.document.content.get('mechs',[]):self.unit_ids.append(unit['id']);self.units.insert('end',unit.get('name',unit.get('label',unit['id'])))
            for i,identity in enumerate(self.unit_ids):
                if identity in v.get('broker_stock',[]):self.units.selection_set(i)
            self.initial=self.capture_draft();self.status.set(f'{len(self.catalog["parameters"])} settings; 47 named actions with audited building contexts. Save and Play collect pending fields. Enabling/editing changes strict save identity.')
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
        p=next(p for p in self.catalog['parameters'] if p['id']==self.selected);self.value.set(str(data(self.document)['parameters'].get(p['id'],p['default'])))
        self.details.configure(text=f'{p["label"]}. Range {p["minimum"]}–{p["maximum"]}; original default {p["default"]}. Text reference: {{service:{p["id"]}}}. Stock 0 uses the native purchase-refused branch; edit its wording in CHI scripts.')
    def show_location(self,parameter):
        self.pages.select(2 if parameter is None else 0)
        if parameter==self.selected and self.pending():
            if parameter and self.table.exists(parameter):self.table.see(parameter)
            return
        apply_draft(self);self.refreshing=True
        try:self.search.set('')
        finally:self.refreshing=False
        self.selected=parameter;self.refresh()
        if parameter and self.table.exists(parameter):self.table.see(parameter)
    def show_action(self):
        selection=self.action_table.selection()
        if not selection:return
        a=next(a for a in self.catalog['actions'] if a['id']==selection[0])
        fields=[('Requires','requirements'),('Returns','outputs'),('Changes','mutations'),('Yields','yield'),('Errors','errors')]
        lines=[a['id']+' — '+a['consumer']]+[label+': '+a[key] for label,key in fields]
        self.action_details.configure(text='\n'.join(lines))
    def messages(self):
        from chi_editor import open_campaign
        self.apply();return open_campaign(self.owner)
    def scripts(self):
        from chi_bld_editor import open_scripts
        self.apply();return open_scripts(self.owner)

def open_services(owner):return open_view(owner,'chi-services',lambda:ServiceView(owner))
