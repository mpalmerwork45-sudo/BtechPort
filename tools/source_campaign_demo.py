#!/usr/bin/env python3
"""Reproduce AI7a's two-planet source/build fixture from tested Cairn missions."""
import argparse
import json
import os
from pathlib import Path
import tempfile
import time
from authoring_service import apply_batch,revision
from campaign_source import convert,build
from editor_model import create_project,encoded

ROOT=Path(__file__).resolve().parents[1]


def generate(output,validator,verify=False):
    started=time.monotonic();output=Path(output).resolve()
    if output.exists():raise ValueError('Choose a new output directory; existing work is preserved.')
    output.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix='.source-demo-',dir=output) as temp:
        doc=create_project(ROOT/'examples/cairn-passage',Path(temp)/'package','cairn-planets','BattleTech - Cairn Planets',validator)
        # Existing defence and escort missions keep their tested IDs/routes.
        # Only planet composition is added through the public command service.
        request=dict(api_version=1,request_id='two-planets',project_id=doc.manifest['package_id'],expected_revision=revision(doc),
            label='Place Cairn missions on two planets',scope=['*'],operations=[
                dict(op='world.create',name='Cairn',width=32,height=32),
                dict(op='world.create',name='Cairn II',width=32,height=32),
                dict(op='city.place',world='cairn-planets:world',map='cairn:base',at=[64,64]),
                dict(op='city.place',world='cairn-planets:world',map='cairn:relay',at=[128,64]),
                dict(op='city.place',world='cairn-planets:world-1',map='cairn:pass',at=[64,64])])
        apply_batch(doc,request,save=True)
        source=convert(doc,output/'source')
    (output/'creation.commands.json').write_bytes(encoded(request))
    index=source.source.index.copy();index['notes']=dict(brief='Two planets: defend Cairn relay, then escort a transport on Cairn II.',
        coverage='Reuses Cairn Passage missions. This demonstrates source/build composition, not a new long campaign or unbounded world traversal.')
    (source.root/'SOURCE.json').write_bytes(encoded(index))
    from editor_model import ProjectDocument
    source=ProjectDocument(source.root,validator)
    first=build(source,output/'game');second=build(source,output/'rebuilt')
    if first['fingerprint']!=second['fingerprint'] or first['files']!=second['files']:
        raise RuntimeError('Repeated source compilation changed runtime bytes.')
    report=dict(status='built',source=str(source.root),package=str(output/'game'),fingerprint=first['fingerprint'],
        source_files=len(source.source.disk),source_bytes=sum(map(len,source.source.disk.values())),
        planets=len(source.adventure['worlds']),maps=len(source.adventure['maps']),events=len(source.adventure['events']),
        reproducible=True,seconds=round(time.monotonic()-started,3))
    if verify:
        from authoring_scenarios import run
        scenario=json.loads((ROOT/'examples/authoring/cairn/full-contract.json').read_bytes())
        settings={key:str(ROOT/path) for key,path in [('data','Original DOS'),('dialogue-data','work/talk-data.bin'),('combat-data','work/combat-data.bin'),('world-data','work/world-data.bin')]}
        result=run(source,scenario,output/'scenario',ROOT/'build'/('btp-author-playtest.exe' if os.name=='nt' else 'btp-author-playtest'),settings)
        report['scenario_status']=result['status']
        if result['status']!='passed':report['status']='failed'
    (output/'report.json').write_bytes(encoded(report));return report


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--validator',type=Path,default=ROOT/'build'/('btp-project.exe' if os.name=='nt' else 'btp-project'));parser.add_argument('--verify',action='store_true')
    args=parser.parse_args();report=generate(args.output,args.validator,args.verify);print(json.dumps(report,indent=2))
    return 1 if report['status']=='failed' else 0


if __name__=='__main__':raise SystemExit(main())
