#!/usr/bin/env python3
"""Record/verify reference contents without modifying either supplied directory."""
import argparse
import hashlib
import json
import os
import stat
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFERENCES = ("Original DOS", "UnBattletech")


def snapshot():
    entries = {}
    for directory in REFERENCES:
        base = ROOT / directory
        for p in [base, *sorted(base.rglob("*"))]:
            s = p.lstat()
            row = {"mode": stat.S_IMODE(s.st_mode), "mtime_ns": s.st_mtime_ns}
            if p.is_symlink():
                row.update(type="symlink", target=os.readlink(p))
            elif p.is_file():
                row.update(type="file", size=s.st_size,
                           sha256=hashlib.sha256(p.read_bytes()).hexdigest())
            elif p.is_dir():
                row.update(type="directory")
            else:
                raise RuntimeError(f"Unsupported reference entry: {p}")
            entries[p.relative_to(ROOT).as_posix()] = row
    return entries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("record", "verify"))
    parser.add_argument("--manifest", type=Path, default=ROOT / "docs/reference-baseline.json")
    args = parser.parse_args()
    current = snapshot()
    if args.action == "record":
        if args.manifest.exists():
            parser.error("Baseline already exists; refusing to overwrite it")
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(json.dumps(current, indent=2) + "\n")
        print(f"Recorded {len(current)} entries (including reference .git)")
        return
    baseline = json.loads(args.manifest.read_text())
    changes = [p for p in sorted(set(baseline) | set(current))
               if baseline.get(p) != current.get(p)]
    if changes:
        for p in changes:
            print(f"CHANGED: {p}")
        raise SystemExit(1)
    print(f"VERIFIED: {len(current)} reference entries unchanged (content/mode/mtime)")


if __name__ == "__main__":
    main()
