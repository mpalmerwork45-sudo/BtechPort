#!/usr/bin/env python3
"""Windows/Linux game editor for independent and CHI-dependent projects."""
from __future__ import annotations

import argparse
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
if __name__ == '__main__':
    from editor_runtime import prefer_system_tk
    prefer_system_tk()
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk, filedialog, messagebox, simpledialog

from editor_recovery import recoverable_forms
from editor_model import EditorError, ProjectDocument, create_project
from editor_session import EditorScope, FieldError, guard, report

ROOT = Path(__file__).resolve().parents[1]
LOCATIONS = ["left_arm", "left_torso", "left_leg", "head", "center_torso", "right_arm", "right_torso", "right_leg"]
WEAPONS = ["small_laser", "medium_laser", "large_laser", "ppc", "ac2", "ac5", "ac10", "ac20", "machine_gun", "flamer", "lrm5", "lrm10", "lrm15", "lrm20", "srm2", "srm4", "srm6"]


def configure_editor_style(window):
    """Share a quiet, native-font palette with the roster and map windows."""
    from editor_lists import install
    install(window)
    style = ttk.Style(window)
    if "clam" in style.theme_names() and os.name != "nt":
        style.theme_use("clam")
    palette = dict(background="#f3f3f0", surface="#ffffff", text="#293747",
                   muted="#637181", border="#d9dfe3", accent="#286c80",
                   selection="#deedf2")
    # Configure Tk's named fonts once: mixing a named-font token with a size
    # tuple makes Tk treat that token as a missing *family*, causing fallback
    # glyphs. Positive point sizes keep the user's system DPI scaling intact.
    families=set(tkfont.families(window))
    choices=('Segoe UI','Noto Sans','DejaVu Sans') if os.name=='nt' else ('Noto Sans','DejaVu Sans','Liberation Sans')
    family=next((name for name in choices if name in families),tkfont.nametofont('TkDefaultFont').actual('family'))
    for name in ('TkDefaultFont','TkTextFont','TkMenuFont','TkHeadingFont','TkCaptionFont','TkSmallCaptionFont','TkIconFont','TkTooltipFont'):
        tkfont.nametofont(name).configure(family=family,size=10,weight='normal')
    tkfont.nametofont('TkHeadingFont').configure(weight='bold')
    heading = (family, 11, "bold")
    title = (family, 16, "bold")
    style.configure(".", background=palette["background"], foreground=palette["text"],font='TkDefaultFont')
    for name in ("App.TFrame", "TFrame"):
        style.configure(name, background=palette["background"])
    style.configure("Card.TFrame", background=palette["surface"],
                    bordercolor=palette["border"], relief="solid", borderwidth=1)
    style.configure("TLabel", background=palette["background"], foreground=palette["text"])
    style.configure("App.TLabel", background=palette["background"], foreground=palette["text"])
    style.configure("Card.TLabel", background=palette["surface"], foreground=palette["text"])
    style.configure("Muted.TLabel", background=palette["background"], foreground=palette["muted"])
    style.configure("CardMuted.TLabel", background=palette["surface"], foreground=palette["muted"])
    style.configure("Heading.TLabel", background=palette["surface"], foreground=palette["text"], font=heading)
    style.configure("Title.TLabel", background=palette["background"], foreground=palette["text"], font=title)
    style.configure("Section.TLabel", background=palette["surface"], foreground=palette["accent"],
                    font='TkHeadingFont')
    style.configure("TButton", padding=(10, 6))
    style.configure("Toolbar.TButton", padding=(9, 5))
    style.configure("Accent.TButton", background=palette["accent"], foreground="#ffffff",
                    padding=(14, 5), bordercolor=palette["accent"])
    style.map("Accent.TButton", background=[("disabled", "#dce2e5"), ("pressed", "#1c5262"), ("active", "#205d6f")],
              foreground=[("disabled", "#74808b"), ("!disabled", "#ffffff")])
    style.configure("Danger.TButton", foreground="#98524b", padding=(9, 6))
    style.configure("TEntry", fieldbackground=palette["surface"], padding=(5, 3))
    style.configure("TCombobox", padding=(5, 3))
    style.configure("TNotebook", background=palette["background"], borderwidth=0, tabmargins=(0, 3, 0, 0))
    style.configure("TNotebook.Tab", padding=(11, 7))
    style.map("TNotebook.Tab", background=[("selected", palette["surface"])],
              foreground=[("selected", palette["accent"])])
    style.configure("Treeview", rowheight=tkfont.nametofont('TkDefaultFont').metrics('linespace')+10, background=palette["surface"], fieldbackground=palette["surface"])
    style.configure("Treeview.Heading", padding=(8, 6))
    style.map("Treeview", background=[("selected", palette["selection"])],
              foreground=[("selected", palette["text"])])
    style.configure("Status.TLabel", background="#e9edef", foreground=palette["muted"], padding=(14, 9))
    if isinstance(window,(tk.Tk,tk.Toplevel)):window.configure(background=palette["background"])
    # Tk listboxes/text controls follow the same palette as native ttk fields.
    for option, value in {"background": palette["surface"], "foreground": palette["text"],
                          "selectBackground": palette["selection"], "selectForeground": palette["text"],
                          "highlightBackground": palette["border"], "highlightColor": palette["accent"]}.items():
        window.option_add(f"*Listbox.{option}", value)
    return palette


