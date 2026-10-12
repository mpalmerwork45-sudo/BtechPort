#!/usr/bin/env python3
"""Original numeric service spans, with explicit pre-menu caller locals."""
from pathlib import Path
from combat_oracle import OriginalCombat,UC_X86_REG_CS,UC_X86_REG_IP,UC_X86_REG_BP,UC_X86_REG_SP,UC_X86_REG_SS,UC_X86_REG_DS,UC_X86_REG_ES
from make_party_vectors import fingerprint,SNAP
ROOT=Path(__file__).resolve().parents[1]
def span(m,start,end,locals=None):
    bp=0x7f000;m.write(bp-0x100,bytes(0x120))
    for offset,value in (locals or {}).items():m.word(bp+offset,value)
    for reg,value in [(UC_X86_REG_CS,m.load+0x9b8),(UC_X86_REG_IP,start),(UC_X86_REG_DS,m.ds//16),(UC_X86_REG_ES,m.state//16),(UC_X86_REG_SS,0x7000),(UC_X86_REG_BP,0xf000),(UC_X86_REG_SP,0xee00)]:m.cpu.reg_write(reg,value)
    m.cpu.emu_start((m.load+0x9b8)*16+start,(m.load+0x9b8)*16+end,count=2000000)
    if m.cpu.reg_read(UC_X86_REG_IP)!=end:raise RuntimeError(f'Service span {start:x} stalled at {m.cpu.reg_read(UC_X86_REG_IP):x}')
def cash(m,value=None):
    if value is not None:m.write(m.state+0xd370,value.to_bytes(4,'little'))
    return int.from_bytes(m.read(m.state+0xd370,4),'little')
def main():
    m=OriginalCombat(snapshot=SNAP);rows=['# Original 09B8 numeric repair/reload/refit spans; no menu input or instructions patched.']
    for choice in range(8):
        for loan in range(3):
            m.reset();b=bytearray(m.template(loan));b[123]=choice%4;b[124]=choice//4;b[39:51]=bytes(range(12));b[107:117]=bytes(range(60,70))
            m.write(m.state+0xc724,b);m.word(m.state+0x68,0);m.word(m.state+0x76,m.word(m.ds+0x1d8c+2*choice));m.write(m.state+0xd31d,[choice]);cash(m,50000)
            span(m,0x99e,0xd41)
            rows.append(f'F {choice} {loan} {cash(m)} {fingerprint(m.read(m.state+0xc724,125))}')
    for kind,start,end,first,last in [(0,0x282,0x312,17,28),(1,0x3ac,0x43c,28,36)]:
        for funds in [0,3,4,8,9,18,30,100]:
            m.reset();b=bytearray(m.template());b[first]=max(0,b[first+69]-3);b[first+1]=max(0,b[first+70]-2)
            m.write(m.state+0xc724,b);m.word(m.state+0x68,0);cash(m,funds)
            span(m,start,end,{-0x2e if not kind else -0x2c:5})
            rows.append(f'P {kind} {funds} {cash(m)} {fingerprint(m.read(m.state+0xc724,125))}')
    for funds in [0,1,2,3,4,8,30]:
        m.reset();b=bytearray(m.template());b[39]=0;b[107]=5
        m.write(m.state+0xc724,b);m.word(m.state+0x68,0);cash(m,funds)
        span(m,0x1932,0x1980,{-6:5,-14:2,-12:0})
        rows.append(f'A {funds} {cash(m)} {fingerprint(m.read(m.state+0xc724,125))}')
    (ROOT/'tests/fixtures/service-rules.txt').write_text('\n'.join(rows)+'\n');print(f'Wrote {len(rows)-1} original service cases')
if __name__=='__main__':main()
