#!/usr/bin/env python3
"""Whole-sector fingerprints from bounded, unmodified original instructions."""
from combat_oracle import OriginalCombat, ROOT
from make_combat_vectors import fingerprint

o=OriginalCombat();rows=[]
sectors=[(0,0),(1,1),(4,8),(6,15),(8,8),(10,15),(11,14),(12,12),(14,2),(15,15)]
for seed in [1,123456,0xabcdef]:
    o.reset();o.write(o.ds+0x4fc0,seed.to_bytes(3,'little'))
    noise=bytes(o.call(0x187f,0xbc0)&255 for _ in range(256))
    o.write(o.buffer+0x9fb,noise)
    for rx,ry in sectors:
        o.call(0x187f,0x104e,16*ry+rx);sector=bytearray(4096)
        for by in range(8):
            for bx in range(8):
                o.call(0x187f,0x1314,(rx<<8)+16*bx+8,(ry<<12)+16*by+8)
                grid=o.read(o.buffer+0x7ad,576)
                for y in range(8):
                    at=(by*8+y)*64+bx*8
                    sector[at:at+8]=grid[(8+y)*24+8:(8+y)*24+16]
        rows.append(f'G {seed} {rx} {ry} {fingerprint(sector):016x}')
(ROOT/'tests/fixtures/world-native.txt').write_text(
    '# Original 187F:104E/1314; three seeds, ten sectors incl world edges; no patches.\n'+'\n'.join(rows)+'\n')
print(f'Captured {len(rows)} original whole sectors')
