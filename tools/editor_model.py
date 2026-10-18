"""Roster editor document operations; game semantics belong to btp-project.

Edits are staged in a private package and validated by the same C loader as
the player. Saving replaces only the definition file after validation. The
open snapshot also detects external edits, including changes to maps/assets.
"""
from __future__ import annotations

import copy
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from contextlib import contextmanager


class EditorError(Exception):
    pass


def run_validator(tool: Path, directory: Path) -> str:
    try:
        process = subprocess.run([str(tool.resolve()), "validate", str(directory.resolve())],
                                 capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise EditorError(f"Cannot run the shared validator: {exc}") from exc
    if process.returncode:
        raise EditorError(process.stderr.strip() or process.stdout.strip())
    return process.stdout.strip()


def child(root: Path, relative: str) -> Path:
    # Defense in depth for the file copier, independently of C validation.
    parts = relative.split("/")
    if not parts or any(not p or p in (".", "..") or "\\" in p or ":" in p for p in parts):
        raise EditorError(f"Unsafe project path: {relative}")
    path = root
    for part in parts:
        path = path / part
        if path.is_symlink():
            raise EditorError(f"Symlink is not a package file: {relative}")
    if not path.resolve().is_relative_to(root.resolve()):
        raise EditorError(f"Path leaves project: {relative}")
    return path


def references(manifest: dict) -> list[str]:
    return list(dict.fromkeys(["project.json", manifest["definitions"],
        *([manifest["adventure"]] if "adventure" in manifest else []),
        *([manifest["presentation"]] if "presentation" in manifest else []),
        *([manifest["graphics"]] if "graphics" in manifest else []),
        *[script["file"] for script in manifest.get("scripts", [])],
        *[asset["file"] for asset in manifest["assets"]]]))


def encoded(value: dict) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=True) + "\n").encode("ascii")


AUTHORING_RECEIPTS = 'AUTHORING.json'
METADATA_FILES = ('LIBRARY-SOURCES.json', 'EDITOR.json', AUTHORING_RECEIPTS)


