"""Read-only, source-linked coverage view for retained native campaign traces."""
from pathlib import Path
import tkinter as tk
from tkinter import ttk,filedialog
from editor_model import EditorError
from editor_session import guard,scope_of
from editor_workspace import open_view,view_window


def open_coverage(owner):return open_view(owner,'chi-coverage',lambda:CoverageView(owner))


class CoverageView:
    def __init__(self,owner):
        self.owner=owner;self.document=owner.document;self.scope=scope_of(owner);self.report=None;self.targets={};self.paths=[]
        self.window=view_window(self,owner,'chi-coverage','CHI script coverage');self.status=tk.StringVar(value='Load a BLD trace from a Play snapshot or headless replay.')
        ttk.Label(self.window,text='Native script coverage',style='Title.TLabel',padding=12).pack(anchor='w')
        bar=ttk.Frame(self.window,padding=(12,0,12,8));bar.pack(fill='x')
        for title,method in [('Open traces',self.choose),('Last Play trace',self.last_play),('Open source',self.source)]:
            ttk.Button(bar,text=title,command=lambda fn=method:guard(self,fn)).pack(side='left',padx=(0,6))
        information=ttk.Label(self.window,text='Observed means executed, not verified correct. Unvisited branches remain untested. Native C internals are unknown; service counts show entries and returns at BLD boundaries.',wraplength=650,padding=12)
        information.pack(fill='x')
        status=ttk.Label(self.window,textvariable=self.status,wraplength=650,padding=12);status.pack(side='bottom',fill='x')
        host=ttk.Frame(self.window);host.pack(fill='both',expand=True,padx=12,pady=(0,8))
        self.table=ttk.Treeview(host,columns=('instructions','branches','native'),show='tree headings',selectmode='browse')
        for key,title,width in [('#0','Building / source label',300),('instructions','Instructions',100),('branches','Branches',100),('native','Native enters / returns',150)]:
            self.table.heading(key,text=title);self.table.column(key,width=width,minwidth=80)
        sy=ttk.Scrollbar(host,command=self.table.yview);sy.pack(side='right',fill='y');self.table.configure(yscrollcommand=sy.set)
        sx=ttk.Scrollbar(host,orient='horizontal',command=self.table.xview);sx.pack(side='bottom',fill='x');self.table.configure(xscrollcommand=sx.set)
        self.table.pack(fill='both',expand=True);self.table.bind('<Double-1>',lambda _:guard(self,self.source));self.table.bind('<Return>',lambda _:guard(self,self.source))
        from chi_editor import wrap_labels
        wrap_labels(self.window,[information,status])

    def choose(self):
        paths=filedialog.askopenfilenames(title='Open native BLD traces',filetypes=[('BLD traces','*.jsonl'),('All files','*')],parent=self.window.winfo_toplevel())
        if paths:self.load(paths)

    def last_play(self):
        workspace=getattr(self.window,'workspace',None);folder=getattr(getattr(workspace,'play_session',None),'folder',None)
        if folder is None or not (folder/'bld.jsonl').is_file():raise EditorError('Run Play with an imported campaign first, or choose an existing bld.jsonl trace.')
        self.load([folder/'bld.jsonl'])

    def load(self,paths):
        from editor_tasks import snapshot
        from chi_coverage import coverage
        candidate=snapshot(self.scope);revision=self.document.revision;self.paths=[Path(p) for p in paths]
        paths=list(self.paths);self.status.set('Reading native execution and matching the exact content revision...')
        def ready(result):
            if self.document.revision!=revision:
                self.status.set('Project changed while coverage was loading. Reload traces for the current revision.');return
            self.show(result)
        workspace=getattr(self.window,'workspace',None)
        if workspace:workspace.tasks.submit('Read CHI script coverage',self,lambda cancel:coverage(candidate,paths,cancel),ready)
        else:ready(coverage(candidate,paths))

    def show(self,result):
        self.report=result;self.targets={};self.table.delete(*self.table.get_children())
        for p in result['programs']:
            def ratio(counts):return str(counts['observed'])+' / '+str(counts['declared'])
            parent=self.table.insert('','end',text=p['name'],values=(ratio(p['instructions']),ratio(p['branches']),''));self.targets[parent]=(p['id'],None)
            for n in p['nodes']:
                native=n.get('native');branches=n['branches']
                item=self.table.insert(parent,'end',text=n['id']+' ('+n['op']+')',values=(n['executions'],str(sum(bool(b['executions']) for b in branches))+' / '+str(len(branches)) if branches else '',
                    f"{native['entered']} / {native['returned']}" if native else ''));self.targets[item]=(p['id'],n['id'])
                for edge in branches:
                    child=self.table.insert(item,'end',text=str(edge['choice'])+' -> '+str(edge['target']),values=('',edge['executions'],''));self.targets[child]=(p['id'],n['id'])
        unknown=sum(result['unresolved_observations'].values())
        self.status.set(f"{result['observations']} observations, {len(result['faults'])} faults, {unknown} unresolved observations. Double-click a row to open its source.")

    def source(self):
        from chi_bld_editor import open_scripts
        selected=self.table.selection()
        if selected:open_scripts(self.owner).show_location(*self.targets[selected[0]])
