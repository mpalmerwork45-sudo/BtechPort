"""Private shared-design workspaces: edits and test terrain never touch a game.

The library bundle contains only the design's tile/art closure. Its test canvas
is stored separately for that exact revision, so importing a building cannot
silently import the author's experiments, unrelated tiles or temporary maps.
"""
from __future__ import annotations
import copy
import json
from pathlib import Path
import tempfile

from construction_library import closure,preview_files,rows
from editor_model import EditorError,ProjectDocument,encoded
from tile_editing import metadata


class WorkshopContext:
    def __init__(self,browser,bundle,state_dir):
        self.browser=browser;self.library=browser.library;self.bundle=copy.deepcopy(bundle)
        self.temp=tempfile.TemporaryDirectory(prefix='construction-edit-',dir=state_dir)
        folder=Path(self.temp.name);files=preview_files(bundle)
        # Start with a real map, so the ordinary shape, road, selection and
        # pixel tools all exercise the same rules used by authored games.
        grid=rows(bundle);scene=files['adventure.json']['maps'][0]
        scene['name']='Library test canvas';ground=scene['rows'][0][0]
        width=max(32,len(grid[0])+4);height=max(24,len(grid)+4)
        scene['rows']=[[ground]*width for _ in range(height)]
        for y,row in enumerate(grid):
            for x,value in enumerate(row):
                if value!=' ':scene['rows'][y+2][x+2]=value
        files['adventure.json']['start']['at']=[0,0]
        files['LIBRARY-SOURCES.json']=[dict(entry_id=bundle['entry_id'],revision=bundle['revision'],
            kind=bundle['kind'],provenance=copy.deepcopy(bundle['provenance']))]
        raw={name:encoded(value) for name,value in files.items()}
        saved=self.library.workshop_path(bundle)
        if saved.exists():
            if saved.is_symlink() or saved.stat().st_size>32*1024*1024:
                raise EditorError('The saved workshop must be an ordinary file of at most 32 MiB.')
            record=json.loads(saved.read_text())
            if record.get('format')!='btp-construction-workshop-v1' or set(record.get('files',{}))-set(raw):
                raise EditorError('Invalid saved construction workshop.')
            raw={name:value.encode('utf-8') for name,value in record['files'].items()}
        for name,data in raw.items():(folder/name).write_bytes(data)

    def export_document(self,document,variant=False):
        bundle=closure(document,self.bundle['design']['id'])
        # Keep the original authors/source documents through direct editing.
        documents=bundle['provenance']['documents']
        bundle['provenance']=copy.deepcopy(self.bundle['provenance'])
        bundle['provenance']['documents'].update(documents)
        bundle.update(entry_id=self.bundle['entry_id'],revision=self.bundle['revision'])
        return self.library.save(bundle,expected=None if variant else self.bundle,
            variant=variant,workspace_files=document.files())

    def refresh_browser(self,bundle):
        if self.browser.window.winfo_exists() and self.browser.library is self.library:self.browser.reload(bundle['entry_id'])

    def commit(self,editor):
        # Synchronous close/save uses the same validation and optimistic
        # revision gate as asynchronous Ctrl+S and Save All.
        replacement=tempfile.TemporaryDirectory(prefix='construction-edit-',dir=editor.state_dir)
        try:
            editor.document.stage(Path(replacement.name))
            saved_document=ProjectDocument(Path(replacement.name),editor.validator)
            saved=self.export_document(saved_document)
        except Exception:replacement.cleanup();raise
        from editor_tasks import adopt_saved
        previous=self.temp;self.temp=replacement;self.bundle=saved
        editor.document.root=saved_document.root;adopt_saved(editor.document,saved_document);previous.cleanup()
        self.refresh_browser(saved)
        editor.status.set('Saved shared design and test canvas. Import explicitly to update a game.')


