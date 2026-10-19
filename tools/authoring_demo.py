#!/usr/bin/env python3
"""Create, inspect, break, diagnose and repair a separate playable authoring lab.

All changes use public authoring operations. Existing games and libraries are
read-only inputs; exact requests, previews and gameplay evidence accompany the
new copy. No model/provider or network service is used.
"""
import argparse
import copy
import json
import os
from pathlib import Path
import sys

from asset_catalogue import catalogue,search
from authoring_analysis import analyze
from authoring_contract import AuthoringError,diagnostic
from authoring_service import apply_batch,revision
from authoring_scenarios import run_suite
from authoring_visuals import contact_sheet,animation_strip,map_svg,event_graph
from editor_model import ProjectDocument,EditorError,create_project,encoded
from event_editing import editor_data
from scene_tools import formation_data
from unit_library import closure

ROOT=Path(__file__).resolve().parents[1]


def electric_image():
    """Small owned example artwork, editable in the normal pixel/frame editor."""
    frames=[]
    for phase in range(3):
        rows=[]
        for y in range(16):
            line=[]
            for x in range(16):
                bolt=3+(y*3+phase*5)%10
                color=('555555ff' if x in (0,15) else 'aaaaaaff' if x in (1,14) else
                       'ffffffff' if x==bolt else '55ffffff' if abs(x-bolt)==1 else '0000aaff')
                line.append(color)
            rows.append(''.join(line))
        frames.append(rows)
    return dict(id='author-lab:electric-image',name='Industrial force field',kind='tile',width=16,height=16,frame_ticks=4,frames=frames)


