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
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk, filedialog, messagebox, simpledialog

from editor_model import EditorError, ProjectDocument, create_project

ROOT = Path(__file__).resolve().parents[1]
LOCATIONS = ["left_arm", "left_torso", "left_leg", "head", "center_torso", "right_arm", "right_torso", "right_leg"]
WEAPONS = ["small_laser", "medium_laser", "large_laser", "ppc", "ac2", "ac5", "ac10", "ac20", "machine_gun", "flamer", "lrm5", "lrm10", "lrm15", "lrm20", "srm2", "srm4", "srm6"]


def configure_editor_style(window):
    """Share a quiet, native-font palette with the roster and map windows."""
    style = ttk.Style(window)
    if "clam" in style.theme_names() and os.name != "nt":
        style.theme_use("clam")
    palette = dict(background="#f3f3f0", surface="#ffffff", text="#293747",
                   muted="#637181", border="#d9dfe3", accent="#286c80",
                   selection="#deedf2")
    font = tkfont.nametofont("TkDefaultFont").actual()
    size = font["size"]
    heading = (font["family"], size + 1 if size > 0 else size - 1, "bold")
    title = (font["family"], size + 5 if size > 0 else size - 5, "bold")
    style.configure(".", background=palette["background"], foreground=palette["text"])
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
                    font=(font["family"], size, "bold"))
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
    style.configure("Treeview", rowheight=25, background=palette["surface"], fieldbackground=palette["surface"])
    style.configure("Treeview.Heading", padding=(8, 6))
    style.map("Treeview", background=[("selected", palette["selection"])],
              foreground=[("selected", palette["text"])])
    style.configure("Status.TLabel", background="#e9edef", foreground=palette["muted"], padding=(14, 9))
    window.configure(background=palette["background"])
    # Tk listboxes/text controls follow the same palette as native ttk fields.
    for option, value in {"background": palette["surface"], "foreground": palette["text"],
                          "selectBackground": palette["selection"], "selectForeground": palette["text"],
                          "highlightBackground": palette["border"], "highlightColor": palette["accent"]}.items():
        window.option_add(f"*Listbox.{option}", value)
    return palette


