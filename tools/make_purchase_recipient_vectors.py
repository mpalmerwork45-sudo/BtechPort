#!/usr/bin/env python3
"""Run original shop payment and recipient/swap loops with explicit menu replies."""
import json
import struct
from combat_oracle import OriginalCombat, ROOT, UC_HOOK_CODE
from make_party_vectors import SNAP
from make_combat_vectors import fingerprint
from prepare_talk import EXE_SHA, IMAGE_SHA
from unicorn.x86_const import UC_X86_REG_AX, UC_X86_REG_CS, UC_X86_REG_IP, UC_X86_REG_SP, UC_X86_REG_SS


def main():
    m=OriginalCombat(snapshot=SNAP);answers=[];notices=0
    boundaries={(0x1656,0x388),(0x1656,0x3f5),(0x1656,0xb5e),(0x14d3,0x181e),
                (0x173d,0x53),(0x173d,0x86a),(0x173d,0x259),(0xe31,0x1fdf),(0,0x2867)}
    absolute={(m.load+s)*16+o:(s,o) for s,o in boundaries}
    def hook(cpu,address,size,data):
        nonlocal notices
        if address not in absolute:return
        if absolute[address]==(0x1656,0xb5e):
            if not answers:raise RuntimeError('Unexpected recipient input')
            cpu.reg_write(UC_X86_REG_AX,answers.pop(0))
        if absolute[address]==(0,0x2867):notices+=1
        sp=cpu.reg_read(UC_X86_REG_SP);ss=cpu.reg_read(UC_X86_REG_SS)*16
        off,seg=struct.unpack('<HH',m.read(ss+sp,4))
        cpu.reg_write(UC_X86_REG_SP,sp+4);cpu.reg_write(UC_X86_REG_CS,seg);cpu.reg_write(UC_X86_REG_IP,off)
    h=m.cpu.hook_add(UC_HOOK_CODE,hook);rows=[]
    for pattern,slots in enumerate(([0],[0,1],[0,1,2,3],list(range(8)),[0,3,7])):
        for armour,choice,price in ((0,1,2),(0,11,1500),(1,1,50),(1,4,10000)):
            for path in range(4):
                for funded in range(2):
                    m.reset();notices=0;n=len(slots);cash=price+100 if funded else price-1
                    people=bytearray()
                    for i in range(8):
                        people+=bytes([i if i in slots else 255,8,9,7,2,2,2,2,1,2,2,9,8,2,17,80,0])
                    if path==3:
                        at=17*slots[-1]+(13 if armour else 11);people[at]=choice
                    m.write(m.state+0xc614,people);m.write(m.state+0xd370,cash.to_bytes(4,'little'))
                    ui=m.word(m.ds+0x56b6)*16;m.write(m.state+0xd316,[0]);m.write(m.state+0xd318,[9 if choice>9 else 0])
                    m.word(ui+0x178,choice);m.word(ui+0x198,choice);m.word(ui+0x1b8,choice-9)
                    sequence=([n-1,n] if path in (0,3) else [n-1,0,n] if path==1 else [n]) if n>1 and funded else []
                    answers[:]=sequence
                    m.call(0x14d3,4,9 if armour else 11,limit=500000)
                    if answers:raise RuntimeError('Original did not consume recipient choices')
                    rows.append(f'{pattern} {armour} {choice} {path} {funded} {cash} '+
                        f'{int.from_bytes(m.read(m.state+0xd370,4),"little")} {m.read(m.state+0xd317,1)[0]} '+
                        f'{notices} {fingerprint(m.read(m.state+0xc614,136)):016x}')
    m.cpu.hook_del(h)
    (ROOT/'tests/fixtures/purchase-recipients-primary.txt').write_text('\n'.join(rows)+'\n')
    (ROOT/'tests/fixtures/purchase-recipients-primary.json').write_text(json.dumps(dict(
        executable_sha256=EXE_SHA,image_sha256=IMAGE_SHA,cases=len(rows),
        routines=['14D3:0004 actions 9/11','07DC:13DE armour recipients','07DC:15E6 weapon recipients'],
        prerequisites='Solo, 2/4/8 people and sparse slots 0/3/7; two armour and two weapon prices, funded/insufficient, give/drop/swap/same-equipment choices.',
        intercepted_boundaries=sorted(f'{s:04X}:{o:04X}' for s,o in boundaries),
        comparison='Money, purchase flag, same-equipment notice and all eight complete character record fingerprints. Payment and swaps execute unmodified original instructions; UI replies are supplied.'),indent=2)+'\n')
    print('Original purchase/recipient cases:',len(rows))


if __name__=='__main__':main()