class ProjectDocument:
    def __init__(self, directory: Path, validator: Path, recover=True):
        self.root, self.validator = directory.resolve(), validator.resolve()
        if recover:
            if child(self.root, '.btp-editor-transaction.json').exists():
                from project_lock import project_lock
                with project_lock(self.root): self.recover(self.root)
        elif child(self.root, '.btp-editor-transaction.json').exists():
            raise EditorError('Interrupted save needs recovery; open the project in the editor before inspecting it.')
        run_validator(self.validator, self.root)
        self.manifest = json.loads((self.root / "project.json").read_bytes())
        self.snapshot = {name: child(self.root, name).read_bytes() for name in references(self.manifest)}
        # Attribution travels through history/save/export, without becoming
        # a runtime dependency or part of the game's content fingerprint.
        for name in METADATA_FILES:
            metadata=child(self.root,name)
            if metadata.exists():self.snapshot[name]=metadata.read_bytes()
        self.metadata = {name: data for name, data in self.snapshot.items() if name in METADATA_FILES}
        self.content = json.loads(self.snapshot[self.manifest["definitions"]])
        self.adventure = json.loads(self.snapshot[self.manifest["adventure"]]) if "adventure" in self.manifest else None
        self.art = (json.loads(self.snapshot[self.manifest["graphics"]]) if "graphics" in self.manifest
                    else dict(format="btp-art-v1", schema_version=1, images=[], bindings=[]))
        self.saved = copy.deepcopy(self.content)
        self.saved_adventure = copy.deepcopy(self.adventure)
        self.saved_art = copy.deepcopy(self.art)
        self.saved_manifest = copy.deepcopy(self.manifest)
        self.saved_metadata = copy.deepcopy(self.metadata)
        self.undo_stack: list[dict] = []
        self.redo_stack: list[dict] = []
        self.undo_labels, self.redo_labels = [], []
        self.revision = 0
        self._command_depth = 0
        self._command_label = None

    @contextmanager
    def command(self, label=None):
        """Group one user action, including nested forms, into one undo step.

        No Tk objects or listeners live on the document: worker snapshots and
        recovery can safely copy it. Failed actions restore the in-memory state.
        """
        if self._command_depth:
            yield
            return
        before = (self.content, self.adventure, self.art, self.manifest, self.metadata)
        history = (list(self.undo_stack), list(self.redo_stack), list(self.undo_labels), list(self.redo_labels))
        revision = self.revision
        self._command_depth, self._command_label = 1, label
        try:
            yield
        except Exception:
            self.content, self.adventure, self.art, self.manifest, self.metadata = before
            self.undo_stack, self.redo_stack, self.undo_labels, self.redo_labels = history
            self.revision = revision
            raise
        finally:
            self._command_depth, self._command_label = 0, None

    def edit_label(self, content, adventure, art, manifest, metadata):
        if art != self.art: return 'Edit artwork'
        if content != self.content: return 'Edit unit definitions'
        if adventure != self.adventure:
            for key, label in [('maps','Edit map'), ('world','Edit world'), ('worlds','Edit planet'),
                               ('jigsaws','Edit jigsaw'), ('events','Edit event'), ('people','Edit character'),
                               ('shops','Edit shop'), ('start','Edit starting party')]:
                if (adventure or {}).get(key) != (self.adventure or {}).get(key): return label
            return 'Edit adventure'
        return 'Edit authoring metadata' if metadata != self.metadata else 'Edit package'

    @property
    def dirty(self) -> bool:
        return (self.content != self.saved or self.adventure != self.saved_adventure
                or self.art != self.saved_art or self.manifest != self.saved_manifest or self.metadata != self.saved_metadata)

    def replace(self, content: dict) -> None:
        self.replace_both(content, self.adventure)

    def replace_adventure(self, adventure: dict) -> None:
        self.replace_both(self.content, adventure)

    def replace_both(self, content, adventure):
        self.replace_all(content, adventure, self.art, self.manifest)

    def replace_art(self, art, adventure=None,metadata=None):
        manifest = copy.deepcopy(self.manifest)
        if "graphics" not in manifest:
            name = "graphics.json"
            if name not in self.snapshot and child(self.root, name).exists():
                raise EditorError("graphics.json already exists outside this project's declarations. Rename it or declare it before editing graphics.")
            manifest["graphics"] = name
        self.replace_all(self.content, self.adventure if adventure is None else adventure, art, manifest,metadata)

    def replace_all(self, content, adventure, art, manifest, metadata=None):
        metadata = self.metadata if metadata is None else metadata
        if (content, adventure, art, manifest, metadata) != (self.content, self.adventure, self.art, self.manifest, self.metadata):
            label = self._command_label or self.edit_label(content, adventure, art, manifest, metadata)
            # Only the first replacement in a command records the previous state.
            if self._command_depth != 2:
                self.undo_stack.append(copy.deepcopy((self.content, self.adventure, self.art, self.manifest, self.metadata)))
                self.undo_stack = self.undo_stack[-40:]
                self.undo_labels.append(label); self.undo_labels = self.undo_labels[-40:]
            if self._command_depth: self._command_depth = 2
            self.redo_stack.clear()
            self.redo_labels.clear()
            self.revision += 1
            self.content = copy.deepcopy(content)
            self.adventure = copy.deepcopy(adventure)
            self.art = copy.deepcopy(art)
            self.manifest = copy.deepcopy(manifest)
            self.metadata = copy.deepcopy(metadata)

    def undo(self) -> None:
        if self.undo_stack:
            receipts = self.metadata.get(AUTHORING_RECEIPTS)
            self.redo_labels.append(self.undo_labels.pop() if self.undo_labels else 'Edit')
            self.redo_stack.append((self.content, self.adventure, self.art, self.manifest, self.metadata))
            self.content, self.adventure, self.art, self.manifest, self.metadata = self.undo_stack.pop()
            # Undo reverses the edit, not the record that this request ran.
            # A delayed CLI retry must never resurrect an intentionally undone edit.
            if receipts is not None: self.metadata = dict(self.metadata, **{AUTHORING_RECEIPTS: receipts})
            self.revision += 1

    def redo(self) -> None:
        if self.redo_stack:
            receipts = self.metadata.get(AUTHORING_RECEIPTS)
            self.undo_labels.append(self.redo_labels.pop() if self.redo_labels else 'Edit')
            self.undo_stack.append((self.content, self.adventure, self.art, self.manifest, self.metadata))
            self.content, self.adventure, self.art, self.manifest, self.metadata = self.redo_stack.pop()
            if receipts is not None: self.metadata = dict(self.metadata, **{AUTHORING_RECEIPTS: receipts})
            self.revision += 1

    def files(self) -> dict[str, bytes]:
        files = dict(self.snapshot)
        if self.content != self.saved:
            files[self.manifest["definitions"]] = encoded(self.content)
        if self.adventure != self.saved_adventure:
            files[self.manifest["adventure"]] = encoded(self.adventure)
        if "graphics" in self.manifest and (self.art != self.saved_art or self.manifest["graphics"] not in files):
            files[self.manifest["graphics"]] = encoded(self.art)
        if self.manifest != self.saved_manifest:
            files["project.json"] = encoded(self.manifest)
        if 'LIBRARY-SOURCES.json' in files and 'LIBRARY-SOURCES.json' not in self.metadata:
            files['LIBRARY-SOURCES.json'] = encoded([])
        if 'EDITOR.json' in files and 'EDITOR.json' not in self.metadata:
            files['EDITOR.json'] = encoded({})
        files.update(self.metadata)
        return files

    def unchanged_on_disk(self) -> None:
        for name in METADATA_FILES:
            if name not in self.snapshot and child(self.root, name).exists():
                raise EditorError(f'{name} appeared outside this editor. Reopen before saving; your disk file was preserved.')
        for name, original in self.snapshot.items():
            try:
                unchanged = child(self.root, name).read_bytes() == original
            except OSError:
                unchanged = False
            if not unchanged:
                raise EditorError(f"{name} changed outside this editor. Reopen the project before saving; your disk files were preserved.")
        for name in self.files().keys() - self.snapshot.keys():
            if child(self.root, name).exists():
                raise EditorError(f"{name} appeared outside this editor. Reopen before saving; your disk file was preserved.")

    def stage(self, root: Path) -> None:
        for name, data in self.files().items():
            path = child(root, name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)

    @staticmethod
    def atomic_file(target: Path, data: bytes):
        fd, temporary = tempfile.mkstemp(prefix=".btp-editor-", dir=target.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    @staticmethod
    def recover(root: Path):
        journal = child(root, ".btp-editor-transaction.json")
        if not journal.exists():
            return
        try:
            entries = json.loads(journal.read_bytes())
            if not isinstance(entries, list) or not 1 <= len(entries) <= 128:
                raise ValueError("Invalid transaction")
            prepared = []
            for entry in entries:
                path = child(root, entry["file"])
                old = base64.b64decode(entry["old"], validate=True) if entry["old"] is not None else None
                current = path.read_bytes() if path.exists() else None
                if current != old and (current is None or hashlib.sha256(current).hexdigest() != entry["new_sha256"]):
                    raise EditorError("An interrupted save also has external edits. Files were preserved; restore or review .btp-editor-transaction.json before reopening.")
                prepared.append((path, old))
            # A crash leaves either old or new complete file snapshots. Roll
            # back all of them before the shared validator reads the package.
            for path, old in prepared:
                if old is None:
                    if path.exists(): path.unlink()
                else: ProjectDocument.atomic_file(path, old)
            journal.unlink()
        except (ValueError, KeyError, TypeError) as exc:
            raise EditorError("Cannot recover the editor's interrupted save journal; disk files were preserved.") from exc

    def validate(self) -> str:
        self.unchanged_on_disk()
        with tempfile.TemporaryDirectory(prefix="btp-editor-validate-") as directory:
            self.stage(Path(directory))
            return run_validator(self.validator, Path(directory))

    def save(self) -> str:
        from project_lock import project_lock
        with project_lock(self.root):
            return self._save_locked()

    def _save_locked(self) -> str:
        result = self.validate()
        self.unchanged_on_disk()
        if not self.dirty:
            return result  # Preserve original formatting and package digest.
        changed = {name: data for name, data in self.files().items() if data != self.snapshot.get(name)}
        journal = child(self.root, ".btp-editor-transaction.json")
        transaction = [{"file": name, "old": base64.b64encode(self.snapshot[name]).decode("ascii") if name in self.snapshot else None,
                        "new_sha256": hashlib.sha256(data).hexdigest()} for name, data in changed.items()]
        # Validate the entire candidate first. A durable rollback journal
        # protects a save that updates both definitions and adventure files.
        with journal.open("xb") as stream:
            stream.write(encoded(transaction))
            stream.flush()
            os.fsync(stream.fileno())
        try:
            self.unchanged_on_disk()
            for name, data in changed.items():
                path = child(self.root, name)
                path.parent.mkdir(parents=True, exist_ok=True)
                self.atomic_file(path, data)
        except Exception:
            self.recover(self.root)
            raise
        journal.unlink()
        self.snapshot.update(changed)
        self.saved = copy.deepcopy(self.content)
        self.saved_adventure = copy.deepcopy(self.adventure)
        self.saved_art = copy.deepcopy(self.art)
        self.saved_manifest = copy.deepcopy(self.manifest)
        self.saved_metadata = copy.deepcopy(self.metadata)
        return result

    def duplicate(self, collection: str, index: int) -> str:
        content = copy.deepcopy(self.content)
        values = content[collection]
        original = copy.deepcopy(values[index])
        prefix = self.manifest["package_id"]
        stem = {"mechs":"mech","weapons":"weapon","equipment":"equipment"}[collection]
        existing = {item["id"] for item in values}
        serial = 1
        while f"{prefix}:{stem}-{serial}" in existing:
            serial += 1
        original["id"] = f"{prefix}:{stem}-{serial}"
        original["name"] = original["name"][:90] + " copy"
        label_limit = 15 if collection == "mechs" else 11
        original["label"] = original["label"][:label_limit - 5] + " Copy"
        values.append(original)
        self.replace(content)
        return original["id"]

    def play_command(self, settings: dict, state_dir: Path, here=None) -> list[str]:
        self.save()
        required = ["player"] if self.manifest["requires"] == "none" else ["player", "data", "dialogue-data", "combat-data", "world-data"]
        for key in required:
            if not settings.get(key) or not Path(settings[key]).exists():
                raise EditorError(f"Configure an existing {key} path in Player setup.")
        # One save namespace per exact edit. Preview never loads or overwrites
        # a user's normal campaign or a previous content revision.
        digest = hashlib.sha256(b"".join(self.snapshot[name] for name in references(self.manifest))).hexdigest()[:20]
        work = state_dir / "play" / self.manifest["package_id"] / digest
        work.mkdir(parents=True, exist_ok=True)
        replay = work / "start.actions"
        replay.write_text("", encoding="ascii")
        return [str(Path(settings["player"]).resolve()), "--project", str(self.root),
                *[arg for key in required[1:] for arg in ("--" + key, str(Path(settings[key]).resolve()))],
                *(["--play-here", *map(str, here)] if here else []),
                "--replay", str(replay.resolve()), "--save-file", str((work / "game.btp").resolve())]

    def export(self, target: Path):
        self.validate()
        if target.exists():
            raise EditorError("Export requires a new directory; existing files are preserved.")
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".btp-export-", dir=target.parent) as directory:
            staging = Path(directory) / "package"
            staging.mkdir()
            self.stage(staging)
            for name in ["README.md", "LICENSE.md", "SOURCE-README.md", "ART-SOURCE-README.md", "VEHICLE-SOURCE-README.md", "sources.json", "CREDITS.md"]:
                source = child(self.root, name)
                if source.is_file():
                    shutil.copyfile(source, staging / name)
            run_validator(self.validator, staging)
            if target.exists():
                raise EditorError("Export directory appeared during validation.")
            staging.rename(target)


