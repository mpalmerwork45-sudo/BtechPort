#!/usr/bin/env python3
"""Execute all 18 original speaker programs; record numeric port-write facts."""
import argparse
import json
from pathlib import Path
from combat_oracle import OriginalCombat, UC_HOOK_INSN, UC_X86_INS_OUT
from unicorn.x86_const import (UC_X86_REG_CS,UC_X86_REG_IP,UC_X86_REG_DS,UC_X86_REG_SS,UC_X86_REG_SP,UC_X86_REG_BP)

ROOT=Path(__file__).resolve().parents[1]
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot',default='work/reference-runs/1791709609448346900/combat-menu')
    args=parser.parse_args();m=OriginalCombat(snapshot=args.snapshot);rows=[]
    writes=[]
    def watch(cpu,port,size,value,data):
        if port in (0x42,0x61):writes.append((port,value))
    m.cpu.hook_add(UC_HOOK_INSN,watch,None,1,0,UC_X86_INS_OUT)
    for p in range(1,19):
        m.reset();m.speaker=0;m.word(m.ds+0x5006,2);writes.clear()
        m.call(0x17c5,2,p,limit=40000000)
        pitch=[v for port,v in writes if port==0x42]
        noise=[v for port,v in writes if port==0x61 and v==2]
        h=14695981039346656037
        for v in pitch:h=((h^v)*1099511628211)&((1<<64)-1)
        rows.append(f'S {p} {len(pitch)//2} {h:016x} {len(noise)}')
        print(rows[-1],flush=True)
    path=ROOT/'tests/fixtures/speaker-primary.txt';path.write_text('\n'.join(rows)+'\n')
    path.with_suffix('.json').write_text(json.dumps({'authority':'original 0000:19BF -> 17C5:0002 (same physical code as 1631:1942)',
        'snapshot':args.snapshot,'delay_prerequisite':'DS5006=2 reduces CPU busy loops; divisor/noise programs remain unmodified',
        'source_exe_sha256':'15a1712682cf1fe50ca9e6a68a4b31d3bef7912401915edf7bb6242be193562a'},indent=2)+'\n')
    rows=[]
    for frequency in range(3):
        for kind in range(22):
            for flags in (0,1,2):
                for seed in (0,1,42,0xffffff,0xd23646):
                    m.reset();m.write(m.ds+0x4fc0,seed.to_bytes(3,'little'));m.write(m.state+0xd35b,[frequency]);bp=0x7f000
                    for off,value in ((6,kind),(8,flags),(-8,0)):m.word(bp+off,value)
                    for reg,value in ((UC_X86_REG_CS,m.load),(UC_X86_REG_IP,0x4900),(UC_X86_REG_DS,m.ds//16),
                            (UC_X86_REG_SS,0x7000),(UC_X86_REG_SP,0xee00),(UC_X86_REG_BP,0xf000)):m.cpu.reg_write(reg,value)
                    m.cpu.emu_start(m.load*16+0x4900,m.load*16+0x494d,count=1000)
                    if m.cpu.reg_read(UC_X86_REG_IP)!=0x494d:raise RuntimeError('Outtake span did not terminate')
                    rows.append(f'O {frequency} {kind} {flags} {seed} {m.word(bp-8)} {int.from_bytes(m.read(m.ds+0x4fc0,3),"little")}')
    (ROOT/'tests/fixtures/outtake-primary.txt').write_text('\n'.join(rows)+'\n');print(f'Original outtake decisions: {len(rows)}')
if __name__=='__main__':main()
