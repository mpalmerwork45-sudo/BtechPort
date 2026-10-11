#!/usr/bin/env python3
"""Compare original mission, all goods and lounge facts; restart each new phase.

Export only numeric observations, input actions and text hashes. Mission waits
normalize the software delay to deterministic updates; exact DOS CPU timing and
its stack-local elapsed counter are outside this comparison. Controlled cash and
Rick occupancy are explicit preconditions, never ordinary campaign progress.
"""
import argparse
import binascii
import hashlib
import json
import struct
import subprocess
import tempfile
from pathlib import Path
from prepare_talk import extract, EXE_SHA, IMAGE_SHA
from verify_m2 import check, digest
from verify_m2f import z

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/"tests/fixtures"
RUNS = {"mission-pass":"1791702526057748887", "mission-fail":"1791700897500835555",
        "full-goods":"1791701039890663749", "lounge":"1791702226982563634",
        "diagonal-human":"1791703432794053744", "diagonal-mech":"1791703495815619813"}
MENUS = (7,12,13,14,15,16,17,18,19,24,30)
KEYS = {"Up":"up","Down":"down","Left":"left","Right":"right","Return":"accept",
        "space":"accept","BackSpace":"cancel","Home":"up-left","Prior":"up-right",
        "End":"down-left","Next":"down-right"}

def sources():
    _, info = extract((ROOT/"Original DOS/BTECH.EXE").read_bytes())
    from exepack import unpack
    image, _ = unpack((ROOT/"Original DOS/BTECH.EXE").read_bytes())
    texts = [image[r["image_offset"]:r["image_offset"]+r["length"]] for r in info["strings"]]
    bodies = {}
    for n in ("TRAINING","BARRACKS","LOUNGE","WEAPON","ARMOR"):
        raw = (ROOT/"Original DOS"/(n+".BLD")).read_bytes()
        bodies[n] = bytes(((v+41)&255)^233 for v in raw[2:])
        check(len(bodies[n]) == int.from_bytes(raw[:2],"little"),"Wrong original BLD length")
    return bodies, texts

def observation(directory, label):
    snap = json.loads((directory/(label+"-state.json")).read_text())
    ram = (directory/(label+"-ram.bin")).read_bytes()
    ds = int(snap["data_segment"],16)*16; state = int(snap["state_segment"],16)*16
    menus = struct.unpack_from("<H",ram,ds+0x56b6)[0]*16
    return {"label":label,"position":[v&127 for v in snap["cursor_raw"]],
        "story_flags":snap["story_state_bytes"][:23],"device":snap["story_state_bytes"][47],
        "recruitment":ram[state+0xd339],"talk_result":ram[state+0xd33a],
        "credits":struct.unpack_from("<I",ram,state+0xd370)[0],
        "allowance_cap":snap["allowance_cap"],"equipment":snap["equipment"],
        "skills":snap["skills"],"investments":snap["investments"],
        "menu_choices":{str(i):struct.unpack_from("<H",ram,menus+0x98+16*i)[0] for i in MENUS},
        "quiz_selected":struct.unpack_from("<H",ram,menus+0x98+16*37)[0],
        "loop_timer":snap["loop_timer"],"rng":snap["npc_rng"],
        "mech_frame":snap["sprite_frames"][0],"player_sprite":150+snap["sprite_frames"][4],"terrain":snap["heat"],
        "mount":snap["mount"]}

def mode(label, row):
    if label.startswith("diagonal-human-"): return "local-exploration"
    if label.startswith("diagonal-mech-"): return "training-mission"
    if label.endswith("entry"): return "entry-confirm"
    if label == "training-menu" or label.startswith("quiz-"): return "training-quiz"
    if label == "mission-start" or label.startswith(("mission-east","mission-south","mission-north","mission-west","mission-home","pass-out","pass-return")) or label == "pass-corner":
        return "building" if row["story_flags"][20] == 255 else "training-mission"
    if label in ("start","funded") or "walk" in label or "road" in label or label.endswith("exit"): return "local-exploration"
    return "building"

