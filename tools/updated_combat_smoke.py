"""Real SDL settings/Space and held Enhanced combat saves on either platform."""
import json
from pathlib import Path
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def run(env, work):
    from reference_session import WindowKeys
    from updated_smoke import run as startup_checks
    startup_checks(env, work, setup_only=True)
    binary = ROOT / "build/btech-headless"
    env = dict(env, SDL_AUDIODRIVER="dummy")
    cases = [
        ("old-updated", "legacy", [], "legacy"),
        ("rules", "settings", [], "legacy"),
        ("enable", "settings", ["Up", "space"], "enhanced"),
        ("disable", "settings", ["Up", "space", "space", "Down", "space"], "legacy"),
        ("target", "target", [], "enhanced"),
        ("retreat", "retreat", [], "enhanced"),
        ("deferred", "deferred", [], "enhanced"),
        ("effects", "effects", [], "enhanced"),
        ("original-import", None, [], "legacy"),
    ]
    with tempfile.TemporaryDirectory(prefix="updated-combat-", dir=work) as directory:
        tmp = Path(directory)
        for label, prerequisite, inputs, rules in cases:
            # Each launch uses a new save path so F9 cannot accidentally read
            # the previous scenario if F5 were to fail.
            base = tmp / f"{label}-slot.btp"
            slot = base.with_name(base.stem + "-updated.btp")
            frame = work / "lrm" / f"native-{label}.ppm"
            expected = tmp / "expected.ppm"
            tail = tmp / "tail.actions"
            start = work / "lrm" / f"{prerequisite}.btp" if prerequisite else ROOT / "Original DOS/GAME3"
            process = subprocess.Popen([str(ROOT / "build/btech-port"), "--edition", "updated",
                "--load", str(start), "--save-file", str(base), "--frame", str(frame)],
                cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            keyboard = WindowKeys()
            try:
                for _ in range(200):
                    found = [w for w, n in keyboard.windows() if n.startswith("BtechPort")]
                    if len(found) == 1:
                        window = found[0]
                        break
                    if process.poll() is not None:
                        raise RuntimeError(label + ": " + process.communicate()[1])
                    time.sleep(.025)
                else:
                    raise RuntimeError(label + " window unavailable")
                time.sleep(.1)
                for key in inputs:
                    keyboard.key(window, key)
                keyboard.key(window, "F5")
                for _ in range(100):
                    if slot.exists():
                        break
                    time.sleep(.02)
                before = json.loads(subprocess.check_output([str(binary), "--load", str(slot)], cwd=ROOT, text=True))
                assert before["combat_rules"] == rules, label
                time.sleep(.15)
                keyboard.key(window, "F9")
                keyboard.key(window, "Ctrl+Shift+Escape")
                out, err = process.communicate(timeout=15)
                if process.returncode or err:
                    raise RuntimeError(label + ": " + err)
                actual = json.loads(out)
                delta = actual["tick"] - before["tick"]
                assert 0 <= delta <= 20, (label, delta)
                tail.write_text("idle\n" * delta)
                wanted = json.loads(subprocess.check_output([str(binary), "--load", str(slot),
                    "--replay", str(tail), "--frame", str(expected)], cwd=ROOT, text=True))
                assert actual == wanted and frame.read_bytes() == expected.read_bytes(), label
                print(f"PASS: Updated {label}, {rules} rules, Space/F5/F9 and exact continued state/pixels.", flush=True)
            finally:
                keyboard.x.XCloseDisplay(keyboard.display)
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=5)
