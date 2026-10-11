#!/usr/bin/env python3
"""Capture bounded original enemy orders and paths, with controlled units."""
import random
from combat_oracle import OriginalCombat,ROOT
from make_combat_vectors import fingerprint

o=OriginalCombat(snapshot=ROOT/'work/reference-runs/1791709609448346900/combat-menu')
source=random.Random(1988);rows=[]
positions=[(64,77,101,89),(84,85,96,93),(96,93,99,93),(99,93,96,93)]
positions += [(x,y,x+source.randrange(-12,13),y+source.randrange(-12,13))
    for x,y in [(source.randrange(24,104),source.randrange(24,104)) for _ in range(60)]]
for kind in [0,1]:
    for n,(px,py,ex,ey) in enumerate(positions):
        o.reset();unit=16 if kind else 12;heat=n%3*5;weapon=n%14;direction=n%8
        o.write(o.state+0x406a,bytes(48));o.word(o.state+0x406a,1);o.word(o.state+0x406a+2*unit,1)
        o.write(o.state+0xc724,o.template(2));o.write(o.state+0xc918,o.template())
        o.write(o.state+0xc69c,bytes([0,6,0,0,0,0,0,0,0,0,0,weapon,8,0,0,60,0]))
        for u,x,y in [(0,px,py),(unit,ex,ey)]:
            o.word(o.state+0x4004+2*u,0xc00+x);o.word(o.state+0x4036+2*u,0xc000+y)
        o.write(o.state+0x3920+unit,[direction]);o.write(o.state+0x396c+unit,[direction])
        o.write(o.state+0x72,[heat]);o.word(o.state+0x374c,1 if kind else 0)
        o.word(o.state+0xe48e,0);o.write(o.state+0xd333,[0]);o.word(o.state+0x3772,0)
        o.call(0xe31,0x3ab,unit,0,limit=2000000)
        order=o.read(o.state+0x32c6+unit*48,4)
        face=o.read(o.state+0x396c+unit,1)[0];plan=o.read(o.state+0x3920+unit,1)[0]
        rows.append(f'A {kind} {px} {py} {ex} {ey} {direction} {heat} {weapon} '
            f'{order[0]} {face} {plan} {fingerprint(o.read(o.state+0x40b4+24*unit,24)):016x} '
            f'{fingerprint(o.read(o.state+0x3800+12*unit,12)):016x} '
            f'{o.read(o.state+0x40b4+24*unit,24).hex()} {order.hex()} {o.word(o.state+0x3770)}')
(ROOT/'tests/fixtures/combat-ai.txt').write_text(
    '# Controlled original 0E31:03AB enemy decisions and 103B:193B paths; MAP1.\n'+'\n'.join(rows)+'\n')
print(f'Wrote {len(rows)} original enemy decision/path cases')
