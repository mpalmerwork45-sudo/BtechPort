"""Shared Unit Library browser and editing through the existing property forms."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from editor_model import EditorError, ProjectDocument, encoded
from unit_library import UnitLibrary, KINDS, ROOT, closure, import_units, needs_original, stage_preview
from library_defaults import apply_sprite_defaults


def seed_library(library, paths):
    """Add shipped designs and migrate default art once, retaining author edits."""
    existing={entry['entry_id']:entry for entry in library.entries()}
    added=0
    def add(document,kind,values,source=None):
        nonlocal added
        for item in values:
            if item['id'] in existing:
                prior=existing[item['id']];migrated=apply_sprite_defaults(prior)
                if migrated!=prior:existing[item['id']]=library.save(migrated,expected=prior)
                continue
            bundle=closure(document,item['id'],kind)
            if source:bundle['provenance']['documents'].update(source)
            existing[item['id']]=library.save(apply_sprite_defaults(bundle));added+=1
    doc=ProjectDocument(ROOT/'examples/vehicle-lab',library.validator)
    add(doc,'Vehicles',doc.content['mechs'],{'VEHICLE-SOURCE-README.md':(ROOT/'content/catalogues/vehicles/README.md').read_text()})
    # Numeric templates can be browsed without DOS files; their requested
    # default animations now carry an explicit original-asset dependency.
    for path in ('battletech-demo','beacon-demo','adventure-demo'):
        doc=ProjectDocument(ROOT/'examples'/path,library.validator)
        add(doc,'Infantry',doc.adventure['people'])
        add(doc,'Mechs',doc.content['mechs'])
    # This authored catalogue is self-contained numeric content; no combat
    # cache or online download is needed to browse/import its definitions.
    catalogue=ROOT/'content/catalogues/mechs'
    doc=ProjectDocument(ROOT/'examples/battletech-demo',library.validator)
    doc.replace(json.loads((catalogue/'units.json').read_text()))
    doc.manifest['title']='Classic Inner Sphere mech catalogue'
    add(doc,'Mechs',doc.content['mechs'],{'SOURCE-README.md':(catalogue/'README.md').read_text(),
                                       'LICENSE.md':(catalogue/'LICENSE.md').read_text(),
                                       'sources.json':(catalogue/'sources.json').read_text()})
    cache=Path(paths['combat-data'])
    if cache.exists():
        with tempfile.TemporaryDirectory(prefix='library-builtins-') as tmp:
            tmp=Path(tmp);updated=tmp/'updated'
            result=subprocess.run([str(library.validator),'export',str(updated),'--roster',str(ROOT/'content/updated/roster.json'),
                                   '--combat-data',str(cache)],capture_output=True,text=True,timeout=30)
            if result.returncode:raise EditorError(result.stderr.strip())
            doc=ProjectDocument(updated,library.validator);add(doc,'Mechs',doc.content['mechs'])
            original=tmp/'original.json'
            result=subprocess.run([str(library.validator),'export-original-units',str(original),'--combat-data',str(cache)],
                                  capture_output=True,text=True,timeout=20)
            if result.returncode:raise EditorError(result.stderr.strip() or 'Rebuild btp-project for original unit export.')
            # Use the exported project's explicit dependency contract to
            # validate the original symbolic definitions as well.
            content=json.loads(original.read_text());content.update(package_id=doc.content['package_id'],content_version=doc.content['content_version'])
            content['rules']=doc.content['rules'];doc.replace(content)
            add(doc,'Mechs',content['mechs'],{'ORIGINAL-ADAPTATION.md':
                'Derived locally from the audited original combat templates; no original artwork is included. '
                'Prices use 350 credits/ton and ammunition reloads use 3 credits/shot. '
                'Training Chameleon dummy structure uses the minimum structure compatible with its armour, required by authored-unit validation. '
                'Original numeric movement/loadouts are retained; these are CHI adaptations, not tabletop record sheets.'})
    return added


class EntryContext:
    def __init__(self,browser,bundle):
        self.browser,self.bundle=browser,copy.deepcopy(bundle)
        self.temp=tempfile.TemporaryDirectory(prefix='unit-edit-',dir=browser.owner.state_dir)
        stage_preview(bundle,Path(self.temp.name))

    def commit(self,editor):
        self.bundle=self.browser.library.export_unit(editor.document,self.bundle['definition'],
            self.bundle['kind'],expected=self.bundle)
        self.browser.refresh(self.bundle['entry_id'])
        editor.status.set(f"Saved to Unit Library, revision {self.bundle['revision']}. Import explicitly to update a game.")


class LibraryBrowser:
    def __init__(self,owner):
        self.owner=owner
        owner.state_dir.mkdir(parents=True,exist_ok=True)
        self.library=UnitLibrary(Path(owner.settings.get('library-root',ROOT/'work/unit-library')),owner.validator)
        self.window=tk.Toplevel(owner.window);self.window.title('BattleTech Construction Kit - Unit Library')
        self.window.geometry('1000x730');self.window.minsize(940,650)
        self.timer=None;self.photos=[];self.phase=0;self.documents=[];self.editors=[]
        header=ttk.Frame(self.window,padding=(16,12));header.pack(fill='x')
        ttk.Label(header,text='Unit Library',style='Title.TLabel').pack(side='left')
        ttk.Button(header,text='Library folder...',command=lambda:self.guard(self.folder)).pack(side='right')
        self.location=ttk.Label(self.window,text=str(self.library.root),style='Muted.TLabel',padding=(16,0))
        self.location.pack(fill='x')
        bar=ttk.Frame(self.window,padding=(12,8));bar.pack(fill='x')
        for text,method in [('Import into game',self.import_selected),('Export from game',self.export_from_game),
                            ('Edit unit',self.edit),('Duplicate variant',self.duplicate),('New unit',self.new),('Sources',self.sources)]:
            ttk.Button(bar,text=text,width=0,command=lambda f=method:self.guard(f)).pack(side='left',padx=3)
        target=ttk.Frame(self.window,padding=(16,0,16,8));target.pack(fill='x')
        self.target=ttk.Label(target,text='');self.target.pack(side='left')
        ttk.Button(target,text='Choose game...',command=lambda:self.guard(self.choose_game)).pack(side='right')
        filters=ttk.Frame(self.window,padding=(16,0,16,8));filters.pack(fill='x')
        self.kind=tk.StringVar(value='All');self.query=tk.StringVar();self.weight=tk.StringVar(value='All weights')
        for variable,values,width in [(self.kind,('All',*KINDS),12),(self.weight,('All weights','Light','Medium','Heavy','Assault'),14)]:
            box=ttk.Combobox(filters,textvariable=variable,values=values,state='readonly',width=width);box.pack(side='left',padx=(0,8));box.bind('<<ComboboxSelected>>',lambda _:self.refresh())
        ttk.Label(filters,text='Search').pack(side='left');ttk.Entry(filters,textvariable=self.query).pack(side='left',fill='x',expand=True,padx=8)
        self.query.trace_add('write',lambda *_:self.refresh())
        body=ttk.Panedwindow(self.window,orient='horizontal',height=300);body.pack(fill='both',expand=True,padx=16,pady=(0,10))
        left=ttk.Frame(body);right=ttk.Frame(body,padding=(16,0));body.add(left,weight=3);body.add(right,weight=2)
        self.listing=ttk.Treeview(left,columns=('kind','mass'),show='tree headings',selectmode='extended')
        for col,title,width in [('#0','Design',245),('kind','Type',85),('mass','Tons',50)]:
            self.listing.heading(col,text=title);self.listing.column(col,width=width,stretch=col=='#0')
        scroll=ttk.Scrollbar(left,command=self.listing.yview);self.listing.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right',fill='y');self.listing.pack(fill='both',expand=True)
        self.listing.bind('<<TreeviewSelect>>',lambda _:self.guard(self.show))
        self.listing.bind('<Double-1>',lambda _:self.guard(self.edit))
        self.canvas=tk.Canvas(right,width=240,height=160,background='#dfe5e8',highlightthickness=0);self.canvas.pack(fill='x')
        # Library artwork belongs to the blueprint, not to the currently open
        # game. Reuse the staged editor so Apply and Save to library stay explicit.
        ttk.Button(right,text='Edit sprite...',command=lambda:self.guard(self.edit_sprite)).pack(fill='x',pady=(6,0))
        self.sprite_menu=tk.Menu(self.window,tearoff=False)
        self.sprite_menu.add_command(label='Edit sprite...',command=lambda:self.guard(self.edit_sprite))
        self.sprite_menu.add_command(label='Select sprite...',command=lambda:self.guard(self.select_sprite))
        self.canvas.bind('<Button-3>',self.sprite_popup)
        detail=ttk.Frame(right);detail.pack(fill='both',expand=True,pady=(10,0))
        self.details=tk.Text(detail,height=6,width=30,wrap='word',borderwidth=0,font='TkDefaultFont',background='#f3f3f0',foreground='#293747')
        ds=ttk.Scrollbar(detail,command=self.details.yview);self.details.configure(yscrollcommand=ds.set)
        ds.pack(side='right',fill='y');self.details.pack(fill='both',expand=True)
        self.info=tk.StringVar()
        def update_info(*_):
            self.details.configure(state='normal');self.details.delete('1.0','end');self.details.insert('1.0',self.info.get());self.details.configure(state='disabled')
        self.info.trace_add('write',update_info)
        bottom=ttk.Frame(self.window,padding=(16,0,16,8));bottom.pack(side='bottom',fill='x',before=body)
        options=ttk.Frame(bottom);options.pack(fill='x',pady=(0,8))
        ttk.Label(options,text='On import',style='Muted.TLabel').pack(side='left',padx=(0,8))
        self.policy=tk.StringVar(value='Keep existing')
        ttk.Combobox(options,textvariable=self.policy,values=('Keep existing','Replace selected designs','Import variants'),state='readonly',width=25).pack(side='left')
        self.infantry_art=tk.BooleanVar(value=False)
        ttk.Checkbutton(options,text='Install shared NPC/enemy infantry artwork',variable=self.infantry_art).pack(side='left',padx=12)
        actions=ttk.Frame(bottom);actions.pack(fill='x')
        ttk.Button(actions,text='Add missing built-ins',command=lambda:self.guard(self.builtins)).pack(side='left')
        ttk.Label(actions,text='Ctrl/Shift: select several. Double-click: edit.',style='Muted.TLabel').pack(side='right')
        self.status=tk.StringVar(value='Library designs are independent of game projects.')
        self.status_label=ttk.Label(self.window,textvariable=self.status,style='Status.TLabel',wraplength=900)
        self.status_label.pack(side='bottom',fill='x',before=bottom)
        self.window.bind('<Destroy>',self.destroyed,add='+')
        self.window.protocol('WM_DELETE_WINDOW',self.close)
        self.builtins()

    def guard(self,method):
        try:return method()
        except (EditorError,OSError,ValueError,KeyError,IndexError,StopIteration) as exc:
            self.status.set(str(exc));messagebox.showerror('Unit Library',str(exc),parent=self.window)

    def refresh(self,select=None):
        if not hasattr(self,'listing'):return
        selection=select or (self.listing.selection()[0] if self.listing.selection() else None)
        self.listing.delete(*self.listing.get_children());self.bundles={b['entry_id']:b for b in self.library.entries()}
        query=self.query.get().casefold()
        for identity,bundle in self.bundles.items():
            if self.kind.get()!='All' and bundle['kind']!=self.kind.get():continue
            unit=bundle['person'] or bundle['content']['mechs'][0];mass=unit.get('mass_tons',0)
            weight='Light' if mass<=35 else 'Medium' if mass<=55 else 'Heavy' if mass<=75 else 'Assault'
            if self.weight.get()!='All weights' and (not mass or weight!=self.weight.get()):continue
            if query and query not in (bundle['name']+' '+identity+' '+str(unit.get('movement',{}))).casefold():continue
            self.listing.insert('','end',iid=identity,text=bundle['name'],values=(bundle['kind'],mass or '-'))
        children=self.listing.get_children()
        if children:self.listing.selection_set(selection if selection in children else children[0])
        self.target.configure(text='Game: '+self.owner.document.manifest['title'] if self.owner.document else 'Choose a game to import designs into it.')
        self.show()

    def selected(self):return [self.bundles[i] for i in self.listing.selection()]

    def show(self):
        self.stop();self.canvas.delete('all');selected=self.selected()
        if not selected:self.info.set('No matching designs.');return
        bundle=selected[0];unit=bundle['person'] or bundle['content']['mechs'][0]
        details=f"{bundle['name']}\n{bundle['kind']} | revision {bundle['revision']}\n{bundle['definition']}\n\n"
        if bundle['kind']=='Infantry':details+=f"Attributes: {unit['attributes']}\nSkills: {unit['skills']}\nWeapon {unit['weapon']} | Armour {unit['armor']}"
        else:
            details+=f"{unit['mass_tons']} tons | Walk {unit['movement']['walk']} | Jump {unit['movement']['jump']}\n{len(unit['loadout'])} weapons | {unit['price']:,} C-bills"
        details+='\n\n'+('Needs original CHI sprites.' if needs_original(bundle) else 'Package graphics; original CHI sprites not required.')
        details+='\nSource: '+bundle['provenance']['project']
        self.info.set(details)
        try:
            # Decode directly: browsing a blueprint never creates/edits a game.
            from editor_units import indexed_sprite
            from art_editing import original_sprite
            from graphics_editor import photo
            source=type('SpriteSource',(),dict(validator=self.owner.validator))()
            if bundle['kind']=='Infantry':
                binding=next((b for b in bundle['graphics']['bindings'] if b['slot']=='npc'),None)
                if binding:image=next(i for i in bundle['graphics']['images'] if i['id']==binding['image'])
                elif bundle.get('infantry_source')=='chi:infantry':image=original_sprite(source,self.owner.settings,270,16)
                else:image=indexed_sprite(bundle['presentation'] or json.loads((ROOT/'examples/beacon-demo/presentation.json').read_text()),2)
            else:
                p=bundle['content']['presentations'][0]
                if p['source']=='package:art':image=next(i for i in bundle['graphics']['images'] if i['id']==p['image'])
                elif p['source'].startswith('package:walker'):image=indexed_sprite(bundle['presentation'],0 if p['source'].endswith('a') else 1)
                else:
                    image=original_sprite(source,self.owner.settings,0 if p['source']=='chi:locust' else 146,16)
            frames=range(16,20) if len(image['frames'])==32 else range(min(4,len(image['frames'])))
            zoom=max(1,min(5,144//max(image['width'],image['height'])))
            self.photos=[photo(self.window,image,frame=f,zoom=zoom) for f in frames];self.animate()
        except (EditorError,OSError,KeyError,StopIteration):
            self.canvas.create_text(120,80,text='Original sprite preview unavailable.\nCheck Player setup.',width=220)

    def animate(self):
        self.timer=None
        if not self.photos:return
        self.canvas.delete('preview');self.canvas.create_image(120,80,image=self.photos[self.phase%len(self.photos)],tags='preview')
        self.phase+=1;self.timer=self.window.after(140,self.animate)

    def stop(self):
        if self.timer is not None:self.window.after_cancel(self.timer)
        self.timer=None;self.photos=[];self.phase=0

    def builtins(self):
        count=seed_library(self.library,self.owner.settings);self.refresh()
        self.status.set(f'{len(self.bundles)} designs in the library. Added {count} missing built-ins; default sprites checked.')

    def folder(self):
        path=filedialog.askdirectory(title='Shared Unit Library folder',parent=self.window)
        if path:
            self.library=UnitLibrary(path,self.owner.validator);self.owner.settings['library-root']=str(self.library.root)
            (self.owner.state_dir/'settings.json').write_text(json.dumps(self.owner.settings,indent=2))
            self.location.configure(text=str(self.library.root));self.builtins()

    def choose_game(self):
        self.owner.open_project()
        if self.owner.document:self.owner.window.deiconify()
        self.refresh()

    def import_selected(self):
        if not self.owner.document:raise EditorError('Choose a game first.')
        self.owner.apply_form()
        if self.owner.map_editor:self.owner.map_editor.apply_pending()
        policy={'Keep existing':'keep','Replace selected designs':'replace','Import variants':'variant'}[self.policy.get()]
        result=import_units(self.owner.document,self.selected(),policy,self.infantry_art.get())
        if result:
            kind,identity=result[0];self.owner.kind.set(kind);self.owner.change_kind();self.owner.refresh_list(identity)
            if self.owner.map_editor:self.owner.map_editor.refresh()
        self.status.set(f'Imported {len(result)} designs as one Undo step. Save the game, then place them in shops, encounters or the starting party.')

    def export_from_game(self):
        if not self.owner.document or self.owner.collection not in ('mechs','people') or not self.owner.current:
            raise EditorError('Select a mech, vehicle or infantry character in the game editor first.')
        self.owner.apply_form();kind='Infantry' if self.owner.collection=='people' else self.owner.kind.get()
        bundle=closure(self.owner.document,self.owner.current,kind);expected=next((b for b in self.library.entries() if b['entry_id']==bundle['entry_id']),None)
        variant=False
        if expected:
            answer=messagebox.askyesnocancel('Existing library design','Update the library entry?\nYes: update it. No: save a new variant.',parent=self.window)
            if answer is None:return
            variant=not answer
        saved=self.library.export_unit(self.owner.document,self.owner.current,kind,variant,expected if not variant else None)
        self.refresh(saved['entry_id']);self.status.set('Blueprint and its dependencies exported to the shared library.')

    def edit(self):
        if not self.selected():return
        from roster_editor import RosterEditor
        bundle=self.selected()[0];context=EntryContext(self,bundle)
        window=tk.Toplevel(self.window);editor=RosterEditor(window,self.owner.validator,self.owner.state_dir,context)
        editor.settings.update(self.owner.settings)
        editor.set_document(ProjectDocument(Path(context.temp.name),self.owner.validator))
        editor.kind.set(bundle['kind']);editor.change_kind();editor.refresh_list(bundle['definition'])
        window.title('Unit Library - '+bundle['name'])
        window.bind('<Destroy>',lambda e:context.temp.cleanup() if e.widget==window else None,add='+')
        self.editors.append(editor);return editor

    def edit_sprite(self):
        editor=self.edit()
        if editor:editor.edit_unit_sprite()
        return editor

    def select_sprite(self):
        editor=self.edit()
        if editor:editor.choose_sprite()
        return editor

    def sprite_popup(self,event):
        if not self.selected():return
        try:self.sprite_menu.tk_popup(event.x_root,event.y_root)
        finally:self.sprite_menu.grab_release()

    def duplicate(self):
        if self.selected():
            bundle=copy.deepcopy(self.selected()[0]);bundle['name']=bundle['name'][:89]+' copy'
            unit=bundle['person'] or bundle['content']['mechs'][0];unit['name']=bundle['name']
            saved=self.library.save(bundle,variant=True);self.refresh(saved['entry_id']);return self.edit()

    def sources(self):
        if not self.selected():return
        bundle=self.selected()[0];window=tk.Toplevel(self.window);window.title('Unit sources - '+bundle['name']);window.geometry('800x600')
        ttk.Label(window,text='Source: '+bundle['provenance']['project'],padding=12).pack(fill='x')
        tabs=ttk.Notebook(window);tabs.pack(fill='both',expand=True,padx=12,pady=(0,12))
        documents=bundle['provenance'].get('documents',{}) or {'Notes':'Created in the Unit Library. No external source documents were attached.'}
        for name,contents in documents.items():
            frame=ttk.Frame(tabs);tabs.add(frame,text=name)
            text=tk.Text(frame,wrap='word',font='TkTextFont');scroll=ttk.Scrollbar(frame,command=text.yview)
            text.configure(yscrollcommand=scroll.set);scroll.pack(side='right',fill='y');text.pack(fill='both',expand=True)
            text.insert('1.0',contents);text.configure(state='disabled')

    def new(self):
        from adventure_editor import Form
        form=Form(self,'New library unit');form.window.geometry('700x300')
        choices={'Mech':'mech','Tracked vehicle':'tracked','Wheeled vehicle':'wheeled','Hovercraft':'hover','Infantry character':'infantry'}
        form.field('name','New unit');form.field('type','Mech',tuple(choices))
        form.submit(lambda values:self.create_unit(choices[values['type']],values['name']))
        return form

    def create_unit(self,kind,name):
        doc=ProjectDocument(ROOT/'examples/beacon-demo',self.owner.validator)
        if kind=='infantry':bundle=closure(doc,doc.adventure['people'][1]['id'],'Infantry')
        elif kind in ('tracked','wheeled','hover'):
            doc=ProjectDocument(ROOT/'examples/vehicle-lab',self.owner.validator)
            identity={'tracked':'vehicles:patton','wheeled':'vehicles:skulker','hover':'vehicles:pegasus'}[kind]
            bundle=closure(doc,identity,'Vehicles')
            bundle['provenance']['documents']['VEHICLE-SOURCE-README.md']=(ROOT/'content/catalogues/vehicles/README.md').read_text()
        else:
            from unit_editing import add_unit
            content=copy.deepcopy(doc.content);identity=add_unit(content,kind,'New '+('mech' if kind=='mech' else 'vehicle'));doc.replace(content)
            bundle=closure(doc,identity,'Mechs')
        bundle['name']=name
        (bundle['person'] or bundle['content']['mechs'][0])['name']=bundle['name']
        bundle['provenance']['project']='Created in Unit Library from '+bundle['provenance']['project']
        bundle=apply_sprite_defaults(bundle)
        saved=self.library.save(bundle,variant=True);self.refresh(saved['entry_id']);return self.edit()

    def destroyed(self,event):
        if event.widget==self.window:self.stop()

    def close(self):
        for editor in self.editors:
            if editor.window.winfo_exists():
                editor.close()
                if editor.window.winfo_exists():return
        self.window.destroy()
