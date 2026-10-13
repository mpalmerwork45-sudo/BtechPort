#!/usr/bin/env python3
"""Record numeric regions from ordinary original target/withdrawal menu inputs.

The private GAME4 prerequisite activates GAME3's parked vehicles, puts character
four on foot, and enables its encounter gate. No executable or assets change.
Raw screenshots/RAM remain in ignored work/; only hashes and crop bounds commit.
"""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image
from prepare_talk import EXE_SHA, IMAGE_SHA

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / 'work/reference-runs/1791924339149371505'
CASES = (
    ('weapons', (72, 96, 248, 104)),
    ('target', (0, 0, 104, 200)),
    ('target-next', (0, 0, 104, 200)),
    ('weapons-assigned', (72, 96, 248, 104)),
    ('withdrawal', (0, 0, 104, 200)),
    ('withdrawal-return', (104, 72, 216, 56)),
    ('withdrawal-return', (0, 0, 104, 200)),
    ('weapons', (0, 0, 104, 96)),
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', type=Path, default=DEFAULT)
    args = parser.parse_args()
    rows, sources = [], []
    for index, (label, bounds) in enumerate(CASES):
        frame = Image.open(args.capture / 'captures' / f'{label}.png').convert('RGB')
        if frame.size != (320, 200):
            raise ValueError('Expected original 320x200 capture')
        x, y, width, height = bounds
        pixels = frame.crop((x, y, x+width, y+height)).tobytes()
        value = 0xcbf29ce484222325
        for byte in pixels:
            value = ((value ^ byte) * 0x100000001b3) & 0xffffffffffffffff
        rows.append(f'T {index} {x} {y} {width} {height} {value:016x}')
        sources.append(dict(case=index, label=label, bounds=bounds,
                            rgb_sha256=hashlib.sha256(pixels).hexdigest()))
    (ROOT / 'tests/fixtures/target-ui-primary.txt').write_text('\n'.join(rows)+'\n')
    metadata = dict(executable_sha256=EXE_SHA, image_sha256=IMAGE_SHA,
                    cases=sources, capture_run=args.capture.name,
                    prerequisites=__doc__.strip(),
                    routines=['0D43:0004 weapon list', '0D43:07CB target selection',
                              '103B:069F withdrawal and 103B result caller'],
                    limits='Complete unmasked UI regions; not battlefield equality. '
                    'Assigned-row comparison sets the original selected row explicitly; '
                    'native automatic advancement and override dialogs are outside this renderer comparison.')
    (ROOT / 'tests/fixtures/target-ui-primary.json').write_text(json.dumps(metadata, indent=2)+'\n')
    print('Original weapon/target/withdrawal regions:', len(rows))


if __name__ == '__main__':
    main()
