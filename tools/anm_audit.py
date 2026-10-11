#!/usr/bin/env python3
"""Independent ANM decoder, based on original 187F:23EC and 0800:1AFD.

The executable consumes 3872 XOR bytes per frame, including frames with a run
that reaches the boundary before its count expires. No game assets are saved in
the repository. This module also supplies numeric frame facts to the oracle.
"""
import argparse
import hashlib
import json
from pathlib import Path

PACKED = 88 * 88 // 2


def decode(data):
    if len(data) < 51:
        raise ValueError("Truncated ANM header")
    end = data[:32].find(b"\0")
    if end <= 0 or any(c < 65 or c > 82 for c in data[:end]):
        raise ValueError("Invalid ANM sequence")
    sequence = data[:end].decode("ascii")
    frame = bytearray(PACKED)
    offset = 51
    frames = []
    for letter in sequence:
        start, out = offset, 0
        while out < PACKED:
            if offset >= len(data):
                raise ValueError("Truncated ANM packet")
            control = data[offset]
            offset += 1
            repeat = control == 0 or control >= 128
            if control == 0:
                if offset + 2 > len(data):
                    raise ValueError("Truncated ANM count")
                count = int.from_bytes(data[offset:offset+2], "big")
                offset += 2
                if count == 0:
                    count = 65536  # Original LOOP wraps CX=0.
            else:
                count = 256-control if repeat else control
            count = min(count, PACKED-out)
            needed = 1 if repeat else count
            if offset + needed > len(data):
                raise ValueError("Truncated ANM delta")
            for i in range(count):
                frame[out+i] ^= data[offset if repeat else offset+i]
            out += count
            offset += needed
        units = data[32+ord(letter)-65]*data[50]*3//4
        frames.append({"letter":letter,"offset":start,"end":offset,
                       "units":units,"packed":bytes(frame),
                       "sha256":hashlib.sha256(frame).hexdigest()})
    return {"sequence":sequence,"scale":data[50],"frames":frames,
            "consumed":offset,"size":len(data)}


def facts(result):
    return {**result,"frames":[{k:v for k,v in f.items() if k != "packed"}
                               for f in result["frames"]]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("Original DOS"))
    args = parser.parse_args()
    results = {}
    for kind in range(22):
        data = (args.data/f"O{kind}.ANM").read_bytes()
        results[str(kind)] = {"source_sha256":hashlib.sha256(data).hexdigest(),
                              **facts(decode(data))}
    print(json.dumps(results, indent=2))
