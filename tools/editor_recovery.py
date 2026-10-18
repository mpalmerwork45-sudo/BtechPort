"""Private, versioned editor drafts, distinct from package and game saves.

Records contain data and a whitelist of built-in form routes, never executable
callbacks. Restoring a conflicting baseline requires a new directory.
"""
from __future__ import annotations
import base64
import copy
import functools
import hashlib
import json
from pathlib import Path
import time
import tkinter as tk
from tkinter import ttk, filedialog
from editor_model import EditorError, ProjectDocument, child, encoded
from editor_session import guard, scope_of

FIELDS=('content','adventure','art','manifest','metadata')
ROUTES={
 'RosterEditor': 'mount_dialog new_definition installed_equipment choose_sprite ammunition',
 'AdventureEditor': 'new_map map_properties overlay_dialog capture_building place_building move_building edit_tile entrance_dialog encounter_dialog service_template person_dialog shop_dialog flag_dialog start_dialog',
 'GraphicsEditor': 'new import_file original binding',
 'PixelEditor': 'rename_layer resize_dialog',
 'WorldEditor': 'new_world rename_world generate city_form',
 'EventGraph': 'link branch',
 'ObjectiveEditor': 'edit',
 'LibraryBrowser': 'new',
}


def recoverable_forms(cls):
    """Explicit registration, also used as the restore-time method whitelist."""
    for name in ROUTES.get(cls.__name__,'').split():
        original=getattr(cls,name)
        @functools.wraps(original)
        def wrapped(self,*args,_method=original,_name=name,**kwargs):
            previous=getattr(self,'_form_action',None)
            self._form_action=dict(method=_name,args=args,kwargs=kwargs)
            try:return _method(self,*args,**kwargs)
            finally:self._form_action=previous
        setattr(cls,name,wrapped)
    return cls


def pack(value):
    if isinstance(value,bytes):return {'$bytes':base64.b64encode(value).decode('ascii')}
    if isinstance(value,Path):return {'$path':str(value)}
    if isinstance(value,tuple):return {'$tuple':[pack(v) for v in value]}
    if isinstance(value,list):return [pack(v) for v in value]
    if isinstance(value,dict):return {k:pack(v) for k,v in value.items()}
    return value


def unpack(value):
    if isinstance(value,list):return [unpack(v) for v in value]
    if isinstance(value,dict):
        if set(value)=={'$bytes'}:return base64.b64decode(value['$bytes'],validate=True)
        if set(value)=={'$path'}:return Path(value['$path'])
        if set(value)=={'$tuple'}:return tuple(unpack(v) for v in value['$tuple'])
        return {k:unpack(v) for k,v in value.items()}
    return value


def describe(view,workspace):
    if hasattr(view,'values') and hasattr(view,'callback'):
        return dict(kind='form',title=view.window.title(),action=getattr(view,'recovery_action',None),owner=describe(view.owner,workspace))
    pane=view.window
    if not hasattr(pane,'key'):return dict(kind='unmapped',title=pane.title())
    return dict(kind=pane.key[1],identity=pane.key[2],state=workspace.view_state(pane),
                inspector=type(view).__name__=='EventProperties')


def identity(scope):
    context=getattr(scope.owner,'library_context',None)
    return ('library:'+str(context.browser.library.root)+':'+context.bundle['entry_id']) if context else 'project:'+str(scope.document.root)


def capture(scope):
    document=scope.document
    drafts=[]
    for draft in scope.live():
        if not draft.pending():continue
        state=copy.deepcopy(draft.capture())
        # Undo snapshots are already bounded separately; recovery needs only
        # the current work, not forty duplicate copies of every bitmap.
        for key in ('history','future'):state.pop(key,None)
        drafts.append(dict(view=describe(draft.view,scope.workspace),state=state))
    context=getattr(scope.owner,'library_context',None)
    return dict(version=1,identity=identity(scope),title=document.manifest['title'],root=str(document.root),
        baseline=document.snapshot,state={k:getattr(document,k) for k in FIELDS},drafts=drafts,
        library=dict(root=str(context.browser.library.root),bundle=context.bundle) if context else None)


def conflicts(record,document):
    if record.get('library'):
        return False  # The caller checks the library's independent revision.
    return record['baseline'] != document.snapshot


def restore_document(record,document):
    if conflicts(record,document):raise EditorError('Recovery baseline differs from the current files. Recover into a copy.')
    with document.command('Recover unsaved edits'):
        document.replace_all(*(copy.deepcopy(record['state'][k]) for k in FIELDS))


