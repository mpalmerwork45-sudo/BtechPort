#!/usr/bin/env python3
"""Capture original fourth/fifth encounter construction and apprenticeship."""
import random
from combat_oracle import OriginalCombat,ROOT
from make_combat_vectors import fingerprint

snapshot=ROOT/'work/reference-runs/1791709609448346900/combat-menu'
o=OriginalCombat(snapshot=snapshot);rows=[];source=random.Random(1988)
for assignment in [3,4]:
    for n in range(48):
        o.reset();seed=source.randrange(1,1<<24);o.write(o.ds+0x4fc0,seed.to_bytes(3,'little'))
        o.write(o.state+0xd30c,[assignment]);o.write(o.state+0xd30f,[0])
        o.word(o.state+0x3772,0);o.word(o.state+0xe48e,0)
        count=3+(o.call(0x187f,0xbc0)&3) if assignment==3 else 1
        o.call(0x7dc,0xd49,0 if assignment==3 else 1,count if assignment==3 else 0)
        row=f'B {assignment} {seed} {n%3} {count+1} {int.from_bytes(o.read(o.ds+0x4fc0,3),"little")}'
        for i in range(count):
            u=16+i if assignment==3 else 12
            record=o.read(o.state+(0xc69c+17*i if assignment==3 else 0xc918),17 if assignment==3 else 125)
            frame=o.read(o.state+0x409a+u,1)[0]-(16 if assignment==3 else 0)
            row+=f' {o.word(o.state+0x4004+2*u)&127} {o.word(o.state+0x4036+2*u)&127} {fingerprint(record):016x} {frame}'
        rows.append(row)
for credits in [0,35,499,500,501,65535,65536,1000000,0xffffffff]:
    o.reset();o.word(o.state+0xd370,credits);o.word(o.state+0xd372,credits>>16)
    o.write(o.state+0xd31a,[0]);o.write(o.state+0xc61d,[0]);o.write(o.state+0xc624,[0])
    o.call(0x14d3,4,15)
    rows.append(f'E {credits} {int.from_bytes(o.read(o.state+0xd370,4),"little")} '
        f'{o.read(o.state+0xc61d,1)[0]} {o.read(o.state+0xc624,1)[0]} {o.read(o.state+0xd31a,1)[0]}')
(ROOT/'tests/fixtures/training-combat-setup.txt').write_text(
    '# Original 07DC:0D49 and 14D3:0004(15); controlled prerequisites, no instruction patches.\n'+'\n'.join(rows)+'\n')
print(f'Wrote {len(rows)} original encounter/apprenticeship cases')
