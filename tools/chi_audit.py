#!/usr/bin/env python3
"""Bounded CHI import inventory: fingerprints and numeric structure, never text/pixels."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import struct
from audit_bld_flow import decrypt, graph

ROOT = Path(__file__).resolve().parents[1]
BUILDINGS = ('TRAINING CITADEL COMSTAR WEAPON ARMOR REPAIR BARRACKS LOUNGE GARAGE '
             'HOSPITAL ARENA PARTY CLOTHES JAIL MAYOR WEAPON2 THEATER FROB VIEWDISK '
             'BARRACK2 ENTRANCE HUT ENDMECH INSTRUCT FINDIT WINSCENE').split()
GRAPHICS = ('BTTLTECH.ICN MECHSHAP.CMP BTSTATS.CMP BTBORDER.CMP ANIMATE.ICN '
            'BTTITLE.CMP INFOCOM.CMP TINYLAND.CMP STARLEAG.ICN MAP.ICN '
            'ENDMECH.CMP DESTRUCT.ICN').split()
RESOURCE_FILES = tuple([f'MAP{i}.MTP' for i in range(1,16)] + GRAPHICS +
                       [f'{name}.BLD' for name in BUILDINGS] +
                       [f'O{i}.ANM' for i in range(22)] + ['WWOODBT.SIF'])
SOURCE_FILES = ('BTECH.EXE', *RESOURCE_FILES)


def audit(source):
    source = Path(source)
    files=[];scripts=[];maps=[]
    for name in SOURCE_FILES:
        path=source/name
        if path.is_symlink() or not path.is_file():raise ValueError(f'Missing regular original file: {name}')
        if path.stat().st_size>1024*1024:raise ValueError(f'Oversized original file: {name}')
        raw=path.read_bytes()
        files.append(dict(file=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
        if name.endswith('.BLD'):
            decoded=decrypt(raw);nodes=graph(decoded)
            scripts.append(dict(file=name,building=BUILDINGS.index(name[:-4]),bytes=len(decoded),
                reachable_instructions=len(nodes),
                native_actions=sorted({decoded[pc+1] for pc in nodes if decoded[pc]==0xf5}),
                state_indices=sorted({decoded[pc+1] for pc in nodes if decoded[pc] in (0xf1,0xf3,0xf4,0xf7)}),
                menus=sorted({decoded[pc+1] for pc in nodes if decoded[pc]==0xf9}),
                confidence='VERIFIED structural traversal; branch execution not implied'))
        if name.endswith('.MTP'):
            if name=='MAP15.MTP':
                maps.append(dict(file=name,width=32,height=24,kind='raw map room',entrances=0));continue
            if len(raw)<541 or len(raw)!=541+raw[3]*raw[4]:raise ValueError(f'Invalid MTP: {name}')
            xs=struct.unpack_from('<16H',raw,389);ys=struct.unpack_from('<16H',raw,421)
            maps.append(dict(file=name,width=raw[3],height=raw[4],kind='local',
                entrances=sum(bool(x and y) for x,y in zip(xs,ys)),
                building_ids=sorted({raw[517+i] for i in range(16) if xs[i] and ys[i]})))
    contexts=[dict(action=i,scripts=[s['file'] for s in scripts if i in s['native_actions']],
        dispatcher='port/core/original_actions.c',
        disposition='C2 compatibility; C4 context registry and editable parameters') for i in range(1,48)]
    return dict(format='btp-chi-audit-v1',source_version='chi-original-dos-1.03',
        files=files,maps=maps,scripts=scripts,native_contexts=contexts,
        totals=dict(source_files=len(files),resource_files=len(RESOURCE_FILES),scripts=len(scripts),
            reachable_instructions=sum(s['reachable_instructions'] for s in scripts),
            max_script_bytes=max(s['bytes'] for s in scripts),max_entrances=max(m['entrances'] for m in maps)),
        limits=dict(bld_program_bytes=9000,legacy_story_bytes=100,authored_flags=64,
            authored_events=1024,authored_shops=16,local_maps=64,entrances_per_map=16),
        note='Contains fingerprints/numeric inventories only. Decoded dialogue, scripts and art stay local.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data',type=Path,default=ROOT/'Original DOS')
    parser.add_argument('--output',type=Path,default=ROOT/'work/chi-import/inventory.json')
    args=parser.parse_args();result=audit(args.data)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result['totals'],sort_keys=True))


if __name__=='__main__':main()
