#!/usr/bin/env python3
"""Run complete original arena/prison fights from declared caller states.

The original town loader, opponent setup, AI and tactical waves execute without
instruction edits. These are controlled numeric prerequisites, not a claim of
having played each approach to the building in DOSBox.
"""
import argparse
import json
from combat_oracle import OriginalCombat, ROOT
from make_live_campaign_vectors import SNAP, address, world
from make_combat_vectors import fingerprint
from make_aftermath_vectors import span
from town_context import load_town, cursor
from prepare_talk import EXE_SHA, IMAGE_SHA


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', type=int, help='Probe one case in ignored work files')
    parser.add_argument('--towns', action='store_true', help='Additional complete Starport and mixed-party town fights')
    args = parser.parse_args()
    m = OriginalCombat(snapshot=SNAP)
    rows, details, records = [], [], []
    contexts = [(4, seed, rental, difficulty) for seed, rental, difficulty in
                ((1, 0, 0), (42, 0, 6), (1, 1, 0), (42, 1, 6))]
    contexts += [(3, seed, 0, 0) for seed in (1, 42)]
    contexts += [(1, seed, 0, 0) for seed in (3, 8)]
    if args.towns:contexts=[(1,seed,0,0) for seed in (4,5,1,42)]
    for case, (kind, seed, rental, difficulty) in enumerate(contexts):
        if args.case is not None and args.case != case:
            continue
        town, x, y, bx, by = (2, 1323, 1111, 1216, 1024) if kind == 4 else (3, 1680, 932, 1664, 896) if kind == 3 else (0, 1263, 1675, 1184, 1600)
        if args.towns:
            town,x,y=(2,1320,1110) if case<2 else (4,1180,1434)
            bx=(x-64)//16*16;by=(y-64)//16*16
        if town:load_town(m, town)
        else:
            # This sector and its combat window contain no town overlay.
            # Run the actual generated landscape from the startup seed.
            m.reset();m.write(m.ds+0x4fc0,(0x020304).to_bytes(3,'little'))
            noise=bytes(m.call(0x187f,0xbc0)&255 for _ in range(256))
            m.write(m.buffer+0x9fb,noise);m.call(0x187f,0x104e,16*(y//128)+x//128)
            m.write(m.state+0xd346,[0])
        px, py = cursor(m, x, y)
        m.word(m.ds+0x2e3a, 0);m.word(m.ds+0x15c, 0);m.word(m.ds+0x14a, 1)
        m.word(m.ds+0x15e, 2);m.word(m.ds+0x150, 139 if kind == 4 else 85)
        m.write(m.state+0x406a, bytes(48));m.write(m.state+0x393c, bytes(48))
        m.write(m.state+0x4004, bytes([255])*48);m.write(m.state+0x4036, bytes([255])*48)
        m.write(m.state+0x396c, bytes(24));m.write(m.state+0x45b6, bytes(24))
        m.write(m.state+0x3920, bytes([255])*24)
        m.write(m.state+0xd331, bytes([255, 0, 0]));m.word(m.state+0x374a, 0)
        m.word(m.state+0x3772, 0);m.word(m.state+0xe48e, rental)
        m.write(m.state+0xd32f, [0]);m.write(m.state+0xd30f, [difficulty])
        # The building takes Jason alone; other records remain available to
        # the outer caller but must not take turns in its temporary arena.
        if kind != 1:
            for bay in range(4):m.write(m.state+0xc724+125*bay, [255])
        friend = 4 if kind == 3 else 0
        friends = [0, 1, 2, 7] if kind == 1 else [friend]
        m.write(m.state+0xc620, [8 if kind == 3 else 0])
        if kind == 4:
            record = bytearray(m.template(0 if rental else 1))
            record[121] = 0;record[122] = 255
            m.write(m.state+0xc724, record)
            m.write(m.state+0xd452, [record[0], 255, 255, 255])
        elif kind == 3:m.write(m.state+0xd30c, [7])
        else:
            m.write(m.state+0xc724+122, [255]);m.write(m.state+0xc614+3*17+12, [8])
        if args.towns and town==2:
            # The port admits only infantry. Use the four actual GAME3
            # people with their original equipment and no active vehicles.
            friends=[4,5,6,7]
            for bay in range(4):
                m.write(m.state+0xc724+125*bay,[255]);m.write(m.state+0xc614+17*bay+12,[8])
        for u in friends:
            m.word(m.state+0x406a+2*u, 1)
            place = u if args.towns and town==2 else 4 if u == 7 else u
            m.word(m.state+0x4004+2*u, px+(m.word(m.ds+0x45c+2*place) if kind == 1 else 0))
            m.word(m.state+0x4036+2*u, py+(m.word(m.ds+0x474+2*place) if kind == 1 else 0))
        span(m, 0x103b, 0xa1, 0x1b8, {6: 1})
        m.write(m.ds+0x4fc0, seed.to_bytes(3, 'little'))
        if kind == 1:span(m, 0x5ab, 0xd68, 0x1462, {})
        else:m.call(0x07dc, 0x0d49, 0x81 if kind == 4 else 0, 0 if kind == 4 else 0x88)
        # 07DC clears old party coordinates during setup; its caller then
        # installs the single participant at the arena/yard entry point.
        if kind != 1:
            m.word(m.state+0x4004+2*friend, px);m.word(m.state+0x4036+2*friend, py)
        ids = [u for u in range(24) if m.word(m.state+0x406a+2*u)]
        if not any(u >= 12 for u in ids):raise RuntimeError('No opponent in the declared context')
        for u in ids:
            face = 4 if u == friend and kind == 4 else 2 if u == 13 and rental else 6
            gait = 0 if u == friend or u == 13 and rental else 12
            m.write(m.state+0x396c+u, [face]);m.write(m.state+0x45b6+u, [face])
            m.write(m.state+0x409a+u, [gait+(16 if 4 <= u < 12 or u >= 16 else 0)])
            m.write(m.state+0x3920+u, [255])
        rng = int.from_bytes(m.read(m.ds+0x4fc0, 3), 'little')
        rows.append(f'B {case} {rng} {bx} {by} {len(friends)} {len(ids)} {town} {x} {y} 0 0')
        rows.append(f'E {kind} {rental} {difficulty}')
        for p in range(8):rows.append('P '+str(p)+' '+' '.join(map(str, m.read(m.state+0xc614+17*p, 17))))
        for bay in range(4):rows.append('M '+str(bay)+' '+' '.join(map(str, m.read(m.state+0xc724+125*bay, 125))))
        for u in ids:
            raw = m.read(address(m, u), 125 if u < 4 or 12 <= u < 16 else 17)
            wx, wy = world(m.word(m.state+0x4004+2*u), m.word(m.state+0x4036+2*u))
            face = m.read(m.state+0x396c+u, 1)[0];walk = m.read(m.state+0x409a+u, 1)[0]&15
            heat = m.read(m.state+(0x6e+u if u < 4 else 0x66+u), 1)[0] if u < 4 or 12 <= u < 16 else 0
            rows.append(f'I {u} {wx-bx} {wy-by} {face} {face} {walk} {heat} 255 {fingerprint(raw):016x}')
            if u >= 12:rows.append(('V ' if u < 16 else 'H ')+str(u)+' '+' '.join(map(str, raw)))
        seen = set(ids)
        for turn in range(128):
            for u in range(24):
                # E48E's harmless second rental mech is a spectator. The
                # original command loop skips its AI until the theft alarm.
                if rental and u == 13:continue
                if m.word(m.state+0x406a+2*u) and m.read(address(m, u), 1)[0] != 255:
                    m.call(0x103b, 0x1774, u, 1, limit=2000000)
                    m.call(0xe31, 0x3ab, u, 0, limit=2000000)
            m.call(0x12e8, 0xc, 0, limit=40000000)
            seen.update(u for u in range(24) if m.word(m.state+0x406a+2*u))
            ids = sorted(seen)
            rng = int.from_bytes(m.read(m.ds+0x4fc0, 3), 'little')
            rows.append(f'T {case} {turn+1} {rng} {len(ids)}')
            for u in ids:
                raw = m.read(address(m, u), 125 if u < 4 or 12 <= u < 16 else 17)
                wx, wy = world(m.word(m.state+0x4004+2*u), m.word(m.state+0x4036+2*u))
                face = m.read(m.state+0x396c+u, 1)[0]
                if face == 255:face = m.read(m.state+0x45b6+u, 1)[0]
                heat = m.read(m.state+(0x6e+u if u < 4 else 0x66+u), 1)[0] if u < 4 or 12 <= u < 16 else 0
                rows.append(f'U {u} {wx-bx} {wy-by} {face} {heat} {fingerprint(raw):016x}')
                records.append(dict(case=case,wave=turn+1,id=u,record=list(raw)))
            won = all(m.read(address(m, u), 1)[0] == 255 for u in ids if u >= 12)
            lost = m.read(m.state+0xc614, 1)[0] == 255 or kind == 4 and m.read(m.state+0xc724, 1)[0] == 255 or kind == 1 and m.read(m.state+0xc625, 1)[0] == 255
            if won or lost:
                rows.append(f'Z {case} {int(won)} {int(lost)}')
                break
        else:raise RuntimeError(f'Case {case} exceeded 128 complete waves')
        details.append(dict(case=case,kind=kind,town=town,cursor=[x,y],seed=seed,rental=rental,difficulty=difficulty,waves=turn+1,won=won,lost=lost))
        print(details[-1], flush=True)
    prefix = ROOT/('work/m4-audit/complete-encounters-probe' if args.case is not None else 'tests/fixtures/complete-town-encounters-primary' if args.towns else 'tests/fixtures/complete-encounters-primary')
    prefix.with_suffix('.txt').write_text('\n'.join(rows)+'\n')
    (ROOT/'work/m4-next').mkdir(parents=True,exist_ok=True)
    (ROOT/'work/m4-next/complete-records.json').write_text(json.dumps(records)+'\n')
    prefix.with_suffix('.json').write_text(json.dumps(dict(
        executable_sha256=EXE_SHA,image_sha256=IMAGE_SHA,cases=details,
        routines=['07DC:0D49 special opponent setup','05AB:0D68..1462 outdoor placement','103B:00A1..01B8 command/heat setup','103B:1774 actor camera','0E31:03AB AI','12E8:000C complete waves'],
        prerequisites=('GAME3 four infantry in Starport; three mechs and Rick on foot in MAP4. Actual party equipment and original opponent placement.' if args.towns else 'GAME3 Jason alone, owned Wasp or rented Locust in arena/prison; three owned mechs and Rick on foot in generated sector D9 at 1263,1675.')+' Original town payloads or generated terrain, declared cursor, seed and arena rank. Original 103B command/heat initialization; inactive coordinates FFFF and unused facing zero. Display/sound off. Arena gate 139, others 85. Harmless rental spectator receives no orders.',
        comparison='Every wave RNG, all records, living coordinates/facing/heat, death/ejection and final win/loss',
        no_instruction_patches=True),indent=2)+'\n')


if __name__ == '__main__':main()
