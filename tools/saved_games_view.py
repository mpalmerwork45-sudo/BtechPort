"""Shared Saved games screen for launcher windows and editor workspace tabs."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
import os,subprocess,tkinter as tk
from tkinter import ttk,filedialog
from editor_model import EditorError,ProjectDocument
from save_catalogue import SaveCatalogue


class SavedGamesView:
    def __init__(self,owner,window=None):
        self.owner=owner;self.scope=getattr(owner,'_editor_scope',None);self.closed=False;self.job=None;self.timer=None
        if window is None:
            from editor_workspace import view_window
            window=view_window(self,owner,'saved-games','Saved games')
        self.window=window;self.status=tk.StringVar(value='Reading saved games…');self.detail=tk.StringVar()
        self.pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='bck-saves');self.model=None;self.rows={};self.context_warning=''
        self.heading=ttk.Label(window,text='Saved games',style='Title.TLabel',padding=12);self.heading.pack(anchor='w')
        intro=ttk.Label(window,text='Continue a slot, recover a retained save into an empty slot, or keep a backup. Earlier saves use their matching campaign revision.',wraplength=650,padding=(12,0,12,12));intro.pack(fill='x')
        # Reserve the actions/status before allocating the resizable table.
        # A narrow workspace must never push recovery controls out of view.
        footer=ttk.Frame(window);footer.pack(side='bottom',fill='x')
        host=ttk.Frame(window,padding=(12,0));host.pack(fill='both',expand=True)
        columns=('slot','saved','revision','location','status')
        self.table=ttk.Treeview(host,columns=columns,show='headings',selectmode='browse',height=8)
        for name,label,width in zip(columns,('Slot','Saved at','Campaign revision','Location','Status'),(65,150,135,130,200)):
            self.table.heading(name,text=label);self.table.column(name,width=width,stretch=name in ('revision','status'))
        self.table.pack(side='left',fill='both',expand=True);scroll=ttk.Scrollbar(host,command=self.table.yview);scroll.pack(side='right',fill='y');self.table.configure(yscrollcommand=scroll.set)
        self.table.bind('<<TreeviewSelect>>',self.select);self.table.bind('<Double-1>',lambda _:self.continue_game());self.table.bind('<Return>',lambda _:self.continue_game())
        detail=ttk.Label(footer,textvariable=self.detail,padding=12,wraplength=650,justify='left');detail.pack(fill='x')
        bar=ttk.Frame(footer,padding=12);bar.pack(fill='x');self.buttons=[]
        for text,method in [('Continue selected',self.continue_game),('Back up selected',self.backup),('Refresh',self.refresh)]:
            button=ttk.Button(bar,text=text,command=method);button.pack(side='left',padx=(0,8));self.buttons.append(button)
        ttk.Label(bar,text='Recover to slot').pack(side='left',padx=(12,4))
        self.slot=tk.StringVar(value='1');ttk.Combobox(bar,textvariable=self.slot,values=tuple(map(str,range(1,7))),width=3,state='readonly').pack(side='left')
        button=ttk.Button(bar,text='Recover copy',command=self.recover);button.pack(side='left',padx=8);self.buttons.append(button)
        extra=ttk.Frame(footer,padding=(12,0,12,8));extra.pack(fill='x')
        ttk.Button(extra,text='Locate matching campaign...',command=self.locate).pack(side='left',padx=(0,8))
        ttk.Button(extra,text='Open backup folder',command=self.open_backups).pack(side='left')
        status=ttk.Label(footer,textvariable=self.status,padding=12,wraplength=650);status.pack(fill='x')
        def resize(event):
            if event.widget is window:
                for label in (intro,detail,status):label.configure(wraplength=max(250,event.width-32))
        window.bind('<Configure>',resize,add='+')
        window.bind('<Destroy>',self.destroyed,add='+');self.refresh()

    def destroyed(self,event):
        if event.widget is self.window:
            self.closed=True
            if self.timer:self.window.after_cancel(self.timer);self.timer=None
            self.pool.shutdown(wait=False,cancel_futures=True)

    def submit(self,label,work,done):
        if self.job:return
        self.status.set(label+'…')
        for button in self.buttons:button.state(['disabled'])
        self.job=(self.pool.submit(work),done);self.timer=self.window.after(40,self.poll)

    def poll(self):
        self.timer=None
        if self.closed or not self.job:return
        future,done=self.job
        if not future.done():self.timer=self.window.after(40,self.poll);return
        self.job=None
        for button in self.buttons:button.state(['!disabled'])
        try:done(future.result())
        except (EditorError,OSError,ValueError,subprocess.SubprocessError) as error:self.status.set(str(error))

    def refresh(self):
        if self.job:return
        # A failed refresh must not leave old rows attached to a different
        # campaign model. Retained revisions can be browsed independently of
        # a missing working directory or an invalid in-progress editor draft.
        self.model=None;self.rows={};self.table.delete(*self.table.get_children());self.detail.set('');self.context_warning=''
        try:
            owner=self.owner;document=None;identity=None
            if self.scope:
                from editor_tasks import snapshot
                choice='My project';location='Editor'
                if self.scope.document:identity=self.scope.document.manifest['package_id']
                try:document=snapshot(self.scope)
                except (EditorError,OSError,ValueError) as error:
                    if not identity:raise
                    self.context_warning='The current draft cannot be used. Showing retained saves: '+str(error)
            else:
                from app_runtime import binary,imported_projects
                from save_catalogue import retained_package_id
                choice=owner.choice.get();location='Launcher'
                path=owner.selected_project()
                if path:
                    try:document=ProjectDocument(path,binary('btp-project'))
                    except (EditorError,OSError,ValueError) as error:
                        ids={row['package_id'] for row in imported_projects(owner.state_dir) if Path(row['path']).resolve()==path.resolve()}
                        if len(ids)==1:identity=ids.pop()
                        elif not ids:identity=retained_package_id(owner.state_dir,path)
                        if not identity:raise
                        self.context_warning='The working project is unavailable. Showing retained saves: '+str(error)
            self.model=SaveCatalogue(owner.state_dir,owner.settings if self.scope else owner.paths,choice,document,location,package_id=identity)
            self.heading.configure(text='Saved games - '+(document.manifest['title'] if document else choice))
            self.submit('Reading six slots, earlier revisions and backups',self.model.scan,self.populate)
        except (EditorError,OSError,ValueError) as error:self.status.set(str(error))

    def populate(self,rows):
        self.table.delete(*self.table.get_children());self.rows={}
        for i,row in enumerate(rows):
            key=str(i);self.rows[key]=row
            revision=(row.signature[:12] if row.signature else row.version) or ('Current project' if row.current else '—')
            saved=datetime.fromtimestamp(row.mtime).strftime('%Y-%m-%d %H:%M:%S') if row.mtime else '—'
            self.table.insert('','end',iid=key,values=(('Quick / 1' if row.slot==1 else str(row.slot)),saved,revision,row.location,row.status))
        available=[k for k,r in self.rows.items() if r.path.exists() and not r.error]
        if available:self.table.selection_set(available[0]);self.table.focus(available[0]);self.select()
        else:self.detail.set('No saved games for this revision yet. F5 writes the quicksave; the in-game menu provides all six slots.')
        self.status.set(' '.join(filter(None,[self.context_warning,*self.model.warnings])) or 'Ready. Recover never replaces an occupied slot. Continue keeps a backup first.')

    def selected(self):
        selection=self.table.selection()
        if not selection:raise EditorError('Select a saved game first.')
        return self.rows[selection[0]]

    def select(self,_=None):
        try:row=self.selected()
        except EditorError:return
        self.slot.set(str(row.slot))
        self.detail.set('File: '+str(row.path)+'\nCampaign: '+(str(row.project) if row.project else 'Original' if row.tag=='BTS1' else 'Updated' if row.tag.startswith('BTU') else 'Exact matching revision not found')+'\n'+row.status)

    def operation(self,label,method,done=None):
        try:row=self.selected()
        except EditorError as error:self.status.set(str(error));return
        self.submit(label,lambda:method(row),done or self.changed)

    def changed(self,path):
        self.status.set('Saved copy: '+str(path));self.refresh()

    def backup(self):
        if self.model:self.operation('Validating and backing up',self.model.backup)
    def recover(self):
        if not self.model:return
        slot=int(self.slot.get());self.operation('Validating and recovering a copy',lambda row:self.model.recover(row,slot))

    def continue_game(self):
        if not self.model:return
        if self.scope:
            session=self.window.workspace.play_session
            if session.preparing or session.process is not None:self.status.set('Stop the running editor game before continuing a save.');return
        self.operation('Validating save and retaining its campaign',self.model.resume,self.launch)

    def launch(self,result):
        command,state=result
        if self.scope:self.window.workspace.play_session.start_saved(self.scope,command)
        else:
            from app_runtime import spawn
            process=spawn(command,self.owner.state_dir);self.owner.running.append(process);self.owner.later(500,lambda:self.owner.monitor(process))
        self.status.set('Continued saved game at tick '+str(state['tick'])+'. A backup was kept before launch.')

    def locate(self):
        if not self.model or not self.model.project_mode or self.job:return
        try:signature=self.selected().signature
        except EditorError:signature=None
        path=filedialog.askdirectory(parent=self.window.winfo_toplevel(),title='Locate the exact old campaign project')
        if path:self.submit('Checking and retaining this campaign revision',lambda:self.model.locate(path,signature),self.changed)

    def open_backups(self):
        if not self.model:return
        path=self.model.state_dir/'save-backups'/self.model.identity;path.mkdir(parents=True,exist_ok=True)
        if os.name=='nt':os.startfile(path)
        else:subprocess.Popen(['xdg-open',str(path)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)


def open_saved_games(owner):
    from editor_workspace import open_view
    return open_view(owner,'saved-games',lambda:SavedGamesView(owner))


def launcher_saved_games(owner):
    existing=getattr(owner,'saved_games_window',None)
    if existing and existing.winfo_exists():existing.destroy()
    window=tk.Toplevel(owner.window);owner.saved_games_window=window
    window.title('Saved games — BattleTech Construction Kit');window.geometry('1100x620');window.minsize(850,520)
    owner.saved_games_view=SavedGamesView(owner,window)
    return owner.saved_games_view
