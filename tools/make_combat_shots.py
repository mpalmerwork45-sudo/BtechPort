#!/usr/bin/env python3
"""Generate original shot-span results, including RNG and record fingerprints."""
import random
from combat_oracle import OriginalCombat, ROOT
from make_combat_vectors import fingerprint

o=OriginalCombat();source=random.Random(1988);rows=[]
for weapon in (15,16,17,18,23,24,29):
    for variant in (0,1):
        for _ in range(64):
            args=(weapon,source.randrange(-1,3),source.randrange(13),source.randrange(5),
                  source.choice((0,7,8,12,13,16,17,23,24,29)),source.randrange(8),
                  source.choice((0,8,16)),variant,source.randrange(1,1<<24))
            v=o.shot(*args)
            rows.append('S '+' '.join(map(str,args))+f" {v['needed']} {v['hit']} {v['location']} {v['damage']} {v['dead']} {v['toppled']} {v['rng']} {fingerprint(v['target']):016x}")
(ROOT/'tests/fixtures/combat-shots.txt').write_text('# Original 12E8:0239..0CD3; stop before destruction cleanup/graphics.\n'+'\n'.join(rows)+'\n')
print(f'Wrote {len(rows)} original shots')
