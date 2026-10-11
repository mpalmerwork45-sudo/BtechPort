#!/usr/bin/env python3
"""Ordinary first pass -> rubble -> tired refusal -> sleep -> third briefing.

The original run uses ordinary keys and read-only RAM. Exported fixtures contain
numeric state and text hashes only. Explicit input/pause and retrace normalization
does not assert DOS keyboard-buffer or wall-clock equivalence.
"""
import argparse
import hashlib
import json
import struct
import tempfile
from pathlib import Path
from verify_m2j import observation, sources, text_spec, mode, run, rewrite_save, KEYS, MENUS
from verify_m2f import z
from verify_m2 import check, digest
from prepare_talk import EXE_SHA, IMAGE_SHA

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"tests/fixtures"
RUN=ROOT/"work/reference-runs/1791705480602565515"
FIXTURE=BASE/"reference-rubble-story.json"
ACTIONS=BASE/"reference-rubble-story.actions"


def commands(directory):
    """Expand route-internal keys/snapshots without inventing observations."""
    for line in (directory/"inputs.jsonl").read_text().splitlines():
        c=json.loads(line)["command"]
        if c[0] == "route":
            label,kind=c[1:3]; route=json.loads((directory/(label+"-route.json")).read_text())
            yield ["snapshot",label+"-begin","training-mission" if kind == "mech" else "local-exploration"]
            for i,key in enumerate(route["keys"]):
                # This original Down was consumed solely to dismiss the pickup
                # pause, after an earlier Return was flushed by the DOS delay.
                yield ["logical-key","accept" if label == "rubble-return" and not i else KEYS[key]]
                if (i+1)%8 == 0 or i+1 == len(route["keys"]):
                    stage="training-mission" if kind == "mech" else "entry-confirm" if i+1 == len(route["keys"]) else "local-exploration"
                    yield ["snapshot",f"{label}-walk{i+1}",stage]
            yield ["snapshot",label,"training-mission" if kind == "mech" else "entry-confirm"]
        elif c[0] == "wait-cooldown":
            yield ["snapshot",c[1]+"-begin","local-exploration"]
            yield ["snapshot",c[1],"local-exploration"]
        else: yield c


def screen_mode(label, row, specified=None):
    if specified:
        if specified == "training-mission" and row["story_flags"][0] == 2 and row["story_flags"][20] == 255: return "building"
        return specified
    if "quiz-intro" in label or "quiz-" in label: return "training-quiz"
    if label in ("rubble-outside","rubble-success-exit","third-tired-exit","rest-exit"): return "local-exploration"
    if label in ("rubble-launch","rubble-carrying"): return "training-mission"
    if label.startswith(("rubble-","third-","rest-")): return "building"
    return mode(label,row)


def text(row,bodies,texts):
    label=row["label"]; t,b=bodies["TRAINING"],bodies["BARRACKS"]
    result=None
    if "quiz-intro" in label: result=texts[55]
    elif "quiz-" in label: result=texts[56]
    elif label in ("rubble-offer","third-tired-offer","third-rested-offer"):
        result=b"".join(z(t,a) for a in (6,0xe3,0x12c,0x167 if label == "rubble-offer" else 0x172,0x1b2))
    elif label == "rubble-briefing": result=z(t,0x40f)
    elif label == "third-tired-briefing": result=z(t,0x4f8)
    elif label == "third-rested-briefing": result=z(t,0x5b7)
    elif label in ("rubble-mech-menu","third-combat-mech-menu"): result=z(t,0xa43)
    elif row["mode"] == "building" and label.startswith("rubble-return"): result=z(t,0x10b4)
    elif label in ("rest-menu","rest-return"): result=z(b,6)
    elif label.startswith("rest-dream"): result=z(b,(0x24c,0x34f,0x45d,0x615,0x7b3,0x88d)[int(label[-1])-1])
    elif label == "rest-wake": result=z(b,0xa11)+z(b,0xa85)
    elif row["mode"] == "training-mission" and label.startswith("rubble-") and row["position"] == [108,36]: result=texts[86]
    if result is None: return text_spec(row,bodies,texts)
    return {"length":len(result),"digest":digest(result) if result else 0,"sha256":hashlib.sha256(result).hexdigest()}