def open_route(scope,route,cache=None):
    key=json.dumps(pack(route),sort_keys=True)
    if cache is not None and key in cache:return cache[key]
    workspace=scope.workspace;owner=scope.owner;kind=route['kind'];ident=route.get('identity')
    if kind=='form':
        parent=open_route(scope,route['owner'],cache);action=route.get('action')
        if not action:raise EditorError('This form has no restore route; its values remain available in Review.')
        method=action['method'];allowed=set()
        for cls in type(parent).__mro__:allowed.update(ROUTES.get(cls.__name__,'').split())
        before={id(d) for d in scope.live()}
        if method=='animation_action' and getattr(parent,'shared_art',False):
            from action_tracks import edit_track
            edit_track(parent)
        elif method=='enemy' and hasattr(parent,'recovery_children'):
            parent.recovery_children['enemy'](*action.get('args',[]))
        elif method in allowed:getattr(parent,method)(*action.get('args',[]),**action.get('kwargs',{}))
        else:raise EditorError('Unknown recovery form route. The draft was retained for review.')
        return next(d.view for d in scope.live() if id(d) not in before and hasattr(d.view,'callback'))
    if kind in ('roster','library-unit'):view=owner
    elif kind=='graphics':view=owner.graphics_editor()
    elif kind=='pixels':
        from graphics_editor import open_image_editor
        image=next(i for i in scope.document.art['images'] if i['id']==ident)
        view=open_image_editor(owner.graphics_editor(),image)
    elif kind in ('maps','world','events','jigsaw','objectives'):
        owner.edit_adventure();maps=owner.map_editor
        if kind=='maps':view=maps
        elif kind=='events':view=maps.event_graph()
        elif kind=='objectives':view=maps.event_graph().objectives()
        else:
            maps.edit_landscape();view=maps.world_editor
            if kind=='jigsaw':
                from world_editor import JigsawEditor
                from editor_workspace import open_view
                jigsaw=next(j for j in scope.document.adventure['jigsaws'] if j['id']==ident)
                view=open_view(view,'jigsaw',lambda:JigsawEditor(view,jigsaw),ident)
    else:raise EditorError('Recovery view unavailable: '+kind)
    workspace.restore_view(view.window,route.get('state',{}))
    if route.get('inspector'):view=view.properties
    return view


