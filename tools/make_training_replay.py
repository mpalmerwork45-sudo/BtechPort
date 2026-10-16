#!/usr/bin/env python3
"""Record an ordinary native two-mission/rest route using only logical inputs.

There are no state/RNG edits. Quiz answers come from the original EXE table;
the walking route follows the objective actually selected by the native RNG.
This is a playability replay, separate from original checkpoint comparisons.
"""
import argparse
import json
import struct
import tempfile
from collections import deque
from pathlib import Path
from exepack import unpack
from verify_m2j import run, KEYS, sources
from verify_m2f import z
from verify_m2 import check, digest
from prepare_talk import EXE_SHA, IMAGE_SHA, DS

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"tests/fixtures"
PATH=BASE/"ordinary-rubble-story.actions"
FACTS=BASE/"ordinary-rubble-story.json"


def generate(binary):
    image,info=unpack((ROOT/"Original DOS/BTECH.EXE").read_bytes())
    check(info["input_sha256"] == EXE_SHA and info["image_sha256"] == IMAGE_SHA,"Wrong EXE identity")
    answers=struct.unpack_from("<10H",image,DS+0x28ec)
    raw=(ROOT/"Original DOS/MAP1.MTP").read_bytes()[541:]
    def tile(x,y):
        return 255 if not 0 <= x < 64 or not 0 <= y < 64 else raw[(y&0x78)*64+(y&7)*8+(x&0x78)*8+(x&7)]
    actions=[]; checkpoints=[]
    with tempfile.TemporaryDirectory(prefix="ordinary-training-",dir=ROOT/"work") as directory:
        tmp=Path(directory); replay=tmp/"leg.actions"; slot=tmp/"state.btp"; state=None
        def advance(leg):
            nonlocal state
            replay.write_text("".join(a+"\n" for a in leg))
            state=json.loads(run(binary,*([] if state is None else ["--load",slot]),"--replay",replay,"--save",slot))
            actions.extend(leg)
        def note(label,**expected):
            row={"label":label,"tick":len(actions),"expected":expected}
            for field,value in expected.items(): check(state[field] == value,label+" unexpected "+field)
            checkpoints.append(row)
        def quiz():
            check(state["mode"] == "training-quiz","Expected ordinary quiz entry")
            advance(["accept"])
            for _ in range(3):
                check(state["quiz"]["phase"] == 2,"Expected quiz question")
                wanted=answers[state["quiz"]["point"]]
                count=(wanted-state["quiz"]["selected"])%20
                advance(["down"]*count+["accept"])
            check(state["mode"] == "building" and state["script_status"] == 6,"Ordinary quiz did not reach mission offer")
        def human(label):
            route=json.loads((ROOT/"work/reference-runs/1791705480602565515"/(label+"-route.json")).read_text())
            advance([KEYS[k] for k in route["keys"]]+["accept"])
        def mech(targets,avoid_return=False):
            start=(state["x_half"],state["y_half"]); parent={start:None}; queue=deque([start]); goal=None
            while queue:
                p=queue.popleft()
                if p in targets: goal=p; break
                for action,dx,dy in (("up",0,-1),("right",1,0),("down",0,1),("left",-1,0)):
                    q=p[0]+dx,p[1]+dy; x,y=q
                    if q in parent or not 0 <= x < 126 or not 2 <= y < 128: continue
                    if tile(x//2,(y-2)//2) >= 85 or tile(x//2+1,(y-2)//2) >= 85: continue
                    if avoid_return and x <= 60 and 73 <= y <= 79: continue
                    parent[q]=(p,action); queue.append(q)
            check(goal is not None,"No native rubble route")
            leg=[]
            while parent[goal] is not None:
                goal,action=parent[goal]; leg.append(action)
            advance(list(reversed(leg)))
        source=json.loads((BASE/"reference-rubble-story.json").read_text())
        end=next(r["tick"] for r in source["checkpoints"] if r["label"] == "rubble-outside")
        original=(BASE/"reference-rubble-story.actions").read_text().splitlines()
        # Reuse the observed walking route, but answer the questions actually
        # drawn now that each movement key advances the original RNG once.
        intro=next(r["tick"] for r in source["checkpoints"] if r["label"]=="training-menu")
        offer=next(r["tick"] for r in source["checkpoints"] if r["label"]=="mission-offer")
        launch=next(r["tick"] for r in source["checkpoints"] if r["label"]=="mission-start")
        advance(original[:intro]);quiz();advance(original[offer:launch])
        note("first-mech",mode="training-mission")
        advance(original[launch:end])
        note("first-success",mode="local-exploration",allowance_cap=150,mech_skills=[0,0])
        advance(["idle"]*((state["story_flags"][20]*1100+223)//224)); human("rubble-entry"); quiz()
        advance(["accept","accept","down","accept","idle"])
        note("rubble-animation",mode="training-mission")
        advance(["idle"]*89)
        check(state["mission"]["assignment"] == 1 and not state["animation"]["active"],"Second mission did not launch")
        rx,ry=state["mission"]["rubble_target"]
        mech({(2*rx-2,2*ry+2),(2*rx,2*ry+2)},True)
        note("rubble-pickup",mode="training-mission")
        check(state["mission"]["phase"] == 6 and state["mission"]["carrying"] == 1,"Rubble pickup failed")
        advance(["accept"]); note("rubble-carrying",mode="training-mission")
        mech({(60,79)}); advance(["idle"])
        note("rubble-result",mode="building",allowance_cap=250,mech_skills=[0,1])
        check(state["story_flags"][0] == 2 and state["story_flags"][1] == 1,"Second result did not advance story")
        advance(["accept"]+["idle"]*1253)
        human("third-entry"); quiz(); advance(["accept"])
        note("third-tired",mode="building",allowance_cap=250)
        check(state["story_flags"][19] == 0,"Rest gate was bypassed")
        advance(["accept"]); human("rest-entry")
        advance(["down"]*((1-state["menu_choices"][19])%2)+["accept"])
        for _ in range(8):
            if state["animation"]["active"]: break
            advance(["accept"])
        check(state["animation"]["active"] == 1,"Ordinary sleep did not play dream")
        advance(["idle"]*10); note("dream-animation",mode="building")
        advance(["idle"]*56); note("rest-wake",mode="building")
        check(state["story_flags"][19] == 1 and state["story_flags"][20] == 0,"Sleep did not clear gate/cooldown")
        advance(["accept","up","accept"]); human("third-rested-entry"); quiz()
        advance(["accept"]); note("third-rested",mode="building",allowance_cap=250,mech_skills=[0,1])
        advance(["accept"]); note("third-mech-menu",mode="building")
        check(state["menu_id"] == 7,"Third weapons assignment did not reach loan menu")
    PATH.write_text("".join(a+"\n" for a in actions))
    FACTS.write_text(json.dumps({"kind":"ordinary-native-playability","source_sha256":EXE_SHA,
        "image_sha256":IMAGE_SHA,"state_edits":False,"scope":"Input-only route; native quest outcomes, not long-wait DOS NPC/RNG equivalence",
        "native_rubble_target":[rx,ry],"checkpoints":checkpoints},indent=2)+"\n")
    print(f"Generated {len(actions)} ordinary native actions, no state/RNG edits; rubble at {rx},{ry}.")


def verify(binary):
    f=json.loads(FACTS.read_text()); states=[json.loads(l) for l in run(binary,"--replay",PATH,"--trace").splitlines()]
    stages={row["label"]:states[row["tick"]] for row in f["checkpoints"]}
    for row in f["checkpoints"]:
        state=states[row["tick"]]
        for field,value in row["expected"].items(): check(state[field] == value,row["label"]+" "+field+" differs")
    pickup=stages["rubble-pickup"]; carried=stages["rubble-carrying"]
    check(pickup["mission"]["phase"] == 6 and carried["mission"]["phase"] == 1 and
          pickup["mission"]["carrying"] == carried["mission"]["carrying"] == 1 and
          pickup["mission"]["rubble_target"] == f["native_rubble_target"] and
          carried["mission"]["rubble_tile"] != 80,"Ordinary rubble pickup/carrying differs")
    check(stages["rubble-result"]["story_flags"][:2] == [2,1] and
          stages["third-tired"]["story_flags"][19] == 0 and
          stages["rest-wake"]["story_flags"][19] == stages["third-rested"]["story_flags"][19] == 1,
          "Ordinary mission/rest gates differ")
    bodies,_=sources()
    for label,resource,offsets in (("rubble-result","TRAINING",(0x10b4,)),
                                  ("third-tired","TRAINING",(0x4f8,)),
                                  ("third-rested","TRAINING",(0x5b7,)),
                                  ("rest-wake","BARRACKS",(0xa11,0xa85))):
        text=b"".join(z(bodies[resource],offset) for offset in offsets); state=stages[label]
        check(state["text_length"] == len(text) and state["text_digest"] == digest(text),
              label+" ordinary result/briefing text differs from original BLD")
    check(states[-1]["story_flags"][0] == 2 and states[-1]["story_flags"][19] == 1 and
          states[-1]["menu_id"] == 7,"Ordinary native progression did not reach rested third assignment")
    with tempfile.TemporaryDirectory(prefix="ordinary-dream-",dir=ROOT/"work") as directory:
        tick=next(row["tick"] for row in f["checkpoints"] if row["label"] == "rest-wake")
        prefix=Path(directory)/"wake.actions"
        prefix.write_text("\n".join(PATH.read_text().splitlines()[:tick])+"\n")
        run(binary,"--replay",prefix,"--frame",ROOT/"work/rest-wake.ppm")
    print(f"PASS: ordinary native two-mission/rest/third-briefing input-only progression, {len(states)-1} ticks.")


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--binary",type=Path,default=ROOT/"build/btech-headless")
    p.add_argument("--generate",action="store_true");a=p.parse_args()
    if a.generate: generate(a.binary.resolve())
    verify(a.binary.resolve())
