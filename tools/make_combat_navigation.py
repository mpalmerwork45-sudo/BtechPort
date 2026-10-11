#!/usr/bin/env python3
"""Extract numeric navigation cases from an explicitly supplied DOS capture."""
import argparse
import random
from combat_oracle import OriginalCombat, ROOT, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_BX
from make_combat_vectors import fingerprint

def generate(snapshot):
    o=OriginalCombat(snapshot=snapshot); source=random.Random(1988); rows=[]
    positions=[(64,77,72,77),(84,85,96,93),(96,93,96,85),(101,85,95,85)]
    for _ in range(256):
        x,y=source.randrange(20,107),source.randrange(20,107)
        positions.append((x,y,x+source.randrange(-18,19),y+source.randrange(-18,19)))
    for x,y,tx,ty in positions:
        o.reset();o.word(o.buffer+0xa44b,0xc00+x);o.word(o.buffer+0xa44d,0xc000+y)
        outside=[]
        def watch(cpu,address,size,data):
            if address in ((o.load+0xe31)*16+0x1c96,(o.load+0xe31)*16+0x1d36):
                if cpu.reg_read(UC_X86_REG_BX)>=576: outside.append(True)
        hook=o.cpu.hook_add(UC_HOOK_CODE,watch)
        result=o.call(0xe31,0x1bfe,0,12,0xc00+tx,0xc000+ty);o.cpu.hook_del(hook)
        rows.append(f"{'X' if outside else 'L'} {x} {y} {tx} {ty} {result}")
        for computer in (0,1):
            o.reset();o.write(o.state+0x406a,bytes(48))
            o.word(o.state+0x406a,1);o.word(o.state+0x4082,1)
            o.word(o.state+0x4004,0xc00+x);o.word(o.state+0x4036,0xc000+y)
            o.word(o.state+0x401c,0xc00+tx);o.word(o.state+0x404e,0xc000+ty)
            o.write(o.state+0x3920,[6]);o.write(o.state+0x3994,[computer])
            o.call(0,0x17bb,0xc00+x,0xc000+y)
            o.call(0x187f,0x1314,0xc00+x,0xc000+y);o.call(0x187f,0x1df8)
            o.write(o.state+0x32c6,bytes([0,0xcc,tx,ty])+bytes([255])*44)
            o.word(o.state+0x3770,8);o.call(0x103b,0x193b,0)
            value=fingerprint(o.read(o.state+0x40b4,24))
            rows.append(f"N {x} {y} {tx} {ty} {computer} {value:016x}")
    return rows

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('snapshot',help='prefix before -ram.bin/-state.json')
    args=parser.parse_args();rows=generate(args.snapshot)
    (ROOT/'tests/fixtures/combat-navigation.txt').write_text(
        '# Original MAP1 navigation; controlled coordinates and one waypoint.\n'+'\n'.join(rows)+'\n')
    print(f'Wrote {len(rows)} original navigation cases')
