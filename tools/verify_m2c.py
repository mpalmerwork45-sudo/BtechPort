#!/usr/bin/env python3
"""Compare empty Talk and a controlled conversation with original checkpoints.

This validates the native handler, not NPC travel. Original text is reconstructed
from primary EXE/MAP1 bytes, independently of the generated C-runtime cache.
"""
import argparse
import hashlib
import json
import struct
import subprocess
from pathlib import Path
from exepack import unpack
from verify_m2 import check, digest

ROOT = Path(__file__).resolve().parents[1]
PREFIX = ["up"]*5+["accept"]+["down"]*3+["accept"]
ACTIONS = PREFIX+["down","accept","accept","up","accept","accept","down","accept","down"]


def run(binary, actions, name, checkpoint):
    path = ROOT/"work/m2c-verification"/(name+".actions")
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text("".join(a+"\n" for a in actions))
    command = [str(binary),"--data",str(ROOT/"Original DOS"),"--dialogue-data",str(ROOT/"work/talk-data.bin"),
               "--replay",str(path),"--trace"]
    if checkpoint: command.append("--conversation-checkpoint")
    result = subprocess.run(command,text=True,capture_output=True,cwd=ROOT,check=True)
    return result.stdout,[json.loads(line) for line in result.stdout.splitlines()]


def original_text(image, map_bytes, payload):
    def string(at): return image[at:image.index(0,at)]
    def name(at): return map_bytes[at:at+16].split(b"\0")[0]
    return {"citadel":payload[6:221],"empty":string(0x3848e),
        "talk-menu":string(0x384be)+name(21)+b"\r"+string(0x384d8),
        "reply":string(0x384dd)+string(0x3b17e)+string(0x38511)+name(165)+string(0x3853f)}


def compare(rows, states, texts, checkpoint):
    for row in rows:
        state = states[row["tick"]]
        for key in ("mode","x_half","y_half","story_flags","menu_selected","talk_phase","talk_selected","talk_result"):
            check(state[key] == row[key],f"{row['label']} {key} differs: {state[key]} != {row[key]}")
        if row["mode"] == "building":
            check(state["npc_pairs"] == row["npc_pairs"],f"{row['label']} NPC context differs")
        check(state["conversation_checkpoint"] == checkpoint and state["map"] == 1 and state["gate"] == 85,
              "Wrong scenario/map/gate")
        native = row["talk_phase"] != 0
        check(state["script_status"] == (5 if native else 3 if row["mode"] == "local-exploration" else 1),
              "Wrong native continuation status")
        check(state["script_pc"] == (4322 if native else 4326 if row["mode"] == "local-exploration" else 234),
              "Bytecode resume PC differs")
        if checkpoint and native:
            check(state["talk_mask"] == 2 and state["talk_count"] == 1,"Wrong occupants")
        if row["talk_phase"] == 3: check(state["talk_actor"] == 1,"Wrong reply actor")
        body = texts[row["text"]]
        check(state["text_length"] == len(body) and state["text_digest"] == digest(body),
              f"{row['label']} original text bytes differ")


