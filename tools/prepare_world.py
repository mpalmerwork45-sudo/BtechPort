#!/usr/bin/env python3
"""Generate a bounded Citadel neighbourhood with the owner's original routines.

This is a reproducible owner-derived cache, not a discovered static world file.
The independent C game reads its tiles without running an emulator. Full native
terrain generation and wider world/campaign transitions remain future work.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from combat_oracle import OriginalCombat, ROOT

def generate(seed,data=ROOT/'Original DOS'):
    o=OriginalCombat(source=data/'BTECH.EXE');noise=bytearray()
    o.write(o.ds+0x4fc0,seed.to_bytes(3,'little'))
    # Original 0000:50D3..50F3 supplies 256 low-byte RNG values to 09FB.
    for _ in range(256):noise.append(o.call(0x187f,0xbc0)&255)
    o.write(o.buffer+0x9fb,noise)
    area=bytearray(192*192)
    for ry in range(11,14):
        for rx in range(11,14):
            o.call(0x187f,0x104e,16*ry+rx)
            for by in range(8):
                for bx in range(8):
                    o.call(0x187f,0x1314,(rx<<8)+16*bx+8,(ry<<12)+16*by+8)
                    grid=o.read(o.buffer+0x7ad,576)
                    for dy in range(8):
                        at=((ry-11)*64+by*8+dy)*192+(rx-11)*64+bx*8
                        area[at:at+8]=grid[(8+dy)*24+8:(8+dy)*24+16]
    if max(area)>=250:raise ValueError('Generated terrain exceeds the verified tile sheet')
    # MAP1's packed entrance words establish sector (12,12). The cache holds
    # generated terrain; native lookup overlays the authentic MTP at that site.
    return area,noise

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--seed',type=int,default=123456)
    p.add_argument('--data',type=Path,default=ROOT/'Original DOS')
    p.add_argument('--output',type=Path,default=ROOT/'work/world-data.bin')
    p.add_argument('--fixture',type=Path,help='Publish only original sector fingerprints');a=p.parse_args()
    if not 0<a.seed<1<<24:p.error('Seed must be a nonzero 24-bit value')
    area,noise=generate(a.seed,a.data)
    exe=hashlib.sha256((a.data/'BTECH.EXE').read_bytes()).digest()
    local=hashlib.sha256((a.data/'MAP1.MTP').read_bytes()).digest()
    header=b'BTW1'+struct.pack('<HHHHI',704,704,192,192,a.seed)+exe+local
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_bytes(header+area)
    a.output.with_suffix('.json').write_text(json.dumps({'format':'BTW1','scope':'Nine generated sectors around Citadel; MAP1 overlay at sector 12,12',
        'executable_sha256':exe.hex(),'map1_sha256':local.hex(),'seed':a.seed,'origin':[704,704],'size':[192,192],
        'routines':['0000:50D3..50F3','187F:0BC0','187F:104E','187F:1314'],
        'noise_sha256':hashlib.sha256(noise).hexdigest(),'tiles_sha256':hashlib.sha256(area).hexdigest(),
        'no_instruction_patches':True,'native_generator':False},indent=2)+'\n')
    if a.fixture:
        from make_combat_vectors import fingerprint
        rows=[f'# Original 187F:104E/1314, seed {a.seed}, 256 original RNG noise bytes; nine complete 64x64 sectors.']
        for y in range(3):
            for x in range(3):
                raw=b''.join(area[(64*y+dy)*192+64*x:(64*y+dy)*192+64*x+64] for dy in range(64))
                rows.append(f'W {11+x} {11+y} {a.seed} {fingerprint(raw):016x}')
        a.fixture.write_text('\n'.join(rows)+'\n')
    print(f'Generated {len(area)} surrounding tiles from original instructions: {a.output}')
