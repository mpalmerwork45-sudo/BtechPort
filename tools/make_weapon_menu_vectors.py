#!/usr/bin/env python3
"""Hash original held weapon pages after ordinary keyboard/menu inputs.

The private GAME4 prerequisite activates GAME3's parked vehicles, puts Rick on
foot, empties one weapon and destroys another critical slot. Original files and
executable instructions remain unchanged. Captures and RAM stay in work/.
"""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image
from prepare_talk import EXE_SHA, IMAGE_SHA

ROOT = Path(__file__).resolve().parents[1]
LABELS = ('weapons', 'assigned', 'override-yes', 'override-no', 'override-refused',
          'replacement-target', 'cleared', 'empty', 'empty-dismissed', 'destroyed',
          'destroyed-dismissed', 'kick', 'kick-human', 'foot-menu', 'foot-target',
          'foot-assigned', 'foot-override', 'foot-override-refused',
          'foot-replacement-target', 'foot-cleared')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--capture', type=Path, default=ROOT/'work/reference-runs/1791959365331060258')
    args = p.parse_args()
    rows, cases = [], []
    for index, label in enumerate(LABELS):
        frame = Image.open(args.capture/'captures'/f'{label}.png').convert('RGB')
        if frame.size != (320, 200):
            raise ValueError('Expected original 320x200 capture')
        regions = [(0, 0, 104, 200)]
        if index < 11 and index != 5:
            regions.append((104, 96, 216, 104))
        for x, y, w, h in regions:
            rgb = frame.crop((x, y, x+w, y+h)).tobytes()
            value = 0xcbf29ce484222325
            for byte in rgb:
                value = ((value ^ byte) * 0x100000001b3) & 0xffffffffffffffff
            rows.append(f'W {index} {x} {y} {w} {h} {value:016x}')
            cases.append(dict(case=index, label=label, bounds=[x, y, w, h],
                              rgb_sha256=hashlib.sha256(rgb).hexdigest()))
    (ROOT/'tests/fixtures/weapon-menu-primary.txt').write_text('\n'.join(rows)+'\n')
    metadata = dict(executable_sha256=EXE_SHA, image_sha256=IMAGE_SHA, cases=cases,
                    capture_run=args.capture.name, prerequisites=__doc__.strip(),
                    routines=['0D43:0004 weapons and infantry', '0D43:07CB target selection',
                              '0000:1A13 yes/no', '103B kick caller at image 0x125e1'],
                    limits='Unmasked complete text panels and weapon window; not battlefield equality.')
    (ROOT/'tests/fixtures/weapon-menu-primary.json').write_text(json.dumps(metadata, indent=2)+'\n')
    print(f'Original weapon menu: {len(LABELS)} held pages, {len(rows)} regions')


if __name__ == '__main__':
    main()
