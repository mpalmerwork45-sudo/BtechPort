#!/usr/bin/env python3
"""Execute original encounter decisions and combat sound selection branches."""
import json,struct
from combat_oracle import OriginalCombat,ROOT,UC_HOOK_CODE
from make_party_vectors import SNAP
from prepare_talk import EXE_SHA,IMAGE_SHA
from unicorn.x86_const import (UC_X86_REG_AX,UC_X86_REG_CS,UC_X86_REG_IP,
    UC_X86_REG_DS,UC_X86_REG_SS,UC_X86_REG_SP,UC_X86_REG_BP)

def main():
    m=OriginalCombat(snapshot=SNAP);sounds=[];stops=set();result=[]
    def hook(cpu,address,size,data):
        relative=address-m.load*16
        if relative in stops:result.append(relative);cpu.emu_stop();return
        # Only display/input and the blocking sound player are replaced.
        # The selected sound argument is observed before its far return.
        if relative not in (0x19bf,0x168e8,0x16955,0x2a4f,0x100bb,0x12b79):return
        sp=cpu.reg_read(UC_X86_REG_SP);ss=16*cpu.reg_read(UC_X86_REG_SS)
        if relative==0x19bf:sounds.append(m.word(ss+sp+4))
        off,seg=struct.unpack('<HH',m.read(ss+sp,4))
        cpu.reg_write(UC_X86_REG_SP,sp+4);cpu.reg_write(UC_X86_REG_CS,seg);cpu.reg_write(UC_X86_REG_IP,off)
    handle=m.cpu.hook_add(UC_HOOK_CODE,hook)
    def span(start,end,limit=1000):
        result.clear();stops.clear();stops.update(end)
        segment=0x103b if start<0x12e80 else 0x12e8
        for reg,v in ((UC_X86_REG_CS,m.load+segment),(UC_X86_REG_IP,start-16*segment),
            (UC_X86_REG_DS,m.ds//16),(UC_X86_REG_SS,0x7000),(UC_X86_REG_SP,0xee00),(UC_X86_REG_BP,0xf000)):
            m.cpu.reg_write(reg,v)
        m.cpu.emu_start(m.load*16+start,0x110000,count=limit)
        if not result:raise RuntimeError(f'Unbounded selection at {start:05X}')
        return result[0]
    rows=[];bp=0x7f000
    for weapon in range(33):
        for visible in (0,1):
            for hit in (0,1):
                m.reset();sounds.clear();m.write(bp-0x80,bytes(0xa0))
                m.word(bp+6,0);m.word(bp+8,12);m.word(bp+10,weapon);m.word(bp+22,hit)
                span(0x143a1,(0x14500,0x14887))
                group=m.word(bp-0x18)
                if visible and group in (2,3):span(0x1486a,(0x14887,))
                span(0x14887,(0x1489c,0x1495d))
                rows.append(f'S {weapon} {visible} {hit} {len(sounds)} '+' '.join(str(v) for v in sounds))
    for start,end,expected in ((0x14af6,0x14b02,8),(0x14b1f,0x14b2b,7)):
        m.reset();sounds.clear();span(start,(end,))
        if sounds!=[expected]:raise RuntimeError('Original destruction sound changed')
        rows.append(f'D {expected}')
    # Human death traverses the real corpse/cleared-order branch, then skips
    # the wreck branch because its caller's mech-dead argument is zero.
    m.reset();sounds.clear();m.write(bp-0x80,bytes(0xa0))
    m.word(bp+8,16);m.word(bp+0x10,1);m.word(bp+0x12,0);m.word(bp+0x14,0)
    span(0x1498c,(0x14ca8,),limit=10000)  # 12E8:1B0C..1E28
    if sounds:raise RuntimeError('Original human death unexpectedly selected a speaker effect')
    rows.append('H 0')
    # The original No branch has exactly one draw, succeeds for nonzero low
    # two bits, and otherwise presents DS:343A before combat settings.
    for seed in (0,1,2,3,4,17,42,1234,5678,0xd23646):
        for yes in (0,1):
            m.reset();m.write(m.ds+0x4fc0,seed.to_bytes(3,'little'));m.word(bp-6,yes)
            reached=span(0x1083a,(0x1086e,0x113e7))
            rows.append(f'E {seed} {yes} {int(reached==0x113e7)} {int.from_bytes(m.read(m.ds+0x4fc0,3),"little")}')
    m.cpu.hook_del(handle)
    (ROOT/'tests/fixtures/event-audit-primary.txt').write_text('\n'.join(rows)+'\n')
    (ROOT/'tests/fixtures/event-audit-primary.json').write_text(json.dumps(dict(
        executable_sha256=EXE_SHA,image_sha256=IMAGE_SHA,cases=len(rows),
        routine='103B:048A..04BE encounter No/Yes; 12E8:1521..1680 fire and 19EA..1A1C hit sounds',
        spans='Image 143A1..14500/14887, 1486A..14887 and 14887..1489C/1495D; beam playback prerequisite visible=0/1',
        intercepted_boundaries=['0000:19BF sound playback (argument observed)','1656:0388/03F5 display','0000:2A4F key wait',
            '0E31:1DAB death text','103B:27C9 corpse mark display'],
        comparison='Sound IDs for all 33 weapons, hit/miss and visibility; ten seeds, encounter Yes/No, exact RNG and evasion outcome'),indent=2)+'\n')
    print('Primary combat event selections:',len(rows))

if __name__=='__main__':main()
