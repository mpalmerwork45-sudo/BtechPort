#!/usr/bin/env python3
"""Verify bounded MAP1 NPC steps and a conversation reached by ordinary inputs.

Frame comparisons include RNG/search state. Route checkpoints compare player and
story state by input ordinal; wall-clock timing and full economy are excluded.
"""
import argparse
import hashlib
import json
import struct
import subprocess
from pathlib import Path
from exepack import unpack
from verify_m2 import check, digest
from verify_m2c import original_text

ROOT = Path(__file__).resolve().parents[1]
TAIL = ["accept", "down", "accept", "down"] + ["idle"] * 5
NPC_FIELDS = ("npc_pairs", "npc_enabled", "npc_phase", "npc_clock", "npc_fault",
              "npc_rng", "npc_search", "npc_loop_timer", "npc_allowance_pending", "npcs")


def run(binary, actions, name):
    path = ROOT / "work/m2d-verification" / (name + ".actions")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(a + "\n" for a in actions))
    result = subprocess.run([str(binary), "--data", str(ROOT / "Original DOS"),
        "--dialogue-data", str(ROOT / "work/talk-data.bin"), "--replay", str(path), "--trace"],
        text=True, capture_output=True, check=True, cwd=ROOT, timeout=15)
    return result.stdout, [json.loads(line) for line in result.stdout.splitlines()]


def compare_route(fixture, actions, states, texts):
    check(len(states) == len(actions) + 1 and all(s["tick"] == i for i, s in enumerate(states)),
          "Replay tick count differs")
    check(all(s["map"] == 1 and s["gate"] == 85 and s["npc_enabled"] == 2 and
              not s["npc_fault"] and not s["conversation_checkpoint"] for s in states),
          "Unexpected map, fault or controlled NPC context")
    initial = states[0]
    for key, value in fixture["baseline"]["native"].items():
        check(initial[key] == value, f"Recorded baseline {key} differs")
    by_input = {0: initial}
    ordinal = 0
    for action, state in zip(actions, states[1:]):
        if action != "idle": ordinal += 1
        by_input[ordinal] = state
    for row in fixture["checkpoints"]:
        state = by_input[row["actions"]]
        check([state["x_half"], state["y_half"]] == row["position"],
              f"{row['label']} player position differs")
        check(state["story_flags"] == row["story_flags"] and state["talk_result"] == row["talk_result"],
              f"{row['label']} story/result differs")
        if row["label"] in ("menu", "talk", "reply"):
            body = texts[{"menu": "citadel", "talk": "talk-menu", "reply": "reply"}[row["label"]]]
            phase = {"menu": 0, "talk": 2, "reply": 3}[row["label"]]
            check(state["mode"] == "building" and state["talk_phase"] == phase and
                  state["text_length"] == len(body) and state["text_digest"] == digest(body),
                  f"{row['label']} original text/continuation differs")
            check(state["npc_pairs"][1][0] == 0x12 and state["npc_pairs"][1][1] > 0 and
                  state["npcs"][1][:2] == [0, 0], "Conversation lacks a naturally arrived NPC")
    arrivals = [(a, b) for a, b in zip(states, states[1:])
                if a["npc_pairs"][1][0] == 0x51 and b["npc_pairs"][1][0] == 0x12]
    check(len(arrivals) == 1, "Missing or repeated slot-1 arrival")
    before, arrived = arrivals[0]
    goal = fixture["waypoints"][1]
    check(all(abs(before["npcs"][1][i] - goal[i]) <= 1 for i in range(2)) and
          arrived["npcs"][1][:2] == [0, 0] and arrived["npc_pairs"][1][1] > 0,
          "Arrival was not preceded by a final walking step")
    building = [s for s in states if s["mode"] in ("entry-confirm", "building")]
    check(building and all(all(s[k] == building[0][k] for k in NPC_FIELDS) for s in building),
          "NPC simulation did not freeze at entry/in the building")
    final = states[-1]
    check(final["talk_phase"] == 3 and final["talk_actor"] == 1 and final["talk_mask"] == 2 and
          final["story_flags"][13] == 1 and final["talk_result"] == 0, "Wrong final conversation")
    print(f"PASS: {len(fixture['checkpoints'])} original player/story checkpoints; default MAP1 walk, "
          f"slot-1 arrival at tick {arrived['tick']}, authentic reply and building suspension.")


def export_frames(directory, output):
    data = json.loads((directory / "npc-travel-frames.json").read_text())
    check(data["kind"] == "read-only-outdoor-frames", "Wrong trace provenance")
    rows = []
    for s in data["frames"]:
        values = [s["phase"], s["loop_timer"], *s["rng"], *s["search"], *s["cursor"]]
        for n in s["npcs"]:
            values += [*n["position"], *n["destination"], n["direction"], *n["pair"]]
        check(len(values) == 65 and all(type(v) is int and 0 <= v <= 65535 for v in values),
              "Malformed numeric original frame")
        rows.append(",".join(map(str, values)) + "\n")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("# numeric projection of read-only original outdoor frames\n" + "".join(rows))


