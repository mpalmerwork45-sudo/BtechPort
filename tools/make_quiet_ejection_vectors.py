#!/usr/bin/env python3
"""Observe original quiet ejection text appended to retained unit headers."""
import json
from combat_oracle import OriginalCombat, ROOT, UC_HOOK_CODE
from make_live_campaign_vectors import SNAP
from prepare_talk import EXE_SHA, IMAGE_SHA, FONT
from make_phoenix_palette_vectors import EGA
from make_battle_text_vectors import fnv
from unicorn.x86_const import UC_X86_REG_SS, UC_X86_REG_SP


def main():
    m=OriginalCombat(snapshot=SNAP);pixels=bytearray(88*88*3);window=4;draws=[];rows=[];private=[]
    def hook(cpu,at,size,data):
        nonlocal window
        st=16*cpu.reg_read(UC_X86_REG_SS)+cpu.reg_read(UC_X86_REG_SP)
        if at==(m.load+0x1656)*16+0x281:window=m.word(st+4)
        elif at==(m.load+0x1656)*16+0x388 and window==4:pixels[:]=bytes(len(pixels))
        elif at==(m.load+0x1656)*16+0x7cb and window==4:
            if m.word(m.state+0x374e)>=m.word(m.state+0x393a):
                pixels[:80*88*3]=pixels[8*88*3:];pixels[80*88*3:]=bytes(8*88*3)
        elif at==(m.load+0x173d)*16+0xd5 and window==4:
            p=m.word(st+4)+16*m.word(st+6);x,y,color=m.word(st+8),m.word(st+10),m.word(st+12)
            raw=m.read(p,1024).split(b'\0')[0];draws.append([x,y,color,raw.decode('latin1')])
            for i,ch in enumerate(raw):
                for dy in range(8):
                    for dx in range(8):
                        xx=(x-1+i)*8+dx;yy=(y-1)*8+dy
                        if 0<=xx<88 and 0<=yy<88:
                            c=EGA[color] if m.image[FONT+8*ch+dy]&(128>>dx) else 0
                            pos=(yy*88+xx)*3;pixels[pos:pos+3]=c.to_bytes(3,'big')
    m.cpu.hook_add(UC_HOOK_CODE,hook)
    for active in (0,1,2,7):
        for target in (0,1,2):
            m.reset();pixels[:]=bytes(len(pixels));draws.clear();window=4
            m.word(m.ds+0x2e38,0);m.word(m.ds+0x2e3a,0);m.word(m.ds+0x15e,2)
            m.word(m.state+0xe48e,0)
            m.call(0x1656,0x281,4);m.call(0x1656,0x388)
            m.call(0x5ab,0x18e8,active,0,0)
            before=fnv(pixels);cursor=[m.word(m.state+o) for o in (0x374c,0x374e)]
            m.call(0xd43,0xa35,target,limit=1000000)
            rows.append(f'Q {active} {target} {before:016x} {fnv(pixels):016x}')
            private.append(dict(active=active,target=target,cursor=cursor,draws=list(draws)))
    (ROOT/'tests/fixtures/quiet-ejection-primary.txt').write_text('\n'.join(rows)+'\n')
    (ROOT/'work/m4-next').mkdir(parents=True,exist_ok=True)
    (ROOT/'work/m4-next/quiet-ejection.json').write_text(json.dumps(private,indent=2)+'\n')
    (ROOT/'tests/fixtures/quiet-ejection-primary.json').write_text(json.dumps(dict(
        executable_sha256=EXE_SHA,image_sha256=IMAGE_SHA,cases=len(rows),
        routines=['05AB:18E8 unit header','0D43:0A35 retirement','1656:03F5 wrapping','173D:00D5 glyphs'],
        prerequisites='GAME3 three active mechs and Rick on foot; quiet mode, window 4 cleared before selected-unit header, then one friendly ejection.',
        comparison='All 88x88 text-window pixels before and after retirement, including retained header and cursor; no instruction edits.'),indent=2)+'\n')
    print('Original quiet ejection panels:',len(rows))


if __name__=='__main__':main()