def text_spec(row, bodies, texts):
    label = row["label"]; result = None
    t, b, l = (bodies[n] for n in ("TRAINING","BARRACKS","LOUNGE"))
    if label == "training-menu": result = texts[55]
    elif label.startswith("quiz-"): result = texts[56]
    elif label == "mission-offer": result = b"".join(z(t,a) for a in (6,0x2d,0x12c,0x15d,0x1b2))
    elif label == "mission-briefing": result = z(t,0x22a)
    elif label == "mech-menu": result = z(t,0xa43)
    elif label == "pass-corner": result = texts[79]
    elif label in ("pass-result","pass-return107"):
        result = z(t,0xff1)+texts[80]+z(t,0x104e)
    elif label in ("mission-result","mission-home56"): result = z(t,0xab5)
    elif label in ("barracks-menu","sleep-menu","sleep-return","sleep-again"): result = z(b,6)
    elif label == "sleep-no-mission": result = z(b,0x9a)
    elif label.startswith("dream"):
        n=int(label[5:]); result = z(b,(0x24c,0x34f,0x45d,0x615,0x7b3,0x88d,0xa11)[n-1])
        if n == 7: result += z(b,0xa85)
    elif label == "sleep-again-return": result = z(b,0xb60)
    elif label in ("lounge-menu","rick-lounge-menu"): result = z(l,0xa)
    elif label in ("lounge-empty","lounge-talk"): result = texts[0]
    elif label.startswith("rick-scene"): result = z(l,(0xca,0x194,0x2f2,0x409,0x50c)[int(label[-1])-1])
    if result is None: return None
    return {"length":len(result),"digest":digest(result) if result else 0,
        "sha256":hashlib.sha256(result).hexdigest()}

def export(kind):
    directory = ROOT/"work/reference-runs"/RUNS[kind]
    commands = [json.loads(line)["command"] for line in (directory/"inputs.jsonl").read_text().splitlines()]
    bodies, texts = sources(); rows=[]; pending=[]; actions=[]; started=False; previous=None
    controlled=False; failure_wait=False
    for index,c in enumerate(commands):
        if c == ["snapshot","start"]: started=True
        if c[0] == "controlled-talk-context":
            if kind == "full-goods": break
            controlled=True
            rows=[]; actions=[]; pending=[]; previous=None
        if c[0] == "controlled-shop-cash":
            controlled=True; rows=[]; actions=[]; pending=[]; previous=None
        if not started: continue
        if c[0] in ("key","keys-fast"): pending += [KEYS[k] for k in c[1:]]
        if c[0] == "quiz-answer":
            answer=json.loads((directory/(c[1]+"-answer.json")).read_text())
            c=["snapshot",c[1]]
        else: answer=None
        if c[0] != "snapshot": continue
        label=c[1]
        row=observation(directory,label); row["mode"]=mode(label,row)
        # A final walking snapshot can already show the entrance prompt. It
        # precedes the named screenshot with no further gameplay input.
        if "walk" in label or "road" in label:
            for nxt in commands[index+1:]:
                if nxt[0] in ("key","keys-fast"): break
                if nxt[0] == "snapshot" and nxt[1].endswith("entry"):
                    row["mode"]="entry-confirm"; break
        if previous:
            frames=(previous["loop_timer"]-row["loop_timer"])&255
            if previous["mode"] == "local-exploration":
                outside=len(pending)-int(row["mode"] == "entry-confirm")
                idle=frames*4-outside; check(idle>=0,label+" outdoor frame interval missing")
                actions += ["idle"]*idle+pending
            else:
                actions += pending
                if row["mode"] == "local-exploration": actions += ["idle"]*(frames*4)
                else: check(not frames,label+" indoor clock advanced")
            if kind == "mission-fail" and label.startswith("mission-north") and not failure_wait:
                # Explicit deterministic normalization: original corner wait
                # produced a failure; this fixture supplies four timer updates.
                actions += ["idle"]*44; failure_wait=True
            if previous["mode"] == "training-mission" and row["mode"] == "building": actions += ["idle"]
        row["tick"]=len(actions); row["text"]=text_spec(row,bodies,texts)
        if answer:
            row["point"]=answer["point"]; row["answer"]=answer["answer"]
            pending=[KEYS[k] for k in answer["keys"]]
        else: pending=[]
        rows.append(row); previous=row
        if kind == "full-goods" and label == "lounge-exit": break
    fixture={"source_sha256":EXE_SHA,"image_sha256":IMAGE_SHA,
        "payload_sha256":{k:hashlib.sha256(v).hexdigest() for k,v in bodies.items()},
        "reference_run":str(directory.relative_to(ROOT)),"controlled":controlled,
        "initial":"cash-20000" if kind == "full-goods" else "rick-lounge" if controlled else "ordinary",
        "mission_time_scope":"input steps and bounded native waits; DOS CPU pacing/elapsed parity not claimed",
        "checkpoints":rows}
    (BASE/("reference-"+kind+".json")).write_text(json.dumps(fixture,indent=2)+"\n")
    (BASE/("reference-"+kind+".actions")).write_text("".join(a+"\n" for a in actions))
    print(f"Exported {kind}: {len(rows)} checkpoints / {len(actions)} actions.")

