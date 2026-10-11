#!/usr/bin/env python3
"""Original ComStar trades/economy and both shops' empty/occupied Talk.

Numeric observations, input actions and text hashes only belong in fixtures.
Occupied shop fixtures explicitly isolate the handler; their arrival is not
claimed. Native route waits match the observed outdoor frame counter, without
claiming intermediate NPC route positions or wall-clock/pixel equality.
"""
import argparse
import hashlib
import json
import struct
import subprocess
from pathlib import Path
from exepack import unpack
from prepare_talk import BANK_OFFSETS, DS, EXE_SHA, IMAGE_SHA
from verify_m2 import check, digest

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "tests/fixtures"
MENUS = (7,8,10,11,12,13,14,15,16,30)
RUNS = {"bank":"1791693440826188406", "bank-rates":"1791693786677767965",
        "armor-talk":"1791693440826188386", "weapon-talk":"1791693440826530230"}


def sources():
    image, info = unpack((ROOT/"Original DOS/BTECH.EXE").read_bytes())
    check(info["input_sha256"] == EXE_SHA and info["image_sha256"] == IMAGE_SHA,"Wrong original executable")
    addresses = [DS+p for p in (0x16de,0x170e,0x1728,0x172d,0x1761,0x178f)]
    for at in range(0x4e32,0x4e5e,4):
        off, seg = struct.unpack_from("<HH",image,DS+at); addresses.append(seg*16+off)
    addresses += [DS+p for p in BANK_OFFSETS]
    for at in range(0x4e7e,0x4e8a,4):
        off, seg = struct.unpack_from("<HH",image,DS+at); addresses.append(seg*16+off)
    texts = [image[a:image.index(0,a)] for a in addresses]
    bodies = {}
    for name in ("COMSTAR","ARMOR","WEAPON"):
        raw = (ROOT/"Original DOS"/(name+".BLD")).read_bytes()
        bodies[name] = bytes(((b+41)&255)^233 for b in raw[2:])
        check(len(bodies[name]) == int.from_bytes(raw[:2],"little"),"BLD size mismatch")
    return image, addresses, texts, bodies


def original(directory, label):
    s = json.loads((directory/(label+"-state.json")).read_text())
    ram = (directory/(label+"-ram.bin")).read_bytes()
    ds, state = int(s["data_segment"],16)*16, int(s["state_segment"],16)*16
    menu = struct.unpack_from("<H",ram,ds+0x56b6)[0]*16
    number = struct.unpack_from("<H",ram,ds+0x5574)[0]*16+0x12
    return s, ram, {"label":label,"position":[v&127 for v in s["cursor_raw"]],
        "story_flags":s["story_state_bytes"][:23],"shop_refusal":s["story_state_bytes"][39],
        "credits":struct.unpack_from("<I",ram,state+0xd370)[0],
        "investments":list(struct.unpack_from("<3I",ram,state+0xd374)),
        "allowance_cap":s["allowance_cap"],"equipment":s["equipment"],
        "menu_choices":{str(i):struct.unpack_from("<H",ram,menu+0x98+16*i)[0] for i in MENUS},
        "talk_selected":struct.unpack_from("<H",ram,menu+0x98+16*20)[0],
        "talk_result":ram[state+0xd33a],
        "npc_pairs":[list(ram[state+0xd398+26*i:state+0xd39a+26*i]) for i in range(8)],
        "loop_timer":s["loop_timer"],
        "number_input":ram[number:number+8].split(b"\0",1)[0].decode("ascii")}


def z(body, at):
    return body[at:body.index(0,at)]


