#!/usr/bin/env python3
"""Record played DOS town walks, excluding inputs consumed by a dialogue."""
import json
import struct
from combat_oracle import ROOT
from prepare_talk import EXE_SHA, IMAGE_SHA


def world(x,y):
    return (x>>8)*128+(x&127),(y>>12)*128+(y&127)


def main():
    rows=[];cases=[]
    runs=[(2,'1791962848011430927','town-start',
           [('down',f'starport-{i}') for i in range(1,4)]+
           [('left',f'starport-{i}') for i in range(4,9)]+
           [('up',f'starport-{i}') for i in range(9,14)]+
           [('right',f'starport-{i}') for i in range(14,18)]+
           [('down',f'starport-{i}') for i in range(18,21)]+
           [('right',f'starport-{i}') for i in range(21,23)]),
          (4,'1791963196424631180','mech-walk-start',
           [(direction,f'mech-walk-{i}') for i,direction in enumerate(['down']*4+['right']*4+['up']*4+['left']*4)])]
    for town,run,start,walk in runs:
        folder=ROOT/'work/reference-runs'/run
        for action,label in [('idle',start)]+walk:
            meta=json.loads((folder/(label+'-state.json')).read_text())
            ram=(folder/(label+'-ram.bin')).read_bytes();base=int(meta['state_segment'],16)*16
            x,y=world(*meta['cursor_raw']);people=[];mechs=[]
            for i in range(8):
                p=ram[base+0xc614+17*i:base+0xc614+17*(i+1)]
                if p[0]!=255 and p[12]>=8:
                    # Outdoor positions are compacted independently of the
                    # character slots; Rick alone occupies position zero.
                    at=len(people)//3
                    px=struct.unpack_from('<H',ram,base+0x400c+2*at)[0]
                    py=struct.unpack_from('<H',ram,base+0x403e+2*at)[0]
                    people.extend((i,*world(px,py)))
            for i in range(4):
                if ram[base+0xc724+125*i]!=255:
                    px=struct.unpack_from('<H',ram,base+0x4004+2*i)[0]
                    py=struct.unpack_from('<H',ram,base+0x4036+2*i)[0]
                    mechs.extend((i,*world(px,py)))
            rows.append(' '.join(map(str,['F',town,action,x,y,len(people)//3,len(mechs)//3,*people,*mechs])))
            cases.append(dict(town=town,run=run,label=label,action=action))
    (ROOT/'tests/fixtures/town-formation-primary.txt').write_text('\n'.join(rows)+'\n')
    (ROOT/'tests/fixtures/town-formation-primary.json').write_text(json.dumps(dict(
        executable_sha256=EXE_SHA,image_sha256=IMAGE_SHA,cases=cases,
        prerequisites='Private GAME3 copies: Starport at (1337,1117), four people on foot and parked vehicles; MAP4 at (1178,1434), three active vehicles and Rick on foot. Encounter delay 255. Ordinary arrow inputs; no instruction edits.',
        comparison='Exact cursor and every active party/mech world position after each recorded input, including whole-formation rejected wall steps.',
        exclusions='Starport first Down was consumed by loading and is omitted. End the trace before the arena entry question. The earlier MAP4 run was stuck in a Mechit-Lube entry question and is not movement evidence.',
        limits='Does not establish doorway triggers for outer members, recovery of malformed older formations, or DOS timing.'),indent=2)+'\n')
    print('Original town formation observations:',len(rows))


if __name__=='__main__':main()
