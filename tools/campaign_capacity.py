#!/usr/bin/env python3
"""Reproduce a bounded, connected campaign for capacity and save measurements.

This is a generated test campaign, not a new authored story release. Every
contract has a town, battlefield, survey, real combat, payment and repair loop.
It uses the independent example's assets, so no DOS data is required.
"""
import argparse
import copy
import json
from pathlib import Path
import tempfile
from editor_model import ProjectDocument, create_project, encoded
from world_editing import upgrade

ROOT = Path(__file__).resolve().parents[1]


def campaign(contracts=20, version=3):
    base = ProjectDocument(ROOT/'examples/beacon-demo', ROOT/'build/btp-project')
    a = copy.deepcopy(base.adventure)
    upgrade(a)
    a.update(format=f'btp-adventure-v{version}', schema_version=version,
             maps=[], events=[], encounters=[], flags=[], objectives=[], variables=[], regions=[])
    end, fault = 'capacity:end', 'capacity:fault'
    a['events'] = [dict(id=end, op='end'), dict(id=fault, op='finish', text='Contract failed. Restore a checkpoint to try again.')]
    a['jigsaws'] = [dict(id='capacity:plain', name='Open countryside', rows=[['beacon:grass']*8 for _ in range(8)])]
    a['worlds'] = [dict(id=f'capacity:planet-{i}', name=f'Frontier {i+1}',
                        pieces=[['capacity:plain']*64 for _ in range(64)], patches=[], cities=[]) for i in range(2)]
    for i in range(contracts):
        prefix = f'capacity:c{i+1:02d}-'
        ident = lambda name: prefix+name
        def event(name, op, **fields):
            a['events'].append(dict(id=ident(name), op=op, **fields))
        def objective(name, key, next):
            event(name, 'objective', objective=ident(key), state='complete', next=ident(next), failure=fault)
        def variable(name, key, next):
            event(name, 'variable', variable=ident(key), action='add', value=1, once=1, next=ident(next), failure=fault)
        for kind in ('town', 'field'):
            rows = [['beacon:grass']*32 for _ in range(24)]
            for y in range(10,15): rows[y][2:30] = ['beacon:road']*28
            for y in range(3,7): rows[y][5:10] = ['beacon:wall']*5
            for y in range(17,21): rows[y][22:26] = ['beacon:trees']*4
            n = i//2
            scene = dict(id=ident(kind), name=f'Contract {i+1} '+kind, origin=[64+(n%6)*64,64+(n//6)*64],
                         rows=rows, overlays=[], entrances=[])
            if kind == 'town':
                scene['entrances'] = [dict(id=ident('office'), name='Contract office', at=[12,24], event=ident('menu'))]
                a['worlds'][i%2]['cities'].append(scene['id'])
            a['maps'].append(scene)
        for key in ('survey', 'patrol'):
            a['variables'].append(dict(id=ident(key+'-count'), name=f'Contract {i+1} {key} count', type='counter', initial=0, maximum=1))
            a['objectives'].append(dict(id=ident(key), title=f'Contract {i+1}: {key}', text=f'Complete the {key} at frontier outpost {i+1}.', initial='active'))
        a['encounters'].append(dict(id=ident('patrol-fight'), map=ident('field'), party_at=[24,26],
            enemies=[dict(kind='mech', definition='beacon:warden', at=[38,26])]))
        event('brief', 'say', text=f'Frontier contract {i+1}. Survey the relay records, clear its hostile Warden, then take payment and travel onward.', next=ident('menu'))
        event('menu', 'choice', text=f'Outpost {i+1}: survey before engaging the patrol.', options=[
            dict(label='Survey relay', next=ident('survey-check')), dict(label='Engage patrol', next=ident('launch-check')),
            dict(label='Leave office', next=end)], cancel=end)
        event('survey-check', 'check', match='all', conditions=[dict(kind='variable', id=ident('survey-count'), compare='eq', value=0)],
              then=ident('survey-count-up'), **{'else':ident('survey-report')})
        variable('survey-count-up', 'survey-count', 'survey-complete')
        objective('survey-complete', 'survey', 'survey-report')
        event('survey-report', 'say', text=f'Relay {i+1} surveyed. The patrol blocks the next leg of the route.', next=ident('menu'))
        event('launch-check', 'check', match='all', conditions=[dict(kind='objective', id=ident('survey'), compare='eq', value='complete')],
              then=ident('depart'), **{'else':ident('survey-needed')})
        event('survey-needed', 'say', text='Survey the relay first to locate the patrol.', next=ident('menu'))
        event('depart', 'transfer', map=ident('field'), at=[24,26], next=ident('battle'), failure=fault)
        event('battle', 'battle', encounter=ident('patrol-fight'), win=ident('patrol-count-up'), loss=fault, flee=ident('retreat'), failure=fault)
        variable('patrol-count-up', 'patrol-count', 'patrol-complete')
        objective('patrol-complete', 'patrol', 'payment')
        event('payment', 'reward', credits=100, next=ident('repair'), failure=fault)
        event('repair', 'repair', cost=0, next=ident('rearm'), unchanged=ident('rearm'), failure=fault)
        event('rearm', 'rearm', cost=0, next=ident('heal'), unchanged=ident('heal'), failure=fault)
        event('heal', 'heal', cost=0, next=ident('report'), unchanged=ident('report'), failure=fault)
        event('report', 'say', text=f'Patrol {i+1} defeated. Payment is 100 credits; the outpost services your lance before the next contract.', next=ident('onward'))
        next_map = f'capacity:c{i+2:02d}-town' if i+1<contracts else ident('town')
        next_event = f'capacity:c{i+2:02d}-brief' if i+1<contracts else 'capacity:finish'
        event('onward', 'transfer', map=next_map, at=[12,24], next=next_event, failure=fault)
        event('retreat', 'transfer', map=ident('town'), at=[12,24], next=ident('withdrawn'), failure=fault)
        event('withdrawn', 'say', text='You withdrew. The contract is still open at this outpost.', next=end)
    a['events'].append(dict(id='capacity:finish', op='finish', text='The frontier network is secure. All contracts completed.'))
    a['start'] = dict(map='capacity:c01-town', at=[12,24], event='capacity:c01-brief', credits=2000,
                      party=[dict(person='beacon:rowan', mech='workshop:rook'), dict(person='beacon:mira', mech='workshop:kite')])
    return a


def scenario(contracts=20):
    steps=[]
    for i in range(contracts):
        prefix=f'capacity:c{i+1:02d}-'
        steps.extend([dict(op='pages'), dict(op='choose', label='Survey relay'), dict(op='pages'),
                      dict(op='choose', label='Engage patrol'), dict(op='battle', control='computer'),
                      dict(op='assert', objective=prefix+'patrol', status='complete', credits=2000+100*(i+1)),
                      dict(op='checkpoint')])
    steps.extend([dict(op='pages'),dict(op='assert',phase='complete')])
    return dict(format='btp-author-scenario-v1',max_ticks=120000,steps=steps)


def generate(output, validator, contracts=20, version=3, verify=False):
    from campaign_source import convert, build
    output=Path(output).resolve()
    if output.exists():raise ValueError('Choose a new output directory; existing work is preserved.')
    output.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix='.capacity-',dir=output) as temp:
        doc=create_project(ROOT/'examples/beacon-demo',Path(temp)/'game','frontier-circuit','Frontier Circuit',validator)
        doc.replace_adventure(campaign(contracts,version));doc.save()
        source=convert(doc,output/'source')
    first=build(source,output/'game');second=build(source,output/'rebuilt')
    assert first['fingerprint']==second['fingerprint'] and first['files']==second['files']
    route=scenario(contracts);(output/'scenario.json').write_bytes(encoded(route))
    report=dict(contracts=contracts,planets=2,maps=len(source.adventure['maps']),events=len(source.adventure['events']),
        variables=2*contracts,objectives=2*contracts,fingerprint=first['fingerprint'],reproducible=True,
        source_files=len(source.source.disk),source_bytes=sum(map(len,source.source.disk.values())))
    if verify:
        from authoring_scenarios import run
        report['scenario']=run(source,route,output/'scenario',ROOT/'build/btp-author-playtest',{})
    (output/'report.json').write_bytes(encoded(report));return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--validator',type=Path,default=ROOT/'build/btp-project');p.add_argument('--contracts',type=int,default=20)
    p.add_argument('--verify',action='store_true');args=p.parse_args()
    if not 1<=args.contracts<=32:p.error('Choose 1..32 contracts.')
    report=generate(args.output,args.validator,args.contracts,verify=args.verify)
    print(json.dumps(report,indent=2));return int(report.get('scenario',{}).get('status','passed')!='passed')


if __name__=='__main__':raise SystemExit(main())
