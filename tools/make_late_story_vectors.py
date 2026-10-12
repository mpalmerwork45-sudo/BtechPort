#!/usr/bin/env python3
"""Execute original laser gifts, mayor meal and cinema exit numeric rules."""
import json
import struct
from combat_oracle import OriginalCombat,ROOT,UC_HOOK_CODE
from make_party_vectors import SNAP
from prepare_talk import EXE_SHA,IMAGE_SHA
from unicorn.x86_const import UC_X86_REG_SS,UC_X86_REG_SP,UC_X86_REG_IP,UC_X86_REG_CS,UC_X86_REG_AX

def main():
    m=OriginalCombat(snapshot=SNAP);answers=[];selected=[]
    boundaries={(0x1656,0x388),(0x1656,0x3f5),(0x1656,0xb5e),(0x14d3,0x181e),
        (0x173d,0x259),(0x173d,0x86a),(0,0x1a13)}
    absolute={(m.load+s)*16+o:(s,o) for s,o in boundaries}
    def hook(cpu,address,size,data):
        if address not in absolute:return
        where=absolute[address];sp=cpu.reg_read(UC_X86_REG_SP);ss=cpu.reg_read(UC_X86_REG_SS)*16
        if where in ((0,0x1a13),(0x1656,0xb5e)):
            if not answers:raise RuntimeError('Unexpected original input request')
            value=answers.pop(0);selected.append(value);cpu.reg_write(UC_X86_REG_AX,value)
        off,seg=struct.unpack('<HH',m.read(ss+sp,4));cpu.reg_write(UC_X86_REG_SP,sp+4)
        cpu.reg_write(UC_X86_REG_CS,seg);cpu.reg_write(UC_X86_REG_IP,off)
    handle=m.cpu.hook_add(UC_HOOK_CODE,hook);rows=[]
    for n in (1,2,4,8):
        for seed in (0,1,42,0xd23646):
            for yes in (0,1):
                m.reset();selected.clear();people=bytearray()
                for i in range(8):
                    people+=bytes((i if i<n else 255,8,9,7,0,0,0,0,1,0,0,9,8,0,0,80,0))
                m.write(m.state+0xc614,people);m.write(m.state+0xd31a,[n-1]);m.write(m.ds+0x4fc0,seed.to_bytes(3,'little'))
                # One recipient per new laser, then Cancel redistribution of
                # the displaced weapon. The solo original asks Yes/No instead.
                answers[:]=[yes] if n==1 else [v for i in range(n) for v in (i,n)]
                m.call(0x14d3,4,41,limit=100000)
                if answers:raise RuntimeError('Original did not consume the documented gift choices')
                after=m.read(m.state+0xc614,136);rng=int.from_bytes(m.read(m.ds+0x4fc0,3),'little')
                rows.append(f'L {n} {seed} {yes} {rng} '+' '.join(f'{after[17*i+11]} {after[17*i+15]}' for i in range(n)))
    for health in (0,1,4,5,6,7,8,40,76,80,120):
        m.reset();m.write(m.state+0xc623,[health]);m.call(0x14d3,4,47,limit=10000)
        rows.append(f'M {health} {m.read(m.state+0xc623,1)[0]}')
    for x,y in ((0x052f,0xd00a),(0x0204,0x603e),(0x092f,0xb032)):
        m.reset();m.word(m.buffer+0xa44b,x);m.word(m.buffer+0xa44d,y);m.call(0x14d3,4,42,limit=10000)
        rows.append(f'C {x} {y} {m.word(m.buffer+0xa44d)} '+' '.join(str(v) for i in range(8) for v in m.read(m.state+0xd398+26*i,2)))
    m.cpu.hook_del(handle)
    (ROOT/'tests/fixtures/late-story-primary.txt').write_text('\n'.join(rows)+'\n')
    (ROOT/'tests/fixtures/late-story-primary.json').write_text(json.dumps(dict(
        executable_sha256=EXE_SHA,image_sha256=IMAGE_SHA,routine='14D3:0004 actions 41, 42, 47; original 07DC:15E6 weapon redistribution',
        cases=len(rows),prerequisites='1/2/4/8 party records, four original RNG seeds, solo Yes/No and explicit recipient/Cancel input, meal health boundaries, packed exit coordinates',
        intercepted_boundaries=sorted(f'{s:04X}:{o:04X}' for s,o in boundaries),
        comparison='Weapons, health, exact RNG, exit coordinate and eight NPC room/counter bytes; original instructions unmodified'),indent=2)+'\n')
    print('Primary late-story numeric cases:',len(rows))

if __name__=='__main__':main()
