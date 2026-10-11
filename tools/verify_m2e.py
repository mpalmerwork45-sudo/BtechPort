#!/usr/bin/env python3
"""Compare two original shop loops, confirmation boundaries and equipment/cash.

Fixtures contain original numeric observations and text ranges/hashes only.
Explicit native idle ticks reproduce captured outdoor loop-counter increments;
NPC positions between these route snapshots and wall-clock cadence are excluded.
"""
import argparse
import hashlib
import json
import struct
import subprocess
from pathlib import Path
from verify_m2 import check, digest

ROOT = Path(__file__).resolve().parents[1]
MENUS = (8, 12, 13, 14, 15, 16, 30)
COUNTS = {8: 5, 12: 4, 13: 6, 14: 5, 15: 4, 16: 7, 30: 3}
# Payload ranges established from original screens and original BLD paths.
TEXTS = {
    "armor-menu": ("ARMOR", [0xA], 1, 0xEF, 12, None),
    "armor-browse": ("ARMOR", [0xF1, 0x229, 0x280, 0x297], 1, 0x2B4, 13, 3),
    "armor-item": ("ARMOR", [0x2C2, 0x93F], 6, 0x95E, None, None),
    "armor-buy": ("ARMOR", [0xC5B], 2, 0xD34, None, None),
    "armor-declined": ("ARMOR", [0x182, 0x229, 0x280, 0x297], 1, 0x2B4, 13, 3),
    "armor-insufficient": ("ARMOR", [0x969, 0xA0F], 2, 0xA93, None, 1),
    "weapon-menu": ("WEAPON", [0xA], 1, 0xE8, 30, None),
    "weapon-browse": ("WEAPON", [0xEA, 0x221, 0x25F], 1, 0x275, 15, 3),
    "weapon-blades": ("WEAPON", [0x27A], 1, 0x3AD, 16, None),
    "weapon-item": ("WEAPON", [0x3AF, 0x1391], 6, 0x13A7, None, None),
    "weapon-buy": ("WEAPON", [0x14C9], 2, 0x15FE, None, None),
    "weapon-declined": ("WEAPON", [0xEA, 0x221, 0x25F], 1, 0x275, 15, 3),
}
ALIASES = {"armor-return": "armor-menu", "armor-rebrowse": "armor-browse",
    "armor-second-item": "armor-item", "armor-no-selected": "armor-item",
    "armor-unfunded-item": "armor-item", "weapon-return": "weapon-menu",
    "weapon-second-item": "weapon-item", "weapon-no-selected": "weapon-item"}


def payloads():
    result = {}
    for name in ("ARMOR", "WEAPON"):
        raw = (ROOT / "Original DOS" / (name + ".BLD")).read_bytes()
        body = bytes(((b + 41) & 255) ^ 233 for b in raw[2:])
        check(int.from_bytes(raw[:2], "little") == len(body), "BLD size word differs")
        result[name] = body
    return result


def original(directory, label):
    s = json.loads((directory / (label + "-state.json")).read_text())
    ram = (directory / (label + "-ram.bin")).read_bytes()
    ds, state = int(s["data_segment"], 16)*16, int(s["state_segment"], 16)*16
    menu = struct.unpack_from("<H", ram, ds+0x56B6)[0]*16
    return s, ram, {"label": label, "position": [v & 127 for v in s["cursor_raw"]],
        "story_flags": s["story_state_bytes"][:23], "shop_refusal": s["story_state_bytes"][39],
        "credits": struct.unpack_from("<I", ram, state+0xD370)[0],
        "allowance_cap": struct.unpack_from("<H", ram, state+0xD33F)[0],
        "equipment": {"weapon": ram[state+0xC61F], "armor": ram[state+0xC621],
                      "armor_points": ram[state+0xC622]},
        "menu_choices": {str(i): struct.unpack_from("<H", ram, menu+0x98+16*i)[0] for i in MENUS},
        "loop_timer": s["loop_timer"]}