def run(binary, *args):
    r=subprocess.run([str(binary),*map(str,args)],cwd=ROOT,check=True,capture_output=True,text=True,timeout=30)
    return r.stdout

def rewrite_save(path, change):
    saved=bytearray(path.read_bytes()); payload=bytearray(saved[16:]); change(payload)
    saved[16:]=payload; struct.pack_into("<I",saved,8,binascii.crc32(payload)); path.write_bytes(saved)

def seed(binary, kind, tmp):
    if kind not in ("full-goods","lounge"): return []
    path=tmp/(kind+"-initial.btp"); run(binary,"--save",path)
    if kind == "full-goods":
        def cash(b): struct.pack_into("<I",b,224,20000); b[201]=0
        rewrite_save(path,cash)
    else:
        def position(b): struct.pack_into("<HH",b,12,17,90)
        rewrite_save(path,position)
        p=tmp/"enter.actions"; p.write_text("up\naccept\ndown\n")
        run(binary,"--load",path,"--replay",p,"--save",path)
        context=json.loads((BASE/"lounge-rick-context.json").read_text())
        def rick(b):
            b[128:144]=bytes(v for pair in context["npc_pairs"] for v in pair)
            b[146]=b[404]=context["talk_result"]; b[147]=b[403]=context["recruitment"]
            b[149]=1; b[150:224]=bytes(74); b[395:403]=bytes(8)
            b[37]=7 # The preceding ordinary Talk visit selected room 7.
        rewrite_save(path,rick)
    run(binary,"--load",path) # Apply the same C validation as an ordinary save.
    return ["--load",path]

