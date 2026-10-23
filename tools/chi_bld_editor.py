"""Workspace BLD authoring with typed fields and ordinary recoverable drafts."""
from __future__ import annotations
import copy
import tkinter as tk
from tkinter import ttk
from chi_bld import data,enable,find,put,insert,remove,compiled,describe,DESCRIPTIONS,FIELDS,decode
from editor_model import EditorError
from editor_session import scope_of,register,guard,apply_draft
from editor_workspace import view_window,open_view
from editor_recovery import recoverable_forms


def shown(text):
    for value in (6,14,15):text=text.replace(chr(value),'{color:'+str(value)+'}')
    return text.replace('\r','\n')


def native(text):
    for value in (6,14,15):text=text.replace('{color:'+str(value)+'}',chr(value))
    return text.replace('\n','\r')


@recoverable_forms
class BldView:
    def __init__(self,owner):
        owner.apply_form();self.owner=owner;self.scope=scope_of(owner);self.document=owner.document
        enable(self.document)
        self.window=view_window(self,owner,'chi-bld','CHI scripts')
        self.selected=None;self.original=None;self.fields={};self.targets=[];self.text=None;self.refreshing=False
        self.program=tk.StringVar(value=data(self.document)['programs'][0]['id']);self.search=tk.StringVar();self.status=tk.StringVar()
        ttk.Label(self.window,text='Native building scripts',style='Title.TLabel',padding=(12,10)).pack(anchor='w')
        bar=ttk.Frame(self.window,padding=(12,0,12,8));bar.pack(fill='x')
        ttk.Label(bar,text='Building').pack(side='left',padx=(0,8))
        self.program_picker=ttk.Combobox(bar,state='readonly',width=30);self.program_picker.pack(side='left')
        self.program_picker.bind('<<ComboboxSelected>>',lambda _:guard(self,self.change_program))
        ttk.Label(bar,text='Find').pack(side='left',padx=(16,6));ttk.Entry(bar,textvariable=self.search,width=24).pack(side='left',fill='x',expand=True)
        self.search.trace_add('write',lambda *_:guard(self,self.refresh))
        split=ttk.Panedwindow(self.window,orient='horizontal');split.pack(fill='both',expand=True,padx=12)
        left=ttk.Frame(split);right=ttk.Frame(split);split.add(left,weight=3);split.add(right,weight=2)
        self.table=ttk.Treeview(left,columns=('op','description'),show='tree headings',selectmode='browse')
        for key,title,width in [('#0','Page / label',150),('op','Operation',100),('description','Description',260)]:
            self.table.heading(key,text=title);self.table.column(key,width=width,minwidth=70)
        scroll=ttk.Scrollbar(left,command=self.table.yview);scroll.pack(side='right',fill='y');self.table.configure(yscrollcommand=scroll.set)
        self.table.pack(fill='both',expand=True);self.table.bind('<<TreeviewSelect>>',lambda _:guard(self,self.select))
        self.description=ttk.Label(right,wraplength=290,padding=(10,4));self.description.pack(fill='x')
        self.canvas=tk.Canvas(right,highlightthickness=0,width=310);self.canvas.pack(side='left',fill='both',expand=True)
        scroll=ttk.Scrollbar(right,command=self.canvas.yview);scroll.pack(side='right',fill='y');self.canvas.configure(yscrollcommand=scroll.set)
        self.form=ttk.Frame(self.canvas,padding=10);item=self.canvas.create_window(0,0,window=self.form,anchor='nw')
        self.form.columnconfigure(0,weight=1)
        self.form.bind('<Configure>',lambda _:self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.bind('<Configure>',lambda e:self.canvas.itemconfigure(item,width=e.width))
        buttons=ttk.Frame(self.window,padding=12);buttons.pack(fill='x')
        for title,method in [('Apply instruction',self.apply),('Clone',self.clone),('Insert',self.new),('Remove inserted',self.delete),
                             ('Restore original',self.reset),('Go to target',self.jump),('Enable sources',self.enable_sources),('Refresh',self.refresh)]:
            ttk.Button(buttons,text=title,command=lambda fn=method:guard(self,fn)).pack(side='left',padx=(0,6))
        from editor_ui import flow_toolbar
        flow_toolbar(buttons)
        ttk.Label(self.window,textvariable=self.status,padding=(12,0,12,10),wraplength=720).pack(fill='x')
        self.initial=None
        self.draft=register(self,pending=self.pending,apply=self.apply_pending,capture=self.capture_draft,
            restore=self.restore_draft,accept=self.accept_draft,priority=15)
        self.refresh()

    def capture_draft(self):
        return dict(program=self.program.get(),selected=self.selected,original=copy.deepcopy(self.original),
            values={k:v.get() for k,v in self.fields.items()},targets=[v.get() for v in self.targets],
            text=self.text.get('1.0','end-1c') if self.text is not None else None)

    def restore_draft(self,state):
        self.program.set(state['program']);self.selected=state['selected'];self.original=copy.deepcopy(state['original'])
        if self.original:
            self.render(self.original)
            if 'targets' in self.original and len(state['targets'])!=len(self.targets):
                original=copy.deepcopy(self.original);initial=self.initial;layout=copy.deepcopy(original);layout['targets']=state['targets']
                self.render(layout);self.original=original;self.initial=initial
        for k,value in state['values'].items():self.fields[k].set(value)
        for variable,value in zip(self.targets,state['targets']):variable.set(value)
        if self.text is not None:self.text.delete('1.0','end');self.text.insert('1.0',state['text'])

    def pending(self):
        return self.initial is not None and self.capture_draft()!=self.initial

    def apply_pending(self):
        if not self.pending():return
        record=copy.deepcopy(self.original)
        for key,variable in self.fields.items():
            value=variable.get()
            if key=='note':
                if value:record[key]=value
                else:record.pop(key,None)
            elif key=='target':record[key]=value
            else:
                try:record[key]=int(value)
                except ValueError as error:raise EditorError(key+' must be an integer.') from error
        if self.targets:record['targets']=[v.get() for v in self.targets]
        if self.text is not None:record['text']=native(self.text.get('1.0','end-1c'))
        value=data(self.document);p=find(value,self.program.get());index=next(i for i,n in enumerate(p['nodes']) if n['id']==self.selected)
        p['nodes'][index]=record;put(self.document,value)

    def accept_draft(self):
        if self.selected:
            current=find(data(self.document),self.program.get(),self.selected);self.render(current)

    def apply(self):
        apply_draft(self);self.refresh()

    def change_program(self):
        programs=data(self.document)['programs'];index=self.program_picker.current()
        try:apply_draft(self)
        except Exception:
            self.program_picker.current(next(i for i,p in enumerate(programs) if p['id']==self.program.get()));raise
        self.program.set(programs[index]['id']);self.selected=None;self.original=None;self.initial=None;self.refresh()

    def enable_sources(self):
        enable(self.document);self.refresh()

    def refresh(self):
        if self.refreshing or self.pending():return
        if self.scope.document is not self.document:raise EditorError('The project changed; reopen CHI scripts.')
        self.refreshing=True
        try:
            programs=data(self.document)['programs'];self.program_picker.configure(values=[p['name']+' - '+p['resource'] for p in programs])
            index=next(i for i,p in enumerate(programs) if p['id']==self.program.get());self.program_picker.current(index);p=programs[index]
            self.table.delete(*self.table.get_children());query=self.search.get().casefold();group=None;pages=0;first=None
            for node in p['nodes']:
                if node['op']=='clear' or group is None:
                    pages+=1;group='page-'+str(pages)
                    self.table.insert('','end',iid=group,text='Page / section '+str(pages),open=True)
                description=describe(node)
                if query and query not in (node['id']+' '+node['op']+' '+description+' '+node.get('note','')).casefold():continue
                self.table.insert(group,'end',iid=node['id'],text=node['id'].split(':',1)[-1],values=(node['op'],node.get('note') or description))
                if first is None:first=node['id']
            self.locations={n['id']:n for n in compiled(self.document,p['id'])['nodes']} if self.document.manifest.get('chi_scripts') else {}
            if not self.selected or not self.table.exists(self.selected):self.selected=first
            if self.selected:
                self.table.selection_set(self.selected);self.render(find(data(self.document),p['id'],self.selected))
            self.status.set(f'{len(p["nodes"])} records. Original bytes/labels are retained. Apply adds Undo; Save project persists. Service/mission settings remain C4.2/C4.3.')
            if not self.document.manifest.get('chi_scripts'):self.status.set('Source editing was undone. Redo or Enable sources restores it; original BLD playback is active.')
        finally:self.refreshing=False

    def select(self):
        if self.refreshing:return
        selection=self.table.selection()
        if not selection or selection[0].startswith('page-') or selection[0]==self.selected:return
        try:apply_draft(self)
        except Exception:
            if self.selected:self.table.selection_set(self.selected)
            raise
        self.selected=selection[0];self.render(find(data(self.document),self.program.get(),self.selected))

    def render(self,node):
        self.original=copy.deepcopy(node);self.fields={};self.targets=[];self.text=None
        for child in self.form.winfo_children():child.destroy()
        self.description.configure(text=DESCRIPTIONS[node['op']]+('\n'+describe(node) if node['op']=='native' else ''))
        p=find(data(self.document),self.program.get());labels=[n['id'] for n in p['nodes'] if n['op']!='data'];row=0
        def label(text):
            nonlocal row
            ttk.Label(self.form,text=text).grid(row=row,column=0,sticky='w',pady=(8,3));row+=1
        for key,kind in FIELDS[node['op']].items():
            label(key.replace('_',' ').title())
            if kind=='text':
                self.text=tk.Text(self.form,wrap='word',height=10,width=28,undo=True)
                self.text.grid(row=row,column=0,sticky='nsew');self.text.insert('1.0',shown(node['text']));row+=1
                ttk.Label(self.form,text='Line breaks use native CR. Colour markers: {color:6}, {color:14}, {color:15}.',wraplength=270).grid(row=row,column=0,sticky='w');row+=1
            elif kind=='bytes':
                ttk.Label(self.form,text=str(node['original_size'])+' original bytes retained, including unreachable code/padding.',wraplength=270).grid(row=row,column=0,sticky='w');row+=1
            elif kind=='targets':
                for i,target in enumerate(node['targets']):
                    ttk.Label(self.form,text='Choice / signed index '+str(i)).grid(row=row,column=0,sticky='w');row+=1
                    v=tk.StringVar(value=target);self.targets.append(v)
                    ttk.Combobox(self.form,textvariable=v,values=labels,width=28).grid(row=row,column=0,sticky='ew');row+=1
                controls=ttk.Frame(self.form);controls.grid(row=row,column=0,sticky='ew');row+=1
                for title,delta in [('Add destination',1),('Remove destination',-1)]:
                    ttk.Button(controls,text=title,command=lambda d=delta:guard(self,lambda:self.resize_targets(d))).pack(side='left')
            else:
                v=tk.StringVar(value=str(node[key]));self.fields[key]=v
                choices=labels if kind=='target' else list(map(str,kind)) if node['op'] in ('font','scene','menu') else list(map(str,range(kind[0],kind[-1]+1))) if kind[-1]<50 else None
                control=ttk.Combobox(self.form,textvariable=v,values=choices,width=28) if choices else ttk.Entry(self.form,textvariable=v,width=28)
                control.grid(row=row,column=0,sticky='ew');row+=1
        label('Author note');v=tk.StringVar(value=node.get('note',''));self.fields['note']=v;ttk.Entry(self.form,textvariable=v).grid(row=row,column=0,sticky='ew');row+=1
        location=getattr(self,'locations',{}).get(node['id'],{});origin='new' if 'origin' not in node else f'{node["origin"]:04x}'
        source=next((v['file'] for v in self.document.source.locations if v['id']==p['id']),'chi-scripts.json') if self.document.source else 'chi-scripts.json'
        ttk.Label(self.form,text='Original: '+origin+'  Compiled: '+format(location.get('offset',0),'04x')+'\n'+source+'\n'+node['id'],wraplength=270).grid(row=row,column=0,sticky='w',pady=12)
        self.initial=self.capture_draft()

    def fresh_id(self):
        used={n['id'] for p in data(self.document)['programs'] for n in p['nodes']};i=1
        while 'edit:instruction-'+str(i) in used:i+=1
        return 'edit:instruction-'+str(i)

    def resize_targets(self,delta):
        values=[v.get() for v in self.targets]
        if not 1<=len(values)+delta<=128:raise EditorError('Use 1..128 destinations; menus must match their selector count before Apply.')
        state=self.capture_draft();original=copy.deepcopy(self.original);initial=self.initial
        record=copy.deepcopy(original);record['targets']=values+[values[-1]] if delta>0 else values[:-1]
        self.render(record)
        self.original=original;self.initial=initial
        for key,value in state['values'].items():self.fields[key].set(value)
        if self.text is not None:self.text.delete('1.0','end');self.text.insert('1.0',state['text'])

    def clone(self):
        self.apply()
        if not self.selected:return
        p=find(data(self.document),self.program.get());current=find(data(self.document),p['id'],self.selected)
        if current['op']=='data':raise EditorError('Select an executable label to insert after.')
        node=copy.deepcopy(find(data(self.document),self.program.get(),self.selected))
        if node['op']=='data':raise EditorError('Preserved byte regions cannot be cloned as executable code.')
        node.pop('origin',None);node.pop('original_size',None);node['id']=self.fresh_id()
        insert(self.document,self.program.get(),self.selected,node);self.selected=node['id'];self.refresh()

    def new(self):
        self.apply()
        if not self.selected:return
        p=find(data(self.document),self.program.get());current=find(data(self.document),p['id'],self.selected)
        if current['op']=='data':raise EditorError('Select an executable label to insert after.')
        index=p['nodes'].index(current);next_label=next((n['id'] for n in p['nodes'][index+1:] if n['op']!='data'),self.selected)
        from adventure_editor import Form
        form=Form(self,'Insert BLD instruction');form.field('op','text',[k for k in FIELDS if k!='data'])
        form.field('id',self.fresh_id())
        def apply(value):
            op=value['op'];node=dict(id=value['id'],op=op)
            for key,kind in FIELDS[op].items():
                node[key]='' if kind=='text' else next_label if kind=='target' else [next_label]*(3 if op=='menu' else 1) if kind=='targets' else kind[0]
            if op=='menu':node['menu']=7
            if op=='native':node['action']=next((n['action'] for n in p['nodes'] if n['op']=='native'),1)
            if op=='animation':node['kind']=next((n['kind'] for n in p['nodes'] if n['op']=='animation'),0)
            insert(self.document,self.program.get(),self.selected,node);self.selected=node['id'];self.refresh()
        form.submit(apply);return form

    def delete(self):
        self.apply()
        if self.selected:remove(self.document,self.program.get(),self.selected);self.selected=None;self.refresh()

    def reset(self):
        if not self.selected:return
        node=find(data(self.document),self.program.get(),self.selected)
        if 'origin' not in node:raise EditorError('This is an inserted instruction; use Remove inserted.')
        p=find(data(self.document),self.program.get());base=decode(self.document.snapshot['chi/'+p['resource']],p['resource'][:-4])
        old=next(n for n in base['nodes'] if n['origin']==node['origin']);old['id']=node['id']
        value=data(self.document);target=find(value,p['id']);target['nodes'][next(i for i,n in enumerate(target['nodes']) if n['id']==self.selected)]=old
        self.scope.transact(lambda:put(self.document,value,'Restore original BLD instruction'),subset=[])
        self.render(old);self.refresh()

    def jump(self):
        self.apply()
        node=find(data(self.document),self.program.get(),self.selected);target=node.get('target') or next(iter(node.get('targets',[])),None)
        if target:self.show_location(self.program.get(),target)

    def show_location(self,program,label=None):
        if self.pending() and program==self.program.get() and (not label or label==self.selected):self.window.lift();return
        self.apply();self.program.set(program);self.selected=label;self.initial=None;self.search.set('');self.refresh()
        if self.selected:self.table.see(self.selected)
        self.window.lift()


def open_scripts(owner):
    return open_view(owner,'chi-bld',lambda:BldView(owner))
