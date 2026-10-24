"""Source-linked observations of native BLD execution, separate from authored events.

Reads existing traces without running a campaign or altering the project. A
content fingerprint mismatch is an error, not evidence about the current edit.
Native C branches are explicitly unknown: this measures operation boundaries.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
import re
from editor_model import EditorError,ProjectDocument,encoded
from chi_bld import data,compiled


def edges(program,node):
    op=node['op'];nodes=program['nodes'];index=nodes.index(node)
    after=nodes[index+1]['id'] if index+1<len(nodes) else None
    if op in ('menu','dispatch'):return [(i,target) for i,target in enumerate(node['targets'])]
    if op=='jump':return [(0,node['target'])]
    if op=='event':return [(i,node[key]) for i,key in enumerate(('next','failure','cancel'))]
    if op in ('if','confirm','if_money','if_person_absent','if_skill','if_advanced_kit','if_medical_kit'):
        return [(0,after),(1,node['target'])]
    return []


def coverage(document,traces,cancel=None):
    if document.manifest.get('requires')!='chi-local-dos-1.03':raise EditorError('Open an imported CHI campaign for native script coverage.')
    fingerprint=re.search(r'SHA-256 ([0-9a-f]{64})',document.validate())
    if not fingerprint:raise EditorError('Native validation did not supply a content fingerprint.')
    programs=data(document)['programs'];by_slot={p['building']:p for p in programs}
    adapter_keys=set()
    if document.manifest.get('chi_bridge'):
        from chi_bridge import data as bridge_data
        adapter_keys={(call['program'],call['entry']) for call in bridge_data(document)['native_calls']}
    instructions=Counter();branches=Counter();entered=Counter();returned=Counter();outcomes=Counter();event_enter=Counter();event_return=Counter();faults=[];unknown=Counter();unmapped_branches=[];records=0;headers=[]
    declared_edges={(p['id'],n['id']):set(edges(p,n)) for p in programs for n in p['nodes'] if n['op']!='data'}
    layouts={}
    def layout(slot):
        if slot not in layouts:
            p=by_slot[slot]
            if document.manifest.get('chi_scripts'):
                rows=compiled(document,p['id'])['nodes']
                layouts[slot]={n['offset']:n['id'] for n in rows if n['opcode']}
            else:layouts[slot]={n['origin']:n['id'] for n in p['nodes'] if n['op']!='data'}
        return layouts[slot]
    for file in traces:
        file=Path(file)
        if file.stat().st_size>128*1024*1024:raise EditorError('BLD trace exceeds 128 MiB: '+str(file))
        with file.open(encoding='utf-8') as stream:
            try:header=json.loads(next(stream))
            except (StopIteration,ValueError) as error:raise EditorError('Missing BLD trace header: '+str(file)) from error
            if not isinstance(header,dict) or header.get('format')!='btp-bld-trace-v1' or header.get('kind')!='header':raise EditorError('Not a native BLD trace: '+str(file))
            if header.get('content_digest')!=fingerprint[1]:raise EditorError('BLD trace belongs to a different content revision. Open its retained Play snapshot or record this revision again.')
            headers.append(dict(file=str(file),continuation=bool(header.get('continuation'))))
            for line_no,line in enumerate(stream,2):
                if cancel and cancel.is_set():raise EditorError('Coverage cancelled.')
                try:
                    row=json.loads(line);slot=row['building'];kind=row['kind'];detail=row['detail'];offset=row['from'];destination=row['to']
                    if type(slot) is not int or slot not in by_slot or kind not in ('instruction','branch','native-enter','native-return','resume','fault','event-enter','event-return','bridge-outcome'):
                        raise ValueError('invalid observation kind or building')
                    if any(type(v) is not int or not 0<=v<=65535 for v in (detail,offset,destination)):
                        raise ValueError('invalid observation value')
                    p=by_slot[slot];locations=layout(slot);node=locations.get(offset);target=locations.get(destination)
                    if row.get('resource')!=p['resource']:raise ValueError('resource does not match building')
                    if row.get('program') not in (None,p['id']) or row.get('node') not in (None,node) or row.get('target') not in (None,target):
                        raise ValueError('source label does not match compiled offset')
                except (ValueError,KeyError,TypeError) as error:raise EditorError(f'{file}:{line_no}: invalid BLD observation ({error})') from error
                records+=1
                if not node:
                    unknown[kind]+=1
                    if kind=='fault':faults.append(dict(file=str(file),line=line_no,program=p['id'],offset=offset,error=detail))
                    continue
                key=(p['id'],node)
                if kind=='instruction':instructions[key]+=1
                elif kind=='branch':
                    # Native dispatch uses a signed byte and can reach outside
                    # its declared forward table. Retain unexpected edges as
                    # unresolved evidence instead of losing them from totals.
                    if (detail,target) not in declared_edges[key]:
                        unknown['undeclared-branch']+=1
                        unmapped_branches.append(dict(file=str(file),line=line_no,program=p['id'],node=node,choice=detail,target=target,offset=offset,destination=destination))
                    else:branches[(*key,detail,target)]+=1
                elif kind=='native-enter':entered[key]+=1
                elif kind=='native-return':returned[key]+=1
                elif kind=='bridge-outcome':outcomes[(*key,detail)]+=1
                elif kind=='event-enter':event_enter[key]+=1
                elif kind=='event-return':event_return[(*key,detail)]+=1
                elif kind=='fault':faults.append(dict(file=str(file),line=line_no,program=p['id'],node=node,offset=offset,error=detail))
    result=[]
    for p in programs:
        nodes=[]
        for n in p['nodes']:
            if n['op']=='data':continue
            key=(p['id'],n['id'])
            node=dict(id=n['id'],op=n['op'],executions=instructions[key],
                field_path=f"$.programs[{p['id']}].nodes[{n['id']}]",
                branches=[dict(choice=choice,target=target,executions=branches[(*key,choice,target)]) for choice,target in edges(p,n)])
            if n['op']=='native':
                node['native']=dict(entered=entered[key],returned=returned[key],internal_branches='unknown')
                if key in adapter_keys:node['native']['bridge_outcomes']={name:outcomes[(*key,i)] for i,name in enumerate(('success','failure','cancel'))}
            if n['op']=='event':node['quest']=dict(entered=event_enter[key],returns={name:event_return[(*key,i)] for i,name in enumerate(('success','failure','cancel'))})
            nodes.append(node)
        all_edges=[b for n in nodes for b in n['branches']]
        result.append(dict(id=p['id'],name=p['name'],resource=p['resource'],nodes=nodes,
            instructions=dict(declared=len(nodes),observed=sum(n['executions']>0 for n in nodes)),
            branches=dict(declared=len(all_edges),observed=sum(b['executions']>0 for b in all_edges))))
    return dict(format='btp-chi-coverage-v1',content_digest=fingerprint[1],traces=headers,observations=records,
        programs=result,faults=faults,unresolved_observations=dict(unknown),unmapped_branches=unmapped_branches,
        limitations=['Execution observations do not establish behavioral correctness.',
            'Native C operation internals are unknown; enter/return counts measure only their BLD boundaries.',
            'Unvisited branches are not passed tests. A continued trace does not claim its discarded bootstrap executed.'])


def main():
    from app_runtime import binary
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('project',type=Path);p.add_argument('traces',type=Path,nargs='+');p.add_argument('--output',type=Path)
    a=p.parse_args()
    try:result=coverage(ProjectDocument(a.project,binary('btp-project')),a.traces)
    except (EditorError,OSError) as error:p.exit(1,str(error)+'\n')
    if a.output:
        a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_bytes(encoded(result))
        print(f"Observed {result['observations']} native BLD records across {len(result['programs'])} programs. Report: {a.output}")
    else:print(json.dumps(result,indent=2))


if __name__=='__main__':main()
