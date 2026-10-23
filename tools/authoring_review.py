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
    payload=encoded(record)
    if len(payload)>16*1024*1024:raise AuthoringError('review.too_large','Review exceeds 16 MiB. Split this proposal into smaller batches.')
    ProjectDocument.atomic_file(Path(folder)/'review.json',payload)


def read(folder):
    folder=Path(folder).resolve();record=read_json(folder/'review.json')
    required={'status','project_root','project_id','base_revision','request','effective_request','groups','selected','allowed_scope','imports','history','diagnostics'}
    if not isinstance(record,dict) or record.get('format')!=FORMAT or not required.issubset(record):
        raise AuthoringError('review.invalid','Select a complete Construction Kit review directory.')
    return record


def freeze_imports(request,base_dir,folder,retained=None):
    from authoring_contract import IMPORT_OPERATIONS
    imports={};total=0
    for op in request['operations']:
        if op['op'] not in IMPORT_OPERATIONS or op['file'] in imports:continue
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


def visual_artifacts(before,after,changes,folder,settings,cancelled,world_changes=()):
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
        from world_review import overview
        for n,change in enumerate(world_changes):
            if not change.get(side):continue
            try:artifacts.append(dict(kind='world',side=side,id=change['id'],**overview(document,change,folder/(side+'-world-'+str(n)+'.svg'),settings,cancelled)))
            except (EditorError,OSError,ValueError,KeyError) as error:
                if diagnostic(error)['code']=='job.cancelled':raise
                diagnostics.append(dict(code='preview.unavailable',severity='warning',object_id=change['id'],message=str(error)))
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
            root=folder/name;root.mkdir();source.stage_authoring(root)
        from world_review import changes as changed_worlds
        record.update(result=result,result_revision=revision(candidate),changes=details(document,candidate,result['changes']),
                      conflicts=conflicts(document,candidate,cancelled),dependency_before=dependencies(document),dependency_after=dependencies(candidate),
                      world_changes=changed_worlds(document,candidate,cancelled))
        record['displaced_details']=result['displaced_details']
        if visuals:
            record['artifacts'],warnings=visual_artifacts(document,candidate,result['changes'],folder,settings or {},cancelled,record['world_changes'])
            record['diagnostics'].extend(warnings)
        if cancelled():raise AuthoringError('job.cancelled','Review preparation cancelled.')
        document.unchanged_on_disk()
        record['status']='conflicts' if record['conflicts'] else 'ready'
    except Exception as error:
        record['status']='cancelled' if diagnostic(error)['code']=='job.cancelled' else 'failed'
        record['diagnostics'].append(diagnostic(error))
    try:write(folder,record)
    except AuthoringError as error:
        # Retain the snapshots even if their combined display report is too
        # large. Never publish a proposal whose review cannot be read back.
        for key in ('result','result_revision','dependency_before','dependency_after','displaced_details'):record.pop(key,None)
        record.update(status='failed',changes=[],conflicts=[],artifacts=[],world_changes=[],diagnostics=[diagnostic(error)])
        write(folder,record)
    return record


def world_crop(folder,identity,rect,validator,settings=None,cancelled=lambda:False):
    """Retain a paired full-pixel crop of exact review snapshots, on demand."""
    # One writer per crop cache also makes its 64-crop limit meaningful when
    # the GUI and a local author request detail at the same time.
    with project_lock(Path(folder)/'world-crops'):
        return _world_crop(folder,identity,rect,validator,settings,cancelled)


