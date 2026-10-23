"""Independent regression-selection fixture: isolated sites and two planets."""
import copy
import json
from pathlib import Path

from editor_model import encoded
from authoring_service import revision
from world_route_demo import create as create_world,journey

ROOT=Path(__file__).resolve().parents[1]


def create(folder,tool):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    doc=create_world(folder/'game',tool);a=copy.deepcopy(doc.adventure)
    a['tiles'].append(dict(a['tiles'][0],id='survey:yard-grass'))
    for name in ('yard','range'):
        a['maps'].append(dict(id='survey:'+name,name=name.title(),origin=[0,0],
            rows=[['survey:yard-grass' if name=='yard' else 'beacon:grass']*16 for _ in range(16)],overlays=[],entrances=[]))
        a['events'].append(dict(id='survey:'+name+'-welcome',op='say',text='Inspect the '+name+'.',next='survey:end'))
    doc.replace_adventure(a);doc.save()
    suite=dict(format='btp-author-suite-v1',cases=[])
    for name in ('yard','range'):
        fixture=dict(api_version=1,request_id='start-'+name,project_id=doc.manifest['package_id'],expected_revision='new',
            label='Start at the '+name,scope=['*'],operations=[dict(op='start.set',changes=dict(map='survey:'+name,
                at=[16,20],event='survey:'+name+'-welcome',party=[dict(person='survey:pilot-0',mech='workshop:rook')]))])
        (folder/(name+'.commands.json')).write_bytes(encoded(fixture))
        scenario=dict(format='btp-author-scenario-v1',steps=[dict(op='pages'),dict(op='walk',map='survey:'+name,at=[24,20]),
            dict(op='assert',map='survey:'+name,phase='exploration',formation='compact'),dict(op='checkpoint')])
        (folder/(name+'.json')).write_bytes(encoded(scenario))
        suite['cases'].append(dict(id=name,file=name+'.json',fixture=name+'.commands.json',seeds=[11223583,2026]))
    (folder/'world.json').write_bytes(encoded(journey()));suite['cases'].append(dict(id='world',file='world.json'))
    (folder/'suite.json').write_bytes(encoded(suite));return doc,folder/'suite.json'


def request(doc,kind='local'):
    operations={
        'local':[dict(op='object.patch',collection='events',id='survey:yard-welcome',changes=dict(text='The yard is ready for inspection.'))],
        'tile':[dict(op='object.patch',collection='tiles',id='beacon:grass',changes=dict(mini_color=3))],
        'unit':[dict(op='object.patch',collection='mechs',id='workshop:rook',changes=dict(price=1250))],
        'world':[dict(op='city.place',world='survey:aster',map='survey:port',at=[62,16])],
    }[kind]
    return dict(api_version=1,request_id='selection-'+kind,project_id=doc.manifest['package_id'],expected_revision=revision(doc),
        label='Review '+kind+' change',scope=['*'],operations=operations)


def build(folder,tool,runner,windows=False):
    import authoring_review as review
    folder=Path(folder).resolve();doc,suite=create(folder,tool);cases={}
    for kind in ('local','tile','unit','world'):
        proposal=folder/('review-'+kind);record=review.prepare(doc,request(doc,kind),proposal,visuals=False)
        if record['status']!='ready':raise AssertionError(record)
        impact=review.suggest_cases(proposal,tool,suite)
        cases[kind]=dict(suggested=impact['suggested'],report=impact['report'])
    proposal=folder/'review-local';selection=cases['local']['report']
    full=review.check_candidate(proposal,tool,runner=runner,selection=selection)
    selected=review.check_candidate(proposal,tool,runner=runner,selection=selection,suggested=True)
    if full['status']!='passed' or selected['status']!='passed':raise AssertionError((full,selected))
    all_runs=json.loads(Path(full['report']).read_bytes())['runs'];chosen=json.loads(Path(selected['report']).read_bytes())['runs']
    for item in chosen:
        expected=next(r for r in all_runs if (r['case'],r['seed'])==(item['case'],item['seed']))
        left=json.loads(Path(item['report']).read_bytes());right=json.loads(Path(expected['report']).read_bytes())
        if left['result']!=right['result'] or left['coverage']!=right['coverage']:raise AssertionError('Selected/full results differ.')
        for name in (left['result']['save'],'replay.actions'):
            if (Path(item['report']).parent/name).read_bytes()!=(Path(expected['report']).parent/name).read_bytes():
                raise AssertionError('Selected/full save or ordinary inputs differ.')
    report=dict(status='passed',cases=cases,full=full,selected=selected,
        seconds_saved=round(full['elapsed_seconds']-selected['elapsed_seconds'],4),
        timing_basis='One local run on this fixture; includes native fixtures and snapshots. No general speed guarantee.',
        compared='Final native state, event coverage, exact save bytes and ordinary-input replay for every selected seed.')
    if windows:
        from editor_model import ProjectDocument
        from world_route_demo import windows_check
        reference=chosen[0];path=Path(reference['report']).parent
        report['windows']=windows_check(ProjectDocument(path/'game',tool),json.loads((path/'scenario.json').read_bytes()),folder/'windows',reference)
    (folder/'report.json').write_bytes(encoded(report));return report


def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--windows',action='store_true');args=parser.parse_args()
    if args.output.exists():parser.error('Use a new output directory.')
    print(json.dumps(build(args.output,ROOT/'build/btp-project',ROOT/'build/btp-author-playtest',args.windows),indent=2))


if __name__=='__main__':main()
