#!/usr/bin/env python3
"""Original brief/verbose shot text and glyph positions in window 4.

The actual 1656 text engine and 173D glyph-call coordinates are observed. Only
numeric hashes enter fixtures; strings/draw traces remain ignored locally.
Shot prerequisites are explicit and do not represent a complete played battle.
"""
import argparse,json
from combat_oracle import OriginalCombat,ROOT,UC_HOOK_CODE
from make_live_campaign_vectors import SNAP
from prepare_talk import EXE_SHA,IMAGE_SHA,FONT
from make_phoenix_palette_vectors import EGA
from make_aftermath_vectors import span
from unicorn.x86_const import UC_X86_REG_SS,UC_X86_REG_SP,UC_X86_REG_BP


def fnv(data):
    h=0xcbf29ce484222325
    for b in data:h=((h^b)*0x100000001b3)&0xffffffffffffffff
    return h


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--deaths',action='store_true',help='Include original retirement/ejection and infantry death text')
    args=parser.parse_args()
    m=OriginalCombat(snapshot=SNAP);rows=[];private=[];mode=0;actor=0;target=12
    fragments=[];pixels=bytearray(88*88*3);draws=[];window=4
    def address(u):return m.state+(0xc724+125*(u if u<4 else u-8) if u<4 or 12<=u<16 else 0xc614+17*(u-4 if u<12 else u-8))
    def hook(cpu,at,size,data):
        nonlocal window
        st=16*cpu.reg_read(UC_X86_REG_SS)+cpu.reg_read(UC_X86_REG_SP)
        if at==(m.load+0x12e8)*16+0x239:
            m.word(m.ds+0x2e38,mode);m.word(m.ds+0x2e3a,0);m.word(m.ds+0x15c,0)
            bp=16*cpu.reg_read(UC_X86_REG_SS)+cpu.reg_read(UC_X86_REG_BP)
            a0,t0=m.word(bp-2),m.word(bp-0x28)
            a=m.read(address(a0),17 if a0>=16 else 125);t=m.read(address(t0),17 if t0>=16 else 125)
            m.write(address(actor),a);m.write(address(target),t)
            if args.deaths and (4<=target<12 or target>=16):m.write(address(target)+15,[1])
            m.word(bp-2,actor);m.word(bp-0x28,target)
            m.word(m.state+0x4004+2*target,0xc44);m.word(m.state+0x4036+2*target,0xc040)
            m.write(m.state+0x396c+target,[2]);m.write(m.state+0x32c6+48*actor,[0])
        elif at==(m.load+0x1656)*16+0x281:window=m.word(st+4)
        elif at==(m.load+0x1656)*16+0x388 and window==4:pixels[:]=bytes(len(pixels))
        elif at==(m.load+0x1656)*16+0x3f5:
            if window!=4:raise RuntimeError('Unexpected report window')
            p=m.word(st+4)+16*m.word(st+6);fragments.append(m.read(p,1024).split(b'\0')[0])
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
    for mode in ((0,1,2) if args.deaths else (1,2)):
        for actor,target in ((0,12),(12,0),(4,12),(16,0),(0,16),(12,4),(4,16),(16,4)):
            ak=actor in (4,16);tk=target in (4,16)
            for w in ((0,7,11) if ak else (16,17,23,29,32)):
                for weak in (0,1):
                    for seed in (1,42):
                        fragments.clear();draws.clear();pixels[:]=bytes(len(pixels));window=4
                        result=m.shot(w,0,0,1,0,2,0,weak,seed,int(ak),int(tk))
                        dead=int(bool(result['dead']))
                        if args.deaths:
                            # The shot probe stops before cleanup. Execute
                            # its actual next retirement/infantry span using
                            # the already damaged records and text window.
                            if tk:
                                dead=int(m.read(address(target)+15,1)[0]==0)
                                if dead:span(m,0x12e8,0x1b15,0x1bfc,{8:target,0x14:target-4 if target<12 else target-8})
                            elif dead:m.call(0xd43,0xa35,target,limit=1000000)
                        raw=b''.join(fragments);crit=sum(p==b'\rCritical!' for p in fragments)
                        # Location result records the original caller's first
                        # hit region; infantry and ineffective small arms use 0.
                        values=(mode,actor,target,w,weak,seed,result['hit'],result['location'],crit)
                        if args.deaths:values+=(dead,)
                        rows.append('T '+' '.join(map(str,values))+f' {fnv(raw):016x} {fnv(pixels):016x}')
                        private.append(dict(case=len(rows)-1,fragments=[p.decode('latin1') for p in fragments],draws=list(draws)))
    label='battle-death' if args.deaths else 'battle-text'
    (ROOT/f'tests/fixtures/{label}-primary.txt').write_text('\n'.join(rows)+'\n')
    (ROOT/f'work/m4-audit/{label}.json').write_text(json.dumps(private,indent=2)+'\n')
    (ROOT/f'tests/fixtures/{label}-primary.json').write_text(json.dumps(dict(
        executable_sha256=EXE_SHA,image_sha256=IMAGE_SHA,cases=len(rows),
        routines=['12E8:0239..0CD3 shot','0E31:11AB critical','1656:03F5 text and wrapping','173D:00D5 glyph coordinates']+(['0D43:0A35 retirement/ejection','12E8:1B15..1BFC infantry death'] if args.deaths else []),
        prerequisites='Original mixed-party snapshot; explicit attacker/target IDs, weapon, armour/structure, seed; window 4. Sound/outtakes off. '+('Human targets have one HP; execute retirement and infantry death cleanup after the shot probe.' if args.deaths else 'Stop before destruction cleanup.'),
        comparison='Complete text stream and all 88x88 interior RGB pixels reconstructed from original glyph calls; original window is (8,8)..(95,95). '+('Includes silent/brief/verbose casualty text and friendly ejection. Native pixel comparison covers brief/verbose only; quiet ejection retains a prior window cursor not represented by this fixture.' if args.deaths else 'No battlefield or death-cleanup claim.'),
        no_instruction_patches=True),indent=2)+'\n')
    print('Original battle report cases:',len(rows))


if __name__=='__main__':main()
