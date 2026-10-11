#!/usr/bin/env python3
"""Compare first Katrina visit, repeat denial and re-entry with original facts.

State bytes 0..21 are compared throughout. Byte 22 is compared only before the
original outdoor countdown resumes; its timing is deliberately not modeled.
Screens establish modes/highlights. PCs come from bytecode, not a captured IP.
"""
import argparse
import hashlib
import json
from pathlib import Path

from verify_m2 import ROOT, check, digest, run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=ROOT / "build/btech-headless")
    parser.add_argument("--reference-run", type=Path)
    parser.add_argument("--native-log", type=Path)
    args = parser.parse_args()
    binary = args.binary.resolve()
    fixture = json.loads((ROOT / "tests/fixtures/reference-katrina.json").read_text())
    raw = (ROOT / "Original DOS/CITADEL.BLD").read_bytes()
    payload = bytes(((byte + 41) & 255) ^ 233 for byte in raw[2:])
    check(int.from_bytes(raw[:2], "little") == len(payload) and
          hashlib.sha256(payload).hexdigest() == fixture["decrypted_sha256"], "Wrong Citadel payload")
    bodies = {}
    for text in fixture["texts"]:
        body = b"".join(payload[offset:offset + length] for offset, length in text["spans"])
        check(len(body) == text["length"] and hashlib.sha256(body).hexdigest() == text["sha256"],
              f"Original {text['name']} text bytes differ")
        bodies[text["name"]] = body
    work = ROOT / "work/m2b-verification"
    work.mkdir(parents=True, exist_ok=True)
    actions = ["up"] * 5 + ["accept"] * 6 + ["down"] * 4 + ["accept", "down", "up", "accept"]
    result, states = run(binary, actions, work, "katrina")
    repeated, _ = run(binary, actions, work, "repeat")
    check(result.stdout == repeated.stdout, "Katrina replay is not deterministic")
    check(len(states) == 20 and all(state["tick"] == i for i, state in enumerate(states)), "Wrong tick count")
    for row in fixture["checkpoints"]:
        state = states[row["tick"]]
        for key in ("x_half", "y_half", "mode"):
            check(state[key] == row[key], f"{row['label']} {key} differs")
        check(state["map"] == 1 and state["gate"] == 85 and len(state["story_flags"]) == 23, "Wrong state projection")
        check(state["story_flags"][:22] == row["story_flags"], f"{row['label']} persistent bytes differ")
        if row.get("compare_countdown"):
            check(state["story_flags"][22] == row["original_countdown"], f"{row['label']} script-set byte 22 differs")
        if "menu_selected" in row:
            check(state["menu_selected"] == row["menu_selected"], f"{row['label']} highlight differs")
    for text, tick in zip(fixture["texts"], (6,7,8,10)):
        state = states[tick]
        check(state["text_spans"] == text["spans"] and state["text_length"] == text["length"] and
              state["text_offset"] == text["spans"][0][0], f"Wrong {text['name']} text ranges")
        check(state["text_digest"] == digest(bodies[text["name"]]), f"Native {text['name']} bytes differ")
        check(state["script_pc"] == text["resume_pc"] and
              state["script_status"] == (1 if tick == 6 else 2), f"Wrong {text['name']} branch/pause")
    check(states[9]["script_status"] == states[11]["script_status"] == 1 and
          states[16]["script_status"] == 3, "Conversation/menu/exit dispatch differs")
    # Recovering a failed class choice after a verified visit must retain progress.
    prefix = actions + ["up", "up", "accept", "accept"]
    rejected, failed = run(binary, prefix, work, "class-after-katrina", success=False)
    check("unsupported opcode" in rejected.stderr and failed[-1]["script_opcode"] == 0xf5 and
          failed[-1]["story_flags"] == states[-1]["story_flags"], "Class fault lost or invented story progress")
    _, recovered = run(binary, prefix + ["cancel"], work, "recovered")
    check(recovered[-1]["mode"] == "building" and recovered[-1]["menu_selected"] == 2 and
          recovered[-1]["story_flags"] == states[-1]["story_flags"], "Recovery changed completed progress")
    print("PASS: 20 original Katrina checkpoints / 20 native states, four text hashes, three-block conversation, byte updates, repeat denial, exit/re-entry highlight, deterministic replay and failed-choice rollback.")
    print("Scope: byte 22 countdown timing after exit is excluded; original fonts/animation/timing remain approximate.")
    if args.native_log:
        recorded_actions = args.native_log.read_text().splitlines()
        check(recorded_actions == actions + ["idle"] * 5, "Unexpected native Katrina input log")
        _, recorded = run(binary, recorded_actions, work, "recorded")
        _, expected_native = run(binary, actions + ["idle"] * 5, work, "native-expected")
        check(recorded[-1] == expected_native[-1], "Recorded native state drifted")
        print("PASS: native SDL Katrina inputs replay to the same complete canonical state.")
    if args.reference_run:
        for row in fixture["checkpoints"]:
            snapshot = json.loads((args.reference_run / (row["label"] + "-state.json")).read_text())
            check(snapshot["gate"] == 85 and snapshot["map1_payload_present"], "Original map/gate differs")
            for axis, key in enumerate(("x_half", "y_half")):
                party = snapshot["party_x_raw"] if axis == 0 else snapshot["party_y_raw"]
                check(snapshot["cursor_raw"][axis] & 127 == row[key] and party[0] & 127 == row[key],
                      f"Original {row['label']} {key} differs")
            check(snapshot["story_state_bytes"][:22] == row["story_flags"] and
                  snapshot["story_state_bytes"][22] == row["original_countdown"] and
                  snapshot["credits"] == row["original_credits"] == 35, "Original state/credits differs")
            if row["mode"] == "building":
                check(snapshot["citadel_payload_sha256"] == fixture["decrypted_sha256"], "Original payload hash differs")
                ram = (args.reference_run / (row["label"] + "-ram.bin")).read_bytes()
                offset = int(snapshot["citadel_payload_guest_offset"], 16)
                check(ram[offset:offset + len(payload)] == payload, "Original RAM/script differs")
        print("PASS: live original cursor, party[0], persistent bytes, recorded countdown observations, unchanged credits and full decrypted payload match the fixture. Modes/highlights were checked against screenshots.")


if __name__ == "__main__":
    main()
