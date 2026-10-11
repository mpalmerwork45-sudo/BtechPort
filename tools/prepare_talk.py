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


def extract(source):
    image, metadata = unpack(source)
    if metadata["input_sha256"] != EXE_SHA or metadata["image_sha256"] != IMAGE_SHA:
        raise ValueError("Native dialogue offsets require the audited v1.03 executable")
    addresses = [DS+p for p in (0x16de,0x170e,0x1728,0x172d,0x1761,0x178f)]
    for entry in range(0x4e32,0x4e5e,4):
        offset, segment = struct.unpack_from("<HH",image,DS+entry)
        addresses.append(segment*16+offset) # Unrelocated image uses relative segments.
    blob = bytearray(); ranges = []; origins = []
    for address in addresses:
        end = image.index(0,address)
        text = image[address:end]
        if len(text) > 512 or any(c != 13 and not 32 <= c < 127 for c in text):
            raise ValueError("Invalid original dialogue string")
        ranges.append((len(blob),len(text))); blob += text+b"\0"
        origins.append({"image_offset":address,"length":len(text),
                        "sha256":hashlib.sha256(text).hexdigest()})
    header = b"BTT1"+struct.pack("<HH",len(blob),len(ranges))
    header += bytes.fromhex(EXE_SHA)+bytes.fromhex(IMAGE_SHA)
    header += b"".join(struct.pack("<HH",*r) for r in ranges)
    return header+blob, {**metadata,"format":"BTT1","strings":origins}


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