class RosterEditor:
    def __init__(self, window: tk.Tk, validator: Path, state_dir: Path):
        self.window, self.validator, self.state_dir = window, validator, state_dir
        self.document: ProjectDocument | None = None
        self.map_editor = None
        self.current = None
        self.collection = "mechs"
        self.variables: dict[tuple[str, ...], tuple[tk.StringVar, bool]] = {}
        self.loadout = []
        self.populating = False
        self.form_dirty = False
        self.settings = self.defaults()
        try:
            self.settings.update(json.loads((state_dir / "settings.json").read_text()))
        except (OSError, ValueError):
            pass
        self.palette = configure_editor_style(window)
        window.title("BtechPort game editor")
        window.geometry("1000x740")
        window.minsize(940, 690)
        header = ttk.Frame(window, style="App.TFrame", padding=(16, 12, 16, 8))
        header.pack(fill="x")
        ttk.Label(header, text="Game editor", style="Title.TLabel").pack(side="left")
        self.profile_label = ttk.Label(header, text="Create a game or open a project.", style="Muted.TLabel")
        self.profile_label.pack(side="right", anchor="s", pady=3)
        actions = ttk.Frame(window, style="Card.TFrame", padding=(9, 7))
        actions.pack(fill="x", padx=14, pady=(0, 8))
        toolbar = ttk.Frame(actions, style="Card.TFrame", borderwidth=0)
        toolbar.pack(fill="x")
        for group in [[("New project", self.new_project), ("Open", self.open_project), ("Save", self.save)],
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
        ttk.Button(author_bar, text="Maps / events", style="Toolbar.TButton",
                   command=lambda: self.guarded(self.edit_adventure)).pack(side="left", padx=2)
        ttk.Button(author_bar, text="Export game", style="Toolbar.TButton",
                   command=lambda: self.guarded(self.export_project)).pack(side="left", padx=2)
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
        box = ttk.Combobox(left, textvariable=self.kind, values=["Mechs", "Weapons"], state="readonly")
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
        ttk.Button(buttons, text="Duplicate / add", command=lambda: self.guarded(self.duplicate)).pack(side="left")
        ttk.Button(buttons, text="Delete", style="Danger.TButton", command=lambda: self.guarded(self.delete)).pack(side="right")
        self.selection_title = ttk.Label(right, text="Definition details", style="App.TLabel", padding=(2, 2, 0, 6))
        self.selection_title.pack(anchor="w")
        self.notebook = ttk.Notebook(right)
        self.notebook.pack(fill="both", expand=True)
        self.status = tk.StringVar(value="Ready")
        ttk.Label(window, textvariable=self.status, style="Status.TLabel", wraplength=900).pack(fill="x")
        window.protocol("WM_DELETE_WINDOW", self.close)
        window.bind("<Control-s>", lambda _e: self.guarded(self.save))
        window.bind("<Control-z>", lambda _e: self.guarded(self.undo))
        window.bind("<Control-y>", lambda _e: self.guarded(self.redo))
        self.populate()

    @staticmethod
    def defaults() -> dict:
        suffix = ".exe" if os.name == "nt" else ""
        return {"player": str(ROOT / "build" / ("btech-port" + suffix)), "data": str(ROOT / "Original DOS"),
                **{key + "-data": str(ROOT / "work" / (key + "-data.bin")) for key in ["combat", "world"]},
                "dialogue-data": str(ROOT / "work/talk-data.bin")}

    def guarded(self, operation):
        try:
            return operation()
        except (EditorError, OSError, ValueError, KeyError, IndexError) as exc:
            self.status.set(str(exc))
            messagebox.showerror("Roster editor", str(exc), parent=self.window)
            return None

    def discard_or_save(self) -> bool:
        if self.map_editor:
            self.map_editor.apply_pending()
        if not self.document or not (self.document.dirty or self.form_dirty):
            return True
        answer = messagebox.askyesnocancel("Unsaved edits", "Save your changes before closing this project?", parent=self.window)
        if answer is None:
            return False
        if answer:
            self.save()
        return True

    def set_document(self, document: ProjectDocument):
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

    def open_project(self):
        if not self.discard_or_save():
            return
        path = filedialog.askdirectory(title="Open directory containing project.json", parent=self.window)
        if path:
            self.set_document(ProjectDocument(Path(path), self.validator))

    def new_project(self):
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
            self.set_document(create_project(template, Path(parent) / package_id, package_id, title, self.validator))

    def change_kind(self):
        self.apply_form()
        self.collection = "mechs" if self.kind.get() == "Mechs" else "weapons"
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
            query = self.search.get().lower()
            for item in self.document.content[self.collection]:
                if query and query not in (item["name"] + " " + item["id"]).lower():
                    continue
                self.visible.append(item["id"])
                self.listing.insert("end", (f"{item['mass_tons']:3d}t  " if self.collection == "mechs" else "") + item["name"])
            total = len(self.document.content[self.collection])
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
        return next(v for v in self.document.content[self.collection] if v["id"] == self.current)

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
            value = value[part]
        variable = tk.StringVar(value=str(value))
        variable.trace_add("write", lambda *_: self.changed())
        self.variables[tuple(path)] = (variable, integer)
        title = ttk.Label(frame, text=label, style="Card.TLabel")
        title.grid(row=row, column=0, sticky="w", padx=(0, 14), pady=5)
        control = ttk.Combobox(frame, textvariable=variable, values=choices, state="readonly") if choices is not None else ttk.Entry(frame, textvariable=variable, state="readonly" if readonly else "normal")
        control.grid(row=row, column=1, sticky="ew", pady=5)
        if hasattr(frame, "editor_canvas"):
            self.bind_form_scroll(title, frame.editor_canvas)
            # Keep native combobox wheel selection instead of scrolling twice.
            if choices is None:
                self.bind_form_scroll(control, frame.editor_canvas)

    def changed(self):
        self.form_dirty = True
        self.status.set("Unsaved edits. Validate checks the complete project; Save preserves disk files if validation fails.")

    def populate(self):
        for tab in self.notebook.tabs():
            self.notebook.nametowidget(tab).destroy()
        self.variables = {}
        self.form_dirty = False
        if not self.current:
            self.selection_title.configure(text="Definition details")
            frame = self.tab("Get started")
            ttk.Label(frame, text="Create your game", style="Heading.TLabel").pack(anchor="w", pady=(4, 12))
            ttk.Label(frame, text="Open a project or choose New project to make your own copy.\n\n"
                      "Use the roster to edit mechs and weapons. Open Maps / events to build terrain, place people and write your story.",
                      style="CardMuted.TLabel", wraplength=450, justify="left").pack(anchor="w")
            return
        self.selection_title.configure(text=self.item()["name"])
        general = self.tab("Properties")
        self.field(general, 0, "Stable ID", ["id"], readonly=True)
        self.field(general, 1, "Full name", ["name"])
        self.field(general, 2, "Game label", ["label"])
        if self.collection == "mechs":
            for row, (label, path) in enumerate([("Mass (tons)", ["mass_tons"]), ("Price (C-bills)", ["price"]),
                    ("Walk", ["movement", "walk"]), ("Jump", ["movement", "jump"]),
                    ("Engine heat sinks", ["engine_heat_sinks"])], 3):
                self.field(general, row, label, path, integer=True)
            self.field(general, 8, "Presentation", ["presentation"], choices=[p["id"] for p in self.document.content["presentations"]])
            for name, key in [("Armor", "armor"), ("Structure", "structure"), ("Components", "external_heat_sinks")]:
                frame = self.tab(name)
                for row, field in enumerate(self.item()[key]):
                    self.field(frame, row, field.replace("_", " ").title(), [key, field], integer=True)
                if key == "external_heat_sinks":
                    for row, field in enumerate(self.item()["actuators"], len(LOCATIONS)):
                        self.field(frame, row, field.replace("_", " ").title() + " actuators (0-15)", ["actuators", field], integer=True)
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
        item = next(v for v in content[self.collection] if v["id"] == self.current)
        for path, (variable, integer) in self.variables.items():
            target = item
            for key in path[:-1]:
                target = target[key]
            try:
                target[path[-1]] = int(variable.get()) if integer else variable.get()
            except ValueError as exc:
                raise EditorError(f"{'.'.join(path)} must be a whole number.") from exc
        if self.collection == "mechs":
            item["loadout"] = copy.deepcopy(self.loadout)
        self.document.replace(content)
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
        dialog = tk.Toplevel(self.window)
        dialog.title("Weapon mount")
        dialog.transient(self.window)
        dialog.grab_set()
        values = {key: tk.StringVar(value=str(value)) for key, value in mount.items()}
        for row, (key, choices) in enumerate([("weapon", weapons), ("location", LOCATIONS), ("ammunition", None)]):
            ttk.Label(dialog, text=key.title()).grid(row=row, column=0, padx=12, pady=8)
            widget = ttk.Combobox(dialog, textvariable=values[key], values=choices, state="readonly", width=42) if choices else ttk.Entry(dialog, textvariable=values[key])
            widget.grid(row=row, column=1, padx=12, pady=8, sticky="ew")
        def apply():
            new = {key: int(value.get()) if key == "ammunition" else value.get() for key, value in values.items()}
            if adding:
                self.loadout.append(new)
            else:
                self.loadout[index] = new
            self.changed()
            self.refresh_mounts()
            dialog.destroy()
        ttk.Button(dialog, text="Apply", command=lambda: self.guarded(apply)).grid(row=3, column=1, pady=12)
        dialog.bind("<Escape>", lambda _e: dialog.destroy())

    def remove_mount(self):
        if self.mounts.selection():
            self.loadout.pop(int(self.mounts.selection()[0]))
            self.changed()
            self.refresh_mounts()

    def duplicate(self):
        if self.document and self.current:
            self.apply_form()
            index = next(i for i, value in enumerate(self.document.content[self.collection]) if value["id"] == self.current)
            identity = self.document.duplicate(self.collection, index)
            self.search.set("")
            self.refresh_list(identity)
            self.status.set("Copy added with a new stable ID. Edit its properties, then Validate.")

    def delete(self):
        if self.document and self.current:
            self.apply_form()
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
            if self.map_editor:
                self.map_editor.apply_pending()
            self.apply_form()
            self.status.set(self.document.save())
            self.refresh_list()

    def validate(self):
        if self.document:
            if self.map_editor:
                self.map_editor.apply_pending()
            self.apply_form()
            self.status.set(self.document.validate())

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
            self.apply_form()
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
            self.document.export(target)
            self.status.set(f"Validated project exported to {target}. Saves and caches were excluded.")

    def close(self):
        def finish():
            if self.discard_or_save():
                self.window.destroy()
        self.guarded(finish)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", nargs="?", type=Path)
    suffix = ".exe" if os.name == "nt" else ""
    parser.add_argument("--validator", type=Path, default=ROOT / "build" / ("btp-project" + suffix))
    parser.add_argument("--state-dir", type=Path, default=ROOT / "work/roster-editor")
    args = parser.parse_args()
    window = tk.Tk()
    app = RosterEditor(window, args.validator, args.state_dir.resolve())
    if args.project:
        app.guarded(lambda: app.set_document(ProjectDocument(args.project, args.validator)))
    window.mainloop()


if __name__ == "__main__":
    main()
