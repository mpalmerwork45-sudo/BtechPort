"""Bounded graph lint plus native whole-party navigation/deployment probes."""
from collections import deque
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

from authoring_contract import API_VERSION,AuthoringError,diagnostic
from authoring_service import revision
from editor_model import EditorError,encoded
from event_editing import edges


def region_roots(adventure):
    return [r[key] for r in adventure.get('regions',[]) for key in ('enter','leave') if key in r]


def graph_checks(document):
    a=document.adventure or {};events={e['id']:e for e in a.get('events',[])};diagnostics=[]
    graph={identity:[t for _,t in edges(e) if t in events] for identity,e in events.items()}
    roots=[a.get('start',{}).get('event')]+[e['event'] for m in a.get('maps',[]) for e in m['entrances']]+region_roots(a)
    reachable=set();queue=deque(r for r in roots if r in events)
    def add(code,message,identity,severity='warning',**fields):
        diagnostics.append(dict(code=code,severity=severity,message=message,object_id=identity,
            field_path='adventure.events/'+identity,location=None,**fields))
    while queue:
        current=queue.popleft()
        if current in reachable:continue
        reachable.add(current);queue.extend(graph[current])
    for identity,event in events.items():
        if identity not in reachable:add('event.unreachable','No route from the starting event, entrances or region triggers reaches this event.',identity)
        for branch,target in edges(event):
            if target not in events:add('event.branch_missing','Event branch '+branch+' refers to '+target+'.',identity,'error',branch=branch,target=target)
    # Find strongly connected components iteratively: a 256-node chain should
    # not depend on the host Python recursion limit.
    reverse={i:[] for i in graph}
    for i,targets in graph.items():
        for target in targets:reverse[target].append(i)
    seen=set();order=[]
    for root in graph:
        stack=[(root,False)]
        while stack:
            current,finish=stack.pop()
            if finish:order.append(current);continue
            if current in seen:continue
            seen.add(current);stack.append((current,True));stack.extend((t,False) for t in graph[current] if t not in seen)
    seen=set();cycles=[];yielding={'say','choice','shop','battle','picture','end','finish'}
    for root in reversed(order):
        if root in seen:continue
        component=set();stack=[root]
        while stack:
            current=stack.pop()
            if current in seen:continue
            seen.add(current);component.add(current);stack.extend(reverse[current])
        cyclic=len(component)>1 or root in graph[root]
        if not cyclic:continue
        cycles.append(sorted(component))
        if all(events[i]['op'] not in yielding for i in component):
            closed=all(t in component for i in component for t in graph[i])
            add('event.non_yielding_cycle' if closed else 'event.synchronous_cycle',
                'Synchronous event cycle can exhaust the runtime command budget before yielding.',min(component),
                'error' if closed and bool(component&reachable) else 'warning',events=sorted(component))
    lua=any(e['op']=='lua' for e in events.values())
    writes={e['flag'] for e in events.values() if e['op']=='flag' and e.get('value',0)>0 and e['id'] in reachable}
    for objective in a.get('objectives',[]):
        if 'initial' in objective:
            if objective['initial'] not in ('complete','failed') and not any(
                    e['id'] in reachable and e['op']=='objective' and e['objective']==objective['id'] and e['state']=='complete'
                    for e in events.values()):
                diagnostics.append(dict(code='objective.completion_missing',severity='warning',
                    message='No explicit reachable event completes this objective. Verify its intended failure-only or unfinished route.',
                    object_id=objective['id'],field_path='adventure.objectives/'+objective['id'],location=None))
            continue
        for field in ('active','complete'):
            if objective[field] not in writes:
                diagnostics.append(dict(code='objective.coverage_unknown' if lua else 'objective.flag_unset',severity='warning',
                    message=('No explicit reachable event sets this objective flag; Lua needs a scenario check.' if lua else 'No reachable flag event activates this objective state.'),
                    object_id=objective['id'],field_path='adventure.objectives/'+objective['id']+'/'+field,location=None))
    return dict(diagnostics=diagnostics,events=len(events),reachable_from_declared_roots=len(reachable),cycles=cycles,
        basis='Explicit event edges from start, entrances and region triggers; region access, conditions and Lua execution are not proven.')


