"""Bounded SDL checks for Updated selection, trading and building portraits."""
import json
from pathlib import Path
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def run(env, work, building_art_only=False, setup_only=False):
    from reference_session import WindowKeys
    env = dict(env, SDL_AUDIODRIVER="dummy")
    with tempfile.TemporaryDirectory(prefix="updated-ui-", dir=work) as directory:
        tmp = Path(directory)

        def play(label, inputs, options=(), expect_error=False, recording=True):
            frame = work / f"updated-{label}.ppm"
            report = tmp / "audio.json"
            slot = tmp / f"{label}.btp"
            record = tmp / f"{label}.actions"
            process = subprocess.Popen([str(ROOT / "build/btech-port"), *map(str, options),
                "--save-file", str(slot), *( ["--record", str(record)] if recording else []), "--frame", str(frame),
                "--audio-report", str(report)], cwd=ROOT, env=env,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            keys = WindowKeys()
            try:
                window = None
                for _ in range(200):
                    matches = [w for w, n in keys.windows() if n.startswith("BtechPort")]
                    if len(matches) == 1:
                        window = matches[0]
                        break
                    if process.poll() is not None:
                        raise RuntimeError(process.communicate()[1])
                    time.sleep(.025)
                if window is None:
                    raise RuntimeError("Updated check window did not appear")
                # Allow the first event wait/frame to settle before injection.
                time.sleep(.1)
                for key in inputs:
                    keys.key(window, key)
                    if process.poll() is not None:
                        raise RuntimeError(f"{label}: input unexpectedly closed game")
                keys.key(window, "Ctrl+Shift+Escape")
                out, err = process.communicate(timeout=15)
                if process.returncode or (err and not expect_error):
                    raise RuntimeError(f"{label}: {err}")
                return json.loads(out), json.loads(report.read_text()), slot, frame, record
            finally:
                keys.x.XCloseDisplay(keys.display)
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=5)

        if building_art_only:
            from PIL import Image
            prefix = tmp / "visit"
            subprocess.run([str(ROOT / "build/btp-building-art-tests"), str(ROOT / "Original DOS"),
                str(work / "talk-data.bin"), str(work / "combat-data.bin"), str(work / "world-data.bin"),
                str(ROOT / "content/updated/roster.json"), str(prefix)], cwd=tmp,
                check=True, capture_output=True, timeout=30)
            for name in ("training", "lounge", "prison", "inventor", "cinema", "hospital", "comstar",
                         "clothes", "video-hut", "mayor"):
                state, _, slot, frame, _ = play(f"building-{name}", ["F5", "F9"],
                    ["--load", f"{prefix}-{name}.btp"], recording=False)
                saved = slot.with_name(slot.stem + "-updated.btp")
                assert state["mode"] == "building" and saved.read_bytes()[:4] == b"BTU1"
                with Image.open(frame) as actual, Image.open(ROOT / f"content/updated/art/{name}.png") as expected:
                    assert actual.crop((8, 8, 96, 96)).tobytes() == expected.convert("RGB").tobytes(), name
                restored = tmp / "restored.ppm"
                subprocess.run([str(ROOT / "build/btech-headless"), "--load", str(saved),
                    "--frame", str(restored)], cwd=ROOT, check=True, capture_output=True, timeout=10)
                assert frame.read_bytes() == restored.read_bytes(), name
                print(f"PASS: {name} native window, exact portrait, F5/F9 and restored full frame.", flush=True)
            return

        state, audio, slot, frame, _ = play("selector", ["Escape", "F5"])
        assert state["tick"] == 0 and not audio["opened"] and not slot.exists()
        print("PASS: selector precedes logo/audio; Escape stays open; no game save before selection.", flush=True)
        for name, choice in (("original", ["space"]), ("original-number", ["1"]),
                             ("updated", ["Down", "space"]), ("updated-number", ["2"]),
                             ("updated-keypad", ["KP_Down", "KP_Enter"])):
            updated = name.startswith("updated")
            state, audio, slot, frame, record = play(name, choice + ["F5"])
            chosen = slot.with_name(slot.stem + "-updated.btp") if updated else slot
            assert chosen.read_bytes()[:4] == (b"BTU2" if updated else b"BTS1")
            if updated:
                assert state["combat_rules"] == "enhanced"
            if updated:
                assert not slot.exists()
            assert state["mode"] == "logos", state["mode"]
            # The selected edition still shows exactly the original logo.
            expected = tmp / "expected.ppm"
            subprocess.run([str(ROOT / "build/btech-headless"), "--load", str(chosen),
                "--frame", str(expected)], cwd=ROOT, check=True, capture_output=True, timeout=10)
            assert frame.read_bytes() == expected.read_bytes()
            print(f"PASS: {name} selection, logo, save namespace and automatic edition detection.", flush=True)
        state, _, _, _, _ = play("credit", ["Shift+k+y+r", "2", "space", "space", "Return"])
        assert state["credits"] == 10035 and state["mode"] == "local-exploration", state
        assert state["combat_rules"] == "enhanced"
        state, audio, _, _, _ = play("bad-roster", ["2"], ["--roster", tmp / "missing.json"], True)
        assert state["tick"] == 0 and not audio["opened"]
        state, _, _, _, _ = play("fallback", ["2", "1"], ["--roster", tmp / "missing.json"], True)
        assert state["mode"] == "logos"
        print("PASS: setup credit shortcut, new-game branch, bad-roster rejection and Original fallback.", flush=True)
        if setup_only:
            return

        start = tmp / "starport.btp"
        subprocess.run([str(ROOT / "build/btp-roster-tests"), str(ROOT / "Original DOS"),
            str(work / "talk-data.bin"), str(work / "combat-data.bin"), str(work / "world-data.bin"),
            str(ROOT / "content/updated/roster.json"), str(start)], cwd=tmp,
            check=True, capture_output=True, timeout=20)
        catalogue = json.loads((ROOT / "content/updated/roster.json").read_text())["mechs"]
        for model in (0, 1, 2, *range(13, len(catalogue))):
            for damaged in range(2):
                (work / f"updated-inspect-{model}-{damaged}.ppm").write_bytes(
                    Path(f"{start}-inspect-{model}-{damaged}.ppm").read_bytes())
        state, _, _, _, _ = play("broker-door", ["Up"], ["--load", start])
        assert state["mode"] == "entry-confirm"
        state, _, _, _, _ = play("broker-hub", ["Up", "space"], ["--load", start])
        assert state["actions_menu"]["phase"] == 28
        state, _, _, _, _ = play("broker-stock", ["Up", "space", "space", "Down", "Down"], ["--load", start])
        assert state["actions_menu"]["phase"] == 25
        for index, price in enumerate((12000, 22000, 36000)):
            inputs = ["Up", "space", "space"] + ["Down"] * index + ["space", "F5", "F9", "Up", "space"]
            state, _, _, _, record = play(f"broker-{index}", inputs, ["--load", start], recording=False)
            assert state["credits"] == 200000 - price and state["campaign"]["mounted"] == 0
            assert state["actions_menu"]["phase"] == 27 and state["actions_menu"]["notice"] == 1
            assert state["mech_types"][0] != 255
        print("PASS: added Starport doorway, broker counter and all three Space/F5/F9 purchases.", flush=True)
        # Cross both scrolling boundaries with real keyboard events. Held
        # saves retain the viewport and absolute model, including the two
        # Crusaders sharing an initial and the Atlas's later catalogue code.
        browse = ["Up", "space", "space"]
        state, _, _, _, _ = play("broker-scroll", browse + ["Down"] * 8 + ["F5", "F9"],
            ["--load", start], recording=False)
        assert state["actions_menu"]["phase"] == 25 and state["actions_menu"]["selected"] == 7
        state, _, _, _, _ = play("broker-atlas-confirm", browse + ["Down"] * 14 + ["space"], ["--load", start])
        assert state["actions_menu"]["phase"] == 26 and state["actions_menu"]["selected"] == 1
        for index, price, label in ((13, 50000, "zeus"), (14, 70000, "atlas"),
                                    (15, 37000, "crusader-lrm"), (16, 39000, "crusader-srm"),
                                    (17, 25000, "phoenix-hawk"), (18, 31000, "dragon"),
                                    (19, 45000, "grasshopper"), (20, 62000, "highlander"),
                                    (21, 57000, "stalker"), (22, 15000, "jenner")):
            state, _, _, _, _ = play(f"broker-{label}", browse + ["Down"] * index +
                ["space", "F5", "F9", "Up", "space"], ["--load", start], recording=False)
            assert state["credits"] == 200000 - price and state["actions_menu"]["notice"] == 1
        state, _, _, _, _ = play("broker-last-row", browse + ["Up", "Up"], ["--load", start])
        assert state["actions_menu"]["phase"] == 25 and state["actions_menu"]["selected"] == 6
        state, _, _, _, _ = play("broker-last-back", browse + ["Down"] * len(catalogue) + ["space", "F5"], ["--load", start])
        assert state["actions_menu"]["phase"] == 28 and state["actions_menu"]["selected"] == 0
        print("PASS: scrolling, wrap, held selection, ten later-model purchases and final Back row.", flush=True)
        # Buy four, attempt a fifth, then sell a middle bay. The saved result
        # is reused to check the actual visible list and freed-bay purchase.
        inputs = ["Up", "space", "space"] + ["space", "Up", "space", "space"] * 4
        state, _, _, _, _ = play("broker-full", inputs + ["space", "Up", "space"], ["--load", start])
        assert state["credits"] == 152000 and state["actions_menu"]["notice"] == 3
        sale_menu = inputs + ["BackSpace", "Down", "space", "Down"]
        state, _, _, _, _ = play("broker-sale-list", sale_menu, ["--load", start])
        assert state["actions_menu"]["phase"] == 29
        state, _, _, _, _ = play("broker-sale-confirm", sale_menu + ["space"], ["--load", start])
        assert state["actions_menu"]["phase"] == 30
        state, _, slot, _, _ = play("broker-sale", sale_menu + ["space", "F5", "F9", "Up", "space", "F5"],
            ["--load", start], recording=False)
        assert state["credits"] == 158000 and state["actions_menu"]["phase"] == 31
        assert state["actions_menu"]["notice"] == 5 and state["mech_types"][1] == 255
        sold = slot.with_name(slot.stem + "-updated.btp")
        state, _, _, _, _ = play("broker-replace", ["BackSpace", "space", "Down", "Down", "space", "Up", "space"], ["--load", sold])
        assert state["credits"] == 122000 and state["mech_types"][1] == ord("C")
        print("PASS: full bays reject payment; selling with held save/load frees the chosen bay for replacement.", flush=True)
