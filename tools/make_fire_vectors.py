#!/usr/bin/env python3
"""Capture original flame-marker dice, offsets, ring wrap and terrain invariance."""
from combat_oracle import OriginalCombat, ROOT

o=OriginalCombat(snapshot=ROOT/'work/reference-runs/1791709609448346900/combat-menu')
rows=['# Original 12E8:1E46 and 103B:27C9; visual flame ring, unchanged terrain grid.']
for case in range(128):
    o.reset();seed=12345+case*78101;kind=case%2;unit=16 if kind else 12
    x=64+case%32;y=72+case%24;next=(case%4)*21
    o.write(o.state+0xd457,bytes(256));o.word(o.state+0xd557,next)
    o.word(o.state+0x4004+2*unit,0xc00+x);o.word(o.state+0x4036+2*unit,0xc000+y)
    o.word(o.ds+0x2e3a,0);o.call(0,0x17bb,0xc00+x,0xc000+y)
    before=o.read(o.buffer+0x7ad,576);o.write(o.ds+0x4fc0,seed.to_bytes(3,'little'))
    o.call(0x12e8,0x1e46,unit,-1 if kind else 0,0 if kind else -1)
    sprite=o.read(o.state+0xd457+next,1)[0]
    mx=o.read(o.state+0xd4d7+next,1)[0];my=o.read(o.state+0xd517+next,1)[0]
    o.call(0,0x17bb,0xc00+x,0xc000+y);o.call(0x173d,0x6c3)
    unchanged=int(before==o.read(o.buffer+0x7ad,576))
    if not unchanged:raise RuntimeError('Original terrain grid changed after flame insertion')
    rows.append(f'F {seed} {kind} {x} {y} {next} {o.word(o.state+0xd557)} {sprite} {mx} {my} '
        f'{int.from_bytes(o.read(o.ds+0x4fc0,3),"little")} {unchanged}')
(ROOT/'tests/fixtures/combat-fire.txt').write_text('\n'.join(rows)+'\n')
print(f'Wrote {len(rows)-1} original flame/ring/terrain cases')
