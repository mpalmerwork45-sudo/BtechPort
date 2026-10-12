#!/usr/bin/env python3
"""Execute original visibility updates and TINYLAND terrain selection.

Only numeric projections and source identities enter the repository. The
movement span has explicit cursor/stack prerequisites; no instructions change.
"""
import json
from combat_oracle import OriginalCombat,ROOT
from make_party_vectors import SNAP
from prepare_talk import EXE_SHA,IMAGE_SHA
from unicorn.x86_const import (UC_X86_REG_CS,UC_X86_REG_IP,UC_X86_REG_DS,
    UC_X86_REG_SS,UC_X86_REG_BP,UC_X86_REG_SP)

def fnv(data):
    h=0xcbf29ce484222325
    for b in data:h=((h^b)*0x100000001b3)&0xffffffffffffffff
    return h

def fog(m,x,y,mapper):
    m.reset();m.write(m.state+0xcb0c,bytes(2048))
    m.write(m.state+0xd33d,bytes([mapper]));m.write(m.state+0xd346,b'\0')
    m.word(m.buffer+0xa44b,(x//128<<8)|(x&127))
    m.word(m.buffer+0xa44d,(y//128<<12)|(y&127))
    for reg,value in ((UC_X86_REG_CS,m.load),(UC_X86_REG_IP,0x10b),
        (UC_X86_REG_DS,m.ds//16),(UC_X86_REG_SS,0x7000),
        (UC_X86_REG_SP,0xee00),(UC_X86_REG_BP,0xf000)):
        m.cpu.reg_write(reg,value)
    m.cpu.emu_start(m.load*16+0x10b,m.load*16+0x20a,count=2000)
    if m.cpu.reg_read(UC_X86_REG_IP)!=0x20a:raise RuntimeError('Visibility span exceeded bound')
    return fnv(m.read(m.state+0xcb0c,2048))

def main():
    m=OriginalCombat(snapshot=SNAP);rows=['# Executed original movement visibility and 187F:1F04 mini tile selection.']
    for mapper in range(2):
        for x in (16,31,32,48,64,80,96,112,127,128,1536,1605,2032):
            for y in (16,127,128,1561,2000):rows.append(f'F {x} {y} {mapper} {fog(m,x,y,mapper):016x}')
    for level in (0,16,32,48,64,80,128,144,255):
        for mask in range(16):
            m.reset();m.write(m.buffer+0x664,bytes([level])*64);m.write(m.buffer+0x424,bytes([mask])*64)
            m.call(0x187f,0x1f04,0,limit=2000)
            rows.append(f'T {level} {mask} {m.read(m.buffer+0x244b,1)[0]}')
    (ROOT/'tests/fixtures/world-view-primary.txt').write_text('\n'.join(rows)+'\n')
    (ROOT/'tests/fixtures/world-view-primary.json').write_text(json.dumps(dict(
        executable_sha256=EXE_SHA,image_sha256=IMAGE_SHA,fog_span='0000:010B..020A',
        mini_routine='187F:1F04',fog_cases=130,terrain_cases=144,
        initial_fog=dict(snapshot='1791789043720104596/first-time-question',rows=[98,99,100,101,102,103],byte=12,value=31),
        comparison='2048-byte visibility fingerprints and numeric mini indices; no whole-screen map equivalence claimed'),indent=2)+'\n')
    print('Primary world-view cases:',len(rows)-1)
if __name__=='__main__':main()
