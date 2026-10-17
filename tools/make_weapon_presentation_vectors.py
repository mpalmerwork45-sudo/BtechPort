#!/usr/bin/env python3
"""Observe original weapon poses, trajectories, sound order and retrace holds.

Runs the original 12E8:12C7 presentation routine with explicit prerequisites.
Pixel blits, map drawing, sound playback, flips and waits are host boundaries;
the original animation interpreters and trajectory instructions run unchanged.
"""
import argparse
import json
import struct
from combat_oracle import OriginalCombat, ROOT, UC_HOOK_CODE
from make_combat_live_turns import SNAPSHOT
from prepare_talk import EXE_SHA, IMAGE_SHA
from unicorn.x86_const import UC_X86_REG_AX, UC_X86_REG_BP, UC_X86_REG_CS, UC_X86_REG_IP, UC_X86_REG_SP, UC_X86_REG_SS


def fingerprint(values):
    result = 14695981039346656037
    for value in values:
        for byte in struct.pack('<H', value & 65535):
            result = ((result ^ byte) * 1099511628211) & ((1 << 64)-1)
    return f'{result:016x}'


class PresentationOracle:
    def __init__(self):
        self.m = OriginalCombat(snapshot=SNAPSHOT)
        self.events = []
        self.skip = {(0, 0x2a93), (0x187f, 0x28eb), (0x187f, 0x377),
                     (0xe31, 0x1f09), (0xe31, 0x1f73), (0x173d, 0x31c),
                     (0x173d, 0x6c3), (0x173d, 6), (0, 0x19bf), (0, 0x48b7)}
        self.watch = {(self.m.load+s)*16+o: (s, o) for s, o in
                      self.skip | {(0, 0x17b6)}}
        self.m.cpu.hook_add(UC_HOOK_CODE, self.hook)

    def hook(self, cpu, at, size, data):
        if at not in self.watch:
            return
        m = self.m
        where = self.watch[at]
        ss = 16*cpu.reg_read(UC_X86_REG_SS)
        sp = cpu.reg_read(UC_X86_REG_SP)
        stack = ss+sp
        caller = (m.word(stack+2)-m.load, m.word(stack))
        if where == (0, 0x17b6):
            bp = ss+cpu.reg_read(UC_X86_REG_BP)
            self.events.append(('pose', m.word(bp+6), cpu.reg_read(UC_X86_REG_AX)))
            return
        if where == (0xe31, 0x1f73):
            args = tuple(m.word(stack+4+2*i) for i in range(3))
            self.events.append(('missile' if caller[1] == 0x1960 else 'impact', *args))
        elif where == (0x173d, 0x31c):
            self.events.append(('beam', *(m.word(stack+4+2*i) for i in range(5))))
        elif where == (0x173d, 6):
            self.events.append(('wait', m.word(stack+4)))
        elif where == (0, 0x19bf):
            self.events.append(('sound', m.word(stack+4)))
        elif where == (0, 0x48b7):
            self.events.append(('outtake', m.word(stack+4)))
        off, seg = m.word(stack), m.word(stack+2)
        cpu.reg_write(UC_X86_REG_SP, sp+4)
        cpu.reg_write(UC_X86_REG_CS, seg)
        cpu.reg_write(UC_X86_REG_IP, off)

    def observe(self, weapon, direction, family, target_human, hit, graphics=1, layout=0):
        m = self.m
        m.reset()
        actor = 4 if family == 2 else 0
        target = 16 if target_human else 12
        dx, dy = ((0, -1), (1, -1), (1, 0), (1, 1),
                  (0, 1), (-1, 1), (-1, 0), (-1, -1))[direction]
        ax, ay = (64, 64) if layout < 2 else (42, 64)
        distance = 6 if layout == 0 else 1 if layout == 1 else 24
        tx, ty = ax+dx*distance, ay+dy*distance
        # A separate idle camera unit allows actor/target visibility cases.
        m.write(m.state+0x4004, bytes([255])*100)
        m.write(m.state+0xd55e, bytes(24))
        m.write(m.state+0x409a, bytes(24))
        camera = 7
        m.write(m.state+0xc620, [camera])
        for unit, x, y in ((camera, 64, 64), (actor, ax, ay), (target, tx, ty)):
            m.word(m.state+0x4004+2*unit, 0xc00+x)
            m.word(m.state+0x4036+2*unit, 0xc000+y)
        m.write(m.state+0xd55e+actor, [family == 1])
        m.word(m.ds+0x2e3a, graphics)
        m.word(m.ds+0x14a, 1)
        m.word(m.ds+0x4fba, 3)  # Existing VGA rendering/palette contract.
        m.call(0, 0x17bb, 0xc40, 0xc040)
        m.call(0x187f, 0x1314, 0xc40, 0xc040)
        m.call(0x187f, 0x1df8)
        m.call(0, 0xe4b, limit=1000000)
        self.events.clear()
        # reaction, human-death and mech-death are separate original caller
        # arguments. This corpus exercises surviving hit/miss presentation.
        m.call(0x12e8, 0x12c7, actor, target, weapon, direction,
               target_human and hit, 0, 0, 0, hit, 0, 0, limit=4000000)
        return (ax, ay, tx, ty), list(self.events)


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    oracle = PresentationOracle()
    rows = ['# weapon direction family target_human hit graphics layout ax ay tx ty | pose_count pose_hash wait_count retraces sounds... | trail_kind trail_count trail_hash | impact_count impact_hash | event_order_hash',
            '# Family 0/1: two mech sprite families; family 2: infantry. VGA camera 64,64. Final hash: observable phase/sound order.']
    cases = 0
    for family in range(3):
        weapons = range(14) if family == 2 else range(15, 33)
        for weapon in weapons:
            for direction in range(8):
                for target_human, hit, graphics, layout in ((0, 0, 1, 0), (0, 1, 1, 0),
                        (1, 1, 1, 0), (0, 1, 0, 0), (0, 1, 1, 1), (0, 1, 1, 2)):
                    coordinates, events = oracle.observe(weapon, direction, family, target_human, hit, graphics, layout)
                    actor = 4 if family == 2 else 0
                    poses = [e[2] for e in events if e[0] == 'pose' and e[1] == actor]
                    waits = [e[1] for e in events if e[0] == 'wait']
                    sounds = [e[1] for e in events if e[0] == 'sound']
                    trail = [e for e in events if e[0] in ('missile', 'beam')]
                    impacts = [e[1:] for e in events if e[0] == 'impact']
                    trail_kind = 1 if trail and trail[0][0] == 'missile' else 2 if trail else 0
                    points = [(e[2], e[3], e[1]) if e[0] == 'missile' else
                              (e[1], e[2], e[5]) for e in trail]
                    order = [1 if e[0] == 'pose' else 2 if e[0] == 'wait' else
                             3 if e[0] == 'sound' else 4 if e[0] == 'missile' else
                             5 if e[0] == 'beam' else 6 if e[0] == 'impact' else 7 for e in events]
                    phases = []
                    for event in events:
                        phase = (1 if event[0] == 'pose' and event[1] == actor else
                                 100+event[1] if event[0] == 'sound' else
                                 2 if event[0] == 'missile' else 3 if event[0] == 'beam' else
                                 4 if event[0] == 'impact' else 0)
                        if phase and (not phases or phases[-1] != phase):
                            phases.append(phase)
                    rows.append(' '.join(map(str, (weapon, direction, family, target_human, hit, graphics, layout, *coordinates))) +
                        f' | {len(poses)} {fingerprint(poses)} {len(waits)} {sum(waits)} {len(sounds)} ' + ' '.join(map(str, sounds)) +
                        f' | {trail_kind} {len(points)} {fingerprint(v for p in points for v in p)}' +
                        f' | {len(impacts)} {fingerprint(v for p in impacts for v in p)} | {fingerprint(order)} {fingerprint(phases)}')
                    cases += 1
    (ROOT/'tests/fixtures/weapon-presentation-primary.txt').write_text('\n'.join(rows)+'\n')
    (ROOT/'tests/fixtures/weapon-presentation-primary.json').write_text(json.dumps(dict(
        executable_sha256=EXE_SHA, image_sha256=IMAGE_SHA, cases=cases,
        routine='12E8:12C7 complete surviving attack presentation; 0000:1732 original animation interpreter',
        prerequisites='Camera 64,64; two mech families and infantry; their applicable weapons; eight directions; hit/miss, infantry targets, graphics off, close and partially offscreen shots; VGA palette.',
        boundaries=sorted(f'{s:04X}:{o:04X}' for s, o in oracle.skip),
        comparison='Ordered pose/wait/sound/draw observations; all visible missile/beam coordinates and frame/color IDs; exact impact anchors and frame order.',
        limits='Requested retraces and event order, not physical XT decode/blit cost or speaker calibration. Casualties and outtake playback have their separate existing comparisons.',
        no_instruction_patches=True), indent=2)+'\n')
    print(f'Original weapon presentation: {cases} complete sequences')


if __name__ == '__main__':
    main()
