#!/usr/bin/env python3
"""Original PC-speaker pitch and complete SIF IRQ trace fingerprints."""
from pathlib import Path
import struct
from combat_oracle import OriginalCombat,UC_HOOK_INSN,UC_X86_INS_OUT,UC_X86_REG_CS,UC_X86_REG_IP,UC_X86_REG_SP,UC_X86_REG_SS,UC_X86_REG_AX
from unicorn.x86_const import UC_X86_REG_DX
ROOT=Path(__file__).resolve().parents[1]
def main():
    m=OriginalCombat();outputs=[]
    def watch(cpu,port,size,value,data):
        if port in [0x42,0x61]:outputs.append((port,value))
    m.cpu.hook_add(UC_HOOK_INSN,watch,None,1,0,UC_X86_INS_OUT)
    rows=['# Original 184B:0139..015F / 0298; PIT 1193182 Hz, IRQ reload 4095, PC-speaker pace 4.']
    for note in range(128):
        m.reset()
        for reg,value in [(UC_X86_REG_CS,0x184b),(UC_X86_REG_IP,0x139),(UC_X86_REG_SS,0x7000),(UC_X86_REG_SP,0xf000),(UC_X86_REG_AX,note)]:m.cpu.reg_write(reg,value)
        m.cpu.emu_start(0x184b0+0x139,0x184b0+0x15f,count=5000)
        if m.cpu.reg_read(UC_X86_REG_IP)!=0x15f:raise RuntimeError('Pitch span stalled')
        rows.append(f'N {note} {m.cpu.reg_read(UC_X86_REG_DX)}')
    m.reset();m.write(m.buffer+0x244b,(ROOT/'Original DOS/WWOODBT.SIF').read_bytes()+bytes(4))
    m.call(0x184b,0x306,0);m.call(0x184b,0x306,1,0x244b,m.buffer//16,4)
    h=14695981039346656037;count=0;divisor=0
    while m.speaker&3:
        outputs.clear();m.call(0x184b,0x298)
        pit=[v for p,v in outputs if p==0x42]
        if pit:
            if len(pit)!=2:raise RuntimeError('Unexpected PIT write count')
            divisor=pit[0]+(pit[1]<<8)
        pos=m.word(0x184b0+0x205)-0x244b;clock=m.read(0x184b0+0x209,1)[0]
        for n in struct.pack('<HHBB',pos,divisor,bool(m.speaker&3),clock):h=((h^n)*1099511628211)&((1<<64)-1)
        count+=1
        if count>20000:raise RuntimeError('Title trace did not terminate')
    rows.append(f'T {count} {h:016x} {pos} {divisor} {clock}')
    rows.append('P '+m.read(m.ds+0x141a,26).hex())
    (ROOT/'tests/fixtures/audio-primary.txt').write_text('\n'.join(rows)+'\n')
    print(f'Wrote 128 original pitch cases and {count} title IRQ fingerprint steps')
if __name__=='__main__':main()