def export(binary):
    bodies,texts=sources(); actions=[]; pending=[]; rows=[]; waits=[]; previous=None; started=False
    expanded=list(commands(RUN))
    for index,c in enumerate(expanded):
        if c == ["snapshot","start"]: started=True
        if not started: continue
        if c[0] in ("key","keys-fast"): pending += [KEYS[k] for k in c[1:]]
        elif c[0] == "logical-key": pending.append(c[1])
        if c[0] == "quiz-answer":
            answer=json.loads((RUN/(c[1]+"-answer.json")).read_text()); c=["snapshot",c[1]]
        else: answer=None
        if c[0] != "snapshot": continue
        label=c[1]; row=observation(RUN,label); row["mode"]=screen_mode(label,row,c[2] if len(c)>2 else None)
        if "walk" in label and len(c) == 2:
            for nxt in expanded[index+1:]:
                if nxt[0] in ("key","keys-fast","logical-key","quiz-answer"): break
                if nxt[0] == "snapshot" and nxt[1].endswith("entry"):
                    row["mode"]="entry-confirm"; break
        if previous:
            frames=(previous["loop_timer"]-row["loop_timer"])&255
            if previous["label"] == "rubble-pickup" and label == "rubble-carrying":
                check(pending == ["accept"],"Unexpected original pickup input")
                pending=["idle"] # Original Return was discarded by its delay/input flush.
            if previous["mode"] == "local-exploration":
                outdoor=len(pending)-int(row["mode"] == "entry-confirm")
                idle=frames*4-outdoor; check(idle>=0,label+" missing outdoor frame interval")
                actions += ["idle"]*idle+pending
            else:
                actions += pending
                if row["mode"] == "local-exploration": actions += ["idle"]*(frames*4)
                else: check(not frames,label+" indoor clock advanced")
            if previous["mode"] == "training-mission" and row["mode"] == "building": actions.append("idle")
        if label in ("mission-start","rubble-launch","rest-wake"):
            kind=8 if label == "rest-wake" else 0
            retraces=147 if kind else 200
            count=(retraces*1000+2239)//2240
            waits.append({"trigger_tick":len(actions),"animation":kind,"retraces":retraces,"idle_ticks":count})
            actions += ["idle"]*count
        ram=(RUN/(label+"-ram.bin")).read_bytes(); snap=json.loads((RUN/(label+"-state.json")).read_text())
        state=int(snap["state_segment"],16)*16
        row["mech_skills"]=list(ram[state+0xc61b:state+0xc61d])
        if row["mode"] == "training-mission" and label.startswith("rubble-"):
            row["rubble_target"]=[55,17]
            ds=int(snap["data_segment"],16)*16
            p=struct.unpack_from("<H",ram,ds+0x5470)[0]*16+0x101d
            x,y=row["rubble_target"]; row["rubble_tile"]=ram[p+(y&0x78)*64+(y&7)*8+(x&0x78)*8+(x&7)]
        row["tick"]=len(actions); row["text"]=text(row,bodies,texts)
        if answer:
            row["point"]=answer["point"]; row["answer"]=answer["answer"]; pending=[KEYS[k] for k in answer["keys"]]
        else: pending=[]
        rows.append(row); previous=row
    fixture={"source_sha256":EXE_SHA,"image_sha256":IMAGE_SHA,
        "payload_sha256":{k:hashlib.sha256(v).hexdigest() for k,v in bodies.items()},
        "reference_run":str(RUN.relative_to(ROOT)),"initial":"ordinary-original-run","cutscene_waits":waits,
        "rng_preconditions":[{"label":r["label"],"tick":r["tick"],"rng":r["rng"]} for r in rows
            if r["label"] in ("rubble-quiz-intro","third-tired-quiz-intro","third-rested-quiz-intro")],
        "comparison_scope":"State/text/mission comparison with three explicit original RNG checkpoint prerequisites; unseeded long-wait NPC/RNG parity differs",
        "input_normalization":["Early Return after rubble pickup maps to idle: DOS discarded it",
            "First Down on return route maps to accept: DOS used it only to acknowledge pickup"],
        "timing_scope":"outdoor frame counter and fixed-step retraces; DOS CPU/keyboard-buffer timing excluded",
        "checkpoints":rows}
    FIXTURE.write_text(json.dumps(fixture,indent=2)+"\n"); ACTIONS.write_text("".join(a+"\n" for a in actions))
    print(f"Exported {len(rows)} ordinary rubble/story checkpoints and {len(actions)} actions.")


def canonical_trace(binary,f,tmp):
    """Resume the original RNG prerequisite at bounded quiz checkpoints only.

    No position, credit, story, skill, inventory or mission state is changed.
    Long outdoor idle timing does not yet preserve all NPC arrival RNG draws.
    An independent ordinary native replay tests playability without these seeds.
    """
    lines=ACTIONS.read_text().splitlines(); states=[]; contexts=[]; begin=0; initial=[]
    for i,point in enumerate(f["rng_preconditions"]+[None]):
        end=point["tick"] if point else len(lines)
        replay=tmp/f"leg-{i}.actions"; replay.write_text("\n".join(lines[begin:end])+"\n")
        slot=tmp/f"context-{i}.btp"
        leg=[json.loads(v) for v in run(binary,*initial,"--replay",replay,"--trace","--save",slot).splitlines()]
        states += leg if not states else leg[1:]
        if point:
            rewrite_save(slot,lambda b: b.__setitem__(slice(153,156),bytes(point["rng"])))
            states[-1]=json.loads(run(binary,"--load",slot))
            contexts.append((end,slot)); initial=["--load",slot]; begin=end
    return states,contexts


