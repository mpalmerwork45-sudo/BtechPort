"""One Construction Kit workspace, with reusable views and scoped commands."""
from __future__ import annotations
import json
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
from editor_session import scope_of, guard, report


def workspace_of(owner):
    scope=scope_of(owner)
    if scope is not None and hasattr(scope,'workspace'):return scope.workspace
    window=getattr(owner,'window',owner)
    return getattr(window,'workspace',None)


def existing_view(owner,kind,identity=None):
    workspace=workspace_of(owner)
    if workspace:
        view=workspace.views.get((id(scope_of(owner)),kind,identity))
        if view and view.winfo_exists():view.lift();return view.controller
    return None


def open_view(owner,kind,factory,identity=None):
    return existing_view(owner,kind,identity) or factory()


def view_window(controller,owner,kind,title,identity=None):
    workspace=workspace_of(owner)
    if workspace:
        return workspace.add_view(controller,scope_of(owner),kind,title,identity)
    window=tk.Toplevel(owner.window);window.title(title)
    return window


class EditorPane(ttk.Frame):
    """A view's content host, with a small adapter for existing window methods.

    Geometry and transient calls are intentionally local no-ops: the workspace
    owns geometry. Dialogs still use real Toplevels and the visible root.
    """
    def __init__(self,workspace,key,title,controller=None,scope=None):
        super().__init__(workspace.tabs)
        self.workspace,self.key,self.caption,self.controller,self.scope=workspace,key,title,controller,scope
        self.close_callback=None
        self.jobs=set()
    def title(self,value=None):
        if value is None:return self.caption
        self.caption=value;self.workspace.tabs.tab(self,text=value if len(value)<=22 else value[:19]+'...')
    def geometry(self,*_):return ''
    def minsize(self,*_):return None
    def transient(self,*_):return None
    def withdraw(self):return None
    def deiconify(self):self.lift()
    def lift(self,*_):self.workspace.activate(self)
    def protocol(self,name,callback=None):
        if name=='WM_DELETE_WINDOW':
            if callback is not None:self.close_callback=callback
            return self.close_callback
    def after(self,ms,callback=None,*args):
        if callback is None:return super().after(ms)
        job=None
        def run():
            self.jobs.discard(job)
            if self.winfo_exists():return callback(*args)
        job=super().after(ms,run);self.jobs.add(job);return job
    def after_cancel(self,job):
        self.jobs.discard(job);return super().after_cancel(job)
    def destroy(self):
        for job in list(self.jobs):self.after_cancel(job)
        if self.workspace.views.get(self.key) is self:self.workspace.views.pop(self.key,None)
        custom=self.workspace.custom_inspectors.pop(self.key,None)
        if custom is not None:custom.destroy()
        super().destroy()


