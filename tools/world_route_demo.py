"""Independent two-planet navigation fixture, using the shipped sample art.

No original resources, model service or private saves are required. Coordinates
deliberately exercise cities spanning 64-tile runtime sectors and water beneath
an overlaid town. The same package can be opened and repaired in the editor.
"""
import copy
import json
from pathlib import Path
from editor_model import create_project,encoded
from world_editing import upgrade

ROOT=Path(__file__).resolve().parents[1]


def create(output,tool):
    doc=create_project(ROOT/'examples/beacon-demo',output,'world-survey','World Survey',tool)
    a=copy.deepcopy(doc.adventure);upgrade(a)
    a.update(format='btp-adventure-v3',schema_version=3)
    a['events']=[dict(id='survey:end',op='end'),
        dict(id='survey:outbound',op='transfer',map='survey:landing',at=[16,20],next='survey:end',failure='survey:end'),
        dict(id='survey:homebound',op='transfer',map='survey:home',at=[16,20],next='survey:end',failure='survey:end')]
    for key in ('shops','encounters','objectives','flags'):a[key]=[]
    def town(identity,origin,entrances):
        return dict(id=identity,name=identity.split(':')[1].title(),origin=origin,
            rows=[['beacon:grass']*16 for _ in range(16)],overlays=[],entrances=entrances)
    a['maps']=[town('survey:home',[8,16],[]),
        town('survey:port',[60,16],[dict(id='survey:shuttle',name='Shuttle to Boreal',at=[10,20],event='survey:outbound')]),
        town('survey:landing',[8,16],[dict(id='survey:return',name='Shuttle to Aster',at=[24,20],event='survey:homebound')])]
    a['jigsaws']=[dict(id='survey:plain',name='Plain',rows=[['beacon:grass']*8 for _ in range(8)]),
                  dict(id='survey:lake',name='Lake',rows=[['beacon:water']*8 for _ in range(8)])]
    a['worlds']=[dict(id='survey:'+name,name=name.title(),pieces=[['survey:plain']*16 for _ in range(8)],patches=[],cities=cities)
                 for name,cities in [('aster',['survey:home','survey:port']),('boreal',['survey:landing'])]]
    a['worlds'][0]['pieces'][2][8]='survey:lake'
    # Four mounted pilots and two walkers test both independent formation
    # arrays. The last vehicle has stricter water/woods rules than a mech.
    pilot=copy.deepcopy(a['people'][0]);a['people']=[]
    for i in range(6):
        p=copy.deepcopy(pilot);p.update(id=f'survey:pilot-{i}',identity=f'actor:{i}',name=f'Pilot {i+1}');a['people'].append(p)
    a['start']=dict(map='survey:home',at=[16,20],event='survey:end',credits=2000,
        party=[dict(person=f'survey:pilot-{i}',mech='workshop:rook' if i<3 else 'survey:carrier' if i==3 else 'none') for i in range(6)])
    content=copy.deepcopy(doc.content)
    content['mechs'].append(dict(id='survey:carrier',name='Survey Carrier',label='Carrier',kind='vehicle',mass_tons=30,price=100,
        presentation='beacon:biped',movement=dict(type='tracked',walk=4,jump=0),engine_heat_sinks=0,
        armor={k:20 for k in ('front','left','right','rear','turret')},
        structure={k:3 for k in ('front','left','right','rear','turret')},
        loadout=[dict(weapon='workshop:cool-beam',location='turret',ammunition=0)]))
    doc.replace_all(content,a,doc.art,doc.manifest,{})
    doc.save();return doc


