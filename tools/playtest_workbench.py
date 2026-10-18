"""Immutable project snapshots and real-player event traces for author testing."""
from editor_session import guard
from editor_workspace import view_window
import json
from pathlib import Path
import queue
import re
import shutil
import subprocess
import tempfile
import threading
import tkinter as tk
from tkinter import ttk
from editor_model import EditorError,ProjectDocument,encoded

def checkpoint_command(project,settings,folder,actions,load=None):
    """No shell and no normal save slots: every run owns its output directory."""
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    (folder/'actions.txt').write_text(actions,encoding='ascii')
    args=[str(Path(settings['player']).resolve()),'--headless','--project',str(Path(project).resolve()),
          '--replay',str(folder/'actions.txt'),'--event-trace',str(folder/'events.jsonl'),
          '--save',str(folder/'state.btp'),'--frame',str(folder/'frame.ppm')]
    for key in ('data','dialogue-data','combat-data','world-data'):
        if settings.get(key):args+=['--'+key,str(Path(settings[key]).resolve())]
    if load:args+=['--load',str(Path(load).resolve())]
    return args

def make_checkpoint(document,settings,root,name,actions,source=None):
    if not re.fullmatch('[A-Za-z0-9_-]{1,60}',name):raise EditorError('Checkpoint names use 1..60 letters, digits, underscores or dashes.')
    root=Path(root).resolve();root.mkdir(parents=True,exist_ok=True);target=root/name
    if target.exists():raise EditorError('Choose a new checkpoint name; existing checkpoints are preserved.')
    with tempfile.TemporaryDirectory(prefix='.playtest-',dir=root) as tmp:
        stage=Path(tmp)
        if source:
            source=Path(source).resolve();ProjectDocument(source/'game',document.validator).export(stage/'game')
        else:document.export(stage/'game')
        result=subprocess.run(checkpoint_command(stage/'game',settings,stage,actions,source/'state.btp' if source else None),
                              capture_output=True,text=True,timeout=30)
        if result.returncode:raise EditorError(result.stderr.strip() or 'The playtest failed.')
        try:state=json.loads(result.stdout)
        except ValueError as exc:raise EditorError('The player returned an invalid state report.') from exc
        (stage/'state.json').write_bytes(encoded(state))
        (stage/'checkpoint.json').write_bytes(encoded(dict(format='btp-checkpoint-v1',name=name,source=str(source) if source else None)))
        if target.exists():raise EditorError('Checkpoint appeared while testing; choose another name.')
        # Publish only a complete validated snapshot, state, trace and frame.
        stage.rename(target)
    return target

