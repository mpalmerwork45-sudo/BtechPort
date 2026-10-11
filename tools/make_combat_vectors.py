#!/usr/bin/env python3
"""Regenerate factual numeric cases by executing the original instructions."""
import random
from pathlib import Path
from combat_oracle import OriginalCombat, DS, STATE, BUFFER, ROOT

def fingerprint(record):
    value = 14695981039346656037
    for byte in record:
        value = ((value ^ byte)*1099511628211) & ((1 << 64)-1)
    return value

def generate():
    oracle = OriginalCombat(); random_source = random.Random(0xb7ec)
    rows = []
    seeds = [random_source.randrange(1,1 << 24) for _ in range(128)]
    for seed in seeds:
        result, after = oracle.dice(seed.to_bytes(3,"little"))
        rows.append(f"D {seed} {result} {int.from_bytes(bytes(after),'little')}")
    for weapon in (15,16,17,23,24,29,32):
        for dx in range(-31,32):
            oracle.reset(); x,y,tx,ty = 64,64,64+dx,64+(dx%9)-4
            oracle.word(BUFFER+0xa44b,0xc00+x); oracle.word(BUFFER+0xa44d,0xc000+y)
            oracle.word(STATE+0x401c,0xc00+tx); oracle.word(STATE+0x404e,0xc000+ty)
            result = oracle.call(0xe31,0xf24,12,weapon)
            rows.append(f"R {weapon} {x} {y} {tx} {ty} {result}")
    for choice in range(3):
        for mode in range(3):
            for heat in (0,4,5,13,29,30):
                for left,right in ((207,207),(0,0),(199,207),(200,207),(0,8),(255,255),(7,7)):
                    oracle.reset(); record = bytearray(oracle.template(choice)); record[36:38] = bytes([left,right])
                    oracle.write(STATE+0xc724,record); oracle.write(STATE+0x6e,[heat])
                    oracle.call(0x103b,0x22bc,0,mode)
                    rows.append(f"P {choice} {mode} {heat} {left} {right} {oracle.word(STATE+0x3770)}")
        for loc in range(28,36):
            for variant in range(3):
                for seed in seeds[:16]:
                    oracle.reset(); record = bytearray(oracle.template(choice))
                    if variant == 1: record[loc] = 0
                    if variant == 2: record[36:38] = bytes(2)
                    oracle.write(STATE+0xc724,record); oracle.write(DS+0x4fc0,seed.to_bytes(3,"little"))
                    oracle.word(STATE+0xe484,0)
                    oracle.call(0xe31,0x11ab,0,loc)
                    after = int.from_bytes(oracle.read(DS+0x4fc0,3),"little")
                    record_hash = fingerprint(oracle.read(STATE+0xc724,125))
                    rows.append(f"K {choice} {loc} {seed} {variant} {oracle.word(STATE+0xe484)} {after} {record_hash:016x}")
    return rows

if __name__ == "__main__":
    rows = generate()
    path = ROOT/"tests/fixtures/combat-primitives.txt"
    path.write_text("# Original 8086 oracle: dice, mech range, movement points, critical effects.\n"+
                    "# Inputs and resulting numbers/fingerprints only; no executable or asset bytes.\n"+"\n".join(rows)+"\n")
    print(f"Wrote {len(rows)} original instruction cases to {path}")