def journey():
    steps=[dict(op='assert',world='survey:aster',world_at=[32,52],formation='compact',party_count=6,owned_mechs=4),
        dict(op='assert',discovered=dict(world='survey:boreal',at=[16,24],seen=0))]
    for at in ([54,64],[90,64],[138,64],[142,56]):
        steps.extend([dict(op='walk',world='survey:aster',at=at),dict(op='assert',world_at=at,formation='compact'),dict(op='checkpoint')])
    steps.extend([dict(op='capture'),dict(op='walk',entrance='survey:shuttle'),dict(op='assert',phase='entry'),
        dict(op='checkpoint'),dict(op='enter'),dict(op='assert',world='survey:boreal',world_at=[32,52],formation='compact'),
        dict(op='assert',discovered=dict(world='survey:boreal',at=[16,24],seen=1)),dict(op='checkpoint')])
    for at in ([54,64],[150,64]):steps.extend([dict(op='walk',world='survey:boreal',at=at),dict(op='assert',world_at=at,formation='compact')])
    steps.extend([dict(op='capture'),dict(op='checkpoint'),dict(op='walk',entrance='survey:return'),dict(op='enter'),
        dict(op='assert',world='survey:aster',world_at=[32,52],formation='compact'),
        dict(op='assert',discovered=dict(world='survey:aster',at=[72,32],seen=1)),
        dict(op='assert',discovered=dict(world='survey:boreal',at=[72,32],seen=1)),
        dict(op='assert',discovered=dict(world='survey:aster',at=[120,56],seen=0)),dict(op='checkpoint')])
    return dict(format='btp-author-scenario-v1',steps=steps)


def windows_check(doc,scenario,folder,reference,settings=None):
    """Optional same-input Windows continuation in the isolated test prefix."""
    import subprocess
    from windows_check import WINE,arguments,environment
    folder=Path(folder).resolve();folder.mkdir()
    scenario=copy.deepcopy(scenario)
    if 'checkpoint' in scenario:
        # The validated Linux run already staged the exact input; a relative
        # local copy also avoids embedding host paths into Windows JSON.
        (folder/'initial.btp').write_bytes((Path(reference['report']).parent/'initial.btp').read_bytes())
        scenario['checkpoint']['file']='initial.btp'
    source=folder/'scenario.json';source.write_bytes(encoded(scenario))
    env=environment();env.pop('DISPLAY',None);env.pop('WAYLAND_DISPLAY',None)
    options=[]
    for k,v in (settings or {}).items():options.extend(['--'+k,Path(v)])
    command=[str(WINE),*arguments([ROOT/'build-windows/btp-author-playtest.exe','--project',doc.root,
        '--scenario',source,'--artifacts',folder,*options])]
    p=subprocess.run(command,env=env,capture_output=True,text=True,timeout=60)
    (folder/'steps.jsonl').write_text(p.stdout);(folder/'stderr.txt').write_text(p.stderr)
    if p.returncode:raise RuntimeError('Windows route failed: '+p.stderr[-2000:])
    result=json.loads(p.stdout.splitlines()[-1])
    expected=json.loads(Path(reference['report']).read_bytes())['result']
    if result!=expected:raise RuntimeError('Windows and Linux route state/results differ.')
    if (folder/result['save']).read_bytes()!=(Path(reference['report']).parent/expected['save']).read_bytes():
        raise RuntimeError('Windows and Linux route save bytes differ.')
    report=dict(status='passed',check='Same route state and exact save bytes on Linux and Windows/Wine',ticks=result['ticks'])
    (folder/'report.json').write_bytes(encoded(report));return report


def main():
    import argparse
    from authoring_scenarios import run
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--windows',action='store_true',help='Also verify the Windows runner under isolated Wine, with exact save comparison')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    doc=create(args.output/'game',ROOT/'build/btp-project')
    scenario=journey();(args.output/'journey.json').write_bytes(encoded(scenario))
    result=run(doc,scenario,args.output/'journey',ROOT/'build/btp-author-playtest')
    if args.windows and result['status']=='passed':result['windows']=windows_check(doc,scenario,args.output/'windows',result)
    print(json.dumps(result,indent=2))
    return result['status']!='passed'


if __name__=='__main__':raise SystemExit(main())
