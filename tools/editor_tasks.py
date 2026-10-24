"""Bounded editor jobs; workers only receive detached data, never Tk objects."""
from __future__ import annotations
import copy
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import hashlib
import gc
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import time
import traceback
from editor_model import EditorError,ProjectDocument,encoded,references,needs_original
from editor_session import report,scope_of,guard,clear_problems


@dataclass
class Job:
    label: str
    owner: object
    future: object
    done: object
    failed: object
    cancelled: object
    cancellable: bool
    started: float


class Tasks:
    def __init__(self,workspace):
        self.workspace=workspace;self.pool=ThreadPoolExecutor(max_workers=2,thread_name_prefix='bck-work')
        self.jobs=[];self.timer=None;self.closed=False
        # Tk variables in closed forms can belong to reference cycles. Python's
        # automatic collector otherwise finalizes them on whichever worker
        # happens to allocate next, calling Tcl from the wrong thread. During
        # this GUI process we collect cycles explicitly on the GUI thread.
        gc.disable();self.last_collection=0

    def collect_gui_cycles(self):
        if time.monotonic()-self.last_collection>=2:
            self.last_collection=time.monotonic();gc.collect()

    def submit(self,label,owner,work,done=lambda _:None,failed=None,cancellable=True,quiet=False,dispose=None):
        if self.closed:raise EditorError('The workspace is closing.')
        if len(self.jobs)>=8:raise EditorError('Eight tasks are already queued. Wait for one to finish before starting another.')
        cancel=threading.Event()
        def run():
            if cancel.is_set():return None
            return work(cancel)
        job=Job(label,owner,self.pool.submit(run),done,failed,cancel,cancellable,time.monotonic())
        job.quiet=quiet;job.dispose=dispose;self.jobs.append(job)
        self.workspace.update_busy()
        self.workspace.update_commands()
        if not quiet:self.workspace.status.set(label+'…');self.workspace.log(label+' started.')
        if self.timer is None:self.timer=self.workspace.window.after(40,self.poll)
        return job

    def poll(self):
        self.timer=None
        for job in list(self.jobs):
            if not job.future.done():continue
            self.jobs.remove(job)
            alive=job.owner.window.winfo_exists()
            try:
                value=job.future.result()
                if job.cancelled.is_set() and job.cancellable:
                    if job.dispose:job.dispose(value)
                    if alive and job.failed:job.failed(EditorError(job.label+' cancelled.'))
                elif alive:job.done(value)
                elif job.dispose:job.dispose(value)
                if not job.quiet:self.workspace.log(f'{job.label} finished in {time.monotonic()-job.started:.2f}s.')
            except Exception as error:
                if alive:
                    if job.failed:guard(job.owner,lambda:job.failed(error))
                    else:report(job.owner,error,traceback.format_exc())
            if alive and hasattr(job.owner,'status') and not job.quiet:self.workspace.status.set(job.owner.status.get())
        self.workspace.update_busy()
        self.workspace.update_commands()
        if self.jobs and not self.closed:self.timer=self.workspace.window.after(40,self.poll)

    def cancel(self,scope=None):
        for job in self.jobs:
            if job.cancellable and (scope is None or scope_of(job.owner) is scope):job.cancelled.set()
        self.workspace.status.set('Cancellation requested. A durable save already in progress will finish safely.')

    def busy(self,scope):return any(scope_of(j.owner) is scope and not j.cancellable for j in self.jobs)

    def shutdown(self):
        self.closed=True
        if self.timer:self.workspace.window.after_cancel(self.timer);self.timer=None
        for job in self.jobs:
            if job.cancellable:job.cancelled.set()
        self.pool.shutdown(wait=False,cancel_futures=True)


def signature(scope):
    return (id(scope.document),scope.document.revision,
            [(id(d),copy.deepcopy(d.capture())) for d in scope.live() if d.pending()])


def snapshot(scope):
    """Validate the combined candidate without consuming forms or invalid text."""
    if not scope.document:raise EditorError('Open a project first.')
    # With no fields to apply, taking an isolated copy cannot mutate the live
    # document. Avoid a second full rollback copy in that common path. Dirty
    # drafts retain the ordinary preview transaction and all rollback checks.
    if not any(d.pending() for d in scope.live()):return scope.document.worker_copy()
    return scope.transact(lambda:scope.document.worker_copy(),preview=True)


def adopt_saved(live,saved):
    # Only advance the disk baseline. Edits made during the durable write stay
    # in the live document and are still marked unsaved.
    for name in ('snapshot','source','saved','saved_adventure','saved_art','saved_manifest','saved_metadata'):
        setattr(live,name,copy.deepcopy(getattr(saved,name)))


