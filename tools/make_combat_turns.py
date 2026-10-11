#!/usr/bin/env python3
"""Replay explicit orders through original full turn instructions, no UI patches."""
import argparse
from combat_oracle import OriginalCombat, ROOT
from make_combat_vectors import fingerprint

def generate(snapshot):
    o=OriginalCombat(snapshot=snapshot);o.word(o.ds+0x2e3a,0)
    rows=['# Controlled original combat-menu context: Locusts at 64,77 / 114,89; RNG 70,54,210.',
          '# Player rank 0, original records; target actuators/ammo/movement disabled.']
    actions=[('W',72,77)]+[('T',)]*4+[('W',84,85)]+[('T',)]*5+[('F',2)]+[('T',)]*2+[
        ('W',96,93)]+[('T',)]*9+[('W',96,85)]+[('T',)]*40
    for action in actions:
        if action[0]=='W':
            x,y=action[1:];o.write(o.state+0x32c6,bytes([0,0xcc,x,y])+bytes([255])*44)
            rows.append(f'W {x} {y}')
        elif action[0]=='F':
            o.write(o.state+0x3800+action[1],[12]);rows.append(f'F {action[1]}')
        else:
            o.call(0x103b,0x1774,0,1,limit=2000000)
            o.call(0xe31,0x3ab,12,0,limit=2000000)
            try: o.call(0x12e8,0xc,1,limit=20000000)
            except RuntimeError:
                print('After turns:',sum(r.startswith('T ') for r in rows));raise
            units=[]
            for u,record,heat in ((0,0xc724,0x6e),(12,0xc918,0x72)):
                face=o.read(o.state+0x396c+u,1)[0]
                if face==255:face=o.read(o.state+0x45b6+u,1)[0]
                units.extend((o.word(o.state+0x4004+u*2)&127,o.word(o.state+0x4036+u*2)&127,
                              face,o.read(o.state+heat,1)[0],f'{fingerprint(o.read(o.state+record,125)):016x}'))
            rows.append('T '+' '.join(map(str,units))+f" {int.from_bytes(o.read(o.ds+0x4fc0,3),'little')}")
            if o.read(o.state+0xc918,1)==b'\xff':break
    (ROOT/'tests/fixtures/combat-turns.txt').write_text('\n'.join(rows)+'\n')
    print(f'Wrote {sum(r.startswith("T ") for r in rows)} original full turns')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('snapshot');generate(p.parse_args().snapshot)
