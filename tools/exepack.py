#!/usr/bin/env python3
"""Read the supplied EXEPACK variant, returning its unrelocated load image.

Independently implemented from the RB header / backward RLE format description;
no third-party unpacker code. This is data extraction, not a replacement DOS EXE.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path


def unpack(b):
    if len(b) < 28 or b[:2] != b"MZ":
        raise ValueError("Not a complete DOS MZ header")
    h = struct.unpack_from("<14H", b)
    start = h[4] * 16
    packed_end = start + h[11] * 16
    if not 28 <= start < packed_end or packed_end + 16 > len(b):
        raise ValueError("EXEPACK header outside file")
    fields = struct.unpack_from("<8H", b, packed_end)
    if fields[7] != 0x4252 or h[10] != 16:
        raise ValueError("Unsupported EXEPACK variant (expected 16-byte RB header)")
    length = fields[6] * 16
    if not 0 < length <= 0x100000 or packed_end + fields[3] != len(b):
        raise ValueError("Invalid EXEPACK image/stub size")
    out = bytearray(length)
    src, dest = packed_end - 1, length
    while src >= start and b[src] == 255:
        src -= 1
    runs = 0
    while True:
        if src - 2 < start:
            raise ValueError("Truncated EXEPACK run")
        command = b[src]
        count = struct.unpack_from("<H", b, src - 2)[0]
        src -= 3
        if count == 0 or count > dest:
            raise ValueError("EXEPACK output run exceeds image")
        dest -= count
        if command & 0xFE == 0xB0:
            if src < start:
                raise ValueError("Truncated EXEPACK repeat")
            out[dest:dest + count] = bytes([b[src]]) * count
            src -= 1
        elif command & 0xFE == 0xB2:
            if src - count + 1 < start:
                raise ValueError("Truncated EXEPACK literal")
            out[dest:dest + count] = b[src - count + 1:src + 1]
            src -= count
        else:
            raise ValueError(f"Unknown EXEPACK command 0x{command:02x}")
        runs += 1
        if command & 1:
            break
    if dest != src + 1 - start:
        raise ValueError("EXEPACK prefix length mismatch")
    out[:dest] = b[start:src + 1]
    return bytes(out), {"entry_cs": fields[1], "entry_ip": fields[0],
                        "image_size": length, "runs": runs, "prefix_size": dest,
                        "input_sha256": hashlib.sha256(b).hexdigest(),
                        "image_sha256": hashlib.sha256(out).hexdigest()}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source", type=Path)
    p.add_argument("output", type=Path, help="Use an ignored work/ destination")
    a = p.parse_args()
    image, metadata = unpack(a.source.read_bytes())
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_bytes(image)
    a.output.with_suffix(".json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata))
