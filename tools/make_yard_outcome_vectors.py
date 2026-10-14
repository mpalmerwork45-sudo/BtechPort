#!/usr/bin/env python3
"""Execute original arena/prison restoration for explicit combat outcomes.

The combat/minigame call is a declared prerequisite boundary, not a played win.
All backup, restore, full-garage and ownership instructions execute unchanged.
"""
import json,struct
from combat_oracle import OriginalCombat,ROOT,UC_HOOK_CODE
from make_party_vectors import SNAP
from make_combat_vectors import fingerprint
from prepare_talk import EXE_SHA,IMAGE_SHA
from unicorn.x86_const import UC_X86_REG_SS,UC_X86_REG_SP,UC_X86_REG_IP,UC_X86_REG_CS

def main():
    m=OriginalCombat(snapshot=SNAP);selected=0;stolen=0;destroyed=0;prison=0
    boundaries={(0,0x48b7),(0x7dc,0x629),(0xc67,0xb98),(0x1656,0x388),(0x1656,0x3f5),
        (0x173d,0x259),(0x187f,0x104e),(0x187f,0x1da8),(0,0x2da8),(0xd43,0xc72)}
    absolute={(m.load+s)*16+o:(s,o) for s,o in boundaries}
    def hook(cpu,address,size,data):
        if address not in absolute:return
        where=absolute[address];sp=cpu.reg_read(UC_X86_REG_SP);ss=cpu.reg_read(UC_X86_REG_SS)*16
        if where==(0xc67,0xb98):m.word(m.state+0x68,selected)
        if where==(0x7dc,0x629):
            m.word(m.ds+0x14a,0 if destroyed else 1)
            m.word(m.state+0x406a,0 if destroyed else 1);m.word(m.state+0x4036,0x8066)
            if prison:
                if destroyed:m.write(m.state+0xd334,[1])
            else:
                m.write(m.state+0xd32f,[stolen]);m.write(m.state+0xc724+17,[2])
                if destroyed:m.write(m.state+0xc724,[255])
        off,seg=struct.unpack('<HH',m.read(ss+sp,4));cpu.reg_write(UC_X86_REG_SP,sp+4)
        cpu.reg_write(UC_X86_REG_CS,seg);cpu.reg_write(UC_X86_REG_IP,off)
    handle=m.cpu.hook_add(UC_HOOK_CODE,hook);rows=[];parking=[]
    templates=[m.template(),m.image[0x282e7:0x282e7+125],m.image[0x2826a:0x2826a+125],m.image[0x281ed:0x281ed+125]]
    def setup(count):
        m.reset();m.write(m.state+0xc614,bytes(v for i in range(8) for v in [i if i<5 else 255,8,9,7,0,0,0,0,1,0,0,9,8,0,0,80,0]))
        m.write(m.state+0xd452,[templates[i][0] if i<count else 255 for i in range(4)])
        for i in range(4):
            record=bytearray(templates[i] if i<count else bytes([255])+bytes(124));record[121]=record[122]=255
            m.write(m.state+0xc724+125*i,record)
        m.word(m.ds+0x14a,1);m.write(m.state+0xd334,[0]);m.write(m.state+0xd32f,[0])
    def result(prefix):
        tags=m.read(m.state+0xd452,4);records=[]
        # Keep the raw active bytes too: projecting parked ownership in the
        # older record hashes hid accidental reactivation on arena return.
        parking.append(prefix+' '+' '.join(str(m.read(m.state+0xc724+125*i,1)[0]) for i in range(4)))
        for i in range(4):
            b=bytearray(m.read(m.state+0xc724+125*i,121))
            if b[0]==255 and tags[i]!=255:b[0]=tags[i] # Logical parked ownership projection.
            records.append(f'{fingerprint(b):016x}')
        rows.append(prefix+f' {m.read(m.state+0xd334,1)[0]} '+ ' '.join(records))
    for count in (0,1,3,4):
        for stolen in range(2):
            for destroyed in range(2):
                prison=0;selected=0;setup(count);m.call(0x14d3,4,33);m.call(0x14d3,4,35,limit=1000000)
                result(f'A 1 {count} 0 {stolen} {destroyed}')
    for selected in range(4):
        for destroyed in range(2):
            prison=0;stolen=0;setup(4);m.call(0x14d3,4,34,limit=1000000);m.call(0x14d3,4,35,limit=1000000)
            result(f'A 0 4 {selected} 0 {destroyed}')
    for count in (0,1,3,4):
        for destroyed in range(2):
            prison=1;selected=0;stolen=0;setup(count);m.call(0x14d3,4,40,limit=1000000)
            result(f'P {count} {destroyed}')
    m.cpu.hook_del(handle)
    (ROOT/'tests/fixtures/yard-outcomes-primary.txt').write_text('\n'.join(rows)+'\n')
    (ROOT/'tests/fixtures/yard-parking-primary.txt').write_text('\n'.join(parking)+'\n')
    (ROOT/'tests/fixtures/yard-outcomes-primary.json').write_text(json.dumps(dict(
        executable_sha256=EXE_SHA,image_sha256=IMAGE_SHA,cases=len(rows),
        routines='14D3:0004 actions 33/34/35/40, original owned/rental/prison restoration helpers',
        prerequisites='0/1/3/4 owned bays, four owned selections, normal/stolen, surviving/destroyed vehicle. Combat/minigame result supplied at 07DC:0629.',
        intercepted_boundaries=[f'{s:04X}:{o:04X}' for s,o in sorted(boundaries)],
        comparison='Failure flag and four 121-byte vehicle fingerprints; parked tag projected from D452. The separate yard-parking-primary.txt retains all four raw active bytes, without that projection. Crew allocation is a subsequent UI boundary. No claim that these supplied outcomes were played battles.'),indent=2)+'\n')
    print('Original yard restoration outcomes:',len(rows))
if __name__=='__main__':main()