def create_project(template: Path, target: Path, package_id: str, title: str, validator: Path) -> ProjectDocument:
    if target.exists():
        raise EditorError("Choose a new project directory; existing directories are preserved.")
    source = ProjectDocument(template, validator, recover=False)
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".btp-new-", dir=target.parent) as directory:
        staging = Path(directory) / "package"
        staging.mkdir()
        source.stage(staging)
        # A new package has its own request identity space. Export of the same
        # package retains receipts, but creation from a template starts fresh.
        if (staging / AUTHORING_RECEIPTS).exists(): (staging / AUTHORING_RECEIPTS).unlink()
        manifest = copy.deepcopy(source.manifest)
        manifest.update(package_id=package_id, title=title, content_version="1.0.0")
        content = copy.deepcopy(source.content)
        content.update(package_id=package_id, content_version="1.0.0")
        (staging / "project.json").write_bytes(encoded(manifest))
        child(staging, manifest["definitions"]).write_bytes(encoded(content))
        for name in ["README.md", "SOURCE-README.md", "ART-SOURCE-README.md", "VEHICLE-SOURCE-README.md", "LICENSE.md", "sources.json", "CREDITS.md"]:
            path = child(source.root, name)
            if path.is_file():
                shutil.copyfile(path, staging / name)
        run_validator(validator, staging)
        if target.exists():
            raise EditorError("The target directory appeared while creating the project.")
        staging.rename(target)
    return ProjectDocument(target, validator)
