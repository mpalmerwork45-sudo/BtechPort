"""Durable, inspectable proposals with exact inputs and validated partial groups.

Review directories are private artifacts outside the game. Their base and
candidate are ordinary packages, so they remain inspectable after an editor or
model crash. Applying always rechecks the live revision and shared validator.
"""
import copy
import hashlib
import json
from pathlib import Path
import time
import uuid

from authoring_contract import API_VERSION,AuthoringError,check_batch,diagnostic,read_json
from authoring_service import apply_batch,detached,revision
from authoring_protection import rules,conflicts,value_at
from editor_model import ProjectDocument,EditorError,encoded,child
from project_lock import project_lock

FORMAT='btp-author-review-v1'


def groups(request):
    return copy.deepcopy(request.get('groups') or [dict(id='batch',label=request['label'],operations=list(range(len(request['operations']))),requires=[])])


def selected_request(request,selected=None):
    check_batch(request);values=groups(request);by_id={v['id']:v for v in values}
    chosen=set(by_id if selected is None else selected)
    if not chosen or chosen-set(by_id):raise AuthoringError('group.invalid','Choose at least one existing change group.')
    pending=list(chosen)
    while pending:
        for dependency in by_id[pending.pop()].get('requires',[]):
            if dependency not in chosen:chosen.add(dependency);pending.append(dependency)
    result=copy.deepcopy(request)
    if chosen!=set(by_id):
        indices={i for g in values if g['id'] in chosen for i in g['operations']}
        result['operations']=[op for i,op in enumerate(request['operations']) if i in indices]
        # A partial acceptance has its own durable receipt; retrying either the
        # complete proposal or a different subset cannot impersonate this one.
        suffix=hashlib.sha256(encoded(sorted(chosen))).hexdigest()[:16]
        result['request_id']=request['request_id'][:74]+'.part-'+suffix
        result.pop('groups',None)
    return result,[v['id'] for v in values if v['id'] in chosen]


def write(folder,record):
    ProjectDocument.atomic_file(Path(folder)/'review.json',encoded(record))


def read(folder):
    folder=Path(folder).resolve();record=read_json(folder/'review.json')
    required={'status','project_root','project_id','base_revision','request','effective_request','groups','selected','allowed_scope','imports','history','diagnostics'}
    if not isinstance(record,dict) or record.get('format')!=FORMAT or not required.issubset(record):
        raise AuthoringError('review.invalid','Select a complete Construction Kit review directory.')
    return record


def freeze_imports(request,base_dir,folder,retained=None):
    imports={};total=0
    for op in request['operations']:
        if op['op'] not in ('art.import','unit.import','script.import') or op['file'] in imports:continue
        original=Path((retained or {}).get(op['file'],op['file']));original=original if original.is_absolute() else Path(base_dir)/original
        if original.is_symlink() or not original.is_file() or original.stat().st_size>16*1024*1024:
            raise AuthoringError('import.unavailable','Import needs a regular file up to 16 MiB: '+str(original))
        payload=original.read_bytes();total+=len(payload)
        if total>64*1024*1024:raise AuthoringError('capacity.exceeded','Review imports exceed 64 MiB.')
        name='imports/'+str(len(imports))+original.suffix
        destination=child(folder,name);destination.parent.mkdir(exist_ok=True);destination.write_bytes(payload)
        imports[op['file']]=dict(file=name,sha256=hashlib.sha256(payload).hexdigest())
    return imports


def import_paths(folder,record):
    result={}
    for name,item in record['imports'].items():
        path=child(Path(folder),item['file'])
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:
            raise AuthoringError('review.changed','A retained import changed. Prepare a new proposal.')
        result[name]=path
    return result


def short(value,limit=6000):
    payload=json.dumps(value,ensure_ascii=True,indent=2)
    return payload if len(payload)<=limit else payload[:max(0,limit-150)]+'\n… [complete value in retained package; sha256 '+hashlib.sha256(payload.encode()).hexdigest()+']'


