#!/usr/bin/env python3
"""Bounded SDL window/input/presentation check on a private Xvfb display."""
import json
import os
import select
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    work = ROOT / "work"
    work.mkdir(exist_ok=True)
    read_fd, write_fd = os.pipe()
    with (work / "native-xvfb.log").open("w") as log:
        xvfb = subprocess.Popen([str(ROOT / "local-deps/xvfb/usr/bin/Xvfb"),
            "-displayfd", str(write_fd), "-screen", "0", "1024x768x24", "-nolisten", "tcp"],
            pass_fds=(write_fd,), stdout=log, stderr=subprocess.STDOUT)
        os.close(write_fd)
        try:
            if not select.select([read_fd], [], [], 10)[0]:
                raise RuntimeError("Private display did not start")
            number = os.read(read_fd, 32).decode().strip()
            if not number.isdigit():
                raise RuntimeError("Invalid private display number")
            env = dict(os.environ, DISPLAY=":" + number)
            env.pop("SDL_VIDEODRIVER", None)
            result = subprocess.run([str(ROOT / "build/btech-port"), "--smoke",
                "--data", str(ROOT / "Original DOS"), "--record", str(work / "native-x11.actions"),
                "--frame", str(work / "native-x11.ppm")], env=env, timeout=15, check=True,
                capture_output=True, text=True)
            print(result.stdout.strip())
            print("PASS: native X11 window, SDL arrow events, texture presentation, bounded exit.")
            result = subprocess.run([str(ROOT / "build/btech-port"), "--smoke-citadel",
                "--data", str(ROOT / "Original DOS"), "--record", str(work / "native-citadel-x11.actions"),
                "--frame", str(work / "native-citadel-x11.ppm")], env=env, timeout=15, check=True,
                capture_output=True, text=True)
            print(result.stdout.strip())
            subprocess.run(["python3", str(ROOT / "tools/verify_m2.py"), "--native-log",
                str(work / "native-citadel-x11.actions")], check=True, timeout=15)
            print("PASS: native X11 Citadel entry, menu/confirm events, dialogue, exit and recorded replay.")
            result = subprocess.run([str(ROOT / "build/btech-port"), "--smoke-katrina",
                "--data", str(ROOT / "Original DOS"), "--record", str(work / "native-katrina-x11.actions"),
                "--frame", str(work / "native-katrina-x11.ppm")], env=env, timeout=15, check=True,
                capture_output=True, text=True)
            print(result.stdout.strip())
            subprocess.run(["python3", str(ROOT / "tools/verify_m2b.py"), "--native-log",
                str(work / "native-katrina-x11.actions")], check=True, timeout=15)
            print("PASS: native X11 Katrina dialogue, repeat denial, exit/re-entry and recorded replay.")
            result = subprocess.run([str(ROOT / "build/btech-port"), "--smoke-talk",
                "--data", str(ROOT / "Original DOS"), "--record", str(work / "native-talk-x11.actions"),
                "--frame", str(work / "native-talk-x11.ppm")], env=env, timeout=15, check=True,
                capture_output=True, text=True)
            print(result.stdout.strip())
            subprocess.run(["python3", str(ROOT / "tools/verify_m2c.py"), "--native-log",
                str(work / "native-talk-x11.actions")], check=True, timeout=15)
            print("PASS: native X11 controlled Talk menu, Done, retained selection, NPC reply, return, exit and replay.")
            print("Running native X11 MAP1 walk/arrival/conversation (about 84 seconds).", flush=True)
            result = subprocess.run([str(ROOT / "build/btech-port"), "--smoke-arrival",
                "--replay", str(ROOT / "tests/fixtures/citadel-arrival.actions"),
                "--data", str(ROOT / "Original DOS"), "--record", str(work / "native-arrival-x11.actions"),
                "--frame", str(work / "native-arrival-x11.ppm")], env=env, timeout=120, check=True,
                capture_output=True, text=True)
            replayed = subprocess.run([str(ROOT / "build/btech-headless"), "--replay",
                str(work / "native-arrival-x11.actions")], check=True, timeout=15,
                capture_output=True, text=True, cwd=ROOT)
            if json.loads(result.stdout) != json.loads(replayed.stdout):
                raise RuntimeError("Native arrival state differs from its headless input replay")
            print(result.stdout.strip())
            subprocess.run(["python3", str(ROOT / "tools/verify_m2d.py"), "--native-log",
                str(work / "native-arrival-x11.actions")], check=True, timeout=15)
            print("PASS: native X11 normal exploration, NPC arrival/reply, return/exit and full canonical replay equality.")
        finally:
            os.close(read_fd)
            xvfb.terminate()
            try:
                xvfb.wait(timeout=5)
            except subprocess.TimeoutExpired:
                xvfb.kill()
                xvfb.wait()


if __name__ == "__main__":
    main()
