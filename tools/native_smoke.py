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
    print("Running accelerated native X11 two-shop walk/purchases/return.", flush=True)
    result = subprocess.run([str(ROOT / "build/btech-port"), "--smoke-shops", "--smoke-fast",
        "--replay", str(ROOT / "tests/fixtures/reference-shops.actions"),
        "--data", str(ROOT / "Original DOS"), "--record", str(work / "native-shops-x11.actions"),
        "--frame", str(work / "native-shops-x11.ppm")], env=env, timeout=140, check=True,
        capture_output=True, text=True, cwd=ROOT)
    replayed = subprocess.run([str(ROOT / "build/btech-headless"), "--replay",
        str(work / "native-shops-x11.actions"), "--frame", str(work / "replayed-shops.ppm")], check=True, timeout=15,
        capture_output=True, text=True, cwd=ROOT)
    if (work / "native-shops-x11.actions").read_text().splitlines() != (ROOT / "tests/fixtures/reference-shops.actions").read_text().splitlines()+["idle"]*5 or json.loads(result.stdout) != json.loads(replayed.stdout) or (work / "native-shops-x11.ppm").read_bytes() != (work / "replayed-shops.ppm").read_bytes():
        raise RuntimeError("Native shop inputs/state/frame differ from complete headless input replay")
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
        print(f"Running accelerated native X11 {scenario}, {ticks} logical ticks.",flush=True)
        result = subprocess.run([str(ROOT/"build/btech-port"),"--smoke-replay","--smoke-fast","--replay",str(path),
            "--record",str(record),"--frame",str(frame),*initial],env=env,timeout=ticks*0.032+35,
            check=True,capture_output=True,text=True,cwd=ROOT)
        replayed_frame=work/("replayed-"+scenario+".ppm")
        replayed = subprocess.run([str(ROOT/"build/btech-headless"),"--replay",str(record),"--frame",str(replayed_frame),*initial],
            check=True,timeout=20,capture_output=True,text=True,cwd=ROOT)
        if record.read_text().splitlines() != path.read_text().splitlines()+["idle"]*5 or json.loads(result.stdout) != json.loads(replayed.stdout) or frame.read_bytes() != replayed_frame.read_bytes():
            raise RuntimeError(f"Native {scenario} input/final state/frame differs from complete headless replay")
        if scenario == "bank-editor":
            state = json.loads(result.stdout)
            if state["credits"] != 5 or state["investments"] != [30,0,0]:
                raise RuntimeError("Native editor failed leading-zero, erasure, Escape clear or Enter submission")
        print(f"PASS: native X11 {scenario}, SDL input/presentation and complete canonical state equality.",flush=True)
    subprocess.run(["python3",str(ROOT/"tools/verify_m2f.py")],check=True,timeout=30,cwd=ROOT)


def school(env, work):
    path = ROOT/"tests/fixtures/reference-class-funded.actions"
    record = work/"native-class-x11.actions"; frame = work/"native-class-x11.ppm"
    ticks = len(path.read_text().splitlines())+5
    print(f"Running accelerated native X11 funded course/cooldown/re-enrolment, {ticks} logical ticks.",flush=True)
    result = subprocess.run([str(ROOT/"build/btech-port"),"--smoke-replay","--smoke-fast","--replay",str(path),
        "--record",str(record),"--frame",str(frame)],env=env,timeout=ticks*0.032+35,
        check=True,capture_output=True,text=True,cwd=ROOT)
    replayed_frame=work/"replayed-class.ppm"
    replayed = subprocess.run([str(ROOT/"build/btech-headless"),"--replay",str(record),"--frame",str(replayed_frame)],
        check=True,capture_output=True,text=True,cwd=ROOT,timeout=20)
    if record.read_text().splitlines() != path.read_text().splitlines()+["idle"]*5 or json.loads(result.stdout) != json.loads(replayed.stdout) or frame.read_bytes() != replayed_frame.read_bytes():
        raise RuntimeError("Native Class inputs/final state/frame differ from complete headless replay")
    subprocess.run(["python3",str(ROOT/"tools/verify_m2h.py"),"--native-log",str(record)],
        check=True,timeout=30,cwd=ROOT)
    print("PASS: native X11 ordinary funding, paid Class, cooldown refusal/expiry and repeat enrolment; complete canonical state equality.",flush=True)


