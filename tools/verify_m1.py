#!/usr/bin/env python3
"""Check the canonical original movement fixture against the independent core.

Optional --reference-run also checks freshly captured original snapshots and
reports pixel agreement for the map panel (Pillow needed only for that report).
No proprietary bytes are written into tests or docs.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=ROOT / "build/btech-headless")
    parser.add_argument("--reference-run", type=Path)
    parser.add_argument("--native-log", type=Path)
    args = parser.parse_args()
    manifest = json.loads((ROOT / "docs/original-manifest.json").read_text())
    for row in manifest["files"]:
        data = (ROOT / row["path"]).read_bytes()
        check(len(data) == row["size"] and hashlib.sha256(data).hexdigest() == row["sha256"],
              f"Original differs from the audited corpus: {row['path']}")
    fixture = json.loads((ROOT / "tests/fixtures/reference-movement.json").read_text())
    work = ROOT / "work/m1-verification"
    work.mkdir(parents=True, exist_ok=True)
    replay = work / "movement.actions"
    replay.write_text("".join(step["action"] + "\n" for step in fixture["steps"]))
    command = [str(args.binary.resolve()), "--data", str(ROOT / "Original DOS"),
               "--replay", str(replay), "--trace"]
    a = subprocess.run(command, check=True, capture_output=True, text=True).stdout
    b = subprocess.run(command, check=True, capture_output=True, text=True).stdout
    check(a == b, "Identical logical replay is not deterministic")
    states = [json.loads(line) for line in a.splitlines()]
    expected = [fixture["initial"], *fixture["steps"]]
    check(len(states) == len(expected), "Missing replay snapshots")
    for index, (got, want) in enumerate(zip(states, expected)):
        for key in ("x_half", "y_half"):
            check(got[key] == want[key], f"Step {index} {key}: native {got[key]}, original {want[key]}")
        check(got["gate"] == 85 and got["map"] == 1, "Wrong gate/location projection")
        check(got["tick"] == index, "Replay tick count mismatch")
    bad = work / "unsupported.actions"
    bad.write_text("unimplemented-opcode\n")
    rejected = subprocess.run([str(args.binary.resolve()), "--data", str(ROOT / "Original DOS"),
                               "--replay", str(bad)], capture_output=True, text=True)
    check(rejected.returncode != 0 and "Unsupported replay action" in rejected.stderr,
          "Unknown logical action was silently accepted")
    print(f"PASS: {len(expected)} canonical movement states, free/blocked steps, deterministic replay, unknown-action rejection; all 88 original hashes match.")
    if args.native_log:
        output = subprocess.run([str(args.binary.resolve()), "--data", str(ROOT / "Original DOS"),
                                 "--replay", str(args.native_log.resolve())], check=True,
                                capture_output=True, text=True).stdout
        s = json.loads(output)
        check(s["x_half"] == 70 and s["y_half"] == 25 and s["tick"] == 8 and s["blocked"] == 0,
              "Native recorded inputs do not replay to the smoke state")
        print("PASS: recorded native SDL inputs replay to the same logical state and tick.")
    if args.reference_run:
        run = args.reference_run.resolve()
        original_states = [json.loads((run / "before-start-state.json").read_text())]
        original_states += [json.loads((run / (step["label"] + "-state.json")).read_text()) for step in fixture["steps"]]
        for index, (got, want) in enumerate(zip(original_states, expected)):
            check(got["map1_payload_present"] and got["gate"] == 85, "Original map/gate evidence failed")
            for axis, key in enumerate(("x_half", "y_half")):
                check((got["cursor_raw"][axis] & 127) == want[key], f"Original cursor step {index} drifted")
                party = got["party_x_raw"] if axis == 0 else got["party_y_raw"]
                check((party[0] & 127) == want[key], f"Original player step {index} drifted")
        print("PASS: live original cursor AND party[0] match the canonical movement fixture.")
        # The screenshot compares geometry/palette. Behavioral equivalence is
        # established above; screenshot agreement never replaces that check.
        from PIL import Image
        first = work / "first.actions"
        first.write_text("right\n")
        frame = work / "start.ppm"
        subprocess.run([str(args.binary.resolve()), "--data", str(ROOT / "Original DOS"),
                        "--replay", str(first), "--frame", str(frame)], check=True, capture_output=True)
        native = Image.open(frame).convert("RGB").crop((104, 0, 320, 200))
        original = Image.open(run / "captures/start.png").convert("RGB").crop((104, 0, 320, 200))
        same = sum(a == b for a, b in zip(native.getdata(), original.getdata()))
        total = 216 * 200
        check(same / total > 0.97, "Map-panel pixel agreement unexpectedly below 97%")
        print(f"MAP1 panel: {same}/{total} pixels equal ({100*same/total:.3f}%). Player/NPC sprites and UI remain partial; whole-screen equality is not claimed.")
        tiles_file = work / "tiles.indices"
        subprocess.run([str(args.binary.resolve()), "--data", str(ROOT / "Original DOS"),
                        "--export-tiles", str(tiles_file)], check=True, capture_output=True)
        indices = tiles_file.read_bytes()
        palette = [(0,0,0),(0,0,170),(0,170,0),(0,170,170),(170,0,0),(170,0,170),(170,85,0),(170,170,170),
                   (85,85,85),(85,85,255),(85,255,85),(85,255,255),(255,85,85),(255,85,255),(255,255,85),(255,255,255)]
        reference = list(Image.open(ROOT / "UnBattletech/Assets/BTTLTECH.png").convert("RGB").getdata())
        check([palette[i] for i in indices] == reference, "Independent C tile decoding differs from secondary PNG check")
        print("PASS: all 64000 decoded tile pixels match the secondary PNG (standard palette, before observed terrain remap).")


if __name__ == "__main__":
    main()
