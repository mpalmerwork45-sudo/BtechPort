#!/usr/bin/env python3
"""Observe the original cinema's complete scrolling film dialogue.

Execute the supplied BLD and original text engine, rasterizing glyph calls with
the owner's font. Only numeric PCs and pixel hashes leave ignored work/.
Animation/audio playback and key waits are explicit presentation boundaries.
"""
import json
from audit_bld_flow import decrypt
from combat_oracle import OriginalCombat, ROOT, UC_HOOK_CODE
from make_party_vectors import SNAP, fingerprint
from prepare_talk import EXE_SHA, IMAGE_SHA, FONT
from make_phoenix_palette_vectors import EGA
from unicorn.x86_const import UC_X86_REG_SS, UC_X86_REG_SP, UC_X86_REG_BP, UC_X86_REG_CS, UC_X86_REG_IP, UC_X86_REG_AX


def main():
    m=OriginalCombat(snapshot=SNAP);pixels=bytearray(200*184*3);rows=[];scrolls=0;window=6
    boundaries={(0x173d,0x259),(0x173d,0x86a),(0x173d,0xd5),
                (0,0x1a13),(0xe31,0x1fdf),(0,0x48b7),(0,0x19bf)}
    absolute={(m.load+s)*16+o:(s,o) for s,o in boundaries}
    output=ROOT/'work/m4-audit';output.mkdir(parents=True,exist_ok=True)
    def hook(cpu,at,size,data):
        nonlocal scrolls,window
        ss=16*cpu.reg_read(UC_X86_REG_SS);sp=cpu.reg_read(UC_X86_REG_SP)
        bp=ss+cpu.reg_read(UC_X86_REG_BP)
        if at==(m.load+0x1656)*16+0x281:window=m.word(ss+sp+4)
        if window==6 and at==(m.load+0x1656)*16+0x388:
            pixels[:]=bytes(len(pixels));scrolls=0
        if window==6 and at==(m.load+0x1656)*16+0x7cb:
            if m.word(m.state+0x374e)>=m.word(m.state+0x393a):
                pixels[:-200*8*3]=pixels[200*8*3:];pixels[-200*8*3:]=bytes(200*8*3);scrolls+=1
        if at not in absolute:return
        where=absolute[at]
        if where==(0,0x1a13):cpu.reg_write(UC_X86_REG_AX,1)
        if where==(0x173d,0xd5) and window==6:
            pointer=m.word(ss+sp+4)+16*m.word(ss+sp+6)
            x,y,color=(m.word(ss+sp+i) for i in (8,10,12))
            for i,ch in enumerate(m.read(pointer,1024).split(b'\0')[0]):
                for dy in range(8):
                    for dx in range(8):
                        xx=(x-14+i)*8+dx;yy=(y-1)*8+dy
                        if 0<=xx<200 and 0<=yy<184:
                            c=EGA[color] if m.image[FONT+8*ch+dy]&(128>>dx) else 0
                            pos=(yy*200+xx)*3;pixels[pos:pos+3]=c.to_bytes(3,'big')
        if where in ((0x173d,0x259),(0,0x48b7)):
            pc=m.word(bp-10)
            if pc>=659:
                event='W' if where==(0x173d,0x259) else 'A'
                if event=='A':pc+=1 # VM consumes the flags byte after the far call.
                rows.append(f'{event} {pc} {scrolls} {fingerprint(pixels)}')
                (output/f'theater-original-{event}-{pc}.ppm').write_bytes(b'P6\n200 184\n255\n'+pixels)
        off,seg=m.word(ss+sp),m.word(ss+sp+2)
        cpu.reg_write(UC_X86_REG_SP,sp+4);cpu.reg_write(UC_X86_REG_CS,seg);cpu.reg_write(UC_X86_REG_IP,off)
    handle=m.cpu.hook_add(UC_HOOK_CODE,hook)
    script=decrypt((ROOT/'Original DOS/THEATER.BLD').read_bytes())
    m.write(m.state+0xa0,script);m.word(m.state+0x4584,16);m.write(m.state+0xd370,(5).to_bytes(4,'little'))
    m.call(0x7dc,0x1c0,0xa0,m.state//16,limit=3000000)
    m.cpu.hook_del(handle)
    (ROOT/'tests/fixtures/theater-text-primary.txt').write_text('\n'.join(rows)+'\n')
    (ROOT/'tests/fixtures/theater-text-primary.json').write_text(json.dumps(dict(
        executable_sha256=EXE_SHA,image_sha256=IMAGE_SHA,cases=len(rows),
        routine='07DC:01C0 complete THEATER.BLD with 1656:03F5 text and 1656:07CB scroll',
        comparison='200x184 interior RGB hashes at every film/held page after the opening clear; original glyph rasterization, wrapping, scroll and final clear.',
        prerequisites='Five credits and Yes to admission; original text window 6. ANM/audio/native exit/key calls supplied as boundaries; no timing claim.',
        boundaries=sorted(f'{s:04X}:{o:04X}' for s,o in boundaries),no_instruction_patches=True),indent=2)+'\n')
    print('Original theater text panels:',len(rows),'max scroll rows:',max(int(r.split()[2]) for r in rows))


if __name__=='__main__':main()