class Workspace:
    def __init__(self,window,validator,state_dir):
        from roster_editor import RosterEditor,configure_editor_style
        self.window,self.validator,self.state_dir=window,validator,Path(state_dir)
        window.workspace=self
        self.views={};self.scopes=[];self.history=[];self.history_index=-1;self.custom_inspectors={}
        self.navigating=False;self.tree_refreshing=False;self.tree_actions={};self.last_tree_selection=None
        self.last_signature=None;self.problems=[];self.closing=False;self.timer=None;self.restoring=False
        self.layout_file=self.state_dir/'workspace.json'
        try:self.layout=json.loads(self.layout_file.read_text())
        except (OSError,ValueError):self.layout={}
        configure_editor_style(window)
        window.title('BattleTech Construction Kit');window.geometry('1280x800');window.minsize(960,620)
        self.status=tk.StringVar(value='Open a project or choose a template to begin.')
        self.actions={};self.action_entries={};self.action_buttons={}
        from editor_ui import TextHistory
        self.text_history=TextHistory(window)
        self.toolbar=ttk.Frame(window,padding=(10,6));self.toolbar.pack(fill='x')
        self.vertical=ttk.Panedwindow(window,orient='vertical');self.vertical.pack(fill='both',expand=True)
        self.horizontal=ttk.Panedwindow(self.vertical,orient='horizontal');self.vertical.add(self.horizontal,weight=8)
        self.explorer=ttk.Frame(self.horizontal,padding=6);self.horizontal.add(self.explorer,weight=1)
        ttk.Label(self.explorer,text='PROJECT',style='Section.TLabel').pack(anchor='w',pady=(2,6))
        self.query=tk.StringVar();ttk.Entry(self.explorer,textvariable=self.query,width=22).pack(fill='x',pady=(0,6))
        self.query.trace_add('write',lambda *_:self.refresh_tree())
        tree_host=ttk.Frame(self.explorer);tree_host.pack(fill='both',expand=True)
        self.tree=ttk.Treeview(tree_host,show='tree',selectmode='browse');self.tree.pack(side='left',fill='both',expand=True)
        tree_scroll=ttk.Scrollbar(tree_host,command=self.tree.yview);tree_scroll.pack(side='right',fill='y');self.tree.configure(yscrollcommand=tree_scroll.set)
        self.tree.bind('<<TreeviewSelect>>',self.select_tree)
        self.tree.bind('<Return>',lambda _:self.select_tree(force=True))
        self.tree.bind('<ButtonRelease-1>',lambda _:self.select_tree(force=True))
        self.tree.bind('<Button-3>',self.tree_menu)
        self.centre=ttk.Frame(self.horizontal);self.horizontal.add(self.centre,weight=5)
        navigation=ttk.Frame(self.centre,padding=(4,2));navigation.pack(fill='x')
        ttk.Button(navigation,text='Back',width=6,command=lambda:self.navigate(-1)).pack(side='left')
        ttk.Button(navigation,text='Forward',width=8,command=lambda:self.navigate(1)).pack(side='left')
        self.breadcrumb=tk.StringVar(value='Welcome');breadcrumb=ttk.Label(navigation,textvariable=self.breadcrumb,width=1)
        ttk.Button(navigation,text='Close tab',command=self.close_tab).pack(side='right')
        overflow=ttk.Menubutton(navigation,text='Open tabs');self.tab_menu=tk.Menu(overflow,tearoff=False,postcommand=self.fill_tab_menu)
        overflow.configure(menu=self.tab_menu);overflow.pack(side='right',padx=4)
        breadcrumb.pack(side='left',fill='x',expand=True,padx=8)
        self.tabs=ttk.Notebook(self.centre);self.tabs.pack(fill='both',expand=True)
        self.tabs.bind('<<NotebookTabChanged>>',self.tab_changed)
        self.tabs.bind('<Button-3>',self.tab_context)
        self.inspector=ttk.Frame(self.horizontal,padding=10);self.horizontal.add(self.inspector,weight=1)
        ttk.Label(self.inspector,text='INSPECTOR',style='Section.TLabel').pack(anchor='w')
        from adventure_editor import scroll_frame
        self.inspect_generic,inspect_body=scroll_frame(self.inspector,width=210,height=300);self.inspect_generic.pack(fill='both',expand=True)
        self.inspect_title=tk.StringVar(value='Selection');ttk.Label(inspect_body,textvariable=self.inspect_title,font='TkHeadingFont',wraplength=210).pack(anchor='w',pady=10)
        self.inspect_text=tk.StringVar();ttk.Label(inspect_body,textvariable=self.inspect_text,wraplength=210,justify='left').pack(anchor='w',fill='x')
        self.inspect_actions=ttk.Frame(inspect_body);self.inspect_actions.pack(fill='x',pady=12)
        self.bottom=ttk.Notebook(self.vertical);self.vertical.add(self.bottom,weight=1)
        self.problem_page=ttk.Frame(self.bottom);self.bottom.add(self.problem_page,text='Problems')
        self.problem_list=ttk.Treeview(self.problem_page,columns=('scope','message'),show='headings',height=4)
        self.problem_list.heading('scope',text='Scope');self.problem_list.heading('message',text='Problem')
        self.problem_list.column('scope',width=180,stretch=False);self.problem_list.column('message',width=650)
        self.problem_list.pack(fill='both',expand=True);self.problem_list.bind('<Double-1>',self.open_problem);self.problem_list.bind('<Return>',self.open_problem)
        self.output=tk.Text(self.bottom,height=5,wrap='word',state='disabled',font='TkFixedFont');self.bottom.add(self.output,text='Output')
        footer=ttk.Frame(window);footer.pack(side='bottom',fill='x',before=self.vertical);footer.columnconfigure(0,weight=1)
        ttk.Label(footer,textvariable=self.status,style='Status.TLabel',width=1).grid(row=0,column=0,sticky='ew')
        self.busybar=ttk.Progressbar(footer,mode='indeterminate',length=90);self.busy=False
        pane=self.add_view(None,None,'roster','Units')
        self.app=RosterEditor(pane,validator,self.state_dir)
        pane.controller=self.app;pane.scope=self.app._editor_scope
        self.attach_scope(self.app._editor_scope)
        from editor_recovery import Recovery
        self.recovery=Recovery(self)
        from editor_tasks import Tasks,PlaySession
        self.tasks=Tasks(self);self.play_session=PlaySession(self)
        self.install_actions();self.show_welcome();self.restore_layout()
        window.protocol('WM_DELETE_WINDOW',self.close)
        import traceback
        window.report_callback_exception=lambda kind,error,tb:report(self.active_owner(),error,''.join(traceback.format_exception(kind,error,tb)))
        self.timer=window.after(250,self.poll)
        window.bind('<Destroy>',self.destroyed,add='+')

    def destroyed(self,event):
        if event.widget is self.window:
            self.closing=True
            if self.timer:self.window.after_cancel(self.timer);self.timer=None
            self.tasks.shutdown();self.play_session.shutdown()

    def update_busy(self):
        active=any(not job.quiet for job in self.tasks.jobs)
        if active==self.busy:return
        self.busy=active
        if active:self.busybar.grid(row=0,column=1,padx=8);self.busybar.start(70)
        else:self.busybar.stop();self.busybar.grid_remove()

    def attach_scope(self,scope):
        scope.workspace=self;scope.on_problem=lambda problem:self.problem(scope,problem)
        if scope not in self.scopes:self.scopes.append(scope)

    def add_view(self,controller,scope,kind,title,identity=None):
        key=(id(scope),kind,identity)
        pane=EditorPane(self,key,title,controller,scope);self.views[key]=pane
        self.tabs.add(pane,text=title);self.tabs.select(pane)
        return pane

    def current_view(self):
        selected=self.tabs.select()
        return self.tabs.nametowidget(selected) if selected else None

    def active_owner(self):
        view=self.current_view()
        return (view.controller if view and view.controller else getattr(self,'app',self))

    def active_scope(self):
        return scope_of(self.active_owner()) or self.app._editor_scope

    def activate(self,view):
        if view.winfo_exists():self.tabs.add(view,text=view.caption[:22]);self.tabs.select(view)

    def hide(self,view):
        # Map/asset browsers provide shared caches to their open child views.
        # Closing their tab retains that controller, without a hidden OS window.
        self.tabs.hide(view)

    def tab_changed(self,_=None):
        view=self.current_view()
        if not view:return
        self.record_navigation()
        self.breadcrumb.set(view.caption)
        self.update_inspector()
        status=getattr(view.controller,'status',None)
        if status is not None:self.status.set(status.get())

    def navigate(self,step):
        index=self.history_index+step
        while 0<=index<len(self.history):
            entry=self.history[index];view=self.views.get(entry['key'])
            if view and view.winfo_exists():
                self.navigating=True
                try:
                    self.restore_view(view,entry['state']);self.tabs.select(view);self.window.update_idletasks();self.history_index=index
                except Exception as error:report(self.active_owner(),error)
                finally:self.navigating=False
                return
            index+=step

    def view_state(self,view):
        owner=view.controller;kind=view.key[1];state={}
        if owner is None:return state
        if kind in ('roster','library-unit'):state.update(kind=owner.kind.get(),current=owner.current)
        elif kind=='maps':state.update(map=owner.scene()['id'],marker=owner.selected_marker,cursor=owner.cursor,tab=owner.tabs.index(owner.tabs.select()))
        elif kind=='world':state.update(world=owner.world_id,city=owner.city)
        elif kind=='events':state.update(event=owner.selected,filter=owner.view_mode.get())
        elif kind=='graphics':state.update(selected=owner.selected)
        elif kind=='construction':state.update(current=owner.current,role=owner.selected_role,footprint_zoom=owner.footprint_zoom.get(),
            footprint_scroll=[owner.footprint.xview()[0],owner.footprint.yview()[0]],preview_scroll=[owner.preview.xview()[0],owner.preview.yview()[0]])
        elif kind=='patterns':state.update(selected=owner.selected)
        elif kind=='pixels':
            state.update(frame=owner.frame.current())
            if owner.map_context:state.update(map_context=owner.map_context,show_neighbours=owner.show_neighbours.get())
            if hasattr(owner,'view'):state.update(view=owner.view.get(),direction=owner.direction,phase=owner.phase)
        if hasattr(owner,'zoom'):state['zoom']=owner.zoom.get()
        if hasattr(owner,'canvas'):state['scroll']=[owner.canvas.xview()[0],owner.canvas.yview()[0]]
        return state

    def record_navigation(self):
        view=self.current_view()
        if self.navigating or self.restoring or not view:return
        entry=dict(key=view.key,state=self.view_state(view))
        if self.history_index>=0 and self.history[self.history_index]==entry:return
        self.history=self.history[:self.history_index+1]+[entry];self.history_index=len(self.history)-1

    def restore_view(self,view,state):
        owner=view.controller;kind=view.key[1]
        if owner is None:return
        if kind in ('roster','library-unit'):
            self.open_unit(state.get('kind','Mechs'),state.get('current'),owner)
        elif kind=='maps':
            owner.map_choice.current(next(i for i,m in enumerate(owner.adventure['maps']) if m['id']==state['map']));owner.change_map()
            owner.selected_marker=tuple(state['marker']) if state.get('marker') else None;owner.cursor=tuple(state.get('cursor',owner.cursor))
            # Old layouts can refer to the Events page, now hidden in favour
            # of its own workspace tab. Never restore an inaccessible page.
            page=state.get('tab',0)
            if page not in range(len(owner.tabs.tabs())) or owner.tabs.tab(page,'state')=='hidden':page=0
            owner.tabs.select(page)
        elif kind=='world':owner.world_id=state.get('world');owner.city=state.get('city');owner.refresh()
        elif kind=='events':owner.selected=state.get('event');owner.view_mode.set(state.get('filter','Nearby events'));owner.edit()
        elif kind=='graphics':owner.selected=state.get('selected');owner.refresh()
        elif kind=='construction':owner.current=state.get('current');owner.selected_role=state.get('role');owner.refresh()
        elif kind=='patterns':owner.selected=state.get('selected');owner.refresh()
        elif kind=='pixels':
            if hasattr(owner,'view'):
                owner.view.set(state.get('view',owner.view.get()));owner.direction=state.get('direction',owner.direction);owner.phase=state.get('phase',0);owner.refresh_frames()
            else:owner.frame.current(state.get('frame',0))
            if state.get('map_context'):
                from tile_context import context_grid
                if context_grid(owner.document,state['map_context']):
                    owner.set_map_context(state['map_context']);owner.show_neighbours.set(state.get('show_neighbours',True))
        if 'zoom' in state and hasattr(owner,'zoom'):owner.zoom.set(state['zoom'])
        if kind=='construction' and 'footprint_zoom' in state:owner.footprint_zoom.set(state['footprint_zoom'])
        if hasattr(owner,'draw'):owner.draw()
        if 'scroll' in state and hasattr(owner,'canvas'):
            owner.canvas.xview_moveto(state['scroll'][0]);owner.canvas.yview_moveto(state['scroll'][1])
            # Worlds draw only the viewport; restoring its scroll position must
            # redraw that destination just as wheel zoom and scrollbars do.
            if kind=='world':owner.schedule()
        if kind=='construction':
            for name in ('footprint','preview'):
                if name+'_scroll' in state:
                    canvas=getattr(owner,name);x,y=state[name+'_scroll'];canvas.xview_moveto(x);canvas.yview_moveto(y)

    def action(self,name,method,menu,shortcut=None):
        self.actions[name]=method
        self.action_entries[name]=(menu,0 if menu.index('end') is None else menu.index('end')+1)
        menu.add_command(label=name,command=lambda:self.invoke(name),accelerator=shortcut or '')
    def invoke(self,name):
        if not self.command_enabled(name):self.status.set(name+' is unavailable for the current selection or while a conflicting task runs.');return
        return guard(self.active_owner(),self.actions[name],publish=False)

    def fill_tab_menu(self):
        self.tab_menu.delete(0,'end')
        for view in self.views.values():self.tab_menu.add_command(label=view.caption,command=view.lift)

    def install_actions(self):
        menu=tk.Menu(self.window);self.window.configure(menu=menu)
        groups={name:tk.Menu(menu,tearoff=False) for name in ('File','Edit','View','Project','Play','Help')}
        for name,sub in groups.items():menu.add_cascade(label=name,menu=sub)
        self.action('New project',self.app.new_project,groups['File'])
        self.action('Open project',self.app.open_project,groups['File'])
        from editor_tasks import save,validate
        self.action('Save active scope',lambda:save(self,self.active_scope()),groups['File'],'Ctrl+S')
        self.action('Save project',lambda:save(self,self.app._editor_scope),groups['File'])
        self.action('Save all',self.save_all_async,groups['File'])
        self.action('Recovery drafts',self.recovery.browse,groups['File'])
        self.action('Export game',self.app.export_project,groups['File'])
        self.action('Close tab',self.close_tab,groups['File'],'Ctrl+W')
        self.action('Close editor',self.close,groups['File'])
        self.action('Undo',lambda:self.edit_history(False),groups['Edit'],'Ctrl+Z')
        self.action('Redo',lambda:self.edit_history(True),groups['Edit'],'Ctrl+Y')
        self.action('Find command',self.command_picker,groups['Edit'],'Ctrl+Shift+P')
        for name,pane,parent in [('Project explorer',self.explorer,self.horizontal),('Inspector',self.inspector,self.horizontal),('Problems and output',self.bottom,self.vertical)]:
            self.action(name,lambda p=pane,host=parent:self.toggle_panel(host,p),groups['View'])
        self.action('Reset layout',self.reset_layout,groups['View'])
        for percent in (100,150,200):self.action(f'Interface scale {percent}%',lambda p=percent:self.scale(p),groups['View'])
        self.action('Validate',lambda:validate(self,self.active_scope()),groups['Project'])
        self.action('Unit Library',self.app.open_library,groups['Project'])
        self.action('Player setup',self.app.setup,groups['Project'])
        self.action('Ammunition',lambda:self.active_scope().owner.ammunition(),groups['Project'])
        self.action('New definition',lambda:self.active_scope().owner.new_definition(),groups['Project'])
        self.action('Duplicate definition',lambda:self.active_scope().owner.duplicate(),groups['Project'])
        self.action('Delete definition',lambda:self.active_scope().owner.delete(),groups['Project'])
        self.action('Find usages',self.find_usages,groups['Project'])
        for kind in ('Building','Wall','Road'):
            self.action(kind+' designer',lambda k=kind:self.map_view().construction(k),groups['Project'])
        self.action('Pattern Library',lambda:self.map_view().patterns(),groups['Project'])
        from delivery_gui import report as assets
        from save_migration import dialog
        self.action('Assets and dependencies',lambda:assets(self.app),groups['Project'])
        self.action('Migrate an old save',lambda:dialog(self.app),groups['Project'])
        self.action('Play from start',lambda:self.play_session.start(self.app._editor_scope),groups['Play'],'F5')
        self.action('Preview library design',lambda:self.play_session.start(self.active_scope()),groups['Play'])
        self.action('Play from here',self.play_here,groups['Play'])
        self.action('Checkpoints and trace',self.open_playtest,groups['Play'])
        self.action('Stop test',self.play_session.stop,groups['Play'])
        self.action('Cancel background tasks',self.tasks.cancel,groups['Project'])
        self.action('Shortcuts and help',self.help,groups['Help'])
        for text,action in [('Save','Save active scope'),('Undo','Undo'),('Redo','Redo'),('Validate','Validate')]:
            button=ttk.Button(self.toolbar,text=text,command=lambda a=action:self.invoke(a));button.pack(side='left',padx=3)
            self.action_buttons[action]=button
            from editor_ui import tooltip
            tooltip(button,lambda a=action:self.command_label(a))
        ttk.Button(self.toolbar,text='Find command...',command=self.command_picker).pack(side='left',padx=14)
        options=ttk.Menubutton(self.toolbar,text='Play options');options.configure(menu=groups['Play']);options.pack(side='right')
        play=ttk.Button(self.toolbar,text='Play',style='Accent.TButton',command=lambda:self.invoke('Play from start'));play.pack(side='right',padx=3)
        self.action_buttons['Play from start']=play
        tooltip(play,'Play the current project from its start (F5), including unsaved edits. Play options offers Play from here and Stop test.')
        keys={'<Control-s>':'Save active scope','<Control-z>':'Undo','<Control-y>':'Redo','<Control-Shift-Z>':'Redo','<Control-w>':'Close tab','<Control-Shift-P>':'Find command','<F5>':'Play from start'}
        for key,action in keys.items():self.window.bind(key,lambda event,a=action:self.shortcut(event,a))
        self.window.bind('<Control-Tab>',lambda _:self.next_tab())

    def shortcut(self,event,action):
        if self.window.grab_current() is not None:return
        if action in ('Undo','Redo') and isinstance(event.widget,tk.Text):return
        if action in ('Undo','Redo') and self.text_history.undo(event.widget,action=='Redo'):return 'break'
        self.invoke(action);return 'break'

    def command_label(self,name):
        scope=self.active_scope();document=scope.document if scope else None
        if document and name in ('Undo','Redo'):
            labels=document.undo_labels if name=='Undo' else document.redo_labels
            return name+(' '+labels[-1] if labels else '')
        return name

    def command_enabled(self,name):
        scope=self.active_scope();document=scope.document if scope else None
        if name=='Save project':return bool(self.app.document) and not getattr(self.app._editor_scope,'saving',False)
        if name=='Save all':return any(s.document and not getattr(s,'saving',False) and s.dirty() for s in self.scopes)
        if name=='Save active scope' or name=='Validate':return bool(document) and not getattr(scope,'saving',False)
        if name in ('Undo','Redo'):
            return bool(document and ((document.undo_stack if name=='Undo' else document.redo_stack) or any(d.pending() for d in scope.live())))
        if name in ('Export game','Assets and dependencies','Migrate an old save'):return bool(self.app.document)
        if name in ('New definition','Duplicate definition','Delete definition','Ammunition','Find usages'):return bool(document)
        if name in ('Building designer','Wall designer','Road designer','Pattern Library'):return bool(self.app.document and self.app.document.adventure)
        if name in ('Play from start','Play from here','Checkpoints and trace'):return bool(self.app.document) and not self.play_session.preparing
        if name=='Preview library design':return bool(document and scope.owner.library_context) and not self.play_session.preparing
        if name=='Stop test':return self.play_session.preparing or self.play_session.process is not None
        if name=='Cancel background tasks':return any(j.cancellable and not j.quiet for j in self.tasks.jobs)
        return True

    def update_commands(self):
        for name,(menu,index) in self.action_entries.items():
            enabled=self.command_enabled(name);menu.entryconfigure(index,state='normal' if enabled else 'disabled',label=self.command_label(name))
            if name in self.action_buttons:self.action_buttons[name].state(['!disabled' if enabled else 'disabled'])

    def scale(self,percent):
        from roster_editor import configure_editor_style
        hidden=[(host,pane) for host,pane in ((self.horizontal,self.explorer),(self.horizontal,self.inspector),(self.vertical,self.bottom)) if str(pane) not in host.panes()]
        self.window.tk.call('tk','scaling',(96/72)*percent/100);configure_editor_style(self.window)
        self.layout['scale']=percent;self.window.update_idletasks();self.reset_layout()
        for host,pane in hidden:host.forget(pane)
        if percent>=150 and self.window.winfo_width()<1600 and str(self.explorer) in self.horizontal.panes():self.horizontal.forget(self.explorer)
        self.window.update_idletasks()
        if str(self.explorer) not in self.horizontal.panes() and str(self.inspector) in self.horizontal.panes():
            self.horizontal.sashpos(0,max(480,self.horizontal.winfo_width()-min(400,int(230*percent/100))))
        self.status.set(f'Interface scale {percent}%. View menus can collapse panels; fields and artwork remain scrollable.')

    def next_tab(self):
        tabs=tuple(p for p in self.tabs.tabs() if self.tabs.tab(p,'state')!='hidden')
        if tabs:self.tabs.select(tabs[(tabs.index(self.tabs.select())+1)%len(tabs)])
        return 'break'

    def edit_history(self,redo):
        from editor_history import history
        history(self,redo)

    def tab_context(self,event):
        try:view=self.tabs.nametowidget(self.tabs.tabs()[self.tabs.index(f'@{event.x},{event.y}')])
        except tk.TclError:return
        # Capture the clicked pane. A later selection change must never close
        # another tab, and the existing draft/save protections still apply.
        self.tabs.select(view)
        menu=tk.Menu(self.tabs,tearoff=False)
        menu.add_command(label='Close',command=lambda:guard(view.controller or self.app,lambda:self.close_tab(view)))
        try:menu.tk_popup(event.x_root,event.y_root)
        finally:menu.grab_release()

    def close_tab(self,view=None):
        view=view or self.current_view()
        if not view:return
        if not view.winfo_exists():return
        if view.controller is self.app:
            self.show_welcome();return
        if view.close_callback:view.close_callback()
        elif not view.scope or view.scope.confirm_view(view):view.destroy()

    def close_scope(self,scope):
        if self.tasks.busy(scope):self.status.set('This scope is finishing a durable save. Close it after the save finishes.');return
        self.tasks.cancel(scope)
        if not scope.confirm_close():return
        self.recovery.clear(scope)
        # Library sprite tabs are notebook siblings, not children of the unit
        # tab. Retire them before its temporary package is cleaned up.
        for pane in list(self.views.values()):
            if pane.scope is scope and pane.controller is not scope.owner:pane.destroy()
        scope.owner.window.destroy()
        if scope in self.scopes:self.scopes.remove(scope)

    def play_here(self):
        maps=self.map_view();self.play_session.start(self.app._editor_scope,(maps.scene()['id'],*maps.cursor))

    def save_all_async(self,finished=None):
        from editor_tasks import save
        remaining=[s for s in self.scopes if s.owner.window.winfo_exists() and s.document and s.dirty()]
        failures=[]
        def next_scope(ok=True):
            if not ok:failures.append(True)
            if remaining:
                scope=remaining.pop(0)
                try:save(self,scope,next_scope)
                except Exception as error:report(scope.owner,error);next_scope(False)
            else:
                self.status.set('Some scopes could not be saved. See Problems.' if failures else 'All requested snapshots saved.')
                if finished:finished(not failures)
        next_scope()

    def save_all(self):
        failures=[]
        for scope in list(self.scopes):
            if scope.owner.window.winfo_exists() and scope.document and scope.dirty():
                try:scope.owner.save()
                except Exception as error:failures.append(str(error));report(scope.owner,error)
        self.status.set('Some scopes could not be saved. See Problems.' if failures else 'All open scopes saved.')
        return not failures

    def map_view(self):self.app.edit_adventure();return self.app.map_editor
    def find_usages(self):
        from editor_dependencies import dialog
        owner=self.active_owner();pane=self.current_view();identity=None
        if pane and pane.key[1] in ('pixels','jigsaw'):identity=pane.key[2]
        elif pane and pane.key[1] in ('graphics','events'):identity=owner.selected
        elif pane and pane.key[1]=='maps':identity=owner.scene()['id']
        else:identity=getattr(owner,'current',None)
        if isinstance(identity,str):dialog(owner,identity)
        else:self.status.set('Select a unit, map, event or image to find its usages.')
    def open_map(self,identity=None):
        owner=self.map_view()
        if identity:
            owner.map_choice.current(next(i for i,m in enumerate(owner.adventure['maps']) if m['id']==identity));owner.change_map()
        owner.tabs.select(owner.map_tab);self.update_inspector()
    def open_event(self,identity=None):
        owner=self.map_view()
        graph=owner.event_graph()
        if identity:graph.selected=identity
        graph.edit();graph.window.lift();graph.fit();self.update_inspector()
    def open_world(self,identity=None):
        owner=self.map_view();owner.edit_landscape()
        if identity:owner.world_editor.world_id=identity;owner.world_editor.refresh()
    def open_art(self):return self.app.graphics_editor()
    def open_playtest(self):
        from playtest_workbench import PlaytestWindow
        owner=self.map_view();return open_view(owner,'playtest',lambda:PlaytestWindow(owner))

    def open_unit(self,kind,identity=None,owner=None):
        owner=owner or self.app;owner.apply_form();owner.window.lift();owner.kind.set(kind);owner.change_kind()
        if identity:owner.refresh_list(identity)
        self.update_inspector()

    def refresh_tree(self):
        if not hasattr(self,'app'):return
        opened={self.tree.item(i,'text') for i in self.tree.get_children() if self.tree.item(i,'open')}
        selection=self.tree.selection();self.tree_refreshing=True
        try:
            self.tree.delete(*self.tree.get_children());self.tree_actions={};query=self.query.get().casefold()
            def row(parent,key,label,action=None):
                self.tree.insert(parent,'end',iid=key,text=label,open=label in opened or (not opened and label=='Local maps'))
                if action:self.tree_actions[key]=action
                return key
            document=self.app.document
            if document:
                for kind,collection in [('Mechs','mechs'),('Vehicles','mechs'),('Infantry','people'),('Weapons','weapons'),('Equipment','equipment')]:
                    category=row('',kind,kind,lambda k=kind:self.open_unit(k))
                    values=(document.adventure or {}).get('people',[]) if collection=='people' else document.content.get(collection,[])
                    for value in values:
                        if collection=='mechs' and (value.get('kind')=='vehicle')!=(kind=='Vehicles'):continue
                        label=value.get('name',value['id'])
                        if query and query not in (label+' '+value['id']).casefold():continue
                        row(category,kind+':'+value['id'],label,lambda k=kind,i=value['id']:self.open_unit(k,i))
                if document.adventure:
                    worlds=row('','worlds','Worlds / planets',self.open_world)
                    from world_editing import all_worlds
                    for planet in all_worlds(document.adventure):
                        if not query or query in (planet['name']+' '+planet['id']).casefold():row(worlds,'world:'+planet['id'],planet['name'],lambda i=planet['id']:self.open_world(i))
                    maps=row('','maps','Local maps',self.open_map)
                    for scene in document.adventure['maps']:
                        if not query or query in (scene['name']+' '+scene['id']).casefold():row(maps,'map:'+scene['id'],scene['name'],lambda i=scene['id']:self.open_map(i))
                    construct=row('','construction','Construction tools',lambda:self.map_view().construction())
                    for kind in ('Building','Wall','Road'):row(construct,'construction:'+kind,kind+' designer',lambda k=kind:self.map_view().construction(k))
                    row(construct,'patterns','Pattern Library',lambda:self.map_view().patterns())
                    events=row('','events','Events / objectives',self.open_event)
                    for event in document.adventure['events']:
                        if not query or query in str(event).casefold():row(events,'event:'+event['id'],event['id'].split(':')[-1]+' ('+event['op']+')',lambda i=event['id']:self.open_event(i))
                row('','art','Artwork',self.open_art)
            row('','library','Shared Unit Library',self.app.open_library)
            for item in selection:
                if self.tree.exists(item):self.tree.selection_set(item)
        finally:self.tree_refreshing=False

    def select_tree(self,_=None,force=False):
        if self.tree_refreshing:return
        selected=self.tree.selection()
        if selected and selected[0] in self.tree_actions:
            if selected[0]==self.last_tree_selection and not force:return
            self.record_navigation();self.last_tree_selection=selected[0];guard(self.app,self.tree_actions[selected[0]]);self.record_navigation()

    def tree_menu(self,event):
        selected=self.tree.identify_row(event.y)
        if selected:self.tree.selection_set(selected)
        menu=tk.Menu(self.window,tearoff=False)
        for action in ('New definition','Duplicate definition','Delete definition'):
            menu.add_command(label=action,command=lambda a=action:self.invoke(a))
        try:menu.tk_popup(event.x_root,event.y_root)
        finally:menu.grab_release()

    def update_inspector(self):
        if not hasattr(self,'app'):return
        owner=self.active_owner();view=self.current_view()
        for panel in self.custom_inspectors.values():panel.pack_forget()
        custom=self.custom_inspectors.get(view.key) if view else None
        if custom is not None:
            self.inspect_generic.pack_forget();custom.pack(fill='both',expand=True);return
        self.inspect_generic.pack(fill='both',expand=True)
        self.inspect_title.set(view.caption if view else 'Selection')
        scope=scope_of(owner);document=scope.document if scope else None
        lines=[('Shared library design' if scope and scope.owner.library_context else 'Project')]
        if document:lines.append(document.manifest['title'])
        for child in self.inspect_actions.winfo_children():child.destroy()
        if hasattr(owner,'current') and owner.current and hasattr(owner,'item'):
            value=owner.item();lines.extend([value.get('name',value['id']),value['id']])
            if 'mass_tons' in value:lines.extend([str(value['mass_tons'])+' tons',str(value.get('price',0))+' C-bills'])
            if owner.collection in ('mechs','people'):
                for label,callback in [('Edit sprite',owner.edit_unit_sprite),('Choose sprite',owner.choose_sprite)]:ttk.Button(self.inspect_actions,text=label,command=lambda f=callback:guard(owner,f)).pack(fill='x',pady=3)
            if owner.library_context:ttk.Button(self.inspect_actions,text='Preview design',command=lambda:self.invoke('Preview library design')).pack(fill='x',pady=3)
        elif view and view.key[1]=='construction' and owner.profile:
            from construction_editing import part_name
            p=owner.profile;lines.extend([p['name'],f"{len(p['footprint'][0])} × {len(p['footprint'])} footprint",'Paint height: 0 erases a cell. Walls support 1–3 storeys; buildings 1–8.'])
            if owner.selected_role:
                lines.extend([part_name(owner.selected_role),'This tile is shared by every matching part in the set. Clone it before making a separate variant.'])
                for label,callback in [('Choose tile',owner.choose_part),('Edit pixels',owner.edit_part),('Clone tile',owner.clone_part)]:ttk.Button(self.inspect_actions,text=label,command=lambda f=callback:guard(owner,f)).pack(fill='x',pady=3)
        elif view and view.key[1]=='patterns' and owner.current():
            p=owner.current();lines.extend([p['name'],f"{len(p['rows'][0])} × {len(p['rows'])} tiles",'Saved with this project. Export includes the tile definitions and owned artwork.'])
        elif hasattr(owner,'scene'):
            scene=owner.scene();lines.extend([scene['name'],scene['id'],f'{len(scene["rows"][0])} x {len(scene["rows"])} tiles'])
            marker=owner.selected_marker
            if marker and marker[0] in ('entrance','npc'):
                entrance=next((e for e in scene['entrances'] if e['id']==marker[2]),None)
                if entrance:
                    lines.extend([entrance['name'],'Position: '+str(entrance['at'])])
                    ttk.Button(self.inspect_actions,text='Edit entrance',command=lambda:guard(owner,owner.edit_marker)).pack(fill='x',pady=3)
                    ttk.Button(self.inspect_actions,text='Open event',command=lambda:self.open_event(entrance['event'])).pack(fill='x',pady=3)
                    event=next((e for e in owner.adventure['events'] if e['id']==entrance['event']),None)
                    if event and event['op']=='transfer':ttk.Button(self.inspect_actions,text='Open destination map',command=lambda:self.open_map(event['map'])).pack(fill='x',pady=3)
        else:lines.append('Select an object to edit its properties. Changes belong to the scope shown above.')
        self.inspect_text.set('\n\n'.join(lines))

    def problem(self,scope,problem):
        self.problems.append(problem);index=str(len(self.problems)-1)
        title=scope.document.manifest['title'] if scope.document else 'Editor'
        self.problem_list.insert('','end',iid=index,values=(title,problem['message']))
        if str(self.bottom) not in self.vertical.panes():self.vertical.add(self.bottom,weight=1)
        self.bottom.select(self.problem_page);self.status.set(problem['message'])
        self.log(problem.get('details') or problem['message'])

    def open_problem(self,_=None):
        selected=self.problem_list.selection()
        if not selected:return
        problem=self.problems[int(selected[0])];owner=problem['owner']
        if owner.window.winfo_exists():
            owner.window.lift();owner.window.focus_set()
            if hasattr(owner,'show_error'):
                from editor_session import FieldError
                owner.show_error(FieldError(problem['message'],problem.get('field')))
        else:self.log(problem.get('details') or problem['message']);self.bottom.select(self.output)

    def log(self,text):
        self.output.configure(state='normal');self.output.insert('end',text+'\n');self.output.see('end');self.output.configure(state='disabled')

    def show_welcome(self):
        previous=self.views.get((id(None),'welcome',None))
        if previous:previous.lift();return
        pane=self.add_view(None,None,'welcome','Welcome')
        ttk.Label(pane,text='BattleTech Construction Kit',style='Title.TLabel',padding=24).pack(anchor='w')
        ttk.Label(pane,text='Create a campaign, edit maps and artwork, and play your game.',padding=(24,0)).pack(anchor='w')
        buttons=ttk.Frame(pane,padding=24);buttons.pack(anchor='w')
        for title,callback in [('New project',self.app.new_project),('Open project',self.app.open_project),('Unit Library',self.app.open_library)]:ttk.Button(buttons,text=title,command=lambda f=callback:guard(self.app,f)).pack(side='left',padx=4)
        ttk.Label(pane,text='Recent projects',font='TkHeadingFont',padding=(24,8)).pack(anchor='w')
        for path in self.layout.get('recent',[])[:8]:
            ttk.Button(pane,text=str(path),command=lambda p=path:guard(self.app,lambda:self.open_project_path(p))).pack(anchor='w',padx=24,pady=3)

    def open_project_path(self,path):
        from editor_model import ProjectDocument
        if self.app.discard_or_save():self.app.set_document(ProjectDocument(Path(path),self.validator),check=False)

    def new_project(self):
        from adventure_editor import Form
        from editor_model import create_project,EditorError
        from tkinter import filedialog
        if not self.app.discard_or_save():return
        root=Path(__file__).resolve().parents[1]
        templates={'Independent adventure':root/'examples/beacon-demo','BattleTech campaign':root/'examples/battletech-demo','Vehicles and planets':root/'examples/vehicle-lab'}
        if self.app.document:templates={'Current project':self.app.document.root,**templates}
        form=Form(self.app,'New project')
        form.field('title','My campaign');form.field('package_id','my-campaign',label='Project ID')
        form.field('template',next(iter(templates)),list(templates))
        form.field('directory',str(root/'work'/'my-campaign'),label='New project folder')
        def browse():
            path=filedialog.askdirectory(parent=form.window,title='Choose a parent folder')
            if path:form.values['directory'].set(str(Path(path)/form.values['package_id'].get()))
        ttk.Button(form.body,text='Choose parent folder...',command=browse).grid(row=form.row,column=1,sticky='e');form.row+=1
        ttk.Label(form.body,text='The independent template needs no original files. A project\nretains the resource requirements of its chosen template.',wraplength=510).grid(row=form.row,column=0,columnspan=2,sticky='w',pady=12);form.row+=1
        def create(values):
            identity=values['package_id']
            if not identity or not identity[0].islower() or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in identity):raise EditorError('Use a lowercase letter first, followed by lowercase letters, digits or hyphens.')
            document=create_project(templates[values['template']],Path(values['directory']).expanduser(),identity,values['title'],self.validator)
            self.app.set_document(document,check=False)
        form.submit(create);return form

    def project_changed(self):
        self.window.after_idle(lambda:self.recovery.offer(self.app._editor_scope))
        path=str(self.app.document.root)
        self.layout['recent']=[path]+[p for p in self.layout.get('recent',[]) if p!=path][:7]
        self.refresh_tree();self.app.window.lift()
        saved=self.layout.get('projects',{}).get(path)
        if saved:self.window.after_idle(lambda:self.restore_tabs(saved))

    def project_replacing(self,scope):
        if getattr(scope,'saving',False):
            from editor_model import EditorError
            raise EditorError('A save is in progress. Wait for it to finish before switching projects.')
        # Notebook pages are siblings, so replacing a project must retire all
        # its views explicitly rather than rely on a Toplevel's child teardown.
        self.persist_layout()
        self.recovery.clear(scope)
        for view in list(self.views.values()):
            if view.scope is scope and view.controller is not scope.owner and view.key[1]!='library':view.destroy()
        scope.live();self.last_tree_selection=None

    def restore_tabs(self,saved):
        self.restoring=True
        try:
            for entry in saved.get('tabs',[]):
                try:
                    kind=entry['kind'];identity=entry.get('identity');owner=self.app
                    if kind=='roster':view=owner.window
                    elif kind=='maps':view=self.map_view().window
                    elif kind=='world':self.open_world();view=owner.map_editor.world_editor.window
                    elif kind=='graphics':view=self.open_art().window
                    elif kind=='events':view=self.map_view().event_graph().window
                    elif kind=='construction':view=self.map_view().construction(identity).window
                    elif kind=='patterns':view=self.map_view().patterns().window
                    elif kind=='jigsaw':
                        from world_editor import JigsawEditor
                        maps=self.map_view();maps.edit_landscape();world=maps.world_editor
                        jigsaw=next(j for j in owner.document.adventure.get('jigsaws',[]) if j['id']==identity)
                        view=open_view(world,'jigsaw',lambda:JigsawEditor(world,jigsaw),identity).window
                    elif kind=='pixels':
                        from graphics_editor import open_image_editor
                        image=next(i for i in owner.document.art['images'] if i['id']==identity)
                        view=open_image_editor(owner.graphics_editor(),image).window
                    else:continue
                    self.restore_view(view,entry.get('state',{}))
                except (KeyError,ValueError,StopIteration):continue
            selected=saved.get('active')
            if selected:
                view=next((v for v in self.views.values() if v.scope is self.app._editor_scope and [v.key[1],v.key[2]]==selected),None)
                if view:view.lift()
        finally:self.restoring=False

    def command_picker(self):
        dialog=tk.Toplevel(self.window);dialog.title('Find command');dialog.transient(self.window)
        query=tk.StringVar();entry=ttk.Entry(dialog,textvariable=query,width=50);entry.pack(fill='x',padx=12,pady=12)
        listing=tk.Listbox(dialog,width=55,height=16);listing.pack(fill='both',expand=True,padx=12,pady=(0,12))
        def refresh(*_):
            listing.delete(0,'end')
            for name in self.actions:
                if query.get().casefold() in name.casefold():listing.insert('end',name)
            if listing.size():listing.selection_set(0)
        def choose(_=None):
            if listing.curselection():name=listing.get(listing.curselection()[0]);dialog.destroy();self.invoke(name)
        query.trace_add('write',refresh);refresh();entry.focus_set();dialog.grab_set()
        entry.bind('<Return>',choose);listing.bind('<Return>',choose);listing.bind('<Double-1>',choose);dialog.bind('<Escape>',lambda _:dialog.destroy())

    def help(self):
        self.log('Ctrl+S: save active project or library design | Ctrl+Z / Ctrl+Y: undo / redo\n'
            'Ctrl+Shift+Z: redo | Ctrl+Tab: next tab | Ctrl+W: close tab\n'
            'Ctrl+Shift+P: find command | F5: play from start | Escape: cancel the current gesture\n'
            'Ctrl + mouse wheel: zoom at the pointer on map, world, graph and art canvases.\n'
            'Zoom boxes accept a percentage followed by Enter; map tools stay visible above the canvas.\n\n'
            'Save project gathers every project tab. Library designs save separately; Save all reports each scope.\n'
            'If you edit during save validation, save again when prompted; nothing is written by the outdated validation.\n'
            'Double-click a Problem to find its editor. View > Reset layout restores hidden panels.\n'
            'File > Recovery drafts reviews unfinished work without publishing it into a game.\n'
            'Play uses a private snapshot and private saves. Play > Stop test stops only this session.\n\n'
            'Workspace guide: '+str(Path(__file__).resolve().parents[1]/'docs/EDITOR_WORKSPACE.md'))
        if str(self.bottom) not in self.vertical.panes():self.vertical.add(self.bottom,weight=1)
        self.bottom.select(self.output)

    def toggle_panel(self,host,pane):
        if str(pane) in host.panes():host.forget(pane)
        else:
            if pane is self.explorer:host.insert(0,pane,weight=1)
            else:host.add(pane,weight=1)

    def reset_layout(self):
        for pane in tuple(self.horizontal.panes()):self.horizontal.forget(pane)
        for pane in (self.explorer,self.centre,self.inspector):
            if str(pane) not in self.horizontal.panes():self.horizontal.add(pane,weight=5 if pane is self.centre else 1)
        if str(self.bottom) not in self.vertical.panes():self.vertical.add(self.bottom,weight=1)
        self.window.update_idletasks()
        self.horizontal.sashpos(0,210);self.horizontal.sashpos(1,max(680,self.window.winfo_width()-240))
        self.vertical.sashpos(0,max(340,self.vertical.winfo_height()-155))

    def restore_layout(self):
        if 'scale' in self.layout:self.scale(self.layout['scale'])
        self.reset_layout()
        geometry=self.layout.get('geometry')
        if geometry:
            # A disconnected monitor must not leave the editor off screen.
            import re
            match=re.fullmatch(r'(\d+)x(\d+)\+(-?\d+)\+(-?\d+)',geometry)
            if match:
                w,h,x,y=map(int,match.groups());sw,sh=self.window.winfo_screenwidth(),self.window.winfo_screenheight()
                self.window.geometry(f'{min(w,sw)}x{min(h,sh)}+{max(0,min(x,sw-min(w,sw)))}+{max(0,min(y,sh-min(h,sh)))}')
        self.window.after_idle(self.restore_sashes)

    def restore_sashes(self):
        if not self.window.winfo_exists():return
        self.reset_layout()
        for host,key in ((self.horizontal,'horizontal'),(self.vertical,'vertical')):
            extent=host.winfo_width() if host is self.horizontal else host.winfo_height()
            for i,fraction in enumerate(self.layout.get(key,[])):
                if i<len(host.panes())-1:host.sashpos(i,int(max(.1,min(.9,fraction))*extent))
        for name,pane,host in [('explorer',self.explorer,self.horizontal),('inspector',self.inspector,self.horizontal),('bottom',self.bottom,self.vertical)]:
            if name in self.layout.get('hidden',['bottom']) and str(pane) in host.panes():host.forget(pane)

    def persist_layout(self):
        self.layout['geometry']=self.window.geometry()
        for host,key in ((self.horizontal,'horizontal'),(self.vertical,'vertical')):
            extent=host.winfo_width() if host is self.horizontal else host.winfo_height()
            self.layout[key]=[host.sashpos(i)/max(1,extent) for i in range(len(host.panes())-1)]
        self.layout['hidden']=[name for name,pane,host in [('explorer',self.explorer,self.horizontal),('inspector',self.inspector,self.horizontal),('bottom',self.bottom,self.vertical)] if str(pane) not in host.panes()]
        if self.app.document:
            tabs=[dict(kind=v.key[1],identity=v.key[2],state=self.view_state(v)) for v in self.views.values() if v.scope is self.app._editor_scope and v.key[1]!='library' and self.tabs.tab(v,'state')!='hidden']
            active=self.current_view()
            self.layout.setdefault('projects',{})[str(self.app.document.root)]=dict(tabs=tabs,active=[active.key[1],active.key[2]] if active else None)
        self.state_dir.mkdir(parents=True,exist_ok=True)
        from editor_model import ProjectDocument,encoded
        ProjectDocument.atomic_file(self.layout_file,encoded(self.layout))

    def poll(self):
        if self.closing:return
        self.recovery.tick()
        self.update_commands()
        from editor_history import refresh_scope
        for current in self.scopes:
            if not current.owner.window.winfo_exists() or not current.document:continue
            revision=(id(current.document),current.document.revision)
            if getattr(current,'seen_revision',None)!=revision:
                current.seen_revision=revision;refresh_scope(self,current)
        scope=self.app._editor_scope
        signature=(id(self.app.document),len(self.app.document.undo_stack) if self.app.document else 0,id(self.app.document.content) if self.app.document else 0,id(self.app.document.adventure) if self.app.document else 0)
        if signature!=self.last_signature:self.last_signature=signature;self.refresh_tree();self.update_inspector()
        dirt={id(s):s.dirty() for s in self.scopes if s.owner.window.winfo_exists()}
        if self.app.document:self.window.title('BattleTech Construction Kit - '+self.app.document.manifest['title']+(' *' if dirt.get(id(scope)) else ''))
        for pane in self.views.values():
            if pane.scope and pane.scope.document:
                title=pane.caption if len(pane.caption)<=22 else pane.caption[:19]+'...'
                if dirt.get(id(pane.scope)):title+=' *'
                if self.tabs.tab(pane,'text')!=title:self.tabs.tab(pane,text=title)
        self.timer=self.window.after(300,self.poll)

    def close(self):
        if any(self.tasks.busy(s) for s in self.scopes):self.status.set('A durable operation is finishing. Close the editor after it completes.');return
        dirty=[s for s in self.scopes if s.owner.window.winfo_exists() and s.dirty()]
        if dirty:
            titles='\n'.join(s.document.manifest['title'] for s in dirty if s.document)
            answer=messagebox.askyesnocancel('Unsaved changes','Save these scopes before closing?\n\n'+titles,parent=self.window)
            if answer is None:return
            if answer:
                self.save_all_async(lambda ok:self.finish_close() if ok and not any(s.dirty() for s in self.scopes if s.owner.window.winfo_exists()) else None)
                return
        self.finish_close()

    def finish_close(self):
        self.persist_layout();self.closing=True
        for scope in self.scopes:
            if scope.owner.window.winfo_exists() and scope.document:self.recovery.clear(scope)
        if self.timer:self.window.after_cancel(self.timer)
        self.window.destroy()


def create_editor(window,validator,state_dir):
    workspace=Workspace(window,validator,state_dir)
    return workspace.app
