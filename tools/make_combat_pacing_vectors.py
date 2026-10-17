#!/usr/bin/env python3
"""Observe waits inside complete original combat waves, not just the delay helper.

The existing MAP1 capture supplies resources. Controlled orders, positions and
seed are explicit prerequisites. No original instruction bytes are patched.
"""
import argparse
import json
from combat_oracle import OriginalCombat, ROOT, UC_HOOK_CODE
from make_combat_live_turns import SNAPSHOT
from prepare_talk import EXE_SHA, IMAGE_SHA
from unicorn.x86_const import UC_X86_REG_SS, UC_X86_REG_SP, UC_X86_REG_CS, UC_X86_REG_IP


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    m = OriginalCombat(snapshot=SNAPSHOT)
    events = []
    # Return only across host-facing boundaries: retrace/key waits, screen
    # flips, sound/outtakes and drawing. All movement/attack instructions run.
    skip = {(0x173d, 6), (0x173d, 0x259), (0x173d, 0x6c3),
            (0, 0x19bf), (0, 0x48b7), (0xe31, 0x1f09)}
    watch = {(m.load + s)*16 + o: (s, o) for s, o in
             skip | {(0xe31, 0x1dcc), (0x12e8, 0x1002), (0x12e8, 0x12c7)}}

    def hook(cpu, at, size, data):
        if at not in watch:
            return
        where = watch[at]
        sp = cpu.reg_read(UC_X86_REG_SP)
        stack = 16*cpu.reg_read(UC_X86_REG_SS) + sp
        caller = (m.word(stack+2)-m.load, m.word(stack))
        if where == (0x12e8, 0x1002):
            events.append(('step',))
        elif where == (0x12e8, 0x12c7):
            events.append(('shot',))
        elif where == (0xe31, 0x1dcc):
            events.append(('pace', *caller))
        elif where == (0x173d, 6):
            events.append(('wait', m.word(stack+4), *caller))
        elif where == (0x173d, 0x259):
            events.append(('key', *caller))
        if where in skip:
            off, seg = m.word(stack), m.word(stack+2)
            cpu.reg_write(UC_X86_REG_SP, sp+4)
            cpu.reg_write(UC_X86_REG_CS, seg)
            cpu.reg_write(UC_X86_REG_IP, off)

    handle = m.cpu.hook_add(UC_HOOK_CODE, hook)
    rows = ['# graphics speed moving orders | steps shots pauses key_waits speed_retraces pose_retraces final_x final_y',
            '# Controlled complete 12E8:000C(0) waves; MAP1, two intact mechs, no enemy orders.']
    cases = 0
    for graphics in range(2):
        for speed in range(6):
            for moving, orders in ((0, 0), (1, 0), (1, 1), (1, 2)):
                m.reset()
                m.word(m.ds+0x2e3a, graphics)
                m.word(m.ds+0x14a, 1)
                m.word(m.ds+0x15c, 0)
                m.word(m.ds+0x15e, speed)
                m.word(m.state+0xe48e, 0)
                m.word(m.state+0x374c, 0)
                for address, length in ((0x406a, 48), (0x5e, 60), (0xd576, 8), (0xc618, 5)):
                    m.write(m.state+address, bytes(length))
                for address, length in ((0x3800, 288), (0x32c6, 1152), (0x4004, 100)):
                    m.write(m.state+address, bytes([255])*length)
                m.write(m.state+0xc724, m.template(0))
                m.write(m.state+0xc918, m.template(2))
                for unit, x in ((0, 84), (12, 90)):
                    m.word(m.state+0x406a+2*unit, 1)
                    m.word(m.state+0x4004+2*unit, 0xc00+x)
                    m.word(m.state+0x4036+2*unit, 0xc055)
                    for address in (0x396c, 0x3920, 0x45b6):
                        m.write(m.state+address+unit, [2 if not unit else 6])
                if moving:
                    m.write(m.state+0x32c6, [0, 0xcc, 88, 85])
                for weapon in range(orders):
                    m.write(m.state+0x3800+weapon, [12])
                m.write(m.ds+0x4fc0, (123456).to_bytes(3, 'little'))
                m.call(0x103b, 0x1774, 0, 1, limit=2000000)
                events.clear()
                m.call(0x12e8, 0xc, 0, limit=20000000)
                steps, shots, pauses, keys = (sum(e[0] == name for e in events)
                                              for name in ('step', 'shot', 'pace', 'key'))
                # Every speed pause must follow an attack, at the same
                # original call site. No movement step inserts such a wait.
                waiting = False
                for event in events:
                    if event[0] == 'shot':
                        assert not waiting
                        waiting = True
                    elif event[0] == 'pace':
                        assert waiting and event[1:] == (0x12e8, 0xd7b)
                        waiting = False
                assert not waiting and steps == 12 and shots == pauses == orders
                assert keys == (orders if speed == 5 else 0)
                speed_waits = [e[1] for e in events if e[0] == 'wait' and e[2] == 0xe31]
                pose_waits = [e[1] for e in events if e[0] == 'wait' and e[2] != 0xe31]
                assert speed_waits == ([12*speed]*orders if speed < 5 else [])
                assert graphics or not pose_waits
                values = (steps, shots, pauses, keys, sum(speed_waits), sum(pose_waits),
                          m.word(m.state+0x4004) & 127, m.word(m.state+0x4036) & 127)
                rows.append(' '.join(map(str, (graphics, speed, moving, orders))) + ' | ' +
                            ' '.join(map(str, values)))
                cases += 1
    m.cpu.hook_del(handle)
    (ROOT/'tests/fixtures/combat-pacing-primary.txt').write_text('\n'.join(rows)+'\n')
    (ROOT/'tests/fixtures/combat-pacing-primary.json').write_text(json.dumps(dict(
        executable_sha256=EXE_SHA, image_sha256=IMAGE_SHA, cases=cases,
        prerequisites='MAP1 snapshot; player loan 0 at 84,85; target loan 2 at 90,85; seed 123456; zero skills/heat; optional walk to 88,85; 0/1/2 player gun orders; no enemy orders.',
        routines='103B:1774 route/camera; 12E8:000C complete wave; 12E8:1002 movement; 12E8:12C7 attack presentation; 12E8:0D76 -> 0E31:1DCC post-attack speed pause.',
        boundaries=sorted(f'{s:04X}:{o:04X}' for s, o in skip),
        comparison='Ordered attack/pause calls and retrace/key counts inside 48 full waves. Movement adds no speed pause. Graphics-off skips pose waits. All six speed selections, idle/moving and zero/one/two attacks.',
        limits='Retrace requests, not physical XT wall-clock measurements. CPU drawing, sound duration, outtake playback and numeric combat rules are outside this fixture; covered separately where documented.',
        no_instruction_patches=True), indent=2)+'\n')
    print(f'Original combat pacing: {cases} complete waves')


if __name__ == '__main__':
    main()