def open_workshop(browser,bundle):
    from adventure_editor import AdventureEditor
    from editor_session import EditorScope,guard
    from editor_workspace import workspace_of
    from editor_recovery import recoverable_forms
    from types import SimpleNamespace
    import tkinter as tk
    from tkinter import ttk

    @recoverable_forms
    class Workshop(AdventureEditor):
        def __init__(self):
            self.owner=browser;self.window=browser.window
            self.validator=browser.document.validator;self.state_dir=browser.owner.parent.state_dir
            self.state_dir.mkdir(parents=True,exist_ok=True)
            self.settings=dict(browser.owner.parent.settings)
            self.library_context=WorkshopContext(browser,bundle,self.state_dir)
            self.document=ProjectDocument(Path(self.library_context.temp.name),self.validator)
            self._editor_scope=EditorScope(self);workspace=workspace_of(browser)
            if workspace:workspace.attach_scope(self._editor_scope)
            self.view_title='Library workshop - '+bundle['name']
            self.current=None;self.collection='construction';self.form_dirty=False
            self.map_editor=self;self.art_editor=None
            parent=SimpleNamespace(window=browser.window,document=self.document,settings=self.settings,state_dir=self.state_dir,
                validator=self.validator,_editor_scope=self._editor_scope,export_project=self.export_project,setup=self.setup,
                save=self.save,validate=self.validate,apply_form=lambda:None,refresh_list=lambda:None,
                graphics_editor=self.graphics_editor,launch_player=self.launch_player,map_editor=self)
            super().__init__(parent)
            self.parent.window=self.window
            self.tabs.hide(self.world_tab);self.tabs.hide(self.event_tab);self.tabs.tab(self.map_tab,text='Test canvas')
            bar=ttk.Frame(self.window,padding=6);bar.pack(fill='x',before=self.tabs)
            self.buttons={}
            actions=[('Save shared design',self.save),('Edit definition',self.edit_definition),
                     ('Draw / stamp design',self.use_design),('Test canvas',self.play)]
            if bundle['kind']=='Pattern':actions.append(('Update pattern from selection',self.update_pattern))
            for label,callback in actions:
                button=ttk.Button(bar,text=label,width=0,command=lambda f=callback:guard(self,f));button.pack(side='left',padx=3,pady=3)
                self.buttons[label]=button
            more=ttk.Menubutton(bar,text='Workshop actions');more.pack(side='left',padx=3)
            menu=tk.Menu(more,tearoff=False);more.configure(menu=menu)
            for label,callback in [('Rename design...',self.rename),('Save variant...',self.variant),('Clear test canvas',self.clear_canvas),('Close workshop',self.close)]:
                menu.add_command(label=label,command=lambda f=callback:guard(self,f))
            from editor_ui import flow_toolbar
            flow_toolbar(bar)
            note=ttk.Label(self.window,text='Edit shared definitions and pixels; draw trials below. Save retains this canvas separately. Import the design to update a game.',wraplength=900,padding=(8,4))
            note.pack(fill='x',before=bar);note.bind('<Configure>',lambda e:note.configure(wraplength=max(200,e.width-16)))
            self.window.protocol('WM_DELETE_WINDOW',self.close)
            self.window.bind('<Destroy>',lambda e:self.library_context.temp.cleanup() if e.widget==self.window else None,add='+')
            self.zoom_control.set(24);self.use_design()
            if workspace:self.window.after_idle(lambda:workspace.recovery.offer(self._editor_scope))

        def refresh_list(self,*_):pass
        def apply_form(self):pass
        def build_maps(self):
            super().build_maps()
            # This is a reusable art/design workshop, not a second mission
            # editor. Keep the familiar drawing tools while giving the canvas
            # the space occupied by encounters, NPCs and project navigation.
            self.map_choice.master.pack_forget();self.sidebar.hide(1)
            self.drawing_tools.destroy()
            from editor_canvas import DrawingTools
            self.drawing_tools=DrawingTools(self.map_tab,self.tool,[('Canvas',[
                (value,title,hint) for value,title,hint in [
                    ('Paint','Paint','Paint the selected tile.'),('Line','Line','Draw a tile line.'),
                    ('Rectangle','Rectangle','Draw a tile rectangle.'),('Fill','Fill','Fill connected terrain.'),
                    ('Eyedropper','Pick tile','Choose a tile from the test canvas.'),('Select','Select','Select a map block to copy, cut or update the shared pattern.'),
                    ('Paste','Paste','Stamp the selected pattern.'),('Building','Building','Draw a building footprint.'),
                    ('Wall','Wall','Draw connected walls.'),('Road','Road','Draw connected roads.'),
                    ('Start','Start','Choose the player position for testing.')]])],lambda _:self.guard(self.choose_drawing_tool))
            self.drawing_tools.pack(fill='x',before=self.map_body)
            trace=self.tool.trace_add('write',lambda *_:self.show_tool_options())
            self.drawing_tools.bind('<Destroy>',lambda e:self.tool.trace_remove('write',trace) if e.widget is self.drawing_tools else None,add='+')
        def reload_graphics(self):
            originals={key:value for key,value in getattr(browser.owner,'graphics',{}).items() if key.startswith('chi:')}
            if self.document.manifest['requires']!='none' and originals:
                from editor_tiles import art_tiles
                from tile_animation import TileGraphics
                self.cancel_gesture();self.images.clear();self.graphics=TileGraphics(originals)
                self.graphics.animations.update({key:value for key,value in getattr(browser.owner.graphics,'animations',{}).items() if key[0].startswith('chi:')})
                self.graphics.update(art_tiles(self.document));self.graphics_note.set('Graphics ready | original tiles from open project')
                self.graphics_label.pack_forget();self.refresh()
            else:super().reload_graphics()
        def edit_adventure(self):self.map_editor=self;self.window.lift()
        def graphics_editor(self):
            from roster_editor import RosterEditor
            return RosterEditor.graphics_editor(self)
        def setup(self):return browser.owner.parent.setup()
        def export_project(self):raise EditorError('Save the shared design, then import it into a game to export a game package.')
        def save(self):
            if getattr(self._editor_scope,'saving',False):raise EditorError('This shared design is already being saved. Wait for the save to finish.')
            return self._editor_scope.transact(lambda:self.library_context.commit(self))
        def validate(self):self.status.set(self._editor_scope.transact(self.document.validate))
        def launch_player(self,here=None):
            workspace=workspace_of(self)
            if workspace:return workspace.play_session.start(self._editor_scope,here=here)
            raise EditorError('Open the workshop in the Construction Kit workspace to play the test canvas.')
        def play(self):return self.launch_player()
        def play_here(self):return self.launch_player((self.scene()['id'],*self.cursor))
        def close(self):
            workspace=workspace_of(self)
            if workspace:workspace.close_scope(self._editor_scope)
            elif self._editor_scope.confirm_close():self.window.destroy()
        def definition(self):return self.library_context.bundle['design']['id']
        def rename(self):
            from adventure_editor import Form
            form=Form(self,'Shared design name');form.field('name',closure(self.document,self.definition())['name'])
            def apply(values):
                name=values['name'].strip()
                if not name or len(name)>95:raise EditorError('Use a name of 1..95 characters.')
                data=metadata(self.document);identity=self.definition();kind=self.library_context.bundle['kind']
                if kind=='Tile':data.setdefault('tile_names',{})[identity]=name
                else:
                    next(p for p in data['map_patterns' if kind=='Pattern' else 'construction_sets'] if p['id']==identity)['name']=name
                if identity in data.get('catalogue',{}):data['catalogue'][identity]['name']=name
                meta=dict(self.document.metadata);meta['EDITOR.json']=encoded(data)
                with self.document.command('Rename shared design'):
                    self.document.replace_all(self.document.content,self.document.adventure,self.document.art,self.document.manifest,meta)
                self.refresh()
            form.submit(apply);return form
        def edit_definition(self):
            kind=self.library_context.bundle['kind'];identity=self.definition()
            if kind=='Tile':
                from tile_editing import edit_pixels
                return edit_pixels(self,identity)
            if kind=='Pattern':
                self.tool.set('Select');self.selection_rect=(2,2,2+len(rows(self.library_context.bundle)[0])-1,2+len(rows(self.library_context.bundle))-1)
                self.draw();self.status.set('Paint the pattern on the test canvas, select its rectangle, then Update pattern from selection. Right-click tiles to edit their pixels in context.');return
            editor=self.construction(kind);editor.current=identity;editor.refresh();return editor
        def use_design(self):
            kind=self.library_context.bundle['kind'];identity=self.definition()
            if kind=='Tile':
                from tile_editing import select_tile
                select_tile(self,identity);self.tool.set('Paint')
            elif kind=='Pattern':
                design=next(p for p in metadata(self.document)['map_patterns'] if p['id']==identity)
                self.use_pattern(design['rows'],design['name'])
            else:
                profile=next(p for p in metadata(self.document)['construction_sets'] if p['id']==identity)
                self.construction_tools.activate(profile)
            self.window.lift()
        def update_pattern(self):
            if self.library_context.bundle['kind']!='Pattern':raise EditorError('Only a saved map pattern can be replaced from a selection.')
            if self.selection_rect is None:raise EditorError('Use Select and drag a rectangle on the test canvas first.')
            from map_patterns import capture,save_pattern
            design=next(p for p in metadata(self.document)['map_patterns'] if p['id']==self.definition())
            save_pattern(self.document,capture(self.document,self.scene_index,self.selection_rect),design['name'],design['id'])
            self.status.set('Shared pattern updated in memory. Save shared design to retain it.');self.refresh()
        def clear_canvas(self):
            a=copy.deepcopy(self.document.adventure);scene=a['maps'][0]
            ground=next(t['id'] for t in a['tiles'] if t['id'].startswith('preview:floor'))
            scene.update(rows=[[ground]*len(scene['rows'][0]) for _ in scene['rows']],overlays=[])
            data=metadata(self.document);data.pop('map_constructions',None)
            meta=dict(self.document.metadata);meta['EDITOR.json']=encoded(data)
            with self.document.command('Clear library test canvas'):self.document.replace_art(self.document.art,a,meta)
            self.selection_rect=None;self.refresh()
        def variant(self):
            from adventure_editor import Form
            form=Form(self,'Save a new shared design variant');form.field('name',self.library_context.bundle['name']+' copy')
            def apply(values):
                # The variant uses a detached snapshot, keeping the current
                # entry, its unsaved edits and Undo history unchanged.
                candidate=self.document.worker_copy();data=metadata(candidate);identity=self.definition()
                if self.library_context.bundle['kind']=='Tile':data.setdefault('tile_names',{})[identity]=values['name']
                else:
                    key='map_patterns' if self.library_context.bundle['kind']=='Pattern' else 'construction_sets'
                    next(p for p in data[key] if p['id']==identity)['name']=values['name']
                meta=dict(candidate.metadata);meta['EDITOR.json']=encoded(data)
                candidate.replace_all(candidate.content,candidate.adventure,candidate.art,candidate.manifest,meta)
                candidate.validate();saved=self.library_context.export_document(candidate,variant=True)
                self.library_context.refresh_browser(saved);self.status.set('Saved a new shared variant. This workshop still edits the original entry.')
            form.submit(apply,'Save variant');return form
    return Workshop()