def save(workspace,scope,finished=None):
    if getattr(scope,'saving',False):
        workspace.status.set('This scope is already being saved.')
        if finished:finished(False)
        return
    if not scope.document:
        if finished:finished(True)
        return
    candidate=snapshot(scope);stamp=signature(scope);scope.saving=True;owner=scope.owner;phase={'commit':False}
    def fail(error):
        scope.saving=False
        if not phase['commit'] and stamp!=signature(scope):owner.status.set('Earlier draft validation failed after you changed it. Save again to validate current edits.')
        else:report(owner,error,category='save' if phase['commit'] else 'validation')
        if finished:finished(False)
    def validated(_):
        if stamp!=signature(scope):
            scope.saving=False
            owner.status.set('Edits changed during validation. Save again to include the current work; no files were written.')
            if finished:finished(False)
            return
        clear_problems(scope,'validation')
        # All fields were checked together. Now consume exactly that draft and
        # let the worker finish the journalled write, without blocking the UI.
        scope.apply_pending()
        phase['commit']=True
        candidate=scope.document.worker_copy();context=getattr(owner,'library_context',None)
        def commit(cancel):
            if context:
                replacement=tempfile.TemporaryDirectory(prefix='unit-edit-',dir=owner.state_dir)
                try:
                    candidate.stage(Path(replacement.name));doc=ProjectDocument(Path(replacement.name),candidate.validator)
                    bundle=context.browser.library.export_unit(doc,context.bundle['definition'],context.bundle['kind'],expected=copy.deepcopy(context.bundle))
                    return doc,bundle,replacement
                except Exception:replacement.cleanup();raise
            candidate.save();return candidate,None,None
        def committed(result):
            saved,bundle,replacement=result;live=scope.document
            if context:
                old=context.temp;context.temp=replacement;context.bundle=bundle
                live.root=saved.root;old.cleanup();context.browser.refresh(bundle['entry_id'])
            adopt_saved(live,saved);scope.saving=False
            scope.workspace.recovery.write(scope,background=True)
            owner.status.set('Saved. Newer edits remain unsaved.' if scope.dirty() else 'Saved '+live.manifest['title']+'.')
            if finished:finished(True)
        workspace.tasks.submit('Saving '+candidate.manifest['title'],owner,commit,committed,fail,cancellable=False)
    try:workspace.tasks.submit('Validating before save',owner,lambda cancel:candidate.validate(),validated,fail)
    except Exception:
        scope.saving=False
        raise


def validate(workspace,scope):
    candidate=snapshot(scope);stamp=signature(scope)
    def done(result):
        if stamp!=signature(scope):scope.owner.status.set('Validation finished for an earlier edit. Validate again to check current changes.')
        else:
            clear_problems(scope,'validation');scope.owner.status.set(result);workspace.log(result)
    def failed(error):
        if stamp!=signature(scope):scope.owner.status.set('Earlier draft validation failed. Validate again to check the current changes.')
        else:report(scope.owner,error,category='validation')
    workspace.tasks.submit('Validating project',scope.owner,lambda cancel:candidate.validate(),done,failed)


def export(workspace,scope,target):
    candidate=snapshot(scope);revision=candidate.revision
    workspace.tasks.submit('Exporting game',scope.owner,lambda cancel:candidate.export(target),
        lambda _:scope.owner.status.set(f'Exported validated revision {revision} to {target}.'),cancellable=False)


