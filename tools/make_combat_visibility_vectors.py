#!/usr/bin/env python3
"""Observe 0000:0E4B's visibility flags, including sector-edge crossings."""
import json
from combat_oracle import OriginalCombat,ROOT
from make_live_campaign_vectors import SNAP
from prepare_talk import EXE_SHA,IMAGE_SHA


def packed(x,y):return (x//128<<8)|(x&127),(y//128<<12)|(y&127)


def main():
    m=OriginalCombat(snapshot=SNAP);rows=[]
    for infantry in (0,1):
        unit=4 if infantry else 0
        for centre in (64,0,127):
            offsets=[(x,y) for y in range(-16,17) for x in range(-17,18)] if centre==64 else [(x,y) for x,y in [(v,0) for v in range(-17,18)]+[(0,v) for v in range(-16,17)]]
            for dx,dy in offsets:
                m.reset();m.write(m.state+0x406a,bytes(48));m.word(m.state+0x406a+2*unit,1)
                cx,cy=packed(1536+centre,1536+centre);x,y=packed(1536+centre+dx,1536+centre+dy)
                m.word(m.buffer+0xa44b,cx);m.word(m.buffer+0xa44d,cy)
                m.word(m.state+0x4004+2*unit,x);m.word(m.state+0x4036+2*unit,y)
                m.call(0,0xe4b,limit=1000000)
                visible=m.read(m.state+0x42f6+unit,1)[0]
                rows.append(f'V {infantry} {centre} {dx} {dy} {visible}')
    (ROOT/'tests/fixtures/combat-visibility-primary.txt').write_text('\n'.join(rows)+'\n')
    (ROOT/'tests/fixtures/combat-visibility-primary.json').write_text(json.dumps(dict(
        executable_sha256=EXE_SHA,image_sha256=IMAGE_SHA,cases=len(rows),routine='0000:0E4B writes state:42F6 visibility flags',
        prerequisites='One active GAME3 mech or infantry at declared offsets; cursor half-tile 64/0/127, crossing sector boundaries using normal packed coordinates.',
        comparison='Exact unit visibility controlling sprite admission and beam sound; original instructions unchanged. Does not claim complete battlefield pixel parity.'),indent=2)+'\n')
    print('Original combat visibility cases:',len(rows))


if __name__=='__main__':main()
