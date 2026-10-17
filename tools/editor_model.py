"""Roster editor document operations; game semantics belong to btp-project.

Edits are staged in a private package and validated by the same C loader as
the player. Saving replaces only the definition file after validation. The
open snapshot also detects external edits, including changes to maps/assets.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


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
        *[asset["file"] for asset in manifest["assets"]]]))


def encoded(value: dict) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=True) + "\n").encode("ascii")


class ProjectDocument:
    def __init__(self, directory: Path, validator: Path):
        self.root, self.validator = directory.resolve(), validator.resolve()
        run_validator(self.validator, self.root)
        self.manifest = json.loads((self.root / "project.json").read_bytes())
        self.snapshot = {name: child(self.root, name).read_bytes() for name in references(self.manifest)}
        self.content = json.loads(self.snapshot[self.manifest["definitions"]])
        self.saved = copy.deepcopy(self.content)
        self.undo_stack: list[dict] = []
        self.redo_stack: list[dict] = []

    @property
    def dirty(self) -> bool:
        return self.content != self.saved

    def replace(self, content: dict) -> None:
        if content != self.content:
            self.undo_stack.append(copy.deepcopy(self.content))
            self.undo_stack = self.undo_stack[-40:]
            self.redo_stack.clear()
            self.content = copy.deepcopy(content)

    def undo(self) -> None:
        if self.undo_stack:
            self.redo_stack.append(self.content)
            self.content = self.undo_stack.pop()

    def redo(self) -> None:
        if self.redo_stack:
            self.undo_stack.append(self.content)
            self.content = self.redo_stack.pop()

    def unchanged_on_disk(self) -> None:
        for name, original in self.snapshot.items():
            try:
                unchanged = child(self.root, name).read_bytes() == original
            except OSError:
                unchanged = False
            if not unchanged:
                raise EditorError(f"{name} changed outside this editor. Reopen the project before saving; your disk files were preserved.")

    def stage(self, root: Path) -> None:
        for name, data in self.snapshot.items():
            path = child(root, name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(encoded(self.content) if self.dirty and name == self.manifest["definitions"] else data)

    def validate(self) -> str:
        self.unchanged_on_disk()
        with tempfile.TemporaryDirectory(prefix="btp-editor-validate-") as directory:
            self.stage(Path(directory))
            return run_validator(self.validator, Path(directory))

    def save(self) -> str:
        result = self.validate()
        self.unchanged_on_disk()
        if not self.dirty:
            return result  # Preserve original formatting and package digest.
        target = child(self.root, self.manifest["definitions"])
        data = encoded(self.content)
        fd, temporary = tempfile.mkstemp(prefix=".btp-editor-", dir=target.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            self.unchanged_on_disk()
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        self.snapshot[self.manifest["definitions"]] = data
        self.saved = copy.deepcopy(self.content)
        return result

    def duplicate(self, collection: str, index: int) -> str:
        content = copy.deepcopy(self.content)
        values = content[collection]
        original = copy.deepcopy(values[index])
        prefix = self.manifest["package_id"]
        stem = "mech" if collection == "mechs" else "weapon"
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

    def play_command(self, settings: dict, state_dir: Path) -> list[str]:
        self.save()
        required = ["player", "data", "dialogue-data", "combat-data", "world-data"]
        for key in required:
            if not settings.get(key) or not Path(settings[key]).exists():
                raise EditorError(f"Configure an existing {key} path in Player setup.")
        # One save namespace per exact edit. Preview never loads or overwrites
        # a user's normal campaign or a previous content revision.
        digest = hashlib.sha256(b"".join(self.snapshot.values())).hexdigest()[:20]
        work = state_dir / "play" / self.manifest["package_id"] / digest
        work.mkdir(parents=True, exist_ok=True)
        replay = work / "start.actions"
        replay.write_text("", encoding="ascii")
        return [str(Path(settings["player"]).resolve()), "--project", str(self.root),
                *[arg for key in required[1:] for arg in ("--" + key, str(Path(settings[key]).resolve()))],
                "--replay", str(replay.resolve()), "--save-file", str((work / "game.btp").resolve())]


def create_project(template: Path, target: Path, package_id: str, title: str, validator: Path) -> ProjectDocument:
    if target.exists():
        raise EditorError("Choose a new project directory; existing directories are preserved.")
    source = ProjectDocument(template, validator)
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".btp-new-", dir=target.parent) as directory:
        staging = Path(directory) / "package"
        staging.mkdir()
        source.stage(staging)
        manifest = copy.deepcopy(source.manifest)
        manifest.update(package_id=package_id, title=title, content_version="1.0.0")
        content = copy.deepcopy(source.content)
        content.update(package_id=package_id, content_version="1.0.0")
        (staging / "project.json").write_bytes(encoded(manifest))
        child(staging, manifest["definitions"]).write_bytes(encoded(content))
        for name in ["README.md", "SOURCE-README.md", "ART-SOURCE-README.md", "LICENSE.md", "sources.json"]:
            path = child(source.root, name)
            if path.is_file():
                shutil.copyfile(path, staging / name)
        run_validator(validator, staging)
        if target.exists():
            raise EditorError("The target directory appeared while creating the project.")
        staging.rename(target)
    return ProjectDocument(target, validator)
