"""Shared styles/patterns beside the existing project designers."""
import copy
import tkinter as tk
from pathlib import Path
from tkinter import ttk,filedialog
from types import SimpleNamespace
from construction_library import ConstructionLibrary,DEFAULT_ROOT,KINDS,closure,import_bundle,preview_files,rows,summary
from editor_model import EditorError,ProjectDocument,encoded
from editor_session import guard,scope_of,visible_parent
from editor_workspace import view_window,open_view,workspace_of
from editor_tasks import snapshot,signature
from tile_editing import metadata
from editor_recovery import recoverable_forms


@recoverable_forms
class ConstructionBrowser:
    def __init__(self,maps):
        self.owner=maps;self.document=maps.document;self.selected=None;self.bundles=[];self.photos=[];self.workshops=[]
        self.library=ConstructionLibrary(maps.parent.settings.get('construction-library-root',DEFAULT_ROOT),self.document.validator)
        self.window=view_window(self,maps,'construction-library','Construction Library')
        self.status=tk.StringVar(value='Tiles, buildings, walls, roads and patterns shared between projects.')
        self.kind=tk.StringVar(value='All');self.query=tk.StringVar();self.generation=0;self.load_generation=0
        self.location=tk.StringVar(value=str(self.library.root))
        heading=ttk.Frame(self.window,padding=10);heading.pack(fill='x')
        ttk.Label(heading,text='Construction Library',style='Heading.TLabel').pack(side='left')
        ttk.Button(heading,text='Library folder...',command=lambda:guard(self,self.folder)).pack(side='right')
        location_label=ttk.Label(self.window,textvariable=self.location,style='Muted.TLabel',padding=(10,0))
        location_label.pack(fill='x')
        help_label=ttk.Label(self.window,text='Edit shared designs directly in a private workshop and test them on its canvas. Import copies into '+self.document.manifest['title']+' when ready.',
                  padding=10,wraplength=800);help_label.pack(fill='x')
        for label in (location_label,help_label):
            label.bind('<Configure>',lambda event,w=label:w.configure(wraplength=max(100,event.width-20)))
        bar=ttk.Frame(self.window,padding=(8,0));bar.pack(fill='x');self.buttons={}
        for label,callback in [('Edit in library',self.edit),('New shared design...',self.new),('Import into project',self.import_selected),('Import and edit',lambda:self.import_selected(True)),
                               ('Save project design...',self.export_dialog),('Load bundle...',self.load_file),
                               ('Export bundle...',self.export_file),('Refresh',self.reload)]:
            button=ttk.Button(bar,text=label,width=0,command=lambda f=callback:guard(self,f));button.pack(side='left',padx=3,pady=3)
            self.buttons[label]=button
        from editor_ui import flow_toolbar
        flow_toolbar(bar)
        # Keep the actual preview useful in a short dock: its explanation and
        # folder path are secondary to the always-visible transfer controls.
        self.compact=None
        def layout(event):
            if event.widget is not self.window:return
            compact=event.height<600
            if compact==self.compact:return
            self.compact=compact
            for label in (location_label,help_label):
                if compact:label.pack_forget()
                else:label.pack(fill='x',before=bar)
        self.window.bind('<Configure>',layout,add='+')
        filters=ttk.Frame(self.window,padding=10);filters.pack(fill='x')
        box=ttk.Combobox(filters,textvariable=self.kind,values=['All',*KINDS],state='readonly',width=12);box.pack(side='left')
        box.bind('<<ComboboxSelected>>',lambda _:self.refresh())
        ttk.Label(filters,text='Search').pack(side='left',padx=(12,4))
        entry=ttk.Entry(filters,textvariable=self.query);entry.pack(side='left',fill='x',expand=True)
        entry.bind('<Return>',lambda _:guard(self,self.refresh))
        ttk.Button(filters,text='Search',command=lambda:guard(self,self.refresh)).pack(side='left',padx=4)
        ttk.Label(self.window,textvariable=self.status,wraplength=850,padding=10).pack(side='bottom',fill='x')
        body=ttk.Panedwindow(self.window,orient='horizontal');body.pack(fill='both',expand=True,padx=10,pady=10)
        left=ttk.Frame(body);right=ttk.Frame(body);body.add(left,weight=1);body.add(right,weight=2)
        self.listing=ttk.Treeview(left,columns=('kind',),selectmode='browse')
        self.listing.heading('#0',text='Design');self.listing.heading('kind',text='Type')
        self.listing.column('#0',width=210);self.listing.column('kind',width=75,stretch=False)
        scroll=ttk.Scrollbar(left,command=self.listing.yview);scroll.pack(side='right',fill='y')
        self.listing.configure(yscrollcommand=scroll.set);self.listing.pack(fill='both',expand=True)
        self.listing.bind('<<TreeviewSelect>>',lambda _:guard(self,self.select))
        self.listing.bind('<Double-1>',lambda _:guard(self,self.edit))
        self.detail=tk.StringVar();detail_label=ttk.Label(right,textvariable=self.detail,wraplength=470,padding=6);detail_label.pack(fill='x')
        detail_label.bind('<Configure>',lambda event:detail_label.configure(wraplength=max(100,event.width-12)))
        self.canvas=tk.Canvas(right,background='#273b45',highlightthickness=0,width=480,height=320);self.canvas.pack(fill='both',expand=True)
        self.canvas.bind('<Configure>',lambda _:self.draw())
        self.preview=None;self.reload()

    def current(self):
        value=next((b for b in self.bundles if b['entry_id']==self.selected),None)
        if value is None:raise EditorError('Select a library design first.')
        return value

    def reload(self,selected=None):
        library=self.library;self.load_generation+=1;generation=self.load_generation
        def done(values):
            if self.library is not library or generation!=self.load_generation:return
            self.bundles=values;self.preview_key=None
            if selected:self.selected=selected
            self.refresh()
        workspace=workspace_of(self)
        if workspace:workspace.tasks.submit('Loading Construction Library',self,lambda cancel:library.entries(),done)
        else:done(library.entries())

    def refresh(self):
        from asset_catalogue import matches
        self.listing.delete(*self.listing.get_children())
        values=[b for b in self.bundles if (self.kind.get()=='All' or b['kind']==self.kind.get()) and matches(summary(b),self.query.get())]
        for b in values:self.listing.insert('','end',iid=b['entry_id'],text=b['name'],values=(b['kind'],))
        if self.selected not in {b['entry_id'] for b in values}:self.selected=values[0]['entry_id'] if values else None
        if self.selected:self.listing.selection_set(self.selected);self.listing.see(self.selected)
        else:
            self.generation+=1;self.preview_key=None;self.preview=None;self.draw()
            self.detail.set('No matching designs. Use Save project design, or Save to library in a designer or the project Pattern Library.')
        self.status.set(f'{len(values)} matching designs. Library files persist independently of this project.')

    def select(self):
        selection=self.listing.selection()
        if not selection:return
        self.selected=selection[0];bundle=copy.deepcopy(self.current());record=summary(bundle)
        key=(str(self.library.root),bundle['entry_id'],bundle['revision'])
        if key==getattr(self,'preview_key',None):return
        self.preview_key=key
        self.detail.set(f"{bundle['name']}\n{record['construction_kind']} | {record['width']} x {record['height']} tiles | revision {record['revision']}\n"
            f"{record['tiles']} tile definitions, {record['images']} owned images | {record['dependency']} assets\n"
            +record['description'])
        self.generation+=1;generation=self.generation;self.preview=None;self.draw()
        settings=dict(self.owner.parent.settings);validator=self.document.validator
        original_graphics=copy.deepcopy(getattr(self.owner,'graphics',{}))
        def work(cancel):
            from authoring_visuals import VisualSource
            files=preview_files(bundle)
            doc=SimpleNamespace(manifest=files['project.json'],content=files['content.json'],adventure=files['adventure.json'],
                art=files['graphics.json'],snapshot={k:encoded(v) for k,v in files.items()},validator=validator)
            source=VisualSource(doc,settings)
            # Imported CHI projects can have locally extracted atlases with
            # no machine-wide DOS path. Browsing reuses those decoded pixels,
            # while library files retain their explicit original references.
            if all(t['sheet']=='package:art' or t['sheet'] in original_graphics for t in bundle['tiles']):
                from editor_tiles import art_tiles
                source._tiles=original_graphics;source._tiles.update(art_tiles(doc))
            return source.grid(rows(bundle))
        def done(pixels):
            if generation==self.generation:self.preview=pixels;self.draw()
        def failed(error):
            if generation==self.generation:self.preview_key=None;self.status.set('Preview unavailable: '+str(error))
        workspace=workspace_of(self)
        if workspace:workspace.tasks.submit('Previewing construction',self,work,done,failed,quiet=True)
        else:
            try:done(work(None))
            except EditorError as error:failed(error)

    def draw(self):
        self.canvas.delete('all');self.photos=[]
        if not self.preview:return
        pixels=self.preview;w,h=len(pixels[0]),len(pixels)
        scale=min(max(1,self.canvas.winfo_width()-16)/w,max(1,self.canvas.winfo_height()-16)/h,3)
        dw,dh=max(1,int(w*scale)),max(1,int(h*scale))
        image=tk.PhotoImage(master=self.window,width=dw,height=dh)
        image.put(' '.join('{'+ ' '.join(pixels[min(h-1,y*h//dh)][min(w-1,x*w//dw)] for x in range(dw))+'}' for y in range(dh)))
        self.photos=[image];self.canvas.create_image(8,8,anchor='nw',image=image)

    def folder(self):
        path=filedialog.askdirectory(parent=visible_parent(self),title='Shared Construction Library folder')
        if path:
            self.library=ConstructionLibrary(path,self.document.validator);self.location.set(str(self.library.root))
            app=self.owner.parent;app.settings['construction-library-root']=str(self.library.root)
            ProjectDocument.atomic_file(app.state_dir/'settings.json',encoded(app.settings))
            self.selected=None;self.reload()

    def import_selected(self,edit=False):
        bundle=copy.deepcopy(self.current());workspace=workspace_of(self);scope=scope_of(self)
        def show(design_id):
            self.owner.refresh()
            if workspace:
                from editor_history import refresh_scope
                refresh_scope(workspace,scope)
            if edit:
                if bundle['kind']=='Tile':
                    from tile_editing import edit_pixels
                    edit_pixels(self.owner,design_id)
                elif bundle['kind']=='Pattern':
                    editor=self.owner.patterns();editor.selected=design_id;editor.refresh()
                else:
                    editor=self.owner.construction(bundle['kind']);editor.current=design_id;editor.refresh()
            self.status.set('Imported '+bundle['name']+'. Undo removes the import. Save the project to keep it.')
        if workspace:
            candidate=snapshot(scope);stamp=signature(scope)
            def work(cancel):return import_bundle(candidate,bundle)
            def done(design_id):
                if stamp!=signature(scope):raise EditorError('Project changed while importing. Import again to include the latest edits.')
                scope.transact(lambda:None)
                with self.document.command('Import Construction Library design'):
                    self.document.replace_all(candidate.content,candidate.adventure,candidate.art,candidate.manifest,candidate.metadata)
                show(design_id)
            workspace.tasks.submit('Importing construction',self,work,done)
        else:show(import_bundle(self.document,bundle))

    def export_dialog(self,design_id=None):
        scope=scope_of(self);candidate=snapshot(scope) if scope and workspace_of(self) else copy.deepcopy(self.document)
        return self._export_dialog(design_id,candidate)

    def export_tile_dialog(self,source):
        from tile_editing import ensure_tile
        scope=scope_of(self);candidate=snapshot(scope) if scope and workspace_of(self) else copy.deepcopy(self.document)
        identity=source.get('id') or ensure_tile(candidate,source['sheet'],source['graphic'])
        return self._export_dialog(identity,candidate)

    def _export_dialog(self,design_id,candidate):
        from adventure_editor import Form
        data=metadata(candidate);designs=[p for key in ('construction_sets','map_patterns') for p in data.get(key,[])]
        designs.extend(dict(id=t['id'],name=data.get('tile_names',{}).get(t['id'],t['id'].split(':')[-1])) for t in candidate.adventure['tiles'])
        if not designs:raise EditorError('Create a tile, building, wall, road or saved pattern in this project first.')
        selected=next((d for d in designs if d['id']==design_id),designs[0])
        f=Form(self,'Save design to Construction Library')
        f.field('design',selected['id'],[d['id'] for d in designs],label='Project construction set or pattern')
        f.field('save_as','New library copy',['New library copy','Update selected library entry'])
        f.field('name',selected['name'])
        ttk.Label(f.body,text='The design and its tiles/art are copied. Updating requires a selected library entry of the same type.',
                  wraplength=500).grid(row=f.row,column=0,columnspan=2,padx=10,pady=8);f.row+=1
        def apply(values):
            bundle=closure(candidate,values['design']);bundle['name']=values['name'];bundle['design']['name']=values['name']
            notes=bundle['editing'].get('catalogue',{}).get(bundle['design']['id'])
            if notes and 'name' in notes:notes['name']=values['name']
            expected=copy.deepcopy(self.current()) if values['save_as']=='Update selected library entry' else None
            if expected:
                if expected['kind']!=bundle['kind']:raise EditorError('Choose a library entry of the same type to update.')
                bundle.update(entry_id=expected['entry_id'],revision=expected['revision'])
            self.save_bundle(bundle,expected,variant=expected is None)
        f.submit(apply,'Save to library');return f

    def edit(self,entry_id=None):
        if entry_id:self.selected=entry_id
        bundle=self.current()
        for editor in self.workshops:
            if editor.window.winfo_exists() and editor.library_context.bundle['entry_id']==bundle['entry_id']:
                editor.window.lift();return editor
        from construction_workshop import open_workshop
        editor=open_workshop(self,copy.deepcopy(bundle));self.workshops.append(editor);return editor

    def new(self):
        from adventure_editor import Form
        f=Form(self,'New shared design');f.field('name','New shared design');f.field('kind','Building',list(KINDS))
        def apply(values):
            from construction_editing import new_profile
            from tile_editing import create_tile
            from map_patterns import save_pattern
            # This template is read only; every new definition is built in a
            # private document and enters the library before opening an editor.
            from construction_library import ROOT
            doc=ProjectDocument(ROOT/'examples/beacon-demo',self.document.validator)
            kind=values['kind']
            if kind in ('Tile','Pattern'):
                tile_id=create_tile(doc,name=values['name'])
                identity=tile_id if kind=='Tile' else save_pattern(doc,[[tile_id]],values['name'])
            else:identity=new_profile(doc,kind)
            bundle=closure(doc,identity);bundle['name']=bundle['design']['name']=values['name']
            bundle['provenance']=dict(project='Created in Construction Library',package='construction-library',documents={})
            saved=self.library.save(bundle,variant=True)
            self.bundles=self.library.entries();self.kind.set('All');self.query.set('');self.selected=saved['entry_id'];self.refresh()
            self.edit(saved['entry_id'])
        f.submit(apply,'Create shared design');return f

    def save_bundle(self,bundle,expected=None,variant=False):
        from construction_library import check_bundle
        check_bundle(bundle);library=self.library
        def done(saved):
            if library is self.library:
                self.kind.set('All');self.query.set('');self.reload(saved['entry_id'])
            self.status.set('Saved '+saved['name']+' to the shared library.')
        workspace=workspace_of(self)
        if workspace:workspace.tasks.submit('Saving Construction Library design',self,lambda cancel:library.save(bundle,expected,variant),done,cancellable=False)
        else:done(library.save(bundle,expected,variant))

    def load_file(self):
        from authoring_contract import read_json
        path=filedialog.askopenfilename(parent=visible_parent(self),title='Load construction or pattern bundle',
            filetypes=[('Construction Library','*.construction.json'),('JSON','*.json')])
        if path:self.save_bundle(read_json(Path(path)),variant=True)

    def export_file(self):
        bundle=self.current()
        path=filedialog.asksaveasfilename(parent=visible_parent(self),title='Export construction or pattern bundle',
            defaultextension='.construction.json',initialfile=bundle['name']+'.construction.json',
            filetypes=[('Construction Library','*.construction.json')])
        if path:
            ProjectDocument.atomic_file(Path(path),encoded(bundle))
            self.status.set('Exported portable definition and tile/art dependencies.')


def open_library(maps):
    return open_view(maps,'construction-library',lambda:ConstructionBrowser(maps))