def build(output,validator,runner,analyzer,settings,cancelled=lambda:False):
    output=Path(output).resolve()
    if output.exists():raise AuthoringError('output.exists','Choose a new output directory for the authoring lab.')
    output.mkdir(parents=True)
    doc=create_project(ROOT/'examples/relay-contract',output/'game','relay-contract','BattleTech - Relay Authoring Lab',validator)
    # Search the shipped, attributed numeric catalogue in memory. Its source
    # directory and the shared Unit Library are never seeded or modified here.
    source=copy.copy(doc);source.content=json.loads((ROOT/'content/catalogues/mechs/units.json').read_bytes())
    source.manifest=dict(doc.manifest,title='Classic Inner Sphere mech catalogue')
    source.root=ROOT/'content/catalogues/mechs';source.metadata={}
    found=search(catalogue(source),'kind:mech class:light weapon:lrm')
    if not found['items']:raise AuthoringError('object.missing','The shipped catalogue has no matching light missile unit.')
    chosen=found['items'][0];bundle=closure(source,chosen['id'])
    (output/'missile-unit.unit.json').write_bytes(encoded(bundle))
    (output/'selection.json').write_bytes(encoded(dict(query='kind:mech class:light weapon:lrm',selected=chosen)))
    def batch(name,operations,scope):
        request=dict(api_version=1,request_id='author-lab-'+name,project_id=doc.manifest['package_id'],expected_revision=revision(doc),
                     label=name.replace('-',' ').title(),scope=scope,operations=operations)
        (output/(name+'.commands.json')).write_bytes(encoded(request))
        return apply_batch(doc,request,base_dir=output,save=True,cancelled=cancelled)
    stock=list(doc.adventure['shops'][0]['stock'])+[chosen['id']]
    parts=editor_data(doc)
    pattern=parts['map_patterns'][0]['id']
    operations=[dict(op='unit.import',file='missile-unit.unit.json'),
        dict(op='object.patch',collection='shops',id='relay:stock',changes={'stock':stock}),
        dict(op='object.put',collection='images',value=electric_image()),
        dict(op='art.clone',source='author-lab:electric-image',id='author-lab:electric-copy',name='Force field copy'),
        dict(op='object.put',collection='tiles',value=dict(id='author-lab:electric-fence',sheet='package:art',graphic='author-lab:electric-copy',terrain='wall',mini_color=9)),
        dict(op='map.paint',map='relay:town',tile='author-lab:electric-fence',start=[29,3]),
        *[dict(op='asset.annotate',id=identity,changes=notes) for identity,notes in [
            (chosen['id'],dict(tags=['light','missile-support','catalogue-import'],description='Selected by actual mass and missile armament; CHI-adapted numeric template.')),
            ('relay:depot',dict(tags=['industrial','building'],description='Depot corners and walls for stepped industrial buildings.')),
            ('relay:road',dict(tags=['industrial','road'],description='Connected depot access roads.',edges={'north':'road','east':'road','south':'road','west':'road'})),
            (pattern,dict(tags=['industrial','road-pattern'],description='Reusable office and access-road block.')),
            ('author-lab:electric-fence',dict(name='Industrial force field',tags=['industrial','force-field','electricity'],description='Owned three-frame animated barrier, 128 ms per frame.'))]]]
    batch('create-content',operations,['*'])
    selected=[]
    for query in ('kind:mech class:light weapon:lrm','kind:construction tag:industrial','kind:tile tag:force-field animated:true','kind:pattern tag:road-pattern'):
        result=search(catalogue(doc),query)
        if not result['items']:raise AuthoringError('demo.search_failed','A recorded asset query returned no matches: '+query)
        selected.extend(result['items'])
    visuals=output/'visuals';visuals.mkdir()
    contact_sheet(doc,selected,visuals/'selection.svg',settings)
    electric=next(r for r in selected if r['id']=='author-lab:electric-fence')
    animation_strip(doc,electric,visuals/'electricity.svg',settings)
    animation_strip(doc,next(r for r in selected if r['id']==chosen['id']),visuals/'unit-down.svg',settings,direction=4)
    map_svg(doc,'relay:town',visuals/'depot.svg',settings,overlays=['entrances','formations','grid'])
    event_graph(doc,visuals/'contract-events.svg','relay:battle',2)
    clean=analyze(doc,analyzer,settings,output=output/'lint-before.json')
    if clean['status']=='failed':raise AuthoringError('demo.invalid','The initial lab failed mission checks.')
    encounter=copy.deepcopy(doc.adventure['encounters'][0]);at=encounter['enemies'][0]['at']
    dx,dy=formation_data(doc,settings)['mechs'][0]
    blocked=[encounter['party_at'][0]+dx,encounter['party_at'][1]+dy]
    operation=dict(op='marker.move',map=encounter['map'],kind='enemy',id=encounter['id'],enemy_index=0,at=blocked)
    batch('break-deployment',[operation],['adventure.encounters/'+encounter['id']])
    broken=analyze(doc,analyzer,settings,output=output/'lint-broken.json')
    if not any(p['code']=='deployment.overlap' for p in broken['diagnostics']):raise AuthoringError('demo.check_failed','The broken deployment was not diagnosed.')
    suite_path=ROOT/'examples/authoring/scenarios/relay.suite.json';suite=json.loads(suite_path.read_bytes())
    failed_route=run_suite(doc,suite,suite_path.parent,output/'broken-scenarios',runner,settings,cancelled,case_ids=['victory'])
    if failed_route['status']!='failed':raise AuthoringError('demo.check_failed','The blocked battle unexpectedly passed its victory route.')
    batch('repair-deployment',[dict(operation,at=at)],['adventure.encounters/'+encounter['id']])
    fixed=analyze(doc,analyzer,settings,output=output/'lint-repaired.json')
    if fixed['status']=='failed':raise AuthoringError('demo.invalid','The repaired deployment still fails mission checks.')
    passed=run_suite(doc,suite,suite_path.parent,output/'repaired-scenarios',runner,settings,cancelled,case_ids=['victory'])
    result=dict(api_version=1,status=passed['status'],project=str(doc.root),revision=revision(doc),selected_unit=chosen['id'],
        diagnosed='deployment.overlap',broken_report=failed_route['report'],repaired_report=passed['report'],
        visuals=str(visuals),play=[str(ROOT/'build'/('btech-port.exe' if os.name=='nt' else 'btech-port')),'--project',str(doc.root)],
        edit=[sys.executable,str(ROOT/'tools/game_editor.py'),str(doc.root)])
    (output/'demo-report.json').write_bytes(encoded(result))
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    suffix='.exe' if os.name=='nt' else ''
    for key,name in [('validator','btp-project'),('runner','btp-author-playtest'),('analyzer','btp-author-analyze')]:parser.add_argument('--'+key,type=Path,default=ROOT/'build'/(name+suffix))
    for key,path in [('data','Original DOS'),('dialogue-data','work/talk-data.bin'),('combat-data','work/combat-data.bin'),('world-data','work/world-data.bin')]:parser.add_argument('--'+key,type=Path,default=ROOT/path)
    parser.add_argument('--cancel-file',type=Path);args=parser.parse_args()
    try:
        result=build(args.output,args.validator,args.runner,args.analyzer,
            {k:str(getattr(args,k.replace('-','_'))) for k in ('data','dialogue-data','combat-data','world-data')},
            cancelled=lambda:bool(args.cancel_file and args.cancel_file.exists()))
    except (EditorError,OSError,ValueError) as exc:result=dict(api_version=1,status='failed',diagnostics=[diagnostic(exc)])
    print(json.dumps(result,indent=2));return 0 if result['status']=='passed' else 1


if __name__=='__main__':raise SystemExit(main())
