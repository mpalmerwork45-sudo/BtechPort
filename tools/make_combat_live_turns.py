#!/usr/bin/env python3
"""Compare controlled complete robot/Locust turns with the owner's instructions.

The existing third-encounter RAM capture supplies selectors and resources.
Each case supplies explicit unit/command prerequisites; no code is patched.
The final argument is zero to avoid the campaign Game Over UI on player death.
"""
import argparse
from combat_oracle import OriginalCombat, ROOT
from make_combat_vectors import fingerprint

SNAPSHOT = ROOT / 'work/reference-runs/1791709609448346900/combat-menu'

def generate():
    o = OriginalCombat(snapshot=SNAPSHOT)
    rows = ['# Controlled 103B:1774, 0E31:03AB and complete 12E8:000C(0) turns; MAP1.',
            '# Cases supply ranks, positions, heat, equipment and orders; no executable patches.']
    for kind in (3, 4, 5):
        for case in range(42):
            o.reset(); loan = case % 3; movement = case % 4
            if movement == 3: movement = 255
            if movement == 2 and not o.template(loan)[50]: movement = 0
            count = 4 + case % 4 if kind == 3 else 3 if kind==5 else 2
            seed = 123456 + case * 78901; heat = case % 3 * 5
            px, py = ((96, 93), (84, 85), (99, 93))[case % 3]
            gx, gy = px + 4, py + (case % 2) * 4
            o.word(o.ds + 0x2e3a, 0); o.word(o.state + 0x14a, 1)
            o.word(o.state + 0xe48e, 0); o.word(o.state + 0x374c, count - 1 if kind == 3 else 0)
            o.write(o.state + 0x406a, bytes(48)); o.write(o.state + 0x5e, bytes(60))
            o.write(o.state + 0xd576, bytes(8)); o.write(o.state + 0xc618, bytes(5))
            o.write(o.state + 0x3800, bytes([255]) * 288)
            o.write(o.state + 0x32c6, bytes([255]) * 1152)
            o.write(o.state + 0xc724, o.template(loan)); o.write(o.state + 0xc918, o.template())
            o.write(o.state + 0xc995, o.template())
            initial = []
            ids = [0] + ([16 + i for i in range(count - 1)] if kind == 3 else list(range(12,12+count-1)))
            for i, unit in enumerate(ids):
                x = px if not i else px + 6 + ((i - 1) % 3) * 4
                y = py if not i else py + ((i - 1) // 3) * 4
                direction = 2 if not i else 6
                weapon = (case + i - 1) % 14
                body = 2 + (case + i) % 11
                o.word(o.state + 0x406a + 2 * unit, 1)
                o.word(o.state + 0x4004 + 2 * unit, 0xc00 + x)
                o.word(o.state + 0x4036 + 2 * unit, 0xc000 + y)
                for a in (0x396c, 0x3920, 0x45b6): o.write(o.state + a + unit, [direction])
                if i and kind == 3:
                    o.write(o.state + 0xc69c + 17 * (i - 1),
                            [0, body, 0, 0, 0, 0, 0, 0, 0, 0, 0, weapon, 8, 0, 0, body * 10, 0])
                initial += [x, y, direction, heat if not i else 0, weapon, body]
            o.write(o.state + 0x6e, [heat])
            if movement != 255: o.write(o.state + 0x32c6, [movement, 0xcc, gx, gy])
            # Alternate one gun, all available guns, Kick, and idle orders.
            order = case % 4
            weapons = 1 if order == 0 else 11 if order == 1 else 0
            for w in range(weapons): o.write(o.state + 0x3800 + w, [ids[1]])
            if order == 2: o.write(o.state + 0x380b, [ids[1]])
            o.write(o.ds + 0x4fc0, seed.to_bytes(3, 'little'))
            # Refresh camera, cover and terrain even for an idle order. The
            # capture's old position otherwise leaves stale 32AE/3750 fields.
            o.call(0x103b, 0x1774, 0, 1, limit=2000000)
            for unit in ids[1:]: o.call(0xe31, 0x3ab, unit, 0, limit=2000000)
            o.call(0x12e8, 0xc, 0, limit=20000000)
            row = 'C ' + ' '.join(map(str, [kind, loan, seed, count, movement, gx, gy, order] + initial))
            results = []
            for i, unit in enumerate(ids):
                address = 0xc724 if not i else 0xc69c + 17 * (i - 1) if kind == 3 else 0xc918+125*(i-1)
                record = o.read(o.state + address, 17 if i and kind == 3 else 125)
                face = o.read(o.state + 0x396c + unit, 1)[0]
                if face == 255: face = o.read(o.state + 0x45b6 + unit, 1)[0]
                h = o.read(o.state + (0x6e if not i else 0x66+unit), 1)[0] if not (i and kind == 3) else 0
                results += [str(o.word(o.state + 0x4004 + 2 * unit) & 127),
                            str(o.word(o.state + 0x4036 + 2 * unit) & 127), str(face), str(h),
                            f'{fingerprint(record):016x}']
            rows.append(row + ' | ' + ' '.join(results) + ' ' +
                        str(int.from_bytes(o.read(o.ds + 0x4fc0, 3), 'little')))
    (ROOT / 'tests/fixtures/combat-live-turns.txt').write_text('\n'.join(rows) + '\n')
    print(f'Wrote {len(rows) - 2} complete original live encounter turns')

if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    generate()
