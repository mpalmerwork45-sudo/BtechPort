#!/usr/bin/env python3
"""Hash held original arena results from played win/loss captures.

The private GAME4 is a native export of the ordinary GAME3-to-arena approach.
Both original fights use a rented Locust: computer orders win the first, and
leaving weapons unassigned loses the second. No damage or result is injected.
"""
import hashlib
import json
from pathlib import Path
from PIL import Image
from prepare_talk import EXE_SHA, IMAGE_SHA

ROOT=Path(__file__).resolve().parents[1]


def main():
    cases=[];rows=[]
    for win,run,label in ((1,'1791962267261198406','arena-end-37'),
                          (0,'1791962676085215019','loss-finish-5')):
        frame=Image.open(ROOT/'work/reference-runs'/run/'captures'/f'{label}.png').convert('RGB')
        if frame.size!=(320,200):raise ValueError('Expected original 320x200 screenshot')
        rgb=frame.crop((104,72,320,128)).tobytes();value=0xcbf29ce484222325
        for byte in rgb:value=((value^byte)*0x100000001b3)&0xffffffffffffffff
        rows.append(f'A {win} {value:016x}')
        cases.append(dict(win=win,run=run,label=label,bounds=[104,72,216,56],
                          rgb_sha256=hashlib.sha256(rgb).hexdigest()))
    (ROOT/'tests/fixtures/arena-ui-primary.txt').write_text('\n'.join(rows)+'\n')
    (ROOT/'tests/fixtures/arena-ui-primary.json').write_text(json.dumps(dict(
        executable_sha256=EXE_SHA,image_sha256=IMAGE_SHA,cases=cases,
        prerequisite=__doc__.strip(),routine='103B:13AD..13E0 with 14D3:17C6/17EA',
        comparison='Complete unmasked 216x56 result popups. Both original returns place the party '
            'at (1337,1117); rental win awards 500 C-bills and rental loss awards none.',
        limits='Does not establish complete battlefield or wall-clock parity.'),indent=2)+'\n')
    print('Original arena result panels:',len(cases))


if __name__=='__main__':main()