def specification(row, texts, bodies):
    label = row["label"]
    if row["mode"] != "building": return None
    resource = "COMSTAR" if label.startswith("bank-") else "ARMOR" if label.startswith("armor-") else "WEAPON"
    body = bodies[resource]
    spec = {"resource":resource,"status":1,"pc":0x1b6 if resource == "COMSTAR" else 0xef if resource == "ARMOR" else 0xe8,
            "menu":10 if resource == "COMSTAR" else 12 if resource == "ARMOR" else 30,"talk_phase":0,"bank_phase":0}
    parts = [z(body,6 if resource == "COMSTAR" else 10)]
    if resource != "COMSTAR":
        slot = 4 if resource == "ARMOR" else 3
        if label.endswith("talk-empty") or label.endswith(("talk-menu","done-selected","talk-again","second-selected","second-reply","first-reply")):
            spec.update(status=5,pc=0xa99 if slot == 4 else 0x1606,menu=None)
            if label.endswith("talk-empty"): spec["talk_phase"] = 1; parts = [texts[0]]
            elif label.endswith(("second-reply","first-reply")):
                actor = 4 if label.endswith("second-reply") else 1
                destination = row["npc_pairs"][actor][0]&7
                names = (ROOT/"Original DOS/MAP1.MTP").read_bytes()
                spec.update(talk_phase=3,talk_actor=actor)
                parts = [texts[3],texts[6+slot],texts[4],names[133+16*destination:149+16*destination].split(b"\0",1)[0],texts[5]]
            else:
                names = (ROOT/"Original DOS/MAP1.MTP").read_bytes()
                spec["talk_phase"] = 2
                parts = [texts[1]]+[names[5+16*i:21+16*i].split(b"\0",1)[0]+b"\r" for i in (1,4)]+[texts[2]]
        result = b"".join(parts)
    elif label == "bank-intro":
        spec.update(status=2,pc=0x2cf,menu=None); result = z(body,0x1b8)
    elif label in ("bank-menu","bank-reentry-menu"):
        result = b"".join(parts)
    elif label == "bank-change":
        spec.update(pc=0x380,menu=7); result = z(body,0x34c)
    elif label in ("bank-invest-menu","bank-sell-menu","bank-invest-amount","bank-sell-amount","bank-buy-again","bank-zero-amount",
                    "bank-invested","bank-sold","bank-buy-clipped","bank-buy-no-cash","bank-sell-not-owned","bank-zero-sale",
                    "bank-sell-clipped","bank-sell-no-stock","bank-nasdiv-buy","bank-bakphar-buy"):
        buy = label in ("bank-invest-menu","bank-invest-amount","bank-buy-again","bank-invested","bank-buy-clipped","bank-buy-no-cash","bank-nasdiv-buy","bank-bakphar-buy")
        message = label in ("bank-invested","bank-sold","bank-buy-clipped","bank-buy-no-cash","bank-sell-not-owned","bank-zero-sale","bank-sell-clipped","bank-sell-no-stock","bank-nasdiv-buy","bank-bakphar-buy")
        menu = label in ("bank-invest-menu","bank-sell-menu")
        spec.update(status=2 if message else 5,pc=0x2cf if message else 0x382 if buy else 0x387,
                    menu=None,bank_phase=3 if message else 1 if menu else 2)
        if label in ("bank-buy-no-cash","bank-sell-no-stock"):
            result = z(body,0x34c)+texts[29 if buy else 18]
        else:
            result = texts[30 if buy else 19]+b"".join(texts[40:43])
            if label == "bank-sell-not-owned": result += texts[28]
            elif not menu:
                # Available balance is the value shown BEFORE the transaction.
                available = {"bank-invest-amount":35,"bank-buy-again":12,"bank-sell-amount":30,"bank-zero-amount":35,
                    "bank-invested":35,"bank-sold":30,"bank-buy-clipped":12,"bank-zero-sale":35,"bank-sell-clipped":35,
                    "bank-nasdiv-buy":5,"bank-bakphar-buy":4}[label]
                # The shared decimal-format buffer is overwritten after a
                # trade. Receipt input comes from recorded keys/screens,
                # not from that later cash-display buffer.
                typed = {"bank-invested":"30","bank-sold":"7","bank-buy-clipped":"999","bank-zero-sale":"0",
                         "bank-sell-clipped":"999","bank-nasdiv-buy":"1","bank-bakphar-buy":"1"}.get(label,row["number_input"])
                spec["typed"] = typed
                result += texts[31 if buy else 20]+typed.encode()+texts[32 if buy else 21]+str(available).encode()
                if message:
                    company = row["menu_choices"]["7"]
                    amount = {"bank-invested":30,"bank-sold":7,"bank-buy-clipped":12,"bank-zero-sale":0,
                              "bank-sell-clipped":35,"bank-nasdiv-buy":1,"bank-bakphar-buy":1}[label]
                    if label.endswith("clipped"): result += texts[33 if buy else 22]
                    if not amount: result += texts[38 if buy else 27]+texts[39]
                    else: result += texts[34 if buy else 23]+str(amount).encode()+texts[35 if buy else 24]+texts[40+company]+texts[36 if buy else 25]+str(row["investments"][company]).encode()+texts[37 if buy else 26]
    else:
        # Balance screen following a trade, error, zero or ordinary re-entry.
        spec.update(pc=0x34a,menu=11)
        result = z(body,0x2d1)+str(row["credits"]).encode()
        count = 0
        for i, balance in enumerate(row["investments"]):
            if balance: result += texts[40+i]+str(balance).encode(); count += 1
        if not count: result += texts[17]
        result += z(body,0x2ff)
    spec.update(length=len(result),digest=digest(result),sha256=hashlib.sha256(result).hexdigest())
    return spec