def compare_live(directory, rows, image, payload, controlled):
    if controlled:
        audit = json.loads((directory/"controlled-context.json").read_text())
        context = json.loads((ROOT/"tests/fixtures/talk-context.json").read_text())
        check(audit["kind"] == "controlled-precondition" and len(audit["changes"]) == 9,"Missing precondition audit")
        check([r["after"] for r in audit["changes"][:8]] == context["npc_pairs"] and
              audit["changes"][8]["after"] == [context["talk_result"]],"Different controlled precondition")
    for row in rows:
        snapshot = json.loads((directory/(row["label"]+"-state.json")).read_text())
        ram = (directory/(row["label"]+"-ram.bin")).read_bytes()
        state_base = int(snapshot["state_segment"],16)*16
        check([v&127 for v in snapshot["cursor_raw"]] == [row["x_half"],row["y_half"]],"Original position drift")
        check((snapshot["party_x_raw"][0]&127,snapshot["party_y_raw"][0]&127) ==
              (row["x_half"],row["y_half"]),"Original party/cursor differ")
        check(snapshot["story_state_bytes"][:23] == row["story_flags"] and snapshot["credits"] == 35,
              "Original story/credits drift")
        pairs = [list(ram[state_base+0xd398+26*i:state_base+0xd39a+26*i]) for i in range(8)]
        if row["mode"] == "building": check(pairs == row["npc_pairs"],"Original building NPC context drift")
        check(ram[state_base+0xd33a] == row["talk_result"] and
              ram[state_base+0xd339] == row["recruitment"],"Original NPC/result drift")
        at = int(snapshot["citadel_payload_guest_offset"],16)
        check(ram[at:at+len(payload)] == payload,"Original RAM/BLD mismatch")
        load = int(snapshot["load_segment"],16)*16
        map_base = load+0x1c6c0
        map_bytes = (ROOT/"Original DOS/MAP1.MTP").read_bytes()
        check(ram[map_base+0xa461:map_base+0xa4e1] == map_bytes[5:133] and
              ram[map_base+0xa561:map_base+0xa5e1] == map_bytes[133:261],"Original NPC/destination names mismatch")
        for address in (0x3848e,0x384be,0x384d8,0x384dd,0x38511,0x3853f,0x3b17e):
            end = image.index(0,address)+1
            check(ram[load+address:load+end] == image[address:end],"Original EXE text mismatch")
    print("PASS: live original snapshots match numeric context, flags, position, result, unchanged credits and full BLD/EXE text bytes.")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--binary",type=Path,default=ROOT/"build/btech-headless")
    p.add_argument("--reference-run",type=Path)
    p.add_argument("--empty-reference-run",type=Path)
    p.add_argument("--native-log",type=Path)
    args = p.parse_args(); binary = args.binary.resolve()
    fixture = json.loads((ROOT/"tests/fixtures/reference-talk.json").read_text())
    image, metadata = unpack((ROOT/"Original DOS/BTECH.EXE").read_bytes())
    raw = (ROOT/"Original DOS/CITADEL.BLD").read_bytes()
    payload = bytes(((b+41)&255)^233 for b in raw[2:])
    check(metadata["input_sha256"] == fixture["source_sha256"] and metadata["image_sha256"] == fixture["image_sha256"] and
          hashlib.sha256(payload).hexdigest() == fixture["decrypted_sha256"],"Wrong original data")
    texts = original_text(image,(ROOT/"Original DOS/MAP1.MTP").read_bytes(),payload)
    for row in fixture["texts"]:
        check(len(texts[row["key"]]) == row["length"] and
              hashlib.sha256(texts[row["key"]]).hexdigest() == row["sha256"],"Original text fixture differs")
    first, states = run(binary,ACTIONS,"conversation",True)
    second, _ = run(binary,ACTIONS,"repeat",True)
    check(first == second and len(states) == 20 and all(s["tick"] == i for i,s in enumerate(states)),
          "Replay/tick determinism differs")
    compare(fixture["checkpoints"],states,texts,1)
    _, empty = run(binary,PREFIX+["accept"],"empty",False)
    compare(fixture["empty_checkpoints"],empty,texts,0)
    check(empty[10]["talk_mask"] == empty[10]["talk_count"] == 0,"Empty room invented an occupant")
    print("PASS: 10 controlled conversation + 3 unmodified empty-room checkpoints, exact text hashes, Done/result effects, retained selections and deterministic replay.")
    if args.native_log:
        actions = args.native_log.read_text().splitlines()
        check(actions == ACTIONS+["idle"]*5,"Unexpected native Talk input record")
        _, recorded = run(binary,actions,"recorded",True)
        # Five extra indoor idle ticks change only the counter and the new
        # complete-state fingerprint, which includes that counter.
        check({k:v for k,v in recorded[-1].items() if k not in ("tick","state_digest")} ==
              {k:v for k,v in states[-1].items() if k not in ("tick","state_digest")},"Native input replay differs")
        print("PASS: native SDL Talk selection, reply, return and exit inputs replay to the same canonical state.")
    if args.reference_run: compare_live(args.reference_run,fixture["checkpoints"],image,payload,True)
    if args.empty_reference_run: compare_live(args.empty_reference_run,fixture["empty_checkpoints"],image,payload,False)
    print("Scope: controlled NPC presence is explicit; NPC arrival/travel, post-exit timers, full RNG, pixels and pacing remain outside parity.")


if __name__ == "__main__": main()
