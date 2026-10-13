#!/usr/bin/env python3
"""Complete tactical waves from a captured live, sector-crossing DOS caller.

Retain the live party, terrain buffers, formations, sprite sequences and enemy
records. Only ordinary combat display/sound settings and computer orders are
chosen. Spy variants add a declared rider/pilot prerequisite. No code changes.
"""
import json
import struct
from pathlib import Path
from combat_oracle import OriginalCombat, ROOT, UC_HOOK_CODE
from make_combat_vectors import fingerprint
from make_aftermath_vectors import span
from prepare_talk import EXE_SHA, IMAGE_SHA
from unicorn.x86_const import UC_X86_REG_CS, UC_X86_REG_IP, UC_X86_REG_SP, UC_X86_REG_SS

SNAP = ROOT/'work/reference-runs/1791861341506357450/mech-command'
BX, BY = 1184, 1600


def address(m, unit):
    return m.state+(0xc724+125*unit if unit<4 else 0xc918+125*(unit-12)
                    if unit<16 and unit>=12 else 0xc614+17*(unit-4)
                    if unit<12 else 0xc69c+17*(unit-16))


def world(x, y):
    return (x>>8)*128+(x&127), (y>>12)*128+(y&127)


def main():
    m = OriginalCombat(snapshot=SNAP)
    rows = []; debug = []; shots=[];pending={}
    # These are only the spy branch's display/poll boundaries. Complete 12E8
    # wave arithmetic, original AI, deaths and ejections execute normally.
    boundaries = {(0x1656,0x3f5),(0x1656,0x281),(0x1656,0x388),(0x1656,4),
                  (0x173d,0x259),(0x173d,0x86a),(0x173d,0x2f),(0,0x4cac),(0,0x2a2b),(0x103b,0x27c9)}
    absolute = {(m.load+s)*16+o for s,o in boundaries}
    spy_branch = False
    def hook(cpu, at, size, data):
        off=at-(m.load+0x12e8)*16
        if off in (0x239,0xa42,0xc12,0xcb2,0xcd3):
            from unicorn.x86_const import UC_X86_REG_BP
            bp=16*cpu.reg_read(UC_X86_REG_SS)+cpu.reg_read(UC_X86_REG_BP)
            if off==0x239:
                pending.clear();pending.update(actor=m.word(bp-2),target=m.word(bp-0x28),weapon=m.word(bp-0x48),rng_before=int.from_bytes(m.read(m.ds+0x4fc0,3),'little'),range=m.word(bp-0x5c),moved=m.read(bp-0x78+m.word(bp-0x28),1)[0])
            elif off==0xa42 and pending:
                pending.update(location=m.word(bp-0x60),damage=m.word(bp-0x7c))
            elif pending:
                pending.update(needed=m.word(bp-0x30),hit=m.word(bp-0x56),destroyed=m.word(bp-0x2c),rng=int.from_bytes(m.read(m.ds+0x4fc0,3),'little'));shots.append(dict(pending));pending.clear()
        if not spy_branch or at not in absolute: return
        sp = cpu.reg_read(UC_X86_REG_SP); ss = 16*cpu.reg_read(UC_X86_REG_SS)
        off, seg = struct.unpack('<HH',m.read(ss+sp,4))
        cpu.reg_write(UC_X86_REG_SP,sp+4);cpu.reg_write(UC_X86_REG_CS,seg);cpu.reg_write(UC_X86_REG_IP,off)
    handle = m.cpu.hook_add(UC_HOOK_CODE,hook)
    for case in range(5):
        variant=1+(case-1)%2 if case else 0
        m.reset();m.word(m.ds+0x2e3a,0);m.word(m.ds+0x15c,0)
        if case:
            spy = bytes([5,10,9,5,0,1,1,0,1,3,0,9,1,0,0,100,0])
            m.write(m.state+0xc614+17*4,spy);m.write(m.state+0xd331,bytes([4,1,1]));m.word(m.state+0x374a,1)
            m.write(m.state+0xc724+125+122,[4 if variant==1 else 1])
            if variant==2:
                m.write(m.state+0xc724+125+121,[4]);m.write(m.state+0xc614+17+8,[1])
        if case>=3:m.write(m.state+0xc724+125+39,[12])
        ids = [u for u in range(24) if m.word(m.state+0x406a+2*u)]
        seed = int.from_bytes(m.read(m.ds+0x4fc0,3),'little')
        rows.append(f'B {case} {seed} {BX} {BY} {sum(u<12 for u in ids)} {len(ids)}')
        for person in range(8):rows.append('P '+str(person)+' '+' '.join(str(b) for b in m.read(m.state+0xc614+17*person,17)))
        for bay in range(4):rows.append('M '+str(bay)+' '+' '.join(str(b) for b in m.read(m.state+0xc724+125*bay,125)))
        for unit in ids:
            raw = m.read(address(m,unit),125 if unit<4 or 12<=unit<16 else 17)
            x,y = world(m.word(m.state+0x4004+2*unit),m.word(m.state+0x4036+2*unit))
            face = m.read(m.state+0x396c+unit,1)[0];fallback=m.read(m.state+0x45b6+unit,1)[0]
            if face==255:face=fallback
            walk=m.read(m.state+0x409a+unit,1)[0]&15
            heat=m.read(m.state+(0x6e+unit if unit<4 else 0x66+unit),1)[0] if unit<4 or 12<=unit<16 else 0
            heading=m.read(m.state+0x3920+unit,1)[0]
            rows.append(f'I {unit} {x-BX} {y-BY} {face} {fallback} {walk} {heat} {heading} {fingerprint(raw):016x}')
            if unit>=16:rows.append('H '+str(unit)+' '+' '.join(str(b) for b in raw))
        ended=False
        seen=set(ids)
        for turn in range(64):
            shots.clear()
            ids = [u for u in range(24) if m.word(m.state+0x406a+2*u)]
            for unit in ids:
                if m.read(address(m,unit),1)[0]!=255:
                    m.call(0x103b,0x1774,unit,1,limit=2000000)
                    m.call(0xe31,0x3ab,unit,0,limit=2000000)
            plans=[dict(id=u,commands=list(m.read(m.state+0x32c6+48*u,4)),path=list(m.read(m.state+0x40b4+24*u,24)),orders=list(m.read(m.state+0x3800+12*u,12))) for u in ids]
            m.call(0x12e8,0xc,0,limit=40000000)
            if case and not turn:
                spy_branch=True
                span(m,0x103b,0x8a0,0xcdb,{})
                spy_branch=False
            seen.update(u for u in range(24) if m.word(m.state+0x406a+2*u))
            ids = sorted(seen)
            rng = int.from_bytes(m.read(m.ds+0x4fc0,3),'little')
            rows.append(f'T {case} {turn+1} {rng} {len(ids)}')
            states=[]
            for unit in ids:
                raw=m.read(address(m,unit),125 if unit<4 or 12<=unit<16 else 17)
                x,y=world(m.word(m.state+0x4004+2*unit),m.word(m.state+0x4036+2*unit))
                face=m.read(m.state+0x396c+unit,1)[0]
                if face==255:face=m.read(m.state+0x45b6+unit,1)[0]
                heat=m.read(m.state+(0x6e+unit if unit<4 else 0x66+unit),1)[0] if unit<4 or 12<=unit<16 else 0
                rows.append(f'U {unit} {x-BX} {y-BY} {face} {heat} {fingerprint(raw):016x}')
                states.append(dict(id=unit,x=x,y=y,face=face,heat=heat,record=list(raw)))
            debug.append(dict(case=case,turn=turn+1,rng=rng,units=states,plans=plans,shots=list(shots)))
            won=all(m.read(address(m,u),1)[0]==255 for u in ids if u>=12)
            lost=m.read(m.state+0xc614,1)[0]==255 or m.read(m.state+0xc625,1)[0]==255
            if won or lost or not m.word(m.ds+0x14a):
                rows.append(f'Z {case} {int(won)} {int(lost)}');ended=True;break
        if not ended:raise RuntimeError('Live encounter exceeded 64 complete waves')
    m.cpu.hook_del(handle)
    (ROOT/'work/m4-audit/live-campaign-debug.json').write_text(json.dumps(debug,indent=2)+'\n')
    (ROOT/'tests/fixtures/live-campaign-primary.txt').write_text('\n'.join(rows)+'\n')
    (ROOT/'tests/fixtures/live-campaign-primary.json').write_text(json.dumps(dict(
        executable_sha256=EXE_SHA,image_sha256=IMAGE_SHA,snapshot=str(SNAP.relative_to(ROOT)),
        waves=len(debug),cases=5,normal='Captured GAME3 encounter: three mechs, Rick on foot, one hostile mech and six humans. Original positions span Y sectors 12/13.',
        variants='Case 1 adds a spy passenger in Commando; case 2 a spy pilot with an armed Rex passenger. Cases 3/4 repeat those branches with finite ammunition in the affected vehicle; retain consumed rounds. Execute original 103B post-wave betrayal after the first complete wave.',
        frame='Compare world positions relative to a declared 16-aligned 1184/1600 window. The original retains packed world coordinates; its rules are not a 128x128 sector window.',
        routines=['0E31:03AB complete AI','12E8:000C complete waves, deaths and ejections','103B:08A0..0CDB spy outcome'],
        intercepted_boundaries=sorted(f'{s:04X}:{o:04X} (spy display only)' for s,o in boundaries),
        comparison='Each wave: original IDs, all living world positions, facing, heat, full-record hashes and RNG, ending at victory or essential-member loss. Numeric source-state prerequisites; no source instruction edits.'),indent=2)+'\n')
    print('Original live campaign:',len(debug),'complete waves')


if __name__=='__main__':main()
