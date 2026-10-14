#!/usr/bin/env python3
"""Execute the original whole-party wall test at played town positions."""
import json
from combat_oracle import OriginalCombat, ROOT
from prepare_talk import EXE_SHA, IMAGE_SHA


def main():
    source=json.loads((ROOT/'tests/fixtures/town-formation-primary.json').read_text())
    rows=[]
    # Active-slot flags are caller prerequisites, independent of which named
    # character pilots a mech. Keep each configuration within eight people.
    groups=((1,0),(4,0),(8,0),(0,1),(1,3),(4,4))
    for case in source['cases']:
        prefix=ROOT/'work/reference-runs'/case['run']/case['label']
        m=OriginalCombat(snapshot=prefix)
        px,py=m.word(m.buffer+0xa44b),m.word(m.buffer+0xa44d)
        x,y=(px>>8)*128+(px&127),(py>>12)*128+(py&127)
        for people,mechs in groups:
            for i in range(12):m.word(m.state+0x406a+2*i,int(i<mechs if i<4 else i<4+people))
            for dy in (-1,0,1):
                for dx in (-1,0,1):
                    if not dx and not dy:continue
                    # D55C is the original caller's already-handled-dialogue
                    # latch. Skip entry questions; retain all wall checks.
                    m.word(m.state+0xd55c,1)
                    blocked=m.call(0,0x1c12,dx,dy)
                    if blocked not in (0,1):raise ValueError(blocked)
                    rows.append(f'F {case["town"]} {x} {y} {people} {mechs} {dx} {dy} {blocked}')
    (ROOT/'tests/fixtures/formation-collision-primary.txt').write_text('\n'.join(rows)+'\n')
    (ROOT/'tests/fixtures/formation-collision-primary.json').write_text(json.dumps(dict(
        executable_sha256=EXE_SHA,image_sha256=IMAGE_SHA,routine='0000:1C12',cases=len(rows),
        snapshots='town-formation-primary.json: 40 played Starport/MAP4 frames',
        prerequisites='Six active compact formations, eight directions at every recorded cursor. D55C=1 suppresses doorway questions only. Original viewport, gate 85, offset tables and instructions are unchanged.',
        comparison='Exact rejection of the entire cursor step, including both mech ground tiles and all eight foot positions.',
        limits='Doorway prompts, deep-water messages and damaged-save recovery are separate.',
        intercepted_boundaries=[],no_instruction_patches=True),indent=2)+'\n')
    print('Original whole-formation collision cases:',len(rows))


if __name__=='__main__':main()
