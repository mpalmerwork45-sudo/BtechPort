#!/usr/bin/env python3
"""Run the original arena retirement and termination checks on explicit states.

Only the declared numeric spans execute. Stop before display/ejection and before
the next scene; no executable byte is patched and no played fight is claimed.
"""
import json
from combat_oracle import OriginalCombat, ROOT, UC_HOOK_CODE
from make_party_vectors import SNAP
from prepare_talk import EXE_SHA, IMAGE_SHA
from unicorn.x86_const import UC_X86_REG_CS, UC_X86_REG_IP


def main():
    m = OriginalCombat(snapshot=SNAP)
    stop = 0
    def boundary(cpu, address, size, data):
        if address == m.load * 16 + stop:
            cpu.reg_write(UC_X86_REG_CS, 0x6000);cpu.reg_write(UC_X86_REG_IP, 0)
    m.cpu.hook_add(UC_HOOK_CODE, boundary)
    rows = []
    for rental in (0, 1):
        for alarm in (0, 1):
            for target in (0, 12, 13):
                m.reset();m.word(m.state + 0xe48e, rental and not alarm)
                m.write(m.state + 0xd32f, [alarm])
                for i, address in zip((0, 12, 13), (0xc724, 0xc918, 0xc995)):
                    m.write(m.state + address, m.template())
                    m.word(m.state + 0x406a + 2 * i, 1)
                stop = 0xdf4a
                m.call(0xd43, 0xa35, target)
                values = [m.read(m.state + p, 1)[0] for p in (0xc724, 0xc918, 0xc995)]
                rows.append('D ' + ' '.join(map(str, [rental, alarm, target] + values)))
    for alarm in (0, 1):
        for mech in (0, 1):
            for opponent in (0, 1):
                for spectator in (0, 1):
                    m.reset();m.write(m.state + 0x406a, bytes(48))
                    for unit, active in ((0, mech), (12, opponent), (13, spectator)):
                        m.word(m.state + 0x406a + 2 * unit, active)
                        m.word(m.state + 0x4004 + 2 * unit, 0xa2b)
                        m.word(m.state + 0x4036 + 2 * unit, 0x8057)
                    m.word(m.ds + 0x14a, 1);m.word(m.state + 0x374c, 0)
                    m.write(m.state + 0xd32f, [alarm])
                    # A bounded interior span with its original caller frame.
                    m.write(0x7fe80, bytes(160));m.word(0x7ff06, 2)
                    stop = 0x11302;m.call(0x103b, 0xd0e)
                    rows.append(f'E {alarm} {mech} {opponent} {spectator} {m.word(0x7feee)}')
    (ROOT / 'tests/fixtures/arena-finish-primary.txt').write_text('\n'.join(rows) + '\n')
    (ROOT / 'tests/fixtures/arena-finish-primary.json').write_text(json.dumps(dict(
        executable_sha256=EXE_SHA, image_sha256=IMAGE_SHA, cases=len(rows),
        spans=['0D43:0A35..0B1A', '103B:0D0E..0F52'],
        prerequisites='Rental/alarm state, defeated unit, three standing/dead actor combinations; arena argument 2 and living Jason',
        boundaries='Stop at image DF4A before display/ejection and 11302 before scene processing',
        comparison='Silent spectator removal; normal arena ends on mech loss, theft escape keeps fighting'), indent=2) + '\n')
    print('Wrote', len(rows), 'primary arena termination cases')


if __name__ == '__main__':main()