def text_spec(label, row, bodies):
    key = ALIASES.get(label, label)
    if key not in TEXTS:
        return None
    name, offsets, status, pc, menu, cash_after = TEXTS[key]
    body = bodies[name]
    spans = [[a, body.index(0, a)-a] for a in offsets]
    output = b""
    for i, (a, n) in enumerate(spans, 1):
        output += body[a:a+n]
        if i == cash_after:
            output += str(row["credits"]).encode("ascii")
    return {"resource": name, "spans": spans, "length": len(output),
        "sha256": hashlib.sha256(output).hexdigest(), "digest": digest(output),
        "status": status, "pc": pc, "menu": menu,
        "confirmation": int(label.endswith("no-selected")) if status == 6 else None}


def export(directory, script, stem):
    bodies = payloads()
    actions, pending, rows = [], [], []
    started = False
    previous = None
    keys = {"Up": "up", "Down": "down", "Left": "left", "Right": "right", "Return": "accept"}
    for command in json.loads(script.read_text()):
        if command == ["snapshot", "start"]:
            started = True
        elif started and command[0] == "key":
            pending.extend(keys[k] for k in command[1:])
        if not started or command[0] != "snapshot":
            continue
        label = command[1]
        _, _, row = original(directory, label)
        row["mode"] = "entry-confirm" if label.endswith("entry") else (
            "local-exploration" if label == "start" or "road" in label or label.endswith(("exit", "funded")) else "building")
        if previous:
            frames = (previous["loop_timer"]-row["loop_timer"]) & 255
            if previous["mode"] == "local-exploration":
                # Entry's final deferred key is outside the outdoor clock.
                outdoor_keys = len(pending) - int(row["mode"] == "entry-confirm")
                idle = frames*4-outdoor_keys
                check(idle >= 0, "Missed original frame interval; cannot infer replay pacing")
                actions += ["idle"]*idle + pending
            else:
                check(not frames or row["mode"] == "local-exploration", "Building clock advanced")
                actions += pending + ["idle"]*(frames*4)
        check(not pending or previous is not None, "Unexpected start inputs")
        row["tick"] = len(actions)
        row["text"] = text_spec(label, row, bodies)
        rows.append(row)
        pending, previous = [], row
    fixture = {"scope": "ordinary zero-investment MAP1 baseline; two purchases; explicit native frame-counter waits",
        "reference_run": str(directory.relative_to(ROOT)), "input_script": str(script.relative_to(ROOT)),
        "payload_sha256": {n: hashlib.sha256(b).hexdigest() for n, b in bodies.items()},
        "checkpoints": rows}
    base = ROOT / "tests/fixtures"
    (base / (stem + ".json")).write_text(json.dumps(fixture, indent=2) + "\n")
    (base / (stem + ".actions")).write_text("".join(a + "\n" for a in actions))
    print(f"Exported {len(rows)} original observations and {len(actions)} explicit native ticks.")


def run(binary, path, name):
    result = subprocess.run([str(binary), "--replay", str(path), "--trace"],
        check=True, capture_output=True, text=True, cwd=ROOT, timeout=20)
    return result.stdout, [json.loads(line) for line in result.stdout.splitlines()]


