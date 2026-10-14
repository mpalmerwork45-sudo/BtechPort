#!/usr/bin/env python3
"""Observe original outer-member entry questions; answer No at the UI boundary."""
import json
from combat_oracle import OriginalCombat, ROOT, UC_HOOK_CODE
from prepare_talk import EXE_SHA, IMAGE_SHA
from unicorn.x86_const import UC_X86_REG_CS, UC_X86_REG_IP, UC_X86_REG_SP, UC_X86_REG_SS, UC_X86_REG_AX


def main():
    rows=[];seen=set()
    for town,snapshot,centres in (
        (2,'1791962848011430927/town-start',((1338,1117),(1339,1117),(1340,1117),(1297,1077),(1300,1092))),
        (4,'1791963196424631180/mech-walk-start',((1183,1442),(1184,1442),(1184,1443),(1185,1443),(1184,1444)))):
        m=OriginalCombat(snapshot=ROOT/'work/reference-runs'/snapshot);doors=[]
        boundaries={(0x14d3,0x17c6),(0x1656,0x3f5),(0,0x1a13)}
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
        for x,y in centres:
            m.reset();px=(x//128<<8)|(x&127);py=(y//128<<12)|(y&127)
            m.call(0,0x17bb,px,py);m.call(0x187f,0x1314,px,py);m.call(0x187f,0x1df8)
            for people,mechs in ((1,0),(4,0),(8,0),(0,1),(1,3),(4,4)):
                for i in range(12):
                    active=i<mechs if i<4 else i<4+people
                    m.word(m.state+0x406a+2*i,int(active))
                    m.word(m.state+0x4004+2*i,px+m.word(m.ds+0x45c+2*i))
                    m.word(m.state+0x4036+2*i,py+m.word(m.ds+0x474+2*i))
                for dy in (-1,0,1):
                    for dx in (-1,0,1):
                        if not dx and not dy:continue
                        m.word(m.state+0xd55c,0);doors.clear();blocked=m.call(0,0x1c12,dx,dy)
                        if len(doors)>1:raise ValueError(doors)
                        door=doors[0] if doors else -1
                        if door>=0:seen.add((town,door))
                        rows.append(f'E {town} {x} {y} {people} {mechs} {dx} {dy} {door} {blocked}')
        m.cpu.hook_del(handle)
    if len(seen)<3:raise ValueError(('Too few original doors',seen))
    (ROOT/'tests/fixtures/formation-entrance-primary.txt').write_text('\n'.join(rows)+'\n')
    (ROOT/'tests/fixtures/formation-entrance-primary.json').write_text(json.dumps(dict(
        executable_sha256=EXE_SHA,image_sha256=IMAGE_SHA,routine='0000:1C12',cases=len(rows),doors=sorted(seen),
        prerequisites='Original Starport/MAP4 RAM; ten cursor positions near four entrances, six compact formations and eight directions. Original viewport rebuilt; active flags and outdoor positions supplied as caller prerequisites.',
        intercepted_boundaries=['14D3:17C6 popup','1656:03F5 text; record requested door name','0000:1A13 Yes/No returns No'],
        comparison='Exact first doorway offered and collision return after declining. Original machine instructions unchanged.',no_instruction_patches=True),indent=2)+'\n')
    print('Original formation entry cases:',len(rows),'doors:',sorted(seen))


if __name__=='__main__':main()
