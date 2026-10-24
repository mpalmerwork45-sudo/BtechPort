"""CHI import and native dialogue views using ordinary document transactions."""
from __future__ import annotations
import argparse
import copy
import json
from pathlib import Path
import struct
from editor_model import EditorError,ProjectDocument,encoded


def wrap_labels(window,labels):
    last=[None]
    def resize(event):
        if event.widget is not window or event.width==last[0]:return
        last[0]=event.width
        for label in labels:label.configure(wraplength=max(220,event.width-24))
    window.bind('<Configure>',resize,add='+')


def campaign_data(document):
    if document.manifest.get('requires')!='chi-local-dos-1.03':
        raise EditorError('Open an imported CHI project to edit its compatibility settings.')
    return json.loads(document.metadata['campaign.json'])


def native_dialogue(document):
    campaign_data(document)
    data=document.snapshot['chi/talk-data.bin'];count=struct.unpack_from('<H',data,6)[0]
    if data[:4]!=b'BTTA' or count not in (373,375):raise EditorError('Unsupported native dialogue cache.')
    base=72+count*4
    return [data[base+at:base+at+size].decode('ascii')
            for at,size in (struct.unpack_from('<HH',data,72+4*i) for i in range(count))]


def set_dialogue(document,index,text):
    """GUI/CLI share rollback, native validation, Undo and strict content identity."""
    count=len(native_dialogue(document))
    if type(index) is not int or not 0<=index<count:raise EditorError('Native text index must be 0..'+str(count-1)+'.')
    if text is not None and not isinstance(text,str):raise EditorError('Native text must be a string.')
    value=campaign_data(document)
    overrides=[v for v in value['dialogue_overrides'] if v['index']!=index]
    if text is not None:overrides.append(dict(index=index,text=text))
    value['dialogue_overrides']=sorted(overrides,key=lambda v:v['index'])
    metadata=copy.deepcopy(document.metadata);metadata['campaign.json']=encoded(value)
    with document.command('Edit CHI native text'):
        document.replace_all(document.content,document.adventure,document.art,document.manifest,metadata)
        document.validate()


class CampaignView:
    def __init__(self,owner):
        import tkinter as tk
        from tkinter import ttk
        from editor_session import scope_of,guard
        from editor_workspace import view_window
        owner.apply_form();self.owner=owner;self.scope=scope_of(owner);self.document=owner.document
        value=campaign_data(self.document);self.base=native_dialogue(self.document)
        self.window=view_window(self,owner,'chi-campaign','CHI campaign')
        self.status=tk.StringVar();self.selected=None
        ttk.Label(self.window,text='Imported '+value['edition'].title()+' CHI campaign',style='Title.TLabel',padding=12).pack(anchor='w')
        information=ttk.Label(self.window,text='Edit native dialogue below. Project > CHI scripts edits building dialogue and control flow. Project > CHI services edits service content. CHI missions and campaign edits mission settings. Maps and presentation have their own tools.',wraplength=500,padding=(12,0,12,8));information.pack(fill='x')
        host=ttk.Panedwindow(self.window,orient='horizontal');host.pack(fill='both',expand=True,padx=12,pady=6)
        left=ttk.Frame(host);right=ttk.Frame(host);host.add(left,weight=1);host.add(right,weight=2)
        self.search=tk.StringVar();ttk.Entry(left,textvariable=self.search).pack(fill='x',pady=(0,6))
        self.table=ttk.Treeview(left,columns=('text',),show='tree headings',selectmode='browse')
        self.table.heading('#0',text='ID');self.table.column('#0',width=55,stretch=False)
        self.table.heading('text',text='Native text');self.table.column('text',width=270)
        bar=ttk.Scrollbar(left,command=self.table.yview);bar.pack(side='right',fill='y');self.table.configure(yscrollcommand=bar.set)
        self.table.pack(fill='both',expand=True)
        self.table.bind('<<TreeviewSelect>>',lambda _:guard(self,self.select,publish=False))
        self.search.trace_add('write',lambda *_:self.refresh())
        ttk.Label(right,text='Text').pack(anchor='w')
        self.text=tk.Text(right,wrap='word',width=28,height=6,undo=True);self.text.pack(fill='both',expand=True,pady=8)
        buttons=ttk.Frame(right);buttons.pack(fill='x',before=self.text)
        ttk.Button(buttons,text='Apply text',command=lambda:guard(self,self.apply,publish=False)).pack(side='left',padx=(0,8))
        ttk.Button(buttons,text='Restore original text',command=lambda:guard(self,self.reset,publish=False)).pack(side='left')
        ttk.Button(buttons,text='Refresh',command=self.refresh).pack(side='left',padx=8)
        from editor_ui import flow_toolbar
        flow_toolbar(buttons)
        status=ttk.Label(self.window,textvariable=self.status,padding=12,wraplength=500);status.pack(fill='x',before=host)
        wrap_labels(self.window,[information,status])
        self.refresh()

    def refresh(self):
        if self.scope.document is not self.document:raise EditorError('The project changed; reopen CHI campaign.')
        values={v['index']:v['text'] for v in campaign_data(self.document)['dialogue_overrides']}
        query=self.search.get().casefold();scroll=self.table.yview();selected=self.selected
        self.table.delete(*self.table.get_children())
        for i,base in enumerate(self.base):
            text=values.get(i,base)
            if query not in (str(i)+' '+text).casefold():continue
            self.table.insert('','end',iid=str(i),text=str(i)+('*' if i in values else ''),values=(text.replace('\r',' / ')[:100],))
        if selected is not None and self.table.exists(str(selected)):self.table.selection_set(str(selected))
        if scroll:self.table.yview_moveto(scroll[0])
        self.status.set(f'{len(values)} overrides. Apply adds an Undo step. Save project writes changes.')

    def select(self):
        selection=self.table.selection()
        if not selection:return
        self.selected=int(selection[0]);values={v['index']:v['text'] for v in campaign_data(self.document)['dialogue_overrides']}
        self.text.delete('1.0','end');self.text.insert('1.0',values.get(self.selected,self.base[self.selected]).replace('\r','\n'))

    def apply(self):
        if self.selected is None:raise EditorError('Select a native text entry first.')
        text=self.text.get('1.0','end-1c').replace('\n','\r')
        self.scope.transact(lambda:set_dialogue(self.document,self.selected,text));self.refresh()

    def reset(self):
        if self.selected is None:raise EditorError('Select a native text entry first.')
        self.scope.transact(lambda:set_dialogue(self.document,self.selected,None));self.refresh();self.select()