def write_fixture(stem, rows, actions, directory, script, controlled):
    image, addresses, texts, bodies = sources()
    for row in rows: row["text"] = specification(row,texts,bodies)
    fixture = {"source_sha256":EXE_SHA,"image_sha256":IMAGE_SHA,
        "payload_sha256":{k:hashlib.sha256(v).hexdigest() for k,v in bodies.items()},
        "reference_run":str(directory.relative_to(ROOT)),"input_script":str(script.relative_to(ROOT)),
        "controlled":controlled,"checkpoints":rows}
    (BASE/(stem+".json")).write_text(json.dumps(fixture,indent=2)+"\n")
    (BASE/(stem+".actions")).write_text("".join(a+"\n" for a in actions))
    print(f"Exported {stem}: {len(rows)} original checkpoints, {len(actions)} native ticks; controlled={controlled}.")


def export(kind, directory):
    script = ROOT/"tools"/("reference-"+kind+".json")
    started = False; controlled = False; actions = []; pending = []; rows = []; previous = None
    keys = {"Up":"up","Down":"down","Left":"left","Right":"right","Return":"accept","space":"accept", "BackSpace":"cancel","Escape":"clear",**{str(i):str(i) for i in range(10)}}
    for command in json.loads(script.read_text()):
        if command == ["snapshot","start"]: started = True
        elif command[0] == "controlled-talk-context":
            write_fixture("reference-"+kind+"-empty",rows,actions,directory,script,False)
            actions, rows, previous = [], [], None; controlled = True
        elif started and command[0] == "key": pending += [keys[k] for k in command[1:]]
        if not started or command[0] != "snapshot": continue
        label = command[1]; _, _, row = original(directory,label)
        row["mode"] = "entry-confirm" if label.endswith("entry") else "local-exploration" if label == "start" or "road" in label or "wait" in label or label.endswith(("exit","funded")) else "building"
        if previous:
            frames = (previous["loop_timer"]-row["loop_timer"])&255
            if previous["mode"] == "local-exploration":
                outdoor = len(pending)-int(row["mode"] == "entry-confirm")
                if row["mode"] == "building":
                    check(pending == ["down","up","accept"],"Unobserved mixed entry input sequence")
                    outdoor = 1 # Down outdoors; Up defers entry; Accept is indoors.
                ticks = frames*4-outdoor
                check(ticks >= 0,"Incomplete frame interval")
                actions += ["idle"]*ticks+pending
            else:
                check(not frames or row["mode"] == "local-exploration","Indoor clock moved")
                actions += pending+["idle"]*(frames*4) if not controlled else pending
        row["tick"] = len(actions); rows.append(row); pending, previous = [], row
    write_fixture("reference-"+kind,rows,actions,directory,script,controlled)
    if kind == "bank-rates":
        frames = json.loads((directory/"investments-frames.json").read_text())["frames"]
        # Same 65 NPC fields as M2d, followed by cash, 3 investments, cap.
        out = ["# phase,loop,rng[3],search[2],cursor[2],npc[8][7],cash,investments[3],cap\n"]
        for r in frames:
            values = [r["phase"],r["loop_timer"],*r["rng"],*r["search"],*r["cursor"]]
            for n in r["npcs"]: values += [*n["position"],*n["destination"],n["direction"],*n["pair"]]
            values += [r["credits"],*r["investments"],r["allowance_cap"]]
            out.append(",".join(map(str,values))+"\n")
        (BASE/"bank-frames.csv").write_text("".join(out))


def run(binary, path, controlled):
    args = [str(binary),"--replay",str(path),"--trace"]
    if controlled: args += ["--shop-talk-checkpoint","armor" if "armor" in path.name else "weapon"]
    result = subprocess.run(args,check=True,capture_output=True,text=True,cwd=ROOT,timeout=30)
    return result.stdout,[json.loads(line) for line in result.stdout.splitlines()]


