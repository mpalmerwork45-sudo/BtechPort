"""Portable local authoring inbox: JSON files, no network or executable commands.

The editor owns the session and its GUI-thread document. Clients submit bounded
snapshot/proposal jobs, then read retained results. Per-job files avoid shared
queue rewrites; an atomic command file is the publication point.
"""
import hashlib
import os
from pathlib import Path
import re
import time
import uuid

from authoring_contract import AuthoringError,read_json,check_batch
from editor_model import ProjectDocument,encoded,child
from authoring_review import freeze_imports,import_paths
from authoring_service import revision

FORMAT='btp-author-session-v1'
JOB_ID=re.compile(r'^[a-zA-Z0-9._-]{1,80}$')


def write(path,value):
    ProjectDocument.atomic_file(Path(path),encoded(value))


def info(folder):
    value=read_json(Path(folder)/'session.json')
    if value.get('format')!=FORMAT:raise AuthoringError('session.invalid','Select a Construction Kit authoring session directory.')
    result=dict(value)
    # A heartbeat is only liveness information; it never grants application or
    # makes a stale revision acceptable after an editor restart.
    result['connected']=value.get('status')=='active' and time.time()-value.get('heartbeat',0)<15
    if value.get('status')=='active' and not result['connected']:result['status']='interrupted'
    return result


def create(document,folder,*,brief='',constraints=(),allowed_scope=('*',),policy='review',scope_kind='project'):
    folder=Path(folder).resolve()
    if folder.is_relative_to(document.root):raise AuthoringError('output.invalid','A local session belongs outside the game directory.')
    if folder.exists():raise AuthoringError('output.exists','Choose a new session directory.')
    if policy not in ('review','apply_within_scope'):raise AuthoringError('session.invalid','Choose review or apply_within_scope.')
    if len(brief)>4096 or len(constraints)>32 or any(len(s)>1024 for s in constraints):raise AuthoringError('query.bounds','Session brief or constraints exceed their bounds.')
    if not 1<=len(allowed_scope)<=64 or any(not s or len(s)>1024 for s in allowed_scope):raise AuthoringError('scope.denied','Declare at least one bounded write scope.')
    folder.mkdir(parents=True,mode=0o700);(folder/'jobs').mkdir(mode=0o700)
    value=dict(format=FORMAT,id=uuid.uuid4().hex,status='active',pid=os.getpid(),heartbeat=time.time(),
        project_root=str(document.root),project_id=document.manifest['package_id'],scope_kind=scope_kind,
        base_revision=revision(document),brief=brief,constraints=list(constraints),allowed_scope=list(allowed_scope),policy=policy)
    write(folder/'session.json',value);return value


def job_folder(folder,identity):
    if not JOB_ID.fullmatch(identity):raise AuthoringError('session.invalid','Invalid local job ID.')
    return child(Path(folder).resolve(),'jobs/'+identity)


def jobs(folder):
    records=[]
    paths=sorted((Path(folder)/'jobs').glob('*/job.json'))
    if len(paths)>256:raise AuthoringError('capacity.exceeded','This session has more than 256 jobs; start another session.')
    connected=info(folder)['connected']
    for path in paths:
        value=read_json(path)
        if not connected and value['status'] in ('queued','running'):value=dict(value,status='interrupted')
        records.append(value)
    return sorted(records,key=lambda r:r['created'])


def submit(folder,kind,*,request=None,base_dir=None,job_id=None):
    folder=Path(folder).resolve();session=info(folder)
    if not session['connected']:raise AuthoringError('session.disconnected','Start or reconnect an authoring session in the open editor.')
    if kind not in ('snapshot','propose'):raise AuthoringError('session.invalid','Supported jobs are snapshot and propose.')
    if kind=='propose':
        check_batch(request)
        if len(encoded(request))>2*1024*1024:
            raise AuthoringError('request.too_large','Split reviewed command files above 2 MiB into smaller proposals.')
    identity=job_id or uuid.uuid4().hex;target=job_folder(folder,identity)
    command=dict(kind=kind,request=request)
    command_hash=hashlib.sha256(encoded(command)).hexdigest()
    input_hashes={}
    for op in (request or {}).get('operations',[]):
        if op['op'] not in ('art.import','unit.import','script.import'):continue
        path=Path(op['file']);path=path if path.is_absolute() else Path(base_dir or Path.cwd())/path
        if path.is_symlink() or not path.is_file() or path.stat().st_size>16*1024*1024:
            raise AuthoringError('import.unavailable','Import needs a regular file up to 16 MiB: '+str(path))
        input_hashes[op['file']]=hashlib.sha256(path.read_bytes()).hexdigest()
    if target.exists():
        prior=read_json(target/'job.json')
        if prior.get('command_sha256')!=command_hash or prior.get('input_sha256',{})!=input_hashes:
            raise AuthoringError('request.reused','This job ID already belongs to another request or import revision.')
        if (target/'command.json').exists():
            import_paths(target,read_json(target/'command.json'))
            return prior
        raise AuthoringError('session.interrupted','This submission was interrupted before publication. Submit with a new job ID.')
    if len(list((folder/'jobs').iterdir()))>=256:raise AuthoringError('capacity.exceeded','Session job limit reached; start another session.')
    if sum(r['status'] in ('queued','running') for r in jobs(folder))>=8:raise AuthoringError('session.busy','Eight authoring jobs are already queued; wait or cancel one.')
    target.mkdir(mode=0o700)
    record=dict(id=identity,kind=kind,status='queued',created=time.time(),command_sha256=command_hash,input_sha256=input_hashes,diagnostics=[])
    write(target/'job.json',record)
    try:
        command['imports']=freeze_imports(request,base_dir or Path.cwd(),target) if request else {}
        if {key:value['sha256'] for key,value in command['imports'].items()}!=input_hashes:
            raise AuthoringError('revision.conflict','An import changed while the job was submitted.')
        write(target/'command.json',command)
    except Exception:
        record['status']='submission_failed';write(target/'job.json',record);raise
    return record


def cancel(folder,identity):
    target=job_folder(folder,identity)
    if not (target/'job.json').is_file():raise AuthoringError('object.missing','Unknown authoring job.')
    write(target/'cancel.json',dict(cancel=True,at=time.time()))
    return dict(status='cancellation_requested',id=identity)


def wait(folder,identity,seconds=30):
    if not 0<=seconds<=60:raise AuthoringError('query.bounds','Wait between 0 and 60 seconds.')
    target=job_folder(folder,identity);deadline=time.monotonic()+seconds
    while True:
        record=read_json(target/'job.json')
        if record['status'] not in ('queued','running') or time.monotonic()>=deadline:return record
        if not info(folder)['connected']:return dict(record,status='interrupted')
        time.sleep(.05)
