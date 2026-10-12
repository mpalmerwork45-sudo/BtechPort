#!/usr/bin/env python3
"""Primary seventh/eighth branch, opening and enemy setup comparisons."""
from combat_oracle import OriginalCombat,ROOT
from make_combat_vectors import fingerprint
from unicorn.x86_const import (UC_X86_REG_CS,UC_X86_REG_IP,UC_X86_REG_DS,
    UC_X86_REG_ES,UC_X86_REG_SS,UC_X86_REG_BP,UC_X86_REG_SP,UC_X86_REG_EFLAGS)

o=OriginalCombat(snapshot=ROOT/'work/reference-runs/1791709609448346900/combat-menu');rows=[]
for assignment in [6,7]:
    for seed in [1,123456,4321987,15678901,785435,92841,16777215,1000]:
        o.reset();o.write(o.ds+0x4fc0,seed.to_bytes(3,'little'))
        o.call(0x187f,0xbc0) # Original launch animation dispatcher draw.
        o.word(o.state+0x3772,0);o.write(o.state+0xd30c,[assignment]);o.write(o.state+0xd30f,[0])
        o.word(0x7f006,assignment)
        for reg,value in [(UC_X86_REG_CS,o.load+0x7dc),(UC_X86_REG_IP,0x765),
            (UC_X86_REG_DS,o.ds//16),(UC_X86_REG_ES,o.state//16),
            (UC_X86_REG_SS,0x7000),(UC_X86_REG_BP,0xf000),(UC_X86_REG_SP,0xef00),(UC_X86_REG_EFLAGS,2)]:
            o.cpu.reg_write(reg,value)
        o.cpu.emu_start((o.load+0x7dc)*16+0x765,(o.load+0x7dc)*16+0x7c3,count=200000)
        if o.cpu.reg_read(UC_X86_REG_IP)!=0x7c3:raise RuntimeError('Branch bound')
        invasion=o.word(o.state+0x3772)
        if invasion and o.read(o.buffer+0x101d+0xff0,16)!=bytes([64])*16:raise RuntimeError('Opening differs')
        o.call(0x7dc,0xd49,assignment-3,0);count=4 if invasion else assignment-3
        row=f'P {assignment} {seed} {invasion} {count+1} {int.from_bytes(o.read(o.ds+0x4fc0,3),"little")}'
        for i in range(count):
            row+=f' {o.word(o.state+0x4004+2*(12+i))&127} {o.word(o.state+0x4036+2*(12+i))&127} '
            row+=f'{fingerprint(o.read(o.state+0xc918+125*i,125)):016x}'
        rows.append(row)
(ROOT/'tests/fixtures/invasion-setup.txt').write_text(
    '# Original 07DC:0765..07C3 and 0D49; O0 draw prerequisite; branch/opening/records/RNG.\n'+'\n'.join(rows)+'\n')
print(f'Captured {len(rows)} original seventh/eighth cases')
