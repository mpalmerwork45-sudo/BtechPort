#!/usr/bin/env python3
"""Execute larger mixed encounters, AI and successive original ejections."""
import json
from combat_oracle import OriginalCombat,ROOT,UC_HOOK_CODE
from make_party_vectors import SNAP
from make_combat_vectors import fingerprint
from make_aftermath_vectors import span
from prepare_talk import EXE_SHA,IMAGE_SHA
from unicorn.x86_const import UC_X86_REG_BP,UC_X86_REG_SS

def main():
    m=OriginalCombat(snapshot=SNAP);rows=[];debug=[];deaths={};shots=[];pending={}
    def death(cpu,address,size,data):
        if address not in ((m.load+0x12e8)*16+0xc12,(m.load+0x12e8)*16+0xcb2):return
        bp=cpu.reg_read(UC_X86_REG_SS)*16+cpu.reg_read(UC_X86_REG_BP);target=m.word(bp-0x28)
        if target<4:deaths[target]=(m.word(m.state+0x4004+2*target),m.word(m.state+0x4036+2*target))
    handle=m.cpu.hook_add(UC_HOOK_CODE,death)
    def shot_trace(cpu,address,size,data):
        offset=address-(m.load+0x12e8)*16
        if offset not in (0x239,0xc12,0xcb2,0xcd3):return
        bp=cpu.reg_read(UC_X86_REG_SS)*16+cpu.reg_read(UC_X86_REG_BP)
        if offset==0x239:
            pending.clear();pending.update(actor=m.word(bp-2),target=m.word(bp-0x28),weapon=m.word(bp-0x48),
                before_rng=int.from_bytes(m.read(m.ds+0x4fc0,3),'little'),range=m.word(bp-0x5c),moved=m.read(bp-0x78+m.word(bp-0x28),1)[0],actor_position=[m.word(m.state+0x4004+2*m.word(bp-2))&127,m.word(m.state+0x4036+2*m.word(bp-2))&127],target_position=[m.word(m.state+0x4004+2*m.word(bp-0x28))&127,m.word(m.state+0x4036+2*m.word(bp-0x28))&127],target_face=list(m.read(m.state+0x396c+m.word(bp-0x28),1)),target_fallback=list(m.read(m.state+0x45b6+m.word(bp-0x28),1)))
        elif pending:
            pending.update(needed=m.word(bp-0x30),hit=m.word(bp-0x56),
                rng=int.from_bytes(m.read(m.ds+0x4fc0,3),'little'),location=m.word(bp-0x60), damage=m.word(bp-0x7c), destroyed=m.word(bp-0x2c));shots.append(dict(pending));pending.clear()
    trace=m.cpu.hook_add(UC_HOOK_CODE,shot_trace)
    for case,seed in enumerate((0x123456,0xd23646)):
        m.reset();deaths.clear();m.word(m.ds+0x2e3a,0);m.word(m.ds+0x5006,2)
        m.word(m.ds+0x14a,1);m.word(m.ds+0x15e,2);m.word(m.state+0xe48e,0);m.word(m.state+0x3772,0)
        m.write(m.state+0xd333,[0]);m.write(m.buffer+0x101d,bytes([64])*4096)
        m.write(m.state+0x406a,bytes(48));m.write(m.state+0x5e,bytes(60));m.write(m.state+0x3986,bytes(12))
        m.write(m.state+0xd576,bytes(8));m.write(m.state+0x3800,bytes([255])*288);m.write(m.state+0x32c6,bytes([255])*1152)
        people=[]
        for i in range(8):
            people+= [i if i<5 else 255,8,(9,10,7,12,10,0,0,0)[i],7,2,2,2,2,1 if i<2 else 0,0,0,
                13 if i==3 else 9,0 if i in (0,4) else 1 if i==1 else 8,1,25,80,0]
        m.write(m.state+0xc614,people)
        for i in range(8):m.write(m.state+0xc724+125*i,bytes([255])+bytes(124))
        ids=[0,1,6,7,12,13]+list(range(16,24));friends=[0,1,6,7]
        positions=[(64,64),(68,68),(62,69),(61,64),(76,64),(82,68)]+[(76+3*(i%4),70+3*(i//4)) for i in range(8)]
        kinds=[2,1,4,4,0,3]+[4]*8
        templates=[m.template(),m.template(1),m.template(2),m.image[0x282e7:0x282e7+125]]
        rows.append(f'B {case} {seed} {case} 4 {len(ids)}')
        for i,(unit,(x,y),kind) in enumerate(zip(ids,positions,kinds)):
            direction=2 if i<4 else 6;weapon=13 if i==3 else 9 if i<4 else 7+(i%7)
            if kind<4:
                b=bytearray(templates[kind]);b[121]=unit if unit<4 else 0;b[122]=4 if unit==0 else 255
                if (not case and unit<2) or (case and unit>=12):b[17:36]=bytes([1])*19
                m.write(m.state+(0xc724+125*unit if unit<4 else 0xc918+125*(unit-12)),b)
            elif unit>=16:
                m.write(m.state+0xc69c+17*(unit-16),[0,8,0,0,0,0,0,0,0,0,0,weapon,8,0,0,80,0])
            m.word(m.state+0x406a+2*unit,1);m.word(m.state+0x4004+2*unit,0xc00+x);m.word(m.state+0x4036+2*unit,0xc000+y)
            for at in (0x3920,0x396c,0x45b6):m.write(m.state+at+unit,[direction])
            # The combat caller initializes each sprite sequence too. A stale
            # pointer from a different unit changes facing on its first step.
            sequence=m.word(m.ds+0x563e)*16+0x25a+4*(direction+(8 if kind==4 else 0))
            m.write(m.word(m.ds+0x5640)*16+0x1f6+4*unit,m.read(sequence,4))
            rows.append(f'I {unit} {kind} {x} {y} {direction} {weapon}')
        m.write(m.ds+0x4fc0,seed.to_bytes(3,'little'));ejected=set();ended=False
        for turn in range(128):
            shots.clear()
            # AI performs its own class-first nearest-target scan. Actor IDs
            # stay original; no port decisions are supplied to the oracle.
            for unit in sorted(ids):
                at=m.state+(0xc724+125*unit if unit<4 else 0xc918+125*(unit-12) if 12<=unit<16 else 0xc614+17*(unit-4) if unit<12 else 0xc69c+17*(unit-16))
                if m.read(at,1)[0]!=255:m.call(0xe31,0x3ab,unit,0,limit=2000000)
            plans=[dict(id=u,commands=list(m.read(m.state+0x32c6+48*u,4)),
                path=list(m.read(m.state+0x40b4+24*u,24)),orders=list(m.read(m.state+0x3800+12*u,12))) for u in ids]
            m.call(0x12e8,0xc,0,limit=40000000)
            for unit in (0,1):
                if m.read(m.state+0xc724+125*unit,1)[0]==255 and unit not in ejected:
                    if unit not in deaths:raise RuntimeError('Destroyed owned mech missed its original position')
                    # 12E8 already calls A35 at the destruction boundary. Do not
                    # eject again after the wave or reset the original positions.
                    ejected.add(unit)
                    for member in ((0,4) if not unit else (1,)):
                        if m.read(m.state+0xc614+17*member,1)[0]!=255 and 4+member not in ids:ids.insert(len(friends),4+member);friends.append(4+member)
            rng=int.from_bytes(m.read(m.ds+0x4fc0,3),'little');rows.append(f'T {case} {turn+1} {rng} {len(ids)}')
            state=[]
            for unit in ids:
                at=m.state+(0xc724+125*unit if unit<4 else 0xc918+125*(unit-12) if 12<=unit<16 else 0xc614+17*(unit-4) if unit<12 else 0xc69c+17*(unit-16));inf=unit not in (0,1,12,13)
                b=m.read(at,17 if inf else 125);face=m.read(m.state+0x396c+unit,1)[0]
                if face==255:face=m.read(m.state+0x45b6+unit,1)[0]
                x=m.word(m.state+0x4004+2*unit)&127;y=m.word(m.state+0x4036+2*unit)&127
                heat=0 if inf else m.read(m.state+(0x6e+unit if unit<4 else 0x66+unit),1)[0]
                rows.append(f'U {unit} {x} {y} {face} {heat} {fingerprint(b):016x}')
                state.append(dict(id=unit,x=x,y=y,direction=face,heat=heat,record=list(b)))
            debug.append(dict(case=case,turn=turn+1,rng=rng,continue_flag=m.word(m.ds+0x14a),plans=plans,shots=list(shots),units=state))
            dead=m.read(m.state+0xc614,1)[0]==255
            won=all(u['record'][0]==255 for u in state if u['id']>=12)
            if dead or won or not m.word(m.ds+0x14a):
                rows.append(f'Z {case} {int(won)} {int(dead)} {len(ejected)}');ended=True;break
        if not ended:
            (ROOT/'work/m4-audit/mixed-encounters-debug.json').write_text(json.dumps(debug,indent=2)+'\n')
            raise RuntimeError('Mixed encounter did not end within 128 complete turns')
    m.cpu.hook_del(handle)
    m.cpu.hook_del(trace)
    (ROOT/'work/m4-audit/mixed-encounters-debug.json').write_text(json.dumps(debug,indent=2)+'\n')
    (ROOT/'tests/fixtures/mixed-encounters-primary.txt').write_text('\n'.join(rows)+'\n')
    (ROOT/'tests/fixtures/mixed-encounters-primary.json').write_text(json.dumps(dict(
        executable_sha256=EXE_SHA,image_sha256=IMAGE_SHA,encounters=2,turns=len(debug),
        routines=['0E31:03AB AI including target search','12E8:000C complete turns','0D43:0A35 ejections called by the complete-turn program'],
        prerequisites='Controlled open MAP1 terrain, two owned mechs/two people against two mechs/eight people, five character records, one-point weakened friendly/enemy vehicle structure, two seeds; computer orders for all living friends.',
        ejection_boundary='Original complete-turn routine calls A35 itself. Observe the resulting activation flags and add its live people to the next AI wave.',
        comparison='Every complete turn: original IDs, living positions, facing, heat, complete record fingerprints and RNG; victory or the original continue-flag loss boundary, and ejections. No whole DOS UI encounter claim.',intercepted_boundaries=[]),indent=2)+'\n')
    print('Original complete mixed encounters:',len(debug),'turns')
if __name__=='__main__':main()