def compare(binary, stem, live):
    fixture = json.loads((BASE/(stem+".json")).read_text()); path = BASE/(stem+".actions")
    output, states = run(binary,path,fixture["controlled"])
    check(output == run(binary,path,fixture["controlled"])[0],"Non-deterministic replay")
    check(len(states) == len(path.read_text().splitlines())+1,"Incomplete replay")
    image, addresses, texts, bodies = sources()
    check(fixture["payload_sha256"] == {k:hashlib.sha256(v).hexdigest() for k,v in bodies.items()},"Wrong BLDs")
    for row in fixture["checkpoints"]:
        s = states[row["tick"]]; label = row["label"]
        check([s["x_half"],s["y_half"]] == row["position"],label+" position differs")
        for field in ("mode","story_flags","shop_refusal","credits","investments","allowance_cap","equipment","talk_result"):
            check(s[field] == row[field],f"{label} {field} differs: {s[field]} / {row[field]}")
        check({str(i):s["menu_choices"][i] for i in MENUS} == row["menu_choices"],label+" menu memory differs")
        # Menu 20 writes its remembered selection only on confirmation. These
        # two transient highlights are established by the captured screens.
        talk_highlight = 2 if label.endswith("done-selected") else 1 if label.endswith("second-selected") else row["talk_selected"]
        check(s["talk_selected"] == talk_highlight,label+" Talk highlight differs")
        if not fixture["controlled"]: check(s["npc_loop_timer"] == row["loop_timer"],label+" frame counter differs")
        if fixture["controlled"] and row["mode"] == "building": check(s["npc_pairs"] == row["npc_pairs"],label+" occupants differ")
        spec = row["text"]
        if spec:
            check(spec == specification(row,texts,bodies),label+" original text specification differs")
            for key, field in (("status","script_status"),("pc","script_pc"),("length","text_length"),("digest","text_digest"),("talk_phase","talk_phase"),("bank_phase","bank_phase")):
                check(s[field] == spec[key],f"{label} {field} differs: {s[field]} / {spec[key]}")
            if spec["menu"] is not None:
                check(s["menu_id"] == spec["menu"] and s["menu_selected"] == row["menu_choices"][str(spec["menu"])] ,label+" selection differs")
            if "talk_actor" in spec: check(s["talk_actor"] == spec["talk_actor"],label+" speaker differs")
            if "typed" in spec: check(s["bank_input"] == spec["typed"],label+" typed amount differs")
        if live:
            snap, ram, actual = original(live,label)
            check(all(actual[k] == row[k] for k in actual),label+" live original state differs")
            check(all(snap[k][0]&127 == row["position"][axis] for axis,k in enumerate(("party_x_raw","party_y_raw"))),label+" party position differs")
            if spec: check(ram.find(bodies[spec["resource"]]) >= 0,label+" original BLD not resident")
            load = int(snap["load_segment"],16)*16
            for address, text in zip(addresses,texts): check(ram[load+address:load+address+len(text)] == text,"Original EXE string differs")
    if live:
        commands = [json.loads(line)["command"] for line in (live/"inputs.jsonl").read_text().splitlines()]
        check(commands == json.loads((ROOT/fixture["input_script"]).read_text()),"Original input provenance differs")
        if "talk" in stem:
            audit = json.loads((live/"controlled-context.json").read_text())
            context = json.loads((ROOT/audit["fixture"]).read_text())
            check(audit["kind"] == "controlled-precondition" and len(audit["changes"]) == 9 and
                [c["after"] for c in audit["changes"][:8]] == context["npc_pairs"] and
                audit["changes"][-1]["after"] == [context["talk_result"]],"Controlled Talk audit differs")
        else: check(not any(c[0] == "controlled-talk-context" for c in commands),"Bank run injected a context")
    print(f"PASS: {stem}, {len(fixture['checkpoints'])} original checkpoints; state, original text hashes and deterministic replay.")
    return states[-1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--binary",type=Path,default=ROOT/"build/btech-headless")
    p.add_argument("--export",choices=RUNS)
    p.add_argument("--reference-run",type=Path)
    p.add_argument("--live",action="store_true")
    p.add_argument("--native-log",type=Path)
    p.add_argument("--scenario",choices=("bank","bank-rates","armor-talk","weapon-talk"),default="bank")
    args = p.parse_args()
    if args.export:
        export(args.export,args.reference_run or ROOT/"work/reference-runs"/RUNS[args.export]); return
    for kind in RUNS:
        live = ROOT/"work/reference-runs"/RUNS[kind] if args.live else args.reference_run if args.scenario == kind else None
        compare(args.binary.resolve(),"reference-"+kind,live)
        if kind.endswith("talk"): compare(args.binary.resolve(),"reference-"+kind+"-empty",live)
    if args.native_log:
        stem = "reference-"+args.scenario; fixture = json.loads((BASE/(stem+".json")).read_text())
        expected = (BASE/(stem+".actions")).read_text().splitlines()+["idle"]*5
        check(args.native_log.read_text().splitlines() == expected,"Native input log differs")
        run(args.binary.resolve(),args.native_log,fixture["controlled"])
        print("PASS: native input log replays through the same banking/shop handler.")
    subprocess.run([str(args.binary.resolve().with_name("btp-bank-tests")),"Original DOS"],check=True,cwd=ROOT,timeout=30)


if __name__ == "__main__": main()