def sprites(env, work):
    from reference_session import WindowKeys
    record = work/'native-sprites.actions'
    frame = work/'native-sprites.ppm'
    actual = subprocess.run([str(ROOT/'build/btech-port'),'--smoke','--record',str(record),
        '--frame',str(frame)],env=env,cwd=ROOT,capture_output=True,text=True,check=True,timeout=15)
    expected = subprocess.run([str(ROOT/'build/btech-headless'),'--replay',str(record),
        '--frame',str(work/'replayed-sprites.ppm')],cwd=ROOT,capture_output=True,text=True,check=True,timeout=15)
    if json.loads(actual.stdout) != json.loads(expected.stdout) or frame.read_bytes() != (work/'replayed-sprites.ppm').read_bytes():
        raise RuntimeError('Native sprite state/frame differs from headless replay')
    process = subprocess.Popen([str(ROOT/'build/btech-port'),'--sprite-preview',
        '--frame',str(work/'native-mechs.ppm')],env=env,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    keys = WindowKeys()
    try:
        window = None
        for _ in range(100):
            found = [(w,n) for w,n in keys.windows() if n.startswith('BtechPort')]
            if len(found) == 1: window = found[0][0]; break
            if process.poll() is not None: raise RuntimeError('Sprite preview failed to start')
            time.sleep(0.05)
        if window is None: raise RuntimeError('Sprite preview window did not appear')
        time.sleep(0.5)
        keys.key(window,'Escape')
        out,err = process.communicate(timeout=10)
        if process.returncode: raise RuntimeError(err)
        tick = json.loads(out)['tick']
        # Only two small animated examples vary with time; the static grid must match.
        subprocess.run([str(ROOT/'build/btech-headless'),'--sprite-preview','--frame',str(work/'mechs-headless.ppm')],
            cwd=ROOT,capture_output=True,check=True,timeout=15)
        a=(work/'native-mechs.ppm').read_bytes(); b=(work/'mechs-headless.ppm').read_bytes()
        header=len(b'P6\n320 200\n255\n')
        if not tick or any(a[header+(y*320+72)*3:header+(y*320+320)*3] !=
                           b[header+(y*320+72)*3:header+(y*320+320)*3] for y in range(200)):
            raise RuntimeError('Native mech preview did not animate or its grid differs')
        print('PASS: native sprite movement/frame replay; animated mech preview, static grid and Escape exit.',flush=True)
    finally:
        keys.x.XCloseDisplay(keys.display)
        if process.poll() is None:
            process.terminate()
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired: process.kill(); process.wait()


def diagonals(env, work):
    from reference_session import WindowKeys
    from verify_m2j import rewrite_save
    import struct
    binary=ROOT/'build/btech-headless'
    with tempfile.TemporaryDirectory(prefix='native-diagonal-',dir=work) as directory:
        tmp=Path(directory)
        for kind in ('human','mech','bank-keypad'):
            start=tmp/(kind+'.btp'); prefix=tmp/'prefix.actions'
            if kind == 'mech':
                f=json.loads((ROOT/'tests/fixtures/reference-mission-pass.json').read_text())
                tick=next(r['tick'] for r in f['checkpoints'] if r['label']=='mission-start')
                lines=(ROOT/'tests/fixtures/reference-mission-pass.actions').read_text().splitlines()[:tick]
            elif kind == 'bank-keypad':
                f=json.loads((ROOT/'tests/fixtures/reference-bank.json').read_text())
                tick=next(r['tick'] for r in f['checkpoints'] if r['label']=='bank-invest-amount')
                lines=(ROOT/'tests/fixtures/reference-bank.actions').read_text().splitlines()[:tick]
            else: lines=[]
            prefix.write_text(''.join(a+'\n' for a in lines))
            subprocess.run([str(binary),'--replay',str(prefix),'--save',str(start)],
                cwd=ROOT,check=True,capture_output=True,timeout=20)
            if kind == 'human':
                rewrite_save(start,lambda b: struct.pack_into('<HH',b,12,64,79))
            record=work/('native-diagonal-'+kind+'.actions')
            process=subprocess.Popen([str(ROOT/'build/btech-port'),'--load',str(start),
                '--record',str(record),'--frame',str(work/('native-diagonal-'+kind+'.ppm'))],
                env=env,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            keys=WindowKeys()
            try:
                window=None
                for _ in range(100):
                    found=[(w,n) for w,n in keys.windows() if n.startswith('BtechPort')]
                    if len(found)==1: window=found[0][0]; break
                    if process.poll() is not None: raise RuntimeError('Diagonal window failed to start')
                    time.sleep(.05)
                if window is None: raise RuntimeError('Diagonal window did not appear')
                if kind == 'bank-keypad':
                    for k in ('Num_Lock','KP_1','KP_2','BackSpace','Escape','KP_3','KP_0','KP_Enter','Return'):
                        keys.key(window,k)
                    time.sleep(.1)
                    keys.key(window,'Num_Lock')
                else:
                    for k in ('Home','Prior','End','Next','KP_7','KP_9','KP_1','KP_3'):
                        keys.key(window,k)
                    for k in ('Up+Left','Up+Right','Down+Left','Down+Right'):
                        keys.key(window,k,press_gap=0)
                    keys.key(window,'Right') # All released: cardinal again.
                keys.key(window,'Escape')
                out,err=process.communicate(timeout=10)
                if process.returncode: raise RuntimeError(err)
                expected=subprocess.run([str(binary),'--load',str(start),'--replay',str(record)],
                    cwd=ROOT,check=True,capture_output=True,text=True,timeout=20)
                actual=json.loads(out)
                if actual != json.loads(expected.stdout): raise RuntimeError(kind+' native diagonal/keypad replay differs')
                inputs=[a for a in record.read_text().splitlines() if a != 'idle']
                if kind == 'bank-keypad':
                    if inputs != ['1','2','cancel','clear','3','0','accept','accept'] or actual['credits'] != 5 or actual['investments'] != [30,0,0]:
                        raise RuntimeError('Bank keypad stopped accepting digits/clear/Enter')
                else:
                    wanted=['up-left','up-right','down-left','down-right']*3+['right']
                    if inputs != wanted: raise RuntimeError(kind+' diagonal key/chord/release mismatch: '+repr(inputs))
                    if actual['x_half'] != 65 or actual['y_half'] != 79: raise RuntimeError(kind+' diagonal axes did not move together')
                print('PASS: native '+kind+' keys, arrow chords/releases, complete replay and final state.',flush=True)
            finally:
                keys.x.XCloseDisplay(keys.display)
                if process.poll() is None:
                    process.terminate()
                    try: process.wait(timeout=5)
                    except subprocess.TimeoutExpired: process.kill(); process.wait()


def training(env, work):
    from reference_session import WindowKeys
    from verify_m2j import seed
    binary=ROOT/"build/btech-headless"
    with tempfile.TemporaryDirectory(prefix="native-training-",dir=work) as directory:
        tmp=Path(directory)
        for kind in ("mission-pass","mission-fail","full-goods","lounge"):
            path=ROOT/"tests/fixtures"/("reference-"+kind+".actions")
            record=work/("native-"+kind+".actions"); frame=work/("native-"+kind+".ppm")
            initial=seed(binary,kind,tmp); ticks=len(path.read_text().splitlines())+5
            print(f"Running accelerated native {kind}: {ticks} SDL input/presentation ticks.",flush=True)
            result=subprocess.run([str(ROOT/"build/btech-port"),"--smoke-replay","--smoke-fast","--replay",str(path),
                "--record",str(record),"--frame",str(frame),*map(str,initial)],
                cwd=ROOT,env=env,check=True,capture_output=True,text=True,timeout=ticks*.032+30)
            replayed_frame=tmp/(kind+".ppm")
            expected=subprocess.run([str(binary),*map(str,initial),"--replay",str(record),"--frame",str(replayed_frame)],
                cwd=ROOT,check=True,capture_output=True,text=True,timeout=20)
            if record.read_text().splitlines() != path.read_text().splitlines()+["idle"]*5 or json.loads(result.stdout) != json.loads(expected.stdout) or frame.read_bytes() != replayed_frame.read_bytes():
                raise RuntimeError(kind+" native input/final state/frame differs from complete headless replay")
            print("PASS: native "+kind+" complete inputs/state equal the canonical replay.",flush=True)
        fixture=json.loads((ROOT/"tests/fixtures/reference-mission-pass.json").read_text())
        lines=(ROOT/"tests/fixtures/reference-mission-pass.actions").read_text().splitlines()
        for label in ("quiz-1","mission-start","dream3"):
            tick=next(r["tick"] for r in fixture["checkpoints"] if r["label"] == label)
            prefix=tmp/"prefix.actions"; prefix.write_text("".join(a+"\n" for a in lines[:tick]))
            start=tmp/"start.btp"; slot=tmp/"slot.btp"
            subprocess.run([str(binary),"--replay",str(prefix),"--save",str(start)],
                cwd=ROOT,check=True,capture_output=True,timeout=20)
            process=subprocess.Popen([str(ROOT/"build/btech-port"),"--load",str(start),
                "--save-file",str(slot),"--frame",str(work/("native-"+label+".ppm"))],
                cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            keys=WindowKeys()
            try:
                window=None
                for _ in range(100):
                    found=[(w,n) for w,n in keys.windows() if n.startswith("BtechPort")]
                    if len(found)==1: window=found[0][0]; break
                    if process.poll() is not None: raise RuntimeError("Training save window failed to start")
                    time.sleep(.05)
                if window is None: raise RuntimeError("Training save window did not appear")
                keys.key(window,"F5")
                time.sleep(.15)
                saved=subprocess.run([str(binary),"--load",str(slot)],cwd=ROOT,check=True,capture_output=True,text=True,timeout=20)
                before=json.loads(saved.stdout)
                keys.key(window,"Down" if label=="quiz-1" else "Right" if label=="mission-start" else "Return")
                keys.key(window,"F9"); keys.key(window,"Escape")
                out,err=process.communicate(timeout=10)
                if process.returncode: raise RuntimeError(err)
                actual=json.loads(out); wanted=dict(before)
                actual.pop("tick"); wanted.pop("tick")
                if label=="mission-start":
                    # The restored driving clock legitimately resumes during
                    # the F9/Escape event interval; position/gait/loan stay exact.
                    elapsed=actual["mission"]["elapsed"]; old=wanted["mission"]["elapsed"]
                    if not old <= elapsed <= old+10: raise RuntimeError("Driving clock did not resume the saved interval")
                    actual["mission"]["elapsed"]=old
                    actual["mission"]["idle"]=wanted["mission"]["idle"]
                if actual != wanted: raise RuntimeError(label+" F9 did not restore the complete paused/driving state")
                print("PASS: native F5/F9 restores "+label+" after changing it.",flush=True)
            finally:
                keys.x.XCloseDisplay(keys.display)
                if process.poll() is None:
                    process.terminate()
                    try: process.wait(timeout=5)
                    except subprocess.TimeoutExpired: process.kill(); process.wait()

def rubble(env,work,combat=False,kind=None):
    """Accelerated input-only full route, followed by real-time F5/F9 probes."""
    from reference_session import WindowKeys
    binary=ROOT/"build/btech-headless"
    kind=kind or ("combat" if combat else "rubble-story")
    path=ROOT/("tests/fixtures/ordinary-"+kind+".actions")
    facts=json.loads((ROOT/("tests/fixtures/ordinary-"+kind+".json")).read_text())
    lines=path.read_text().splitlines(); record=work/("native-"+kind+".actions"); frame=work/("native-"+kind+".ppm")
    started=time.monotonic()
    actual=subprocess.run([str(ROOT/"build/btech-port"),"--smoke-replay","--smoke-fast","--replay",str(path),
        "--record",str(record),"--frame",str(frame)],cwd=ROOT,env=env,check=True,capture_output=True,text=True,timeout=90)
    elapsed=time.monotonic()-started
    replayed=work/("native-"+kind+"-replayed.ppm")
    wanted=subprocess.run([str(binary),"--replay",str(record),"--frame",str(replayed)],
        cwd=ROOT,check=True,capture_output=True,text=True,timeout=20)
    if record.read_text().splitlines() != lines+["idle"]*5 or json.loads(actual.stdout) != json.loads(wanted.stdout) or frame.read_bytes() != replayed.read_bytes():
        raise RuntimeError("Accelerated ordinary native route differs from complete headless input/state/frame replay")
    scope={"training-combat":"five-mission robot/duel/Mechit-Lube", "sixth-story":"Rick/device, sixth mission and retries", "kick":"kick combat/victory/report",
        "combat":"three-mission combat/victory/report","rubble-story":"two-mission/rest/third-briefing"}[kind]
    print(f"PASS: ordinary native {scope} SDL route, {len(lines)+5} ticks in {elapsed:.2f}s (normal pacing {32*(len(lines)+5)/1000:.2f}s). Exact input/state/frame equality.",flush=True)
    with tempfile.TemporaryDirectory(prefix="native-"+kind+"-",dir=work) as directory:
        tmp=Path(directory); prefix=tmp/"prefix.actions"; start=tmp/"start.btp"; slot=tmp/"slot.btp"; tail=tmp/"tail.actions"
        labels=("queued-route","movement-replace","combat-effect","mechit-confirm") if kind=="training-combat" else (
            ("rick-talk-menu","rick-scene3","rick-device-exit","sixth-start","sixth-victory") if kind=="sixth-story" else (
            ("kick-target","kick-queued","resolving") if kind=="kick" else (
                ("computer","route-preview","route-confirmed","weapons","target","resolving") if combat else (
                    "rubble-animation","rubble-pickup","rubble-carrying","dream-animation"))))
        for label in labels:
            tick=next(r["tick"] for r in facts["checkpoints"] if r["label"] == label)
            prefix.write_text("".join(a+"\n" for a in lines[:tick]))
            subprocess.run([str(binary),"--replay",str(prefix),"--save",str(start)],cwd=ROOT,check=True,capture_output=True,timeout=20)
            process=subprocess.Popen([str(ROOT/"build/btech-port"),"--load",str(start),"--save-file",str(slot),
                "--frame",str(work/("native-"+label+".ppm"))],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            keys=WindowKeys()
            try:
                window=None
                for _ in range(100):
                    found=[(w,n) for w,n in keys.windows() if n.startswith("BtechPort")]
                    if len(found) == 1: window=found[0][0]; break
                    if process.poll() is not None: raise RuntimeError(kind+" save window failed to start")
                    time.sleep(.05)
                if window is None: raise RuntimeError(kind+" save window did not appear")
                keys.key(window,"F5"); time.sleep(.1)
                before=json.loads(subprocess.run([str(binary),"--load",str(slot)],cwd=ROOT,check=True,capture_output=True,text=True).stdout)
                if label == "rubble-pickup": keys.key(window,"Return")
                keys.key(window,"Right"); time.sleep(.15)
                keys.key(window,"F9"); keys.key(window,"Escape")
                out,err=process.communicate(timeout=10)
                if process.returncode: raise RuntimeError(err)
                restored=json.loads(out); delta=restored["tick"]-before["tick"]
                if not 0 <= delta <= 20: raise RuntimeError("Unexpected post-load real-time interval")
                tail.write_text("idle\n"*delta)
                expected=json.loads(subprocess.run([str(binary),"--load",str(slot),"--replay",str(tail)],
                    cwd=ROOT,check=True,capture_output=True,text=True).stdout)
                if restored != expected: raise RuntimeError(label+" real-time F9 restoration/continuation differs")
                print("PASS: real-time native F5/F9 restores "+label+" and its exact continuation.",flush=True)
                if combat or kind in ("training-combat","kick","sixth-story"):
                    expected_frame=tmp/"restored.ppm"
                    subprocess.run([str(binary),"--load",str(slot),"--replay",str(tail),"--frame",str(expected_frame)],
                        cwd=ROOT,check=True,capture_output=True,timeout=20)
                    if (work/("native-"+label+".ppm")).read_bytes()!=expected_frame.read_bytes():
                        raise RuntimeError(label+" native saved-state pixels differ from headless rendering")
            finally:
                keys.x.XCloseDisplay(keys.display)
                if process.poll() is None:
                    process.terminate()
                    try: process.wait(timeout=5)
                    except subprocess.TimeoutExpired: process.kill(); process.wait()

def world(env,work):
    """Real F4 map toggle, movement, F5/F9 and exact saved-clock pixels."""
    from reference_session import WindowKeys
    binary=ROOT/'build/btech-headless';slot=work/'native-area.btp';frame=work/'native-area.ppm'
    process=subprocess.Popen([str(ROOT/'build/btech-port'),'--save-file',str(slot),'--frame',str(frame)],
        cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    keys=WindowKeys()
    try:
        window=None
        for _ in range(100):
            found=[(w,n) for w,n in keys.windows() if n.startswith('BtechPort')]
            if len(found)==1:window=found[0][0];break
            if process.poll() is not None:raise RuntimeError('Area map window failed to start')
            time.sleep(.05)
        if window is None:raise RuntimeError('Area map window did not appear')
        keys.key(window,'F4');keys.key(window,'F5');time.sleep(.1)
        before=json.loads(subprocess.run([str(binary),'--load',str(slot)],cwd=ROOT,check=True,capture_output=True,text=True).stdout)
        keys.key(window,'Right');keys.key(window,'F4');keys.key(window,'F9');keys.key(window,'F4');keys.key(window,'Escape')
        out,err=process.communicate(timeout=10)
        if process.returncode:raise RuntimeError(err)
        after=json.loads(out);delta=after['tick']-before['tick']
        if not 0<=delta<=20:raise RuntimeError('Unexpected area map restored interval')
        tail=work/'native-area-tail.actions';tail.write_text('idle\n'*delta)
        replay=work/'native-area-replayed.ppm'
        args=[str(binary),'--load',str(slot),'--world-overview','--frame',str(replay)]
        if delta:args+=['--replay',str(tail)]
        expected=json.loads(subprocess.run(args,cwd=ROOT,check=True,capture_output=True,text=True).stdout)
        if after!=expected or frame.read_bytes()!=replay.read_bytes():raise RuntimeError('F4/F9 area state or generated-map pixels differ')
        print('PASS: native F4 generated Citadel area map, F5/F9 state and exact saved-clock pixel continuation.',flush=True)
    finally:
        keys.x.XCloseDisplay(keys.display)
        if process.poll() is None:
            process.terminate()
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.wait()

def campaign(env,work):
    """Check only new milestone tails; prefixes are ordinary-input saves."""
    from reference_session import WindowKeys
    env=dict(env,SDL_AUDIODRIVER='dummy')
    binary=ROOT/'build/btech-headless';native=ROOT/'build/btech-port'
    with tempfile.TemporaryDirectory(prefix='native-campaign-',dir=work) as directory:
        tmp=Path(directory);prefix=tmp/'prefix.actions';start=tmp/'start.btp';tail=tmp/'tail.actions'
        for kind,label in [('invasion','invasion-start'),('invasion-loss','invasion-start'),('starport',None),('rex','civilian-clothing'),('services','rex-and-commando')]:
            lines=(ROOT/f'tests/fixtures/ordinary-{kind}.actions').read_text().splitlines()
            facts=json.loads((ROOT/f'tests/fixtures/ordinary-{kind}.json').read_text())
            tick=next(c['tick'] for c in facts['checkpoints'] if c['label']==label) if label else len((ROOT/'tests/fixtures/ordinary-invasion.actions').read_text().splitlines())
            prefix.write_text('\n'.join(lines[:tick])+'\n');tail.write_text('\n'.join(lines[tick:])+'\n')
            subprocess.run([str(binary),'--replay',str(prefix),'--save',str(start)],cwd=ROOT,check=True,capture_output=True,timeout=20)
            record=work/f'native-{kind}.actions';frame=work/f'native-{kind}.ppm';expected=tmp/'expected.ppm'
            began=time.monotonic()
            actual=subprocess.run([str(native),'--load',str(start),'--replay',str(tail),'--smoke-replay','--smoke-fast','--record',str(record),'--frame',str(frame)],cwd=ROOT,env=env,check=True,capture_output=True,text=True,timeout=45)
            wanted=subprocess.run([str(binary),'--load',str(start),'--replay',str(record),'--frame',str(expected)],cwd=ROOT,check=True,capture_output=True,text=True,timeout=20)
            if record.read_text().splitlines()!=lines[tick:]+['idle']*5 or json.loads(actual.stdout)!=json.loads(wanted.stdout) or frame.read_bytes()!=expected.read_bytes():raise RuntimeError(kind+' native input/state/frame differs')
            print(f'PASS: native {kind} tail, {len(lines)-tick+5} SDL inputs in {time.monotonic()-began:.2f}s; exact state/frame replay.',flush=True)
        probes=[('rex','rex-crest'),('services','partial-ammo-amount'),('title',None)]
        for kind,label in probes:
            if kind=='title':
                prefix.write_text('idle\n'*30)
                opts=['--title-preview','--replay',str(prefix)]
            else:
                facts=json.loads((ROOT/f'tests/fixtures/ordinary-{kind}.json').read_text())
                lines=(ROOT/f'tests/fixtures/ordinary-{kind}.actions').read_text().splitlines()
                tick=next(c['tick'] for c in facts['checkpoints'] if c['label']==label)
                prefix.write_text('\n'.join(lines[:tick])+'\n');opts=['--replay',str(prefix)]
            subprocess.run([str(binary),*opts,'--save',str(start)],cwd=ROOT,check=True,capture_output=True,timeout=20)
            slot=tmp/'slot.btp';frame=work/f'native-{label or kind}-restore.ppm'
            process=subprocess.Popen([str(native),'--load',str(start),'--save-file',str(slot),'--frame',str(frame)],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            keys=WindowKeys()
            try:
                window=None
                for _ in range(100):
                    found=[(w,n) for w,n in keys.windows() if n.startswith('BtechPort')]
                    if len(found)==1:window=found[0][0];break
                    if process.poll() is not None:raise RuntimeError('Native campaign window failed')
                    time.sleep(.02)
                if window is None:raise RuntimeError('Native campaign window did not appear')
                keys.key(window,'F5');time.sleep(.1)
                before=json.loads(subprocess.run([str(binary),'--load',str(slot)],cwd=ROOT,check=True,capture_output=True,text=True).stdout)
                keys.key(window,'Right');time.sleep(.1);keys.key(window,'F9')
                if label=='partial-ammo-amount':
                    # Restore "1", append/erase 0, clear, type 1 again; Space
                    # must leave the amount open. The final state still equals
                    # the saved state plus indoor idle ticks.
                    for key in ('0','BackSpace','Escape','1','space'):keys.key(window,key)
                keys.close_window(window)
                out,err=process.communicate(timeout=10)
                if process.returncode:raise RuntimeError(err)
                restored=json.loads(out);delta=restored['tick']-before['tick']
                if not 0<=delta<=50:raise RuntimeError('Native restore interval was unbounded')
                tail.write_text('idle\n'*delta);expected=tmp/'restored.ppm'
                wanted=subprocess.run([str(binary),'--load',str(slot),'--replay',str(tail),'--frame',str(expected)],cwd=ROOT,check=True,capture_output=True,text=True)
                if restored!=json.loads(wanted.stdout) or frame.read_bytes()!=expected.read_bytes():raise RuntimeError((label or kind)+' native F5/F9 differs')
                print('PASS: native F5/F9 '+(label or 'title music')+' state, clock and pixels.',flush=True)
                if label=='partial-ammo-amount':print('PASS: native ammo digits, Backspace erasure, Escape clear and Space ignored.',flush=True)
            finally:
                keys.x.XCloseDisplay(keys.display)
                if process.poll() is None:process.terminate();process.wait(timeout=5)

def menu(env,work):
    """Ordinary SDL Space/settings and six persistent slots in a private directory."""
    with tempfile.TemporaryDirectory(prefix='native-menu-',dir=work) as directory:
        tmp=Path(directory);base=tmp/'slot.btp';actions=tmp/'route.actions';record=tmp/'record.actions'
        keys=[]
        def choose(row):keys.extend(['down']*row+['accept'])
        def setting(row,selected):
            keys.append('menu');choose(1);choose(0)
            current=0 if row==1 else 1 if row==2 else 2
            keys.extend(['down']*((selected-current)%3)+['accept'])
        previous_steps=1;slot=0
        for wanted in range(6):
            selected=wanted%3;setting(previous_steps,selected);previous_steps=1<<selected
            keys.append('menu');choose(5);keys.extend(['down']*((wanted-slot)%7)+['accept']);slot=wanted
        for wanted in range(6):
            keys.append('menu');choose(4);keys.extend(['down']*((wanted-slot)%7)+['accept']);slot=wanted
        keys.append('menu');choose(2);choose(0);keys.extend(['accept','menu']);choose(6);keys.append('cancel')
        actions.write_text('\n'.join(keys)+'\n')
        frame=work/'native-space-menu.ppm';expected=tmp/'expected.ppm'
        env=dict(env,SDL_AUDIODRIVER='dummy')
        actual=subprocess.run([str(ROOT/'build/btech-port'),'--smoke-replay','--smoke-fast','--replay',str(actions),'--save-file',str(base),'--record',str(record),'--frame',str(frame)],cwd=ROOT,env=env,check=True,capture_output=True,text=True,timeout=20)
        wanted=subprocess.run([str(ROOT/'build/btech-headless'),'--replay',str(record),'--save-file',str(base),'--frame',str(expected)],cwd=ROOT,check=True,capture_output=True,text=True,timeout=20)
        if record.read_text().splitlines()!=keys+['idle']*5 or json.loads(actual.stdout)!=json.loads(wanted.stdout) or frame.read_bytes()!=expected.read_bytes():raise RuntimeError('Native menu inputs/state/pixels differ')
        for number in range(1,7):
            path=base if number==1 else tmp/f'slot-{number}.btp'
            state=json.loads(subprocess.run([str(ROOT/'build/btech-headless'),'--load',str(path)],cwd=ROOT,check=True,capture_output=True,text=True).stdout)
            if state['actions_menu']['steps']!=1<<((number-1)%3):raise RuntimeError('Slot did not retain its separate movement setting')
        print(f'PASS: native Space/settings/inspection/overhead, all six saves and loads, {len(keys)+5} exact SDL inputs and pixels.',flush=True)

def presentation(env,work):
    """Focused, real-time SDL checks, seeded by ordinary logical input saves."""
    binary=ROOT/'build/btech-headless';native=ROOT/'build/btech-port'
    source=ROOT/'tests/fixtures/ordinary-combat.actions';lines=source.read_text().splitlines()
    rows=[json.loads(row) for row in subprocess.check_output([str(binary),'--replay',str(source),'--trace'],cwd=ROOT,text=True).splitlines()]
    fight=ROOT/'tests/fixtures/ordinary-training-combat.actions'
    battle=[json.loads(row) for row in subprocess.check_output([str(binary),'--replay',str(fight),'--trace'],cwd=ROOT,text=True).splitlines()]
    cases=[('entry',source,next(i for i,s in enumerate(rows) if s['mode']=='entry-confirm'),['idle']*2),
        ('combat-control',source,next(i for i,s in enumerate(rows) if s['combat']['phase']==1 and not s['animation']['active']),['idle']*2),
        ('combat-sound',source,next(i for i,s in enumerate(rows) if s['audio']['effects']),['idle']*30),
        ('combat-outtake',fight,next(i for i,s in enumerate(battle) if s['animation']['active']==3),['idle']*30),
        ('return-to-base',source,next(i for i,s in enumerate(rows) if s['mission']['phase']==7),['idle']*2+['accept'])]
    with tempfile.TemporaryDirectory(prefix='native-presentation-',dir=work) as directory:
        tmp=Path(directory)
        for name,path,tick,keys in cases:
            prefix=tmp/'prefix.actions';start=tmp/'start.btp';tail=tmp/'tail.actions';record=tmp/'record.actions';report=tmp/'audio.json'
            prefix.write_text('\n'.join(path.read_text().splitlines()[:tick])+'\n')
            subprocess.run([str(binary),'--replay',str(prefix),'--save',str(start)],cwd=ROOT,check=True,capture_output=True)
            tail.write_text('\n'.join(keys)+'\n');frame=work/('native-'+name+'.ppm');want=tmp/'expected.ppm'
            actual=subprocess.run([str(native),'--load',str(start),'--smoke-replay','--replay',str(tail),'--record',str(record),
                '--frame',str(frame),'--audio-report',str(report)],cwd=ROOT,env=dict(env,SDL_AUDIODRIVER='dummy'),check=True,capture_output=True,text=True,timeout=20)
            expected=subprocess.run([str(binary),'--load',str(start),'--replay',str(record),'--frame',str(want)],cwd=ROOT,check=True,capture_output=True,text=True)
            device=json.loads(report.read_text())
            if json.loads(actual.stdout)!=json.loads(expected.stdout) or frame.read_bytes()!=want.read_bytes() or not device['opened']:
                raise RuntimeError(name+' native state/pixels/audio device differs')
            if name=='combat-sound' and not device['nonzero']:raise RuntimeError(name+' queued silent PCM')
            print(f'PASS: native {name}, exact input/state/pixels; SDL queued {device["nonzero"]} nonzero audio samples.',flush=True)

def original_saves(env,work):
    """Six owner GAME files enter SDL, inspect Jason, save and reopen privately."""
    binary=ROOT/'build/btech-headless';native=ROOT/'build/btech-port'
    with tempfile.TemporaryDirectory(prefix='native-original-',dir=work) as directory:
        tmp=Path(directory)
        for slot in range(1,7):
            original=ROOT/f'Original DOS/GAME{slot}';raw=original.read_bytes()
            active=any(raw[0x111+125*i]!=255 for i in range(4))
            keys=['menu']+['down']*(3 if active else 2)+['accept','accept','idle','accept']
            tail=tmp/'tail.actions';tail.write_text('\n'.join(keys)+'\n');record=tmp/'record.actions';save=tmp/'native.btp'
            frame=work/f'native-original-{slot}.ppm';expected=tmp/'expected.ppm'
            actual=subprocess.run([str(native),'--load',str(original),'--smoke-replay','--smoke-fast','--replay',str(tail),
                '--record',str(record),'--save',str(save),'--frame',str(frame)],cwd=ROOT,env=dict(env,SDL_AUDIODRIVER='dummy'),check=True,capture_output=True,text=True)
            wanted=subprocess.run([str(binary),'--load',str(original),'--replay',str(record),'--frame',str(expected)],cwd=ROOT,check=True,capture_output=True,text=True)
            reopened=json.loads(subprocess.check_output([str(binary),'--load',str(save),'--export-original',str(tmp/f'GAME{slot}')],cwd=ROOT,text=True))
            if json.loads(actual.stdout)!=json.loads(wanted.stdout) or json.loads(actual.stdout)!=reopened or frame.read_bytes()!=expected.read_bytes():
                raise RuntimeError('Original GAME native/reopened state or pixels differs')
            print(f'PASS: native original GAME{slot}, inspection, internal save/reopen/export, exact SDL state and pixels.',flush=True)

def aftermath(env,work):
    """Explicit combat result prerequisite; SDL continuation, not a campaign proof."""
    subprocess.run([str(ROOT/'build/btp-aftermath-tests'),str(ROOT/'Original DOS')],cwd=ROOT,check=True,capture_output=True,text=True)
    with tempfile.TemporaryDirectory(prefix='native-aftermath-',dir=work) as directory:
        tmp=Path(directory);tail=tmp/'tail.actions';record=tmp/'record.actions';frame=work/'native-aftermath.ppm';expected=tmp/'expected.ppm'
        tail.write_text('accept\n'*30)
        actual=subprocess.run([str(ROOT/'build/btech-port'),'--load',str(work/'aftermath-salvage.btp'),'--smoke-replay','--smoke-fast','--replay',str(tail),'--record',str(record),'--frame',str(frame)],cwd=ROOT,env=env,check=True,capture_output=True,text=True)
        wanted=subprocess.run([str(ROOT/'build/btech-headless'),'--load',str(work/'aftermath-salvage.btp'),'--replay',str(record),'--frame',str(expected)],cwd=ROOT,check=True,capture_output=True,text=True)
        if json.loads(actual.stdout)!=json.loads(wanted.stdout) or frame.read_bytes()!=expected.read_bytes():raise RuntimeError('Native aftermath continuation differs')
        print('PASS: native saved salvage prerequisite, exact SDL input/state/pixels and resumed exploration.',flush=True)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shops-only", action="store_true")
    parser.add_argument("--m2f-only", action="store_true")
    parser.add_argument("--bank-input-only", action="store_true")
    parser.add_argument("--save-only", action="store_true")
    parser.add_argument("--school-only", action="store_true")
    parser.add_argument("--sprites-only", action="store_true")
    parser.add_argument("--training-only", action="store_true")
    parser.add_argument("--diagonal-only", action="store_true")
    parser.add_argument("--rubble-only", action="store_true")
    parser.add_argument("--combat-only", action="store_true")
    parser.add_argument("--training-combat-only", action="store_true")
    parser.add_argument("--world-only", action="store_true")
    parser.add_argument("--campaign-only", action="store_true")
    parser.add_argument("--menu-only", action="store_true")
    parser.add_argument('--presentation-only',action='store_true')
    parser.add_argument('--original-save-only',action='store_true')
    parser.add_argument('--aftermath-only',action='store_true')
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
            if args.aftermath_only:
                aftermath(env,work);return
            if args.original_save_only:
                original_saves(env,work);return
            if args.presentation_only:
                presentation(env,work);return
            if args.campaign_only:
                campaign(env,work);return
            if args.menu_only:
                menu(env,work);return
            if args.world_only:
                world(env,work);return
            if args.training_combat_only:
                rubble(env,work,kind="training-combat")
                rubble(env,work,kind="kick")
                rubble(env,work,kind="sixth-story")
                return
            if args.combat_only:
                rubble(env,work,combat=True)
                return
            if args.rubble_only:
                rubble(env,work)
                return
            if args.diagonal_only:
                diagonals(env,work)
                return
            if args.training_only:
                training(env,work)
                return
            if args.sprites_only:
                sprites(env,work)
                saves(env,work)
                return
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
            if args.school_only:
                school(env,work)
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
            print("Running accelerated native X11 MAP1 walk/arrival/conversation.", flush=True)
            result = subprocess.run([str(ROOT / "build/btech-port"), "--smoke-arrival", "--smoke-fast",
                "--replay", str(ROOT / "tests/fixtures/citadel-arrival.actions"),
                "--data", str(ROOT / "Original DOS"), "--record", str(work / "native-arrival-x11.actions"),
                "--frame", str(work / "native-arrival-x11.ppm")], env=env, timeout=120, check=True,
                capture_output=True, text=True)
            replayed = subprocess.run([str(ROOT / "build/btech-headless"), "--replay",
                str(work / "native-arrival-x11.actions"), "--frame", str(work / "replayed-arrival.ppm")], check=True, timeout=15,
                capture_output=True, text=True, cwd=ROOT)
            if (work / "native-arrival-x11.actions").read_text().splitlines() != (ROOT / "tests/fixtures/citadel-arrival.actions").read_text().splitlines()+["accept","down","accept","down"]+["idle"]*5 or json.loads(result.stdout) != json.loads(replayed.stdout) or (work / "native-arrival-x11.ppm").read_bytes() != (work / "replayed-arrival.ppm").read_bytes():
                raise RuntimeError("Native arrival inputs/state/frame differ from its headless input replay")
            print(result.stdout.strip())
            subprocess.run(["python3", str(ROOT / "tools/verify_m2d.py"), "--native-log",
                str(work / "native-arrival-x11.actions")], check=True, timeout=15)
            print("PASS: native X11 normal exploration, NPC arrival/reply, return/exit and full canonical replay equality.")
            sprites(env,work)
            shops(env, work)
            m2f(env, work)
            saves(env,work)
            school(env,work)
            training(env,work)
            rubble(env,work)
            rubble(env,work,combat=True)
            rubble(env,work,kind="training-combat")
            rubble(env,work,kind="kick")
            rubble(env,work,kind="sixth-story")
            world(env,work)
            diagonals(env,work)
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
