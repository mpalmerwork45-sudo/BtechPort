#!/usr/bin/env python3
"""Small Windows/Linux roster editor for CHI-dependent project packages."""
from __future__ import annotations

import argparse
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

from editor_model import EditorError, ProjectDocument, create_project

ROOT = Path(__file__).resolve().parents[1]
LOCATIONS = ["left_arm", "left_torso", "left_leg", "head", "center_torso", "right_arm", "right_torso", "right_leg"]
WEAPONS = ["small_laser", "medium_laser", "large_laser", "ppc", "ac2", "ac5", "ac10", "ac20", "machine_gun", "flamer", "lrm5", "lrm10", "lrm15", "lrm20", "srm2", "srm4", "srm6"]


class RosterEditor:
    def __init__(self, window: tk.Tk, validator: Path, state_dir: Path):
        self.window, self.validator, self.state_dir = window, validator, state_dir
        self.document: ProjectDocument | None = None
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
        style = ttk.Style(window)
        if "clam" in style.theme_names() and os.name != "nt":
            style.theme_use("clam")
        window.title("BtechPort roster editor")
        window.geometry("1000x740")
        window.minsize(940, 690)
        toolbar = ttk.Frame(window, padding=8)
        toolbar.pack(fill="x")
        for label, command in [("New project", self.new_project), ("Open", self.open_project), ("Save", self.save),
                               ("Validate", self.validate), ("Undo", self.undo), ("Redo", self.redo),
                               ("Play", self.play), ("Player setup", self.setup)]:
            ttk.Button(toolbar, text=label, command=lambda cb=command: self.guarded(cb)).pack(side="left", padx=3)
        ttk.Label(window, text="CHI-dependent projects | original files required | edits require a new campaign", padding=(12, 2)).pack(anchor="w")
        self.project_label = ttk.Label(window, text="Open a project or create one from a template.", padding=(12, 4))
        self.project_label.pack(anchor="w")
        body = ttk.Panedwindow(window, orient="horizontal")
        body.pack(fill="both", expand=True, padx=10, pady=4)
        left = ttk.Frame(body, width=270)
        right = ttk.Frame(body)
        body.add(left, weight=1)
        body.add(right, weight=4)
        self.kind = tk.StringVar(value="Mechs")
        box = ttk.Combobox(left, textvariable=self.kind, values=["Mechs", "Weapons"], state="readonly")
        box.pack(fill="x", pady=4)
        box.bind("<<ComboboxSelected>>", lambda _e: self.guarded(self.change_kind))
        self.search = tk.StringVar()
        ttk.Label(left, text="Search name or ID").pack(anchor="w")
        ttk.Entry(left, textvariable=self.search).pack(fill="x", pady=4)
        self.search.trace_add("write", lambda *_: self.guarded(self.refresh_list))
        list_frame = ttk.Frame(left)
        list_frame.pack(fill="both", expand=True)
        self.listing = tk.Listbox(list_frame, exportselection=False, width=32)
        scrollbar = ttk.Scrollbar(list_frame, command=self.listing.yview)
        self.listing.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.listing.pack(side="left", fill="both", expand=True)
        self.listing.bind("<<ListboxSelect>>", lambda _e: self.guarded(self.select))
        buttons = ttk.Frame(left)
        buttons.pack(fill="x", pady=6)
        ttk.Button(buttons, text="Duplicate / add", command=lambda: self.guarded(self.duplicate)).pack(side="left")
        ttk.Button(buttons, text="Delete", command=lambda: self.guarded(self.delete)).pack(side="right")
        self.notebook = ttk.Notebook(right)
        self.notebook.pack(fill="both", expand=True)
        self.status = tk.StringVar(value="Ready")
        ttk.Label(window, textvariable=self.status, padding=10, wraplength=1000).pack(fill="x")
        window.protocol("WM_DELETE_WINDOW", self.close)
        window.bind("<Control-s>", lambda _e: self.guarded(self.save))
        window.bind("<Control-z>", lambda _e: self.guarded(self.undo))
        window.bind("<Control-y>", lambda _e: self.guarded(self.redo))

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
        if not self.document or not (self.document.dirty or self.form_dirty):
            return True
        answer = messagebox.askyesnocancel("Unsaved edits", "Save your changes before closing this project?", parent=self.window)
        if answer is None:
            return False
        if answer:
            self.save()
        return True

    def set_document(self, document: ProjectDocument):
        self.document = document
        self.current = None
        self.form_dirty = False
        self.search.set("")
        self.refresh_list()
        self.project_label.configure(text=f"{document.manifest['title']} - {document.root}")
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
        template = self.document.root if self.document else ROOT / "examples/project-demo"
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
        frame = ttk.Frame(self.notebook, padding=12)
        frame.columnconfigure(1, weight=1)
        self.notebook.add(frame, text=name)
        return frame

    def field(self, frame, row, label, path, integer=False, choices=None, readonly=False):
        value = self.item()
        for part in path:
            value = value[part]
        variable = tk.StringVar(value=str(value))
        variable.trace_add("write", lambda *_: self.changed())
        self.variables[tuple(path)] = (variable, integer)
        ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", padx=(0, 14), pady=4)
        control = ttk.Combobox(frame, textvariable=variable, values=choices, state="readonly") if choices is not None else ttk.Entry(frame, textvariable=variable, state="readonly" if readonly else "normal")
        control.grid(row=row, column=1, sticky="ew", pady=4)

    def changed(self):
        self.form_dirty = True
        self.status.set("Unsaved edits. Validate checks the complete project; Save preserves disk files if validation fails.")

    def populate(self):
        for tab in self.notebook.tabs():
            self.notebook.nametowidget(tab).destroy()
        self.variables = {}
        self.form_dirty = False
        if not self.current:
            return
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
            buttons = ttk.Frame(frame)
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
            ttk.Label(general, text="Ranges use CHI map distances. Updated LRMs use the package's LRM rules.\nThe C validator checks supported behavior and ammunition combinations.", wraplength=570).grid(row=11, column=0, columnspan=2, pady=16, sticky="w")

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
            if self.form_dirty:
                # A half-typed/non-numeric field is reversible too. It has
                # not reached the document history or the disk yet.
                self.populate()
                self.status.set("Unapplied form edits undone.")
                return
            self.document.undo()
            self.refresh_list()
            self.status.set("Undo applied.")

    def redo(self):
        if self.document:
            self.apply_form()
            self.document.redo()
            self.refresh_list()
            self.status.set("Redo applied.")

    def save(self):
        if self.document:
            self.apply_form()
            self.status.set(self.document.save())
            self.refresh_list()

    def validate(self):
        if self.document:
            self.apply_form()
            self.status.set(self.document.validate())

    def setup(self):
        dialog = tk.Toplevel(self.window)
        dialog.title("Player setup - explicit local dependencies")
        dialog.transient(self.window)
        values = {key: tk.StringVar(value=value) for key, value in self.settings.items()}
        for row, key in enumerate(["player", "data", "dialogue-data", "combat-data", "world-data"]):
            ttk.Label(dialog, text=key).grid(row=row, column=0, padx=8, pady=6)
            ttk.Entry(dialog, textvariable=values[key], width=65).grid(row=row, column=1, padx=8, pady=6)
            def browse(k=key):
                path = filedialog.askdirectory(parent=dialog) if k == "data" else filedialog.askopenfilename(parent=dialog)
                if path:
                    values[k].set(path)
            ttk.Button(dialog, text="Browse", command=browse).grid(row=row, column=2, padx=8)
        def apply():
            self.settings = {key: value.get() for key, value in values.items()}
            self.state_dir.mkdir(parents=True, exist_ok=True)
            (self.state_dir / "settings.json").write_text(json.dumps(self.settings, indent=2), encoding="utf-8")
            dialog.destroy()
        ttk.Button(dialog, text="Save setup", command=lambda: self.guarded(apply)).grid(row=5, column=1, pady=12)

    def play(self):
        if self.document:
            self.apply_form()
            command = self.document.play_command(self.settings, self.state_dir)
            self.state_dir.mkdir(parents=True, exist_ok=True)
            with (self.state_dir / "player.log").open("a", encoding="utf-8") as log:
                subprocess.Popen(command, cwd=self.state_dir, stdout=log, stderr=log)
            self.status.set("Player launched with a fresh campaign and separate playtest save slots. See player.log for launch diagnostics.")

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
