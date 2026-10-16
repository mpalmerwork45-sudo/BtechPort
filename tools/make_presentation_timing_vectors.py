#!/usr/bin/env python3
"""Observe original animation/delay calls, without estimating CPU execution time.

All 22 ANMs execute through 0000:48B7/1AFD and the original decoder. File
reads, drawing, retrace waits and speaker playback are explicit boundaries.
Only numeric delays and frame hashes are committed, never original graphics.
"""
import json
from combat_oracle import OriginalCombat, ROOT, UC_HOOK_CODE
from make_party_vectors import SNAP, fingerprint
from prepare_talk import EXE_SHA, IMAGE_SHA
from unicorn.x86_const import UC_X86_REG_SS, UC_X86_REG_SP, UC_X86_REG_CS, UC_X86_REG_IP, UC_X86_REG_AX


def main():
    m=OriginalCombat(snapshot=SNAP);rows=[];delays=[];frames=[];sounds=[];kind=0;keys=0
    boundaries={(0x173d,6),(0x173d,0x259),(0x173d,0x814),(0x187f,0x33d0),(0x187f,0x3336),
                (0x187f,0xd1),(0x187f,0x1e37),(0,0x28cc),(0,0x19bf),(0x1656,0x281),(0x1656,0x388)}
    absolute={(m.load+s)*16+o:(s,o) for s,o in boundaries}
    def hook(cpu,at,size,data):
        nonlocal keys
        if at not in absolute:return
        where=absolute[at];ss=16*cpu.reg_read(UC_X86_REG_SS);sp=cpu.reg_read(UC_X86_REG_SP)
        if where==(0x173d,0x814):
            target=m.word(ss+sp+8)+16*m.word(ss+sp+10)
            raw=(ROOT/f'Original DOS/O{kind}.ANM').read_bytes();assert len(raw)<=m.word(ss+sp+12)
            m.write(target,raw);cpu.reg_write(UC_X86_REG_AX,len(raw))
        elif where==(0x187f,0x33d0):cpu.reg_write(UC_X86_REG_AX,5)
        elif where==(0x173d,6):delays.append(m.word(ss+sp+4))
        elif where==(0x173d,0x259):keys+=1
        elif where==(0,0x19bf):sounds.append(m.word(ss+sp+4))
        elif where==(0x187f,0x1e37):frames.append(m.read(m.buffer+0x244b,3872))
        off,seg=m.word(ss+sp),m.word(ss+sp+2)
        cpu.reg_write(UC_X86_REG_SP,sp+4);cpu.reg_write(UC_X86_REG_CS,seg);cpu.reg_write(UC_X86_REG_IP,off)
    handle=m.cpu.hook_add(UC_HOOK_CODE,hook)
    # Choose a seed whose actual random draw passes the original mask even
    # for non-forced playback; preserve the RNG instructions themselves.
    seed=0
    for candidate in range(1,100):
        m.reset();m.write(m.ds+0x4fc0,candidate.to_bytes(3,'little'))
        if not m.call(0x187f,0xbc0)&3:seed=candidate;break
    assert seed
    for kind in range(22):
        for flags in range(3):
            m.reset();delays.clear();frames.clear();sounds.clear()
            m.write(m.ds+0x4fc0,seed.to_bytes(3,'little'));m.write(m.state+0xd35b,[0]);m.word(m.state+0x4fba,3)
            m.call(0,0x48b7,kind,flags,limit=6000000)
            assert frames and delays
            rows.append('A '+ ' '.join(map(str,(kind,flags,len(frames),len(delays),sum(delays),len(sounds))))+' '+
                        fingerprint(b''.join(frames))+' '+ ' '.join(map(str,delays+sounds)))
    for speed in range(6):
        m.reset();delays.clear();keys=0;m.word(m.ds+0x15e,speed)
        m.call(0xe31,0x1dcc)
        rows.append('S '+ ' '.join(map(str,(speed,keys,len(delays),*delays))))
    m.cpu.hook_del(handle)
    (ROOT/'tests/fixtures/presentation-timing-primary.txt').write_text('\n'.join(rows)+'\n')
    (ROOT/'tests/fixtures/presentation-timing-primary.json').write_text(json.dumps(dict(
        executable_sha256=EXE_SHA,image_sha256=IMAGE_SHA,cases=66,combat_speeds=6,seed=seed,
        routines='0000:48B7/1AFD animation dispatcher/frames; 187F:23EC decoder; 0E31:1DCC combat pacing',
        comparison='All packed frame hashes, ordered 173D:0006 retrace counts and startup speaker calls, flags 0/1/2. O8 repeats seven times; every other ANM adds 50 retraces after frame zero. Flags zero add 60 final retraces and O0 sound 12.',
        boundaries=sorted(f'{s:04X}:{o:04X}' for s,o in boundaries),
        limits='VGA retrace requests, not wall-clock measurements. CPU decode cost and physical XT speaker/acoustic timing are excluded.',no_instruction_patches=True),indent=2)+'\n')
    print('Original presentation timing: 66 animations and 6 combat speeds')


if __name__=='__main__':main()
