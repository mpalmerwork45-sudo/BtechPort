#!/usr/bin/env python3
"""Bounded SDL window/input/presentation check on a private Xvfb display."""
import json
import os
import select
import subprocess
import argparse
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def saves(env, work):
    from reference_session import WindowKeys
    with tempfile.TemporaryDirectory(prefix="native-save-",dir=work) as directory:
        tmp = Path(directory); start = tmp/"start.btp"; slot = tmp/"slot.btp"
        prefix = tmp/"prefix.actions"
        fixture = json.loads((ROOT/"tests/fixtures/reference-bank.json").read_text())
        tick = next(c["tick"] for c in fixture["checkpoints"] if c["label"] == "bank-invest-amount")
        lines = (ROOT/"tests/fixtures/reference-bank.actions").read_text().splitlines()[:tick]
        prefix.write_text("\n".join(lines)+"\n")
        subprocess.run([str(ROOT/"build/btech-headless"),"--replay",str(prefix),"--save",str(start)],
            check=True,capture_output=True,text=True,cwd=ROOT,timeout=20)
        process = subprocess.Popen([str(ROOT/"build/btech-port"),"--load",str(start),
            "--save-file",str(slot),"--frame",str(work/"native-save-load.ppm")],
            env=env,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        keys = WindowKeys()
        try:
            window = None
            for _ in range(100):
                found = [(w,n) for w,n in keys.windows() if n.startswith("BtechPort")]
                if len(found) == 1: window = found[0][0]; break
                if process.poll() is not None: raise RuntimeError("Save/load window failed to start")
                time.sleep(0.05)
            if window is None: raise RuntimeError("Save/load window did not appear")
            keys.key(window,"F9") # Missing slot must retain the current amount editor.
            keys.key(window,"1"); keys.key(window,"F5")
            for _ in range(100):
                if slot.exists(): break
                time.sleep(0.02)
            saved = subprocess.run([str(ROOT/"build/btech-headless"),"--load",str(slot)],
                check=True,capture_output=True,text=True,cwd=ROOT,timeout=20)
            state = json.loads(saved.stdout)
            if state["bank_input"] != "1" or state["bank_phase"] != 2 or state["credits"] != 35:
                raise RuntimeError("Native F5 did not save the partial amount after a failed load")
            keys.key(window,"2"); keys.key(window,"F9") # Restore 1 after editing to 12.
            keys.key(window,"Return"); keys.key(window,"Escape")
            stdout,stderr = process.communicate(timeout=10)
            if process.returncode or "Cannot open save" not in stderr: raise RuntimeError(stderr)
            tail = tmp/"tail.actions"; tail.write_text("accept\n")
            expected = subprocess.run([str(ROOT/"build/btech-headless"),"--load",str(slot),
                "--replay",str(tail)],check=True,capture_output=True,text=True,cwd=ROOT,timeout=20)
            actual = json.loads(stdout); wanted = json.loads(expected.stdout)
            # Wall-clock idle ticks indoors affect only the counter; the full
            # logical state and next transaction must match the saved restart.
            actual.pop("tick"); wanted.pop("tick")
            if actual != wanted or actual["credits"] != 34 or actual["investments"] != [1,0,0]:
                raise RuntimeError("Native F9 restore/transaction differs from process-restarted save")
            print("PASS: native F5 save/F9 load, partial amount, failed-load preservation and identical transaction continuation.",flush=True)
        finally:
            keys.x.XCloseDisplay(keys.display)
            if process.poll() is None:
                process.terminate()
                try: process.wait(timeout=5)
                except subprocess.TimeoutExpired: process.kill(); process.wait()


def shops(env, work):
    print("Running native X11 two-shop walk/purchases/return (about 98 seconds).", flush=True)
    result = subprocess.run([str(ROOT / "build/btech-port"), "--smoke-shops",
        "--replay", str(ROOT / "tests/fixtures/reference-shops.actions"),
        "--data", str(ROOT / "Original DOS"), "--record", str(work / "native-shops-x11.actions"),
        "--frame", str(work / "native-shops-x11.ppm")], env=env, timeout=140, check=True,
        capture_output=True, text=True, cwd=ROOT)
    replayed = subprocess.run([str(ROOT / "build/btech-headless"), "--replay",
        str(work / "native-shops-x11.actions")], check=True, timeout=15,
        capture_output=True, text=True, cwd=ROOT)
    if json.loads(result.stdout) != json.loads(replayed.stdout):
        raise RuntimeError("Native shop state differs from complete headless input replay")
    print(result.stdout.strip())
    subprocess.run(["python3", str(ROOT / "tools/verify_m2e.py"), "--native-log",
        str(work / "native-shops-x11.actions")], check=True, timeout=20)
    print("PASS: native X11 two shops, purchases, outdoor return and complete canonical replay equality.")


def m2f(env, work, input_only=False):
    scenarios = ("bank-editor",) if input_only else ("bank","bank-rates","armor-talk","weapon-talk","bank-editor")
    for scenario in scenarios:
        path = ROOT/"tests/fixtures"/("reference-"+scenario+".actions")
        if scenario == "bank-editor":
            # Synthetic editor inputs appended to the verified ordinary entry.
            # Escape must clear the amount instead of closing the SDL window.
            fixture = json.loads((ROOT/"tests/fixtures/reference-bank.json").read_text())
            amount_tick = next(c["tick"] for c in fixture["checkpoints"] if c["label"] == "bank-invest-amount")
            prefix = (ROOT/"tests/fixtures/reference-bank.actions").read_text().splitlines()[:amount_tick]
            path = work/"native-bank-editor-input.actions"
            path.write_text("\n".join(prefix+["0","1","2","cancel","clear","3","0","accept","accept"])+"\n")
        record = work/("native-"+scenario+"-x11.actions")
        frame = work/("native-"+scenario+"-x11.ppm")
        initial = ["--shop-talk-checkpoint","armor" if scenario.startswith("armor") else "weapon"] if scenario.endswith("talk") else []
        ticks = len(path.read_text().splitlines())+5
        print(f"Running native X11 {scenario}, {ticks} ticks (about {ticks*0.032:.0f} seconds).",flush=True)
        result = subprocess.run([str(ROOT/"build/btech-port"),"--smoke-replay","--replay",str(path),
            "--record",str(record),"--frame",str(frame),*initial],env=env,timeout=ticks*0.032+35,
            check=True,capture_output=True,text=True,cwd=ROOT)
        replayed = subprocess.run([str(ROOT/"build/btech-headless"),"--replay",str(record),*initial],
            check=True,timeout=20,capture_output=True,text=True,cwd=ROOT)
        if record.read_text().splitlines() != path.read_text().splitlines()+["idle"]*5 or json.loads(result.stdout) != json.loads(replayed.stdout):
            raise RuntimeError(f"Native {scenario} input/final state differs from complete headless replay")
        if scenario == "bank-editor":
            state = json.loads(result.stdout)
            if state["credits"] != 5 or state["investments"] != [30,0,0]:
                raise RuntimeError("Native editor failed leading-zero, erasure, Escape clear or Enter submission")
        print(f"PASS: native X11 {scenario}, SDL input/presentation and complete canonical state equality.",flush=True)
    subprocess.run(["python3",str(ROOT/"tools/verify_m2f.py")],check=True,timeout=30,cwd=ROOT)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shops-only", action="store_true")
    parser.add_argument("--m2f-only", action="store_true")
    parser.add_argument("--bank-input-only", action="store_true")
    parser.add_argument("--save-only", action="store_true")
    args = parser.parse_args()
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
            os.environ["DISPLAY"] = env["DISPLAY"]
            os.environ["BTECH_REFERENCE_VIRTUAL"] = "1"
            if args.shops_only:
                shops(env, work)
                return
            if args.m2f_only:
                m2f(env,work)
                return
            if args.bank_input_only:
                m2f(env,work,input_only=True)
                return
            if args.save_only:
                saves(env,work)
                return
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
            shops(env, work)
            m2f(env, work)
            saves(env,work)
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
