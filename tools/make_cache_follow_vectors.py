#!/usr/bin/env python3
"""Execute continuous original MAP14/MAP15 walks for whole foot parties.

Select only paths which do not open a cache interaction. Wall/contact rules
have a separate corpus. The original movement and formation redraw routines
execute every half-step; caller step settings and party records are explicit.
"""
import json,struct
from combat_oracle import OriginalCombat,ROOT
from make_cache_movement_vectors import SNAP
from prepare_talk import EXE_SHA,IMAGE_SHA


def main():
    m=OriginalCombat(snapshot=SNAP);rows=[];moves=0
    dirs=((0,-1),(1,-1),(1,0),(1,1),(0,1),(-1,1),(-1,0),(-1,-1))
    for room in (0,1):
        raw=(ROOT/f'Original DOS/MAP{14+room}.MTP').read_bytes();raw=raw if room else raw[541:]
        width,height,gate=(32,24,139) if room else (64,64,33)
        def tile(x,y):
            tx=(x+1)//2;ty=y//2
            if tx<0 or tx>=width or ty<0 or ty>=height:return 255
            return raw[(ty//8*(width//8)+tx//8)*64+ty%8*8+tx%8]
        for count in (1,5,8):
            m.reset();m.write(m.buffer+0x101d,raw);m.write(m.state+0xd346,[1]);m.write(m.state+0xd34e,[room]);m.word(m.ds+0x150,gate)
            if room:
                for by in range(3):m.write(m.buffer+0x664+8*by,bytes(range(0x90+4*by,0x94+4*by)))
            m.call(0x187f,0x1da8)
            for i in range(4):m.write(m.state+0xc724+125*i,[255])
            for i in range(8):m.write(m.state+0xc614+17*i,bytes([i if i<count else 255,8,9,7,0,0,0,0,1,0,0,0,8,0,0,80,0]))
            fx=struct.unpack('<8h',m.read(m.ds+0x464,16));fy=struct.unpack('<8h',m.read(m.ds+0x47c,16))
            def legal(x,y):return all(tile(x+fx[i],y+fy[i])<gate for i in range(count))
            x,y=(4,34) if room else (6,122)
            if not legal(x,y):raise RuntimeError('Declared entry formation overlaps a wall')
            m.call(0,0x17bb,0xc00+x,0xc000+y);m.call(0x187f,0x1314,0xc00+x,0xc000+y);m.call(0x187f,0x1df8);m.call(0,0x51b)
            rows.append(f'C {room} {count} {x} {y}')
            rng=42
            for move in range(128):
                steps=(1,2,4)[move%3];effective=1 if room else steps
                choices=[d for d,(dx,dy) in enumerate(dirs) if all(legal(x+dx*j,y+dy*j) for j in range(1,effective+1))]
                if not choices:steps=effective=1;choices=[d for d,(dx,dy) in enumerate(dirs) if legal(x+dx,y+dy)]
                if not choices:raise RuntimeError('Declared route reached a closed pocket')
                rng=(rng*1664525+1013904223)&0xffffffff;direction=choices[(rng>>16)%len(choices)]
                key=m.word(m.ds+0x160+2*direction)
                for _ in range(effective):
                    m.word(m.state+0xd55c,1);m.call(0,0x218f,key);m.call(0,0x51b)
                x=m.word(m.buffer+0xa44b)&127;y=m.word(m.buffer+0xa44d)&127
                positions=[v for i in range(count) for v in (m.word(m.state+0x400c+2*i)&127,m.word(m.state+0x403e+2*i)&127)]
                rows.append(' '.join(map(str,('W',steps,direction,x,y,*positions))));moves+=1
    (ROOT/'tests/fixtures/cache-follow-primary.txt').write_text('\n'.join(rows)+'\n')
    (ROOT/'tests/fixtures/cache-follow-primary.json').write_text(json.dumps(dict(
        executable_sha256=EXE_SHA,image_sha256=IMAGE_SHA,inputs=moves,contexts=6,
        routines=['0000:218F movement','0000:051B complete formation','187F:1314/1DF8 viewport'],
        prerequisites='Cache-entry RAM, original MAP14/MAP15 payloads, 1/5/8 people on foot, no active mechs, 1/2/4 step settings (MAP15 uses one). Continuous legal routes; interactions excluded. D55C suppresses entry questions.',
        comparison='Cursor and every compact member position after each input; no state reset between steps, no instruction edits. Does not establish recovery paths from malformed legacy formations.'),indent=2)+'\n')
    print('Original continuous cache inputs:',moves)


if __name__=='__main__':main()
