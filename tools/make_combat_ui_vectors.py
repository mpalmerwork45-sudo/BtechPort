#!/usr/bin/env python3
"""Numeric RGB evidence from the owner's original combat menu/scan captures.

The private GAME4 copy activates GAME3's parked vehicles, puts its fourth
character on foot and enables an encounter. Original code and assets are
unchanged. Screenshots and RAM remain under ignored work/.
"""
import argparse,hashlib,json
from pathlib import Path
from PIL import Image
from prepare_talk import EXE_SHA,IMAGE_SHA

ROOT=Path(__file__).resolve().parents[1]
DEFAULT=ROOT/'work/reference-runs/1791861341506357450'
CASES=('mech-command','rex-command','possum-command','foot-command',
       'scan-choice','scan-friend','scan-friend-3','scan-foot-warning','scan-enemy-human')

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--capture',type=Path,default=DEFAULT)
    args=parser.parse_args();rows=[];sources=[]
    for index,label in enumerate(CASES):
        p=args.capture/'captures'/f'{label}.png';frame=Image.open(p).convert('RGB')
        if frame.size!=(320,200):raise RuntimeError('Expected original 320x200 frame')
        pixels=frame.crop((0,0,104,200)).tobytes();h=0xcbf29ce484222325
        for value in pixels:h=((h^value)*0x100000001b3)&0xffffffffffffffff
        rows.append(f'U {index} {h:016x}')
        sources.append({'case':index,'label':label,'left_rgb_sha256':hashlib.sha256(pixels).hexdigest()})
    (ROOT/'tests/fixtures/combat-ui-primary.txt').write_text('\n'.join(rows)+'\n')
    (ROOT/'tests/fixtures/combat-ui-primary.json').write_text(json.dumps(dict(
        executable_sha256=EXE_SHA,image_sha256=IMAGE_SHA,cases=sources,
        prerequisites='Controlled private GAME3 copy: original three parked vehicles active, fourth character on foot, encounter gate enabled; actual DOS menu keys. Enemy-human health/weapon and Northwest bearing retained in the native UI prerequisite.',
        routines=['103B:14C3 commands','05AB:18E8 headers','103B:2591 scan scope','05AB:1467 summary/detail'],
        comparison='All 104x200 left RGB pixels, including borders and selection. Does not compare battlefield placement or a full DOS fight.'),indent=2)+'\n')
    print('Original combat menu/scan regions:',len(rows))
if __name__=='__main__':main()
