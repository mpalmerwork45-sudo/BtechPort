"""Command files enter the visible editor through normal drafts and history.

This is an explicit file exchange, not a live remote control session. Workers
validate detached snapshots; the GUI thread rejects results if the author kept
editing while validation ran. No model or network access is involved.
"""
from pathlib import Path
from tkinter import filedialog
from authoring_contract import AuthoringError,read_json
from authoring_service import apply_batch,revision
from authoring_inspect import summary
from editor_model import ProjectDocument,encoded
from editor_tasks import snapshot,signature
from editor_history import refresh_scope


def apply_file(workspace,path=None):
    scope=workspace.app._editor_scope
    if path is None:
        path=filedialog.askopenfilename(parent=workspace.window,title='Apply authoring command file',filetypes=[('JSON commands','*.json')])
    if not path:return
    path=Path(path);request=read_json(path);candidate=snapshot(scope);stamp=signature(scope)
    def work(cancel):
        result=apply_batch(candidate,request,base_dir=path.parent,cancelled=cancel.is_set)
        return result
    def done(result):
        if signature(scope)!=stamp:
            raise AuthoringError('revision.conflict','The editor changed while commands were checked. Export a fresh summary and rebase the batch.')
        if result['status']=='already_applied':
            workspace.status.set('This command file was already applied.');return
        def publish():
            scope.document.replace_all(candidate.content,candidate.adventure,candidate.art,candidate.manifest,candidate.metadata)
        with scope.document.command(request['label']):scope.transact(publish)
        refresh_scope(workspace,scope);scope.seen_revision=(id(scope.document),scope.document.revision)
        workspace.status.set(f"Applied {len(request['operations'])} commands. Undo reverses this batch; Save publishes it.")
        workspace.log(workspace.status.get())
    return workspace.tasks.submit('Check authoring commands',scope.owner,work,done)


def export_summary(workspace,path=None):
    scope=workspace.app._editor_scope
    if path is None:
        path=filedialog.asksaveasfilename(parent=workspace.window,title='Export authoring summary',defaultextension='.json',filetypes=[('JSON summary','*.json')])
    if not path:return
    path=Path(path).resolve()
    if path.is_relative_to(scope.document.root):raise AuthoringError('output.invalid','Save the summary outside your game project.')
    candidate=snapshot(scope)
    def done(result):
        ProjectDocument.atomic_file(path,encoded(result))
        workspace.status.set('Exported authoring summary, including current editor drafts.')
    return workspace.tasks.submit('Inspect authoring snapshot',scope.owner,lambda cancel:summary(candidate,candidate.validator),done)


def check_mission(workspace):
    from authoring_analysis import analyze
    from editor_session import clear_problems
    import json,os
    scope=workspace.active_scope();candidate=snapshot(scope);stamp=signature(scope)
    settings=dict(scope.owner.settings)
    analyzer=Path(__file__).resolve().parents[1]/'build'/('btp-author-analyze.exe' if os.name=='nt' else 'btp-author-analyze')
    def done(result):
        if signature(scope)!=stamp:raise AuthoringError('revision.conflict','The document changed during mission checks; run Check mission again.')
        clear_problems(scope)
        for diagnostic in result['diagnostics']:
            problem=dict(diagnostic,owner=scope.owner,field=None,details=json.dumps(diagnostic,indent=2))
            identity=diagnostic.get('object_id');location=diagnostic.get('location')
            if location and location.get('map'):
                def navigate(where=location):
                    workspace.open_map(where['map']);maps=workspace.app.map_editor;maps.cursor=tuple(where['at']);maps.draw()
                problem['navigate']=navigate
            elif identity and any(e['id']==identity for e in (scope.document.adventure or {}).get('events',[])):
                problem['navigate']=lambda identity=identity:workspace.open_event(identity)
            workspace.problem(scope,problem)
        message=f"Mission checks: {sum(p['severity']=='error' for p in result['diagnostics'])} errors, {sum(p['severity']=='warning' for p in result['diagnostics'])} warnings."
        scope.owner.status.set(message);workspace.status.set(message);workspace.log(message+' '+result['coverage'])
    return workspace.tasks.submit('Check mission',scope.owner,lambda cancel:analyze(candidate,analyzer,settings),done)
