#!/usr/bin/env python3
"""Executed primary field healing, crew assignment and formation numeric spans."""
from combat_oracle import OriginalCombat,ROOT
from make_aftermath_vectors import span
from make_party_vectors import SNAP,fingerprint

def main():
    m=OriginalCombat(snapshot=SNAP);rows=['# Explicit medical/crew/formation caller prerequisites; primary instructions unmodified.']
    for skill in range(6):
        for equipment in range(1,5):
            for seed in (1,42,0xffffff):
                m.reset();m.write(m.ds+0x4fc0,seed.to_bytes(3,'little'))
                for p in range(8):m.write(m.state+0xc614+17*p,bytes([p,8,9,7])+bytes(8)+bytes([8,0,0,30+p,0]))
                for p in range(8):
                    code=m.read(m.ds+0x2601+4*skill+equipment,1)[0]
                    count=code&15;mult=code>>4 if code&240 else 1
                    span(m,0xc31,0x1bc,0x207,{-22:p,-26:80,-10:count,-18:mult,-2:0})
                rows.append(f'H {skill} {equipment} {seed} {int.from_bytes(m.read(m.ds+0x4fc0,3),"little")} '+ ' '.join(str(m.read(m.state+0xc623+17*p,1)[0]) for p in range(8)))
    for person in range(8):
        for seat in (121,122):
            for occupied in (0,1):
                m.reset()
                for p in range(8):m.write(m.state+0xc614+17*p,bytes([p])+bytes(11)+bytes([8])+bytes(4))
                for slot in range(4):
                    b=bytearray(m.template());b[121]=1 if occupied else 255;b[122]=2 if occupied else 255;m.write(m.state+0xc724+125*slot,b)
                locals={-26:0,-28:seat,-24:person,-8:2}
                # Remove this member from previous records before replacing a seat.
                span(m,0xc67,0x67f,0x6da,locals,stack_data=True)
                span(m,0xc67,0x756,0x7bf,locals,stack_data=True)
                span(m,0xc67,0x838,0x873,locals,stack_data=True)
                rows.append(f'C {person} {seat} {occupied} '+m.read(m.state+0xc724+250+121,2).hex()+' '+ ' '.join(str(m.read(m.state+0xc620+17*p,1)[0]) for p in range(8)))
    for skill in range(1,6):
        for technician in (0,1,7):
            for count in (1,4):
                m.reset();m.write(m.ds+0x4fc0,(42).to_bytes(3,'little'))
                for i in range(4):
                    b=bytearray(m.template());b[17:36]=bytes(19);b[51]=0x90;b[85]=0xa2;m.write(m.state+0xc724+125*i,b)
                    donor=bytearray(m.template());donor[51]=16;donor[85]=34;m.write(m.state+0xc918+125*i,donor);m.word(m.state+0x3954+2*i,i<count)
                span(m,0x5ab,0xc7,0x42a,{-6:skill,-4:technician})
                if technician:span(m,0x5ab,0x43c,0x46a,{-8:count,-4:technician})
                rows.append(f'T {skill} {technician} {count} {m.word(0x7f000-40) if technician else 0} {int.from_bytes(m.read(m.ds+0x4fc0,3),"little")} '+ ' '.join(fingerprint(m.read(m.state+0xc724+125*i,125)) for i in range(4)))
    # Formation origin (64,64); no RNG or rendering calls.
    m.reset();m.word(m.buffer+0xa44b,0xc40);m.word(m.buffer+0xa44d,0xc040)
    for p in range(8):m.write(m.state+0xc614+17*p,bytes([p])+bytes(11)+bytes([8])+bytes(4))
    for slot in range(4):m.write(m.state+0xc724+125*slot,m.template())
    span(m,0x103b,0x1ce,0x2db,{-40:0xc40,-46:0xc040})
    for p in range(8):rows.append(f'P {p} {m.word(m.state+0x400c+2*p)&127} {m.word(m.state+0x403e+2*p)&127}')
    for p in range(4):rows.append(f'M {p} {m.word(m.state+0x4004+2*p)&127} {m.word(m.state+0x4036+2*p)&127}')
    (ROOT/'tests/fixtures/field-primary.txt').write_text('\n'.join(rows)+'\n');print('Primary field/crew/formation cases:',len(rows)-1)
if __name__=='__main__':main()
