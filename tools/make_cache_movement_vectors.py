#!/usr/bin/env python3
"""Original whole-formation collision and first cache contact, both rooms.

The real viewport and wall routine run unchanged. Cache interactions are
intercepted after recording their first contact; their rules have a separate
534-case corpus. Numeric fixtures contain no map payloads.
"""
import json,struct
from combat_oracle import OriginalCombat,ROOT,UC_HOOK_CODE
from prepare_talk import EXE_SHA,IMAGE_SHA
from unicorn.x86_const import UC_X86_REG_SP,UC_X86_REG_SS,UC_X86_REG_BP,UC_X86_REG_CS,UC_X86_REG_IP
SNAP=ROOT/'work/reference-runs/1792046692272345269/cache-entry'

def main():
    m=OriginalCombat(snapshot=SNAP);rows=[];contact=[]
    boundaries={(0xb5d,o) for o in (0x79c,0x913,0x980,0xab6,0x1e9,0x3aa,0x288,0x2a8,0x4ab,0x2d2,0x55a)}
    absolute={(m.load+s)*16+o for s,o in boundaries}
    def hook(cpu,at,size,data):
        ss=16*cpu.reg_read(UC_X86_REG_SS)
        if at==m.load*16+0x1e89:
            bp=ss+cpu.reg_read(UC_X86_REG_BP);i=m.word(bp-0x12)
            contact.append((i,m.word(bp-0x10)))
        if at in absolute:
            sp=cpu.reg_read(UC_X86_REG_SP);off,seg=m.word(ss+sp),m.word(ss+sp+2)
            cpu.reg_write(UC_X86_REG_SP,sp+4);cpu.reg_write(UC_X86_REG_CS,seg);cpu.reg_write(UC_X86_REG_IP,off)
    handle=m.cpu.hook_add(UC_HOOK_CODE,hook)
    for room in (0,1):
        raw=(ROOT/f'Original DOS/MAP{14+room}.MTP').read_bytes();raw=raw if room else raw[541:]
        width,height,gate=(32,24,139) if room else (64,64,33)
        def tile(x,y):
            tx=(x+1)//2;ty=y//2
            if tx<0 or tx>=width or ty<0 or ty>=height:return 255
            return raw[(ty//8*(width//8)+tx//8)*64+ty%8*8+tx%8]
        # Sample every fourth legal position plus all positions immediately
        # beside a terminal/door/symbol. Keep a bounded stratified set.
        legal=[(x,y) for y in range(2,height*2-2) for x in range(2,width*2-3) if tile(x,y)<gate]
        centres=legal[::max(1,len(legal)//120)][:120]
        for x,y in centres:
            m.reset();m.write(m.buffer+0x101d,raw);m.write(m.state+0xd346,[1]);m.write(m.state+0xd34e,[room]);m.word(m.ds+0x150,gate)
            # 0B5D:0718 maps MAP15's four-by-three jigsaw blocks into
            # the eight-column viewport table; retaining MAP14's stride is wrong.
            if room:
                for by in range(3):m.write(m.buffer+0x664+8*by,bytes(range(0x90+4*by,0x94+4*by)))
            m.call(0x187f,0x1da8)
            px,py=0xc00+x,0xc000+y
            m.call(0,0x17bb,px,py);m.call(0x187f,0x1314,px,py);m.call(0x187f,0x1df8)
            for count in (1,5,8):
                for i in range(12):m.word(m.state+0x406a+2*i,int(4<=i<4+count))
                for dy in (-1,0,1):
                    for dx in (-1,0,1):
                        if not (dx or dy):continue
                        contact.clear();m.word(m.state+0xd55c,1)
                        blocked=m.call(0,0x1c12,dx,dy)
                        if blocked not in (0,1) or len(contact)>1:raise ValueError((blocked,contact))
                        index,t=contact[0] if contact else (-1,0)
                        rows.append(f'C {room} {x} {y} {count} {dx} {dy} {blocked} {index} {t}')
    m.cpu.hook_del(handle)
    (ROOT/'tests/fixtures/cache-movement-primary.txt').write_text('\n'.join(rows)+'\n')
    (ROOT/'tests/fixtures/cache-movement-primary.json').write_text(json.dumps(dict(
        executable_sha256=EXE_SHA,image_sha256=IMAGE_SHA,cases=len(rows),routine='0000:1C12 with original 187F:1314 viewport',
        prerequisites='Original cache-entry RAM; fresh MAP14/MAP15, gates 33/139, 120 sampled legal cursor positions per room, 1/5/8 compact people, eight directions. Doors initially closed. Some larger formations intentionally overlap obstacles to exercise older-save recovery decisions.',
        comparison='Whole-step rejection and first blocked compact member/tile, including contacts made by followers. No wall-clock or complete-route claim.',
        intercepted_boundaries=sorted(f'{s:04X}:{o:04X} cache interaction' for s,o in boundaries),no_instruction_patches=True),indent=2)+'\n')
    print('Original cache movement cases:',len(rows))
if __name__=='__main__':main()