def objective_access(document, findings):
    """Connect a sealed entrance to objectives available only through it.

    This is a warning over explicit graph edges and initial-party geometry.
    An opaque Lua writer prevents a definitive access claim.
    """
    a=document.adventure or {};events={e['id']:e for e in a.get('events',[])}
    if any(e['op']=='lua' for e in events.values()):return []
    blocked={p['object_id']:p for p in findings if p['code']=='entrance.unreachable'}
    if not blocked:return []
    roots=[a.get('start',{}).get('event')]+[door['event'] for m in a.get('maps',[]) for door in m['entrances'] if door['id'] not in blocked]+region_roots(a)
    def reach(roots):
        visited=set();queue=deque(r for r in roots if r in events)
        while queue:
            current=queue.popleft()
            if current in visited:continue
            visited.add(current);queue.extend(t for _,t in edges(events[current]) if t in events)
        return visited
    usable=reach(roots);result=[]
    for objective in a.get('objectives',[]):
        writers={e['id'] for e in events.values() if (
            e['op']=='objective' and e.get('objective')==objective['id'] and e.get('state')=='complete' if 'initial' in objective else
            e['op']=='flag' and e.get('flag')==objective['complete'] and e.get('value',0)>0)}
        if not writers or writers&usable:continue
        doors=[door['id'] for m in a.get('maps',[]) for door in m['entrances'] if door['id'] in blocked and reach([door['event']])&writers]
        if doors:result.append(dict(code='objective.inaccessible',severity='warning',object_id=objective['id'],
            field_path='adventure.objectives/'+objective['id'],location=blocked[doors[0]]['location'],blocked_entrances=doors,
            message='Every explicit completion route for this objective is behind an entrance unreachable by the initial formation. Check the doorway/path or provide another route.'))
    return result


def analyze(document,analyzer,settings=None,navigation=True,output=None):
    base=revision(document);static=graph_checks(document);problems=list(static['diagnostics']);native=None
    valid=True
    try:document.validate()
    except EditorError as exc:problems.append(diagnostic(exc));valid=False
    if valid and navigation and document.adventure:
        analyzer=Path(analyzer).resolve()
        if not analyzer.is_file():
            problems.append(dict(code='navigation.unavailable',severity='warning',message='Build btp-author-analyze for native navigation checks.',object_id=None,location=None))
        else:
            # Native checks receive the exact document including unsaved GUI
            # drafts. They never recover/write into the live project directory.
            with tempfile.TemporaryDirectory(prefix='btp-mission-check-') as temporary:
                folder=Path(temporary);document.stage(folder)
                command=[str(analyzer),'--project',str(folder)]
                for key,value in (settings or {}).items():
                    if key in ('data','dialogue-data','combat-data','world-data'):command.extend(['--'+key,str(Path(value).resolve())])
                try:
                    process=subprocess.run(command,capture_output=True,text=True,timeout=25)
                    if process.returncode:raise ValueError(process.stderr.strip()[:2000] or 'Native probe could not load gameplay dependencies.')
                    if len(process.stdout)>2*1024*1024:raise ValueError('Native probe exceeded its diagnostic budget.')
                    native=json.loads(process.stdout);problems.extend(native['diagnostics']);problems.extend(objective_access(document,native['diagnostics']))
                except (OSError,ValueError,subprocess.TimeoutExpired) as exc:
                    problems.append(dict(code='navigation.unavailable',severity='warning',message=str(exc),object_id=None,location=None))
    elif not navigation:
        problems.append(dict(code='navigation.not_run',severity='info',message='Static-only analysis requested; navigation and deployment were not checked.',object_id=None,location=None))
    document.unchanged_on_disk()
    report=dict(api_version=API_VERSION,status='failed' if any(p['severity']=='error' for p in problems) else 'checked',
        revision=base,project_id=document.manifest['package_id'],diagnostics=problems,graph=static,
        navigation=native,native_sha256=hashlib.sha256(Path(analyzer).read_bytes()).hexdigest() if native else None,
        coverage='Initial-party local geometry and explicit event graph. Later recruits, world-spanning routes, conditions and Lua require declared gameplay scenarios.')
    if output:
        output=Path(output).resolve()
        if output.is_relative_to(document.root):raise AuthoringError('output.invalid','Save analysis outside the game project.')
        output.parent.mkdir(parents=True,exist_ok=True)
        with output.open('xb') as stream:stream.write(encoded(report))
        report['report']=str(output)
    return report