def _world_crop(folder,identity,rect,validator,settings,cancelled):
    from world_review import Surface,overlap,detail
    folder=Path(folder).resolve();record=read(folder)
    if identity not in [w['id'] for w in record.get('world_changes',[])]:
        raise AuthoringError('object.missing','Select a changed world in this review.')
    if len(rect)!=4 or any(type(n)!=int for n in rect) or min(rect[:2])<0 or min(rect[2:])<1 or max(rect[2:])>64:
        raise AuthoringError('coordinate.bounds','Review detail crops use world-tile rectangles up to 64 by 64.')
    # Cache only a bounded set of crops. The original snapshots, revision and
    # content are checked even when reopening a previously rendered crop.
    docs={}
    change=next(w for w in record['world_changes'] if w['id']==identity)
    for side,key in [('before','base_revision'),('after','result_revision')]:
        if not change[side]:continue
        if cancelled():raise AuthoringError('job.cancelled','World detail cancelled.')
        docs[side]=ProjectDocument(folder/side,validator,recover=False)
        if revision(docs[side])!=record[key]:raise AuthoringError('review.changed','Retained world snapshot changed; prepare a new proposal.')
    cache=folder/'world-crops';cache.mkdir(exist_ok=True)
    digest=hashlib.sha256(encoded(dict(world=identity,rect=rect))).hexdigest();index=cache/(digest+'.json')
    if index.exists():
        result=read_json(index)
        for item in result:
            path=child(cache,Path(item['artifact']['path']).name)
            if hashlib.sha256(path.read_bytes()).hexdigest()!=item['artifact']['sha256']:
                raise AuthoringError('review.changed','A retained world preview changed; prepare a new review.')
            item['artifact']['path']=str(path)
        return result
    if len(list(cache.glob('*.json')))>=64:raise AuthoringError('preview.bounded','This review has 64 detail crops; use an existing crop or prepare another review.')
    result=[]
    for side,document in docs.items():
        if cancelled():raise AuthoringError('job.cancelled','World detail cancelled.')
        surface=Surface(document,identity);hit=overlap(rect,[0,0,surface.width,surface.height])
        if not hit:continue
        # A cancelled/failed render can leave an unindexed SVG. Give each
        # attempted write its own name so retrying preserves the evidence.
        target=cache/(uuid.uuid4().hex+'-'+side+'.svg')
        preview=detail(document,change,target,hit,settings,cancelled)
        result.append(dict(kind='world',side=side,id=identity,**preview))
    if not result:raise AuthoringError('coordinate.bounds','The crop must intersect the world in at least one retained snapshot.')
    if cancelled():raise AuthoringError('job.cancelled','World detail cancelled.')
    ProjectDocument.atomic_file(index,encoded(result));return result


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
                      approved_overrides=prepared['overrides'],application={k:v for k,v in result.items() if k in ('status','request_id','base_revision','result_revision','current_revision')})
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


def suggest_cases(folder,validator,suite,*,cancelled=lambda:False):
    """Retain a suite and its explanations without running or publishing it."""
    from authoring_impact import capture_suite,analyse,cancelled_check
    folder=Path(folder).resolve();record=read(folder)
    if len(record.get('selections',[]))>=32:raise AuthoringError('capacity.exceeded','This review already has 32 scenario selections.')
    before=ProjectDocument(folder/'before',validator,recover=False);after=ProjectDocument(folder/'after',validator,recover=False)
    if revision(before)!=record['base_revision'] or revision(after)!=record.get('result_revision'):
        raise AuthoringError('review.changed','Retained review snapshots changed; prepare the proposal again.')
    output=folder/('selection-'+uuid.uuid4().hex);output.mkdir()
    inputs=capture_suite(suite,output/'inputs',cancelled)
    report=analyse(before,after,read_json(output/inputs['suite']),(output/inputs['suite']).parent,cancelled)
    report.update(base_revision=record['base_revision'],revision=record['result_revision'],inputs=inputs)
    before.unchanged_on_disk();after.unchanged_on_disk();cancelled_check(cancelled)
    path=output/'selection.json';payload=encoded(report);ProjectDocument.atomic_file(path,payload)
    with project_lock(folder):
        latest=read(folder)
        if latest['base_revision']!=record['base_revision'] or latest['result_revision']!=record['result_revision']:
            raise AuthoringError('review.changed','Proposed content changed during dependency analysis.')
        if len(latest.get('selections',[]))>=32:raise AuthoringError('capacity.exceeded','This review already has 32 scenario selections.')
        latest.setdefault('selections',[]).append(dict(report=str(path.relative_to(folder)),sha256=hashlib.sha256(payload).hexdigest(),
            revision=record['result_revision'],base_revision=record['base_revision']))
        write(folder,latest)
    return dict(report=str(path),**report)


