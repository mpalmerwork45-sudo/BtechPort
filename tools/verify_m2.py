#!/usr/bin/env python3
"""Compare the bounded Citadel loop with original-game factual checkpoints.

Screens establish modes/choices/text order; raw snapshots establish coordinates,
party[0], flags and unchanged credits. Script PC is bytecode-derived, not a live
instruction pointer. Rendering and original timing are explicitly outside parity.
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


def digest(data):
    value = 2166136261
    for byte in data:
        value = ((value ^ byte) * 16777619) & 0xffffffff
    return value


def run(binary, actions, work, name, success=True):
    replay = work / (name + ".actions")
    replay.write_text("".join(action + "\n" for action in actions))
    result = subprocess.run([str(binary), "--data", str(ROOT / "Original DOS"),
        "--replay", str(replay), "--trace"], text=True, capture_output=True)
    check((result.returncode == 0) == success, f"Unexpected replay result: {result.stderr}")
    return result, [json.loads(line) for line in result.stdout.splitlines()]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=ROOT / "build/btech-headless")
    parser.add_argument("--reference-run", type=Path)
    parser.add_argument("--native-log", type=Path)
    args = parser.parse_args()
    binary = args.binary.resolve()
    fixture = json.loads((ROOT / "tests/fixtures/reference-citadel.json").read_text())
    raw = (ROOT / "Original DOS/CITADEL.BLD").read_bytes()
    payload = bytes(((b + 41) & 255) ^ 233 for b in raw[2:])
    check(int.from_bytes(raw[:2], "little") == len(payload) and
          hashlib.sha256(payload).hexdigest() == fixture["decrypted_sha256"], "Wrong Citadel data")
    for text in fixture["texts"]:
        body = payload[text["offset"]:text["offset"] + text["length"]]
        check(hashlib.sha256(body).hexdigest() == text["sha256"], "Dialogue bytes differ from fixture")
    work = ROOT / "work/m2-verification"
    work.mkdir(parents=True, exist_ok=True)
    actions = ["up"] * 5 + ["accept", "down", "accept"] + ["accept"] * 6
    actions += ["down"] * 3 + ["accept", "down"]
    result, states = run(binary, actions, work, "citadel")
    repeat, _ = run(binary, actions, work, "repeat")
    check(result.stdout == repeat.stdout, "Citadel replay is not deterministic")
    indexes = dict(zip([row["label"] for row in fixture["checkpoints"]],
        [0,1,2,3,4,5,6,8,9,10,11,12,13,14,18,19]))
    for row in fixture["checkpoints"]:
        state = states[indexes[row["label"]]]
        for key in ("x_half", "y_half", "mode"):
            check(state[key] == row[key], f"{row['label']} {key}: {state[key]} != {row[key]}")
        check(state["story_flags"][:16] == row["story_flags"] and not any(state["story_flags"][16:]),
              f"{row['label']} story bytes differ")
        check(state["map"] == 1 and state["gate"] == 85, "Wrong map/gate")
    check(len(states) == 20 and all(s["tick"] == i for i, s in enumerate(states)), "Tick/state count mismatch")
    for i, tick in enumerate([6,8,9,10,11,12,13,14]):
        text = fixture["texts"][0 if i in (0,7) else i]
        state = states[tick]
        check(state["text_offset"] == text["offset"] and state["text_length"] == text["length"], "Wrong text range")
        check(state["text_digest"] == digest(payload[text["offset"]:text["offset"] + text["length"]]), "Native decoded text differs")
    check(states[7]["menu_selected"] == states[14]["menu_selected"] == 1 and
          states[17]["menu_selected"] == 4, "Menu selection/return behavior differs")
    check([s["script_pc"] for s in states[8:14]] == fixture["hall_resume_pcs"], "Hall bytecode dispatch differs")
    check(states[18]["script_status"] == 3 and states[18]["script_opcode"] == 255, "Exit did not execute FF")
    prefix = ["up"]*5+["accept","down","down","accept","accept"]
    _, course = run(binary,prefix,work,"class-offer")
    check(course[-1]["mode"] == "building" and course[-1]["menu_id"] == 9 and
          course[-1]["school_phase"] == 1 and course[-1]["story_flags"][7] == 1,
          "Class did not reach its verified course offer")
    _, declined = run(binary, ["up"] * 5 + ["right", "accept"], work, "decline")
    check(declined[-1]["mode"] == "local-exploration" and declined[-1]["y_half"] == 20 and
          declined[-1]["story_flags"][10] == 0, "Decline incorrectly executed building script")
    print("PASS: 16 original Hall checkpoints / 20 native states, seven texts, six pauses, retained selection, exit, replay, decline and Class offer.")
    if args.native_log:
        replay_actions = args.native_log.read_text().splitlines()
        _, recorded = run(binary, replay_actions, work, "recorded")
        check(len(replay_actions) == 24 and replay_actions[:19] == actions and
              replay_actions[19:] == ["idle"] * 5, "Unexpected native recorded inputs")
        _, expected_native = run(binary, actions + ["idle"] * 5, work, "native-expected")
        check(recorded[-1] == expected_native[-1], "Recorded native state drifted, including outdoor NPC ticks")
        print("PASS: native SDL Citadel inputs replay to the same complete canonical state.")
    if args.reference_run:
        for row in fixture["checkpoints"]:
            snapshot = json.loads((args.reference_run / (row["label"] + "-state.json")).read_text())
            check(snapshot["gate"] == 85 and snapshot["map1_payload_present"], "Live original map/gate differs")
            for axis, key in enumerate(("x_half", "y_half")):
                party = snapshot["party_x_raw"] if axis == 0 else snapshot["party_y_raw"]
                check((snapshot["cursor_raw"][axis] & 127) == row[key] and
                      (party[0] & 127) == row[key], f"Live original {row['label']} {key} drifted")
            check(snapshot["story_state_bytes"][:16] == row["story_flags"] and
                  snapshot["credits"] == row["original_credits"] == 35, "Live original flags/credits differ")
            if row["mode"] == "building":
                check(snapshot["citadel_payload_sha256"] == fixture["decrypted_sha256"], "Original decoded payload differs")
                ram = (args.reference_run / (row["label"] + "-ram.bin")).read_bytes()
                offset = int(snapshot["citadel_payload_guest_offset"], 16)
                check(ram[offset:offset + len(payload)] == payload, "Original RAM/script mismatch")
        print("PASS: live original cursor, party[0], 16 flags, unchanged credits and full decrypted payload match the fixture. Modes/text order were checked against captured screens; PC is bytecode-derived.")


if __name__ == "__main__":
    main()
