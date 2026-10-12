#!/usr/bin/env python3
"""Execute original cache rules with bounded presentation/device boundaries.

Original instructions are unchanged; only UI, sound and map redraw calls are
intercepted. Fixtures contain numeric results and source identities only.
"""
import json,struct
from pathlib import Path
from combat_oracle import OriginalCombat,ROOT
from make_party_vectors import SNAP
from prepare_talk import EXE_SHA,IMAGE_SHA
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_SS,UC_X86_REG_SP,UC_X86_REG_IP,UC_X86_REG_CS,UC_X86_REG_AX

def fnv(data):
    h=0xcbf29ce484222325
    for b in data:h=((h^b)*0x100000001b3)&0xffffffffffffffff
    return h
def normalized(raw,width):
    return bytes(raw[((y//8)*(width//8)+x//8)*64+(y%8)*8+x%8] for y in range(len(raw)//width) for x in range(width))

def main():
    m=OriginalCombat(snapshot=SNAP);answer=1;sounds=[]
    boundaries={(0x14d3,0x17c6),(0x14d3,0x17ea),(0x1656,0x3f5),(0x1656,0x388),
        (0x173d,0x259),(0x173d,0x53),(0x173d,0x86a),(0x173d,6),(0x173d,0x6c3),
        (0x187f,0x1314),(0x187f,0x1f04),(0x187f,0x18ef),(0,0x51b),(0,0x19bf),(0,0x1a13)}
    absolute={(m.load+segment)*16+offset:(segment,offset) for segment,offset in boundaries}
    def hook(cpu,address,size,data):
        if address not in absolute:return
        where=absolute[address];sp=cpu.reg_read(UC_X86_REG_SP);ss=cpu.reg_read(UC_X86_REG_SS)*16
        if where==(0,0x19bf):sounds.append(m.word(ss+sp+4))
        if where==(0,0x1a13):cpu.reg_write(UC_X86_REG_AX,answer)
        off,seg=struct.unpack('<HH',m.read(ss+sp,4))
        cpu.reg_write(UC_X86_REG_SP,sp+4);cpu.reg_write(UC_X86_REG_CS,seg);cpu.reg_write(UC_X86_REG_IP,off)
    handle=m.cpu.hook_add(UC_HOOK_CODE,hook)
    rows=['# Original 0B5D cache terminal, door, secret and password rules; UI/device boundaries only.']
    tx=m.read(m.ds+0x21ce,33);ty=m.read(m.ds+0x21f0,33)
    for i in range(33):
        for used in range(2):
            for answer in range(2):
                m.reset();m.write(m.state+0xd347,b'\xff'*3);m.write(m.state+0x45de,bytes(33));m.write(m.state+0x45de+i,bytes([used]))
                m.call(0xb5d,0x3aa,tx[i]-1,ty[i],limit=10000)
                rows.append(f'T {i} {used} {answer} '+' '.join(map(str,m.read(m.state+0xd347,3))))
    raw=(ROOT/'Original DOS/MAP14.MTP').read_bytes()[541:]
    dx=m.read(m.ds+0x247a,12);dy=m.read(m.ds+0x2486,12)
    requirements=[m.read(m.ds+address,12) for address in (0x2492,0x249e,0x24aa)]
    for i in range(12):
        for missing in range(8):
            m.reset();m.write(m.buffer+0x101d,raw);m.write(m.state+0x45de,bytes(33));m.write(m.state+0xd34f,bytes(12));sounds.clear()
            cards=bytes(255 if missing&(1<<c) or i==11 else requirements[c][i]-1 for c in range(3))
            m.write(m.state+0xd347,cards)
            m.call(0xb5d,0xab6,dx[i]-1,dy[i],-1,limit=20000)
            changed=normalized(m.read(m.buffer+0x101d,4096),64)
            rows.append(f'D {i} {missing} {m.read(m.state+0xd34f+i,1)[0]} {fnv(changed):016x} {fnv(m.read(m.state+0x45de,33)):016x} {sounds.count(10)}')
    m.reset();m.write(m.buffer+0x101d,raw);m.call(0xb5d,0x1e9,limit=10000)
    rows.append(f'S {fnv(normalized(m.read(m.buffer+0x101d,4096),64)):016x}')
    puzzle=(ROOT/'Original DOS/MAP15.MTP').read_bytes();wanted=struct.unpack('<7H',m.read(m.ds+0x241e,14))
    for raw_index,value in enumerate(puzzle):
        if not 151<=value<=240:continue
        m.reset();m.write(m.buffer+0x101d,puzzle);sounds.clear()
        x=(raw_index//64%4)*8+raw_index%8;y=raw_index//64//4*8+raw_index%64//8
        m.call(0xb5d,0x913,2*x-1,2*y,limit=10000)
        rows.append(f'X {x} {y} {m.read(m.buffer+0x101d+raw_index,1)[0]} {sounds.count(15)}')
    for mask in range(128):
        for extra in range(2):
            m.reset();p=bytearray(puzzle)
            for i,index in enumerate(wanted):
                if mask&(1<<i):p[index]+=1
            if extra:p[next(i for i,v in enumerate(p) if 151<=v<=240 and i not in wanted)]+=1
            m.write(m.buffer+0x101d,p);m.write(m.state+0xd34a,b'\0');sounds.clear()
            m.call(0xb5d,0x980,limit=100000)
            rows.append(f'P {mask} {extra} {m.read(m.state+0xd34a,1)[0]} {fnv(normalized(m.read(m.buffer+0x101d,768),32)):016x} {sounds[-1]}')
    m.cpu.hook_del(handle)
    (ROOT/'tests/fixtures/cache-primary.txt').write_text('\n'.join(rows)+'\n')
    (ROOT/'tests/fixtures/cache-primary.json').write_text(json.dumps(dict(
        executable_sha256=EXE_SHA,image_sha256=IMAGE_SHA,cases=len(rows)-1,
        routines=['0B5D:03AA','0B5D:0AB6','0B5D:01E9','0B5D:0913','0B5D:0980'],
        prerequisites='Fresh original MAP14/MAP15 payloads, explicit used-terminal/card state and all 128 password subsets with/without an extra symbol',
        intercepted_boundaries=sorted(f'{s:04X}:{o:04X}' for s,o in boundaries),
        comparison='Code IDs, door flags, consumed-terminal/map fingerprints, password flags/reset and sound dispatch; original instructions unchanged'),indent=2)+'\n')
    print('Primary cache numeric cases:',len(rows)-1)
if __name__=='__main__':main()