class ImportView:
    def __init__(self,owner):
        import tkinter as tk
        from tkinter import ttk,filedialog
        import queue
        from editor_workspace import view_window,workspace_of
        from editor_session import guard
        from app_runtime import ROOT
        self.owner=owner;self.workspace=workspace_of(owner)
        self.window=view_window(self,owner,'chi-import','Import CHI campaign')
        self.status=tk.StringVar(value='Choose the original DOS 1.03 game folder and a new output folder.')
        self.source=tk.StringVar(value=owner.settings.get('data',''))
        self.target=tk.StringVar(value=str(ROOT/'work'/'my-chi-campaigns'))
        self.edition=tk.StringVar(value='both');self.messages=queue.SimpleQueue();self.cancel_event=None;self.result=None
        ttk.Label(self.window,text='Import CHI campaign',style='Title.TLabel',padding=12).pack(anchor='w')
        form=ttk.Frame(self.window,padding=12);form.pack(fill='x');form.columnconfigure(1,weight=1)
        for row,(label,value) in enumerate([('Original game folder',self.source),('New output folder',self.target)]):
            ttk.Label(form,text=label).grid(row=row,column=0,padx=(0,12),pady=8,sticky='w')
            ttk.Entry(form,textvariable=value,width=60).grid(row=row,column=1,sticky='ew')
            def browse(variable=value,kind=row):
                path=filedialog.askdirectory(parent=self.window.winfo_toplevel(),title='Choose original game folder' if kind==0 else 'Choose output parent folder')
                if path:variable.set(str(Path(path)/'My CHI campaigns') if kind else path)
            ttk.Button(form,text='Browse...',command=browse).grid(row=row,column=2,padx=(8,0))
        ttk.Label(form,text='Campaigns').grid(row=2,column=0,sticky='w',pady=8)
        ttk.Combobox(form,textvariable=self.edition,values=('both','original','updated'),state='readonly').grid(row=2,column=1,sticky='w')
        information=ttk.Label(self.window,text='Requires all 77 unmodified DOS 1.03 files (including BTECH.EXE). Original retains the native roster/rules; Updated includes the expanded roster, broker and Enhanced combat. Both creates separate projects and save slots. Completed imports play without the original installation. Original-derived files stay private.',wraplength=500,padding=12);information.pack(fill='x')
        bar=ttk.Frame(self.window,padding=12);bar.pack(fill='x')
        self.start_button=ttk.Button(bar,text='Import',style='Accent.TButton',command=lambda:guard(self,self.start,publish=False));self.start_button.pack(side='left')
        self.cancel_button=ttk.Button(bar,text='Cancel import',command=self.cancel,state='disabled');self.cancel_button.pack(side='left',padx=8)
        ttk.Button(bar,text='Inspect interrupted imports',command=lambda:guard(self,self.interrupted,publish=False)).pack(side='left',padx=8)
        self.progress=ttk.Progressbar(bar,mode='indeterminate');self.progress.pack(side='left',fill='x',expand=True,padx=8)
        from editor_ui import flow_toolbar
        flow_toolbar(bar)
        self.completed=ttk.Frame(self.window,padding=12);self.completed.pack(fill='x')
        status=ttk.Label(self.window,textvariable=self.status,wraplength=500,padding=12);status.pack(fill='x')
        wrap_labels(self.window,[information,status])
        self.window.protocol('WM_DELETE_WINDOW',self.close)

    def start(self):
        import threading
        from chi_import import import_campaigns
        source,target,edition=self.source.get(),self.target.get(),self.edition.get()
        self.cancel_event=threading.Event();self.result=None
        for child in self.completed.winfo_children():child.destroy()
        self.start_button.state(['disabled']);self.cancel_button.state(['!disabled']);self.progress.start(15)
        def work(_):return import_campaigns(source,target,edition,self.owner.validator,self.cancel_event,self.messages.put)
        def finish(result):
            self.result=result;self.finish();self.status.set('Import complete: '+result['output'])
            from app_runtime import register_imported_projects
            try:
                register_imported_projects(self.owner.state_dir,result['projects'])
                if getattr(self.owner,'launcher',None):self.owner.launcher.refresh_imported_projects()
            except (EditorError,OSError) as error:
                self.status.set('Import complete: '+result['output']+'; launcher registration failed: '+str(error))
            import tkinter.ttk as ttk
            from editor_session import guard
            for project in result['projects']:
                row=ttk.Frame(self.completed);row.pack(fill='x',pady=4)
                ttk.Label(row,text=project['edition'].title(),width=12).pack(side='left')
                ttk.Button(row,text='Edit',command=lambda p=project:guard(self,lambda:self.edit(p),publish=False)).pack(side='left',padx=6)
                ttk.Button(row,text='Play',command=lambda p=project:guard(self,lambda:self.play(p),publish=False)).pack(side='left')
            self.owner.settings.setdefault('player',str(Path(self.owner.validator).with_name('btech-port')))
        def failed(error):
            self.finish();self.start_button.configure(text='Retry import')
            self.status.set(str(error)+' Fix the folder/files or choose another new output folder, then Retry import.')
        try:self.workspace.tasks.submit('Importing CHI campaigns',self,work,finish,failed,cancellable=False)
        except Exception:self.finish();raise
        self.poll()

    def poll(self):
        while not self.messages.empty():self.status.set(self.messages.get())
        if self.cancel_event is not None:self.window.after(75,self.poll)

    def finish(self):
        self.cancel_event=None;self.progress.stop();self.start_button.state(['!disabled']);self.cancel_button.state(['disabled'])

    def cancel(self):
        if self.cancel_event:self.cancel_event.set();self.status.set('Cancelling safely...')

    def interrupted(self):
        from chi_import import interrupted_imports
        rows=interrupted_imports(Path(self.target.get()).parent)
        self.status.set('No marked interrupted imports in this parent folder.' if not rows else '\n'.join(row['staging']+' — '+row['recovery'] for row in rows))

    def close(self):
        if self.cancel_event:self.cancel();return
        self.window.destroy()

    def edit(self,project):
        if not self.owner.discard_or_save():return
        self.owner.set_document(ProjectDocument(Path(project['path']),self.owner.validator))
        open_campaign(self.owner)

    def play(self,project):
        from app_runtime import game_command,spawn
        command=game_command('My project',self.owner.settings,self.owner.state_dir,Path(project['path']))
        spawn(command,self.owner.state_dir);self.status.set('Started '+project['edition']+'; its project saves are separate.')


def open_campaign(owner):
    from editor_workspace import open_view
    return open_view(owner,'chi-campaign',lambda:CampaignView(owner))


def open_import(owner):
    from editor_workspace import open_view
    return open_view(owner,'chi-import',lambda:ImportView(owner))


def main():
    from app_runtime import binary
    parser=argparse.ArgumentParser(description='Edit imported native dialogue with shared validation and atomic Save.')
    parser.add_argument('--project',type=Path,required=True);parser.add_argument('--index',type=int,required=True)
    options=parser.add_mutually_exclusive_group(required=True)
    options.add_argument('--text');options.add_argument('--text-file',type=Path);options.add_argument('--reset',action='store_true')
    args=parser.parse_args()
    try:
        document=ProjectDocument(args.project,binary('btp-project'))
        text=None if args.reset else args.text_file.read_text().replace('\n','\r') if args.text_file else args.text
        set_dialogue(document,args.index,text);print(document.save())
    except (EditorError,OSError,ValueError) as error:parser.exit(1,str(error)+'\n')


if __name__=='__main__':main()
