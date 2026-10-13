#!/usr/bin/env python3
"""Bounded original recruitment, spy coin and post-wave betrayal outcomes."""
import json,struct
from combat_oracle import OriginalCombat,ROOT,UC_HOOK_CODE
from make_party_vectors import SNAP
from make_combat_vectors import fingerprint
from prepare_talk import EXE_SHA,IMAGE_SHA
from unicorn.x86_const import UC_X86_REG_AX,UC_X86_REG_CS,UC_X86_REG_IP,UC_X86_REG_SP,UC_X86_REG_SS,UC_X86_REG_BP,UC_X86_REG_DS,UC_X86_REG_EFLAGS

def people(count):
    return bytearray(v for i in range(8) for v in
        (i if i<count else 255,8,9,7,0,0,0,0,1,0,0,0,8,0,0,80,0))

def main():
    m=OriginalCombat(snapshot=SNAP);rows=[];polls=0;delay=0
    boundaries={(0x1656,0x3f5),(0x1656,0x281),(0x1656,0x388),(0x1656,4),
        (0x173d,0x259),(0x173d,0x86a),(0x173d,0x2f),(0,0x4cac),(0,0x2a2b),(0x103b,0x27c9)}
    absolute={(m.load+s)*16+o:(s,o) for s,o in boundaries}
    def hook(cpu,address,size,data):
        nonlocal polls
        if address not in absolute:return
        if absolute[address]==(0x173d,0x2f):
            cpu.reg_write(UC_X86_REG_AX,int(polls>=delay));polls+=1
        sp=cpu.reg_read(UC_X86_REG_SP);ss=cpu.reg_read(UC_X86_REG_SS)*16
        off,seg=struct.unpack('<HH',m.read(ss+sp,4));cpu.reg_write(UC_X86_REG_SP,sp+4)
        cpu.reg_write(UC_X86_REG_CS,seg);cpu.reg_write(UC_X86_REG_IP,off)
    handle=m.cpu.hook_add(UC_HOOK_CODE,hook)
    for count in (2,4,8):
      for next_id in (2,8,9):
       for skill in (5,6):
        for ever in (0,1):
         for delay in range(4):
          for vehicle in range(2):
            m.reset();polls=0;p=people(count);m.write(m.state+0xc614,p)
            for bay in range(4):m.write(m.state+0xc724+125*bay,bytes([255])+bytes(124))
            if vehicle:
                mech=bytearray(m.template());mech[121]=0;mech[122]=255;m.write(m.state+0xc724,mech)
                m.write(m.state+0xc620,b'\0')
            m.write(m.state+0xd456,[next_id]);m.write(m.state+0xd330,bytes([127,0,ever,0]))
            m.write(m.ds+0x4fc0,(0x123456).to_bytes(3,'little'));m.word(m.state+0x3938,0)
            m.call(0x9b8,0xd58,skill,limit=200000)
            chars=m.read(m.state+0xc614,136);mechs=[m.read(m.state+0xc724+125*i,125) for i in range(4)]
            flags=list(m.read(m.state+0xd330,4));seed=int.from_bytes(m.read(m.ds+0x4fc0,3),'little')
            rows.append(f'R {count} {next_id} {skill} {ever} {delay} {vehicle} {seed} {m.read(m.state+0xd456,1)[0]} '
                +' '.join(map(str,flags))+f' {fingerprint(chars):016x} '+' '.join(f'{fingerprint(v):016x}' for v in mechs))
    for discovered in range(2):
      for role in range(5):
        m.reset();p=people(5);spy=2
        for bay in range(4):
            mech=bytearray(m.template());mech[121]=0;mech[122]=255
            if bay==0 and role:
                p[17*spy+12]=0;mech[121]=spy if role<4 else 3;mech[122]=255 if role==1 else 3 if role<4 else spy
                if role in (2,3):p[17*3+12]=0;p[17*3+8]=int(role==3)
            m.write(m.state+0xc724+125*bay,mech)
        m.write(m.state+0xc614,p);m.write(m.state+0xd330,bytes([31,spy,1,1]))
        m.word(m.state+0x14a,1);m.word(m.state+0x374a,discovered)
        for unit in range(12):
            m.word(m.state+0x406a+2*unit,1)
            m.word(m.state+0x4004+2*unit,0xa40+unit)
            m.word(m.state+0x4036+2*unit,0x8040)
        bp=0x7f000;m.write(bp-256,bytes(256))
        for reg,value in ((UC_X86_REG_CS,m.load+0x103b),(UC_X86_REG_IP,0x8a0),(UC_X86_REG_DS,m.ds//16),
                (UC_X86_REG_SS,0x7000),(UC_X86_REG_BP,0xf000),(UC_X86_REG_SP,0xee00),(UC_X86_REG_EFLAGS,2)):
            m.cpu.reg_write(reg,value)
        m.cpu.emu_start((m.load+0x103b)*16+0x8a0,(m.load+0x103b)*16+0xcdb,count=200000)
        if m.cpu.reg_read(UC_X86_REG_IP)!=0xcdb:raise RuntimeError('Spy outcome span exceeded bound')
        chars=m.read(m.state+0xc614,136);flags=list(m.read(m.state+0xd330,4))
        rows.append(f'S {discovered} {role} '+' '.join(map(str,flags))+f' {fingerprint(chars):016x} '
            +' '.join(f'{fingerprint(m.read(m.state+0xc724+125*i,125)):016x}' for i in range(4)))
    def discovery_end(cpu,address,size,data):
        if address==m.load*16+0x3ae9:cpu.emu_stop()
    discovery_hook=m.cpu.hook_add(UC_HOOK_CODE,discovery_end)
    for active in range(2):
      for selected in range(8):
        m.reset();m.write(m.state+0xd331,bytes([2,1,active]));m.word(m.state+0x374a,0)
        bp=0x7f000;m.word(bp-10,selected)
        for reg,value in ((UC_X86_REG_CS,m.load),(UC_X86_REG_IP,0x399d),(UC_X86_REG_DS,m.ds//16),
                (UC_X86_REG_SS,0x7000),(UC_X86_REG_BP,0xf000),(UC_X86_REG_SP,0xee00)):
            m.cpu.reg_write(reg,value)
        m.cpu.emu_start(m.load*16+0x399d,m.load*16+0x39ff,count=20000)
        # Matching the spy jumps directly to the inspector's final boundary.
        if m.cpu.reg_read(UC_X86_REG_IP) not in (0x39ff,0x3ae9):raise RuntimeError('Inspector discovery span exceeded bound')
        rows.append(f'D {active} {selected} {m.word(m.state+0x374a)}')
    m.cpu.hook_del(discovery_hook)
    m.cpu.hook_del(handle)
    (ROOT/'tests/fixtures/recruitment-primary.txt').write_text('\n'.join(rows)+'\n')
    (ROOT/'tests/fixtures/recruitment-primary.json').write_text(json.dumps(dict(
        executable_sha256=EXE_SHA,image_sha256=IMAGE_SHA,cases=len(rows),
        routines=['09B8:0D58, complete generic recruitment and post-wait spy coin','103B:08A0..0CDB, discovered spy after a wave','0000:399D..39FF/3AE9, inspecting a suspected character'],
        prerequisites='2/4/8 people; name counter 2/8/9 including original wrap and duplicate names; doctor/technician; zero/one prior spy; 0..3 explicit polling RNG draws; optional free mech rider. Spy outcomes on foot, pilot alone, pilot with unarmed/armed rider, passenger; discovery flag 0/1 is explicit.',
        intercepted_boundaries=sorted(f'{s:04X}:{o:04X}' for s,o in boundaries),
        comparison='136 character bytes, four complete vehicle record hashes, RNG/name counter and all four spy/encounter flags. Graphics/key polling are explicit boundaries; original instructions unmodified.'),indent=2)+'\n')
    print('Original recruitment/spy cases:',len(rows))
if __name__=='__main__':main()
