#!/usr/bin/env python3
"""Original town painting, neighbour joining and complete surrounding tiles.

Only numeric hashes enter Git. The owner's MTP chunks and unmodified original
programs execute in private RAM; no reference file or instruction is changed.
"""
import json
import struct
from combat_oracle import OriginalCombat, ROOT
from make_combat_vectors import fingerprint
from prepare_talk import EXE_SHA, IMAGE_SHA
from unicorn.x86_const import (UC_X86_REG_CS, UC_X86_REG_DS, UC_X86_REG_SS,
                              UC_X86_REG_SP, UC_X86_REG_BP, UC_X86_REG_IP)


def span(m, segment, start, end, ds, locals=None):
    segment += m.load
    bp = 0x7f000
    m.write(bp-256, bytes(320))
    for off, value in (locals or {}).items():
        m.word(bp+off, value)
    for reg, value in ((UC_X86_REG_CS, segment), (UC_X86_REG_IP, start),
                       (UC_X86_REG_DS, ds), (UC_X86_REG_SS, 0x7000),
                       (UC_X86_REG_SP, 0xee00), (UC_X86_REG_BP, 0xf000)):
        m.cpu.reg_write(reg, value)
    # 104E already called the near joining routine. Drop its translated
    # block so Unicorn honours this span's new stop-before-RET boundary.
    m.cpu.ctl_remove_cache(segment*16, segment*16+0x10000)
    m.cpu.emu_start(segment*16+start, segment*16+end, count=20000)
    if m.cpu.reg_read(UC_X86_REG_IP) != end:
        raise RuntimeError('Town/descriptor instruction bound exceeded')


def main():
    m = OriginalCombat()
    rows = []
    for seed in (1, 123456, 0x020304):
        m.reset()
        m.write(m.ds+0x4fc0, seed.to_bytes(3, 'little'))
        noise = bytes(m.call(0x187f, 0xbc0) & 255 for _ in range(256))
        for town in range(1, 14):
            raw = (ROOT/f'Original DOS/MAP{town}.MTP').read_bytes()
            width, height = raw[3:5]
            rx = struct.unpack_from('<H', raw, 389)[0] >> 8
            ry = struct.unpack_from('<H', raw, 421)[0] >> 12
            m.write(m.buffer+0x9fb, noise)
            m.call(0x187f, 0x104e, 16*ry+rx)
            m.write(m.buffer+0x101d, raw[541:])
            # Execute the city loader's original descriptor-writing span,
            # after its file read supplied MTP dimensions/zero block origin.
            span(m, 0, 0x3050, 0x30bb, m.ds//16,
                 {6: 4, -12: 0, -8: 0, -2: width//8, -10: height//8})
            span(m, 0x187f, 0x1886, 0x18d7, m.buffer//16)
            tiles = bytearray((width+16)*(height+16))
            descriptors = bytearray()
            for by in range(-1, height//8+1):
                for bx in range(-1, width//8+1):
                    # The viewport reaches a neighbouring sector through its
                    # outer piece, not an invalid packed coordinate FF. Keep
                    # the centre in this sector and select the requested piece.
                    cx, cy = min(7, max(0, bx)), min(7, max(0, by))
                    m.call(0x187f, 0x1314, (rx << 8) | (16*cx+8),
                           (ry << 12) | (16*cy+8))
                    grid = m.read(m.buffer+0x7ad, 576)
                    descriptors.append(m.read(m.buffer+0x7a4+(by-cy+1)*3+bx-cx+1, 1)[0])
                    gx, gy = 8+(bx-cx)*8, 8+(by-cy)*8
                    for y in range(8):
                        at = ((by+1)*8+y)*(width+16)+(bx+1)*8
                        tiles[at:at+8] = grid[(gy+y)*24+gx:(gy+y)*24+gx+8]
            rows.append(f'T {seed} {town} {fingerprint(tiles):016x} {fingerprint(descriptors):016x}')
    (ROOT/'tests/fixtures/city-edges-primary.txt').write_text('\n'.join(rows)+'\n')
    (ROOT/'tests/fixtures/city-edges-primary.json').write_text(json.dumps(dict(
        executable_sha256=EXE_SHA, image_sha256=IMAGE_SHA, cases=len(rows),
        routines=['187F:104E generated sector/neighbours', '0000:3050..30BB town descriptors',
                  '187F:1886..18D7 joining masks', '187F:1314 complete viewport pieces'],
        prerequisites='Three generation seeds; all thirteen MAP1..MAP13 MTP sizes and unmodified chunks. City-loader file-read boundary supplied before its descriptor-writing span.',
        comparison='All town tiles plus an eight-tile landscape margin on all four sides; complete block descriptor hashes, including destroyed MAP11.',
        intercepted_boundaries=[], no_instruction_patches=True), indent=2)+'\n')
    print('Original complete city/margin grids:', len(rows))


if __name__ == '__main__':
    main()
