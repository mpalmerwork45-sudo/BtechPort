#!/usr/bin/env python3
"""Extract original numeric combat tables and loan records into an ignored cache."""
import argparse
import hashlib
import json
import struct
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
    programs=bytearray();program_origins=[]
    for group in range(18):
        table=DS+([0x2d58,0x2d78,0x2d98,0x2db8][group] if group<4 else 0x3ff8+(group-4)*32)
        for direction in range(8):
            off,segment=struct.unpack_from('<HH',image,table+direction*4)
            start=segment*16+off;at=start;frames=[]
            for _ in range(32):
                token=image[at];at+=1
                if token==255:break
                if token==253:at+=1;continue
                if token>=128:raise ValueError('Unexpected non-finite attack program')
                frames.append(token)
            else:raise ValueError('Unterminated attack program')
            if not 1<=len(frames)<=8:raise ValueError('Unexpected attack frame count')
            programs+=bytes([len(frames)]+frames+[0]*(8-len(frames)))
            program_origins.append({'table':table+direction*4,'image_offset':start,'length':at-start,
                'sha256':hashlib.sha256(image[start:at]).hexdigest()})
    programs+=image[DS+0x2e3c:DS+0x2e40]+image[DS+0x41d8:DS+0x41db]
    jenner=image[0x283e1:0x283e1+125]
    extra_ranges=[(0x282e7,125),(DS+0x1e7a,7),(DS+0x1e82,8),(DS+0x1e8a,8),
                  (DS+0x2cf4,22),(0x28170,125),(0x281ed,125),(0x2826a,125),
                  (DS+0x1d8c,16),(DS+0x2060,7),(DS+0x1e24,11),(DS+0x141a,26)]
    extra=b''.join(image[a:a+n] for a,n in extra_ranges)
    sound=image[DS+0x5006:DS+0x5006+2+314*2]
    field=b''.join(image[DS+0x2602+4*i:DS+0x2606+4*i] for i in range(8))+image[DS+0x3a16:DS+0x3a2e]+image[DS+0x4f6e:DS+0x4f7e]
    cache_ranges=[(DS+0x21ce,33),(DS+0x21f0,33),(DS+0x2212,33),
        (DS+0x247a,60),(DS+0x241e,14),(DS+0x20bc,18),(DS+0x246e,12),
        (0x1c6c0+0x2257,250),(0x1c6c0+0x2351,250)]
    cache=b''.join(image[a:a+n] for a,n in cache_ranges)
    # 07DC:08D5 selects the arena templates through DS:13E2. These are
    # original records, including its special spectator and UrbanMechs.
    arena_ranges=[]
    for i in range(11):
        offset,segment=struct.unpack_from('<HH',image,DS+0x13e2+4*i)
        arena_ranges.append((segment*16+offset,125))
    arena_ranges.extend(((0x27e80+0x5de,125),(0x27e80+0x65b,125),(DS+0x140e,11),(DS+0x165a,7),(DS+0x1642,16),(DS+0x164e,16)))
    arena=b''.join(image[a:a+n] for a,n in arena_ranges)
    # 12E8:17B2/17CD/17E8 choose origins by sprite family. The missile
    # interpreter repeats six frames through FE 07; preserve its data.
    presentation=image[DS+0x2d28:DS+0x2d58]
    for direction in range(8):
        off,segment=struct.unpack_from('<HH',image,DS+0x2dd8+direction*4)
        at=segment*16+off;program=image[at:at+8]
        if program[6:]!=bytes([254,7]) or any(not 26<=v<=41 for v in program[:6]):
            raise ValueError('Unexpected missile loop')
        presentation+=program[:6]
    return b"BTCC"+b"".join(parts)+programs+jenner+extra+sound+field+cache+arena+presentation, {**metadata,"format":"BTCC/v12","ranges":origins,
        'weapon_presentation':{'muzzle_table':DS+0x2d28,'missile_pointers':DS+0x2dd8,
            'length':len(presentation),'sha256':hashlib.sha256(presentation).hexdigest()},
        'arena_tables':[{'image_offset':a,'length':n,'sha256':hashlib.sha256(image[a:a+n]).hexdigest()} for a,n in arena_ranges],
        'cache_tables':[{'image_offset':a,'length':n,'sha256':hashlib.sha256(image[a:a+n]).hexdigest()} for a,n in cache_ranges],
        'field_tables':{'image_offsets':[DS+0x2602,DS+0x3a16,DS+0x4f6e],'lengths':[32,24,16],'sha256':hashlib.sha256(field).hexdigest()},
        'speaker_programs':{'image_offset':DS+0x5006,'length':len(sound),'sha256':hashlib.sha256(sound).hexdigest()},
        'campaign_ranges':[{'image_offset':a,'length':n,'sha256':hashlib.sha256(image[a:a+n]).hexdigest()} for a,n in extra_ranges],
        'invasion_template':{'image_offset':0x283e1,'length':125,'sha256':hashlib.sha256(jenner).hexdigest()},
        'pose_programs':program_origins,'reaction':DS+0x2e3c,'impact':DS+0x41d8}

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
