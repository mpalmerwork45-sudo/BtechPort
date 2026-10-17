"""Project SDL/load/save checks using the same snapshot in both frontends."""
import json
from pathlib import Path
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def run(env, work):
    from reference_session import WindowKeys
    env = dict(env, SDL_AUDIODRIVER="dummy")
    with tempfile.TemporaryDirectory(prefix="project-ui-", dir=work) as directory:
        tmp = Path(directory)
        prefix = tmp / "fixture"
        args = ["--project", ROOT / "examples/project-demo", "--data", ROOT / "Original DOS",
                "--dialogue-data", work / "talk-data.bin", "--combat-data", work / "combat-data.bin",
                "--world-data", work / "world-data.bin"]
        subprocess.run([str(ROOT / "build/btp-project-tests"), str(ROOT / "Original DOS"),
                        str(work / "talk-data.bin"), str(work / "combat-data.bin"), str(work / "world-data.bin"),
                        str(ROOT / "content/updated/roster.json"), str(ROOT / "examples/project-demo"), str(prefix)],
                       cwd=ROOT, check=True, capture_output=True, text=True, timeout=30)
        for label in ["start", "broker", "purchase", "weapons", "report"]:
            slot = tmp / f"{label}.btp"
            final = tmp / f"{label}-final.btp"
            frame = work / f"project-{label}.ppm"
            process = subprocess.Popen([str(ROOT / "build/btech-port"), *map(str, args),
                "--load", f"{prefix}-{label}.btp", "--save-file", str(slot), "--save", str(final), "--frame", str(frame)],
                cwd=tmp, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            keys = WindowKeys()
            try:
                window = None
                for _ in range(200):
                    matches = [w for w, name in keys.windows() if "Workshop CHI project" in name]
                    if len(matches) == 1:
                        window = matches[0]
                        break
                    if process.poll() is not None:
                        raise RuntimeError(process.communicate()[1])
                    time.sleep(.025)
                if window is None:
                    raise RuntimeError("Project window did not appear")
                time.sleep(.1)
                keys.key(window, "F5")
                keys.key(window, "F9")
                keys.key(window, "Ctrl+Shift+Escape")
                out, err = process.communicate(timeout=15)
                if process.returncode or err:
                    raise RuntimeError(f"{label}: {err}")
                native = json.loads(out)
                saved = slot.with_name(slot.stem + "-project-workshop.btp")
                assert saved.read_bytes()[:4] == b"BTG1"
                restored = tmp / "restored.ppm"
                headless = subprocess.run([str(ROOT / "build/btech-headless"), *map(str, args),
                    "--load", str(final), "--frame", str(restored)], cwd=tmp, check=True,
                    capture_output=True, text=True, timeout=10)
                assert native["state_digest"] == json.loads(headless.stdout)["state_digest"], label
                assert frame.read_bytes() == restored.read_bytes(), label
                print(f"PASS: project {label}, F5/F9, package save, identical native/headless frame.", flush=True)
            finally:
                keys.x.XCloseDisplay(keys.display)
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=5)
