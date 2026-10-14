#!/usr/bin/env python3
"""Execute original unit drawing coordinates; intercept only pixel blitters."""
import json
from combat_oracle import OriginalCombat, ROOT, UC_HOOK_CODE
from make_party_vectors import SNAP
from prepare_talk import EXE_SHA, IMAGE_SHA
from unicorn.x86_const import UC_X86_REG_CS, UC_X86_REG_IP, UC_X86_REG_SP, UC_X86_REG_SS


def main():
    m=OriginalCombat(snapshot=SNAP);rows=[];draws=[]
    boundaries={(0,0x2a93),(0x187f,0x28eb),(0x187f,0x377)}
    absolute={(m.load+s)*16+o:(s,o) for s,o in boundaries}
    def hook(cpu,at,size,data):
        if at not in absolute:return
        sp=cpu.reg_read(UC_X86_REG_SP);ss=cpu.reg_read(UC_X86_REG_SS)*16
        if absolute[at]!=(0,0x2a93):
            draws.append([m.word(ss+sp+12),m.word(ss+sp+14)])
        off,seg=m.word(ss+sp),m.word(ss+sp+2)
        cpu.reg_write(UC_X86_REG_SP,sp+4);cpu.reg_write(UC_X86_REG_CS,seg);cpu.reg_write(UC_X86_REG_IP,off)
    handle=m.cpu.hook_add(UC_HOOK_CODE,hook)
    for unit in (0,3,4,7,11,12,15,16,19,23):
        for x,y in ((64,64),(63,63),(65,65),(60,68),(69,60)):
            m.reset();draws.clear()
            m.write(m.state+0x4004,bytes([255])*100)
            m.word(m.state+0x4004+2*unit,0xc00+x);m.word(m.state+0x4036+2*unit,0xc000+y)
            m.write(m.state+0x409a,bytes(24));m.write(m.state+0xd55e,bytes(24))
            m.call(0,0x17bb,0xc40,0xc040)
            m.call(0x187f,0x1314,0xc40,0xc040);m.call(0x187f,0x1df8)
            m.call(0,0xe4b,limit=1000000)
            if len(draws)!=1:raise ValueError((unit,x,y,draws))
            rows.append(f'S {unit} {x} {y} {draws[0][0]} {draws[0][1]}')
    m.cpu.hook_del(handle)
    (ROOT/'tests/fixtures/combat-anchors-primary.txt').write_text('\n'.join(rows)+'\n')
    (ROOT/'tests/fixtures/combat-anchors-primary.json').write_text(json.dumps(dict(
        executable_sha256=EXE_SHA,image_sha256=IMAGE_SHA,snapshot=str(SNAP.relative_to(ROOT)),
        routines=['0000:0E4B unit renderer','0000:17BB camera position'],cases=len(rows),
        prerequisite='Only the selected unit has a visible position; camera at packed 0C40/C040, original MAP1 viewport. Ten friendly/enemy mech/person IDs, five relative positions.',
        comparison='Exact screen X/Y supplied to the original pixel blitter. Sprite contents, occlusion and time are separate.',
        intercepted_boundaries=['0000:2A93 decorative marks','187F:28EB pixel blit','187F:0377 pixel blit'],
        no_instruction_patches=True),indent=2)+'\n')
    print('Original combat sprite anchors:',len(rows))


if __name__=='__main__':main()
