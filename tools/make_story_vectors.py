#!/usr/bin/env python3
"""Original later-story numeric effects, with explicit original caller state."""
import json
from combat_oracle import OriginalCombat,ROOT
from make_party_vectors import SNAP
from prepare_talk import EXE_SHA,IMAGE_SHA

def main():
    m=OriginalCombat(snapshot=SNAP);rows=['# Executed 14D3:0004 hospital training/kit effects.']
    for action in (21,22,23,25,26):
        for credits in (0,499,500,1000):
            for trained in (0,2):
                m.reset();p=bytearray((0,8,9,7,0,0,0,0,1,0,1,0,8,0,0,75,trained))
                people=p+bytearray([255]+[0]*16)*7;m.write(m.state+0xc614,people)
                m.write(m.state+0xd31a,b'\0\0')
                m.write(m.state+0xd325,b'\0');m.write(m.state+0xd450,b'\0\0')
                m.write(m.state+0xd370,credits.to_bytes(4,'little'))
                m.call(0x14d3,4,action,limit=10000)
                q=m.read(m.state+0xc614,17);cash=int.from_bytes(m.read(m.state+0xd370,4),'little')
                flags=m.read(m.state+0xd31a,2);injured=m.read(m.state+0xd325,1)[0];kits=m.read(m.state+0xd450,2)
                rows.append(f'H {action} {credits} {trained} {cash} {q[10]} {q[16]} {flags[0]} {flags[1]} {injured} {kits[0]} {kits[1]}')
    (ROOT/'tests/fixtures/story-primary.txt').write_text('\n'.join(rows)+'\n')
    (ROOT/'tests/fixtures/story-primary.json').write_text(json.dumps(dict(
        executable_sha256=EXE_SHA,image_sha256=IMAGE_SHA,routine='14D3:0004',cases=len(rows)-1,
        prerequisites='Jason selected, one injured party member, cash boundary cases and medical-training bit variants',
        comparison='Character medicine/training bytes, cash, result flags and kit bytes'),indent=2)+'\n')
    print('Primary hospital cases:',len(rows)-1)
if __name__=='__main__':main()
