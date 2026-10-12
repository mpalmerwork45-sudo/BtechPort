#!/usr/bin/env python3
"""Numeric original ejection, salvage and pocket-cash spans; explicit callers."""
from pathlib import Path
from combat_oracle import OriginalCombat,ROOT
from make_party_vectors import fingerprint,SNAP
from unicorn.x86_const import (UC_X86_REG_CS,UC_X86_REG_IP,UC_X86_REG_DS,UC_X86_REG_SS,UC_X86_REG_SP,UC_X86_REG_BP,UC_X86_REG_ES)

def span(m,segment,start,end,locals,stack_data=False):
    bp=m.ds+0xe000 if stack_data else 0x7f000;m.write(bp-0x100,bytes(0x120))
    for off,value in locals.items():m.word(bp+off,value)
    for reg,value in ((UC_X86_REG_CS,m.load+segment),(UC_X86_REG_IP,start),(UC_X86_REG_DS,m.ds//16),
            (UC_X86_REG_ES,m.state//16),(UC_X86_REG_SS,m.ds//16 if stack_data else 0x7000),(UC_X86_REG_SP,0xdd00 if stack_data else 0xee00),(UC_X86_REG_BP,0xe000 if stack_data else 0xf000)):m.cpu.reg_write(reg,value)
    m.cpu.emu_start((m.load+segment)*16+start,(m.load+segment)*16+end,count=1000000)
    if m.cpu.reg_read(UC_X86_REG_IP)!=end:raise RuntimeError('Aftermath instruction bound exceeded')

def main():
    m=OriginalCombat(snapshot=SNAP);rows=['# Unmodified primary spans; positions/records/ranks/RNG are caller prerequisites.']
    for count in range(9):
        for seed in (0,1,42,0xffffff,0xd23646):
            m.reset();m.write(m.ds+0x4fc0,seed.to_bytes(3,'little'))
            span(m,0x5ab,0x9ec,0xa11,{-4:count,-8:0})
            rows.append(f'R {count} {seed} {m.word(0x7f000-8)} {int.from_bytes(m.read(m.ds+0x4fc0,3),"little")}')
    for skill in range(6):
        for variant in range(8):
            m.reset();b=bytearray(m.template());b[117]=3 if variant&1 else 0;b[118]=2 if variant&2 else 0;b[31]=0 if variant&4 else 3
            m.write(m.state+0xc918,b)
            span(m,0x5ab,0x5ad,0x5e1,{-2:4,-20:skill})
            rows.append(f'S {skill} {variant} {m.word(0x7f000-8)}')
    for loan in range(3):
        for pilot in (0,1,7):
            m.reset();b=bytearray(m.template(loan));kind=b[0];b[0]=255;b[117]=3;b[118]=2;b[31]=b[32]=0
            m.write(m.state+0xc918,b);m.write(m.state+0xc724,bytes([255])+bytes(124));m.write(m.state+0xc614+17*pilot,bytes([pilot])+bytes(11)+bytes([8])+bytes(4));m.write(m.state+0x323e+4,[kind])
            span(m,0x5ab,0x6e2,0x7ad,{-2:4,-6:1,-10:0,-14:pilot})
            rows.append(f'C {loan} {pilot} {fingerprint(m.read(m.state+0xc724,125))} {m.read(m.state+0xc620+17*pilot,1)[0]}')
    for slot in range(4):
        for pilot,second in ((0,255),(0,1),(7,6)):
            m.reset();b=bytearray(m.template());b[121]=pilot;b[122]=second;m.write(m.state+0xc724+125*slot,b)
            for member in range(8):m.write(m.state+0xc614+17*member,bytes([member,8,9,7,0,0,0,1,1,1,0,9,slot,3,30,80,0]))
            m.word(m.state+0xe48e,0);m.word(m.ds+0x15e,2);m.word(m.state+0x4004+2*slot,0xc40);m.word(m.state+0x4036+2*slot,0xc04d)
            seed=m.read(m.ds+0x4fc0,3);m.call(0xd43,0xa35,slot,limit=1000000)
            if seed!=m.read(m.ds+0x4fc0,3):raise RuntimeError('Unexpected ejection RNG')
            values=[m.read(m.state+0xc724+125*slot,1)[0],m.word(m.state+0x393c+2*slot)]
            for member in (pilot,second):
                if member==255:values += [255,0,0,0]
                else:values += [m.read(m.state+0xc620+17*member,1)[0],m.word(m.state+0x4072+2*member),m.word(m.state+0x400c+2*member)&127,m.word(m.state+0x403e+2*member)&127]
            rows.append(f'E {slot} {pilot} {second} '+ ' '.join(map(str,values)))
    (ROOT/'tests/fixtures/aftermath-primary.txt').write_text('\n'.join(rows)+'\n');print('Original aftermath numeric cases:',len(rows)-1)
if __name__=='__main__':main()