class PlaySession:
    def __init__(self,workspace):
        self.workspace=workspace;self.process=None;self.timer=None;self.preparing=False;self.preparation=None
        self.stopping=False;self.scope=None
    def start(self,scope,here=None,checkpoint=None):
        if self.preparing:raise EditorError('A test is already being prepared.')
        if self.process and self.process.poll() is None:raise EditorError('Stop the running test before starting another.')
        # Retire an exited process before replacing its timer/diagnostics.
        if self.process:self.poll()
        candidate=snapshot(scope);stamp=signature(scope);settings=dict(scope.owner.settings);revision=candidate.revision
        state_dir=Path(scope.owner.state_dir).resolve();checkpoint=Path(checkpoint).resolve() if checkpoint else None;launching=False
        self.preparing=True;self.scope=scope;self.stopping=False
        def discard(result):
            # Only our unlaunched temporary snapshot is disposable. Completed
            # playtest logs and all project/game saves keep their own lifetime.
            if result:shutil.rmtree(result[1],ignore_errors=True)
        def prepare(cancel):
            from app_runtime import prepare_original
            if needs_original(candidate.manifest):prepare_original(settings)
            if cancel.is_set():return None
            root=state_dir/'play-snapshots';root.mkdir(parents=True,exist_ok=True)
            folder=Path(tempfile.mkdtemp(prefix='run-',dir=root))
            try:
                if checkpoint:
                    from playtest_workbench import checkpoint_save
                    save=checkpoint_save(checkpoint)
                    source=ProjectDocument(save.parent/'game',candidate.validator)
                    source.export(folder/'game')
                else:candidate.export(folder/'game')
                document=ProjectDocument(folder/'game',candidate.validator)
                from save_catalogue import retain_revision
                retain_revision(document,state_dir)
                # Ordinary Play retains slots for the same exact revision.
                # Play here/checkpoint experiments keep private per-run saves.
                persistent=not checkpoint and here is None
                command=document.play_command(settings,state_dir if persistent else folder,here=here)
                from app_runtime import restore_playtest_saves,project_slot_name
                save_directory=Path(command[command.index('--save-file')+1]).parent
                if persistent:restore_playtest_saves(document,state_dir,save_directory)
                save_slot=save_directory/project_slot_name(document)
                (folder/'PLAY.json').write_bytes(encoded(dict(format='btp-play-session-v1',
                    saves='persistent-revision' if persistent else 'isolated-test',save_file=str(save_slot))))
                if checkpoint:command+=['--load',str(save)]
                # Native BLD observations have their own source identities;
                # authored event counts cannot stand in for campaign coverage.
                native=document.manifest.get('requires')=='chi-local-dos-1.03'
                command+=['--bld-trace' if native else '--event-trace',str(folder/('bld.jsonl' if native else 'events.jsonl'))]
                return command,folder,save_slot
            except Exception:
                discard((None,folder));raise
        def ready(result):
            nonlocal launching
            self.preparing=False;self.preparation=None
            if result is None:return
            if not checkpoint and stamp!=signature(scope):discard(result);return retry()
            command,folder,save_slot=result;self.save_slot=save_slot
            clear_problems(scope,'validation')
            launching=True
            with (folder/'player.log').open('w',encoding='utf-8') as log:self.process=subprocess.Popen(command,cwd=folder,stdout=log,stderr=log)
            clear_problems(scope,'play')
            self.folder=folder;scope.owner.status.set(f'Playing snapshot revision {revision}. Saved games: {save_slot.parent}. Logs: {folder}')
            self.workspace.log(scope.owner.status.get());self.timer=self.workspace.window.after(150,self.poll)
        def failed(error):
            cancelled=self.preparation and self.preparation.cancelled.is_set()
            self.preparing=False;self.preparation=None
            if cancelled:scope.owner.status.set('Playtest preparation cancelled.')
            elif not checkpoint and stamp!=signature(scope):retry()
            else:report(scope.owner,error,category='play' if launching else 'validation')
        def retry():
            # A slow check can finish after a blocked entrance was corrected.
            # Rebuild from the current draft rather than launching/reporting
            # the obsolete snapshot. The newest draft still needs validation.
            if id(scope.document)!=stamp[0]:
                scope.owner.status.set('The project changed during Play preparation. Click Play to test the current project.');return
            self.workspace.log('Edits changed during Play preparation; checking the current draft.')
            self.start(scope,here=here,checkpoint=checkpoint)
        try:self.preparation=self.workspace.tasks.submit('Preparing playtest snapshot',scope.owner,prepare,ready,failed,dispose=discard)
        except Exception:
            self.preparing=False
            raise
    def poll(self):
        if self.timer:self.workspace.window.after_cancel(self.timer)
        self.timer=None
        if not self.process:return
        code=self.process.poll()
        if code is None:self.timer=self.workspace.window.after(150,self.poll);return
        self.workspace.log(f'Playtest exited ({code}). Logs and execution trace: {self.folder}')
        self.process=None
        if code and not self.stopping:
            path=self.folder/'player.log'
            with path.open('rb') as log:
                log.seek(0,2);log.seek(max(0,log.tell()-4000));detail=log.read().decode('utf-8',errors='replace').strip()
            report(self.scope.owner,EditorError(f'Playtest failed (exit {code}).\n{detail or "The player supplied no diagnostic."}\nLog: {path}'),category='play')
        else:self.workspace.status.set('Playtest stopped.' if self.stopping else 'Playtest ended. Your editor work is ready.')
        self.workspace.window.lift()
    def start_saved(self,scope,command):
        """Continue a validated retained revision through the usual Stop/log UI."""
        if self.preparing or self.process is not None:raise EditorError('Stop the running test before continuing a save.')
        state_dir=Path(scope.owner.state_dir).resolve();root=state_dir/'play-snapshots';root.mkdir(parents=True,exist_ok=True)
        self.folder=Path(tempfile.mkdtemp(prefix='run-',dir=root));self.scope=scope;self.stopping=False
        self.save_slot=Path(command[command.index('--load')+1])
        with (self.folder/'player.log').open('w',encoding='utf-8') as log:
            self.process=subprocess.Popen(command,cwd=self.folder,stdout=log,stderr=log)
        self.workspace.log('Continued saved game: '+str(self.save_slot))
        self.timer=self.workspace.window.after(150,self.poll)
    def stop(self):
        if self.preparing:
            # Other validations/imports may share the pool. Stop belongs only
            # to this play session, even before its SDL process has started.
            if self.preparation:self.preparation.cancelled.set()
            self.workspace.status.set('Cancelling playtest preparation…');return
        if self.process and self.process.poll() is None:
            self.stopping=True;self.process.terminate();self.workspace.status.set('Stopping this editor’s playtest…')
        else:self.workspace.status.set('No playtest is running.')
    def shutdown(self):
        if self.timer:self.workspace.window.after_cancel(self.timer);self.timer=None
        if self.process and self.process.poll() is None:self.process.terminate()
