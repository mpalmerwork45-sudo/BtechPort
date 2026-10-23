"""Conservative scenario suggestions for an exact, retained change review.

This is a dependency inventory, not a symbolic player. We follow every explicit
branch and every trigger on a reachable map. Opaque control requests a full suite;
absence of a known dependency is never test evidence.
"""
from collections import defaultdict, deque
import copy
import hashlib
import os
from pathlib import Path

from authoring_contract import AuthoringError, IMPORT_OPERATIONS, check, check_batch, read_json
from authoring_scenarios import DEFAULT_SEED, SCHEMA, SUITE_SCHEMA
from authoring_service import changed_objects
from editor_dependencies import TEXT_KEYS
from editor_model import encoded, child
from adventure_editing import OPS
from world_editing import all_worlds

FORMAT='btp-review-selection-v1'
MAX_NODES=16384
MAX_EDGES=262144
MAX_INPUT_BYTES=64*1024*1024
MAX_INPUT_FILES=256
MAX_REASONS=8
MAX_DEPENDENCIES=128


def cancelled_check(cancelled):
    if cancelled():raise AuthoringError('job.cancelled','Scenario dependency analysis cancelled; no tests were run.')


def capture_suite(source, folder, cancelled=lambda:False):
    """Pin suite, scenarios, saves, fixture commands and their imported bytes.

    Preserve import basenames because image conversion may derive names from
    them. All executable paths point into the retained directory; external
    edits/deletions cannot silently alter a previously displayed selection.
    """
    source=Path(source).resolve();folder=Path(folder).resolve();folder.mkdir()
    captured={};files=[];total=0;rewritten=0
    def capture(path,limit=16*1024*1024):
        nonlocal total
        cancelled_check(cancelled);path=Path(path).resolve()
        if path in captured:return captured[path]
        if len(captured)>=MAX_INPUT_FILES:raise AuthoringError('query.bounds','Suite inputs exceed 256 source files.')
        try:
            with path.open('rb') as stream:data=stream.read(limit+1)
        except OSError as exc:raise AuthoringError('suite.input_unavailable',str(exc)) from exc
        total+=len(data)
        if len(data)>limit or total>MAX_INPUT_BYTES:raise AuthoringError('query.bounds','Suite inputs exceed the per-file or 64 MiB total budget.')
        target=folder/'source'/str(len(files))/path.name;target.parent.mkdir(parents=True);target.write_bytes(data)
        files.append(dict(file=str(target.relative_to(folder)),source=str(path),sha256=hashlib.sha256(data).hexdigest(),bytes=len(data)))
        captured[path]=target;return target
    suite=read_json(capture(source));check(suite,SUITE_SCHEMA)
    ids=[c['id'] for c in suite['cases']]
    if len(ids)!=len(set(ids)):raise AuthoringError('request.invalid','Suite case IDs must be unique.')
    def write(path,value):
        nonlocal rewritten
        data=encoded(value);rewritten+=len(data)
        if len(data)>16*1024*1024 or rewritten>MAX_INPUT_BYTES:
            raise AuthoringError('query.bounds','Runnable suite copies exceed the per-file or 64 MiB rewrite budget.')
        path.write_bytes(data)
        files.append(dict(file=str(path.relative_to(folder)),sha256=hashlib.sha256(data).hexdigest(),bytes=len(data)))
    for case in suite['cases']:
        cancelled_check(cancelled)
        directory=folder/'cases'/case['id'];directory.mkdir(parents=True)
        scenario_source=(source.parent/case['file']).resolve()
        scenario=read_json(capture(scenario_source));check(scenario,SCHEMA)
        if 'checkpoint' in scenario:
            if 'seeds' in case:raise AuthoringError('request.invalid','Checkpoint cases keep saved RNG; remove the seed sweep.')
            save=capture(scenario_source.parent/scenario['checkpoint']['file'])
            scenario['checkpoint']['file']=os.path.relpath(save,directory)
        seeds=case.get('seeds',[])
        if len(seeds)!=len(set(seeds)):raise AuthoringError('request.invalid','A case repeats a seed.')
        write(directory/'scenario.json',scenario);case['file']='cases/'+case['id']+'/scenario.json'
        if case.get('fixture'):
            fixture_source=(source.parent/case['fixture']).resolve()
            fixture=read_json(capture(fixture_source));check_batch(fixture)
            if fixture['expected_revision']!='new':raise AuthoringError('revision.conflict','Suite fixtures require expected_revision "new".')
            for op in fixture['operations']:
                if op['op'] in IMPORT_OPERATIONS:op['file']=os.path.relpath(capture(fixture_source.parent/op['file']),directory)
            write(directory/'fixture.json',fixture);case['fixture']='cases/'+case['id']+'/fixture.json'
    runs=sum(len(c.get('seeds',[0])) for c in suite['cases'])
    if runs>32:raise AuthoringError('query.bounds','A suite runs at most 32 scenarios; split larger studies.')
    write(folder/'suite.json',suite)
    return dict(suite='inputs/suite.json',source=str(source),files=files,bytes=total,retained_bytes=total+rewritten)


