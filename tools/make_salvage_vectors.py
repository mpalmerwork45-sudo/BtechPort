#!/usr/bin/env python3
"""Run the complete original salvage loop with explicit wreck/crew prerequisites.

Keyboard and delay boundaries are supplied by the harness. Selection, retries,
RNG, eligibility, recovered records and text layout execute unmodified. Glyph
calls are rasterized with the original font; raw text stays private and fixtures
contain hashes only.
"""
import argparse,json
from combat_oracle import OriginalCombat, ROOT, UC_HOOK_CODE
from make_party_vectors import SNAP, fingerprint
from prepare_talk import EXE_SHA, IMAGE_SHA, FONT
from make_phoenix_palette_vectors import EGA
from unicorn.x86_const import UC_X86_REG_CS, UC_X86_REG_IP, UC_X86_REG_SP, UC_X86_REG_SS, UC_X86_REG_BP, UC_X86_REG_AX


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--probe-case',type=int);args=parser.parse_args()
    m = OriginalCombat(snapshot=SNAP)
    boundaries = {(0,0x1a13), (0x173d,6), (0x173d,0x259),(0x173d,0xd5)}
    absolute = {(m.load+s)*16+o:(s,o) for s,o in boundaries}
    rows=[]; pages=[]; text=bytearray(); case=0; answer_mask=0; attempts=[];pixels=bytearray(200*72*3)
    def hook(cpu, at, size, data):
        # Observe the eligibility decision before either result branch.
        if at==(m.load+0x5ab)*16+0x5e1:
            bp=cpu.reg_read(UC_X86_REG_SS)*16+cpu.reg_read(UC_X86_REG_BP)
            attempts.append((m.word(bp-14),m.word(bp-16),m.word(bp-8)))
        sp=cpu.reg_read(UC_X86_REG_SP);ss=cpu.reg_read(UC_X86_REG_SS)*16
        bp=ss+cpu.reg_read(UC_X86_REG_BP)
        if at==(m.load+0x1656)*16+0x388:text.clear();pixels[:]=bytes(len(pixels))
        elif at==(m.load+0x1656)*16+0x3f5:
            pointer=m.word(ss+sp+4)+16*m.word(ss+sp+6)
            raw=m.read(pointer,1024);text.extend(raw[:raw.index(0)])
        elif at==(m.load+0x1656)*16+0x7cb:
            if m.word(m.state+0x374e)>=m.word(m.state+0x393a):
                pixels[:64*200*3]=pixels[8*200*3:];pixels[64*200*3:]=bytes(8*200*3)
        elif at==(m.load+0x173d)*16+0xd5:
            pointer=m.word(ss+sp+4)+16*m.word(ss+sp+6)
            x,y,color=(m.word(ss+sp+i) for i in (8,10,12))
            raw=m.read(pointer,1024).split(b'\0')[0]
            for i,ch in enumerate(raw):
                for dy in range(8):
                    for dx in range(8):
                        xx=(x-14+i)*8+dx;yy=(y-15)*8+dy
                        if 0<=xx<200 and 0<=yy<72:
                            c=EGA[color] if m.image[FONT+8*ch+dy]&(128>>dx) else 0
                            pos=(yy*200+xx)*3;pixels[pos:pos+3]=c.to_bytes(3,'big')
        if at not in absolute:return
        where=absolute[at]
        if where==(0,0x1a13):
            pilot=m.word(bp-14);answer=int(bool(answer_mask&(1<<pilot)))
            rows.append(f'Q {pilot} {answer}');cpu.reg_write(UC_X86_REG_AX,answer)
        elif where==(0x173d,0x259):
            for pilot,unit,eligible in attempts:rows.append(f'A {pilot} {unit} {eligible}')
            attempts.clear()
            rows.append(f'W {fingerprint(text)} {fingerprint(pixels)}')
            pages.append(dict(case=case,text=list(text)))
            if args.probe_case is not None:
                (ROOT/f'work/m4-audit/salvage-original-{len(pages)}.ppm').write_bytes(b'P6\n200 72\n255\n'+pixels)
        off,seg=m.word(ss+sp),m.word(ss+sp+2)
        cpu.reg_write(UC_X86_REG_SP,sp+4);cpu.reg_write(UC_X86_REG_CS,seg);cpu.reg_write(UC_X86_REG_IP,off)
    handle=m.cpu.hook_add(UC_HOOK_CODE,hook)
    for skill in (0,3,4,5):
        for damage in range(8):
            for answer_mask in (0,1,2,7):
                for seed in (1,42,0xd23646):
                    if args.probe_case is not None and case!=args.probe_case:case+=1;continue
                    m.reset();text.clear();attempts.clear()
                    # 103B selects window 1 before the salvage loop. Run the
                    # real text engine; observe its glyph calls and scrolling.
                    m.call(0x1656,0x281,1)
                    m.write(m.ds+0x4fc0,seed.to_bytes(3,'little'));m.write(m.state+0x393c,bytes(48))
                    for p in range(8):
                        record=bytearray([p if p<3 else 255,8,9,7,0,0,0,1,1,skill if p==1 else 0,0,9,8,3,30,80,0])
                        m.write(m.state+0xc614+17*p,record)
                    for bay in range(8):m.write(m.state+0xc724+125*bay,bytes([255])+bytes(124))
                    for i,unit in enumerate((12,13,15)):
                        record=bytearray(m.template(i));kind=record[0];record[0]=255
                        if damage&(1<<i):record[117]=3;record[118]=2;record[31]=record[32]=0
                        index=unit-8;m.write(m.state+0xc724+125*index,record)
                        m.write(m.state+0x323e+index,[kind]);m.word(m.state+0x393c+2*unit,1)
                    rows.append(f'C {case} {skill} {damage} {answer_mask} {seed}')
                    m.call(0x5ab,0x4f9,limit=3000000)
                    if attempts:raise RuntimeError('Unobserved salvage result')
                    rows.append('Z '+str(int.from_bytes(m.read(m.ds+0x4fc0,3),'little'))+' '+
                                fingerprint(m.read(m.state+0xc614,8*17))+' '+fingerprint(m.read(m.state+0xc724,4*125))+' '+
                                str(sum(1<<i for i in range(16) if m.word(m.state+0x393c+2*i))))
                    case+=1
    m.cpu.hook_del(handle)
    if args.probe_case is not None:
        (ROOT/'work/m4-audit/salvage-probe.json').write_text(json.dumps(pages,indent=2)+'\n')
        print('\n'.join(rows));return
    (ROOT/'tests/fixtures/salvage-primary.txt').write_text('\n'.join(rows)+'\n')
    (ROOT/'work/m4-audit/salvage-text.json').write_text(json.dumps(pages,indent=2)+'\n')
    (ROOT/'tests/fixtures/salvage-primary.json').write_text(json.dumps(dict(
        executable_sha256=EXE_SHA,image_sha256=IMAGE_SHA,routine='05AB:04F9 complete salvage loop',cases=case,
        prerequisites='Three qualified pilots on foot, three wrecks (Locust, Chameleon, Wasp), four technician ranks, eight damage masks, four answer masks, three RNG seeds; empty garage.',
        boundaries=sorted(f'{s:04X}:{o:04X}' for s,o in boundaries),
        comparison='Prompt order, automatic retries, held-page text and 200x72 interior RGB hashes from original glyph calls/scrolling, full recovered/party records, remaining wrecks and RNG. Window 1 interior (112,120)..(311,191); border separately captured. No live result screenshot or instruction patches.'),indent=2)+'\n')
    print('Original salvage:',case,'complete loops;',len(pages),'held pages')


if __name__=='__main__':main()
