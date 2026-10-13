#!/usr/bin/env python3
"""Execute actions 31/32 in the original dispatcher, with explicit UI replies."""
import json
import struct
from combat_oracle import OriginalCombat, ROOT, UC_HOOK_CODE
from make_party_vectors import SNAP
from prepare_talk import EXE_SHA, IMAGE_SHA
from unicorn.x86_const import UC_X86_REG_SS, UC_X86_REG_SP, UC_X86_REG_IP, UC_X86_REG_CS, UC_X86_REG_AX

def main():
    m=OriginalCombat(snapshot=SNAP);reply=0;questions=0
    boundaries={(0x1656,0x3f5),(0x173d,0x53),(0x173d,0x259),(0,0x1a13),(0xe31,0x1fdf)}
    absolute={(m.load+s)*16+o:(s,o) for s,o in boundaries}
    def hook(cpu,address,size,data):
        nonlocal questions
        if address not in absolute:return
        if absolute[address]==(0,0x1a13):
            cpu.reg_write(UC_X86_REG_AX,reply);questions+=1
        sp=cpu.reg_read(UC_X86_REG_SP);ss=cpu.reg_read(UC_X86_REG_SS)*16
        off,seg=struct.unpack('<HH',m.read(ss+sp,4))
        cpu.reg_write(UC_X86_REG_SP,sp+4);cpu.reg_write(UC_X86_REG_CS,seg);cpu.reg_write(UC_X86_REG_IP,off)
    handle=m.cpu.hook_add(UC_HOOK_CODE,hook);rows=[]
    for member in (0,3):
        for kind in range(1,6):
            capacity=m.image[0x36db0+0x4ddc+kind-1]
            for points in (0,capacity-3,capacity):
                for funds in (0,1,2,19,60,1000):
                    for reply in (0,1):
                        m.reset();questions=0;at=m.state+0xc614+17*member
                        m.write(at,[member]);m.write(at+13,[kind,points]);m.write(m.state+0xd31a,[member])
                        m.write(m.state+0xd370,funds.to_bytes(4,'little'))
                        m.call(0x14d3,4,31);flag=m.read(m.state+0xd32b,1)[0]
                        m.call(0x14d3,4,32,limit=300000)
                        rows.append(f'{member} {kind} {points} {funds} {reply} {flag} {m.read(at+14,1)[0]} '+
                            f'{int.from_bytes(m.read(m.state+0xd370,4),"little")} {questions}')
    m.cpu.hook_del(handle)
    (ROOT/'tests/fixtures/armour-repair-primary.txt').write_text('\n'.join(rows)+'\n')
    (ROOT/'tests/fixtures/armour-repair-primary.json').write_text(json.dumps(dict(
        executable_sha256=EXE_SHA,image_sha256=IMAGE_SHA,cases=len(rows),
        routine='14D3:0004 actions 31/32, entries 0EDA/0EF3; ARMOR.BLD',
        prerequisites='Two selected members, five armour types, destroyed/partial/full capacity, six balances, Yes/No',
        intercepted_boundaries=[f'{s:04X}:{o:04X}' for s,o in sorted(boundaries)],
        comparison='Armour ID flag, restored protection, remaining money and confirmation count; original instructions unchanged'),indent=2)+'\n')
    print('Original armour repair cases:',len(rows))
if __name__=='__main__':main()
