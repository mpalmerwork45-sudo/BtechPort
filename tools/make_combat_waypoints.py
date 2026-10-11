#!/usr/bin/env python3
"""Capture original queued-route planning and FIFO consumption without UI patches."""
from combat_oracle import OriginalCombat, ROOT
from make_combat_vectors import fingerprint

o=OriginalCombat(snapshot=ROOT/'work/reference-runs/1791709609448346900/combat-menu')
rows=['# Original 12-entry 32C6 queue, 103B:1774 plan and 12E8:000C turn; MAP1.']
for case in range(108):
    o.reset();loan=case%3;mode=case//3%3;heat=case//9%3*5;count=case%12+1
    if mode==2 and not o.template(loan)[50]:mode=0
    o.word(o.ds+0x2e3a,0);o.word(o.state+0x14a,1);o.word(o.state+0xe48e,0)
    o.write(o.state+0x406a,bytes(48));o.word(o.state+0x406a,1)
    o.write(o.state+0xc724,o.template(loan));o.write(o.state+0xc618,bytes(5))
    o.write(o.state+0x5e,bytes(60));o.write(o.state+0x6e,[heat]);o.write(o.state+0xd576,bytes(8))
    o.word(o.state+0x4004,0xc00+96);o.word(o.state+0x4036,0xc000+93)
    for a in (0x396c,0x3920,0x45b6):o.write(o.state+a,[2])
    o.write(o.state+0x3800,bytes([255])*288)
    goals=[(97+case%3,93)]+[(100+(i%4)*2,89+(i//4)*2) for i in range(count-1)]
    queue=b''.join(bytes([mode,0xcc,x,y]) for x,y in goals)
    o.write(o.state+0x32c6,queue+bytes([255])*(48-len(queue)))
    o.call(0x103b,0x1774,0,1,limit=2000000)
    path=fingerprint(o.read(o.state+0x40b4,24))
    o.call(0x12e8,0xc,0,limit=20000000)
    after=o.read(o.state+0x32c6,48);remaining=[]
    for i in range(0,48,4):
        if after[i]==255:break
        remaining.extend(after[i+2:i+4])
    row=f'Q {loan} {mode} {heat} {count} '+ ' '.join(str(v) for g in goals for v in g)
    row+=f' | {o.word(o.state+0x4004)&127} {o.word(o.state+0x4036)&127} '
    row+=f'{o.read(o.state+0x6e,1)[0]} {after[0]} {len(remaining)//2} {path:016x}'
    if remaining:row+=' '+' '.join(map(str,remaining))
    rows.append(row)
(ROOT/'tests/fixtures/combat-waypoints.txt').write_text('\n'.join(rows)+'\n')
print(f'Wrote {len(rows)-1} original queue planning/turn cases')
