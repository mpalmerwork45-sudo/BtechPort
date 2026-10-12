#!/usr/bin/env python3
"""Execute original delay loops with the documented nominal 8 MHz clock model."""
import json
from combat_oracle import OriginalCombat,ROOT,UC_HOOK_CODE
from unicorn.x86_const import (UC_X86_REG_CS,UC_X86_REG_IP,UC_X86_REG_DS,
    UC_X86_REG_SS,UC_X86_REG_SP,UC_X86_REG_BP,UC_X86_REG_EFLAGS)
from make_party_vectors import SNAP

# Intel 1979 manual tables 2-20/2-21, four clocks per 8088 word transfer.
# IMUL is the midpoint of 134..160, + direct EA 6 + one word transfer 4.
CLOCKS={0x18105:23,0x1810a:15,0x1810c:32,0x1810f:18,0x18113:16,
    0x18117:157,0x1811b:22,0x18120:32,0x18123:23,0x18129:23,0x1812e:15,
    0x18378:23,0x1837d:15,0x1837f:32,0x18382:18,0x18386:16,0x1838a:157,0x1838e:22}

def observe(m,duration,repeats):
    m.reset();m.word(m.ds+0x5006,2)
    m.word(m.state+(0xe48c if repeats==50 else 0x3246),duration)
    start,end=(0x18105,0x18130) if repeats==50 else (0x18378,0x18393)
    cycles=[];count=[]
    def hook(cpu,address,size,data):
        relative=address-m.load*16
        if relative in (0x1811e,0x18127,0x18391):
            flags=cpu.reg_read(UC_X86_REG_EFLAGS);equal_sign=bool(flags&128)==bool(flags&2048)
            taken=equal_sign and (relative==0x18127 or not flags&64)
            clocks=16 if taken else 4
        elif relative in CLOCKS:clocks=CLOCKS[relative]
        else:raise ValueError(f'Unaudited delay instruction {relative:05x}')
        cycles.append(clocks);count.append(relative)
    for register,value in ((UC_X86_REG_CS,m.load+0x1631),(UC_X86_REG_IP,start-0x16310),
        (UC_X86_REG_DS,m.ds//16),(UC_X86_REG_SS,0x7000),(UC_X86_REG_SP,0xee00),
        (UC_X86_REG_BP,0xf000),(UC_X86_REG_EFLAGS,2)):m.cpu.reg_write(register,value)
    handle=m.cpu.hook_add(UC_HOOK_CODE,hook)
    try:m.cpu.emu_start(m.load*16+start,m.load*16+end,count=1000000)
    finally:m.cpu.hook_del(handle)
    if m.cpu.reg_read(UC_X86_REG_IP)!=end-0x16310:raise RuntimeError('Delay exceeded bound')
    return (sum(cycles)*1193182+4000000)//8000000,len(count)

def main():
    m=OriginalCombat(snapshot=SNAP);rows=['# Actual original instruction paths; nominal Intel midpoint IMUL timings, not measured hardware.']
    for repeats in (1,50):
        for duration in (0,1,2,3,7,15,100,32767,32768,65535):
            clocks,count=observe(m,duration,repeats);rows.append(f'D {duration} {repeats} {clocks} {count}')
    (ROOT/'tests/fixtures/speaker-timing.txt').write_text('\n'.join(rows)+'\n')
    (ROOT/'tests/fixtures/speaker-timing.json').write_text(json.dumps(dict(
        authority='Original physical 180CB: fifty busy loops; 18346: sweep busy loop',
        source_exe_sha256='15a1712682cf1fe50ca9e6a68a4b31d3bef7912401915edf7bb6242be193562a',
        cpu_hz=8000000,calibration_prerequisite=2,cases=20,
        timing_source='https://ardent-tool.com/CPU/docs/Intel/808x/manuals/9800722-03_alt.pdf',
        timing_model='Tables 2-20/2-21; published IMUL midpoint; word-bus transfers included; prefetch contention/interrupts excluded'),indent=2)+'\n')
    print('Primary speaker busy-loop paths:',len(rows)-1)
if __name__=='__main__':main()