def read_selection(folder,selection,record=None):
    """Accept only a linked, unchanged report for these exact review snapshots."""
    folder=Path(folder).resolve();record=record or read(folder)
    path=Path(selection)
    # CLI paths may be relative to the working directory; stored review links
    # are relative to the proposal. Both still have to match a linked report.
    path=path.resolve() if path.is_absolute() or path.is_file() else child(folder,str(path))
    link=next((v for v in record.get('selections',[]) if child(folder,v['report']).resolve()==path.resolve()),None)
    if not link or link['revision']!=record['result_revision'] or link['base_revision']!=record['base_revision']:
        raise AuthoringError('selection.stale','Select a scenario report belonging to this exact proposal.')
    report=read_json(path)
    if hashlib.sha256(encoded(report)).hexdigest()!=link['sha256']:
        raise AuthoringError('selection.changed','Retained scenario selection changed; load the suite again.')
    return dict(report=str(path),**report)


def check_candidate(folder,validator,*,settings=None,analyzer=None,runner=None,suite=None,selection=None,case_ids=None,suggested=False,cancelled=lambda:False):
    """Attach checks of this exact proposed package, never of the live draft."""
    from authoring_analysis import analyze
    from authoring_scenarios import run_suite
    from authoring_impact import verify_inputs
    if suite is not None and selection is not None:raise AuthoringError('request.invalid','Choose a suite file or a retained selection, not both.')
    if suggested and case_ids is not None:raise AuthoringError('request.invalid','Choose suggested cases or explicit case IDs, not both.')
    if (case_ids is not None or suggested) and suite is None and selection is None:
        raise AuthoringError('request.invalid','Case selection requires a suite or retained selection report.')
    folder=Path(folder).resolve();record=read(folder)
    if len(record.get('checks',[]))>=32:raise AuthoringError('capacity.exceeded','This review already has 32 check reports. Prepare another review.')
    settings={k:v for k,v in (settings or {}).items() if k in ('data','dialogue-data','combat-data','world-data')}
    candidate=ProjectDocument(folder/'after',validator,recover=False)
    if revision(candidate)!=record.get('result_revision'):raise AuthoringError('review.changed','Retained candidate changed; prepare it again.')
    output=folder/('checks-'+uuid.uuid4().hex);output.mkdir()
    if suite is not None or selection is not None:
        # Every review suite run pins its inputs. The GUI can reuse a report it
        # already displayed; CLI --suite captures a fresh report by default.
        impact=suggest_cases(folder,validator,suite,cancelled=cancelled) if suite is not None else read_selection(folder,selection,record)
        before=ProjectDocument(folder/'before',validator,recover=False)
        if revision(before)!=record['base_revision']:raise AuthoringError('review.changed','Retained base changed; prepare it again.')
        suite_file=verify_inputs(Path(impact['report']).parent,impact['inputs'])
        if suggested:case_ids=impact['suggested']
        if case_ids==[]:raise AuthoringError('selection.empty','No cases selected. Choose cases explicitly or run the full suite; no tests have passed.')
        result=run_suite(candidate,read_json(suite_file),suite_file.parent,output/'suite',runner,settings,cancelled,case_ids=case_ids)
        verify_inputs(Path(impact['report']).parent,impact['inputs'])
        result['selection']=impact['report'];result['selection_mode']='suggested' if suggested else 'explicit' if case_ids is not None else 'full'
    else:
        if cancelled():raise AuthoringError('job.cancelled','Mission check cancelled.')
        result=analyze(candidate,analyzer,settings,output=output/'lint.json')
    candidate.unchanged_on_disk()
    if suite is not None or selection is not None:before.unchanged_on_disk()
    report_file=output/'result.json';ProjectDocument.atomic_file(report_file,encoded(result))
    with project_lock(folder):
        latest=read(folder)
        if latest['result_revision']!=record['result_revision']:raise AuthoringError('review.changed','Proposed content changed during checks.')
        # Large suite traces stay in their own artifact. Thirty-two linked
        # reports must not make the main review record unreadable.
        concise=dict(status=result['status'],report=str(report_file),diagnostics=[
            {k:(str(v)[:1000] if k=='message' else v) for k,v in d.items() if k in ('code','severity','message')}
            for d in result.get('diagnostics',[])[:8]])
        if len(latest.get('checks',[]))>=32:raise AuthoringError('capacity.exceeded','This review already has 32 check reports.')
        if 'selection' in result:concise.update(selection=result['selection'],selected_cases=result['selected_cases'],unselected_cases=result['unselected_cases'])
        latest.setdefault('checks',[]).append(dict(kind='suite' if suite is not None or selection is not None else 'mission',revision=record['result_revision'],result=concise))
        write(folder,latest)
    return result
