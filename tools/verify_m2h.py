#!/usr/bin/env python3
"""Verify the original paid Class/cooldown loop; export facts without asset text.

Screens establish modes/highlights, RAM establishes ranks/cash/countdowns, and
unpacked EXE/BLD bytes establish native strings and bounded script continuations.
No controlled campaign progress or course funding is injected in these routes.
"""
import argparse
import hashlib
import json
import struct
import subprocess
from pathlib import Path
from prepare_talk import extract, EXE_SHA, IMAGE_SHA
from verify_m2 import check, digest
from verify_m2f import original as bank_original, sources as bank_sources, z

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/"tests/fixtures"
RUNS = {"audit":"1791696349743334353","funded":"1791697254944153773"}
MENUS = (7,8,9,10,11,12,13,14,15,16,30)


def sources():
    image, _, _, bodies = bank_sources()
    cache, info = extract((ROOT/"Original DOS/BTECH.EXE").read_bytes())
    texts = [image[r["image_offset"]:r["image_offset"]+r["length"]] for r in info["strings"]]
    raw = (ROOT/"Original DOS/CITADEL.BLD").read_bytes()
    body = bytes(((v+41)&255)^233 for v in raw[2:])
    check(int.from_bytes(raw[:2],"little") == len(body) == 4328,"Wrong Citadel payload")
    return body, texts, info


def original(directory, label):
    snap, ram, row = bank_original(directory,label)
    ds, state = int(snap["data_segment"],16)*16, int(snap["state_segment"],16)*16
    menus = struct.unpack_from("<H",ram,ds+0x56b6)[0]*16
    row["menu_choices"] = {str(i):struct.unpack_from("<H",ram,menus+0x98+16*i)[0] for i in MENUS}
    row["skills"] = list(ram[state+0xc618:state+0xc61b])
    return snap, ram, row


def spec(row, body, texts):
    name = row["label"]
    if row["mode"] != "building": return None
    # Existing banking checkpoints are numeric regressions; their dialogue was
    # separately covered in M2f. These new text claims are confined to Citadel.
    if row["position"][0] != 69: return None
    result = z(body,6); status, pc, menu, phase = 1, 0xea, 8, 0
    if name == "sentry": result, status, pc, menu = z(body,244), 2, 0x1aa, None
    elif name == "katrina":
        result, status, pc, menu = b"".join(z(body,a) for a in (428,514,756)), 2, 0x349, None
    elif name.endswith("class-intro"):
        result, status, pc, menu = z(body,0xd03), 2, 0xe6c, None
    elif name.endswith(("class-menu","next-menu")):
        result = z(body,0xe72)+b"".join(str(75+125*r).encode() for r in row["skills"])
        pc, menu, phase = 0xf0f, 9, 1
    elif name.endswith(("class-choice","paid","next-refusal")):
        course = row["menu_choices"]["9"]
        trained = row["story_flags"][9] != 0
        rank = row["skills"][course]-int(trained)
        result = texts[43]+texts[46+rank]+texts[51+course]
        if not trained: result += texts[44] if rank == 4 else texts[45]+texts[54]
        status, pc, menu, phase = 2, 0xf75 if trained else 0x10da, None, 2
    elif name.endswith("completed"):
        result, status, pc, menu = z(body,0xf7a), 2, 0x10da, None
    elif name == "tuition-cooldown":
        result, status, pc, menu = z(body,0xf10), 2, 0xf55, None
    return {"status":status,"pc":pc,"menu":menu,"school_phase":phase,
        "length":len(result),"digest":digest(result),"sha256":hashlib.sha256(result).hexdigest()}


def mode(kind, label):
    if label in ("entry","bank-entry","tuition-citadel-entry"): return "entry-confirm"
    if label.startswith("approach") or label == "start" or "road" in label or "wait" in label or label.endswith("exit") or "west" in label or label == "tuition-south25" or label.startswith("tuition-clock"):
        return "local-exploration"
    return "building"


def export(kind, directory):
    script = ROOT/"tools"/("reference-class-"+kind+".json")
    commands = json.loads(script.read_text()); started = False
    actions, pending, rows, previous = [], [], [], None
    keys = {"Up":"up","Down":"down","Left":"left","Right":"right","Return":"accept",
        "space":"accept","BackSpace":"cancel","Escape":"clear",**{str(i):str(i) for i in range(10)}}
    for c in commands:
        if c == ["snapshot","start" if kind == "funded" else "approach25"]: started = True
        elif started and c[0] == "key": pending += [keys[k] for k in c[1:]]
        if not started or c[0] != "snapshot": continue
        label = c[1]; _, _, row = original(directory,label); row["mode"] = mode(kind,label)
        if not previous:
            actions += ["idle"]*(((249-row["loop_timer"])&255)*4)
        if previous:
            frames = (previous["loop_timer"]-row["loop_timer"])&255
            if previous["mode"] == "local-exploration":
                outdoor = len(pending)-int(row["mode"] == "entry-confirm")
                if row["mode"] == "building":
                    check(pending == ["down","up","accept"],"Unobserved mixed entry sequence")
                    outdoor = 1
                ticks = frames*4-outdoor
                check(ticks >= 0,"Incomplete outdoor frame interval")
                actions += ["idle"]*ticks+pending
            else:
                check(not frames or row["mode"] == "local-exploration","Indoor clock moved")
                actions += pending+["idle"]*(frames*4)
        row["tick"] = len(actions); rows.append(row); pending, previous = [], row
    body, texts, info = sources()
    for r in rows: r["text"] = spec(r,body,texts)
    fixture = {"source_sha256":EXE_SHA,"image_sha256":IMAGE_SHA,
        "citadel_sha256":hashlib.sha256(body).hexdigest(),"controlled":False,
        "reference_run":str(directory.relative_to(ROOT)),"input_script":str(script.relative_to(ROOT)),
        "checkpoints":rows}
    stem = "reference-class-"+kind
    (BASE/(stem+".json")).write_text(json.dumps(fixture,indent=2)+"\n")
    (BASE/(stem+".actions")).write_text("".join(a+"\n" for a in actions))
    print(f"Exported {stem}: {len(rows)} original checkpoints, {len(actions)} native ticks.")
    if kind == "funded":
        for name in ("tuition-funding","tuition-clock"):
            data = json.loads((directory/(name+"-frames.json")).read_text())
            check(data["kind"] == "read-only-outdoor-frames","Wrong frame provenance")
            lines = ["# phase,loop,rng[3],search[2],cursor[2],npc[8][7],cash,investments[3],cap\n"]
            for r in data["frames"]:
                values = [r["phase"],r["loop_timer"],*r["rng"],*r["search"],*r["cursor"]]
                for n in r["npcs"]: values += [*n["position"],*n["destination"],n["direction"],*n["pair"]]
                values += [r["credits"],*r["investments"],r["allowance_cap"]]
                check(len(values) == 70,"Wrong frame field count")
                lines.append(",".join(map(str,values))+"\n")
            (BASE/(name+"-frames.csv")).write_text("".join(lines))


