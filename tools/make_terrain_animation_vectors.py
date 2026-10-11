#!/usr/bin/env python3
"""Execute the owner's ICN decoder, animation initialization and tile swaps.

The captured DOS session is EGA and its old animation workspace is not used.
Supply the original resource bytes and the packed-pixel display prerequisite,
then execute the unmodified routines; publish only crop hashes and tile IDs.
"""
from combat_oracle import OriginalCombat, ROOT
from make_combat_vectors import fingerprint

o=OriginalCombat(snapshot=ROOT/'work/reference-runs/1791709609448346900/combat-menu')
data=(ROOT/'Original DOS/ANIMATE.ICN').read_bytes()
o.word(o.ds+0x4fba,1);o.write(0x90000,data[2:])
o.call(0x173d,0x49d,0,0x9000,0,0x9400,limit=2000000)
# 0000:3287..32A0 copies 0x780 words after the first blank tile.
o.call(0x187f,0xa76,128,0x9400,0xd582,o.state//16,0x780)
tiles=list(o.read(o.ds+0x4b0,10));o.word(o.ds+0x5800,0)
rows=['# Original 173D:049D decode, 187F:0A76 initialization and 0000:240B swaps; packed-pixel context.']
for step in range(6):
    o.call(0,0x240b);phase=o.word(o.ds+0x5800)
    for group,tile in enumerate(tiles):
        raw=o.read(o.state+0x4614+tile*128,128)
        pixels=bytes(v for c in raw for v in (c>>4,c&15))
        rows.append(f'T {tile} {phase} {1+3*group+phase} {fingerprint(pixels):016x}')
(ROOT/'tests/fixtures/terrain-animation.txt').write_text('\n'.join(rows)+'\n')
print(f'Wrote {len(rows)-1} original terrain-frame comparisons')