class PlaytestWindow:
    def __init__(self,owner):
        self.owner=owner;self.document=owner.document;self.busy=False
        self.root=owner.parent.state_dir/'checkpoints'/self.document.manifest['package_id'];self.root.mkdir(parents=True,exist_ok=True)
        self.window=view_window(self,owner,'playtest','Playtest checkpoints and trace');self.window.geometry('960x690')
        top=ttk.Frame(self.window,padding=10);top.pack(fill='x')
        ttk.Label(top,text='New checkpoint name').pack(side='left');self.name=tk.StringVar(value='test-1');ttk.Entry(top,textvariable=self.name,width=22).pack(side='left',padx=8)
        for text,method in [('Run from start',lambda:self.run(False)),('Run from selected',lambda:self.run(True)),('Play selected',self.play)]:
            ttk.Button(top,text=text,command=lambda f=method:guard(self,f)).pack(side='left',padx=3)
        body=ttk.Panedwindow(self.window,orient='horizontal');body.pack(fill='both',expand=True,padx=10)
        left=ttk.Frame(body);right=ttk.Frame(body);body.add(left,weight=1);body.add(right,weight=3)
        self.listing=tk.Listbox(left,exportselection=False,width=25);self.listing.pack(fill='both',expand=True);self.listing.bind('<<ListboxSelect>>',lambda _:guard(self,self.show))
        ttk.Label(right,text='Actions (one per line: up, down, left, right, accept, cancel, menu, idle)').pack(anchor='w')
        self.actions=tk.Text(right,height=6,wrap='none');self.actions.pack(fill='x',pady=6);self.actions.insert('1.0','accept\n')
        ttk.Label(right,text='State, flags and event entries (double-click an event to edit it)').pack(anchor='w')
        self.trace=ttk.Treeview(right,columns=('tick','credits'),show='tree headings');self.trace.heading('#0',text='Event / state');self.trace.heading('tick',text='Tick');self.trace.heading('credits',text='Credits')
        self.trace.column('tick',width=70,stretch=False);self.trace.column('credits',width=90,stretch=False)
        scroll=ttk.Scrollbar(right,command=self.trace.yview);self.trace.configure(yscrollcommand=scroll.set);scroll.pack(side='right',fill='y');self.trace.pack(fill='both',expand=True)
        self.trace.bind('<Double-1>',lambda _:guard(self,self.edit_event))
        self.status=tk.StringVar(value='Each run saves its own game snapshot; your ordinary game saves are untouched.')
        ttk.Label(self.window,textvariable=self.status,padding=10,wraplength=900).pack(fill='x');self.refresh()

    def refresh(self,select=None):
        self.entries=sorted(p for p in self.root.iterdir() if (p/'checkpoint.json').is_file())
        self.listing.delete(0,'end')
        for p in self.entries:self.listing.insert('end',p.name)
        if select in self.entries:self.listing.selection_set(self.entries.index(select));self.show()

    def selected(self):return self.entries[self.listing.curselection()[0]] if self.listing.curselection() else None

    def run(self,resume):
        if self.busy:return
        source=self.selected() if resume else None
        if resume and source is None:raise EditorError('Select a checkpoint to continue.')
        if hasattr(self.window,'workspace'):
            from editor_tasks import snapshot
            from editor_session import scope_of
            candidate=snapshot(scope_of(self));settings=dict(self.owner.parent.settings)
            name=self.name.get();actions=self.actions.get('1.0','end-1c');root=self.root
            self.busy=True;self.status.set('Preparing checkpoint and running the player…')
            def done(path):
                self.busy=False;self.refresh(path);self.status.set('Checkpoint saved. Select it to inspect flags, continue or play.')
            def failed(error):self.busy=False;raise error
            try:self.window.workspace.tasks.submit('Running checkpoint',self,lambda cancel:make_checkpoint(candidate,settings,root,name,actions,source),done,failed,cancellable=False)
            except Exception:
                self.busy=False
                raise
            return
        self.owner.apply_pending();self.document.save()
        # The worker reads a detached document; editing can continue without
        # racing its mutable arrays or touching Tk from the worker thread.
        settings=dict(self.owner.parent.settings);name=self.name.get();actions=self.actions.get('1.0','end-1c');replies=queue.Queue()
        snapshot=tempfile.TemporaryDirectory(prefix='checkpoint-input-');self.document.export(Path(snapshot.name)/'game')
        validator=self.document.validator
        self.busy=True;self.status.set('Running the real player; collecting commands, flags and a saved continuation...')
        def work():
            try:replies.put((True,make_checkpoint(ProjectDocument(Path(snapshot.name)/'game',validator),settings,self.root,name,actions,source)))
            except Exception as exc:replies.put((False,str(exc)))
            finally:snapshot.cleanup()
        threading.Thread(target=work,daemon=True).start()
        def poll():
            if not self.window.winfo_exists():return
            try:ok,value=replies.get_nowait()
            except queue.Empty:self.window.after(80,poll);return
            self.busy=False
            if ok:self.refresh(value);self.status.set('Checkpoint saved. Select it to inspect flags, continue the replay or play interactively.')
            else:self.status.set(value)
        self.window.after(80,poll)

    def show(self):
        path=self.selected()
        if not path:return
        self.trace.delete(*self.trace.get_children());state=json.loads((path/'state.json').read_bytes());a=json.loads((path/'game'/json.loads((path/'game/project.json').read_bytes())['adventure']).read_bytes())
        self.trace.insert('','end',text='Final state',values=(state['tick'],state['credits']))
        for flag,value in zip(a['flags'],state.get('authored_event',{}).get('flags',[])):self.trace.insert('','end',text=f'{flag} = {value}')
        for i,line in enumerate((path/'events.jsonl').read_text().splitlines()):
            e=json.loads(line);self.trace.insert('','end',iid=f'event-{i}',text=e['event'],values=(e['tick'],e['credits']))

    def edit_event(self):
        selected=self.trace.selection()
        if not selected or not selected[0].startswith('event-'):return
        identity=self.trace.item(selected[0],'text')
        if not any(e['id']==identity for e in self.document.adventure['events']):raise EditorError('This checkpoint event is absent from the current game.')
        if hasattr(self.window,'workspace'):return self.window.workspace.open_event(identity)
        self.owner.event_id=identity;self.owner.refresh_events();self.owner.populate_event();self.owner.tabs.select(self.owner.event_tab);self.owner.window.lift()

    def play(self):
        path=self.selected()
        if not path:raise EditorError('Select a saved checkpoint.')
        if hasattr(self.window,'workspace'):
            from editor_session import scope_of
            return self.window.workspace.play_session.start(scope_of(self),checkpoint=path)
        settings=self.owner.parent.settings;doc=ProjectDocument(path/'game',self.document.validator)
        command=doc.play_command(settings,self.owner.parent.state_dir)
        command+=['--load',str(path/'state.btp')]
        subprocess.Popen(command,cwd=self.root,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
