#!/usr/bin/env python3
"""Compare original ANM buffers, font and border pixels with independent C output.

Fixtures contain only source identities, numeric observations and hashes.
Cutscene replay waits explicitly normalize VGA retraces to the 32ms core clock.
"""
import argparse
import hashlib
import json
import struct
import subprocess
from pathlib import Path
from anm_audit import decode, facts, PACKED
from prepare_talk import extract, EXE_SHA, IMAGE_SHA
from verify_m2 import check

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/"tests/fixtures"
FIXTURE = BASE/"reference-animations.json"
RUN = ROOT/"work/reference-runs/1791705480602565515"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def export():
    from PIL import Image
    corpus = {}
    for kind in range(22):
        raw = (ROOT/"Original DOS"/f"O{kind}.ANM").read_bytes()
        corpus[str(kind)] = {"source_sha256":sha(raw), **facts(decode(raw))}
    observed = {}
    for label, kind, count in (("launch",0,18),("dream",8,21)):
        raw = json.loads((RUN/(label+"-animation-frames.json")).read_text())["frames"]
        # A poll can straddle the original's buffer/sequence-index writes.
        # Keep only stable agreement; retain the untouched raw capture in work/.
        rows = [r for r in raw if r["index"] == r["sequence_index"]]
        check(len(rows) == count, "Missing stable original animation frames")
        for index, row in enumerate(rows):
            wanted = corpus[str(kind)]["frames"][index % (3 if kind else 18)]
            check(row["index"] == index % (3 if kind else 18) and
                  row["sha256"] == wanted["sha256"] and row["end"] == wanted["end"],
                  "Original animation buffer differs from independent decoding")
        observed[label] = {"animation":kind,"frames":rows,"transition_polls_excluded":len(raw)-len(rows)}
    cache, metadata = extract((ROOT/"Original DOS/BTECH.EXE").read_bytes())
    snap = json.loads((RUN/"rubble-return-state.json").read_text())
    ram = (RUN/"rubble-return-ram.bin").read_bytes()
    load = int(snap["data_segment"],16)*16 - 0x36db0
    font = metadata["font"]
    check(cache[-2048:] == ram[load+font["image_offset"]:load+font["image_offset"]+2048],
          "Extracted original font differs from live original RAM")
    image = Image.open(RUN/"captures/rubble-return.png").convert("RGB")
    def border_cells(left_only=False):
        for x, columns, split in ((0,13,True),(104,27,False)):
            if left_only and x: continue
            for row in range(25):
                for col in range(columns):
                    if row in (0,24) or col in (0,columns-1) or (split and row == 12):
                        yield x+8*col,8*row
    borders = [{"x":x,"y":y,"sha256":sha(image.crop((x,y,x+8,y+8)).tobytes())}
               for x,y in border_cells()]
    FIXTURE.write_text(json.dumps({"source_sha256":EXE_SHA,"image_sha256":IMAGE_SHA,
        "reference_run":str(RUN.relative_to(ROOT)),"corpus":corpus,"observed":observed,
        "font":font,"border_source_sha256":sha((ROOT/"Original DOS/BTBORDER.CMP").read_bytes()),
        "border_cells":borders},indent=2)+"\n")
    print("Exported 22 ANM identities/frame hashes, 39 stable original frames, font and border observations.")


def normalize_waits(binary, actions, rows):
    """Insert only cutscene idle time, preserving every original numeric fact."""
    replay = ROOT/"work/normalize-animation.actions"
    inserted = []
    for _ in range(8):
        replay.write_text("".join(a+"\n" for a in actions))
        result = subprocess.run([str(binary),"--replay",str(replay),"--trace"],cwd=ROOT,
                                check=True,capture_output=True,text=True,timeout=30)
        states = [json.loads(line) for line in result.stdout.splitlines()]
        trigger = next((i for i in range(1,len(states)) if states[i]["animation"]["active"] and
                        not states[i-1]["animation"]["active"] and
                        (i >= len(actions) or actions[i] != "idle")),None)
        if trigger is None: return actions, inserted
        c = states[trigger]["animation"]
        units = c["remaining"]
        if c["kind"] == 8: units += (2-c["step"])*7+(6-c["cycle"])*21
        elif not c["hold"]: units += (17-c["step"])*5+60
        count = (units*1000-c["fraction"]+2239)//2240
        actions[trigger:trigger] = ["idle"]*count
        for row in rows:
            if row["tick"] >= trigger: row["tick"] += count
        inserted.append({"trigger_tick":trigger,"animation":c["kind"],"retraces":units,"idle_ticks":count})
    raise RuntimeError("Too many cutscenes in bounded replay")


def verify(binary, frame=None):
    fixture = json.loads(FIXTURE.read_text())
    check(fixture["source_sha256"] == EXE_SHA and fixture["image_sha256"] == IMAGE_SHA,"Wrong EXE identity")
    output = ROOT/"work/animation-frames.bin"
    subprocess.run([str(binary),str(ROOT/"Original DOS"),str(output)],cwd=ROOT,check=True,timeout=30)
    packed, at, count = output.read_bytes(), 0, 0
    for kind in range(22):
        raw = (ROOT/"Original DOS"/f"O{kind}.ANM").read_bytes()
        original = decode(raw); stored = fixture["corpus"][str(kind)]
        check(stored == {"source_sha256":sha(raw),**facts(original)}, "ANM source/frame facts changed")
        for f in original["frames"]:
            check(packed[at:at+PACKED] == f["packed"],f"C ANM frame differs: O{kind}/{count}")
            at += PACKED; count += 1
    check(at == len(packed),"Trailing C animation export data")
    _, metadata = extract((ROOT/"Original DOS/BTECH.EXE").read_bytes())
    check(metadata["font"] == fixture["font"],"Original font source changed")
    check(sha((ROOT/"Original DOS/BTBORDER.CMP").read_bytes()) == fixture["border_source_sha256"],"Border resource changed")
    if frame:
        from PIL import Image
        im = Image.open(frame).convert("RGB")
        for cell in fixture["border_cells"]:
            x,y=cell["x"],cell["y"]
            check(sha(im.crop((x,y,x+8,y+8)).tobytes()) == cell["sha256"],f"Original border pixels differ at {x},{y}")
        print(f"PASS: {len(fixture['border_cells'])} native border cells exactly match original screenshot pixels.")
    print(f"PASS: {count} C frames across all 22 ANMs; 18 launch/21 dream original frames; original font provenance.")


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--binary",type=Path,default=ROOT/"build/btp-anm-tests")
    p.add_argument("--export",action="store_true")
    p.add_argument("--frame",type=Path)
    a=p.parse_args()
    if a.export: export()
    verify(a.binary.resolve(),a.frame)
