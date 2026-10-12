#!/usr/bin/env python3
"""Bounded, unmodified original Rex/alley and generic-agent setup observations."""
from pathlib import Path
from combat_oracle import OriginalCombat,UC_HOOK_CODE,UC_X86_REG_CS,UC_X86_REG_IP,UC_X86_REG_BP,UC_X86_REG_SP,UC_X86_REG_SS,UC_X86_REG_DS,UC_X86_REG_ES
ROOT=Path(__file__).resolve().parents[1]
SNAP=ROOT/'work/reference-runs/1791709609448346900/combat-menu'
def fingerprint(b):
    h=14695981039346656037
    for n in b:h=((h^n)*1099511628211)&((1<<64)-1)
    return f'{h:016x}'
def stop_call(m,segment,entry,stop,*args):
    reached=[]
    def watch(cpu,address,size,data):
        if address==(m.load+segment)*16+stop:reached.append(True);cpu.emu_stop()
    hook=m.cpu.hook_add(UC_HOOK_CODE,watch)
    try:m.call(segment,entry,*args,limit=500000)
    except RuntimeError:
        if not reached:raise
    finally:m.cpu.hook_del(hook)
    if not reached:raise RuntimeError('Original span missed its boundary')
def main():
    m=OriginalCombat(snapshot=SNAP);rows=['# Original 09B8:104E..136D and E4F..FB7; all other slots empty.']
    for seed in [1,2,3,4,17,1234,5678,0x123456,0xffffff]:
        m.reset()
        for i in range(16):m.write(m.state+0xc614+17*i,bytes([255])+bytes(16))
        for i in range(4):m.write(m.state+0xd452+i,[255])
        m.write(m.state+0xd456,[1]);m.write(m.ds+0x4fc0,seed.to_bytes(3,'little'))
        stop_call(m,0x9b8,0x104e,0x136d)
        rex=m.read(m.state+0xc625,17);mech=m.read(m.state+0xc724,125)
        enemies=[]
        for i in range(8,16):
            b=m.read(m.state+0xc614+17*i,17)
            if b[0]!=255:enemies.extend([str(m.word(m.state+0x4014+2*i)&127),str(m.word(m.state+0x4046+2*i)&127),fingerprint(b)])
        rows.append('R '+str(seed)+' '+str(int.from_bytes(m.read(m.ds+0x4fc0,3),'little'))+' '+rex.hex()+' '+fingerprint(mech)+' '+str(len(enemies)//3)+' '+' '.join(enemies))
    for person in range(2,10):
        for skill in range(7):
            m.reset();m.write(m.state+0xd456,[person]);m.write(m.state+0xc625,bytes(17))
            for i in range(4):m.write(m.state+0xc724+125*i,[255])
            bp=0x7f000;m.word(bp-2,1);m.word(bp+6,skill)
            for reg,value in [(UC_X86_REG_CS,m.load+0x9b8),(UC_X86_REG_IP,0xe4f),(UC_X86_REG_DS,m.ds//16),(UC_X86_REG_ES,m.state//16),(UC_X86_REG_SS,0x7000),(UC_X86_REG_BP,0xf000),(UC_X86_REG_SP,0xee00)]:m.cpu.reg_write(reg,value)
            m.cpu.emu_start((m.load+0x9b8)*16+0xe4f,(m.load+0x9b8)*16+0xfb7,count=200000)
            if m.cpu.reg_read(UC_X86_REG_IP)!=0xfb7:raise RuntimeError('Agent numeric span stalled')
            rows.append(f'G {person} {skill} {int.from_bytes(m.read(m.ds+0x4fc0,3),"little")} {m.read(m.state+0xc625,17).hex()}')
    (ROOT/'tests/fixtures/party-setup.txt').write_text('\n'.join(rows)+'\n')
    print(f'Wrote {len(rows)-1} original party setup cases')
    rows=['# Original 05AB:D68..FBF, numeric encounter candidates before terrain placement.']
    for owned in range(2):
        for seed in [1,2,3,4,17,1234,5678,0x123456,0xffffff]:
            m.reset();m.write(m.ds+0x4fc0,seed.to_bytes(3,'little'))
            for i in range(8,16):m.write(m.state+0xc614+17*i,bytes(17))
            for i in range(8):m.write(m.state+0xc724+125*i,bytes([255])+bytes(124))
            if owned:m.write(m.state+0xc724,m.template())
            bp=0x7f000;m.write(bp-0x100,bytes(0x120))
            for reg,value in [(UC_X86_REG_CS,m.load+0x5ab),(UC_X86_REG_IP,0xd68),(UC_X86_REG_DS,m.ds//16),(UC_X86_REG_ES,m.state//16),(UC_X86_REG_SS,0x7000),(UC_X86_REG_BP,0xf000),(UC_X86_REG_SP,0xee00)]:m.cpu.reg_write(reg,value)
            m.cpu.emu_start((m.load+0x5ab)*16+0xd68,(m.load+0x5ab)*16+0xfbf,count=500000)
            if m.cpu.reg_read(UC_X86_REG_IP)!=0xfbf:raise RuntimeError('Encounter span stalled')
            values=[]
            for i in range(8,16):
                b=m.read(m.state+0xc614+17*i,17)
                if b[0]!=255:values.append(f'{8+i} {fingerprint(b)}')
            for i in range(4,8):
                b=m.read(m.state+0xc724+125*i,125)
                if b[0]!=255:values.append(f'{8+i} {fingerprint(b)}')
            dx=m.word(bp-6);dy=m.word(bp-12)
            rows.append(f'E {owned} {seed} {int.from_bytes(m.read(m.ds+0x4fc0,3),"little")} {dx if dx<32768 else dx-65536} {dy if dy<32768 else dy-65536} {len(values)} '+ ' '.join(values))
    (ROOT/'tests/fixtures/encounter-setup.txt').write_text('\n'.join(rows)+'\n')
    print(f'Wrote {len(rows)-1} original encounter candidate cases')
if __name__=='__main__':main()
