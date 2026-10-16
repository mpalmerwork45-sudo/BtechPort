"""Bounded SDL checks for the edition selector and Updated broker."""
import json
from pathlib import Path
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def run(env, work):
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

        state, audio, slot, frame, _ = play("selector", ["Escape", "F5"])
        assert state["tick"] == 0 and not audio["opened"] and not slot.exists()
        print("PASS: selector precedes logo/audio; Escape stays open; no game save before selection.", flush=True)
        for name, choice in (("original", ["space"]), ("original-number", ["1"]),
                             ("updated", ["Down", "space"]), ("updated-number", ["2"]),
                             ("updated-keypad", ["KP_Down", "KP_Enter"])):
            updated = name.startswith("updated")
            state, audio, slot, frame, record = play(name, choice + ["F5"])
            chosen = slot.with_name(slot.stem + "-updated.btp") if updated else slot
            assert chosen.read_bytes()[:4] == (b"BTU1" if updated else b"BTS1")
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
        state, audio, _, _, _ = play("bad-roster", ["2"], ["--roster", tmp / "missing.json"], True)
        assert state["tick"] == 0 and not audio["opened"]
        state, _, _, _, _ = play("fallback", ["2", "1"], ["--roster", tmp / "missing.json"], True)
        assert state["mode"] == "logos"
        print("PASS: setup credit shortcut, new-game branch, bad-roster rejection and Original fallback.", flush=True)

        start = tmp / "starport.btp"
        subprocess.run([str(ROOT / "build/btp-roster-tests"), str(ROOT / "Original DOS"),
            str(work / "talk-data.bin"), str(work / "combat-data.bin"), str(work / "world-data.bin"),
            str(ROOT / "content/updated/roster.json"), str(start)], cwd=tmp,
            check=True, capture_output=True, timeout=20)
        for index, price in enumerate((12000, 22000, 36000)):
            inputs = ["space", "Up", "space"] + ["Down"] * index + ["space", "F5", "F9", "Up", "space"]
            state, _, _, _, record = play(f"broker-{index}", inputs, ["--load", start], recording=False)
            assert state["credits"] == 200000 - price and state["campaign"]["mounted"] == 0
            assert state["actions_menu"]["phase"] == 27 and state["actions_menu"]["notice"] == 1
            assert state["mech_types"][0] != 255
        print("PASS: all three SDL purchases with Space, F5/F9 held confirmation, correct price and parked delivery.", flush=True)