def verify(binary):
    f=json.loads(FIXTURE.read_text()); bodies,texts=sources()
    with tempfile.TemporaryDirectory(prefix="m2kl-trace-",dir=ROOT/"work") as directory:
        tmp=Path(directory); states,_=canonical_trace(binary,f,tmp)
        again,_=canonical_trace(binary,f,tmp)
        check(states == again,"Checkpoint-conditioned replay is nondeterministic")
    check(f["source_sha256"] == EXE_SHA and f["image_sha256"] == IMAGE_SHA and
          f["payload_sha256"] == {k:hashlib.sha256(v).hexdigest() for k,v in bodies.items()},"Wrong source identity")
    for row in f["checkpoints"]:
        s=states[row["tick"]]; label=row["label"]
        check([s["x_half"],s["y_half"]] == row["position"],f"{label} position {s['x_half']},{s['y_half']} / {row['position']}")
        for field in ("mode","story_flags","device","recruitment","talk_result","credits","allowance_cap","equipment","skills","mech_skills","investments"):
            check(s[field] == row[field],f"{label} {field}: {s[field]} / {row[field]}")
        for i in MENUS: check(s["menu_choices"][i] == row["menu_choices"][str(i)],label+f" selector {i} differs")
        check(s["npc_loop_timer"] == row["loop_timer"],label+" outdoor counter differs")
        if "point" in row:
            check(s["quiz"]["point"] == row["point"] and s["quiz"]["selected"] == row["quiz_selected"],label+" quiz differs")
            check(s["npc_rng"] == row["rng"],label+" quiz RNG differs")
        if row["mode"] == "training-mission":
            check(s["player_sprite"] == row["mech_frame"]+(146 if row["story_flags"][2] else 0),label+" loaned-mech gait differs")
            check(s["mission"]["terrain"] == row["terrain"],label+" terrain differs")
        if "rubble_target" in row:
            check(s["mission"]["rubble_target"] == row["rubble_target"] and s["mission"]["rubble_tile"] == row["rubble_tile"],label+" rubble location/tile differs")
        if row["text"]:
            check(row["text"] == text(row,bodies,texts),label+" original text source changed")
            check(s["text_length"] == row["text"]["length"] and s["text_digest"] == row["text"]["digest"],f"{label} text {s['text_length']} / {row['text']['length']}")
    lines=ACTIONS.read_text().splitlines()
    with tempfile.TemporaryDirectory(prefix="m2kl-",dir=ROOT/"work") as directory:
        tmp=Path(directory); prefix=tmp/"prefix.actions"; tail=tmp/"tail.actions"; slot=tmp/"restart.btp"
        _,contexts=canonical_trace(binary,f,tmp)
        ticks={row["tick"] for row in f["checkpoints"] if row["mode"] in ("building","training-quiz","training-mission")}
        # Include mid-animation states, independently of original polling timing.
        for wait in f["cutscene_waits"]: ticks.update(wait["trigger_tick"]+n for n in (1,10,30))
        for tick in sorted(ticks):
            begin=0; initial=[]
            for context_tick,context in contexts:
                if context_tick <= tick: begin=context_tick; initial=["--load",context]
            next_context=next((t for t,_ in contexts if t > tick),len(lines)+1)
            end=min(tick+32,len(lines),next_context-1)
            prefix.write_text("".join(v+"\n" for v in lines[begin:tick])); tail.write_text("".join(v+"\n" for v in lines[tick:end]))
            check(json.loads(run(binary,*initial,"--replay",prefix,"--save",slot)) == states[tick],"Save prefix differs")
            check(json.loads(run(binary,"--load",slot)) == states[tick],"Restarted rubble/animation state differs")
            check(json.loads(run(binary,"--load",slot,"--replay",tail)) == states[end],"Restarted rubble/animation continuation differs")
        tick=next(r["tick"] for r in f["checkpoints"] if r["label"] == "rubble-return")
        begin,context=contexts[0]; prefix.write_text("\n".join(lines[begin:tick])+"\n")
        run(binary,"--load",context,"--replay",prefix,"--frame",ROOT/"work/rubble-result.ppm")
    print(f"PASS: {len(f['checkpoints'])} original first-pass/rubble/rest/third-briefing state/text checkpoints under three explicit RNG prerequisites; {len(ticks)} phase/animation restarts.")


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--binary",type=Path,default=ROOT/"build/btech-headless")
    p.add_argument("--export",action="store_true"); a=p.parse_args()
    if a.export: export(a.binary.resolve())
    verify(a.binary.resolve())
