#!/usr/bin/env python3
"""Execute the original GAME reader/writer against private memory-backed DOS I/O.

No code patches or writes to either reference tree. The spans stop before the
original load UI/world reconstruction, and do not establish full campaign parity.
"""
import argparse
import hashlib
import json
from pathlib import Path
from combat_oracle import OriginalCombat,ROOT
from unicorn import UC_HOOK_INTR
from unicorn.x86_const import (UC_X86_REG_AX,UC_X86_REG_BX,UC_X86_REG_CX,UC_X86_REG_DX,
    UC_X86_REG_CS,UC_X86_REG_IP,UC_X86_REG_DS,UC_X86_REG_SS,UC_X86_REG_SP,UC_X86_REG_BP,UC_X86_REG_EFLAGS)

class Codec:
    def __init__(self,blob,snapshot):
        self.machine=OriginalCombat(snapshot=snapshot);self.blob=blob;self.position=0;self.output=bytearray();self.events=[]
        self.machine.cpu.hook_add(UC_HOOK_INTR,self.interrupt)
    def interrupt(self,c,num,data):
        ax=c.reg_read(UC_X86_REG_AX);cx=c.reg_read(UC_X86_REG_CX);dx=c.reg_read(UC_X86_REG_DX);ah=ax>>8
        if num!=0x21:raise RuntimeError(f'Unaudited interrupt {num:x}')
        if ah in (0x3c,0x3d):c.reg_write(UC_X86_REG_AX,3)
        elif ah==0x43:c.reg_write(UC_X86_REG_CX,0)
        elif ah==0x44:c.reg_write(UC_X86_REG_DX,0)
        elif ah in (0x3f,0x40):
            address=c.reg_read(UC_X86_REG_DS)*16+dx
            if ah==0x3f:
                body=self.blob[self.position:self.position+cx];self.machine.write(address,body);self.position+=len(body);n=len(body)
            else:self.output.extend(self.machine.read(address,cx));n=cx
            c.reg_write(UC_X86_REG_AX,n);self.events.append((ah,n))
        elif ah==0x42:c.reg_write(UC_X86_REG_AX,0);c.reg_write(UC_X86_REG_DX,0)
        elif ah==0x3e:c.reg_write(UC_X86_REG_AX,0)
        else:raise RuntimeError(f'Unaudited DOS request {ax:x}')
        c.reg_write(UC_X86_REG_EFLAGS,c.reg_read(UC_X86_REG_EFLAGS)&~1)
    def descriptor(self,flags):
        m=self.machine;m.write(m.ds+0x5000,b'PRIVATE.GAM\0')
        return m.call(0x187f,0x33d0,0x5000,m.ds//16,flags,0x180,limit=20000)
    def span(self,start,end,local,fd):
        m=self.machine
        for reg,value in ((UC_X86_REG_CS,m.load),(UC_X86_REG_IP,start),(UC_X86_REG_DS,m.ds//16),
                (UC_X86_REG_SS,0x7000),(UC_X86_REG_SP,0xee00),(UC_X86_REG_BP,0xf000)):m.cpu.reg_write(reg,value)
        m.word(0x7f000+local,fd);m.word(0x7f000-6,0)
        m.cpu.emu_start(m.load*16+start,m.load*16+end,count=100000)
        if m.cpu.reg_read(UC_X86_REG_IP)!=end:raise RuntimeError('Codec instruction bound exceeded')
    def roundtrip(self):
        fd=self.descriptor(0x8000);self.span(0x334f,0x33d8,-12,fd);m=self.machine
        if m.read(m.state+0xc614,0xf44)!=self.blob[1:0xf45] or m.read(m.buffer+0xa44b,4)!=self.blob[0xf45:]:
            raise RuntimeError('Original reader projection differs')
        self.span(0x368b,0x3710,-8,fd)
        if self.output!=self.blob:raise RuntimeError('Original writer roundtrip differs')
        return {'length':len(self.blob),'sha256':hashlib.sha256(self.blob).hexdigest(),'dos_reads_writes':self.events}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot',default='work/reference-runs/1791709609448346900/combat-menu')
    parser.add_argument('files',nargs='*',type=Path);args=parser.parse_args();facts=[]
    for path in args.files or [ROOT/f'Original DOS/GAME{i}' for i in range(1,7)]:
        facts.append({'file':str(path),**Codec(path.read_bytes(),args.snapshot).roundtrip()});print('PASS: original reader/writer',path)
    target=ROOT/'work/m4-audit/original-codec.json';target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps({'read_span':'0000:334F..33D8','write_span':'0000:368B..3710','snapshot':args.snapshot,
        'prerequisites':'Original CRT descriptor opened on a private memory-backed DOS file; caller stack supplied; instructions unmodified',
        'files':facts},indent=2)+'\n')
if __name__=='__main__':main()
