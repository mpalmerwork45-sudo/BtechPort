#!/usr/bin/env python3
"""Execute original finite firing/Kick programs through 0000:1732."""
import struct
from combat_oracle import OriginalCombat, ROOT, DS

o=OriginalCombat(snapshot=ROOT/'work/reference-runs/1791709609448346900/combat-menu')
rows=['# Original 0000:1732 finite attack programs; frame IDs only, no artwork bytes.']
for group in range(18):
    table=DS+([0x2d58,0x2d78,0x2d98,0x2db8][group] if group<4 else 0x3ff8+(group-4)*32)
    for direction in range(8):
        o.reset();off,seg=struct.unpack_from('<HH',o.image,table+direction*4)
        o.word(o.ds+0x1f6,off);o.word(o.ds+0x1f8,seg+o.load);frames=[]
        for _ in range(12):
            at=o.word(o.ds+0x1f6)+16*o.word(o.ds+0x1f8)
            if o.read(at,1)==b'\xff':break
            frames.append(o.call(0,0x1732,0))
        else:raise RuntimeError('Unterminated original effect')
        rows.append(f'P {group} {direction} {len(frames)} '+' '.join(map(str,frames)))
o.reset();o.word(o.ds+0x256,0x41d8);o.word(o.ds+0x258,o.ds//16)
impact=[250+o.call(0,0x1732,24) for _ in range(3)]
rows.append('P 18 0 3 '+' '.join(map(str,impact)))
for infantry in (0,1):
    for direction in range(8):
        o.reset();off,seg=struct.unpack_from('<HH',o.image,DS+(0x27a if infantry else 0x25a)+4*direction)
        o.word(o.ds+0x1f6,off);o.word(o.ds+0x1f8,seg+o.load)
        frames=[o.call(0,0x1732,0)-(16 if infantry else 0) for _ in range(12)]
        rows.append(f'G {infantry} {direction} 12 '+' '.join(map(str,frames)))
(ROOT/'tests/fixtures/combat-poses.txt').write_text('\n'.join(rows)+'\n')
print(f'Wrote {len(rows)-1} executed original firing/Kick frame programs')
