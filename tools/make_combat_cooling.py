#!/usr/bin/env python3
"""Verify heat cleanup against original 0E31:0C63, with explicit unit inputs."""
import random
from combat_oracle import OriginalCombat, ROOT

def generate():
    o=OriginalCombat();rng=random.Random(0xc63);rows=[]
    for loan in range(3):
        for mode in (-1,0,1,2):
            for heat in (0,1,5,13,29,30):
                for burning in (0,1,3):
                    for cover,terrain in ((0,65),(8,15),(16,32)):
                        steps=rng.randrange(13);pool=rng.randrange(36);engine=rng.randrange(4)
                        cooling=rng.randrange(16);sinks=rng.randrange(7)
                        o.reset();record=bytearray(o.template(loan))
                        record[38]=cooling;record[117]=engine
                        for j in range(51,86):
                            if record[j]==34:record[j]=0
                        record[51:51+sinks]=bytes([34])*sinks
                        o.write(o.state+0xc724,record)
                        for j in range(1,8):o.write(o.state+0xc724+125*j,[255])
                        o.write(o.state+0x3800,bytes([255])*288)
                        for offset,value in ((0x32c6,mode&255),(0x6e,heat),(0x92,pool),
                                (0xd576,burning),(0x32ae,cover),(0x3750,terrain)):
                            o.write(o.state+offset,[value])
                        o.write(0x70500,bytes([steps])+bytes(23))
                        o.call(0xe31,0xc63,0x500,0x7000)
                        after=[o.read(o.state+offset,1)[0] for offset in (0x6e,0x92,0xd576)]
                        values=[loan,mode,heat,steps,pool,engine,cooling,sinks,burning,cover,terrain,*after]
                        rows.append('H '+' '.join(map(str,values)))
    return rows

if __name__=='__main__':
    rows=generate()
    (ROOT/'tests/fixtures/combat-cooling.txt').write_text(
        '# Original 0E31:0C63 heat, pool and burning cleanup; controlled inputs.\n'+'\n'.join(rows)+'\n')
    print(f'Wrote {len(rows)} original heat-cleanup cases')
