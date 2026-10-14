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
    # Personal armour repair fragments, appended so earlier text IDs stay stable.
    addresses.extend(DS+p for p in (0x4c1c,0x4c60,0x4c75,0x4c79,0x4c81,0x4cae,0x4cd3,0x4cee,0x4d14,0x4d4f,0x4d67))
    # Speed Shop native headings and the offer/result appended to its BLD text.
    addresses.extend(DS+p for p in (0x1d1e,0x1d33,0x1d9c,0x1dc8,0x1dee))
    # Spy inspection warnings and the three original post-wave branches.
    addresses.extend(DS+p for p in (0x07ff,0x1222,0x34e9,0x34f6,0x3510,0x3555,0x358e,
        0x35d1,0x3610,0x3653,0x3666,0x36a9,0x36f6,0x3731,0x3774,
        0x37b8,0x37fd,0x3830,0x387a))
    # Original mech/on-foot command lists, header and friend/enemy scan text.
    addresses.extend(DS+p for p in (0x121e,0x3a6f,0x3abc,0x3d73,0x1174,0x1189,
        0x1195,0x1245,0x1257,0x1148,0x114f,0x115b,0x1166,0x3d94,0x3dcd,0x3e19))
    # Complete 09B8 repair/reload dialogs. Append to retain earlier text IDs.
    addresses.extend(DS+p for p in (0x17e5,0x17f7,0x1834,0x1879,0x1899,0x18bf,
        0x1902,0x1919,0x192a,0x1981,0x19bc,0x1a19,0x1a4f,0x1a66,0x1a77,
        0x1ace,0x1ada,0x1ae5,0x1ae7,0x1b44,0x1b63,0x1bb5,0x1bd3,0x1c0f,
        0x1c19,0x1c35,0x1c4b,0x1c70,0x1c97,0x1ca7,0x1cce,0x1e99,0x1ea8,
        0x1eae,0x1ed1,0x1eff,0x1f19,0x1f49,0x1f94,0x1fc9,0x2008,
        0x17ce,0x17d6,0x17dc,0xaca,0x1e3c,0x1e4d,0x1e56,0x1e70,0x1e2f))
    # 0C31:000A medical presentation, including cooldown/healthy branches.
    addresses.extend(DS+p for p in (0x252d,0x2538,0x2543,0x2553,0x256f,0x2587,0x2591,0x25a4,0x25cf))
    for entry in range(0x25e2,0x2602,4):
        offset,segment=struct.unpack_from('<HH',image,DS+entry)
        addresses.append(segment*16+offset)
    addresses.append(DS+0x050d) # Original 0000:2A4F held-page footer.
    # Battle results, salvage and pockets (291 onward).
    addresses.extend(DS+p for p in (0x38fc,0x3936,0x3954,0x39aa,0x39ca,0x39f7,
        0xfae,0xfff,0x101d,0x102f,0x104c,0x1085,0x10b5,0x10c6,0x10e5,0x10ff,0x1113,
        0xefe,0xf28,0xf40,0xf65,0xf9e,0xfa0))
    for skill in (2,3,4):
        offset,segment=struct.unpack_from('<HH',image,DS+0xf9a+4*skill)
        addresses.append(segment*16+offset)
    # Original 0D43 weapon/target headings; earlier IDs remain unchanged.
    addresses.extend(DS+p for p in (0x29a3,0x2aa8))
    # 0D43 weapon failures/overrides and infantry prompts; 103B kick prompt.
    addresses.extend(DS+p for p in (0x2a00,0x2a39,0x2a74,0x2ac6,0x2ada,0x2ae6,
        0x2aec,0x2af1,0x2b0c,0x2b16,0x3ce0,0x3cfa))
    # 0D43 weapon-entry shutdown and damaged/destroyed sensor warnings.
    addresses.extend(DS+p for p in (0x2904,0x292d,0x2964))
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
    return header+blob+font, {**metadata,"format":"BTTA/v22","strings":origins,
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
