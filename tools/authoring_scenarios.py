"""Bounded scenario/replay evidence, backed by the actual C player."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import time
from authoring_contract import API_VERSION,AuthoringError,check,obj,enum,integer,array,TEXT,ID
from authoring_service import revision
from editor_model import encoded,EditorError
from event_editing import edges

DEFAULT_SEED=11223583  # Little-endian bytes 31, 66, 171 used by normal games.
MOVEMENT=array(integer(0,2047),2,2)
CHECKPOINT_NAME=dict(type='string',minLength=1,maxLength=48,pattern=r'^[a-zA-Z0-9][a-zA-Z0-9_-]*$')
CHECKPOINT=obj(dict(file=dict(type='string',minLength=1,maxLength=1024),sha256=dict(type='string',pattern='^[0-9a-f]{64}$')),['file','sha256'])
MAX_SAVE_BYTES=160+20480  # Current project-save envelope and serialized state.

STEP_SCHEMAS = [
    obj(dict(op={'const':'input'},action=TEXT,repeat=integer(1,120000)),['op','action']),
    *[obj(dict(op={'const':name}),['op']) for name in ('pages','enter','capture')],
    obj(dict(op={'const':'checkpoint'},name=CHECKPOINT_NAME),['op']),
    obj(dict(op={'const':'walk'},entrance=ID,max_positions=integer(1,1048576)),['op','entrance']),
    *[obj(dict(op={'const':'walk'},**{kind:ID},at=MOVEMENT,max_positions=integer(1,1048576)),['op',kind,'at']) for kind in ('map','world')],
    obj(dict(op={'const':'choose'},label=TEXT),['op','label']),
    obj(dict(op={'const':'battle'},control=enum('computer','hold','retreat'),until_round=integer(1,1024)),['op','control']),
    dict(**obj(dict(op={'const':'assert'},credits=integer(0,16777215),party_count=integer(0,8),owned_mechs=integer(0,4),alive_party=integer(0,8),
        battle_outcome=enum('none','pending','win','loss','retreat'),round_min=integer(0,65535),round_max=integer(0,65535),
        person=ID,health_min=integer(0,255),mech=ID,armor_min=integer(0,2805),armor_max=integer(0,2805),
        structure_min=integer(0,2040),structure_max=integer(0,2040),ammo_min=integer(0,2550),ammo_max=integer(0,2550),
        phase=enum('exploration','entry','text','choice','shop','battle','fault','complete'),
        world=ID,world_at=MOVEMENT,formation=enum('compact'),
        discovered=obj(dict(world=ID,at=array(integer(0,1023),2,2),seen=integer(0,1)),['world','at','seen']),
        map=ID,event=ID,flag=ID,variable=ID,region=ID,group=ID,measure=enum('alive','destroyed','deployed','arrived'),value=integer(0,1000000),objective=ID,status=enum('inactive','active','complete','failed')),['op']),
        anyOf=[dict(required=[key]) for key in ('world','world_at','formation','discovered','credits','party_count','phase','map','event','flag','variable','region','group','objective','owned_mechs','alive_party','battle_outcome','round_min','round_max','person','mech')],
        allOf=[dict(**{'if':dict(required=['flag'])},then=dict(required=['value'])),
               *[dict(**{'if':dict(required=[key])},then=dict(required=['value'])) for key in ('variable','region')],
               dict(**{'if':dict(required=['group'])},then=dict(required=['measure','value'])),
               dict(**{'if':dict(required=['objective'])},then=dict(required=['status'])),
               dict(**{'if':dict(required=['health_min'])},then=dict(required=['person'])),
               *[dict(**{'if':dict(required=[key])},then=dict(required=['mech'])) for key in ('armor_min','armor_max','structure_min','structure_max','ammo_min','ammo_max')]]),
]
SCHEMA = obj(dict(format={'const':'btp-author-scenario-v1'},max_ticks=integer(1,120000),seed=integer(1,16777215),
                  checkpoint=CHECKPOINT,
                  expected_revision=dict(type='string',pattern='^[0-9a-f]{64}$'),
                  steps=array(dict(oneOf=STEP_SCHEMAS),1,256)),['format','steps'])
SCHEMA['not']=dict(required=['seed','checkpoint'])


def checkpoint_bytes(path):
    """Read one bounded input, so hashing and staging use the same bytes."""
    try:
        with Path(path).open('rb') as stream:data=stream.read(MAX_SAVE_BYTES+1)
    except OSError as exc:raise AuthoringError('checkpoint.unreadable',f'Cannot read checkpoint: {exc}','$.checkpoint.file') from exc
    if not 184<=len(data)<=MAX_SAVE_BYTES:
        raise AuthoringError('checkpoint.invalid','Checkpoint is truncated or exceeds the supported save size.','$.checkpoint.file')
    return data


def pin_checkpoint(path):
    path=Path(path).resolve()
    return dict(file=str(path),sha256=hashlib.sha256(checkpoint_bytes(path)).hexdigest())


def run(document, scenario, output, runner, settings=None, cancelled=lambda:False, timeout_seconds=45, fixture=None, *, base_dir=None):
    check(scenario,SCHEMA);base=revision(document)
    if scenario.get('expected_revision',base)!=base:
        raise AuthoringError('revision.conflict','Scenario belongs to another content revision; regenerate its setup.')
    output=Path(output).resolve();runner=Path(runner).resolve()
    if output.is_relative_to(document.root):raise AuthoringError('output.invalid','Run scenarios in an artifact directory outside the project.')
    if output.exists():raise AuthoringError('output.exists','Scenario output must be a new directory.')
    if not runner.is_file():raise AuthoringError('runtime.unavailable','Build btp-author-playtest before running scenarios.')
    names=[s['name'] for s in scenario['steps'] if s['op']=='checkpoint' and 'name' in s]
    if len(set(names))!=len(names):raise AuthoringError('request.invalid','Named checkpoints must be unique within a scenario.','$.steps')
    initial=None;origin=None
    if 'checkpoint' in scenario:
        origin=(Path(base_dir or Path.cwd())/scenario['checkpoint']['file']).resolve()
        initial=checkpoint_bytes(origin)
        if hashlib.sha256(initial).hexdigest()!=scenario['checkpoint']['sha256']:
            raise AuthoringError('checkpoint.hash_mismatch','Checkpoint SHA-256 differs; select the intended save again.','$.checkpoint.sha256')
    document.unchanged_on_disk();output.mkdir(parents=True)
    # A private exact snapshot prevents edits during the run from changing
    # its evidence. It is removed from neither the original nor other jobs.
    game=output/'game';game.mkdir();document.stage(game)
    payload=dict(scenario);payload.pop('expected_revision',None)
    setup=dict(fixture) if fixture else dict(kind='ordinary_new_game')
    if initial is not None:
        # A private pinned input keeps a changed/deleted source save from
        # altering this run or preventing its subsequent reproduction.
        (output/'initial.btp').write_bytes(initial)
        payload['checkpoint']=dict(scenario['checkpoint'],file='initial.btp')
        setup=dict(kind='saved_checkpoint',source=str(origin),file='initial.btp',sha256=payload['checkpoint']['sha256'])
        if fixture:setup['fixture']=fixture
        prior=origin.parent/'report.json'
        if prior.is_file() and prior.stat().st_size<=4*1024*1024:
            try:
                evidence=prior.read_bytes();previous=json.loads(evidence)
                checkpoints=[s['checkpoint'] for s in previous.get('steps',[]) if 'checkpoint' in s]
                if any(c.get('file')==origin.name and c.get('sha256')==setup['sha256'] for c in checkpoints) or previous.get('result',{}).get('save')==origin.name:
                    (output/'initial-report.json').write_bytes(evidence)
                    setup['source_report']=dict(file='initial-report.json',sha256=hashlib.sha256(evidence).hexdigest())
            except (OSError,ValueError,TypeError,AttributeError):pass  # Optional historical evidence never replaces save validation.
    source=output/'scenario.json';source.write_bytes(encoded(payload))
    command=[str(runner),'--project',str(game),'--scenario',str(source)]
    for key,path in (settings or {}).items():command.extend(['--'+key,str(Path(path).resolve())])
    start=time.monotonic();timeout=False;was_cancelled=False;process=None;launch_error=None
    # File-backed diagnostics bound memory even when a runtime fault writes
    # repetitive output. Tick/step limits bound normal recordings and traces.
    with (output/'steps.jsonl').open('wb') as log,(output/'stderr.txt').open('wb') as errors:
        was_cancelled=bool(cancelled());timeout=not was_cancelled and timeout_seconds<=0
        if not was_cancelled and not timeout:
            try:process=subprocess.Popen(command,cwd=output,stdout=log,stderr=errors)
            except OSError as exc:launch_error=str(exc)
        try:
            while process is not None and process.poll() is None:
                was_cancelled=bool(cancelled());timeout=not was_cancelled and time.monotonic()-start>=timeout_seconds
                if was_cancelled or timeout:break
                try:process.wait(timeout=.1)
                except subprocess.TimeoutExpired:pass
        finally:
            # Ctrl+C and cancellation must not leave a test player running.
            if process is not None and process.poll() is None:
                process.terminate()
                try:process.wait(timeout=2)
                except subprocess.TimeoutExpired:process.kill();process.wait()
    elapsed=time.monotonic()-start;path=output/'steps.jsonl'
    records=[]
    if path.stat().st_size<=4*1024*1024:
        try:records=[json.loads(line) for line in path.read_text().splitlines() if line]
        except ValueError:records=[]
    final=records[-1] if records and 'status' in records[-1] else {}
    passed=not timeout and not was_cancelled and process is not None and process.returncode==0 and final.get('status')=='passed'
    message=('Scenario exceeded its wall-clock budget.' if timeout else 'Scenario cancelled.' if was_cancelled else launch_error or final.get('message') or (output/'stderr.txt').read_text()[:4000])
    def read_records(path):
        if not path.is_file() or path.stat().st_size>8*1024*1024:return []
        try:return [json.loads(line) for line in path.read_text().splitlines() if line]
        except ValueError:return []
    observed=read_records(output/'events.jsonl');combat=read_records(output/'combat.jsonl')
    visited={v['event'] for v in observed};pairs={(x['event'],y['event']) for x,y in zip(observed,observed[1:])}
    branches=[]
    for event in (document.adventure or {}).get('events',[]):
        outputs=edges(event)
        for branch,target in outputs:
            if (event['id'],target) in pairs and sum(t==target for _,t in outputs)==1:
                branches.append(dict(event=event['id'],branch=branch,target=target))
    navigation=final.get('navigation',{})
    # A planner failure belongs at its destination; an interrupted walk or
    # assertion belongs at the actual runtime location. Keep source IDs so
    # compiler sector names never send the editor to an unrelated inspector.
    where=final.get('state',{}).get('location')
    if navigation.get('code') not in (None,'route.interrupted','route.passed'):
        where=navigation.get('destination') or where
    failure_code=navigation.get('code')
    if not failure_code or failure_code=='route.passed':failure_code='scenario.failed'
    if initial is not None and not records:failure_code='checkpoint.invalid'
    initial_state=next((r['state'] for r in records if r.get('initial')),None)
    setup.update(initial_state=initial_state,start_tick=final.get('start_tick'),start_rng=final.get('start_rng'))
    report=dict(api_version=API_VERSION,status='passed' if passed else 'cancelled' if was_cancelled else 'failed',project_id=document.manifest['package_id'],
                setup=setup,
                revision=base,runtime_sha256=hashlib.sha256(runner.read_bytes()).hexdigest(),
                scenario_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),elapsed_seconds=round(elapsed,4),
                coverage=dict(basis=('Ordinary input from the pinned checkpoint and its saved RNG. Earlier events and branches are not covered by this run. ' if initial is not None else 'Ordinary input from a new game, with the declared/default initial RNG state. ')+ 'Observed transitions do not prove untested conditions.',
                    events=sorted(visited),branches=branches,unvisited_events=sorted(e['id'] for e in (document.adventure or {}).get('events',[]) if e['id'] not in visited)),
                seed=None if initial is not None else scenario.get('seed',DEFAULT_SEED),combat=combat,
                result=final,steps=[r for r in records if 'step' in r],
                artifacts=[dict(path=str(p),bytes=p.stat().st_size) for p in sorted(output.iterdir()) if p.is_file()],
                reproduction=dict(scenario=str(source),original_command=command,cwd=str(output),requires_new_output_directory=True,
                    load=str(output/'initial.btp') if initial is not None else None,
                    failed_step=next((r['step'] for r in records if r.get('ok') is False),None),replay=str(output/'replay.actions')),
                diagnostics=[] if passed else [dict(code='job.cancelled' if was_cancelled else 'scenario.timeout' if timeout else failure_code,severity='error',
                    message=message or 'Scenario runner failed; inspect stderr.txt.',field_path='$.checkpoint' if failure_code=='checkpoint.invalid' else '$.steps',
                    object_id=final.get('state',{}).get('event'),location=where)])
    (output/'report.json').write_bytes(encoded(report))
    # Console response stays compact. Full per-step evidence is in the report.
    return dict(api_version=API_VERSION,status=report['status'],revision=base,report=str(output/'report.json'),
                elapsed_seconds=report['elapsed_seconds'],result=final,diagnostics=report['diagnostics'])


SUITE_SCHEMA=obj(dict(format={'const':'btp-author-suite-v1'},max_seconds=integer(1,300),
    cases=array(obj(dict(id=dict(type='string',minLength=1,maxLength=48,pattern=r'^[a-zA-Z0-9_-]+$'),file=TEXT,
        fixture=TEXT,seeds=array(integer(1,16777215),1,8),tags=array(TEXT,0,16)),['id','file']),1,16)),['format','cases'])


def run_suite(document,suite,base_dir,output,runner,settings=None,cancelled=lambda:False,case_ids=None):
    """Independent new-game or pinned continuation routes, with one report."""
    from authoring_contract import read_json
    check(suite,SUITE_SCHEMA);base=revision(document);output=Path(output).resolve();base_dir=Path(base_dir).resolve()
    if output.is_relative_to(document.root):raise AuthoringError('output.invalid','Write suite evidence outside the game project.')
    if output.exists():raise AuthoringError('output.exists','Suite output must be a new directory.')
    names=[c['id'] for c in suite['cases']]
    if len(set(names))!=len(names):raise AuthoringError('request.invalid','Suite case IDs must be unique.')
    if case_ids:
        if set(case_ids)-set(names):raise AuthoringError('object.missing','Unknown suite case: '+', '.join(sorted(set(case_ids)-set(names))))
        suite=dict(suite,cases=[c for c in suite['cases'] if c['id'] in set(case_ids)])
    jobs=[]
    for case in suite['cases']:
        scenario=read_json(base_dir/case['file']);check(scenario,SCHEMA)
        if 'checkpoint' in scenario:
            if 'seeds' in case:raise AuthoringError('request.invalid','Checkpoint cases keep saved RNG; remove the seed sweep.')
            jobs.append((case,scenario));continue
        seeds=case.get('seeds',[scenario.get('seed',DEFAULT_SEED)])
        if len(set(seeds))!=len(seeds):raise AuthoringError('request.invalid','A case repeats a seed.')
        for seed in seeds:jobs.append((case,dict(scenario,seed=seed)))
    if len(jobs)>32:raise AuthoringError('query.bounds','A suite runs at most 32 scenarios; split larger studies.')
    document.unchanged_on_disk();output.mkdir(parents=True);start=time.monotonic();runs=[]
    deadline=start+suite.get('max_seconds',180);stop=None
    with tempfile.TemporaryDirectory(prefix='btp-suite-fixtures-') as temporary:
        prepared={}
        for case,scenario in jobs:
            if cancelled():stop='cancelled';break
            remaining=deadline-time.monotonic()
            if remaining<=0:stop='timeout';break
            candidate=document;origin=None
            try:
                if case.get('fixture'):
                    if case['id'] not in prepared:
                        from editor_model import ProjectDocument,AUTHORING_RECEIPTS
                        from authoring_service import apply_batch
                        from authoring_contract import check_batch
                        request_path=base_dir/case['fixture'];request=read_json(request_path);check_batch(request)
                        if request['expected_revision']!='new':raise AuthoringError('revision.conflict','A fixture batch must use expected_revision "new" for its private staged copy.')
                        folder=Path(temporary)/case['id'];folder.mkdir();document.stage(folder)
                        candidate=ProjectDocument(folder,document.validator,recover=False)
                        candidate.metadata.pop(AUTHORING_RECEIPTS,None)
                        apply_batch(candidate,dict(request,expected_revision=revision(candidate)),base_dir=request_path.parent)
                        origin=dict(kind='validated_fixture',source_revision=base,commands_sha256=hashlib.sha256(request_path.read_bytes()).hexdigest())
                        prepared[case['id']]=(candidate,origin)
                    candidate,origin=prepared[case['id']]
                suffix='-checkpoint' if 'checkpoint' in scenario else '-seed-'+str(scenario['seed'])
                result=run(candidate,scenario,output/(case['id']+suffix),runner,settings,cancelled,min(45,max(.01,deadline-time.monotonic())),origin,
                    base_dir=(base_dir/case['file']).parent)
            except (EditorError,OSError) as exc:
                # Keep prior evidence if content changes or a later case fails
                # before launching. A partial suite never reports success.
                runs.append(dict(case=case['id'],tags=case.get('tags',[]),seed=scenario.get('seed'),status='failed',report=None,
                    ticks=None,coverage=dict(events=[],branches=[]),combat=[],diagnostics=[dict(code='suite.setup_failed',severity='error',message=str(exc))]))
                stop='setup_failed';break
            full=json.loads(Path(result['report']).read_bytes())
            runs.append(dict(case=case['id'],tags=case.get('tags',[]),seed=scenario.get('seed'),status=result['status'],report=result['report'],
                             setup=full['setup'],ticks=full['result'].get('ticks'),coverage=full['coverage'],combat=full['combat'],diagnostics=full['diagnostics']))
            if result['status']=='cancelled':stop='cancelled';break
    # Seed samples are descriptive. A hold-policy defeat and computer victory
    # are never blended into one misleading win-rate estimate.
    samples=[]
    for case in suite['cases']:
        subset=[b for run_ in runs if run_['case']==case['id'] for b in run_['combat']]
        if not subset:continue
        samples.append(dict(case=case['id'],samples=len(subset),policies=sorted({b['policy'] for b in subset}),
            metric_bases=sorted({b.get('metric_basis','whole_battle') for b in subset}),
            wins=sum(b['outcome']=='win' for b in subset),losses=sum(b['outcome']=='loss' for b in subset),retreats=sum(b['outcome']=='retreat' for b in subset),
            mean_rounds=sum(b['rounds'] for b in subset)/len(subset),
            mean_rounds_observed=sum(b['rounds']-b.get('start_round',0) for b in subset)/len(subset),
            mean_armor_reduction=sum(b['armor_reduction'] for b in subset)/len(subset),
            mean_structure_reduction=sum(b['structure_reduction'] for b in subset)/len(subset),
            mean_ammunition_reduction=sum(b['ammunition_reduction'] for b in subset)/len(subset),
            friendly_mechs_lost=sum(b['friendly_mechs_lost'] for b in subset)))
    report=dict(api_version=API_VERSION,status='cancelled' if stop=='cancelled' else 'passed' if not stop and all(r['status']=='passed' for r in runs) else 'failed',
        revision=base,project_id=document.manifest['package_id'],runs_planned=len(jobs),runs_completed=len(runs),
        elapsed_seconds=round(time.monotonic()-start,4),stopped=stop,runs=runs,combat_samples=samples,
        coverage=dict(events=sorted({e for r in runs for e in r['coverage']['events']}),
            basis='Only declared routes/seeds/policies are measured; no proof of all Lua paths or general combat balance.'),
        metric_basis='Armor/structure/ammunition reductions include destroyed units and destroyed ammunition, not only shots fired. since_checkpoint samples measure only the remaining portion; rounds is the final battle round, rounds_observed excludes earlier rounds.')
    (output/'suite-report.json').write_bytes(encoded(report))
    return dict(api_version=API_VERSION,status=report['status'],revision=base,report=str(output/'suite-report.json'),
        runs_planned=len(jobs),runs_completed=len(runs),elapsed_seconds=report['elapsed_seconds'],combat_samples=samples)
