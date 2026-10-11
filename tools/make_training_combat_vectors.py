#!/usr/bin/env python3
"""Capture original fourth/sixth encounter setup, results and apprenticeship."""
import random
from combat_oracle import OriginalCombat,ROOT
from make_combat_vectors import fingerprint
from unicorn.x86_const import (UC_X86_REG_CS, UC_X86_REG_IP, UC_X86_REG_DS,
    UC_X86_REG_ES, UC_X86_REG_SS, UC_X86_REG_BP, UC_X86_REG_SP, UC_X86_REG_EFLAGS)

snapshot=ROOT/'work/reference-runs/1791709609448346900/combat-menu'
o=OriginalCombat(snapshot=snapshot);rows=[];source=random.Random(1988)
for assignment in [3,4,5]:
    for n in range(48):
        o.reset();seed=source.randrange(1,1<<24);o.write(o.ds+0x4fc0,seed.to_bytes(3,'little'))
        o.write(o.state+0xd30c,[assignment]);o.write(o.state+0xd30f,[0])
        o.word(o.state+0x3772,0);o.word(o.state+0xe48e,0)
        count=3+(o.call(0x187f,0xbc0)&3) if assignment==3 else assignment-3
        o.call(0x7dc,0xd49,0 if assignment==3 else count,count if assignment==3 else 0)
        row=f'B {assignment} {seed} {n%3} {count+1} {int.from_bytes(o.read(o.ds+0x4fc0,3),"little")}'
        for i in range(count):
            u=16+i if assignment==3 else 12+i
            record=o.read(o.state+(0xc69c+17*i if assignment==3 else 0xc918+125*i),17 if assignment==3 else 125)
            frame=o.read(o.state+0x409a+u,1)[0]-(16 if assignment==3 else 0)
            row+=f' {o.word(o.state+0x4004+2*u)&127} {o.word(o.state+0x4036+2*u)&127} {fingerprint(record):016x} {frame}'
        rows.append(row)
for gunnery in range(5):
    for kicking in range(5):
        for outcome in range(3):
            for seed in (123456, 4321987, 15678901):
                o.reset();o.write(o.ds+0x4fc0,seed.to_bytes(3,'little'))
                o.write(o.state+0xc61b,[gunnery,kicking]);o.write(o.state+0xd30d,[0])
                o.write(o.state+0xc724,[255 if outcome==2 else ord('C')])
                o.word(o.state+0x3992,int(outcome==1));o.word(0x7f006,5)
                for reg,value in ((UC_X86_REG_CS,o.load+0x7dc),(UC_X86_REG_IP,0xc80),
                        (UC_X86_REG_DS,o.ds//16),(UC_X86_REG_ES,o.state//16),
                        (UC_X86_REG_SS,0x7000),(UC_X86_REG_BP,0xf000),
                        (UC_X86_REG_SP,0xef00),(UC_X86_REG_EFLAGS,2)):
                    o.cpu.reg_write(reg,value)
                o.cpu.emu_start((o.load+0x7dc)*16+0xc80,(o.load+0x7dc)*16+0xcee,count=200000)
                if o.cpu.reg_read(UC_X86_REG_IP)!=0xcee:raise RuntimeError('Result span exceeded bound')
                after=list(o.read(o.state+0xc61b,2));result=o.read(o.state+0xd30d,1)[0]
                rows.append(f'R {seed} {gunnery} {kicking} {outcome} {result} {after[0]} {after[1]} '
                    f'{int.from_bytes(o.read(o.ds+0x4fc0,3),"little")}')
for credits in [0,35,499,500,501,65535,65536,1000000,0xffffffff]:
    o.reset();o.word(o.state+0xd370,credits);o.word(o.state+0xd372,credits>>16)
    o.write(o.state+0xd31a,[0]);o.write(o.state+0xc61d,[0]);o.write(o.state+0xc624,[0])
    o.call(0x14d3,4,15)
    rows.append(f'E {credits} {int.from_bytes(o.read(o.state+0xd370,4),"little")} '
        f'{o.read(o.state+0xc61d,1)[0]} {o.read(o.state+0xc624,1)[0]} {o.read(o.state+0xd31a,1)[0]}')
(ROOT/'tests/fixtures/training-combat-setup.txt').write_text(
    '# Original 07DC:0D49, 07DC:0C80..0CEE and 14D3:0004(15); explicit prerequisites, no patches.\n'+'\n'.join(rows)+'\n')
print(f'Wrote {len(rows)} original encounter/apprenticeship cases')