def verify_inputs(folder, inputs):
    """Only retained bytes are runnable; the original paths are provenance."""
    root=Path(folder)/'inputs';total=0
    if len(inputs['files'])>MAX_INPUT_FILES+33:raise AuthoringError('query.bounds','Too many retained suite inputs.')
    for item in inputs['files']:
        path=child(root,item['file']);total+=item['bytes']
        if total>2*MAX_INPUT_BYTES or item['bytes']>16*1024*1024:
            raise AuthoringError('query.bounds','Retained suite inputs exceed their byte budget.')
        try:
            with path.open('rb') as stream:data=stream.read(item['bytes']+1)
        except OSError as exc:raise AuthoringError('selection.changed','Retained suite input is unavailable: '+item['file']) from exc
        if len(data)!=item['bytes'] or hashlib.sha256(data).hexdigest()!=item['sha256']:
            raise AuthoringError('selection.changed','Retained suite input changed: '+item['file']+'. Load the suite again.')
    return child(Path(folder),inputs['suite'])


class Graph:
    def __init__(self, document, cancelled=lambda:False):
        self.document=document;self.nodes={};self.ids=defaultdict(set);self.links=defaultdict(set)
        self.unknown={};self.edges=0;self.cancelled=cancelled
        a=document.adventure or {}
        for section in ('content','adventure','art'):
            for collection,values in (getattr(document,section) or {}).items():
                if not isinstance(values,list):continue
                for item in values:
                    if isinstance(item,dict) and 'id' in item:
                        self.add(section+'.'+collection+'/'+item['id'],item)
        if 'world' in a:self.add('adventure.world',a['world'])
        # Script bodies are deliberately opaque, even when a string happens to
        # resemble a known ID. Their declared continuations are still followed.
        for script in document.manifest.get('scripts',[]):
            node='scripts/'+script['id'];self.add(node,script);self.unknown[node]='Lua script: '+script['id']
        for scene in a.get('maps',[]):
            node='adventure.maps/'+scene['id']
            for entrance in scene.get('entrances',[]):self.ids[entrance['id']].add(node)
        self.tile_keys={t.get('key'):t['id'] for t in a.get('tiles',[]) if t.get('key')}
        for node,value in list(self.nodes.items()):
            cancelled_check(cancelled)
            for target in self.references(value):self.link(node,target)
            if node.startswith('adventure.events/'):
                if value.get('op')=='lua' or value.get('op') not in OPS:self.unknown[node]='Opaque event control: '+value['id']
        # Native movement may encounter any entrance/region on its map, and a
        # composed world contains every town and shared jigsaw, including the
        # terrain surrounding town edges. Treat those as possible dependencies.
        for collection,parent in [('regions','map'),('encounters','map'),('combat_groups','encounter'),('combat_hooks','encounter')]:
            for item in a.get(collection,[]):
                for root in self.ids.get(item.get(parent),()):self.link(root,'adventure.'+collection+'/'+item['id'])
        for world in all_worlds(a):
            for city in world.get('cities',[]):
                for root in self.ids.get(city,()):
                    for target in self.ids.get(world['id'],()):self.link(root,target)

    def add(self,node,value):
        if len(self.nodes)>=MAX_NODES:raise AuthoringError('impact.bounds','Dependency graph exceeds 16,384 objects.')
        self.nodes[node]=value;self.ids[value['id']].add(node)

    def link(self,source,target):
        if target not in self.links[source]:
            if self.edges>=MAX_EDGES:raise AuthoringError('impact.bounds','Dependency graph exceeds 262,144 edges.')
            self.links[source].add(target);self.edges+=1

    def references(self,value):
        result=set();pending=[(value,None)]
        while pending:
            item,key=pending.pop()
            if isinstance(item,dict):
                pending.extend((v,k) for k,v in item.items() if k not in TEXT_KEYS and k not in ('frames','pixels','palette'))
            elif isinstance(item,list):pending.extend((v,key) for v in item)
            elif isinstance(item,str):
                identity=item[8:] if item.startswith('package:') else item
                result.update(self.ids.get(identity,()))
                if key=='rows' and self.document.adventure.get('schema_version')==1:
                    for char in set(item):result.update(self.ids.get(self.tile_keys.get(char),()))
        return result

    def walk(self,scenario,fixture):
        start=copy.deepcopy((self.document.adventure or {}).get('start',{}));unknown=[]
        if fixture:
            if all(op['op']=='start.set' for op in fixture['operations']):
                for op in fixture['operations']:start.update(op['changes'])
            else:unknown.append('Fixture changes more than the starting state; its possible dependencies are unknown.')
        roots=self.references(start)|self.references(scenario['steps'])
        # Bindings apply to every scene. They may select images without unit IDs.
        roots.update(self.references((self.document.art or {}).get('bindings',[])))
        if 'checkpoint' in scenario:unknown.append('Saved checkpoint state is opaque to this static inventory; the native loader still validates it.')
        if 'expected_revision' in scenario:unknown.append('Scenario pins an exact content revision; any change may invalidate its setup.')
        if any(s['op']=='input' for s in scenario['steps']):unknown.append('Raw input may open menus or navigate outside the declared route.')
        if self.document.manifest.get('requires')!='none':unknown.append('Original-game dependencies are external to the retained package.')
        parents={node:None for node in sorted(roots)};queue=deque(parents)
        while queue:
            cancelled_check(self.cancelled);node=queue.popleft()
            if node in self.unknown:unknown.append(self.unknown[node])
            for target in sorted(self.links[node]):
                if target not in parents:parents[target]=node;queue.append(target)
        return parents,sorted(set(unknown))


