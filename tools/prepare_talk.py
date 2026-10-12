#!/usr/bin/env python3
"""Extract bounded native-dialogue strings with our proven EXEPACK reader.

No asset bytes belong in Git. The ignored cache carries source/image hashes and
original addresses in its JSON sidecar; the C runtime reads only the cache.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path
if __package__:
    from .exepack import unpack
else:
    from exepack import unpack

EXE_SHA = "15a1712682cf1fe50ca9e6a68a4b31d3bef7912401915edf7bb6242be193562a"
IMAGE_SHA = "100f0df244e4b0c8693d1b5013fb073f486b35d6f5c538ecd53d03f85ed54bfa"
DS = 0x36DB0
FONT = 0x26D21  # Original 187F:2251 reads 1C6C:A661, eight bytes per glyph.
BANK_OFFSETS = (0x49d3,0x49d9,0x49f6,0x4a09,0x4a1c,0x4a2b,0x4a6a,0x4a86,
    0x4a8d,0x4abc,0x4ac0,0x4acb,0x4af5,0x4b3b,0x4b52,0x4b67,0x4b77,
    0x4bb8,0x4bd8,0x4bdf,0x4c07,0x4c0b,0x1791)
SCHOOL_OFFSETS = (0x491a,0x4948,0x4999)


def extract(source):
    image, metadata = unpack(source)
    if metadata["input_sha256"] != EXE_SHA or metadata["image_sha256"] != IMAGE_SHA:
        raise ValueError("Native dialogue offsets require the audited v1.03 executable")
    addresses = [DS+p for p in (0x16de,0x170e,0x1728,0x172d,0x1761,0x178f)]
    for entry in range(0x4e32,0x4e5e,4):
        offset, segment = struct.unpack_from("<HH",image,DS+entry)
        addresses.append(segment*16+offset) # Unrelocated image uses relative segments.
    addresses.extend(DS+p for p in BANK_OFFSETS)
    for entry in range(0x4e7e,0x4e8a,4):
        offset, segment = struct.unpack_from("<HH",image,DS+entry)
        addresses.append(segment*16+offset)
    addresses.extend(DS+p for p in SCHOOL_OFFSETS)
    for entry in range(0x4ea2,0x4ec2,4):
        offset, segment = struct.unpack_from("<HH",image,DS+entry)
        addresses.append(segment*16+offset)
    addresses.append(DS+0x4f7e)
    addresses.extend(DS+p for p in (0x27f2,0x286c,0x2886))
    for entry in range(0x4de2,0x4e32,4):
        offset, segment = struct.unpack_from("<HH",image,DS+entry)
        addresses.append(segment*16+offset)
    addresses.extend(DS+p for p in (0x146b,0x14a1,0x48b3,0x48df,0x48e4,0x48ee))
    addresses.extend(DS+p for p in (0x1434,0x14ef,0x152a))
    addresses.extend(DS+p for p in (0x1115,0x3d3a,0x3d5e,0x398b))
    for base,count in ((0x2e0c,11),(0x4e8a,6)):
        for i in range(count):
            offset,segment=struct.unpack_from("<HH",image,DS+base+4*i)
            addresses.append(segment*16+offset)
    addresses.extend(DS+p for p in (0x127e,0x12d6,0x12e0,0x1265,0x1269,0x126d,0x1260,
        0xb0e,0xb4c,0xb90,0xbe2))
    addresses.extend(DS+p for p in (0x2075,0x20ce,0x2113,0x215d,0x2240,0x2275,
        0x228b,0x22c7,0x22e8,0x2328,0x2367,0x23b2,0x2409,0x242c,0x2441,0x2457,
        0x2187,0x21b2,0x21b9))
    for entry in range(0x2234,0x2240,4):
        offset,segment=struct.unpack_from('<HH',image,DS+entry)
        addresses.append(segment*16+offset)
    # Primary invasion popups (141..148), laser-shop replacement (149..150)
    # and prison-yard search prompts (151..155); asset bytes stay local.
    addresses.append(DS+0x3452)
    for entry in range(0x3a2e,0x3a42,4):
        offset,segment=struct.unpack_from('<HH',image,DS+entry)
        addresses.append(segment*16+offset)
    addresses.extend(DS+p for p in (0x3497,0x34b8,0x4d8a,0x4da4,0x155d,0x159a,0x15d4,0x1611,0x15f8))
    addresses.extend(DS+p for p in (0x4209,0x4235))
    for entry in range(0x4e5e,0x4e7e,4):
        offset,segment=struct.unpack_from('<HH',image,DS+entry)
        addresses.append(segment*16+offset)
    addresses.extend(DS+p for p in (0x3402,0x3414,0x341b,0x3421,0x3428,0x343a))
    blob = bytearray(); ranges = []; origins = []
    for address in addresses:
        end = image.index(0,address)
        text = image[address:end]
        if len(text) > 512 or any(c not in (6,13,15) and not 32 <= c < 127 for c in text):
            raise ValueError("Invalid original dialogue string")
        ranges.append((len(blob),len(text))); blob += text+b"\0"
        origins.append({"image_offset":address,"length":len(text),
                        "sha256":hashlib.sha256(text).hexdigest()})
    header = b"BTTA"+struct.pack("<HH",len(blob),len(ranges))
    header += bytes.fromhex(EXE_SHA)+bytes.fromhex(IMAGE_SHA)
    header += b"".join(struct.pack("<HH",*r) for r in ranges)
    font = image[FONT:FONT+2048]
    return header+blob+font, {**metadata,"format":"BTTA/v13","strings":origins,
        "font":{"image_offset":FONT,"length":len(font),"sha256":hashlib.sha256(font).hexdigest()}}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data",type=Path,default=Path("Original DOS"))
    p.add_argument("--output",type=Path,default=Path("work/talk-data.bin"))
    args = p.parse_args()
    cache, provenance = extract((args.data/"BTECH.EXE").read_bytes())
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_bytes(cache)
    args.output.with_suffix(".json").write_text(json.dumps(provenance,indent=2)+"\n")
    print(f"Prepared {len(cache)} bytes of local native dialogue data: {args.output}")
