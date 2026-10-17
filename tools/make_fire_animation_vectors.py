#!/usr/bin/env python3
"""Observe persistent fire/debris drawing and frame toggles in the original."""
import json
from combat_oracle import OriginalCombat, ROOT, UC_HOOK_CODE
from make_party_vectors import SNAP
from prepare_talk import EXE_SHA, IMAGE_SHA
from unicorn.x86_const import UC_X86_REG_CS, UC_X86_REG_IP, UC_X86_REG_SP, UC_X86_REG_SS


def main():
    m=OriginalCombat(snapshot=SNAP);draws=[]
    boundaries={(0x187f,0x28eb),(0x187f,0x377)}
    watch={(m.load+s)*16+o for s,o in boundaries}
    def hook(cpu,at,size,data):
        if at not in watch:return
        sp=cpu.reg_read(UC_X86_REG_SP);stack=16*cpu.reg_read(UC_X86_REG_SS)+sp
        draws.append((m.word(stack+12),m.word(stack+14)))
        off,seg=m.word(stack),m.word(stack+2)
        cpu.reg_write(UC_X86_REG_SP,sp+4);cpu.reg_write(UC_X86_REG_CS,seg);cpu.reg_write(UC_X86_REG_IP,off)
    m.cpu.hook_add(UC_HOOK_CODE,hook);rows=[]
    for camera_x,camera_y in ((64,64),(127,127),(128,128),(1536,1536)):
        for dx,dy in ((0,0),(-13,-12),(13,12),(-14,0),(14,0),(0,-13),(0,13),(-8,4),(6,-8)):
            for sprite in (124,125,126,128,129):
                m.reset();m.write(m.state+0xd457,bytes(64))
                far_sector=((camera_y//128)*16+camera_x//128)^0x88
                m.write(m.state+0xd497,bytes([far_sector])*64)
                m.write(m.state+0xd4d7,bytes(64));m.write(m.state+0xd517,bytes(64))
                x,y=camera_x+dx,camera_y+dy
                m.word(m.state+0xd557,0)
                m.call(0x103b,0x27c9,sprite,(x//128)*256+(x&127),(y//128)*4096+(y&127))
                # Declare the camera record directly: invoking the broader
                # camera routine would load unrelated city/world resources.
                m.word(m.buffer+0xa44b,(camera_x//128)*256+(camera_x&127))
                m.word(m.buffer+0xa44d,(camera_y//128)*4096+(camera_y&127))
                for frame in range(4):
                    draws.clear();before=m.read(m.state+0xd457,1)[0]
                    m.call(0,0x2a93,limit=1000000)
                    after=m.read(m.state+0xd457,1)[0]
                    assert len(draws)<=1,(camera_x,camera_y,dx,dy,sprite,draws)
                    px,py=draws[0] if draws else (0,0)
                    rows.append('F '+' '.join(map(str,(camera_x,camera_y,x,y,sprite,frame,len(draws),before,after,px,py))))
    (ROOT/'tests/fixtures/fire-primary.txt').write_text('\n'.join(rows)+'\n')
    (ROOT/'tests/fixtures/fire-primary.json').write_text(json.dumps(dict(
        executable_sha256=EXE_SHA,image_sha256=IMAGE_SHA,cases=len(rows),
        routines=['103B:27C9 world mark insertion','0000:2A93 map decoration renderer'],
        prerequisites='One live fire/corpse/wreck entry, four camera positions including sector seams, nine viewport positions and four consecutive redraws; original VGA path.',
        boundaries=['187F:28EB pixel blit','187F:0377 pixel blit'],
        comparison='Visibility, exact screen anchor, sprite byte before/after each redraw. Visible fire toggles once per redraw; offscreen fire and static debris retain their bytes.',
        limits='Original redraw semantics; host scheduling and CPU drawing cost remain separate. Both original outdoor 0000:051B and combat 0000:0E4B call this shared ring renderer.',
        no_instruction_patches=True),indent=2)+'\n')
    print(f'Original fire and debris: {len(rows)} redraw observations')


if __name__=='__main__':main()
