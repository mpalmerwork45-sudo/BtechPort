"""Source ownership and build controls inside the ordinary editor workspace."""
from pathlib import Path
import tkinter as tk
from tkinter import ttk,filedialog,simpledialog
from campaign_source import CampaignSource,convert,build
from editor_model import EditorError
from editor_session import scope_of,guard
from editor_tasks import snapshot,signature
from editor_workspace import view_window,open_view,workspace_of
from editor_ui import flow_toolbar


class Sources:
    def __init__(self,owner):
        self.owner=owner;self.scope=scope_of(owner);self.document=owner.document;self.workspace=workspace_of(owner)
        self.window=view_window(self,owner,'sources','Campaign sources')
        self.status=tk.StringVar();self.info=tk.StringVar();self.records={}
        ttk.Label(self.window,textvariable=self.info,wraplength=850,padding=12).pack(fill='x')
        bar=ttk.Frame(self.window,padding=6);bar.pack(fill='x')
        self.buttons={}
        for label,action in [('Create source copy...',self.convert),('Build playable package...',self.build),('Open selected object',self.open_object),('Refresh',self.refresh)]:
            button=ttk.Button(bar,text=label,command=lambda f=action:guard(self,f,publish=False));button.pack(side='left',padx=4)
            self.buttons[label]=button
        flow_toolbar(bar)
        host=ttk.Frame(self.window,padding=8);host.pack(fill='both',expand=True)
        self.table=ttk.Treeview(host,columns=('collection','file'),show='tree headings',selectmode='browse')
        self.table.heading('#0',text='Object');self.table.heading('collection',text='Collection');self.table.heading('file',text='Editable source file')
        self.table.column('#0',width=220);self.table.column('collection',width=130,stretch=False);self.table.column('file',width=450)
        y=ttk.Scrollbar(host,command=self.table.yview);y.pack(side='right',fill='y');self.table.configure(yscrollcommand=y.set)
        x=ttk.Scrollbar(host,orient='horizontal',command=self.table.xview);x.pack(side='bottom',fill='x');self.table.configure(xscrollcommand=x.set)
        self.table.pack(fill='both',expand=True);self.table.bind('<Double-1>',lambda _:guard(self,self.open_object,publish=False))
        ttk.Label(self.window,textvariable=self.status,wraplength=850,padding=10).pack(fill='x')
        self.refresh()

    def show_error(self,error):self.status.set(str(error))

    def refresh(self):
        self.document=self.scope.document;source=self.document.source
        self.table.delete(*self.table.get_children());self.records={}
        self.buttons['Create source copy...'].configure(state='disabled' if source else 'normal')
        if source:
            current=CampaignSource(self.document.root,self.document.source_files())
            self.info.set('Source project: '+str(self.document.root)+'\nSave writes the modules below. Play and Build compile the current draft into a normal game package. Double-click an object to edit it with the usual tools.')
            for i,record in enumerate(current.locations):
                key=str(i);self.records[key]=record
                self.table.insert('','end',iid=key,text=record['id'],values=(record['collection'],record['file']))
            self.status.set(f'{len(current.disk)} source files. Text references live in text files; editor notes do not change gameplay saves.')
        else:
            self.info.set('This project uses the existing package format. All editing and Play features remain available. Create source copy makes a separate project with editable map, mission, definition, artwork and dialogue files.')
            self.status.set('Conversion canonicalizes game data. Keep this package for its old saves; the source copy starts a new campaign unless you explicitly migrate a save.')

    def destination(self,action):
        parent=filedialog.askdirectory(parent=self.workspace.window,title=action+' into a NEW subfolder of')
        if not parent:return None
        name=simpledialog.askstring(action,'New folder name:',initialvalue=self.document.manifest['package_id']+('-source' if action=='Create source copy' else '-build'),parent=self.workspace.window)
        if not name:return None
        if Path(name).name!=name or name in ('.','..') or '\\' in name:raise EditorError('Use a plain folder name.')
        return Path(parent)/name

    def convert(self,target=None):
        target=target or self.destination('Create source copy')
        if target is None:return
        candidate=snapshot(self.scope)
        def done(doc):
            # The current project may have newer edits; never replace it or
            # discard drafts just because a background conversion completed.
            self.status.set('Created source copy at '+str(doc.root)+'. Open that directory to edit its modules; your current project is still open.')
            self.workspace.log(self.status.get())
        return self.workspace.tasks.submit('Create source project copy',self,lambda cancel:convert(candidate,target),done,cancellable=False)

    def build(self,target=None):
        target=target or self.destination('Build playable package')
        if target is None:return
        candidate=snapshot(self.scope);stamp=signature(self.scope)
        def done(result):
            suffix=' The editor has newer edits; build again to include them.' if stamp!=signature(self.scope) else ''
            self.status.set('Built '+result['output']+'. Content '+result['fingerprint'][:16]+'.'+suffix)
            self.workspace.log(self.status.get())
        return self.workspace.tasks.submit('Build playable package',self,lambda cancel:build(candidate,target),done,cancellable=False)

    def open_object(self):
        from editor_problems import navigate
        selected=self.table.selection()
        if not selected:return
        record=self.records[selected[0]]
        problem=dict(owner=self.owner,scope=self.scope,document=self.document,message=record['file'],object_id=record['id'],
            field_path='$.'+record['collection']+'['+record['id']+']')
        if not navigate(self.workspace,problem):
            self.status.set('Source: '+str(self.document.root/record['file'])+' '+record['field_path'])


def open_sources(owner):return open_view(owner,'sources',lambda:Sources(owner))