def compare(binary, kind, live=None):
    stem = "reference-class-"+kind; path = BASE/(stem+".actions")
    fixture = json.loads((BASE/(stem+".json")).read_text())
    args = [str(binary),"--replay",str(path),"--trace"]
    result = subprocess.run(args,check=True,capture_output=True,text=True,cwd=ROOT,timeout=30)
    repeat = subprocess.run(args,check=True,capture_output=True,text=True,cwd=ROOT,timeout=30)
    check(result.stdout == repeat.stdout,"Non-deterministic class replay")
    states = [json.loads(line) for line in result.stdout.splitlines()]
    check(len(states) == len(path.read_text().splitlines())+1,"Incomplete class replay")
    body, texts, info = sources()
    check(fixture["source_sha256"] == EXE_SHA and fixture["image_sha256"] == IMAGE_SHA and
        fixture["citadel_sha256"] == hashlib.sha256(body).hexdigest() and not fixture["controlled"],"Wrong class provenance")
    for r in fixture["checkpoints"]:
        s = states[r["tick"]]; label = r["label"]
        check([s["x_half"],s["y_half"]] == r["position"],label+" position differs")
        for field in ("mode","story_flags","credits","investments","allowance_cap","equipment","skills","talk_result"):
            check(s[field] == r[field],f"{label} {field} differs: {s[field]} / {r[field]}")
        check(s["npc_loop_timer"] == r["loop_timer"],label+" frame counter differs")
        for i in MENUS:
            if label == "class-selected" and i == 8: continue # Transient screen highlight precedes RAM's accepted choice.
            check(s["menu_choices"][i] == r["menu_choices"][str(i)],f"{label} menu {i} differs")
        text = r["text"]
        if text:
            check(text == spec(r,body,texts),label+" source text specification differs")
            for key, field in (("status","script_status"),("pc","script_pc"),("length","text_length"),("digest","text_digest"),("school_phase","school_phase")):
                check(s[field] == text[key],f"{label} {field} differs: {s[field]} / {text[key]}")
            if text["menu"] is not None:
                highlight = 2 if label == "class-selected" else r["menu_choices"][str(text["menu"])]
                check(s["menu_id"] == text["menu"] and s["menu_selected"] == highlight,label+" menu/highlight differs")
        if live:
            snap, ram, actual = original(live,label)
            check(all(actual[k] == r[k] for k in actual),label+" recorded/live original projection differs")
            if text:
                check(ram.find(body) >= 0,label+" original Citadel payload not resident")
                load = int(snap["load_segment"],16)*16
                for a in info["strings"][43:]:
                    start = a["image_offset"]+load
                    check(hashlib.sha256(ram[start:start+a["length"]]).hexdigest() == a["sha256"],"Original tuition string differs")
    if kind == "funded":
        checkpoints = {r["label"]:states[r["tick"]] for r in fixture["checkpoints"]}
        paid, done, expired = [checkpoints[n] for n in ("tuition-paid","tuition-completed","tuition-next-menu")]
        check(paid["credits"] == 12 and paid["skills"] == [1,0,0] and paid["story_flags"][9] == 1,
            "Ordinary funding/first course did not complete")
        check(done["story_flags"][21] == 255 and expired["story_flags"][21] == 0 and
            checkpoints["tuition-next-refusal"]["credits"] == 27,"Cooldown/next-course refusal differs")
        check(all(s["story_flags"][0] == 0 for s in states),"Personal skills invented MechWarrior mission progress")
    print(f"PASS: {len(fixture['checkpoints'])} original {kind} Class/economy checkpoints, {len(states)-1} deterministic ticks, exact native/BLD text hashes and cooldown state.")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--binary",type=Path,default=ROOT/"build/btech-headless")
    p.add_argument("--export",choices=RUNS)
    p.add_argument("--reference-run",type=Path)
    p.add_argument("--native-log",type=Path)
    args = p.parse_args()
    if args.export:
        export(args.export,args.reference_run or ROOT/"work/reference-runs"/RUNS[args.export]); return
    for kind in RUNS: compare(args.binary.resolve(),kind,args.reference_run if kind == "funded" else None)
    if args.native_log:
        expected = (BASE/"reference-class-funded.actions").read_text().splitlines()+["idle"]*5
        check(args.native_log.read_text().splitlines() == expected,"Native class inputs differ")
        print("PASS: native SDL course inputs retain the entire ordinary funding/cooldown route.")


if __name__ == "__main__": main()