@recoverable_forms
class RosterEditor:
    def __init__(self, window: tk.Tk, validator: Path, state_dir: Path, library_context=None):
        self.window, self.validator, self.state_dir = window, validator, state_dir
        self.library_context = library_context
        self.document: ProjectDocument | None = None
        self._editor_scope = EditorScope(self)
        if hasattr(window,'workspace'):window.workspace.attach_scope(self._editor_scope)
        self.map_editor = None
        self.art_editor = None
        self.current = None
        self.collection = "mechs"
        self.variables: dict[tuple[str, ...], tuple[tk.StringVar, bool]] = {}
        self.loadout = []
        self.populating = False
        self.form_dirty = False
        self.sprite_timer=None;self.sprite_photos=[];self.sprite_index=0;self.sprite_source=None
        self.settings = self.defaults()
        try:
            self.settings.update(json.loads((state_dir / "settings.json").read_text()))
        except (OSError, ValueError):
            pass
        self.palette = configure_editor_style(window)
        window.title("BattleTech Construction Kit")
        window.geometry("1000x740")
        window.minsize(940, 690)
        header = ttk.Frame(window, style="App.TFrame", padding=(16, 12, 16, 8))
        header.pack(fill="x")
        ttk.Label(header, text="Library unit editor" if library_context else "Game editor", style="Title.TLabel").pack(side="left")
        self.profile_label = ttk.Label(header, text="Create a game or open a project.", style="Muted.TLabel")
        self.profile_label.pack(side="right", anchor="s", pady=3)
        actions = ttk.Frame(window, style="Card.TFrame", padding=(9, 7))
        actions.pack(fill="x", padx=14, pady=(0, 8))
        toolbar = ttk.Frame(actions, style="Card.TFrame", borderwidth=0)
        toolbar.pack(fill="x")
        for group in [[("Save to library", self.save)] if library_context else [("New project", self.new_project), ("Open", self.open_project), ("Save", self.save)],
                      [("Undo", self.undo), ("Redo", self.redo)], [("Validate", self.validate)]]:
            if toolbar.winfo_children():
                ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=8, pady=3)
            for label, command in group:
                ttk.Button(toolbar, text=label, style="Toolbar.TButton",
                           command=lambda cb=command: self.guarded(cb)).pack(side="left", padx=2)
        ttk.Button(toolbar, text="Play", style="Accent.TButton",
                   command=lambda: self.guarded(self.play)).pack(side="right", padx=2)
        author_bar = ttk.Frame(actions, style="Card.TFrame", borderwidth=0, padding=(0, 6, 0, 0))
        author_bar.pack(fill="x")
        ttk.Button(author_bar, text="Graphics / sprites" if library_context else "Maps / events", style="Toolbar.TButton",
                   command=lambda: self.guarded(self.library_graphics if library_context else self.edit_adventure)).pack(side="left", padx=2)
        if not library_context:
            ttk.Button(author_bar,text="Unit Library",style="Toolbar.TButton",command=lambda:self.guarded(self.open_library)).pack(side="left",padx=2)
        if not library_context: ttk.Button(author_bar, text="Export game", style="Toolbar.TButton",
                   command=lambda: self.guarded(self.export_project)).pack(side="left", padx=2)
        if not library_context:
            from delivery_gui import menu as delivery_menu
            delivery_menu(self,author_bar)
        ttk.Button(author_bar,text="Ammunition",style="Toolbar.TButton",command=lambda:self.guarded(self.ammunition)).pack(side="left",padx=2)
        ttk.Button(author_bar, text="Player setup", style="Toolbar.TButton",
                   command=lambda: self.guarded(self.setup)).pack(side="right", padx=2)
        project = ttk.Frame(window, padding=(17, 0, 17, 7))
        project.pack(fill="x")
        self.project_label = ttk.Label(project, text="Open a project or create one from a template.", style="App.TLabel")
        self.project_label.pack(anchor="w")
        self.path_label = ttk.Label(project, text="", style="Muted.TLabel")
        self.path_label.pack(anchor="w", pady=(2, 0))
        body = ttk.Panedwindow(window, orient="horizontal")
        body.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        left = ttk.Frame(body, width=250, style="Card.TFrame", padding=12)
        right = ttk.Frame(body, padding=(12, 0, 0, 0))
        body.add(left, weight=1)
        body.add(right, weight=4)
        sidebar_title = ttk.Frame(left, style="Card.TFrame", borderwidth=0)
        sidebar_title.pack(fill="x", pady=(0, 8))
        ttk.Label(sidebar_title, text="ROSTER", style="Section.TLabel").pack(side="left")
        self.roster_count = ttk.Label(sidebar_title, text="", style="CardMuted.TLabel")
        self.roster_count.pack(side="right")
        self.kind = tk.StringVar(value="Mechs")
        kinds=["Mechs", "Vehicles", "Infantry", "Weapons", "Equipment"]
        if library_context:kinds=[library_context.bundle['kind']]+([] if library_context.bundle['kind']=='Infantry' else ['Weapons','Equipment'])
        box = ttk.Combobox(left, textvariable=self.kind, values=kinds, state="readonly")
        box.pack(fill="x", pady=(0, 12))
        box.bind("<<ComboboxSelected>>", lambda _e: self.guarded(self.change_kind))
        self.search = tk.StringVar()
        ttk.Label(left, text="Search name or ID", style="CardMuted.TLabel").pack(anchor="w")
        ttk.Entry(left, textvariable=self.search).pack(fill="x", pady=(4, 10))
        self.search.trace_add("write", lambda *_: self.guarded(self.refresh_list))
        list_frame = ttk.Frame(left, style="Card.TFrame")
        list_frame.pack(fill="both", expand=True)
        self.listing = tk.Listbox(list_frame, exportselection=False, width=27, borderwidth=0,
                                  highlightthickness=0, activestyle="none", font="TkDefaultFont")
        scrollbar = ttk.Scrollbar(list_frame, command=self.listing.yview)
        self.listing.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.listing.pack(side="left", fill="both", expand=True)
        self.listing.bind("<<ListboxSelect>>", lambda _e: self.guarded(self.select))
        buttons = ttk.Frame(left, style="Card.TFrame", borderwidth=0)
        buttons.pack(fill="x", pady=(10, 0))
        self.duplicate_button=ttk.Button(buttons, text="Duplicate / add", command=lambda: self.guarded(self.duplicate));self.duplicate_button.pack(side="left")
        self.delete_button=ttk.Button(buttons, text="Delete", style="Danger.TButton", command=lambda: self.guarded(self.delete));self.delete_button.pack(side="right")
        self.definition_button=ttk.Button(left,text="New definition...",command=lambda:self.guarded(self.new_definition));self.definition_button.pack(fill="x",pady=(8,0))
        selection=ttk.Frame(right);selection.pack(fill='x',pady=(0,8))
        self.selection_title = ttk.Label(selection, text="Definition details", style="App.TLabel", padding=(2, 2, 0, 6),wraplength=370)
        self.selection_title.pack(side='left',anchor='n')
        self.sprite_panel=ttk.Frame(selection)
        self.sprite_canvas=tk.Canvas(self.sprite_panel,width=120,height=100,background='#e1e1e1',highlightthickness=1,highlightbackground='#cfd8df')
        self.sprite_canvas.pack()
        ttk.Label(self.sprite_panel,text='Right-click for sprite tools',style='Muted.TLabel').pack()
        self.sprite_menu=tk.Menu(self.sprite_canvas,tearoff=False)
        self.sprite_menu.add_command(label='Edit sprite',command=lambda:self.guarded(self.edit_unit_sprite))
        self.sprite_menu.add_command(label='Select sprite',command=lambda:self.guarded(self.choose_sprite))
        self.sprite_canvas.bind('<Button-3>',self.sprite_context)
        self.sprite_canvas.bind('<Double-Button-1>',lambda _:self.guarded(self.edit_unit_sprite))
        self.notebook = ttk.Notebook(right)
        self.notebook.pack(fill="both", expand=True)
        self.status = tk.StringVar(value="Ready")
        ttk.Label(window, textvariable=self.status, style="Status.TLabel", wraplength=900).pack(fill="x")
        self.error_label=ttk.Label(window,text='',foreground='#a03030',wraplength=850,padding=8)
        window.protocol("WM_DELETE_WINDOW", self.close)
        window.bind("<Control-s>", lambda _e: self.guarded(self.save))
        window.bind("<Control-z>", lambda _e: self.guarded(self.undo))
        window.bind("<Control-y>", lambda _e: self.guarded(self.redo))
        window.bind('<Destroy>',lambda e:self.stop_sprite() if e.widget==window else None,add='+')
        self.populate()
        self.draft=self._editor_scope.register(self,lambda:self.form_dirty,self.apply_form,
            self.capture_draft,self.restore_draft)
        if hasattr(window,'workspace'):
            # The workspace supplies global actions and the project explorer.
            # Keep the property editor; avoid a second navigation column.
            header.pack_forget();actions.pack_forget();project.pack_forget()
            body.forget(left)
            window.title('Library design' if library_context else 'Units')

    @staticmethod
    def defaults() -> dict:
        from app_runtime import default_settings
        return default_settings()

    def guarded(self, operation):
        return guard(self,operation)

    def show_error(self,error):
        if hasattr(self.window,'workspace'):self.window.lift()
        self.error_label.configure(text=str(error));self.error_label.pack(side='bottom',fill='x')
        control=self.field_controls.get(tuple(error.field)) if isinstance(error,FieldError) and error.field else None
        if control is not None:
            page=control
            while page.master is not self.notebook:page=page.master
            self.notebook.select(page);control.state(['invalid']);control.focus_set()

    def capture_draft(self):
        return dict(current=self.current,collection=self.collection,kind=self.kind.get(),
            values=[(list(k),v.get()) for k,(v,_) in self.variables.items()],
            loadout=copy.deepcopy(self.loadout),dirty=self.form_dirty)

    def restore_draft(self,state):
        self.current=state['current'];self.collection=state['collection'];self.kind.set(state['kind'])
        self.populate()
        for key,value in state['values']:
            if tuple(key) in self.variables:self.variables[tuple(key)][0].set(value)
        self.loadout=state['loadout'];self.form_dirty=state['dirty']
        if self.current and self.collection=='mechs':self.refresh_mounts()

    def discard_or_save(self) -> bool:
        return self._editor_scope.confirm_close()

    def set_document(self, document: ProjectDocument, check=True):
        if self.document is not None and check and not self.discard_or_save():return
        workspace=getattr(self._editor_scope,'workspace',None)
        if workspace and self.document is not None:workspace.project_replacing(self._editor_scope)
        if self.map_editor:
            self.map_editor.window.destroy()
            self.map_editor = None
        self.document = document
        self.current = None
        self.form_dirty = False
        self.search.set("")
        self.refresh_list()
        self.project_label.configure(text=document.manifest["title"])
        self.path_label.configure(text=str(document.root), wraplength=880)
        self.profile_label.configure(text="Independent game | package assets" if document.manifest["requires"] == "none" else "BattleTech project | original assets")
        self.status.set("Project opened. Existing saves require this exact content; Play starts a separate campaign.")
        if workspace and self is getattr(workspace,'app',None):workspace.project_changed()

    def open_project(self):
        if not self.discard_or_save():
            return
        path = filedialog.askdirectory(title="Open directory containing project.json", parent=self.window)
        if path:
            self.set_document(ProjectDocument(Path(path), self.validator),check=False)

    def new_project(self):
        workspace=getattr(self._editor_scope,'workspace',None)
        if workspace:return workspace.new_project()
        if not self.discard_or_save():
            return
        # A new standalone author can start without exporting or locating any
        # original assets. An open project remains the template for variants.
        template = self.document.root if self.document else ROOT / "examples/beacon-demo"
        package_id = simpledialog.askstring("New project", "New package ID (lowercase letters, digits, hyphens):", parent=self.window)
        if not package_id:
            return
        if not all(c in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in package_id) or not package_id[0].isalpha():
            raise EditorError("Use a lowercase letter first, then lowercase letters, digits or hyphens.")
        title = simpledialog.askstring("Project title", "Title:", initialvalue=package_id, parent=self.window)
        if not title:
            return
        parent = filedialog.askdirectory(title="Create project folder inside", parent=self.window)
        if parent:
            self.set_document(create_project(template, Path(parent) / package_id, package_id, title, self.validator),check=False)

    def change_kind(self):
        self.apply_form()
        self.collection = {'Weapons':'weapons','Equipment':'equipment','Infantry':'people'}.get(self.kind.get(),'mechs')
        self.current = None
        self.refresh_list()

    def refresh_list(self, choose=None):
        if self.populating or not self.document:
            return
        self.apply_form()
        self.populating = True
        try:
            selected = choose or self.current
            self.visible = []
            self.listing.delete(0, "end")
            from asset_catalogue import search_document
            query = self.search.get()
            matching=search_document(self.document,query) if query else None
            for item in self.values():
                if self.collection=='mechs' and (item.get('kind')=='vehicle') != (self.kind.get()=='Vehicles'):continue
                if matching is not None and item['id'] not in matching and query.casefold() not in (item.get('name',item['id'])+' '+item['id']).casefold():
                    continue
                self.visible.append(item["id"])
                self.listing.insert("end", (f"{item['mass_tons']:3d}t  " if self.collection == "mechs" else "") + item.get("name",item['id']))
            total = len(self.values())
            self.roster_count.configure(text=str(total) if len(self.visible) == total else f"{len(self.visible)} / {total}")
            if self.visible:
                index = self.visible.index(selected) if selected in self.visible else 0
                self.listing.selection_set(index)
                self.current = self.visible[index]
            else:
                self.current = None
            self.populate()
        finally:
            self.populating = False

    def select(self):
        if self.populating or not self.listing.curselection():
            return
        selected = self.visible[self.listing.curselection()[0]]
        if selected != self.current:
            self.apply_form()
            self.current = selected
            self.populate()

    def item(self):
        return next(v for v in self.values() if v["id"] == self.current)

    def values(self):
        if self.collection=='people':
            people=self.document.adventure['people'] if self.document.adventure else []
            return [p for p in people if p['id']==self.library_context.bundle['definition']] if self.library_context else people
        return self.document.content.get(self.collection,[])

    def tab(self, name):
        # Long anatomy/component forms remain reachable at the minimum window
        # size. Each tab scrolls independently without changing document state.
        container = ttk.Frame(self.notebook, style="Card.TFrame")
        canvas = tk.Canvas(container, background=self.palette["surface"], borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        frame = ttk.Frame(canvas, padding=14, style="Card.TFrame", borderwidth=0)
        inner = canvas.create_window(0, 0, anchor="nw", window=frame)
        frame.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(inner, width=e.width))
        frame.editor_canvas = canvas
        self.bind_form_scroll(frame, canvas)
        self.bind_form_scroll(canvas, canvas)
        frame.columnconfigure(1, weight=1)
        self.notebook.add(container, text=name)
        return frame

    @staticmethod
    def bind_form_scroll(widget, canvas):
        def wheel(event):
            bounds = canvas.bbox("all")
            if bounds and bounds[3] > canvas.winfo_height():
                amount = -1 if getattr(event, "num", None) == 4 else 1 if getattr(event, "num", None) == 5 else -int(event.delta / 120)
                canvas.yview_scroll(amount, "units")
                return "break"
        for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            widget.bind(sequence, wheel, add="+")

    def field(self, frame, row, label, path, integer=False, choices=None, readonly=False):
        value = self.item()
        for part in path:
            value = value.get(part,'') if isinstance(value,dict) else value[part]
        variable = tk.StringVar(value=str(value))
        variable.trace_add("write", lambda *_: self.changed())
        self.variables[tuple(path)] = (variable, integer)
        title = ttk.Label(frame, text=label, style="Card.TLabel")
        title.grid(row=row, column=0, sticky="w", padx=(0, 14), pady=5)
        control = ttk.Combobox(frame, textvariable=variable, values=choices, state="readonly") if choices is not None else ttk.Entry(frame, textvariable=variable, state="readonly" if readonly else "normal")
        control.grid(row=row, column=1, sticky="ew", pady=5)
        self.field_controls[tuple(path)]=control
        if hasattr(frame, "editor_canvas"):
            self.bind_form_scroll(title, frame.editor_canvas)
            # Keep native combobox wheel selection instead of scrolling twice.
            if choices is None:
                self.bind_form_scroll(control, frame.editor_canvas)

    def changed(self):
        self.form_dirty = True
        self.status.set("Unsaved edits. Validate checks the complete project; Save preserves disk files if validation fails.")
        workspace=getattr(self._editor_scope,'workspace',None)
        if workspace:workspace.status.set(self.status.get())

    def populate(self):
        self.stop_sprite()
        for button in (self.duplicate_button,self.delete_button,self.definition_button):
            button.state(['disabled'] if self.library_context and self.collection in ('mechs','people') else ['!disabled'])
        for tab in self.notebook.tabs():
            self.notebook.nametowidget(tab).destroy()
        self.variables = {}
        self.field_controls = {}
        self.form_dirty = False
        if not self.current:
            self.selection_title.configure(text="Definition details")
            frame = self.tab("Get started")
            ttk.Label(frame, text="Create your game", style="Heading.TLabel").pack(anchor="w", pady=(4, 12))
            ttk.Label(frame, text="Open a project or choose New project to make your own copy.\n\n"
                      "Use the roster to edit mechs and weapons. Open Maps / events to build terrain, place people and write your story.",
                      style="CardMuted.TLabel", wraplength=450, justify="left").pack(anchor="w")
            return
        self.selection_title.configure(text=self.item().get("name",self.current))
        if self.collection in ('mechs','people'):self.start_sprite()
        general = self.tab("Properties")
        self.field(general, 0, "Stable ID", ["id"], readonly=True)
        self.field(general, 1, "Full name", ["name"])
        if self.collection=='people':
            names=('jason','rex','edward','russ','rick','zeke','possum','marco','rusty','hunter')
            choices=[f'actor:{i}' for i in range(10)]+['chi:'+n for n in names]
            self.field(general,2,'Actor identity',['identity'],choices=choices)
            for row,label in enumerate(('Strength','Dexterity','Intelligence'),3):
                self.field(general,row,label,['attributes',row-3],integer=True)
            self.field(general,6,'Personal weapon (0-13)',['weapon'],integer=True)
            self.field(general,7,'Personal armour (0-5)',['armor'],integer=True)
            ttk.Label(general,text='Individual infantry / character template.\nEach template can select its own sprite; an unset sprite uses the project default.',style='CardMuted.TLabel').grid(row=8,column=0,columnspan=2,sticky='w',pady=10)
            ttk.Button(general,text='Choose sprite...',command=lambda:self.guarded(self.choose_sprite)).grid(row=9,column=1,sticky='w')
            skills=self.tab('Skills')
            for row,label in enumerate(('Sidearms','Rifles','Heavy arms','Gunnery','Piloting','Technical','Medical')):
                self.field(skills,row,label+' (0-4)',['skills',row],integer=True)
            return
        self.field(general, 2, "Game label", ["label"])
        if self.collection == "mechs":
            vehicle=self.item().get('kind')=='vehicle'
            for row, (label, path) in enumerate([("Mass (tons)", ["mass_tons"]), ("Price (C-bills)", ["price"]),
                    ("Walk", ["movement", "walk"]), ("Jump", ["movement", "jump"]),
                    ("Engine heat sinks", ["engine_heat_sinks"])], 3):
                self.field(general, row, label, path, integer=True)
            self.field(general, 8, "Presentation", ["presentation"], choices=[p["id"] for p in self.document.content["presentations"]])
            ttk.Button(general,text='Choose sprite...',command=lambda:self.guarded(self.choose_sprite)).grid(row=9,column=1,sticky='w',pady=8)
            from construction_guidance import show as guidance
            ttk.Button(general,text='Construction guidance',command=lambda:self.guarded(lambda:guidance(self))).grid(row=11,column=1,sticky='w',pady=8)
            if vehicle:self.field(general,10,'Drive type',['movement','type'],choices=['tracked','wheeled','hover'])
            for name, key in [("Armor", "armor"), ("Structure", "structure")]+([] if vehicle else [("Equipment", "external_heat_sinks")]):
                frame = self.tab(name)
                for row, field in enumerate(self.item()[key]):
                    self.field(frame, row, field.replace("_", " ").title(), [key, field], integer=True)
                if key == "external_heat_sinks":
                    for row, field in enumerate(self.item()["actuators"], len(LOCATIONS)):
                        self.field(frame, row, field.replace("_", " ").title() + " actuators (0-15)", ["actuators", field], integer=True)
                    ttk.Button(frame,text='Installed equipment',command=lambda:self.guarded(self.installed_equipment)).grid(row=12,column=1,sticky='w',pady=10)
            self.loadout = copy.deepcopy(self.item()["loadout"])
            frame = self.tab("Loadout")
            self.mounts = ttk.Treeview(frame, columns=("weapon", "location", "ammo"), show="headings", height=12, selectmode="browse")
            for key, heading, width in [("weapon", "Weapon ID", 240), ("location", "Location", 130), ("ammo", "Ammo capacity", 100)]:
                self.mounts.heading(key, text=heading)
                self.mounts.column(key, width=width)
            self.mounts.pack(fill="both", expand=True)
            self.mounts.bind("<Double-1>", lambda _e: self.guarded(lambda: self.mount_dialog(False)))
            buttons = ttk.Frame(frame, style="Card.TFrame", borderwidth=0)
            buttons.pack(fill="x", pady=8)
            for label, cb in [("Add mount", lambda: self.mount_dialog(True)), ("Edit mount", lambda: self.mount_dialog(False)), ("Remove mount", self.remove_mount)]:
                ttk.Button(buttons, text=label, command=lambda f=cb: self.guarded(f)).pack(side="left", padx=4)
            self.refresh_mounts()
        elif self.collection=='equipment':
            self.field(general,3,'Behavior',['behavior'],choices=['heat_sink','jump_jet','engine_heat_sink','armor_plating'])
            ttk.Label(general,text='Heat sink: one cooling point and one damageable component slot.\nJump jet: one jump point; CHI does not model individual jet damage.\nInstall these on a mech in its Equipment tab.',style='CardMuted.TLabel',wraplength=490).grid(row=4,column=0,columnspan=2,pady=16,sticky='w')
        else:
            self.field(general, 3, "Behavior", ["behavior"], choices=WEAPONS)
            self.field(general, 4, "Ammunition", ["ammunition"], choices=["none"] + [p["id"] for p in self.document.content["ammunition"]])
            for row, (label, path) in enumerate([("Damage per projectile", ["damage"]), ("Projectiles", ["projectiles"]),
                    ("Heat", ["heat"]), ("Short range", ["ranges", "short"]), ("Medium range", ["ranges", "medium"]),
                    ("Long range", ["ranges", "long"])], 5):
                self.field(general, row, label, path, integer=True)
            ttk.Label(general, text="Ranges use CHI map distances. Updated LRMs use the package's LRM rules.\nThe C validator checks supported behavior and ammunition combinations.", style="CardMuted.TLabel", wraplength=490).grid(row=11, column=0, columnspan=2, pady=16, sticky="w")

    def apply_form(self):
        if not self.form_dirty or not self.document or not self.current:
            return
        content = copy.deepcopy(self.document.content)
        adventure = copy.deepcopy(self.document.adventure)
        values=adventure['people'] if self.collection=='people' else content[self.collection]
        item = next(v for v in values if v["id"] == self.current)
        for path, (variable, integer) in self.variables.items():
            target = item
            for key in path[:-1]:
                target = target[key]
            try:
                target[path[-1]] = int(variable.get()) if integer else variable.get()
            except ValueError as exc:
                raise FieldError(f"{'.'.join(map(str,path))} must be a whole number.",path) from exc
        if self.collection == "mechs":
            item["loadout"] = copy.deepcopy(self.loadout)
        self.document.replace_both(content,adventure)
        self.form_dirty = False

    def refresh_mounts(self):
        self.mounts.delete(*self.mounts.get_children())
        for index, mount in enumerate(self.loadout):
            self.mounts.insert("", "end", iid=str(index), values=(mount["weapon"], mount["location"], mount["ammunition"]))

    def mount_dialog(self, adding):
        selected = self.mounts.selection()
        if not adding and not selected:
            return
        weapons = [w["id"] for w in self.document.content["weapons"]]
        if not weapons:
            raise EditorError("Create a weapon definition first.")
        index = len(self.loadout) if adding else int(selected[0])
        mount = dict(weapon=weapons[0], location="left_arm", ammunition=0) if adding else self.loadout[index]
        from adventure_editor import Form
        dialog=Form(self,'Weapon mount')
        locations=['front','left','right','rear','turret'] if self.item().get('kind')=='vehicle' else LOCATIONS
        if adding:mount['location']=locations[0]
        for key, choices in [("weapon", weapons), ("location", locations), ("ammunition", None)]:
            dialog.field(key,mount[key],choices)
        def apply(values):
            new = {key: int(value) if key == "ammunition" else value for key, value in values.items()}
            if adding:
                self.loadout.append(new)
            else:
                self.loadout[index] = new
            self.changed()
            self.refresh_mounts()
        dialog.submit(apply)
        return dialog

    def remove_mount(self):
        if self.mounts.selection():
            self.loadout.pop(int(self.mounts.selection()[0]))
            self.changed()
            self.refresh_mounts()

    def duplicate(self):
        if self.document and self.current:
            self.apply_form()
            if self.collection=='people':
                from unit_library import fresh_id
                a=copy.deepcopy(self.document.adventure);value=copy.deepcopy(self.item())
                value['id']=fresh_id(self.document.manifest['package_id'],a['people'],'person')
                value['name']=value.get('name','Infantry')[:89]+' copy';a['people'].append(value)
                self.document.replace_adventure(a);self.refresh_list(value['id']);return
            index = next(i for i, value in enumerate(self.document.content[self.collection]) if value["id"] == self.current)
            identity = self.document.duplicate(self.collection, index)
            self.search.set("")
            self.refresh_list(identity)
            self.status.set("Copy added with a new stable ID. Edit its properties, then Validate.")

    def guard(self,fn):return self.guarded(fn)

    def new_definition(self):
        if not self.document:return
        if self.collection=='people':
            self.edit_adventure();self.map_editor.person_dialog();return
        from adventure_editor import Form
        from unit_editing import add_unit,add_weapon,add_equipment
        self.apply_form();f=Form(self,'New definition')
        if self.kind.get()=='Equipment':
            f.field('name','Heat sink');f.field('behavior','heat_sink',['heat_sink','jump_jet','engine_heat_sink','armor_plating'])
        elif self.kind.get()=='Weapons':
            f.field('name','New weapon');f.field('behavior','medium_laser',WEAPONS)
        else:
            f.field('name','New vehicle' if self.kind.get()=='Vehicles' else 'New mech')
            f.field('kind','tracked' if self.kind.get()=='Vehicles' else 'mech',['mech','tracked','wheeled','hover'])
        def apply(v):
            content=copy.deepcopy(self.document.content)
            if self.collection=='equipment':identity=add_equipment(content,v['behavior'],v['name'])
            elif 'behavior' in v:identity=add_weapon(content,v['behavior'],v['name'])
            else:
                identity=add_unit(content,v['kind'],v['name']);self.kind.set('Mechs' if v['kind']=='mech' else 'Vehicles');self.collection='mechs'
            self.document.replace(content);self.search.set('');self.refresh_list(identity)
        f.submit(apply)

    def installed_equipment(self):
        self.apply_form()
        from adventure_editor import Form
        unit_id=self.current;equipment=self.document.content.get('equipment',[])
        if not equipment:raise EditorError('Choose Equipment in the roster, then New definition to create a heat sink or jump jet first.')
        original=copy.deepcopy(self.item().get('equipment',[]));f=Form(self,'Installed mech equipment')
        choice=f.field('entry','New',['New',*[str(i+1) for i in range(len(original))]])
        f.field('definition',equipment[0]['id'],[e['id'] for e in equipment]);f.field('location','left_torso',LOCATIONS);f.field('quantity',1)
        f.field('action','Install / update',['Install / update','Remove'])
        def select(_):
            value=f.values['entry'].get()
            if value!='New':
                for key,value in original[int(value)-1].items():f.values[key].set(str(value))
        choice.bind('<<ComboboxSelected>>',select)
        ttk.Label(f.body,text='Heat sinks add to the numeric external sinks above.\nFor installed jump jets, set the base Jump property to 0.',wraplength=480).grid(row=f.row,column=0,columnspan=2,pady=10);f.row+=1
        def apply(v):
            content=copy.deepcopy(self.document.content);unit=next(m for m in content['mechs'] if m['id']==unit_id)
            entries=copy.deepcopy(original);index=None if v['entry']=='New' else int(v['entry'])-1
            if v['action']=='Remove':
                if index is not None:entries.pop(index)
            else:
                quantity=int(v['quantity'])
                if not 1<=quantity<=12:raise EditorError('Equipment quantity must be 1-12.')
                entry=dict(definition=v['definition'],location=v['location'],quantity=quantity)
                if index is None:entries.append(entry)
                else:entries[index]=entry
            unit['equipment']=entries;self.document.replace(content);self.refresh_list(unit_id)
        f.submit(apply)

    def choose_sprite(self):
        self.apply_form()
        infantry=self.collection=='people'
        from adventure_editor import Form
        from unit_editing import assign_graphic
        from graphics_editor import photo
        sprites=[im for im in self.document.art['images'] if im['kind']=='sprite']
        if not sprites:
            self.graphics_editor()
            self.status.set('Create or import a sprite in Graphics, then choose it for this unit.');return
        identity=self.current;f=Form(self,'Choose unit sprite');choice=f.field('image',sprites[0]['id'],[i['id'] for i in sprites])
        preview=ttk.Label(f.body);preview.grid(row=f.row,column=0,columnspan=2,pady=12);f.row+=1
        def show(*_):
            im=next(i for i in sprites if i['id']==f.values['image'].get());preview.image=photo(f.window,im,zoom=4);preview.configure(image=preview.image)
        choice.bind('<<ComboboxSelected>>',show);show()
        def apply(v):
            if infantry:
                adventure=copy.deepcopy(self.document.adventure)
                next(p for p in adventure['people'] if p['id']==identity)['image']=v['image']
                self.document.replace_adventure(adventure);self.refresh_list(identity);return
            content=copy.deepcopy(self.document.content);assign_graphic(content,identity,v['image']);self.document.replace(content);self.refresh_list(identity)
        f.submit(apply)

    def stop_sprite(self):
        if self.sprite_timer is not None:self.window.after_cancel(self.sprite_timer)
        self.sprite_timer=None;self.sprite_photos=[];self.sprite_source=None
        if self.sprite_panel.winfo_exists():self.sprite_panel.pack_forget()

    def start_sprite(self):
        from editor_units import unit_sprite,person_sprite
        from graphics_editor import photo
        self.sprite_panel.pack(side='right')
        self.sprite_canvas.delete('all')
        try:
            self.sprite_source=person_sprite(self.document,self.settings,self.item()) if self.collection=='people' else unit_sprite(self.document,self.settings,self.item())
            image=self.sprite_source;zoom=max(1,min(5,96//max(image['width'],image['height'])))
            from action_tracks import entries
            track=entries(image,'walk',4)
            frames=[e['frame'] for e in track] if track else range(len(image['frames']))
            self.sprite_delays=[32*e['ticks'] for e in track] if track else [140]*len(image['frames'])
            self.sprite_photos=[photo(self.window,image,frame=i,zoom=zoom) for i in frames]
        except (EditorError,OSError,KeyError,StopIteration) as exc:
            self.sprite_canvas.create_text(60,50,text='Sprite unavailable\nCheck Player setup',width=110,fill='#637181',font='TkDefaultFont')
            self.status.set(str(exc));return
        self.sprite_index=0;self.animate_sprite()

    def animate_sprite(self):
        self.sprite_timer=None
        if not self.sprite_photos or not self.sprite_canvas.winfo_exists():return
        self.sprite_canvas.delete('animation')
        self.sprite_canvas.create_image(60,50,image=self.sprite_photos[self.sprite_index],tags='animation')
        delay=self.sprite_delays[self.sprite_index]
        self.sprite_index=(self.sprite_index+1)%len(self.sprite_photos)
        self.sprite_timer=self.window.after(delay,self.animate_sprite)

    def sprite_context(self,event):
        from editor_ui import popup_menu
        popup_menu(self.sprite_menu,event)

    def edit_unit_sprite(self):
        self.apply_form()
        if self.collection=='people':
            self.edit_person_sprite();return
        from art_editing import clone_image
        from editor_units import unit_sprite
        from unit_editing import assign_graphic
        from graphics_editor import open_image_editor
        unit_id=self.current;view=next(p for p in self.document.content['presentations'] if p['id']==self.item()['presentation'])
        image=unit_sprite(self.document,self.settings,self.item())
        if view['source']!='package:art':
            # Editing a reference sprite explicitly makes a package copy;
            # the original resources and other units' choices stay intact.
            image=clone_image(image,self.document.content['package_id'],self.document.art['images'])
            art=copy.deepcopy(self.document.art);art['images'].append(image)
            content=copy.deepcopy(self.document.content);assign_graphic(content,unit_id,image['id'])
            manifest=copy.deepcopy(self.document.manifest)
            if 'graphics' not in manifest:
                if 'graphics.json' not in self.document.snapshot and (self.document.root/'graphics.json').exists():raise EditorError('Declare or rename the existing graphics.json before copying a sprite.')
                manifest['graphics']='graphics.json'
            self.document.replace_all(content,self.document.adventure,art,manifest)
        library=self.graphics_editor()
        library.selected=image['id'];library.refresh();open_image_editor(library,image)
        self.refresh_list(unit_id)

    def edit_person_sprite(self):
        from editor_units import person_sprite
        from art_editing import clone_image,bind
        from graphics_editor import open_image_editor
        image=person_sprite(self.document,self.settings,self.item())
        if not self.item().get('image'):
            image=clone_image(image,self.document.manifest['package_id'],self.document.art['images'])
            art=copy.deepcopy(self.document.art);art['images'].append(image)
            adventure=copy.deepcopy(self.document.adventure)
            next(p for p in adventure['people'] if p['id']==self.current)['image']=image['id']
            self.document.replace_art(art,adventure=adventure)
        library=self.graphics_editor()
        library.selected=image['id'];library.refresh();open_image_editor(library,image)

    def open_library(self):
        from library_browser import LibraryBrowser
        if getattr(self,'unit_library_window',None) and self.unit_library_window.window.winfo_exists():
            self.unit_library_window.window.lift();return
        self.unit_library_window=LibraryBrowser(self)

    def library_graphics(self):
        return self.graphics_editor()

    def graphics_editor(self):
        from graphics_editor import GraphicsEditor
        from editor_workspace import existing_view
        existing=existing_view(self,'graphics')
        if existing:self.art_editor=existing;return existing
        if self.art_editor and self.art_editor.window.winfo_exists():self.art_editor.window.lift();return self.art_editor
        self.art_editor=GraphicsEditor(self)
        return self.art_editor

    def vehicle_catalogue(self):
        if not self.document:return
        if self.document.adventure is None:raise EditorError('Vehicles require an authored adventure project. Create one from a demo first.')
        from adventure_editor import Form
        from unit_editing import import_catalogue
        self.apply_form();catalogue=ROOT/'content/catalogues/vehicles';data=json.loads((catalogue/'units.json').read_text())
        f=Form(self,'Add vehicles');listing=tk.Listbox(f.body,selectmode='multiple',exportselection=False,height=12,width=55)
        listing.grid(row=0,column=0,columnspan=2,padx=10,pady=10);f.row=1
        for unit in data['mechs']:listing.insert('end',f"{unit['mass_tons']:3d}t  {unit['name']} ({unit['movement']['type']})")
        listing.selection_set(0,'end')
        ttk.Label(f.body,text='Adds editable definitions and original pixel sprites.\nPlace units in Start, shop stock or encounters under Maps / events.',wraplength=500).grid(row=1,column=0,columnspan=2);f.row=2
        def apply(_):
            ids=[data['mechs'][i]['id'] for i in listing.curselection()]
            if not ids:return
            import_catalogue(self.document,catalogue,ids);self.kind.set('Vehicles');self.collection='mechs';self.search.set('');self.refresh_list(ids[0])
            if self.map_editor:self.map_editor.refresh()
        f.submit(apply)

    def ammunition(self):
        if not self.document:return
        from adventure_editor import Form
        from unit_editing import add_ammo
        self.apply_form();f=Form(self,'Ammunition definitions');ids=[a['id'] for a in self.document.content['ammunition']]
        choice=f.field('id','New',['New',*ids]);f.field('price',3,label='Price per shot (1-254)')
        def select(_):
            entry=next((a for a in self.document.content['ammunition'] if a['id']==f.values['id'].get()),None)
            if entry:f.values['price'].set(str(entry['price_per_shot']))
        choice.bind('<<ComboboxSelected>>',select)
        def apply(v):
            content=copy.deepcopy(self.document.content);price=int(v['price'])
            if not 1<=price<=254:raise EditorError('Ammunition price must be 1-254 per shot.')
            if v['id']=='New':add_ammo(content,price)
            else:next(a for a in content['ammunition'] if a['id']==v['id'])['price_per_shot']=price
            self.document.replace(content);self.refresh_list()
        f.submit(apply)

    def delete(self):
        if self.document and self.current:
            if hasattr(self._editor_scope,'workspace'):
                from editor_dependencies import dialog
                return dialog(self,self.current,delete=True)
            self.apply_form()
            if self.collection=='people':
                a=copy.deepcopy(self.document.adventure);a['people']=[p for p in a['people'] if p['id']!=self.current]
                self.document.replace_adventure(a);self.current=None;self.refresh_list();return
            content = copy.deepcopy(self.document.content)
            content[self.collection] = [v for v in content[self.collection] if v["id"] != self.current]
            self.document.replace(content)
            self.current = None
            self.refresh_list()
            self.status.set("Definition removed in memory. Undo restores it; validation catches remaining references.")

    def undo(self):
        if self.document:
            if self.map_editor and self.map_editor.stroke is not None:
                self.map_editor.cancel_gesture()
                self.status.set("Unfinished map gesture cancelled.")
                return
            if self.form_dirty:
                # A half-typed/non-numeric field is reversible too. It has
                # not reached the document history or the disk yet.
                self.populate()
                self.status.set("Unapplied form edits undone.")
                return
            if self.map_editor and self.map_editor.event_pending:
                self.map_editor.event_pending = False
                self.map_editor.populate_event()
                self.status.set("Unapplied event edits undone.")
                return
            self.document.undo()
            self.refresh_list()
            if self.map_editor:
                self.map_editor.refresh()
                self.map_editor.populate_event()
            self.status.set("Undo applied.")

    def redo(self):
        if self.document:
            if self.map_editor:
                self.map_editor.apply_pending()
            self.apply_form()
            self.document.redo()
            self.refresh_list()
            if self.map_editor:
                self.map_editor.refresh()
                self.map_editor.populate_event()
            self.status.set("Redo applied.")

    def save(self):
        if self.document:
            result=self._editor_scope.transact(lambda:self.library_context.commit(self) if self.library_context else self.document.save())
            if not self.library_context:self.status.set(result)
            self.refresh_list()

    def validate(self):
        if self.document:
            self.status.set(self._editor_scope.transact(self.document.validate))

    def setup(self):
        dialog = tk.Toplevel(self.window)
        dialog.title("Player setup")
        dialog.transient(self.window)
        dialog.configure(background=self.palette["background"])
        dialog.columnconfigure(1, weight=1)
        values = {key: tk.StringVar(value=value) for key, value in self.settings.items()}
        keys = ["player"] if self.document and self.document.manifest["requires"] == "none" else ["player", "data", "dialogue-data", "combat-data", "world-data"]
        ttk.Label(dialog, text="Playtest setup", style="Title.TLabel").grid(row=0, column=0, columnspan=3, sticky="w", padx=14, pady=(14, 6))
        explanation = "Choose the built game player to test your package." if len(keys) == 1 else "Choose the game player and your original game files. Terrain previews use the original game folder."
        ttk.Label(dialog, text=explanation, style="Muted.TLabel", wraplength=700).grid(row=1, column=0, columnspan=3, sticky="w", padx=14, pady=(0, 10))
        labels = {"player": "Game player", "data": "Original game folder", "dialogue-data": "Dialogue cache",
                  "combat-data": "Combat cache", "world-data": "World cache"}
        for row, key in enumerate(keys, 2):
            ttk.Label(dialog, text=labels[key]).grid(row=row, column=0, padx=(14, 10), pady=6, sticky="w")
            ttk.Entry(dialog, textvariable=values[key], width=65).grid(row=row, column=1, padx=8, pady=6)
            def browse(k=key):
                path = filedialog.askdirectory(parent=dialog) if k == "data" else filedialog.askopenfilename(parent=dialog)
                if path:
                    values[k].set(path)
            ttk.Button(dialog, text="Browse", command=browse).grid(row=row, column=2, padx=(8, 14))
        def apply():
            self.settings = {key: value.get() for key, value in values.items()}
            self.state_dir.mkdir(parents=True, exist_ok=True)
            (self.state_dir / "settings.json").write_text(json.dumps(self.settings, indent=2), encoding="utf-8")
            dialog.destroy()
            if self.map_editor:
                self.map_editor.reload_graphics()
            self.status.set("Player setup saved. Open map previews use the current graphics paths.")
        ttk.Button(dialog, text="Save setup", style="Accent.TButton", command=lambda: self.guarded(apply)).grid(row=len(keys)+2, column=1, sticky="e", pady=14)
        dialog.bind("<Escape>", lambda _e: dialog.destroy())

    def play(self):
        if self.document:
            if self.map_editor:
                self.map_editor.apply_pending()
            self.launch_player()

    def launch_player(self, here=None):
        if self.document:
            if hasattr(self.window,'workspace'):
                return self.window.workspace.play_session.start(self._editor_scope,here=here)
            self.apply_form()
            from app_runtime import prepare_original
            if self.document.manifest['requires']!='none':prepare_original(self.settings)
            command = self.document.play_command(self.settings, self.state_dir, here=here)
            self.state_dir.mkdir(parents=True, exist_ok=True)
            with (self.state_dir / "player.log").open("a", encoding="utf-8") as log:
                subprocess.Popen(command, cwd=self.state_dir, stdout=log, stderr=log)
            self.status.set("Player launched with a fresh campaign and separate playtest save slots. See player.log for launch diagnostics.")

    def edit_adventure(self):
        if not self.document:
            raise EditorError("Open or create a project first.")
        self.apply_form()
        if self.map_editor and self.map_editor.window.winfo_exists():
            self.map_editor.window.lift()
        else:
            from adventure_editor import AdventureEditor
            self.map_editor = AdventureEditor(self)

    def export_project(self):
        if self.document:
            if self.map_editor:
                self.map_editor.apply_pending()
            self.apply_form()
            parent = filedialog.askdirectory(title="Export game into a NEW subfolder of", parent=self.window)
            if not parent:
                return
            name = simpledialog.askstring("Export folder", "New folder name:", initialvalue=self.document.manifest["package_id"] + "-export", parent=self.window)
            if not name:
                return
            if Path(name).name != name or name in (".", "..") or "\\" in name:
                raise EditorError("Choose one new folder name.")
            target = Path(parent) / name
            workspace=getattr(self._editor_scope,'workspace',None)
            if workspace:
                from editor_tasks import export
                return export(workspace,self._editor_scope,target)
            self.document.export(target)
            self.status.set(f"Validated project exported to {target}. Saves and caches were excluded.")

    def close(self):
        workspace=getattr(self._editor_scope,'workspace',None)
        if workspace and self is workspace.app:return workspace.close()
        if workspace:return workspace.close_scope(self._editor_scope)
        def finish():
            library=getattr(self,'unit_library_window',None)
            if library and library.window.winfo_exists():
                library.close()
                if library.window.winfo_exists():return
            if self.discard_or_save():
                self.window.destroy()
        self.guarded(finish)


def main():
    from app_runtime import binary
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", nargs="?", type=Path)
    parser.add_argument("--validator", type=Path, default=binary('btp-project'))
    parser.add_argument("--state-dir", type=Path, default=ROOT / "work/roster-editor")
    args = parser.parse_args()
    window = tk.Tk()
    from editor_workspace import create_editor
    app = create_editor(window, args.validator, args.state_dir.resolve())
    if args.project:
        app.guarded(lambda: app.set_document(ProjectDocument(args.project, args.validator)))
    window.mainloop()


if __name__ == "__main__":
    main()
