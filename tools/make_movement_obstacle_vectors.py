#!/usr/bin/env python3
"""Original jump obstacle paths and four-sided invasion escape boundaries."""
import json
from combat_oracle import OriginalCombat, ROOT, UC_X86_REG_CS, UC_X86_REG_IP, UC_X86_REG_BP, UC_X86_REG_SP, UC_X86_REG_SS, UC_X86_REG_DS
from make_party_vectors import SNAP
from make_combat_vectors import fingerprint
from prepare_talk import EXE_SHA, IMAGE_SHA

def main():
    m=OriginalCombat(snapshot=SNAP);rows=[]
    for tile in (0,15,31,47,64,80,92,112,139,214):
        for mode in range(3):
            m.reset();m.word(m.ds+0x2e3a,0);m.word(m.state+0x14a,1);m.word(m.state+0xe48e,0)
            m.write(m.state+0x406a,bytes(48));m.word(m.state+0x406a,1)
            m.write(m.buffer+0x101d,bytes([64])*4096);m.write(m.state+0xc724,m.template(2))
            m.write(m.state+0xc618,bytes(5));m.write(m.state+0x5e,bytes(60));m.write(m.state+0x3800,bytes([255])*288)
            m.word(m.state+0x4004,0xc60);m.word(m.state+0x4036,0xc05d)
            m.write(m.state+0x32c6,bytes([mode,0xcc,105,93])+bytes([255])*44)
            # Controlled terrain prerequisite in private RAM, not edited assets.
            for x in (49,50):
                for y in range(64):m.write(m.buffer+0x101d+(y//8*8+x//8)*64+y%8*8+x%8,[tile])
            m.call(0x103b,0x1774,0,1,limit=2000000)
            rows.append(f'P {tile} {mode} {fingerprint(m.read(m.state+0x40b4,24)):016x}')
    cases=[(1534,1600),(1535,1600),(1536,1600),(1663,1600),(1664,1600),
        (1600,1534),(1600,1535),(1600,1536),(1600,1663),(1600,1664)]
    for x,y in cases:
        m.reset();m.word(m.state+0x3772,1);m.word(m.state+0x4004,(x//128)*256+x%128)
        m.word(m.state+0x4036,(y//128)*4096+y%128);bp=0x7f000;m.word(bp-0x38,0)
        for reg,value in ((UC_X86_REG_CS,m.load+0x103b),(UC_X86_REG_IP,0x610),(UC_X86_REG_DS,m.ds//16),
                (UC_X86_REG_SS,0x7000),(UC_X86_REG_BP,0xf000),(UC_X86_REG_SP,0xee00)):m.cpu.reg_write(reg,value)
        m.cpu.emu_start((m.load+0x103b)*16+0x610,(m.load+0x103b)*16+0x651,count=1000)
        if m.cpu.reg_read(UC_X86_REG_IP)!=0x651:raise RuntimeError('Escape boundary did not complete')
        rows.append(f'E {x} {y} {m.word(bp-0x38)}')
    (ROOT/'tests/fixtures/movement-obstacles-primary.txt').write_text('\n'.join(rows)+'\n')
    (ROOT/'tests/fixtures/movement-obstacles-primary.json').write_text(json.dumps(dict(
        executable_sha256=EXE_SHA,image_sha256=IMAGE_SHA,cases=len(rows),
        routines=['103B:1774 and 0E31:0006 path planning','103B:0610..0651 escape bounds'],
        prerequisites='Controlled open terrain with two-tile strip, Chameleon, walk/run/jump; packed-world boundary positions',
        comparison='Complete movement path fingerprints and original outside-Citadel result 2',intercepted_boundaries=[]),indent=2)+'\n')
    print('Original obstacle/escape cases:',len(rows))
if __name__=='__main__':main()
