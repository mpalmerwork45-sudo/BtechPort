#!/usr/bin/env python3
"""Complete original AI encounters in loaded town/landscape contexts.

Original candidate placement and every wave execute normally. The declared
party, terrain-file boundaries and seed are test prerequisites, not a live
DOSBox journey. There are no presentation or arithmetic instruction patches.
"""
import json
from combat_oracle import OriginalCombat,ROOT,UC_HOOK_CODE
from make_live_campaign_vectors import SNAP,address,world
from make_combat_vectors import fingerprint
from make_aftermath_vectors import span
from town_context import load_town,cursor
from prepare_talk import EXE_SHA,IMAGE_SHA
from unicorn.x86_const import UC_X86_REG_BP,UC_X86_REG_SS


def main():
    m=OriginalCombat(snapshot=SNAP);rows=[];details=[];waves=0;debug=[];shots=[];pending={}
    def hook(cpu,at,size,data):
        off=at-(m.load+0x12e8)*16
        if off not in (0x239,0xa42,0xc12,0xcb2,0xcd3):return
        bp=16*cpu.reg_read(UC_X86_REG_SS)+cpu.reg_read(UC_X86_REG_BP)
        if off==0x239:
            pending.clear();pending.update(actor=m.word(bp-2),target=m.word(bp-0x28),weapon=m.word(bp-0x48),rng_before=int.from_bytes(m.read(m.ds+0x4fc0,3),'little'),range=m.word(bp-0x5c),moved=m.read(bp-0x78+m.word(bp-0x28),1)[0])
        elif off==0xa42 and pending:pending.update(location=m.word(bp-0x60),damage=m.word(bp-0x7c))
        elif pending:
            pending.update(needed=m.word(bp-0x30),hit=m.word(bp-0x56),destroyed=m.word(bp-0x2c),rng=int.from_bytes(m.read(m.ds+0x4fc0,3),'little'));shots.append(dict(pending));pending.clear()
    handle=m.cpu.hook_add(UC_HOOK_CODE,hook)
    contexts=((2,1337,1117,4),(2,1337,1117,5),(4,1180,1434,1),(4,1180,1434,5))
    for case,(town,x,y,seed) in enumerate(contexts):
        load_town(m,town);px,py=cursor(m,x,y)
        m.word(m.ds+0x2e3a,0);m.word(m.ds+0x15c,0);m.word(m.ds+0x14a,1)
        m.write(m.state+0x406a,bytes(48));m.write(m.state+0x393c,bytes(48))
        m.write(m.state+0xd331,bytes([255,0,0]));m.word(m.state+0x374a,0)
        if town==2:
            for i in range(4):m.write(m.state+0xc724+125*i,[255]);m.write(m.state+0xc614+17*i+12,[8])
            friends=[4,5,6,7]
        else:friends=[0,1,2,7]
        for unit in friends:
            place=unit if unit<4 else 4+(unit-4 if town==2 else 0)
            m.word(m.state+0x406a+2*unit,1)
            m.word(m.state+0x4004+2*unit,px+m.word(m.ds+0x45c+2*place))
            m.word(m.state+0x4036+2*unit,py+m.word(m.ds+0x474+2*place))
        m.write(m.ds+0x4fc0,seed.to_bytes(3,'little'))
        span(m,0x5ab,0xd68,0x1462,{})
        ids=[u for u in range(24) if m.word(m.state+0x406a+2*u)]
        if len(ids)<=len(friends):raise RuntimeError('No original enemy in context')
        # Ordinary initial facing/path prerequisites, supplied by 103B's
        # combat setup before computer orders. No record/rule changes.
        for u in ids:
            m.write(m.state+0x396c+u,[6]);m.write(m.state+0x45b6+u,[6])
            m.write(m.state+0x409a+u,[0 if u<4 or 12<=u<16 else 16]);m.write(m.state+0x3920+u,[255])
        bx=(x-64)//16*16;by=(y-64)//16*16
        rng=int.from_bytes(m.read(m.ds+0x4fc0,3),'little')
        rows.append(f'B {case} {rng} {bx} {by} {len(friends)} {len(ids)} {town} {x} {y} 0 {seed}')
        for p in range(8):rows.append('P '+str(p)+' '+' '.join(map(str,m.read(m.state+0xc614+17*p,17))))
        for bay in range(4):rows.append('M '+str(bay)+' '+' '.join(map(str,m.read(m.state+0xc724+125*bay,125))))
        placed=[]
        for u in ids:
            raw=m.read(address(m,u),125 if u<4 or 12<=u<16 else 17)
            wx,wy=world(m.word(m.state+0x4004+2*u),m.word(m.state+0x4036+2*u))
            heat=m.read(m.state+(0x6e+u if u<4 else 0x66+u),1)[0] if u<4 or 12<=u<16 else 0
            rows.append(f'I {u} {wx-bx} {wy-by} 6 6 0 {heat} 255 {fingerprint(raw):016x}')
            if u>=12:rows.append(('V ' if u<16 else 'H ')+str(u)+' '+' '.join(map(str,raw)))
            placed.append(dict(id=u,x=wx,y=wy))
        seen=set(ids)
        for turn in range(64):
            shots.clear()
            for u in range(24):
                if m.word(m.state+0x406a+2*u) and m.read(address(m,u),1)[0]!=255:
                    m.call(0x103b,0x1774,u,1,limit=2000000);m.call(0xe31,0x3ab,u,0,limit=2000000)
            plans=[dict(id=u,commands=list(m.read(m.state+0x32c6+48*u,4)),path=list(m.read(m.state+0x40b4+24*u,24)),orders=list(m.read(m.state+0x3800+12*u,12))) for u in ids]
            m.call(0x12e8,0xc,0,limit=40000000)
            debug.append(dict(case=case,turn=turn+1,shots=list(shots),plans=plans))
            seen.update(u for u in range(24) if m.word(m.state+0x406a+2*u));ids=sorted(seen)
            rng=int.from_bytes(m.read(m.ds+0x4fc0,3),'little');waves+=1
            rows.append(f'T {case} {turn+1} {rng} {len(ids)}')
            for u in ids:
                raw=m.read(address(m,u),125 if u<4 or 12<=u<16 else 17)
                wx,wy=world(m.word(m.state+0x4004+2*u),m.word(m.state+0x4036+2*u))
                face=m.read(m.state+0x396c+u,1)[0]
                if face==255:face=m.read(m.state+0x45b6+u,1)[0]
                heat=m.read(m.state+(0x6e+u if u<4 else 0x66+u),1)[0] if u<4 or 12<=u<16 else 0
                rows.append(f'U {u} {wx-bx} {wy-by} {face} {heat} {fingerprint(raw):016x}')
            won=all(m.read(address(m,u),1)[0]==255 for u in ids if u>=12)
            lost=m.read(m.state+0xc614,1)[0]==255 or m.read(m.state+0xc625,1)[0]==255
            if won or lost or not m.word(m.ds+0x14a):
                rows.append(f'Z {case} {int(won)} {int(lost)}');break
        else:rows.append(f'Z {case} 0 0')
        details.append(dict(case=case,town=town,cursor=[x,y],seed=seed,initial=placed,waves=turn+1,
                            end='victory' if won else 'essential-member-loss' if lost else '64-wave observation bound'))
    m.cpu.hook_del(handle)
    (ROOT/'work/m4-audit/town-encounter-debug.json').write_text(json.dumps(debug,indent=2)+'\n')
    (ROOT/'tests/fixtures/town-encounters-primary.txt').write_text('\n'.join(rows)+'\n')
    (ROOT/'tests/fixtures/town-encounters-primary.json').write_text(json.dumps(dict(
        executable_sha256=EXE_SHA,image_sha256=IMAGE_SHA,cases=details,waves=waves,
        routines=['05AB:0D68..1462 placement','103B:1774 actor camera','0E31:03AB complete AI','12E8:000C complete waves'],
        prerequisites='Original GAME3 party in two original town payload contexts, explicit cursor and RNG; four foot soldiers in Starport, three mechs and Rick on foot in MAP4. Town file-read boundaries supplied; initial facing 6, heading 255, gait 0. Sound/verbose/outtake display disabled.',
        comparison='Complete per-wave RNG, all record hashes, living coordinates/facing/heat, deaths/ejections and final victory/loss.',
        no_instruction_patches=True),indent=2)+'\n')
    print('Original town encounters:',len(contexts),'encounter contexts;',waves,'waves')


if __name__=='__main__':main()
