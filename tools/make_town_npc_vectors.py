#!/usr/bin/env python3
"""Execute original town NPC initialization and first timer expiry.

MTP waypoint/route bytes supply the city-loader's completed file-read boundary.
Only numeric observations enter Git; no original instructions/files are edited.
"""
import json
from combat_oracle import OriginalCombat, ROOT
from make_city_edge_vectors import span
from make_party_vectors import SNAP
from prepare_talk import EXE_SHA, IMAGE_SHA


def main():
    m=OriginalCombat(snapshot=SNAP);rows=[]
    for town in range(1,11):
        raw=(ROOT/f'Original DOS/MAP{town}.MTP').read_bytes()
        for seed in (1,1234,0x020304,0x123456,0xffffff):
            m.reset();m.write(m.ds+0x4fc0,seed.to_bytes(3,'little'))
            for selector,offset,data in ((0x53ca,0x4564,raw[389:421]),
                                         (0x53cc,0x4596,raw[421:453]),
                                         (0x53da,0x3768,raw[533:541])):
                m.write(16*m.word(m.ds+selector)+offset,data)
            m.write(m.state+0xd339,[0])
            span(m,0,0x30e2,0x3205,m.ds//16,{8:town})
            # The first update expires each one-frame stay, making its
            # high-nibble origin visible. No path step occurs on this call.
            m.call(0,0x24c2)
            values=[town,seed,int.from_bytes(m.read(m.ds+0x4fc0,3),'little')]
            for i in range(8):
                values += [m.read(m.state+0xd398+26*i,1)[0],
                           m.read(m.state+0xd399+26*i,1)[0],
                           m.word(m.state+0x4024+2*i),m.word(m.state+0x4056+2*i)]
            rows.append('N '+' '.join(map(str,values)))
    (ROOT/'tests/fixtures/town-npcs-primary.txt').write_text('\n'.join(rows)+'\n')
    facts=dict(
        executable_sha256=EXE_SHA,image_sha256=IMAGE_SHA,cases=len(rows),
        routines=['0000:30E2..3205','0000:24C2'],
        prerequisites='All ten populated MTPs; five RNG seeds; original waypoint and route tables loaded, recruitment guard clear.',
        comparison='Eight route pairs, expiry timers, packed visible coordinates and RNG after initialization and first expiry.',
        limits='Original direction/sprite pointer initialization and DOS frame cadence are outside this numeric span.',
        no_instruction_patches=True)
    print('Original town NPC setup/expiry cases:',len(rows))
    rows=[]
    for town in range(2,11):
        raw=(ROOT/f'Original DOS/MAP{town}.MTP').read_bytes()
        for building in (3,4,5,7,9):
            m.reset();m.write(16*m.word(m.ds+0x5460)+0x4602,raw[517:533])
            m.write(m.state+0xd319,[building])
            span(m,0x7dc,0x17c6,0x17ec,m.ds//16)
            room=m.word(0x7eff6)
            rows.append(f'T {town} {building} {room}')
    (ROOT/'tests/fixtures/town-talk-primary.txt').write_text('\n'.join(rows)+'\n')
    facts['talk']=dict(cases=len(rows),routine='07DC:17C6..17EC',
        prerequisites='Nine post-Citadel MTP room tables; conversation categories 3, 4, 5, 7, 9 supplied through original flag 13.',
        comparison='First matching waypoint, or 8 for no match; independent of the entrance used to enter the building.',
        hospital='HOSPITAL.BLD at 3582 writes category 5 before invoking native action 12; preserve this original category.')
    (ROOT/'tests/fixtures/town-npcs-primary.json').write_text(json.dumps(facts,indent=2)+'\n')
    print('Original first-matching Talk waypoint cases:',len(rows))


if __name__=='__main__':main()