def compare(binary, stem, live=None):
    base = ROOT / "tests/fixtures"
    fixture = json.loads((base / (stem + ".json")).read_text())
    path = base / (stem + ".actions")
    actions = path.read_text().splitlines()
    out, states = run(binary, path, stem)
    repeated, _ = run(binary, path, stem)
    check(out == repeated and len(states) == len(actions)+1, "Non-deterministic or incomplete shop replay")
    bodies = payloads()
    check({n: hashlib.sha256(b).hexdigest() for n, b in bodies.items()} == fixture["payload_sha256"], "Shop payload differs")
    for row in fixture["checkpoints"]:
        s = states[row["tick"]]
        check([s["x_half"], s["y_half"]] == row["position"], f"{row['label']} cursor differs")
        for field in ("mode", "story_flags", "shop_refusal", "credits", "allowance_cap", "equipment"):
            check(s[field] == row[field], f"{row['label']} {field} differs: {s[field]} / {row[field]}")
        check(s["npc_loop_timer"] == row["loop_timer"], "Explicit replay frame-counter wait differs")
        check({str(i): s["menu_choices"][i] for i in MENUS} == row["menu_choices"], f"{row['label']} menu memory differs")
        text = row["text"]
        if text:
            check(text == text_spec(row["label"], row, bodies), "Original text ranges/hash differ")
            check(s["text_spans"] == text["spans"] and s["text_length"] == text["length"] and
                  s["text_digest"] == text["digest"] and s["script_status"] == text["status"] and
                  s["script_pc"] == text["pc"], f"{row['label']} BLD path/text differs")
            if text["menu"] is not None:
                check(s["menu_id"] == text["menu"] and s["menu_selected"] == row["menu_choices"][str(text["menu"])], "Menu selection differs")
            if text["confirmation"] is not None:
                check(s["confirm_selected"] == text["confirmation"], "Yes/No selection differs")
    # No NPC timer, allowance or RNG changes during the observed indoor states.
    frozen = None
    fields = ("npc_phase", "npc_clock", "npc_rng", "npc_loop_timer", "npc_search", "npcs", "npc_pairs")
    for s in states:
        if s["mode"] in ("entry-confirm", "building"):
            current = [s[k] for k in fields]
            if frozen is None:
                frozen = current
            check(current == frozen, "Outdoor state advanced inside a shop")
        else:
            frozen = None
    if live:
        inputs = [json.loads(line)["command"] for line in (live / "inputs.jsonl").read_text().splitlines()]
        check(inputs == json.loads((ROOT / fixture["input_script"]).read_text()) and
              not any(c[0] == "controlled-talk-context" for c in inputs), "Different/controlled original inputs")
        for row in fixture["checkpoints"]:
            snap, ram, actual = original(live, row["label"])
            check(all(actual[k] == row[k] for k in actual), "Original snapshot differs")
            state = int(snap["state_segment"], 16)*16
            check(list(ram[state+0xC614:state+0xC614+17*8:17]) == [0]+[255]*7 and
                  struct.unpack_from("<3I", ram, state+0xD374) == (0, 0, 0), "Party/investment precondition differs")
            check(all((snap[k][0] & 127) == row["position"][axis]
                      for axis, k in enumerate(("party_x_raw", "party_y_raw"))), "Original party position differs")
            if row["text"]:
                check(ram.find(bodies[row["text"]["resource"]]) >= 0, "Original RAM lacks complete shop BLD")
        for prefix, expected in (("armor", [(13, 0, 1), (14, 0, 25)]), ("weapon", [(11, 0, 1)])):
            a, before, _ = original(live, prefix+"-item")
            b, after, _ = original(live, prefix+"-buy")
            x, y = int(a["state_segment"],16)*16+0xC614, int(b["state_segment"],16)*16+0xC614
            changes = [(i, left, right) for i, (left, right) in enumerate(zip(before[x:x+136],after[y:y+136])) if left != right]
            check(changes == expected, "Original purchase altered unmodeled party fields")
        print("PASS: unmodified live original inputs, cursor/party, cash, equipment, result bytes, menu memory and complete RAM BLDs.")
    print(f"PASS: {len(fixture['checkpoints'])} original {stem} checkpoints, exact BLD text hashes, cash/equipment/menu effects, deterministic replay and frozen indoor simulation.")
    return states[-1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=ROOT / "build/btech-headless")
    parser.add_argument("--export", type=Path)
    parser.add_argument("--boundaries", action="store_true")
    parser.add_argument("--reference-run", type=Path)
    parser.add_argument("--native-log", type=Path)
    args = parser.parse_args()
    stem = "reference-shop-boundaries" if args.boundaries else "reference-shops"
    if args.export:
        export(args.export.resolve(), ROOT / "tools" / (stem + ".json"), stem)
        return
    binary = args.binary.resolve()
    compare(binary, stem, args.reference_run)
    if not args.boundaries and not args.reference_run:
        compare(binary, "reference-shop-boundaries")
    if args.native_log:
        expected = (ROOT / "tests/fixtures" / (stem + ".actions")).read_text().splitlines()+["idle"]*5
        check(args.native_log.read_text().splitlines() == expected, "Native SDL input log differs")
        _, replayed = run(binary, args.native_log, "native")
        check(replayed[-1]["mode"] == "local-exploration" and replayed[-1]["equipment"] ==
              {"weapon": 1, "armor": 1, "armor_points": 25}, "Native return/equipment differs")
        print("PASS: native SDL shop inputs replay to the same logical transactions and return.")
    print("Scope: native pacing/layout/fonts and intermediate NPC route positions remain approximate; only the flak vest and knife purchases are supported.")


if __name__ == "__main__":
    main()