def compare(binary, kind, tmp, restart=True):
    f=json.loads((BASE/("reference-"+kind+".json")).read_text())
    path=BASE/("reference-"+kind+".actions"); initial=seed(binary,kind,tmp)
    output=run(binary,*initial,"--replay",path,"--trace")
    check(output == run(binary,*initial,"--replay",path,"--trace"),kind+" replay is nondeterministic")
    states=[json.loads(line) for line in output.splitlines()]
    bodies,texts=sources()
    check(f["source_sha256"] == EXE_SHA and f["image_sha256"] == IMAGE_SHA and
        f["payload_sha256"] == {k:hashlib.sha256(v).hexdigest() for k,v in bodies.items()},"Wrong source identity")
    for row in f["checkpoints"]:
        s=states[row["tick"]]; label=kind+"/"+row["label"]
        check([s["x_half"],s["y_half"]] == row["position"],label+" position differs")
        for field in ("mode","story_flags","device","recruitment","talk_result","credits","allowance_cap","equipment","skills","investments"):
            check(s[field] == row[field],f"{label} {field}: {s[field]} / {row[field]}")
        for i in MENUS: check(s["menu_choices"][i] == row["menu_choices"][str(i)],label+f" selector {i} differs")
        if kind != "lounge": check(s["npc_loop_timer"] == row["loop_timer"],label+" outdoor clock differs")
        if "point" in row:
            check(s["quiz"]["point"] == row["point"] and s["quiz"]["selected"] == row["quiz_selected"],label+" quiz differs")
            check(s["npc_rng"] == row["rng"],label+" quiz RNG differs")
        if s["mode"] == "training-mission":
            check(s["player_sprite"] == row["mech_frame"],label+" loaned-mech gait differs")
            check(s["mission"]["terrain"] == row["terrain"],label+" terrain penalty differs")
        if row["label"].startswith("diagonal-human-"):
            check(s["player_sprite"] == row["player_sprite"],label+" human diagonal gait differs")
        text=row["text"]
        if text:
            check(text == text_spec(row,bodies,texts),label+" original text hash differs")
            check(s["text_length"] == text["length"] and s["text_digest"] == text["digest"],
                f"{label} native text differs: {s['text_length']} / {text['length']}")
    # Save and restart at every observed indoor or mission phase, then compare
    # the complete continuation through a bounded tail, including partial quiz.
    if restart:
        lines=path.read_text().splitlines(); prefix=tmp/"prefix.actions"; tail=tmp/"tail.actions"; slot=tmp/"restart.btp"
        for row in f["checkpoints"]:
            if row["mode"] not in ("building","training-quiz","training-mission") and not kind.startswith("diagonal-"): continue
            t=row["tick"]; end=min(t+24,len(lines))
            prefix.write_text("".join(a+"\n" for a in lines[:t])); tail.write_text("".join(a+"\n" for a in lines[t:end]))
            before=json.loads(run(binary,*initial,"--replay",prefix,"--save",slot))
            check(before == json.loads(run(binary,"--load",slot)),kind+" restarted state differs")
            check(json.loads(run(binary,"--load",slot,"--replay",tail)) == states[end],kind+" restarted continuation differs")
    print(f"PASS: {kind}, {len(f['checkpoints'])} original checkpoints, text hashes, replay and new-phase restart.")
    return initial,states

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--binary",type=Path,default=ROOT/"build/btech-headless")
    p.add_argument("--export",action="store_true"); p.add_argument("--scenario",choices=RUNS)
    p.add_argument("--normalize-animations",action="store_true")
    a=p.parse_args(); kinds=[a.scenario] if a.scenario else list(RUNS)
    if a.export:
        for kind in kinds: export(kind)
    if a.normalize_animations:
        from verify_animations import normalize_waits
        bodies,texts=sources()
        for kind in kinds:
            path=BASE/("reference-"+kind+".json"); f=json.loads(path.read_text())
            if "cutscene_waits" in f: continue
            replay=BASE/("reference-"+kind+".actions")
            actions,waits=normalize_waits(a.binary.resolve(),replay.read_text().splitlines(),f["checkpoints"])
            f["cutscene_waits"]=waits
            for row in f["checkpoints"]:
                if row["label"] == "dream7": row["text"]=text_spec(row,bodies,texts)
            path.write_text(json.dumps(f,indent=2)+"\n")
            replay.write_text("".join(v+"\n" for v in actions))
    with tempfile.TemporaryDirectory(prefix="m2j-",dir=ROOT/"work") as directory:
        for kind in kinds: compare(a.binary.resolve(),kind,Path(directory))
if __name__ == "__main__": main()
