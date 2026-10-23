"""Project-owned scenario suites; the native player remains the test oracle.

Definitions live in EDITOR.json, so editing them shares Save/Undo/recovery with
maps. Exported suites retain all inputs outside the project and use the ordinary
CLI format. Static dependencies and observed gameplay are deliberately separate.
"""
import copy
import json
from pathlib import Path
import tempfile

from authoring_contract import AuthoringError, IMPORT_OPERATIONS, check, check_batch, read_json
from authoring_scenarios import SCHEMA, SUITE_SCHEMA, DEFAULT_SEED, pin_checkpoint, run_suite
from authoring_impact import Graph, capture_suite, verify_inputs, cancelled_check
from authoring_service import revision
from editor_model import encoded
from event_editing import editor_data, editor_commit, edges


def suites(document):
    return editor_data(document).get('test_suites',[])


def validate_suite(value, *, runnable=False):
    """Validate owned definitions with the same schemas used for CLI execution."""
    if not isinstance(value,dict):raise AuthoringError('suite.invalid','Expected a suite object.')
    if set(value)-{'id','name','max_seconds','cases'}:raise AuthoringError('suite.invalid','Unknown suite property.')
    # Reuse the standard case-ID schema for suite IDs too; never use user text
    # as a directory name before validation.
    check(value.get('id'),SUITE_SCHEMA['properties']['cases']['items']['properties']['id'])
    if not isinstance(value.get('name'),str) or not 1<=len(value['name'])<=120:
        raise AuthoringError('suite.invalid','Suite names use 1..120 characters.')
    cases=value.get('cases')
    if not isinstance(cases,list) or len(cases)>16:raise AuthoringError('suite.invalid','A suite holds at most 16 cases.')
    if runnable and not cases:raise AuthoringError('suite.empty','Add a scenario case before exporting or running.')
    ordinary=[]
    for case in cases:
        if not isinstance(case,dict) or set(case)-{'id','scenario','file','fixture','fixture_commands','seeds','tags'}:
            raise AuthoringError('suite.invalid','Unknown case property.')
        if ('scenario' in case)==('file' in case):raise AuthoringError('suite.invalid','Choose an owned scenario or a file reference.')
        item={k:v for k,v in case.items() if k in ('id','file','fixture','seeds','tags')}
        item.setdefault('file','scenario.json');ordinary.append(item)
        if 'scenario' in case:
            check(case['scenario'],SCHEMA)
            names=[s['name'] for s in case['scenario']['steps'] if s['op']=='checkpoint' and 'name' in s]
            if len(names)!=len(set(names)):raise AuthoringError('suite.invalid','Checkpoint names must be unique.')
            if 'checkpoint' in case['scenario'] and 'seeds' in case:
                raise AuthoringError('suite.invalid','A checkpoint preserves its RNG; remove the seed sweep.')
        if 'fixture_commands' in case:
            if 'fixture' in case:raise AuthoringError('suite.invalid','Choose an owned fixture or a file reference.')
            check_batch(case['fixture_commands'])
            if case['fixture_commands']['expected_revision']!='new':raise AuthoringError('suite.invalid','Fixture revision must be new.')
        if len(set(case.get('seeds',[])))!=len(case.get('seeds',[])):raise AuthoringError('suite.invalid','A case repeats a seed.')
    # An empty draft is useful, but the standard runnable format requires cases.
    check(dict(format='btp-author-suite-v1',max_seconds=value.get('max_seconds',180),
               cases=ordinary or [dict(id='draft',file='draft.json')]),SUITE_SCHEMA)
    if len({c['id'] for c in cases})!=len(cases):raise AuthoringError('suite.invalid','Case IDs must be unique.')
    if sum(len(c.get('seeds',[DEFAULT_SEED])) for c in cases)>32:raise AuthoringError('query.bounds','A suite runs at most 32 scenarios.')


def put(document,value,previous=None):
    validate_suite(value);data=editor_data(document);items=data.setdefault('test_suites',[])
    if any(s['id']==value['id'] and s['id']!=previous for s in items):raise AuthoringError('suite.exists','That suite ID already exists.')
    if previous is not None and not any(s['id']==previous for s in items):raise AuthoringError('suite.missing','This suite was removed; reopen its form.')
    if previous is None:
        if len(items)>=16:raise AuthoringError('query.bounds','Use at most 16 project suites.')
        items.append(copy.deepcopy(value))
    else:items[next(i for i,s in enumerate(items) if s['id']==previous)]=copy.deepcopy(value)
    with document.command('Edit test suite'):editor_commit(document,data)


