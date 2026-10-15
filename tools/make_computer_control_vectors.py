#!/usr/bin/env python3
"""Run the original command loop with explicit menu choices, without a wave.

Drawing/keyboard boundaries are supplied. AI and per-unit flag writes execute
unchanged in the existing private mixed-party capture. No instructions patched.
"""
import json
import struct
from combat_oracle import OriginalCombat, ROOT, UC_HOOK_CODE
from make_live_campaign_vectors import SNAP
from make_aftermath_vectors import span
from prepare_talk import EXE_SHA, IMAGE_SHA
from unicorn.x86_const import UC_X86_REG_AX, UC_X86_REG_CS, UC_X86_REG_IP, UC_X86_REG_SS, UC_X86_REG_SP


def main():
    m=OriginalCombat(snapshot=SNAP);rows=[];choices=[];seen=[]
    boundaries={(0x1656,0x281),(0x1656,0x388),(0x1656,0x3f5),(0x1656,0xb5e),
                (0,0x2a2b),(0x5ab,0x18e8),(0x173d,0x6c3),(0x103b,0x1774),
                (0x187f,0x18ef),(0,0xe4b),(0x173d,0xd5),(0x187f,0x2b87),(0x173d,0x2f)}
    addresses={(m.load+s)*16+o:(s,o) for s,o in boundaries}
    def hook(cpu,at,size,data):
        if at==(m.load+0x12e8)*16+0xc:raise RuntimeError('Menu unexpectedly started a wave')
        if at not in addresses:return
        where=addresses[at];sp=cpu.reg_read(UC_X86_REG_SP);ss=16*cpu.reg_read(UC_X86_REG_SS)
        if where==(0x1656,0xb5e):
            flags=sum((m.read(m.state+0x3994+i,1)[0]!=0)<<i for i in range(12))
            if not choices:raise RuntimeError('Unexpected extra command menu')
            choice=choices.pop(0);seen.append((choice,flags,m.word(m.state+0x9e)))
            cpu.reg_write(UC_X86_REG_AX,choice)
        if where==(0x173d,0x2f):cpu.reg_write(UC_X86_REG_AX,32)
        off,seg=struct.unpack('<HH',m.read(ss+sp,4))
        cpu.reg_write(UC_X86_REG_SP,sp+4);cpu.reg_write(UC_X86_REG_CS,seg);cpu.reg_write(UC_X86_REG_IP,off)
    m.cpu.hook_add(UC_HOOK_CODE,hook)
    m.word(m.state+0x90,0);m.word(m.state+0x9e,0);m.write(m.state+0x3994,bytes(12))
    # Three original mechs and Rick on foot; menu rows differ on foot.
    m.write(m.state+0x406a,bytes(48))
    for u in (0,1,2,7,13,17):m.word(m.state+0x406a+2*u,1)
    choices[:]=[5,5,7,5,7,5,7,3,5,9]
    result=m.call(0x103b,0x14c3,limit=20000000)
    if choices or result:raise RuntimeError('Did not return through Begin Fight')
    for i,(choice,flags,run) in enumerate(seen):rows.append(f'C {i} {choice} {flags} {run}')
    # 103B:100D..102E observes a key after a computer wave. Only the global
    # run flag clears; the twelve individual control bytes are preserved.
    m.word(m.state+0x9e,1);before=m.read(m.state+0x3994,12)
    span(m,0x103b,0x100d,0x102e,{})
    if m.read(m.state+0x3994,12)!=before:raise RuntimeError('Per-unit control changed on interrupt')
    rows.append(f'K {m.word(m.state+0x9e)} '+str(sum((b!=0)<<i for i,b in enumerate(before))))
    (ROOT/'tests/fixtures/computer-control-primary.txt').write_text('\n'.join(rows)+'\n')
    (ROOT/'tests/fixtures/computer-control-primary.json').write_text(json.dumps(dict(
        executable_sha256=EXE_SHA,image_sha256=IMAGE_SHA,
        routines=['103B:14C3 complete command loop','0E31:03AB AI','103B:100D..102E interrupt'],
        prerequisites='Original mixed-party snapshot; active IDs 0,1,2,7,13,17, initial manual control, menu inputs supplied.',
        boundaries=[f'{s:04X}:{o:04X}' for s,o in sorted(boundaries)],
        comparison='Computer selection is idempotent, affects only selected actor, returns to menu; Next rotates; Begin Fight returns; interrupt clears global run only.',
        no_instruction_patches=True),indent=2)+'\n')
    print('Original computer command observations:',len(rows))


if __name__=='__main__':main()