def details(before,after,changes):
    # A large map/tile batch must still produce a readable review record.
    # Full values remain in the two packages; display excerpts share 4 MiB.
    limit=min(6000,max(150,4*1024*1024//max(1,2*len(changes))))
    return [dict(change,before=short(value_at(before,change['path']),limit),after=short(value_at(after,change['path']),limit)) for change in changes]


def dependencies(document):
    return dict(requires=document.manifest['requires'],assets=document.manifest['assets'],
                scripts=document.manifest.get('scripts',[]),
                presentations=document.content.get('presentations',[]),
                provenance=json.loads(document.metadata.get('LIBRARY-SOURCES.json',b'[]')))


def visual_artifacts(before,after,changes,folder,settings,cancelled):
    from authoring_visuals import map_svg,event_graph
    artifacts=[];diagnostics=[]
    maps=[c['object_id'] for c in changes if c['path'].startswith('adventure.maps/')]
    events=any(c['path'].startswith('adventure.events') for c in changes)
    for side,document in [('before',before),('after',after)]:
        for n,identity in enumerate(maps[:8]):
            if cancelled():raise AuthoringError('job.cancelled','Review preparation cancelled.')
            if not any(m['id']==identity for m in (document.adventure or {}).get('maps',[])):continue
            output=folder/(side+'-map-'+str(n)+'.svg')
            try:artifacts.append(dict(kind='map',side=side,id=identity,**map_svg(document,identity,output,settings,overlays=['entrances','grid'])))
            except (EditorError,OSError,ValueError,KeyError) as error:diagnostics.append(dict(code='preview.unavailable',severity='warning',message=str(error)))
        if events:
            try:artifacts.append(dict(kind='events',side=side,**event_graph(document,folder/(side+'-events.svg'))))
            except (EditorError,OSError,ValueError) as error:diagnostics.append(dict(code='preview.unavailable',severity='warning',message=str(error)))
    if len(maps)>8:diagnostics.append(dict(code='preview.bounded',severity='warning',message='First eight changed maps rendered; all changes remain in retained packages.'))
    return artifacts,diagnostics


def prepare(document,request,folder,*,base_dir=None,selected=None,settings=None,allowed_scope=None,
            cancelled=lambda:False,visuals=True,retained_imports=None):
    folder=Path(folder).resolve();check_batch(request)
    if len(encoded(request))>2*1024*1024:
        raise AuthoringError('request.too_large','Split reviewed command files above 2 MiB into smaller proposals.')
    if folder.is_relative_to(document.root):raise AuthoringError('output.invalid','Keep reviews outside the game project.')
    if folder.exists():raise AuthoringError('output.exists','Choose a new review directory.')
    effective,chosen=selected_request(request,selected);base=revision(document)
    folder.mkdir(parents=True,mode=0o700)
    record=dict(format=FORMAT,api_version=API_VERSION,status='preparing',created=time.time(),
        project_id=document.manifest['package_id'],project_root=str(document.root),base_revision=base,
        request=copy.deepcopy(request),effective_request=effective,groups=groups(request),selected=chosen,
        allowed_scope=list(allowed_scope or request['scope']),brief=request.get('brief',''),constraints=request.get('constraints',[]),
        imports={},changes=[],conflicts=[],diagnostics=[],artifacts=[],history=[])
    write(folder,record)
    try:
        document.unchanged_on_disk()
        if cancelled():raise AuthoringError('job.cancelled','Review preparation cancelled.')
        record['imports']=freeze_imports(request,base_dir or document.root,folder,retained_imports);write(folder,record)
        candidate=detached(document)
        result=apply_batch(candidate,effective,frozen_imports=import_paths(folder,record),cancelled=cancelled,
            protection_overrides=[r['id'] for r in rules(document)],allowed_scope=record['allowed_scope'])
        if result['status']=='already_applied':
            record.update(status='already_applied',result=result);write(folder,record);return record
        # Both complete snapshots are retained for review/recovery. The live
        # document is still untouched, including its drafts and Undo stack.
        for name,source in [('before',document),('after',candidate)]:
            root=folder/name;root.mkdir();source.stage(root)
        record.update(result=result,result_revision=revision(candidate),changes=details(document,candidate,result['changes']),
                      conflicts=conflicts(document,candidate),dependency_before=dependencies(document),dependency_after=dependencies(candidate))
        record['displaced_details']=result['displaced_details']
        if visuals:
            record['artifacts'],warnings=visual_artifacts(document,candidate,result['changes'],folder,settings or {},cancelled)
            record['diagnostics'].extend(warnings)
        if cancelled():raise AuthoringError('job.cancelled','Review preparation cancelled.')
        document.unchanged_on_disk()
        record['status']='conflicts' if record['conflicts'] else 'ready'
    except Exception as error:
        record['status']='cancelled' if diagnostic(error)['code']=='job.cancelled' else 'failed'
        record['diagnostics'].append(diagnostic(error))
    write(folder,record)
    return record


def prepare_apply(document,folder,*,overrides=(),cancelled=lambda:False):
    """Validate a detached result in a worker; publication belongs to its owner."""
    folder=Path(folder).resolve();record=read(folder)
    if str(document.root)!=record['project_root'] or document.manifest['package_id']!=record['project_id']:
        raise AuthoringError('project.mismatch','This review belongs to another project or library editing scope.')
    if record['status'] not in ('ready','conflicts','applied','applying'):
        raise AuthoringError('review.unavailable','Review is '+record['status']+'. Prepare a new proposal or recheck a selected subset.')
    candidate=detached(document)
    result=apply_batch(candidate,record['effective_request'],frozen_imports=import_paths(folder,record),
        protection_overrides=overrides,allowed_scope=record['allowed_scope'],expected_result=record['result_revision'],cancelled=cancelled)
    return dict(candidate=candidate,result=result,record=record,overrides=list(overrides))


def publish(document,folder,prepared,*,save=False):
    folder=Path(folder).resolve()
    with project_lock(folder):
        record=read(folder);result=prepared['result'];candidate=prepared['candidate']
        if record!=prepared['record']:raise AuthoringError('review.changed','The review changed while application was checked.')
        document.unchanged_on_disk()
        if str(document.root)!=record['project_root']:raise AuthoringError('project.mismatch','The editing scope changed.')
        expected=result.get('current_revision') if result['status']=='already_applied' else record['base_revision']
        if revision(document)!=expected:raise AuthoringError('revision.conflict','Human work changed during review. Prepare a fresh proposal.')
        # The shared receipt resolves interruption between publication and this
        # review's status write. An intentional Undo still counts as handled.
        prior=record['status'];record['status']='applying';write(folder,record)
        previous=copy.deepcopy(document.__dict__)
        try:
            if result['status']!='already_applied':
                with document.command(record['effective_request']['label']):
                    document.replace_all(candidate.content,candidate.adventure,candidate.art,candidate.manifest,candidate.metadata)
                    if save:document.save()
        except Exception:
            document.__dict__.clear();document.__dict__.update(previous)
            record['status']=prior;write(folder,record);raise
        record.update(status='applied',applied=time.time(),applied_revision=result.get('current_revision',result['result_revision']),
                      approved_overrides=prepared['overrides'],application=result)
        write(folder,record)
        return result


def apply(document,folder,*,overrides=(),save=False,cancelled=lambda:False):
    return publish(document,folder,prepare_apply(document,folder,overrides=overrides,cancelled=cancelled),save=save)


def decide(folder,action,note=''):
    if action not in ('discard','request_changes'):raise AuthoringError('review.invalid','Choose discard or request_changes.')
    folder=Path(folder).resolve()
    with project_lock(folder):
        record=read(folder)
        if record['status'] in ('applied','applying'):raise AuthoringError('review.unavailable','Use editor Undo for an applied proposal.')
        record['status']='discarded' if action=='discard' else 'changes_requested'
        record['history'].append(dict(action=action,note=note[:4096],at=time.time()));write(folder,record)
    return record


def recheck(document,folder,output,selected,*,settings=None,cancelled=lambda:False):
    record=read(folder)
    if revision(document)!=record['base_revision']:
        raise AuthoringError('revision.conflict','Human work changed since this proposal. Export a fresh snapshot and revise the request.')
    # Reuse the captured input bytes even if their original files disappeared.
    return prepare(document,record['request'],output,selected=selected,settings=settings,allowed_scope=record['allowed_scope'],
                   cancelled=cancelled,retained_imports=import_paths(folder,record))


def check_candidate(folder,validator,*,settings=None,analyzer=None,runner=None,suite=None,cancelled=lambda:False):
    """Attach checks of this exact proposed package, never of the live draft."""
    from authoring_analysis import analyze
    from authoring_scenarios import run_suite
    folder=Path(folder).resolve();record=read(folder)
    if len(record.get('checks',[]))>=32:raise AuthoringError('capacity.exceeded','This review already has 32 check reports. Prepare another review.')
    settings={k:v for k,v in (settings or {}).items() if k in ('data','dialogue-data','combat-data','world-data')}
    candidate=ProjectDocument(folder/'after',validator,recover=False)
    if revision(candidate)!=record.get('result_revision'):raise AuthoringError('review.changed','Retained candidate changed; prepare it again.')
    output=folder/('checks-'+uuid.uuid4().hex);output.mkdir()
    if suite is not None:
        suite=Path(suite);result=run_suite(candidate,read_json(suite),suite.parent,output/'suite',runner,settings,cancelled)
    else:
        if cancelled():raise AuthoringError('job.cancelled','Mission check cancelled.')
        result=analyze(candidate,analyzer,settings,output=output/'lint.json')
    if cancelled():raise AuthoringError('job.cancelled','Mission check cancelled; any completed artifacts were retained.')
    with project_lock(folder):
        latest=read(folder)
        if latest['result_revision']!=record['result_revision']:raise AuthoringError('review.changed','Proposed content changed during checks.')
        latest.setdefault('checks',[]).append(dict(kind='suite' if suite else 'mission',revision=record['result_revision'],result=result))
        write(folder,latest)
    return result
