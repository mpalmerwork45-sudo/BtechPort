#!/usr/bin/env python3
"""Execute original world-positioned debris writes, including ring wrap."""
import json
from combat_oracle import OriginalCombat, ROOT
from make_party_vectors import SNAP
from prepare_talk import EXE_SHA, IMAGE_SHA


def main():
    original = OriginalCombat(snapshot=SNAP)
    rows = []
    for index in (0, 17, 63):
        for sprite in range(124, 130):
            for x, y in ((0, 0), (127, 128), (128, 127), (1323, 1111),
                         (1536, 1535), (2047, 2047), (-1, 2048)):
                original.reset()
                original.word(original.state + 0xd557, index)
                wx, wy = x & 2047, y & 2047
                original.call(0x103b, 0x27c9, sprite,
                              (wx // 128) * 256 + (wx & 127),
                              (wy // 128) * 4096 + (wy & 127))
                result = [original.read(original.state + p + index, 1)[0]
                          for p in (0xd457, 0xd497, 0xd4d7, 0xd517)]
                result.append(original.read(original.state + 0xd557, 1)[0])
                rows.append('M ' + ' '.join(map(str, [index, sprite, x, y] + result)))
    (ROOT / 'tests/fixtures/world-marks-primary.txt').write_text('\n'.join(rows) + '\n')
    (ROOT / 'tests/fixtures/world-marks-primary.json').write_text(json.dumps(dict(
        executable_sha256=EXE_SHA, image_sha256=IMAGE_SHA, cases=len(rows),
        routine='103B:27C9', intercepted_boundaries=[],
        prerequisites='Explicit sprite, packed world position and ring index; negative/overflow coordinates wrap to the original 2048-half-tile world',
        comparison='sprite, Y/X sector byte, two local coordinates and next ring index'), indent=2) + '\n')
    print(f'Wrote {len(rows)} original world-mark cases')


if __name__ == '__main__':
    main()
