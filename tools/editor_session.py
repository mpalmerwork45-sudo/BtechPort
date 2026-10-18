"""Editor scopes, visible diagnostics and recoverable in-memory drafts.

The scope is deliberately independent of a particular window layout. A dialog
and a future notebook view use the same save/close transaction boundaries.
"""
from __future__ import annotations
import copy
from dataclasses import dataclass
import traceback
from contextlib import nullcontext
from tkinter import messagebox
from editor_model import EditorError


class FieldError(EditorError):
    def __init__(self, message, field=None):
        super().__init__(message)
        self.field = field


def scope_of(owner):
    seen = set()
    while owner is not None and id(owner) not in seen:
        seen.add(id(owner))
        scope = getattr(owner, '_editor_scope', None)
        if scope is not None:
            return scope
        owner = getattr(owner, 'owner', None) or getattr(owner, 'parent', None)
    return None


def visible_parent(owner):
    """A modal child owns its errors; a withdrawn ancestor never does."""
    window = owner.window if hasattr(owner, 'window') else owner
    root = window.winfo_toplevel()
    grabbed = root.grab_current()
    if grabbed is not None and grabbed.winfo_exists():
        return grabbed.winfo_toplevel()
    if root.state() != 'withdrawn':
        return root
    focused = root.focus_get()
    return focused.winfo_toplevel() if focused is not None else root._root()


def report(owner, error, details=''):
    scope = scope_of(owner)
    if scope is not None and scope.failure_owner is not None:
        owner, scope.failure_owner = scope.failure_owner, None
    if hasattr(owner, 'status'):
        owner.status.set(str(error))
    if scope is not None:
        scope.problems.append(dict(message=str(error), details=details,
                                   owner=owner, field=getattr(error, 'field', None)))
        if scope.on_problem:
            scope.on_problem(scope.problems[-1])
    if hasattr(owner, 'show_error'):
        owner.show_error(error)
        return
    window = visible_parent(owner)
    focus, grab = window.focus_get(), window.grab_current()
    try:
        messagebox.showerror('BattleTech Construction Kit', str(error), parent=window)
    finally:
        # Native dialogs can release an existing local modal grab.
        if grab is not None and grab.winfo_exists():
            grab.grab_set()
        if focus is not None and focus.winfo_exists():
            focus.focus_set()


def guard(owner, operation, publish=True):
    try:
        scope = scope_of(owner)
        document = scope.document if scope else None
        with document.command() if document else nullcontext():
            result = operation()
            # A completed art command publishes to the shared history. Open
            # forms and unfinished pointer gestures remain recoverable drafts.
            if publish:publish_art(owner)
            return result
    except Exception as error:
        report(owner, error, traceback.format_exc())
        return None


@dataclass
class Draft:
    view: object
    pending: object
    apply: object
    capture: object
    restore: object
    accept: object
    priority: int = 0

    def alive(self):
        return bool(self.view.window.winfo_exists())


class EditorScope:
    def __init__(self, owner):
        self.owner = owner
        self.drafts = []
        self.problems = []
        self.on_problem = None
        self.failure_owner = None
        self.collecting = False
        self.applying = set()

    @property
    def document(self):
        return self.owner.document

    def register(self, view, pending, apply, capture, restore, accept=lambda: None, priority=0):
        draft = Draft(view, pending, apply, capture, restore, accept, priority)
        self.drafts.append(draft)
        return draft

    def live(self):
        self.drafts = [d for d in self.drafts if d.alive()]
        return list(self.drafts)

    def dirty(self):
        return bool(self.document and self.document.dirty) or any(d.pending() for d in self.live())

    def transact(self, operation, only=None, subset=None, preview=False):
        """A failed save restores document AND widget drafts, including bad text.

        Apply callbacks must not destroy their view. Accept callbacks run only
        after all drafts and the requested validation/save have succeeded.
        """
        if self.collecting:
            if only and id(only) not in self.applying:
                self.applying.add(id(only))
                try: only.apply()
                finally: self.applying.remove(id(only))
                # The outer transaction accepts every changed art ancestor.
                if only not in self.applied: self.applied.append(only)
            return operation()
        document = self.document
        before = copy.deepcopy(document.__dict__) if document else None
        drafts = self.live()
        states = [(d, copy.deepcopy(d.capture())) for d in drafts]
        selected = [only] if only else sorted(drafts if subset is None else subset, key=lambda d: (d.priority, drafts.index(d)), reverse=True)
        applied = self.applied = []
        self.collecting = True
        try:
            with document.command('Apply edits') if document else nullcontext():
                for draft in selected:
                    if draft.alive() and (only or draft.pending()):
                        self.failure_owner = draft.view
                        self.applying.add(id(draft))
                        try: draft.apply()
                        finally: self.applying.remove(id(draft))
                        if draft not in applied: applied.append(draft)
                        publish_art(getattr(draft.view,'owner',None), nested=True)
                self.failure_owner = self.owner
                result = operation()
        except Exception:
            if document is not None:
                document.__dict__.clear()
                document.__dict__.update(before)
            for draft, state in states:
                if draft.alive():
                    draft.restore(state)
            raise
        else:
            self.failure_owner = None
            if preview:
                if document is not None:
                    document.__dict__.clear();document.__dict__.update(before)
                for draft,state in states:
                    if draft.alive():draft.restore(state)
                return result
            for draft in applied:
                if draft.alive():
                    draft.accept()
            return result
        finally:
            self.collecting = False

    def confirm_close(self, window=None):
        """Do not collect drafts before asking: Cancel must preserve invalid text."""
        if not self.dirty():
            return True
        answer = messagebox.askyesnocancel('Unsaved edits',
            'Save changes, including unfinished artwork and forms, before closing?',
            parent=visible_parent(window or self.owner))
        if answer is None:
            return False
        if answer:
            self.owner.save()
        return True

    def confirm_view(self,view):
        """Closing a tab applies/discards its drafts, without saving the disk."""
        window=getattr(view,'window',view)
        def belongs(draft):
            child=draft.view.window
            while child is not None:
                if child is window:return True
                child=getattr(child,'master',None)
            return False
        pending=[d for d in self.live() if belongs(d) and d.pending()]
        if not pending:return True
        answer=messagebox.askyesnocancel('Unfinished edits','Apply this tab\'s unfinished edits before closing?',parent=visible_parent(window))
        if answer is None:return False
        if answer:self.transact(lambda:None,subset=pending)
        return True


def register(view, **callbacks):
    scope = scope_of(view)
    return scope.register(view, **callbacks) if scope else None


def apply_draft(view):
    scope = scope_of(view)
    if scope and getattr(view, 'draft', None):
        return scope.transact(lambda: None, only=view.draft)
    view.apply_pending()
    view.accept_draft()


def publish_art(view, nested=False):
    """Only embedded art tools publish at gesture/command boundaries."""
    if view is None or not getattr(view,'shared_art',False): return
    scope=scope_of(view)
    draft=getattr(view,'draft',None)
    if (scope and draft and draft.alive() and hasattr(scope,'workspace')
            and (not scope.collecting or nested) and getattr(view,'before',None) is None
            and draft.pending()):
        apply_draft(view)
