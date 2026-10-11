#!/usr/bin/env python3
"""Inventory originals, including MZ headers and duplicate content groups."""
import collections
import hashlib
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    rows = []
    for path in sorted((ROOT / "Original DOS").rglob("*")):
        if not path.is_file():
            continue
        b = path.read_bytes()
        kind = path.suffix.upper()
        row = {"path": path.relative_to(ROOT).as_posix(), "size": len(b),
               "sha256": hashlib.sha256(b).hexdigest(), "header_hex": b[:16].hex()}
        if b[:2] == b"MZ" and len(b) >= 28:
            h = struct.unpack_from("<14H", b)
            row.update(format="DOS MZ executable", mz={
                "declared_size": (h[2] - 1) * 512 + (h[1] or 512),
                "header_bytes": h[4] * 16, "relocations": h[3],
                "initial_cs": h[11], "initial_ip": h[10],
                "initial_ss": h[7], "initial_sp": h[8]})
            if b"Version 1.03" in b:
                row["version_string"] = "Version 1.03"
        elif kind == ".MTP" and path.name != "MAP15.MTP" and len(b) >= 5:
            row.update(format="MTP header + tiles", width=b[3], height=b[4],
                       tile_data_offset=541,
                       size_matches=541 + b[3] * b[4] == len(b))
        elif path.name == "MAP15.MTP":
            row.update(format="raw 32 x 24 star map (reference interpretation)")
        elif kind in (".ICN", ".CMP"):
            row.update(format="packed nibble graphics / signed RLE", 
                       declared_post_size_bytes=struct.unpack_from("<H", b)[0],
                       compression=b[2], size_matches=len(b) - 2 == struct.unpack_from("<H", b)[0])
        elif kind == ".BLD":
            row.update(format="BLD script / cipher", interpreter_offset=160)
        elif kind == ".ANM":
            row.update(format="ANM XOR-delta animation (reference interpretation)")
        elif path.name.startswith("GAME"):
            row.update(format="original game save; semantics not round-trip verified")
        else:
            row.update(format="UNKNOWN")
        rows.append(row)
    groups = collections.defaultdict(list)
    for r in rows:
        groups[r["sha256"]].append(r["path"])
    output = {"files": rows, "count": len(rows), "total_bytes": sum(r["size"] for r in rows),
              "subdirectories": [p.relative_to(ROOT / "Original DOS").as_posix()
                                 for p in sorted((ROOT / "Original DOS").rglob("*")) if p.is_dir()],
              "duplicate_content_groups": [g for g in groups.values() if len(g) > 1]}
    out = ROOT / "docs/original-manifest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(output, indent=2) + "\n")
    summary = """# Original files — M0, 2026-10-11

**VERIFIED:** 88 files, 641,365 bytes, all in one directory; no identical-content duplicate groups. No manual, README, configuration file or alternate game executable is present. This is the supplied corpus, not a claim that it is a complete retail distribution. Provenance against a separate retail image is **UNKNOWN**. Regenerate this inventory with `python3 tools/inventory.py`; verify the immutable trees with `python3 tools/reference_guard.py verify`.

## Executables and loading

`BTECH.EXE` (152,429 bytes) is the correct game executable. Its embedded version string is **VERIFIED** `Version 1.03`; it boots without patching in DOSBox 0.74-3, using a working copy. `$VERIFY.EXE` (16,281 bytes) is another DOS MZ executable; its exact role is **UNKNOWN**, and it was not needed for the observed run. There is no `UNBTECH.EXE` in the original directory.

`BTECH.EXE` uses the 16-byte `RB` EXEPACK variant: packed header at file offset `0x23870`, initial packed CS:IP `2367:0010`, recovered entry relative CS:IP `187F:2D82`. The independently extracted **unrelocated load image** is 247,216 bytes, SHA-256 `100f0df244e4b0c8693d1b5013fb073f486b35d6f5c538ecd53d03f85ed54bfa`. `tools/exepack.py` reads the binary without modifying it; it does not construct a replacement DOS executable. Packed disk offsets, image offsets, Reko's load base `0800`, and live DOS load segments must be distinguished. The observed DOSBox load segment is `01A2`, not a portable fixed address.

Original launch: `python3 tools/reference_session.py --script tools/reference-movement.json`. The harness mounts only ignored `work/dos/`, selects VGA and hard disk, uses normal CPU core at 10,000 cycles, records inputs, captures frames and reads its child emulator's memory. Xvfb keeps the session off the user's desktop. Every run is bounded and closes automatically. DOSBox, Xvfb and small supporting packages are extracted under `local-deps/`; no system installation or reference modification was performed. Spice86's matching source/runtime and dotnet are missing locally. Details are in [TESTING.md](TESTING.md).

## Resource census and format findings

| Group | Count | Evidence / limits |
|---|---:|---|
| BLD | 26 | All converter raw-byte round trips pass; Citadel decryption/menu/Hall/first Katrina visit/repeat/exit are **VERIFIED**, broader control flow remains **INFERRED/UNKNOWN**. |
| MTP | 15 | MAP1–14 have a **VERIFIED** 541-byte header and 8×8 block order; MAP15 is a different 768-byte raw map. |
| ICN | 5 | **VERIFIED** signed-RLE output is 32,000 packed bytes / 64,000 pixel indices per file. |
| CMP | 7 | Same signed-RLE; format 2 uses column-major packed bytes. |
| ANM | 22 | O0–O21; XOR-delta animation interpretation is **INFERRED**, not implemented. |
| GAME | 6 | GAME1–6, all **VERIFIED** 3913 bytes. Original save semantics **UNKNOWN**. |
| Save backups | 3 | GAME1.bak, GAME4.bak, GAME5.bak, also 3913 bytes. |
| EXE | 2 | BTECH and $VERIFY; both lengths match their MZ declared size. |
| Other | 2 | DEMOFILE (1023 bytes), WWOODBT.SIF (4352 bytes); roles not verified. |

MTP dimensions: MAP1/2/11/14 are 64×64 (4637 bytes), MAP3–10 are 32×32 (1565 bytes), MAP12/13 are 8×8 (605 bytes). MAP15 is 32×24 according to secondary format evidence, not accepted by the local-map parser. All MAP1 tile IDs fit the 250-tile BTTLTECH sheet.

ICN/CMP's initial little-endian size word counts bytes **after the size word**, including the format byte: `file_length - 2`, not `file_length - 3`. Positive runs copy that many literal bytes; negative signed runs repeat the next byte; zero introduces a 16-bit repeat count and value. All twelve files meet the size and decoded-length checks. Format-1 ICN tile pixels can be viewed as 16×4000. The standard EGA palette matches the secondary extraction PNG; the original MAP1 VGA display additionally maps resource index 5→EGA 9 and index 9→EGA 1, verified against captured frames.

Linux paths must preserve case and spaces: use `--data "Original DOS"`, or an absolute quoted path. The native M2b loader expects exact uppercase `MAP1.MTP`, `BTTLTECH.ICN` and `CITADEL.BLD`; the backup suffix is actually lowercase `.bak`. Missing resources produce diagnostics. Proprietary files, extracted pixels, screenshots, RAM dumps and local dependencies are excluded by `.gitignore`. See [Citadel evidence](M2_CITADEL_EVIDENCE.md) and [Katrina evidence](M2_KATRINA_EVIDENCE.md) for the verified BLD subset.

## Complete manifest

Apparent formats below are scoped by the confidence statements above. Full headers and additional metadata are in [original-manifest.json](original-manifest.json).

| File | Bytes | SHA-256 | Apparent format |
|---|---:|---|---|
"""
    for row in rows:
        name = Path(row["path"]).name
        summary += f"| `{name}` | {row['size']} | `{row['sha256']}` | {row['format']} |\n"
    (ROOT / "docs/ORIGINAL_FILES.md").write_text(summary)
    print(json.dumps({k: v for k, v in output.items() if k != "files"}, indent=2))


if __name__ == "__main__":
    main()