def analyse(before,after,suite,base_dir,cancelled=lambda:False):
    """Compare actual semantic diffs with both sides' reachable references."""
    changes=changed_objects(before,after);graphs={};global_paths=[];editor_paths=[];unknown=[]
    for side,doc in [('before',before),('after',after)]:
        try:graphs[side]=Graph(doc,cancelled)
        except AuthoringError as exc:
            if exc.diagnostic['code']!='impact.bounds':raise
            unknown.append(str(exc))
    known=set().union(*(set(g.nodes) for g in graphs.values()))
    for change in changes:
        path=change['path']
        if path.startswith('editor.'):editor_paths.append(path)
        elif path not in known:global_paths.append(path)
    cases=[]
    for case in suite['cases']:
        cancelled_check(cancelled)
        scenario=read_json(Path(base_dir)/case['file']);check(scenario,SCHEMA)
        fixture=read_json(Path(base_dir)/case['fixture']) if case.get('fixture') else None
        dependencies=set();reasons=[];uncertain=list(unknown)
        for path in global_paths:reasons.append(dict(path=path,basis='Shared package configuration, collection order or unclassified runtime data.'))
        for side,graph in graphs.items():
            parents,issues=graph.walk(scenario,fixture);uncertain.extend(issues);dependencies.update(parents)
            for change in changes:
                path=change['path']
                if path not in parents:continue
                chain=[];node=path
                while node is not None:chain.append(node);node=parents[node]
                reasons.append(dict(path=path,side=side,via=list(reversed(chain))[:24],chain_length=len(chain)))
        uncertain=sorted(set(uncertain));paths=sorted(dependencies)
        cases.append(dict(id=case['id'],tags=case.get('tags',[]),classification='unknown' if uncertain else 'affected' if reasons else 'no_known_dependency',
            reasons=reasons[:MAX_REASONS],reason_count=len(reasons),unknown=uncertain[:16],unknown_count=len(uncertain),
            dependencies=paths[:MAX_DEPENDENCIES],dependency_count=len(paths),
            seeds=case.get('seeds',[scenario.get('seed',DEFAULT_SEED)]) if 'checkpoint' not in scenario else [],
            checkpoint=scenario.get('checkpoint'),test_status='not_run'))
    incomplete=any(c['classification']=='unknown' for c in cases)
    suggested=[c['id'] for c in cases if incomplete or c['classification']=='affected']
    return dict(format=FORMAT,status='analysed',cases=cases,suggested=suggested,full_suite_recommended=incomplete,
        changes=[c['path'] for c in changes],editor_only_changes=editor_paths,
        bounds=dict(nodes=MAX_NODES,edges=MAX_EDGES,reasons_per_case=MAX_REASONS,listed_dependencies_per_case=MAX_DEPENDENCIES),
        basis='Conservative explicit references on both revisions; all reachable branches, map triggers and whole composed worlds. '
            'No path execution or Lua interpretation. No known dependency does not mean unaffected or passed. '
            'Any opaque case recommends the full suite. Changes to shared configuration select every case.')