def remove(document,identity):
    data=editor_data(document);data['test_suites']=[s for s in data.get('test_suites',[]) if s['id']!=identity]
    with document.command('Remove test suite'):editor_commit(document,data)


def _scenario_paths(scenario,base):
    scenario=copy.deepcopy(scenario)
    if 'checkpoint' in scenario:scenario['checkpoint']['file']=str((Path(base)/scenario['checkpoint']['file']).resolve())
    return scenario


def _fixture_paths(fixture,base):
    fixture=copy.deepcopy(fixture);check_batch(fixture)
    for op in fixture['operations']:
        if op['op'] in IMPORT_OPERATIONS:op['file']=str((Path(base)/op['file']).resolve())
    return fixture


def import_suite(path,identity,name=None):
    """Import definitions, resolving explicit external resources at their source."""
    path=Path(path).resolve();raw=read_json(path);check(raw,SUITE_SCHEMA)
    value=dict(id=identity,name=name or path.stem,max_seconds=raw.get('max_seconds',180),cases=[])
    for source in raw['cases']:
        case={k:copy.deepcopy(v) for k,v in source.items() if k not in ('file','fixture')}
        scenario_path=(path.parent/source['file']).resolve()
        case['scenario']=_scenario_paths(read_json(scenario_path),scenario_path.parent)
        if source.get('fixture'):
            fixture_path=(path.parent/source['fixture']).resolve()
            case['fixture_commands']=_fixture_paths(read_json(fixture_path),fixture_path.parent)
        value['cases'].append(case)
    validate_suite(value,runnable=True);return value


def scaffold(document,kind,target=None,at=None,checkpoint=None):
    """Generate honest ordinary-input starting points, never a forged success.

    Objective cases need the author to add the route before their assertion.
    Navigation can fail on blocked paths and is only verified by a native run.
    """
    a=document.adventure or {};steps=[dict(op='pages')]
    if kind=='entrance':
        if not any(e['id']==target for m in a.get('maps',[]) for e in m.get('entrances',[])):
            raise AuthoringError('object.missing','Choose an existing entrance.')
        steps.extend([dict(op='walk',entrance=target),dict(op='assert',phase='entry')])
    elif kind in ('map','world'):
        from world_editing import all_worlds
        objects=a.get('maps',[]) if kind=='map' else all_worlds(a)
        if not any(o['id']==target for o in objects):raise AuthoringError('object.missing','Choose an existing '+kind+'.')
        steps.append(dict(op='walk',**{kind:target},at=list(at or [0,0])))
        expected={kind:target}
        if kind=='world':expected['world_at']=list(at or [0,0])
        else:
            # Towns compile into world sectors. Assert their logical world
            # location, not a runtime sector name that authors cannot see.
            world=next((w for w in all_worlds(a) if target in w.get('cities',[])),None)
            if world:
                scene=next(m for m in objects if m['id']==target)
                expected=dict(world=world['id'],world_at=[2*o+p for o,p in zip(scene['origin'],at or [0,0])])
        steps.append(dict(op='assert',**expected))
    elif kind=='objective':
        if not any(o['id']==target for o in a.get('objectives',[])):raise AuthoringError('object.missing','Choose an existing objective.')
        steps.append(dict(op='assert',objective=target,status='complete'))
    elif kind!='start':raise AuthoringError('suite.invalid','Unknown starter scenario kind.')
    steps.append(dict(op='checkpoint',name='finish'))
    result=dict(format='btp-author-scenario-v1',max_ticks=12000,steps=steps)
    if checkpoint:result['checkpoint']=pin_checkpoint(checkpoint)
    check(result,SCHEMA);return result


