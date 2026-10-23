#!/usr/bin/env python3
"""Extract original numeric terrain inputs for the independent C generator.

Ordinary cache preparation uses the standard library. Optional --fixture
generation runs bounded original instructions through the research oracle.
This cache is owner-derived input data, not an original static world map.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def fingerprint(raw):
    h=14695981039346656037
    for value in raw:h=((h^value)*1099511628211)&((1<<64)-1)
    return h

def generate(seed,data=ROOT/'Original DOS'):
    from combat_oracle import OriginalCombat
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

def extract(executable,map1,seed=0x020304):
    """Pure bounded extraction shared by CLI and campaign importer."""
    if not 0<seed<1<<24:raise ValueError('Seed must be a nonzero 24-bit value')
    from exepack import unpack
    from prepare_talk import EXE_SHA, IMAGE_SHA
    source,metadata=unpack(executable)
    if metadata['input_sha256']!=EXE_SHA or metadata['image_sha256']!=IMAGE_SHA:
        raise ValueError('World tables require the audited executable')
    ranges=[(0x1c6c0+0xb0b-17,336),(0x1c6c0+0xc1d,1024),
            (0x1c6c0+0x209d,64),(0x1c6c0+0x211d,96),(0x1c6c0+0x215d,256)]
    tables=b''.join(source[at:at+n] for at,n in ranges)
    exe=hashlib.sha256(executable).digest()
    local=hashlib.sha256(map1).digest()
    header=b'BTW3'+struct.pack('<HHHHI',704,704,192,192,seed)+exe+local
    return header+struct.pack('<Q',fingerprint(tables))+tables, {
        'format':'BTW3','scope':'Static primary inputs; independent C midpoint and tile generation',
        'executable_sha256':exe.hex(),'map1_sha256':local.hex(),'seed':seed,
        'origin':[704,704],'size':[192,192],'ranges':ranges,
        'tables_sha256':hashlib.sha256(tables).hexdigest(),
        'no_instruction_patches':True,'native_generator':True}

if __name__=='__main__':
    # DS:4FC0 starts 04 03 02 in the audited executable. Its first 256
    # draws match BUFFER:09FB in the live DOSBox world capture exactly.
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--seed',type=int,default=0x020304)
    p.add_argument('--data',type=Path,default=ROOT/'Original DOS')
    p.add_argument('--output',type=Path,default=ROOT/'work/world-data.bin')
    p.add_argument('--fixture',type=Path,help='Publish only original sector fingerprints');a=p.parse_args()
    if not 0<a.seed<1<<24:p.error('Seed must be a nonzero 24-bit value')
    # Runtime C generation consumes only original static numeric tables.
    # Full original generation remains available for differential fixtures.
    cache,metadata=extract((a.data/'BTECH.EXE').read_bytes(),(a.data/'MAP1.MTP').read_bytes(),a.seed)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_bytes(cache)
    a.output.with_suffix('.json').write_text(json.dumps(metadata,indent=2)+'\n')
    if a.fixture:
        area,noise=generate(a.seed,a.data)
        rows=[f'# Original 187F:104E/1314, seed {a.seed}, 256 original RNG noise bytes; nine complete 64x64 sectors.']
        for y in range(3):
            for x in range(3):
                raw=b''.join(area[(64*y+dy)*192+64*x:(64*y+dy)*192+64*x+64] for dy in range(64))
                rows.append(f'W {11+x} {11+y} {a.seed} {fingerprint(raw):016x}')
        a.fixture.write_text('\n'.join(rows)+'\n')
    print(f'Prepared {len(cache)-88} bytes of original world tables: {a.output}')
