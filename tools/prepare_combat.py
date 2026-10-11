#!/usr/bin/env python3
"""Extract original numeric combat tables and loan records into an ignored cache."""
import argparse
import hashlib
import json
from pathlib import Path
from exepack import unpack
from prepare_talk import EXE_SHA, IMAGE_SHA, DS

RANGES = [(0x28170,125),(0x281ed,125),(0x28364,125),(DS+0x2ed8,33*17),
          (DS+0x2d0a,15),(DS+0x2e40,46),(DS+0x2e5e,93),
          (DS+0x318a,8),(DS+0x3192,8)]

def extract(source):
    image, metadata = unpack(source)
    if metadata["input_sha256"] != EXE_SHA or metadata["image_sha256"] != IMAGE_SHA:
        raise ValueError("Combat offsets require the audited executable")
    parts = [image[a:a+n] for a,n in RANGES]
    origins = [{"image_offset":a,"length":n,"sha256":hashlib.sha256(b).hexdigest()}
               for (a,n),b in zip(RANGES,parts)]
    return b"BTC1"+b"".join(parts), {**metadata,"format":"BTC1","ranges":origins}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data",type=Path,default=Path("Original DOS"))
    parser.add_argument("--output",type=Path,default=Path("work/combat-data.bin"))
    args = parser.parse_args()
    blob, provenance = extract((args.data/"BTECH.EXE").read_bytes())
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_bytes(blob)
    args.output.with_suffix(".json").write_text(json.dumps(provenance,indent=2)+"\n")
    print(f"Prepared {len(blob)} bytes of original combat data: {args.output}")
