#!/usr/bin/env python3
"""Run the original prison-guard and arena setup, preserving its RNG draws."""
import json
from combat_oracle import OriginalCombat,ROOT
from make_party_vectors import SNAP
from make_combat_vectors import fingerprint
from prepare_talk import EXE_SHA,IMAGE_SHA

def main():
    m=OriginalCombat(snapshot=SNAP);rows=[]
    for seed in (0,1,42,0xd23646):
        m.reset();m.write(m.ds+0x4fc0,seed.to_bytes(3,'little'))
        m.write(m.state+0xd30c,[7]);m.word(m.state+0x3772,0)
        m.call(0x07dc,0x0d49,0,0x88)
        rng=int.from_bytes(m.read(m.ds+0x4fc0,3),'little')
        for i in range(8):
            record=m.read(m.state+0xc69c+17*i,17)
            rows.append(f'P {seed} {rng} {i} {m.word(m.state+0x4024+2*i)} {m.word(m.state+0x4056+2*i)} '+
                        ' '.join(str(v) for v in record))
    for seed in (0,1,42,0xd23646):
        for difficulty in (0,5,6):
            for rental in (0,1):
                m.reset();m.write(m.ds+0x4fc0,seed.to_bytes(3,'little'))
                m.write(m.state+0xd30f,[difficulty]);m.word(m.state+0x3772,0)
                m.word(m.state+0xe48e,rental);m.write(m.state+0xd452,[76,67,83,255])
                m.call(0x07dc,0x0d49,0x81,0)
                rng=int.from_bytes(m.read(m.ds+0x4fc0,3),'little')
                for i in range(2 if rental else 1):
                    record=m.read(m.state+0xc918+125*i,125)
                    rows.append(f'A {seed} {difficulty} {rental} {rng} {i} '+
                        f'{m.word(m.state+0x401c+2*i)} {m.word(m.state+0x404e+2*i)} '+
                        f'{m.read(m.state+0xd56a+i,1)[0]} {m.read(m.state+0x40a6+i,1)[0]} '+
                        f'{fingerprint(record):016x}')
    (ROOT/'tests/fixtures/theft-primary.txt').write_text('\n'.join(rows)+'\n')
    (ROOT/'tests/fixtures/theft-primary.json').write_text(json.dumps(dict(
        executable_sha256=EXE_SHA,image_sha256=IMAGE_SHA,cases=len(rows),
        routine='07DC:0D49 (image 08B09): prison (0,0x88) and arena (0x81,0)',
        prerequisites='Four RNG seeds, eight guards, owned/rented arena, difficulty 0/5/6 and one empty owned bay',
        intercepted_boundaries=[],comparison='Generated guard records, arena record fingerprints, packed coordinates, sprite bases, gait and exact RNG'),indent=2)+'\n')
    print('Primary theft setup cases:',len(rows))

if __name__=='__main__':main()
