#!/usr/bin/env python3
"""Record the original terrain-only encounter scan; this is not a native parity claim.

The native reachability guard is an explicitly requested correction. This
audit records what the original actually checks, including cross-wall cases,
without treating that correction as a recovered original rule.
"""
import hashlib
import json
from combat_oracle import OriginalCombat, ROOT
from make_aftermath_vectors import span
from prepare_talk import EXE_SHA, IMAGE_SHA


def main():
    snapshot = ROOT/'work/reference-runs/1791962848011430927/town-start'
    m = OriginalCombat(snapshot=snapshot)
    cases = []
    for x, y in ((1276, 1078), (1278, 1090), (1288, 1020), (1409, 1090), (1339, 1117)):
        for seed in (1, 2, 3, 17, 1234):
            m.reset()
            px, py = (x//128 << 8) | (x & 127), (y//128 << 12) | (y & 127)
            m.call(0, 0x17bb, px, py)
            m.call(0x187f, 0x1314, px, py)
            m.call(0x187f, 0x1df8)
            for i in range(8):
                m.write(m.state+0xc724+125*i, m.template() if i < 4 else bytes([255])+bytes(124))
            m.write(m.ds+0x4fc0, seed.to_bytes(3, 'little'))
            m.word(m.ds+0x150, 85)
            span(m, 0x5ab, 0xd68, 0x1462, {})
            units = []
            for unit in range(12, 24):
                if not m.word(m.state+0x406a+2*unit):
                    continue
                qx, qy = m.word(m.state+0x4004+2*unit), m.word(m.state+0x4036+2*unit)
                units.append(dict(id=unit, x=(qx >> 8)*128+(qx & 127), y=(qy >> 12)*128+(qy & 127)))
            cases.append(dict(cursor=[x, y], seed=seed,
                              final_rng=int.from_bytes(m.read(m.ds+0x4fc0, 3), 'little'), units=units))
    result = dict(executable_sha256=EXE_SHA, image_sha256=IMAGE_SHA,
        snapshot=str(snapshot.relative_to(ROOT)), snapshot_ram_sha256=hashlib.sha256(m.snapshot).hexdigest(),
        routines=['0000:17BB cursor', '187F:1314 working grid', '187F:1DF8 grid offsets',
                  '05AB:0D68..1462 random candidates and terrain placement'],
        prerequisites='Original loaded Starport snapshot, five controlled cursor locations, four active loan templates, gate 85 and five seeds. The viewport remains the loaded Starport context, including its surrounding pieces; this does not replay sector-loading transitions.',
        observation='Placement checks terrain 16..84 and viewport bounds, with two ground tiles for vehicles. It does not search for a route to the party. Numeric results document this bounded original behavior; native reachable-placement tests intentionally add a guard and are not exact-position comparisons.',
        intercepted_boundaries=[], no_instruction_patches=True, cases=cases)
    (ROOT/'tests/fixtures/encounter-placement-audit.json').write_text(json.dumps(result, indent=2)+'\n')
    print(f'Original terrain-placement audit: {len(cases)} controlled cases')


if __name__ == '__main__':
    main()