def compare_live(directory, fixture, image, payload):
    check(not (directory / "controlled-context.json").exists(), "Natural trace contains a controlled write")
    inputs = [json.loads(line)["command"] for line in (directory / "inputs.jsonl").read_text().splitlines()]
    check(inputs == json.loads((ROOT / "tools/reference-npc.json").read_text()) and
          not any(c[0] == "controlled-talk-context" for c in inputs), "Different original input script")
    for row in fixture["checkpoints"]:
        state = json.loads((directory / (row["label"] + "-state.json")).read_text())
        ram = (directory / (row["label"] + "-ram.bin")).read_bytes()
        base = int(state["state_segment"], 16) * 16
        check([v & 127 for v in state["cursor_raw"]] == row["position"] and
              [state["party_x_raw"][0] & 127, state["party_y_raw"][0] & 127] == row["position"],
              f"{row['label']} original cursor/party differ")
        check(state["story_state_bytes"][:23] == row["story_flags"] and
              ram[base + 0xd33a] == row["talk_result"] and ram[base + 0xd339] == 0,
              f"{row['label']} original flags/result differ")
        if row["label"] in ("menu", "talk", "reply"):
            check(ram[base + 0xd398 + 26] == 0x12 and ram[base + 0xd399 + 26] > 0,
                  "Original conversation lacks an arrived NPC")
            at = int(state["citadel_payload_guest_offset"], 16)
            check(ram[at:at + len(payload)] == payload, "Original BLD payload differs")
            load = int(state["load_segment"], 16) * 16
            for address in (0x384be, 0x384d8, 0x384dd, 0x38511, 0x3853f, 0x3b17e):
                end = image.index(0, address) + 1
                check(ram[load + address:load + end] == image[address:end], "Original EXE text differs")
    baseline = json.loads((directory / "start-state.json").read_text())
    ram = (directory / "start-ram.bin").read_bytes()
    base = int(baseline["state_segment"], 16) * 16
    check(struct.unpack_from("<4I", ram, base + 0xd370) == (35, 0, 0, 0) and
          struct.unpack_from("<H", ram, base + 0xd33f)[0] == 50,
          "Original allowance schedule precondition differs")
    check(json.loads((directory / "arrival-state.json").read_text())["npcs"][1]["timer"] > 0,
          "Original natural arrival snapshot is absent")
    print("PASS: unmodified original inputs, cursor/party/flags/result, natural occupancy, "
          "allowance precondition and complete runtime BLD/EXE text bytes.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=ROOT / "build/btech-headless")
    parser.add_argument("--reference-run", type=Path)
    parser.add_argument("--native-log", type=Path)
    args = parser.parse_args()
    binary = args.binary.resolve()
    fixture = json.loads((ROOT / "tests/fixtures/reference-npc.json").read_text())
    image, metadata = unpack((ROOT / "Original DOS/BTECH.EXE").read_bytes())
    raw = (ROOT / "Original DOS/CITADEL.BLD").read_bytes()
    payload = bytes(((b + 41) & 255) ^ 233 for b in raw[2:])
    check(metadata["input_sha256"] == fixture["source_sha256"] and
          metadata["image_sha256"] == fixture["image_sha256"] and
          hashlib.sha256(payload).hexdigest() == fixture["decrypted_sha256"], "Wrong original data")
    map_bytes = (ROOT / "Original DOS/MAP1.MTP").read_bytes()
    waypoints = list(zip(struct.unpack_from("<8H", map_bytes, 389), struct.unpack_from("<8H", map_bytes, 421)))
    check([list(p) for p in waypoints] == fixture["waypoints"] and
          list(map_bytes[533:541]) == fixture["routes"], "Original NPC route table differs")
    corpus = ROOT / "tests/fixtures/npc-frames.csv"
    check(hashlib.sha256(corpus.read_bytes()).hexdigest() == fixture["frame_csv_sha256"], "Frame corpus changed")
    subprocess.run([str(binary.parent / "btp-npc-tests"), str(ROOT / "Original DOS"), str(corpus)],
                   check=True, timeout=15, cwd=ROOT)
    actions = (ROOT / "tests/fixtures/citadel-arrival.actions").read_text().splitlines()
    first, states = run(binary, actions, "arrival")
    second, _ = run(binary, actions, "repeat")
    check(first == second, "Natural-route replay is nondeterministic")
    texts = original_text(image, map_bytes, payload)
    compare_route(fixture, actions, states, texts)
    _, returned = run(binary, actions + TAIL, "return")
    check(returned[-1]["mode"] == "local-exploration" and returned[-1]["x_half"] == 69 and
          returned[-1]["y_half"] == 21 and returned[-1]["story_flags"][13] == 1,
          "Conversation return/exit did not complete")
    print("PASS: deterministic input replay and conversation return/exit; no controlled presence flag.")
    if args.native_log:
        record = args.native_log.read_text().splitlines()
        check(record == actions + TAIL, "Unexpected native arrival input record")
        _, native = run(binary, record, "recorded")
        check(native[-1] == returned[-1], "Native input replay differs")
        print("PASS: entire native SDL exploration/arrival/reply/return/exit record replays identically.")
    if args.reference_run:
        compare_live(args.reference_run, fixture, image, payload)
        fresh = ROOT / "work/m2d-verification/live-frames.csv"
        export_frames(args.reference_run, fresh)
        subprocess.run([str(binary.parent / "btp-npc-tests"), str(ROOT / "Original DOS"), str(fresh)],
                       check=True, timeout=15, cwd=ROOT)
    print("Scope: complete observed frame steps are compared; player-movement gaps are reported/skipped. "
          "Wall-clock cadence, startup, general economy, world/edge/party rules and NPC pixels remain outside parity.")


if __name__ == "__main__":
    main()