class Recovery:
    def __init__(self,workspace):
        self.workspace=workspace;self.root=workspace.state_dir/'recovery'
        self.root.mkdir(parents=True,exist_ok=True)
        self.last={};self.offered=set();self.last_check=0;self.restoring=False

    def path(self,scope):return self.root/(hashlib.sha256(identity(scope).encode()).hexdigest()+'.json')

    def write(self,scope):
        if not scope.document or not scope.owner.window.winfo_exists():return
        if not scope.dirty():self.clear(scope);return
        record=capture(scope);payload=pack(record);digest=hashlib.sha256(encoded(payload)).hexdigest()
        if self.last.get(record['identity'])==digest:return
        payload['timestamp']=time.time();data=encoded(payload)
        if len(data)>128*1024*1024:raise EditorError('Draft recovery exceeds the 128 MiB safety limit. Save a working copy.')
        ProjectDocument.atomic_file(self.path(scope),data);self.last[record['identity']]=digest

    def clear(self,scope):
        if not scope.document:return
        if identity(scope) in self.pending():return
        path=self.path(scope)
        if path.exists():path.unlink()
        self.last.pop(identity(scope),None)

    def tick(self):
        if self.restoring or time.monotonic()-self.last_check<2:return
        self.last_check=time.monotonic()
        for scope in self.workspace.scopes:
            if scope.owner.window.winfo_exists() and scope.document and identity(scope) not in self.pending():
                guard(scope.owner,lambda s=scope:self.write(s))

    def pending(self):return getattr(self,'awaiting',set())

    def read(self,path):
        if path.stat().st_size>128*1024*1024:raise EditorError('Recovery file is too large.')
        record=unpack(json.loads(path.read_bytes()))
        if record.get('version')!=1:raise EditorError('Unknown recovery version; draft retained.')
        return record

    def offer(self,scope):
        if not scope.document:return
        key=identity(scope);path=self.path(scope)
        if key in self.offered or not path.exists():return
        self.offered.add(key)
        if not hasattr(self,'awaiting'):self.awaiting=set()
        self.awaiting.add(key)
        record=self.read(path)
        window=tk.Toplevel(self.workspace.window);window.title('Recover unfinished work');window.transient(self.workspace.window);window.grab_set()
        stamp=time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(record['timestamp']))
        ttk.Label(window,text=f"Unfinished edits: {record['title']}\nCaptured {stamp}\n{record['identity']}",wraplength=650,padding=12).pack(fill='x')
        conflict=conflicts(record,scope.document)
        context=getattr(scope.owner,'library_context',None)
        if context:conflict=record['library']['bundle']['revision']!=context.bundle['revision']
        if conflict:ttk.Label(window,text='The saved files changed. Recover into a separate project copy to preserve both versions.',wraplength=650,padding=12).pack(fill='x')
        detail=tk.Text(window,width=85,height=16,wrap='word',font='TkFixedFont');detail.insert('1.0',json.dumps(pack(record['drafts']),indent=2));detail.configure(state='disabled')
        bar=ttk.Frame(window,padding=12);bar.pack(fill='x')
        def finish():
            if not getattr(scope,'unrestored_recovery',False):self.awaiting.discard(key)
            window.destroy()
        def recover():
            target=scope
            if conflict:
                folder=filedialog.askdirectory(parent=window,title='Choose an empty directory for recovered project')
                if not folder:return
                root=Path(folder)
                if any(root.iterdir()):raise EditorError('Choose an empty directory; existing files will be preserved.')
                for name,data in record['baseline'].items():
                    file=child(root,name);file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(data)
                document=ProjectDocument(root,scope.owner.validator)
                if self.workspace.app._editor_scope.dirty():
                    raise EditorError('Save or close the current project before opening the recovered copy. The baseline copy is available at '+str(root))
                self.workspace.app.set_document(document);target=self.workspace.app._editor_scope
            self.restore(target,record,allow_copy=conflict)
            # Keep the recovery until a successful save or explicit discard.
            self.last.pop(key,None);finish()
        def discard():path.unlink(missing_ok=True);finish()
        ttk.Button(bar,text='Recover into copy' if conflict else 'Recover',command=lambda:guard(scope.owner,recover)).pack(side='left',padx=4)
        ttk.Button(bar,text='Review fields',command=lambda:detail.pack(fill='both',expand=True,before=bar,padx=12,pady=6)).pack(side='left',padx=4)
        ttk.Button(bar,text='Discard recovery',command=discard).pack(side='right',padx=4)
        # Closing the prompt leaves the record protected from autosave until
        # the user explicitly revisits it through File > Recovery drafts.
        window.protocol('WM_DELETE_WINDOW',window.destroy)

    def restore(self,scope,record,allow_copy=False):
        self.restoring=True
        try:
            if allow_copy:
                with scope.document.command('Recover into copy'):scope.document.replace_all(*(copy.deepcopy(record['state'][k]) for k in FIELDS))
            else:restore_document(record,scope.document)
            from editor_history import refresh_scope
            refresh_scope(self.workspace,scope)
            # Restore parent drafts first; nested forms then bind to the same
            # tracked list, preserving enemy placement edits and invalid text.
            restored={}
            # Build views while the roster/event inputs still contain valid
            # document values. Navigation must not submit recovered bad text.
            for entry in record['drafts']:
                if entry['view']['kind']!='form':
                    route=entry['view'];key=json.dumps(pack(route),sort_keys=True)
                    try:restored[key]=open_route(scope,route,restored)
                    except Exception:pass  # Report below, preserving the entry.
            entries=sorted(record['drafts'],key=lambda e:0 if e['view']['kind']=='form' else 1)
            for entry in entries:
                route=entry['view'];key=json.dumps(pack(route),sort_keys=True)
                try:
                    view=open_route(scope,route,restored);state=copy.deepcopy(entry['state'])
                    if getattr(view,'shared_art',False):state.update(history=[],future=[])
                    view.restore_draft(state);restored[key]=view
                    if hasattr(view,'on_restore'):view.on_restore()
                except Exception as error:
                    if not hasattr(self,'awaiting'):self.awaiting=set()
                    self.awaiting.add(identity(scope))
                    scope.unrestored_recovery=True
                    self.workspace.log('Recovery retained a field draft for review: '+str(error)+'\n'+json.dumps(pack(entry),indent=2))
                    self.workspace.status.set('Some recovered fields need review in Output. The recovery record is retained.')
            scope.seen_revision=(id(scope.document),scope.document.revision)
        finally:self.restoring=False

    def browse(self):
        from editor_pickers import named_choice
        paths=sorted(self.root.glob('*.json'),key=lambda p:p.stat().st_mtime,reverse=True)
        if not paths:self.workspace.status.set('No unsaved recovery drafts.');return
        window=tk.Toplevel(self.workspace.window);window.title('Recovery drafts');window.transient(self.workspace.window)
        listing=tk.Listbox(window,width=100,height=12);listing.pack(fill='both',expand=True,padx=12,pady=12)
        records=[self.read(path) for path in paths]
        for record in records:listing.insert('end',record['title']+' — '+record['identity'])
        def open_selected():
            selected=listing.curselection()
            if not selected:return
            record=records[selected[0]]
            if record.get('library'):
                self.workspace.app.open_library();browser=self.workspace.app.unit_library_window
                if str(browser.library.root)!=record['library']['root']:raise EditorError('Open the recorded library folder first: '+record['library']['root'])
                browser.refresh(record['library']['bundle']['entry_id']);editor=browser.edit();scope=editor._editor_scope
            else:
                if not self.workspace.app.discard_or_save():return
                self.workspace.app.set_document(ProjectDocument(Path(record['root']),self.workspace.validator),check=False);scope=self.workspace.app._editor_scope
            self.offered.discard(identity(scope));window.destroy();self.offer(scope)
        ttk.Button(window,text='Open and review',command=lambda:guard(self.workspace.app,open_selected)).pack(pady=8)
