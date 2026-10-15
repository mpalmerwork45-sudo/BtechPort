#!/usr/bin/env python3
"""Compare all original towns at doorways and tile/sector boundaries."""
import json,struct
from combat_oracle import OriginalCombat, ROOT, UC_HOOK_CODE
from make_party_vectors import SNAP
from town_context import load_town,cursor
from prepare_talk import EXE_SHA,IMAGE_SHA
from unicorn.x86_const import UC_X86_REG_CS,UC_X86_REG_IP,UC_X86_REG_SP,UC_X86_REG_SS,UC_X86_REG_AX


def main():
    m=OriginalCombat(snapshot=SNAP);rows=[];doors=[];seen=set()
    boundaries={(0x14d3,0x17c6),(0x14d3,0x17ea),(0x1656,0x3f5),(0,0x1a13),(0x173d,0x259)}
    absolute={(m.load+s)*16+o:(s,o) for s,o in boundaries}
    def hook(cpu,at,size,data):
        if at not in absolute:return
        sp=cpu.reg_read(UC_X86_REG_SP);ss=cpu.reg_read(UC_X86_REG_SS)*16
        if absolute[at]==(0x1656,0x3f5):
            off,seg=m.word(ss+sp+4),m.word(ss+sp+6)
            if seg*16==m.buffer and 0xa561<=off<0xa621:doors.append((off-0xa561)//16)
        if absolute[at]==(0,0x1a13):cpu.reg_write(UC_X86_REG_AX,0)
        off,seg=m.word(ss+sp),m.word(ss+sp+2)
        cpu.reg_write(UC_X86_REG_SP,sp+4);cpu.reg_write(UC_X86_REG_CS,seg);cpu.reg_write(UC_X86_REG_IP,off)
    handle=m.cpu.hook_add(UC_HOOK_CODE,hook)
    for town in range(1,14):
        raw,ox,oy=load_town(m,town);w,h=raw[3:5];positions=set()
        for i in range(12):
            ex,ey=struct.unpack_from('<H',raw,389+2*i)[0],struct.unpack_from('<H',raw,421+2*i)[0]
            if not ex or not ey:continue
            x=(ex>>8)*128+(ex&127);y=(ey>>12)*128+(ey&127)
            positions.update((x+dx,y+dy) for dx,dy in ((0,-1),(-1,0),(1,0),(0,1)))
        positions.update((ox+x,oy+y) for x,y in ((0,h),(2*w-1,h),(w,0),(w,2*h-1),(15,15),(16,16),(31,31),(32,32)))
        for x,y in sorted(positions):
            px,py=cursor(m,x,y)
            for people,mechs in ((1,0),(8,0),(1,3)):
                for i in range(12):
                    active=i<mechs if i<4 else i<4+people;m.word(m.state+0x406a+2*i,int(active))
                    m.word(m.state+0x4004+2*i,px+m.word(m.ds+0x45c+2*i));m.word(m.state+0x4036+2*i,py+m.word(m.ds+0x474+2*i))
                for dy in (-1,0,1):
                    for dx in (-1,0,1):
                        if not dx and not dy:continue
                        m.word(m.state+0xd55c,0);doors.clear()
                        try:blocked=m.call(0,0x1c12,dx,dy)
                        except Exception as error:
                            raise RuntimeError((town,x,y,people,mechs,dx,dy,hex(m.cpu.reg_read(UC_X86_REG_CS)-m.load),hex(m.cpu.reg_read(UC_X86_REG_IP)))) from error
                        if len(doors)>1 or blocked not in (0,1):raise ValueError((doors,blocked))
                        door=doors[0] if doors else -1
                        if door>=0:seen.add((town,door))
                        rows.append(f'E {town} {x} {y} {people} {mechs} {dx} {dy} {door} {blocked}')
    m.cpu.hook_del(handle)
    (ROOT/'tests/fixtures/town-boundaries-primary.txt').write_text('\n'.join(rows)+'\n')
    (ROOT/'tests/fixtures/town-boundaries-primary.json').write_text(json.dumps(dict(
        executable_sha256=EXE_SHA,image_sha256=IMAGE_SHA,cases=len(rows),doors=sorted(seen),
        routines=['187F:104E','0000:3050..30BB','187F:1886..18D7','187F:1314','0000:1C12'],
        prerequisites='All thirteen original town payloads and entrance tables at original startup seed; three compact formations, eight directions, each entrance approach and eight map/piece boundaries. Original file-read boundaries supplied in private RAM.',
        boundaries=sorted(f'{s:04X}:{o:04X}' for s,o in boundaries),
        comparison='First offered doorway after declining, and complete cursor-step rejection. Includes original deep-water boundary rejection.',
        no_instruction_patches=True),indent=2)+'\n')
    print('Original town boundaries:',len(rows),'cases;',len(seen),'doorways')


if __name__=='__main__':main()
