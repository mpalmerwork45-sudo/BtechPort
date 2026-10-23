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
from tkinter import ttk,filedialog
from editor_model import EditorError,ProjectDocument,encoded


def checkpoint_save(source):
    """Manual checkpoint folders and scenario saves share a snapshot parent."""
    source=Path(source).resolve()
    return source/'state.btp' if source.is_dir() else source


def run_scenario(document,settings,root,name,scenario_file,source=None,cancelled=lambda:False):
    from authoring_contract import read_json
    from authoring_scenarios import run,pin_checkpoint
    if not re.fullmatch('[A-Za-z0-9_-]{1,60}',name):raise EditorError('Run names use 1..60 letters, digits, underscores or dashes.')
    scenario_file=Path(scenario_file).resolve();scenario=read_json(scenario_file)
    if source:
        # This explicit GUI action selects the saved RNG instead of a
        # new-game seed. The file itself is preserved; the pinned request
        # is recorded in the new run's artifact directory.
        scenario=dict(scenario,checkpoint=pin_checkpoint(checkpoint_save(source)));scenario.pop('seed',None)
    suffix='.exe' if document.validator.suffix=='.exe' else ''
    runner=document.validator.parent/('btp-author-playtest'+suffix)
    assets={k:v for k,v in settings.items() if k in ('data','dialogue-data','combat-data','world-data') and v}
    return run(document,scenario,Path(root)/name,runner,assets,cancelled,base_dir=scenario_file.parent)

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
            source=checkpoint_save(source);ProjectDocument(source.parent/'game',document.validator).export(stage/'game')
        else:document.export(stage/'game')
        result=subprocess.run(checkpoint_command(stage/'game',settings,stage,actions,source),
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
        self.status=tk.StringVar(value='Each run saves its own game snapshot; your ordinary game saves are untouched.')
        footer=ttk.Label(self.window,textvariable=self.status,padding=10,wraplength=800);footer.pack(side='bottom',fill='x')
        footer.bind('<Configure>',lambda e:footer.configure(wraplength=max(240,e.width-20)))
        top=ttk.Frame(self.window,padding=10);top.pack(fill='x')
        ttk.Label(top,text='New checkpoint name').pack(side='left');self.name=tk.StringVar(value='test-1');ttk.Entry(top,textvariable=self.name,width=22).pack(side='left',padx=8)
        for text,method in [('Run actions from start',lambda:self.run(False)),('Continue actions',lambda:self.run(True)),('Play selected',self.play)]:
            ttk.Button(top,text=text,command=lambda f=method:guard(self,f)).pack(side='left',padx=3)
        from editor_ui import flow_toolbar
        flow_toolbar(top)
        scenarios=ttk.LabelFrame(self.window,text='Scenario verification against the current project',padding=8);scenarios.pack(fill='x',padx=10,pady=(0,8))
        pathbar=ttk.Frame(scenarios);pathbar.pack(fill='x')
        self.scenario_file=tk.StringVar();ttk.Entry(pathbar,textvariable=self.scenario_file).pack(side='left',fill='x',expand=True,padx=(0,6))
        ttk.Button(pathbar,text='Choose scenario...',command=lambda:guard(self,self.choose_scenario)).pack(side='left')
        controls=ttk.Frame(scenarios);controls.pack(fill='x',pady=(5,0));self.scenario_buttons={}
        for label,method in [('Run scenario file',lambda:self.run_scenario(False)),('From selected checkpoint',lambda:self.run_scenario(True)),('Cancel scenario',self.cancel_scenario),('Show last report',self.show_report)]:
            button=ttk.Button(controls,text=label,command=lambda f=method:guard(self,f));button.pack(side='left',padx=3)
            self.scenario_buttons[label]=button
        flow_toolbar(controls)
        explanation=ttk.Label(scenarios,text='Selected checkpoints keep their saved RNG. Changed game content is rejected. Actions and Play use the saved project version.',wraplength=850)
        explanation.pack(anchor='w',pady=(5,0));scenarios.bind('<Configure>',lambda e:explanation.configure(wraplength=max(240,e.width-20)))
        self.last_report=None;self.scenario_job=None
        body=ttk.Panedwindow(self.window,orient='horizontal');body.pack(fill='both',expand=True,padx=10)
        left=ttk.Frame(body);right=ttk.Frame(body);body.add(left,weight=1);body.add(right,weight=3)
        self.listing=tk.Listbox(left,exportselection=False,width=25);self.listing.pack(fill='both',expand=True);self.listing.bind('<<ListboxSelect>>',lambda _:guard(self,self.show))
        ttk.Label(right,text='Actions (one per line: up, down, left, right, accept, cancel, menu, idle)').pack(anchor='w')
        self.actions=tk.Text(right,height=4,width=30,wrap='none');self.actions.pack(fill='x',pady=6);self.actions.insert('1.0','accept\n')
        ttk.Label(right,text='State, flags and event entries (double-click an event to edit it)').pack(anchor='w')
        self.trace=ttk.Treeview(right,columns=('tick','credits'),show='tree headings',height=6);self.trace.heading('#0',text='Event / state');self.trace.heading('tick',text='Tick');self.trace.heading('credits',text='Credits')
        self.trace.column('tick',width=70,stretch=False);self.trace.column('credits',width=90,stretch=False)
        scroll=ttk.Scrollbar(right,command=self.trace.yview);self.trace.configure(yscrollcommand=scroll.set);scroll.pack(side='right',fill='y');self.trace.pack(fill='both',expand=True)
        self.trace.bind('<Double-1>',lambda _:guard(self,self.edit_event))
        self.refresh()

    def show_error(self,error):self.status.set(str(error))

    def refresh(self,select=None):
        self.entries=[]
        for p in sorted(self.root.iterdir()):
            if (p/'checkpoint.json').is_file():self.entries.append(p/'state.btp')
            elif (p/'report.json').is_file():
                report=json.loads((p/'report.json').read_bytes())
                names=[s['checkpoint']['file'] for s in report.get('steps',[]) if s.get('ok') and 'checkpoint' in s]
                if report.get('status')=='passed':names.append(report['result']['save'])
                self.entries.extend(p/n for n in dict.fromkeys(names) if Path(n).name==n and (p/n).is_file())
        self.listing.delete(0,'end')
        for p in self.entries:
            label='final' if p.name.startswith('final-') else p.stem.removeprefix('checkpoint-')
            if len(label)>48:label='checkpoint'
            self.listing.insert('end',p.parent.name+(' / '+label if p.name!='state.btp' else ''))
        if select and Path(select).is_dir():select=Path(select)/'state.btp'
        if select in self.entries:self.listing.selection_set(self.entries.index(select));self.show()

    def selected(self):return self.entries[self.listing.curselection()[0]] if self.listing.curselection() else None

    def choose_scenario(self):
        name=filedialog.askopenfilename(parent=self.window,title='Choose a scenario JSON file',initialdir=self.document.root,filetypes=[('Scenario JSON','*.json')])
        if name:self.scenario_file.set(name)

    def cancel_scenario(self):
        if self.scenario_job:self.scenario_job.cancelled.set();self.status.set('Stopping scenario; completed evidence will be kept.')

    def run_scenario(self,resume):
        if self.busy:return
        from editor_tasks import snapshot,signature
        from editor_session import scope_of,report,clear_problems
        scope=scope_of(self);workspace=getattr(self.window,'workspace',None)
        if workspace is None:raise EditorError('Open Checkpoints and trace in the main workspace to run scenarios.')
        if not self.scenario_file.get():raise EditorError('Choose a scenario JSON file first.')
        source=self.selected() if resume else None
        if resume and source is None:raise EditorError('Select a checkpoint to continue.')
        candidate=snapshot(scope);stamp=signature(scope);settings=dict(self.owner.parent.settings)
        name=self.name.get();file=self.scenario_file.get();root=self.root
        self.busy=True;self.status.set('Checking current content and running the scenario...')
        def done(result):
            self.busy=False;self.scenario_job=None;self.last_report=Path(result['report'])
            full=json.loads(self.last_report.read_bytes())
            final=self.last_report.parent/full['result']['save'] if result['status']=='passed' else None
            self.refresh(final)
            changed=stamp!=signature(scope)
            if not changed:
                clear_problems(scope,'scenario')
                for item in result.get('diagnostics',[]):
                    problem=dict(item,owner=scope.owner,field=None,category='scenario')
                    scope.problems.append(problem);workspace.problem(scope,problem)
            self.status.set('Scenario '+result['status']+('. Project changed during this run; results describe the earlier snapshot.' if changed else '.')+' Report: '+str(self.last_report))
        def failed(error):
            self.busy=False;self.scenario_job=None
            if stamp!=signature(scope):self.status.set('Scenario stopped for an earlier edit: '+str(error))
            else:report(self,error,category='scenario')
        try:self.scenario_job=workspace.tasks.submit('Running saved journey' if resume else 'Running scenario',self,
            lambda cancel:run_scenario(candidate,settings,root,name,file,source,cancel.is_set),done,failed)
        except Exception:
            self.busy=False
            raise

    def show_report(self):
        from editor_workspace import open_view
        report_path=self.last_report
        if not report_path and self.selected():report_path=self.selected().parent/'report.json'
        if not report_path or not report_path.is_file():raise EditorError('Run a scenario to create a report first.')
        def build():
            owner=type('ScenarioReport',(),{})();owner.owner=self;owner.document=self.document
            owner.window=view_window(owner,self,'scenario-report','Scenario report',str(report_path))
            text=tk.Text(owner.window,wrap='word',font='TkFixedFont',padx=8,pady=8)
            scroll=ttk.Scrollbar(owner.window,command=text.yview);text.configure(yscrollcommand=scroll.set)
            scroll.pack(side='right',fill='y');text.pack(fill='both',expand=True)
            text.insert('1.0',report_path.read_text());text.configure(state='disabled');return owner
        return open_view(self,'scenario-report',build,str(report_path))

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
        self.trace.delete(*self.trace.get_children());folder=path.parent
        if (folder/'report.json').is_file():
            report=json.loads((folder/'report.json').read_bytes());self.last_report=folder/'report.json'
            # Legacy unnamed checkpoints reuse a file. Its state is the
            # last successful write, while named saves remain independent.
            row=next((s for s in reversed(report['steps']) if s.get('ok') and s.get('checkpoint',{}).get('file')==path.name),report['result'])
            state=row['state'];flags=state.get('flags',{})
        else:
            state=json.loads((folder/'state.json').read_bytes());a=json.loads((folder/'game'/json.loads((folder/'game/project.json').read_bytes())['adventure']).read_bytes())
            flags=dict(zip(a['flags'],state.get('authored_event',{}).get('flags',[])))
        self.trace.insert('','end',text='Saved state',values=(state['tick'],state['credits']))
        for flag,value in flags.items():self.trace.insert('','end',text=f'{flag} = {value}')
        for i,line in enumerate((folder/'events.jsonl').read_text().splitlines()):
            e=json.loads(line)
            if e['tick']<=state['tick']:self.trace.insert('','end',iid=f'event-{i}',text=e['event'],values=(e['tick'],e['credits']))

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
        settings=self.owner.parent.settings;doc=ProjectDocument(path.parent/'game',self.document.validator)
        command=doc.play_command(settings,self.owner.parent.state_dir)
        command+=['--load',str(path)]
        subprocess.Popen(command,cwd=self.root,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
