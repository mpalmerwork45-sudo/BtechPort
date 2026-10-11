#!/usr/bin/env python3
"""Record original kick, robot fire and mech-versus-robot attack spans."""
import random
from combat_oracle import OriginalCombat, ROOT
from make_combat_vectors import fingerprint

o=OriginalCombat();source=random.Random(1988);rows=[]
for ak,tk,weapons in [(0,0,[32]),(0,1,[15,16,17,18,23,24,29,32]),(1,0,range(14))]:
    for w in weapons:
        for n in range(48 if w==32 else 24):
            args=(w,source.randrange(-1,3),source.randrange(13),source.randrange(5),
                  source.choice([0,7,8,13,17,24,29]) if not ak else 0,
                  source.randrange(8),source.choice([0,8,16]),n%2,source.randrange(1,1<<24),
                  ak,tk,n%3)
            legs=(source.randrange(8,16),source.randrange(8,16))
            v=o.shot(*args,legs=legs,target_x=65)
            rows.append('A '+' '.join(map(str,(*args,*legs)))+' '+
                ' '.join(map(str,(v['needed'],v['hit'],v['location'],v['damage'],v['dead'],v['toppled'],
                                 v['rng'],v['ammo'],v['pool'],v['burning'])))+f" {fingerprint(v['target']):016x}")
(ROOT/'tests/fixtures/combat-physical.txt').write_text(
    '# Original 12E8:0239..0CD3; explicit close-range caller prerequisites, no code patches.\n'+'\n'.join(rows)+'\n')
print(f'Wrote {len(rows)} original physical/robot attack cases')