def export_suite(document,value,output,cancelled=lambda:False):
    """Create a portable, hash-pinned suite, refusing to overwrite any directory."""
    validate_suite(value,runnable=True);output=Path(output).resolve()
    if output.is_relative_to(document.root):raise AuthoringError('output.invalid','Export test artifacts outside the game project.')
    output.mkdir(parents=True,exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='btp-suite-stage-') as tmp:
        stage=Path(tmp);raw=dict(format='btp-author-suite-v1',max_seconds=value.get('max_seconds',180),cases=[])
        for source in value['cases']:
            cancelled_check(cancelled);case={k:copy.deepcopy(v) for k,v in source.items() if k in ('id','seeds','tags')}
            folder=stage/source['id'];folder.mkdir()
            if 'scenario' in source:
                path=folder/'scenario.json';path.write_bytes(encoded(_scenario_paths(source['scenario'],document.root)))
            else:path=(document.root/source['file']).resolve()
            case['file']=str(path)
            if 'fixture_commands' in source:
                path=folder/'fixture.json';path.write_bytes(encoded(_fixture_paths(source['fixture_commands'],document.root)));case['fixture']=str(path)
            elif source.get('fixture'):case['fixture']=str((document.root/source['fixture']).resolve())
            raw['cases'].append(case)
        source=stage/'suite.json';source.write_bytes(encoded(raw))
        inputs=capture_suite(source,output/'inputs',cancelled)
    inputs['source']='Project suite '+value['id']
    (output/'manifest.json').write_bytes(encoded(dict(format='btp-editor-suite-export-v1',suite_id=value['id'],revision=revision(document),inputs=inputs)))
    return inputs


def coverage(document,suite,base_dir,report=None,cancelled=lambda:False):
    """Never treat a dependency or an old/unrun case as observed coverage."""
    check(suite,SUITE_SCHEMA);graph=Graph(document,cancelled);cases=[];declared=set()
    report=report or {};same=report.get('revision')==revision(document)
    observed=set(report.get('coverage',{}).get('events',[])) if same else set()
    transitions=[b for r in report.get('runs',[]) for b in r.get('coverage',{}).get('branches',[])] if same else []
    for case in suite['cases']:
        cancelled_check(cancelled);path=Path(base_dir)/case['file'];scenario=read_json(path);check(scenario,SCHEMA)
        fixture=read_json(Path(base_dir)/case['fixture']) if case.get('fixture') else None
        parents,unknown=graph.walk(scenario,fixture);events=sorted(p.split('/',1)[1] for p in parents if p.startswith('adventure.events/'))
        declared.update(events)
        result=report.get('case_results',{}).get(case['id'],{}) if same else {}
        runs=[r for r in report.get('runs',[]) if r.get('case')==case['id']] if same else []
        cases.append(dict(id=case['id'],status=result.get('status','not_run'),declared_events=events,dependencies=sorted(parents),unknown=unknown,
                          diagnostics=[d for r in runs for d in r.get('diagnostics',[])],
                          observed_events=sorted({e for r in runs for e in r.get('coverage',{}).get('events',[])})))
    events=[dict(id=e['id'],declared=e['id'] in declared,observed=e['id'] in observed) for e in (document.adventure or {}).get('events',[])]
    branches=[dict(event=e['id'],branch=b,target=t,observed=any(v.get('event')==e['id'] and v.get('branch')==b and v.get('target')==t for v in transitions))
              for e in (document.adventure or {}).get('events',[]) for b,t in edges(e)]
    return dict(format='btp-suite-coverage-v1',revision=revision(document),report_revision=report.get('revision'),
                historical=bool(report and not same),basis='Observed ordinary input in this retained run only. Dependencies are conservative; unvisited branches and unknown control remain unverified.',
                cases=cases,events=events,branches=branches,unvisited_events=[e['id'] for e in events if not e['observed']])


def run(document,value,output,runner,settings=None,case_ids=None,cancelled=lambda:False):
    output=Path(output);inputs=export_suite(document,value,output,cancelled)
    path=verify_inputs(output,inputs);suite=read_json(path)
    result=run_suite(document,suite,path.parent,output/'runs',runner,settings,cancelled=cancelled,case_ids=case_ids)
    verify_inputs(output,inputs)
    report=read_json(Path(result['report']));inventory=coverage(document,suite,path.parent,report,cancelled=lambda:False)
    # Cancelled native runs still have useful partial evidence. Do not lose it
    # by cancelling the final bounded coverage summary as well.
    inventory.update(suite_id=value['id'],suite_definition=value,report=result['report'],inputs=inputs)
    (output/'coverage.json').write_bytes(encoded(inventory))
    return dict(result,coverage=str(output/'coverage.json'),inventory=inventory)


def inspect(document,value,output,cancelled=lambda:False):
    """Retain a dependency inventory without claiming any scenario ran."""
    output=Path(output);inputs=export_suite(document,value,output,cancelled);path=verify_inputs(output,inputs)
    inventory=coverage(document,read_json(path),path.parent,cancelled=cancelled)
    inventory.update(suite_id=value['id'],suite_definition=value,inputs=inputs)
    (output/'coverage.json').write_bytes(encoded(inventory))
    return dict(status='not_run',coverage=str(output/'coverage.json'),inventory=inventory)
