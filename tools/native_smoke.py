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

if __name__=='__main__' and any('editor' in argument or 'construction-kit' in argument for argument in __import__('sys').argv[1:]):
    from editor_runtime import prefer_system_tk
    prefer_system_tk()

ROOT = Path(__file__).resolve().parents[1]

def windows_frontend():
    """Use the Windows SDL executable; keep Linux headless as the oracle."""
    from windows_check import WINE,environment,arguments
    original=subprocess.Popen
    def launch(command,*args,**kwargs):
        if command and Path(str(command[0])).resolve()==ROOT/'build/btech-port':
            command=[str(WINE),*arguments([ROOT/'build-windows/btech-port.exe',*command[1:]])]
            kwargs['env']=environment(kwargs.get('env',os.environ))
            # Exercise the Windows SDL audio queue without requiring a
            # physical Windows audio endpoint on this Linux test host.
            kwargs['env']['SDL_AUDIODRIVER']='dummy'
        return original(command,*args,**kwargs)
    subprocess.Popen=launch

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
            keys.key(window,"Return"); keys.key(window,"Ctrl+Shift+Escape")
            stdout,stderr = process.communicate(timeout=10)
            if process.returncode or "Cannot open save" not in stderr: raise RuntimeError(stderr)
            actual = json.loads(stdout)
            delta=actual['tick']-state['tick']
            if not 1<=delta<=50:raise RuntimeError('Native bank restore clock was unbounded')
            tail = tmp/"tail.actions"; tail.write_text("accept\n"+"idle\n"*(delta-1))
            expected = subprocess.run([str(ROOT/"build/btech-headless"),"--load",str(slot),
                "--replay",str(tail)],check=True,capture_output=True,text=True,cwd=ROOT,timeout=20)
            wanted = json.loads(expected.stdout)
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
        keys.key(window,'Ctrl+Shift+Escape')
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
        print('PASS: native sprite movement/frame replay; animated mech preview, static grid and Ctrl+Shift+Escape exit.',flush=True)
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
                f=json.loads((ROOT/'tests/fixtures/ordinary-rubble-story.json').read_text())
                tick=next(r['tick'] for r in f['checkpoints'] if r['label']=='first-mech')
                lines=(ROOT/'tests/fixtures/ordinary-rubble-story.actions').read_text().splitlines()[:tick]
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
                keys.key(window,'Ctrl+Shift+Escape')
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
                keys.key(window,"F9"); keys.key(window,"Ctrl+Shift+Escape")
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
                keys.key(window,"F9"); keys.key(window,"Ctrl+Shift+Escape")
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
    process=subprocess.Popen([str(ROOT/'build/btech-port'),'--edition','original','--save-file',str(slot),'--frame',str(frame)],
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
        keys.key(window,'Right');keys.key(window,'F4');keys.key(window,'F9');keys.key(window,'F4');keys.key(window,'Ctrl+Shift+Escape')
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
        service_notes=json.loads((ROOT/'tests/fixtures/ordinary-services.json').read_text())['checkpoints']
        ammo_label='partial-ammo-amount' if any(c['label']=='partial-ammo-amount' for c in service_notes) else 'ammo-status'
        probes=[('rex','rex-crest'),('services',ammo_label),('title',None)]
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
        keys.append('menu');choose(2);choose(0);keys.append('menu');choose(6);keys.append('cancel')
        # Physical Space chooses every highlighted item; logical Enter in
        # the expected log remains an independent selection reference.
        actions.write_text('\n'.join('menu' if key=='accept' else key for key in keys)+'\n')
        frame=work/'native-space-menu.ppm';expected=tmp/'expected.ppm'
        env=dict(env,SDL_AUDIODRIVER='dummy')
        actual=subprocess.run([str(ROOT/'build/btech-port'),'--smoke-replay','--smoke-fast','--replay',str(actions),'--save-file',str(base),'--record',str(record),'--frame',str(frame)],cwd=ROOT,env=env,check=True,capture_output=True,text=True,timeout=20)
        wanted=subprocess.run([str(ROOT/'build/btech-headless'),'--replay',str(record),'--save-file',str(base),'--frame',str(expected)],cwd=ROOT,check=True,capture_output=True,text=True,timeout=20)
        if record.read_text().splitlines()!=keys+['idle']*5 or json.loads(actual.stdout)!=json.loads(wanted.stdout) or frame.read_bytes()!=expected.read_bytes():
            (work/'native-menu-actual.json').write_text(actual.stdout)
            (work/'native-menu-wanted.json').write_text(wanted.stdout)
            (work/'native-menu-actual.actions').write_text(record.read_text())
            (work/'native-menu-wanted.actions').write_text('\n'.join(keys+['idle']*5)+'\n')
            raise RuntimeError('Native menu inputs/state/pixels differ')
        for number in range(1,7):
            path=base if number==1 else tmp/f'slot-{number}.btp'
            state=json.loads(subprocess.run([str(ROOT/'build/btech-headless'),'--load',str(path)],cwd=ROOT,check=True,capture_output=True,text=True).stdout)
            if state['actions_menu']['steps']!=1<<((number-1)%3):raise RuntimeError('Slot did not retain its separate movement setting')
        print(f'PASS: native Space/settings/inspection/overhead, all six saves and loads, {len(keys)+5} exact SDL inputs and pixels.',flush=True)
    inspection_saves(env,work)
    overhead(env,work)

def mechit_ui(env,work):
    """Original repair/ammo/recruitment pauses, actual SDL and F5/F9."""
    from reference_session import WindowKeys
    binary=ROOT/'build/btech-headless';env=dict(env,SDL_AUDIODRIVER='dummy')
    with tempfile.TemporaryDirectory(prefix='native-mechit-',dir=work) as directory:
        tmp=Path(directory);tail=tmp/'keys.actions';record=tmp/'record.actions';expected=tmp/'expected.ppm'
        paths=[('repairs','mechit-ui-start.btp',['down']*2+['accept']*9),
               ('ammunition','mechit-ui-start.btp',['down']*3+['accept']*2+['9']*3+['accept']*4),
               ('refit','mechit-apprentice-start.btp',['down','accept','accept','accept','down','accept','accept','accept']),
               ('recruit','mechit-recruit-start.btp',['accept','accept']+['idle']*96+['accept']+['down']*5+['accept'])]
        for label,start,keys in paths:
            # The numeric amount submits with Enter; all menu/Yes-No choices
            # use Space, including the last-mech repair and refit selectors.
            physical=['menu' if key=='accept' and not (label=='ammunition' and i in (8,10)) else key for i,key in enumerate(keys)]
            tail.write_text('\n'.join(physical)+'\n');frame=work/f'native-mechit-{label}.ppm'
            actual=subprocess.run([str(ROOT/'build/btech-port'),'--load',str(work/start),'--smoke-replay','--smoke-fast',
                '--replay',str(tail),'--record',str(record),'--frame',str(frame)],cwd=ROOT,env=env,check=True,capture_output=True,text=True,timeout=25)
            wanted=subprocess.run([str(binary),'--load',str(work/start),'--replay',str(record),'--frame',str(expected)],cwd=ROOT,check=True,capture_output=True,text=True)
            if record.read_text().splitlines()!=keys+['idle']*5 or json.loads(actual.stdout)!=json.loads(wanted.stdout) or frame.read_bytes()!=expected.read_bytes():
                raise RuntimeError(f'Native Mechit-Lube {label} input/state/pixels differ')
            print(f'PASS: native Mechit-Lube {label}, exact SDL inputs, complete state and pixels.',flush=True)
        repair=['down','down','accept','accept'];ammo=['down']*3+['accept']*2
        pages=[('repair-question','mechit-ui-start.btp',repair),
               ('weapon-estimate','mechit-ui-start.btp',repair+['accept']*2),
               ('repair-receipt','mechit-ui-start.btp',repair+['accept']*3),
               ('ammo-amount','mechit-ui-start.btp',ammo),
               ('ammo-limit','mechit-ui-start.btp',ammo+['9']*3+['accept']),
               ('agent-join','mechit-recruit-start.btp',['accept','accept']+['idle']*96),
               ('refit-offer','mechit-apprentice-start.btp',['down','accept','accept','accept','down','accept'])]
        for label,start,keys in pages:
            tail.write_text('\n'.join(keys)+'\n');page=tmp/'page.btp';slot=tmp/'slot.btp'
            subprocess.run([str(binary),'--load',str(work/start),'--replay',str(tail),'--save',str(page)],cwd=ROOT,check=True,capture_output=True)
            frame=work/f'native-mechit-{label}-restore.ppm'
            process=subprocess.Popen([str(ROOT/'build/btech-port'),'--load',str(page),'--save-file',str(slot),'--frame',str(frame)],
                cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            keyboard=WindowKeys()
            try:
                for _ in range(100):
                    found=[(w,n) for w,n in keyboard.windows() if n.startswith('BtechPort')]
                    if len(found)==1:window=found[0][0];break
                    if process.poll() is not None:raise RuntimeError('Mechit window failed to start')
                    time.sleep(.05)
                else:raise RuntimeError('Mechit window did not appear')
                keyboard.key(window,'F5');time.sleep(.1)
                before=json.loads(subprocess.check_output([str(binary),'--load',str(slot)],cwd=ROOT,text=True))
                keyboard.key(window,'Right');time.sleep(.1);keyboard.key(window,'F9');keyboard.key(window,'Ctrl+Shift+Escape')
                out,err=process.communicate(timeout=10)
                if process.returncode:raise RuntimeError(err)
                restored=json.loads(out);delta=restored['tick']-before['tick']
                if not 0<=delta<=20:raise RuntimeError('Unexpected Mechit restore interval')
                tail.write_text('idle\n'*delta)
                wanted=json.loads(subprocess.check_output([str(binary),'--load',str(slot),'--replay',str(tail),'--frame',str(expected)],cwd=ROOT,text=True))
                if restored!=wanted or frame.read_bytes()!=expected.read_bytes():raise RuntimeError(f'Native Mechit {label} restore differs')
                print(f'PASS: native F5/F9 on Mechit-Lube {label}, identical saved continuation.',flush=True)
            finally:
                keyboard.x.XCloseDisplay(keyboard.display)
                if process.poll() is None:process.terminate();process.wait(timeout=5)

def weapon_effects(env,work):
    """Real SDL F5/F9 while weapon effects and outdoor fire are advancing."""
    from reference_session import WindowKeys
    binary=ROOT/'build/btech-headless';env=dict(env,SDL_AUDIODRIVER='dummy')
    with tempfile.TemporaryDirectory(prefix='native-effects-',dir=work) as directory:
        tmp=Path(directory)
        for label in ('firing-pose','missile-flight','beam-sound','impact','outdoor-fire'):
            start=work/'weapon-presentation'/f'{label}.btp';slot=tmp/'slot.btp'
            frame=work/'weapon-presentation'/f'native-{label}.ppm';expected=tmp/'expected.ppm';tail=tmp/'tail.actions'
            process=subprocess.Popen([str(ROOT/'build/btech-port'),'--load',str(start),'--save-file',str(slot),'--frame',str(frame)],
                cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            keyboard=WindowKeys()
            try:
                for _ in range(100):
                    found=[w for w,n in keyboard.windows() if n.startswith('BtechPort')]
                    if len(found)==1:window=found[0];break
                    if process.poll() is not None:raise RuntimeError(label+' window failed')
                    time.sleep(.02)
                else:raise RuntimeError(label+' window unavailable')
                keyboard.key(window,'F5');time.sleep(.1)
                before=json.loads(subprocess.check_output([str(binary),'--load',str(slot)],cwd=ROOT,text=True))
                time.sleep(.15);keyboard.key(window,'F9');keyboard.key(window,'Ctrl+Shift+Escape')
                out,err=process.communicate(timeout=10)
                if process.returncode:raise RuntimeError(err)
                actual=json.loads(out);delta=actual['tick']-before['tick']
                if not 0<=delta<=20:raise RuntimeError(label+' restore clock was unbounded')
                tail.write_text('idle\n'*delta)
                wanted=json.loads(subprocess.check_output([str(binary),'--load',str(slot),'--replay',str(tail),'--frame',str(expected)],cwd=ROOT,text=True))
                if actual!=wanted or frame.read_bytes()!=expected.read_bytes():raise RuntimeError(label+' SDL state/pixels differ')
                print(f'PASS: native F5/F9 {label}; exact state/pixels after resumed animation.',flush=True)
            finally:
                keyboard.x.XCloseDisplay(keyboard.display)
                if process.poll() is None:process.terminate();process.wait(timeout=5)


def combat_pacing(env,work):
    """Use the real 32ms SDL loop and audio queue for short combat waves."""
    binary=ROOT/'build/btech-headless'
    env=dict(env,SDL_AUDIODRIVER='dummy')
    with tempfile.TemporaryDirectory(prefix='native-pacing-',dir=work) as directory:
        tmp=Path(directory)
        cases=[('move',['idle']*12,4),('key',['idle']*20,9),
               ('key-enter',['idle']*16+['accept']+['idle']*20,4),
               ('key-space',['idle']*16+['menu']+['idle']*20,4)]
        for label,actions,phase in cases:
            start=work/f'combat-pacing-{"move" if label=="move" else "key"}.btp'
            tail=tmp/'tail.actions';record=tmp/'record.actions'
            frame=work/f'native-pacing-{label}.ppm';expected=tmp/'expected.ppm'
            tail.write_text('\n'.join(actions)+'\n')
            # Deliberately omit --smoke-fast: the normal clock and queue
            # backpressure must permit the same progress as the core test.
            actual=subprocess.run([str(ROOT/'build/btech-port'),'--load',str(start),
                '--smoke-replay','--replay',str(tail),'--record',str(record),'--frame',str(frame)],
                cwd=ROOT,env=env,check=True,capture_output=True,text=True,timeout=20)
            wanted=subprocess.run([str(binary),'--load',str(start),'--replay',str(record),
                '--frame',str(expected)],cwd=ROOT,check=True,capture_output=True,text=True,timeout=10)
            state=json.loads(actual.stdout)
            if record.read_text().splitlines()!=actions+['idle']*5 or state!=json.loads(wanted.stdout) or frame.read_bytes()!=expected.read_bytes():
                raise RuntimeError(f'Combat pacing {label}: SDL input/state/pixels differ')
            if state['combat']['phase']!=phase:
                raise RuntimeError(f'Combat pacing {label}: movement or attack wait finished at the wrong boundary')
            if label=='key' and state['combat']['step']!=1:
                raise RuntimeError('Key-wait mode did not hold immediately after the first attack')
            print(f'PASS: native combat pacing {label}; normal clock, exact input/state/pixels.',flush=True)


def combat_ui(env,work):
    """Controlled original mixed-party UI prerequisite, real SDL keys/F5/F9."""
    from reference_session import WindowKeys
    binary=ROOT/'build/btech-headless';start=work/'combat-ui-start.btp'
    env=dict(env,SDL_AUDIODRIVER='dummy')
    with tempfile.TemporaryDirectory(prefix='native-combat-ui-',dir=work) as directory:
        tmp=Path(directory);tail=tmp/'keys.actions';record=tmp/'record.actions';expected=tmp/'expected.ppm'
        keys=['up','accept','accept','down','accept','menu']+['accept']*3+['down','accept',
            'accept','down','accept','menu','down','accept','down','accept']
        tail.write_text('\n'.join(keys)+'\n');frame=work/'native-combat-ui.ppm'
        actual=subprocess.run([str(ROOT/'build/btech-port'),'--load',str(start),'--smoke-replay','--smoke-fast',
            '--replay',str(tail),'--record',str(record),'--frame',str(frame)],cwd=ROOT,env=env,check=True,capture_output=True,text=True,timeout=20)
        wanted=subprocess.run([str(binary),'--load',str(start),'--replay',str(record),'--frame',str(expected)],cwd=ROOT,check=True,capture_output=True,text=True)
        recorded=keys.copy();recorded[14]='accept' # SDL normalizes Space on the press-a-key notice.
        if record.read_text().splitlines()!=recorded+['idle']*5 or json.loads(actual.stdout)!=json.loads(wanted.stdout) or frame.read_bytes()!=expected.read_bytes():
            (work/'native-combat-ui-actual.json').write_text(actual.stdout)
            (work/'native-combat-ui-wanted.json').write_text(wanted.stdout)
            (work/'native-combat-ui-record.actions').write_text(record.read_text())
            raise RuntimeError('Native original combat UI keys/state/pixels differ')
        print('PASS: native eight-entry foot menu, friend/enemy summaries, Detail Scan and Space dismissal; exact input/state/pixels.',flush=True)
        # Assign each unit separately, start one wave explicitly, and use
        # Space while it runs. The source is a declared mixed-party test
        # state; every subsequent choice passes through SDL key events.
        keys=['accept','down','down','accept','up','up','accept',
              'down','down','accept','up','up','accept','down','down','accept',
              'up','up','accept','down','down','accept','down','down','accept','menu']+['idle']*2048
        physical=['menu' if key=='accept' else key for key in keys]
        tail.write_text('\n'.join(physical)+'\n')
        command_start=work/'computer-control-start.btp'
        actual=subprocess.run([str(ROOT/'build/btech-port'),'--load',str(command_start),'--smoke-replay','--smoke-fast',
            '--replay',str(tail),'--record',str(record),'--frame',str(frame)],cwd=ROOT,env=env,check=True,capture_output=True,text=True,timeout=20)
        tail.write_text('\n'.join(keys+['idle']*5)+'\n')
        wanted=subprocess.run([str(binary),'--load',str(command_start),'--replay',str(tail),'--frame',str(expected)],cwd=ROOT,check=True,capture_output=True,text=True)
        state=json.loads(actual.stdout)
        if record.read_text().splitlines()!=physical+['idle']*5 or state!=json.loads(wanted.stdout) or frame.read_bytes()!=expected.read_bytes():
            raise RuntimeError('Native individual computer assignments/Space continuation differ')
        if state['combat']['phase']!=4 or state['combat']['automatic']!=15 or state['combat']['auto_run']:
            raise RuntimeError('Computer assignment started continuous fighting or Space lost its assignments')
        print('PASS: Space selects four individual Computer assignments and Begin Fight, then interrupts; exact Enter-equivalent state/pixels.',flush=True)
        # The target/withdrawal files come from the ordinary-input portion of
        # test_combat_ui; they include both held withdrawal messages.
        pages=[('scan-choice',['up','accept']),('scan-summary',['up','accept','accept']),
               ('scan-detail',['up','accept','accept','down','accept']),
               ('target-ui-start',None),('target-ui-target',None),
               ('target-ui-withdrawal',None),('target-ui-return',None)]
        pages += [(f'weapon-ui-{i}',None) for i in (2,7,9,11,14,16)]
        pages += [(f'weapon-warning-{i}',None) for i in (0,2,4)]
        pages += [('computer-control-start',None),('battle-report-brief',None),('battle-report-verbose',None)]
        for label,prefix in pages:
            page=tmp/'page.btp';slot=tmp/'slot.btp'
            if prefix is None:page=work/f'{label}.btp'
            else:
                tail.write_text('\n'.join(prefix)+'\n')
                subprocess.run([str(binary),'--load',str(start),'--replay',str(tail),'--save',str(page)],cwd=ROOT,check=True,capture_output=True)
            frame=work/f'native-{label}-restore.ppm'
            process=subprocess.Popen([str(ROOT/'build/btech-port'),'--load',str(page),'--save-file',str(slot),'--frame',str(frame)],
                cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            keyboard=WindowKeys()
            try:
                for _ in range(100):
                    found=[(w,n) for w,n in keyboard.windows() if n.startswith('BtechPort')]
                    if len(found)==1:window=found[0][0];break
                    if process.poll() is not None:raise RuntimeError('Combat scan window failed to start')
                    time.sleep(.05)
                else:raise RuntimeError('Combat scan window did not appear')
                keyboard.key(window,'F5');time.sleep(.1)
                before=json.loads(subprocess.check_output([str(binary),'--load',str(slot)],cwd=ROOT,text=True))
                keyboard.key(window,'Right');time.sleep(.1);keyboard.key(window,'F9');keyboard.key(window,'Ctrl+Shift+Escape')
                out,err=process.communicate(timeout=10)
                if process.returncode:raise RuntimeError(err)
                restored=json.loads(out);delta=restored['tick']-before['tick']
                if not 0<=delta<=20:raise RuntimeError('Unexpected scan load continuation interval')
                tail.write_text('idle\n'*delta)
                wanted=json.loads(subprocess.check_output([str(binary),'--load',str(slot),'--replay',str(tail),'--frame',str(expected)],cwd=ROOT,text=True))
                if restored!=wanted or frame.read_bytes()!=expected.read_bytes():raise RuntimeError('Native scan save continuation differs')
                print(f'PASS: native F5/F9 restores {label}, complete state and pixels.',flush=True)
            finally:
                keyboard.x.XCloseDisplay(keyboard.display)
                if process.poll() is None:process.terminate();process.wait(timeout=5)

def completion_panels(env,work):
    """Late cinema text and live-compared salvage pages, real keys and F5/F9."""
    from reference_session import WindowKeys
    binary=ROOT/'build/btech-headless';native=ROOT/'build/btech-port'
    env=dict(env,SDL_AUDIODRIVER='dummy')
    for test in ('btp-late-building-tests','btp-aftermath-tests'):
        subprocess.run([str(ROOT/'build'/test),str(ROOT/'Original DOS')],cwd=ROOT,check=True,capture_output=True,timeout=20)
    pages=['theater-988','theater-1125']+[f'salvage-live-{i}' for i in range(3)]
    with tempfile.TemporaryDirectory(prefix='native-completion-',dir=work) as directory:
        tmp=Path(directory);slot=tmp/'slot.btp';tail=tmp/'tail.actions';expected=tmp/'expected.ppm'
        for label in pages:
            start=work/'m4-audit'/f'{label}.btp';frame=work/f'native-{label}-restore.ppm'
            process=subprocess.Popen([str(native),'--load',str(start),'--save-file',str(slot),'--frame',str(frame)],
                cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            keyboard=WindowKeys()
            try:
                for _ in range(100):
                    found=[w for w,n in keyboard.windows() if n.startswith('BtechPort')]
                    if len(found)==1:window=found[0];break
                    if process.poll() is not None:raise RuntimeError(label+' window failed')
                    time.sleep(.02)
                else:raise RuntimeError(label+' window unavailable')
                keyboard.key(window,'F5');time.sleep(.1)
                before=json.loads(subprocess.check_output([str(binary),'--load',str(slot)],cwd=ROOT,text=True))
                # Advance the held text with Space, then restore the earlier
                # panel. F9 must recover its original script/scroll context.
                keyboard.key(window,'space');keyboard.key(window,'F9');keyboard.key(window,'Ctrl+Shift+Escape')
                out,err=process.communicate(timeout=10)
                if process.returncode:raise RuntimeError(err)
                actual=json.loads(out);delta=actual['tick']-before['tick']
                if not 0<=delta<=20:raise RuntimeError(label+' unexpected restore interval')
                tail.write_text('idle\n'*delta)
                wanted=json.loads(subprocess.check_output([str(binary),'--load',str(slot),'--replay',str(tail),'--frame',str(expected)],cwd=ROOT,text=True))
                if actual!=wanted or frame.read_bytes()!=expected.read_bytes():raise RuntimeError(label+' save/pixels differ')
                print(f'PASS: native {label}, Space advances and F5/F9 restores complete state and pixels.',flush=True)
            finally:
                keyboard.x.XCloseDisplay(keyboard.display)
                if process.poll() is None:process.terminate();process.wait(timeout=5)

def encounter_placement(env,work):
    """Starport-boundary offers, menu entry and real F5/F9 for three parties."""
    from reference_session import WindowKeys
    binary=ROOT/'build/btech-headless';native=ROOT/'build/btech-port'
    env=dict(env,SDL_AUDIODRIVER='dummy')
    with tempfile.TemporaryDirectory(prefix='native-encounters-',dir=work) as directory:
        tmp=Path(directory);prefix=tmp/'boundary';tail=tmp/'keys.actions';record=tmp/'record.actions'
        expected=tmp/'expected.ppm';slot=tmp/'slot.btp'
        subprocess.run([str(ROOT/'build/btp-encounter-placement-tests'),str(ROOT/'Original DOS'),str(prefix)],
            cwd=ROOT,check=True,capture_output=True,text=True)
        for group,label in enumerate(('foot','mech','mixed')):
            start=Path(f'{prefix}-{group}.btp');frame=work/f'native-encounter-{label}.ppm'
            tail.write_text('accept\n'*4)
            actual=subprocess.run([str(native),'--load',str(start),'--smoke-replay','--smoke-fast',
                '--replay',str(tail),'--record',str(record),'--frame',str(frame)],
                cwd=ROOT,env=env,check=True,capture_output=True,text=True,timeout=20)
            wanted=subprocess.run([str(binary),'--load',str(start),'--replay',str(record),'--frame',str(expected)],
                cwd=ROOT,check=True,capture_output=True,text=True)
            if record.read_text().splitlines()!=['accept']*4+['idle']*5 or json.loads(actual.stdout)!=json.loads(wanted.stdout) or frame.read_bytes()!=expected.read_bytes():
                raise RuntimeError('Native boundary encounter continuation differs: '+label)
            process=subprocess.Popen([str(native),'--load',str(start),'--save-file',str(slot),'--frame',str(frame)],
                cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            keyboard=WindowKeys()
            try:
                for _ in range(100):
                    found=[w for w,n in keyboard.windows() if n.startswith('BtechPort')]
                    if len(found)==1:window=found[0];break
                    if process.poll() is not None:raise RuntimeError('Boundary encounter window failed to start')
                    time.sleep(.05)
                else:raise RuntimeError('Boundary encounter window did not appear')
                keyboard.key(window,'F5');time.sleep(.1)
                before=json.loads(subprocess.check_output([str(binary),'--load',str(slot)],cwd=ROOT,text=True))
                keyboard.key(window,'Right');keyboard.key(window,'F9');keyboard.key(window,'Ctrl+Shift+Escape')
                out,err=process.communicate(timeout=10)
                if process.returncode:raise RuntimeError(err)
                restored=json.loads(out);delta=restored['tick']-before['tick']
                if not 0<=delta<=20:raise RuntimeError('Unexpected encounter restoration interval')
                tail.write_text('idle\n'*delta)
                wanted=json.loads(subprocess.check_output([str(binary),'--load',str(slot),'--replay',str(tail),'--frame',str(expected)],cwd=ROOT,text=True))
                if restored!=wanted or frame.read_bytes()!=expected.read_bytes():raise RuntimeError('Native boundary F5/F9 differs: '+label)
                print(f'PASS: native Starport-boundary {label} encounter, combat-menu entry and F5/F9; exact continued state/pixels.',flush=True)
            finally:
                keyboard.x.XCloseDisplay(keyboard.display)
                if process.poll() is None:process.terminate();process.wait(timeout=5)

def cache_island(env,work):
    """Walk the visible cave-island edge through actual SDL and save/load."""
    from reference_session import WindowKeys
    binary=ROOT/'build/btech-headless';native=ROOT/'build/btech-port'
    env=dict(env,SDL_AUDIODRIVER='dummy');start=work/'cache-island-start.btp'
    with tempfile.TemporaryDirectory(prefix='native-island-',dir=work) as directory:
        tmp=Path(directory);tail=tmp/'keys.actions';record=tmp/'record.actions';expected=tmp/'expected.ppm'
        frame=work/'native-cache-island.ppm';page=tmp/'page.btp';slot=tmp/'slot.btp'
        keys=['left','right','up-left','down-right','menu'];tail.write_text('\n'.join(keys)+'\n')
        actual=subprocess.run([str(native),'--load',str(start),'--smoke-replay','--smoke-fast',
            '--replay',str(tail),'--record',str(record),'--save',str(page),'--frame',str(frame)],
            cwd=ROOT,env=env,check=True,capture_output=True,text=True,timeout=20)
        wanted=subprocess.run([str(binary),'--load',str(start),'--replay',str(record),'--frame',str(expected)],
            cwd=ROOT,check=True,capture_output=True,text=True)
        state=json.loads(actual.stdout)
        if record.read_text().splitlines()!=keys+['idle']*5 or state!=json.loads(wanted.stdout) or frame.read_bytes()!=expected.read_bytes():
            raise RuntimeError('Native cache-island edge input/state/pixels differ')
        if state['mode']!='actions' or state['map']!=13 or state['campaign']['world']!=[768,778]:
            raise RuntimeError('Visible island edge movement was blocked')
        process=subprocess.Popen([str(native),'--load',str(page),'--save-file',str(slot),'--frame',str(frame)],
            cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        keyboard=WindowKeys()
        try:
            for _ in range(100):
                found=[w for w,n in keyboard.windows() if n.startswith('BtechPort')]
                if len(found)==1:window=found[0];break
                if process.poll() is not None:raise RuntimeError('Island window failed to start')
                time.sleep(.05)
            else:raise RuntimeError('Island window did not appear')
            keyboard.key(window,'F5');time.sleep(.1)
            before=json.loads(subprocess.check_output([str(binary),'--load',str(slot)],cwd=ROOT,text=True))
            keyboard.key(window,'Right');keyboard.key(window,'F9');keyboard.key(window,'Ctrl+Shift+Escape')
            out,err=process.communicate(timeout=10)
            if process.returncode:raise RuntimeError(err)
            restored=json.loads(out);delta=restored['tick']-before['tick']
            if not 0<=delta<=20:raise RuntimeError('Unexpected island restoration interval')
            tail.write_text('idle\n'*delta)
            wanted=json.loads(subprocess.check_output([str(binary),'--load',str(slot),'--replay',str(tail),
                '--frame',str(expected)],cwd=ROOT,text=True))
            if restored!=wanted or frame.read_bytes()!=expected.read_bytes():raise RuntimeError('Native island F5/F9 continuation differs')
            print('PASS: native cave-island edge and diagonal movement, real F5/F9; identical input/state/pixels.',flush=True)
        finally:
            keyboard.x.XCloseDisplay(keyboard.display)
            if process.poll() is None:process.terminate();process.wait(timeout=5)

def overhead(env,work):
    """Open the map with real Space/Up/Space and inspect the X11 window pixels."""
    import ctypes as c
    from PIL import Image,ImageGrab
    from reference_session import WindowKeys
    env=dict(env,SDL_AUDIODRIVER='dummy')
    binary=ROOT/'build/btech-headless'
    with tempfile.TemporaryDirectory(prefix='native-overhead-',dir=work) as directory:
        tmp=Path(directory)
        for name,initial in [('citadel',[]),('world',['--load',str(ROOT/'Original DOS/GAME3')])]:
            start=tmp/'start.btp';slot=tmp/'slot.btp';expected=tmp/'expected.ppm'
            subprocess.run([str(binary),*initial,'--save',str(start)],cwd=ROOT,check=True,capture_output=True)
            frame=work/f'native-overhead-{name}.ppm'
            process=subprocess.Popen([str(ROOT/'build/btech-port'),'--load',str(start),
                '--save-file',str(slot),'--frame',str(frame)],cwd=ROOT,env=env,
                stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            keys=WindowKeys()
            try:
                window=None
                for _ in range(100):
                    found=[w for w,n in keys.windows() if n.startswith('BtechPort')]
                    if len(found)==1:window=found[0];break
                    if process.poll() is not None:raise RuntimeError('Overhead window failed')
                    time.sleep(.02)
                if window is None:raise RuntimeError('Overhead window did not appear')
                # Space confirms Settings, Movement rate and Two steps too.
                for key in ('space','Down','space','space','Down','space',
                            'space','Up','space','F5'):keys.key(window,key)
                for _ in range(100):
                    if slot.exists():break
                    time.sleep(.02)
                saved=json.loads(subprocess.run([str(binary),'--load',str(slot),
                    '--frame',str(expected)],cwd=ROOT,check=True,capture_output=True,text=True).stdout)
                if saved['mode']!='actions' or saved['actions_menu']['phase']!=13:
                    raise RuntimeError('Real Space menu did not open Show Overhead Map')
                if saved['actions_menu']['steps']!=2:
                    raise RuntimeError('Space did not confirm a settings submenu item')
                # Read the actual presented window, including SDL scaling.
                keys.x.XGetGeometry.argtypes=[c.c_void_p,c.c_ulong,c.POINTER(c.c_ulong)]+[c.POINTER(c.c_int)]*2+[c.POINTER(c.c_uint)]*4
                keys.x.XTranslateCoordinates.argtypes=[c.c_void_p,c.c_ulong,c.c_ulong,c.c_int,c.c_int,c.POINTER(c.c_int),c.POINTER(c.c_int),c.POINTER(c.c_ulong)]
                root=c.c_ulong();x=c.c_int();y=c.c_int();width=c.c_uint();height=c.c_uint();border=c.c_uint();depth=c.c_uint()
                if not keys.x.XGetGeometry(keys.display,window,c.byref(root),c.byref(x),c.byref(y),c.byref(width),c.byref(height),c.byref(border),c.byref(depth)):
                    raise RuntimeError('Cannot read overhead window geometry')
                child=c.c_ulong()
                keys.x.XTranslateCoordinates(keys.display,window,keys.root,0,0,c.byref(x),c.byref(y),c.byref(child))
                screen=ImageGrab.grab(xdisplay=env['DISPLAY']).crop((x.value,y.value,x.value+width.value,y.value+height.value))
                screen.save(work/f'native-overhead-{name}-window.png')
                visible=screen.resize((320,200),Image.Resampling.NEAREST).convert('RGB')
                # DOS polls a 2x2 flashing player marker. The save and X11
                # screenshot occur on different polls; compare the remaining
                # map exactly and require a solid, visible marker footprint.
                wx,wy=saved['campaign']['world'] if saved['campaign_flags'][4] else (1536+saved['x_half'],1536+saved['y_half'])
                px=min(318,wx//2-max(0,min(11,wx//128-2))*64)
                py=wy//2-max(0,min(13,wy//128-1))*64
                static=visible.copy();reference=Image.open(expected).convert('RGB')
                marker=[visible.getpixel((px+dx,py+dy)) for dy in range(2) for dx in range(2)]
                if len(set(marker))!=1:raise RuntimeError('Player marker is not the original 2x2 rectangle')
                for dy in range(2):
                    for dx in range(2):static.putpixel((px+dx,py+dy),(0,0,0));reference.putpixel((px+dx,py+dy),(0,0,0))
                if static.tobytes()!=reference.tobytes():
                    raise RuntimeError('Presented overhead pixels differ from the saved map')
                terrain=visible.crop((0,0,320,192))
                count=sum(pixel!=(0,0,0) for pixel in terrain.getdata())
                if count<(2000 if name=='citadel' else 40000):
                    raise RuntimeError('Overhead window contains no visible explored terrain')
                keys.key(window,'F9');keys.close_window(window)
                out,err=process.communicate(timeout=10)
                if process.returncode:raise RuntimeError(err)
                actual=json.loads(out)
                delta=actual['tick']-saved['tick']
                if not 0<=delta<=50:raise RuntimeError('Overhead restore clock was unbounded')
                tail=tmp/'after-restore.actions';tail.write_text('idle\n'*delta)
                wanted=subprocess.run([str(binary),'--load',str(slot),'--replay',str(tail),'--frame',str(expected)],cwd=ROOT,check=True,capture_output=True,text=True)
                if actual!=json.loads(wanted.stdout) or actual['actions_menu']['phase']!=13 or frame.read_bytes()!=expected.read_bytes():
                    raise RuntimeError('Overhead view was not restored visibly by F9')
                print(f'PASS: real Space/Up/Space opens {name} overhead; {count} visible terrain pixels in actual X11 window; F5/F9 restores it.',flush=True)
            finally:
                keys.x.XCloseDisplay(keys.display)
                if process.poll() is None:process.terminate();process.wait(timeout=5)

def inspection_saves(env,work):
    """F5/F9 while character, mech and overhead views are actually open."""
    from reference_session import WindowKeys
    env=dict(env,SDL_AUDIODRIVER='dummy')
    with tempfile.TemporaryDirectory(prefix='native-inspection-',dir=work) as directory:
        tmp=Path(directory);prefix=tmp/'prefix.actions';tail=tmp/'idle.actions'
        for name,initial,row,extra in [('character',[],2,[]),
                ('overhead',[],6,[]),('mech',['--load',str(ROOT/'Original DOS/GAME3')],3,['accept','accept'])]:
            prefix.write_text('\n'.join(['menu']+['down']*row+['accept']+extra)+'\n')
            start=tmp/'start.btp';slot=tmp/'slot.btp';frame=work/f'native-{name}-restore.ppm';expected=tmp/'expected.ppm'
            subprocess.run([str(ROOT/'build/btech-headless'),*initial,'--replay',str(prefix),'--save',str(start)],cwd=ROOT,check=True,capture_output=True,text=True)
            process=subprocess.Popen([str(ROOT/'build/btech-port'),'--load',str(start),'--save-file',str(slot),
                '--frame',str(frame)],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            keys=WindowKeys()
            try:
                window=None
                for _ in range(100):
                    found=[w for w,n in keys.windows() if n.startswith('BtechPort')]
                    if len(found)==1:window=found[0];break
                    if process.poll() is not None:raise RuntimeError(name+' view failed to start')
                    time.sleep(.02)
                if window is None:raise RuntimeError(name+' window did not appear')
                keys.key(window,'F5')
                for _ in range(100):
                    if slot.exists():break
                    time.sleep(.02)
                before=json.loads(subprocess.run([str(ROOT/'build/btech-headless'),'--load',str(slot)],cwd=ROOT,check=True,capture_output=True,text=True).stdout)
                keys.key(window,'Right');keys.key(window,'F9');keys.close_window(window)
                out,err=process.communicate(timeout=10)
                if process.returncode:raise RuntimeError(err)
                actual=json.loads(out);delta=actual['tick']-before['tick']
                if not 0<=delta<=50:raise RuntimeError(name+' restore interval was unbounded')
                tail.write_text('idle\n'*delta)
                wanted=subprocess.run([str(ROOT/'build/btech-headless'),'--load',str(slot),'--replay',str(tail),
                    '--frame',str(expected)],cwd=ROOT,check=True,capture_output=True,text=True)
                if actual!=json.loads(wanted.stdout) or frame.read_bytes()!=expected.read_bytes():
                    raise RuntimeError(name+' F5/F9 changed the view or its saved state')
                required={'character':6,'overhead':13,'mech':21}[name]
                if actual['actions_menu']['phase']!=required:raise RuntimeError(name+' view was not open during save/load')
                print(f'PASS: native F5/F9 while {name} view is open; exact saved state, resumed ticks and RGB pixels.',flush=True)
            finally:
                keys.x.XCloseDisplay(keys.display)
                if process.poll() is None:process.terminate();process.wait(timeout=5)

def presentation(env,work):
    """Focused, real-time SDL checks, seeded by ordinary logical input saves."""
    binary=ROOT/'build/btech-headless';native=ROOT/'build/btech-port'
    source=ROOT/'tests/fixtures/ordinary-combat.actions'
    def locate(path,predicates):
        found={};process=subprocess.Popen([str(binary),'--replay',str(path),'--trace'],cwd=ROOT,text=True,stdout=subprocess.PIPE)
        try:
            for tick,row in enumerate(process.stdout):
                state=json.loads(row)
                for name,predicate in predicates.items():
                    if name not in found and predicate(state):found[name]=tick
                if len(found)==len(predicates):break
            if len(found)!=len(predicates):raise RuntimeError('Missing presentation checkpoints: '+str(predicates.keys()-found.keys()))
        finally:
            process.terminate();process.stdout.close();process.wait(timeout=5)
        return found
    ticks=locate(source,{'entry':lambda s:s['mode']=='entry-confirm',
        'combat-control':lambda s:s['combat']['phase']==1 and not s['animation']['active'],
        'combat-sound':lambda s:s['audio']['effects'] and s['combat']['phase']==9,
        'return-to-base':lambda s:s['mission']['phase']==7})
    fight=ROOT/'tests/fixtures/ordinary-training-combat.actions'
    outtake=locate(fight,{'combat-outtake':lambda s:s['animation']['active']==3})
    cases=[('entry',source,ticks['entry'],['idle']*2),
        ('combat-control',source,ticks['combat-control'],['idle']*2),
        ('combat-sound',source,ticks['combat-sound'],['idle']*30),
        ('combat-outtake',fight,outtake['combat-outtake'],['idle']*30),
        ('return-to-base',source,ticks['return-to-base'],['idle']*2+['accept'])]
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
            if name=='return-to-base' and device['nonzero']:raise RuntimeError(name+' plays sound after combat completion')
            if device.get('peak_queued_bytes',0)>3*1536*2:raise RuntimeError(name+' audio device backlog exceeds three ticks')
            print(f'PASS: native {name}, exact input/state/pixels; SDL queued {device["nonzero"]} nonzero audio samples.',flush=True)

def original_saves(env,work):
    """Six owner GAME files enter SDL, inspect Jason, save and reopen privately."""
    binary=ROOT/'build/btech-headless';native=ROOT/'build/btech-port'
    with tempfile.TemporaryDirectory(prefix='native-original-',dir=work) as directory:
        tmp=Path(directory)
        for slot in range(1,7):
            original=ROOT/f'Original DOS/GAME{slot}';raw=original.read_bytes()
            active=any(raw[0x111+125*i]!=255 for i in range(4))
            keys=['menu']+['down']*(3 if active else 2)+['accept']+(['down','accept'] if active else [])+(['accept'] if sum(raw[1+17*i]!=255 for i in range(8))>1 else [])+['idle','cancel']
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

def field(env,work):
    """Original GAME3 prerequisite and saved native crew/medical/equipment input."""
    subprocess.run([str(ROOT/'build/btp-menu-tests'),str(ROOT/'Original DOS')],cwd=ROOT,check=True,capture_output=True,text=True)
    with tempfile.TemporaryDirectory(prefix='native-field-',dir=work) as directory:
        tmp=Path(directory);tail=tmp/'tail.actions';record=tmp/'record.actions';frame=work/'native-field.ppm';expected=tmp/'expected.ppm'
        keys=['menu']+['down']*3+['accept','down','accept','accept','down','accept','down','accept','menu']+['down']*4+['accept','accept']
        tail.write_text('\n'.join(keys)+'\n')
        actual=subprocess.run([str(ROOT/'build/btech-port'),'--load',str(work/'crew-menu.btp'),'--smoke-replay','--smoke-fast','--replay',str(tail),'--record',str(record),'--frame',str(frame)],cwd=ROOT,env=env,check=True,capture_output=True,text=True)
        wanted=subprocess.run([str(ROOT/'build/btech-headless'),'--load',str(work/'crew-menu.btp'),'--replay',str(record),'--frame',str(expected)],cwd=ROOT,check=True,capture_output=True,text=True)
        if json.loads(actual.stdout)!=json.loads(wanted.stdout) or frame.read_bytes()!=expected.read_bytes():raise RuntimeError('Native field continuation differs')
        print('PASS: native original-save prerequisite, crew continuation, gear transfer and field healing; exact SDL state/pixels.',flush=True)

def controls(env,work):
    """Actual keypad keys with Num Lock off, plus one-key ending exits."""
    from reference_session import WindowKeys
    subprocess.run([str(ROOT/'build/btp-cache-tests'),str(ROOT/'Original DOS')],cwd=ROOT,check=True,capture_output=True,text=True)
    cases=(('keypad',None,('space','KP_2','KP_8','KP_6','KP_4','KP_Enter'),['menu','down','up','right','left','accept']),
           ('ending-letter',work/'m4-audit/cache-final-key.btp',('q',),['accept']),
           ('ending-legacy',work/'m4-audit/cache-old-ending.btp',('F1',),['accept']))
    with tempfile.TemporaryDirectory(prefix='native-controls-',dir=work) as directory:
        tmp=Path(directory)
        for label,start,physical,wanted_keys in cases:
            record=tmp/f'{label}.actions';frame=tmp/f'{label}.ppm';expected=tmp/'expected.ppm'
            if not start:
                fresh=tmp/'fresh.btp'
                subprocess.run([str(ROOT/'build/btech-headless'),'--save',str(fresh)],cwd=ROOT,check=True,capture_output=True)
            initial=['--load',str(start or fresh)]
            process=subprocess.Popen([str(ROOT/'build/btech-port'),*initial,'--record',str(record),'--frame',str(frame)],
                cwd=ROOT,env=dict(env,SDL_AUDIODRIVER='dummy'),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            keys=WindowKeys()
            try:
                window=None
                for _ in range(100):
                    found=[w for w,n in keys.windows() if n.startswith('BtechPort')]
                    if len(found)==1:window=found[0];break
                    if process.poll() is not None:raise RuntimeError(label+' window exited before key input')
                    time.sleep(.02)
                if window is None:raise RuntimeError(label+' window unavailable')
                for key in physical:keys.key(window,key)
                if not start:keys.key(window,'Ctrl+Shift+Escape')
                out,err=process.communicate(timeout=5)
                if process.returncode:raise RuntimeError(err)
                logical=[a for a in record.read_text().splitlines() if a!='idle']
                if logical!=wanted_keys:raise RuntimeError(label+' key mapping: '+repr(logical))
                replay=subprocess.run([str(ROOT/'build/btech-headless'),*initial,'--replay',str(record),'--frame',str(expected)],
                    cwd=ROOT,check=True,capture_output=True,text=True)
                if json.loads(out)!=json.loads(replay.stdout) or frame.read_bytes()!=expected.read_bytes():
                    raise RuntimeError(label+' SDL state/pixels differ from recorded replay')
                print('PASS: native '+label+', actual X11 keys, complete state/pixel replay and process exit.',flush=True)
            finally:
                keys.x.XCloseDisplay(keys.display)
                if process.poll() is None:process.terminate();process.wait(timeout=5)

def intro(env,work):
    """Real held-Shift keys, both intro screens, audio and new/load branches."""
    from reference_session import WindowKeys
    env=dict(env,SDL_AUDIODRIVER='dummy')
    with tempfile.TemporaryDirectory(prefix='native-intro-',dir=work) as directory:
        tmp=Path(directory);record=tmp/'keys.actions';frame=work/'native-intro.ppm'
        report=tmp/'audio.json';expected=tmp/'expected.ppm';slot=tmp/'slot.btp'
        process=subprocess.Popen([str(ROOT/'build/btech-port'),'--intro-preview',
            '--record',str(record),'--frame',str(frame),'--audio-report',str(report),
            '--save-file',str(slot)],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        keys=WindowKeys()
        try:
            window=None
            for _ in range(100):
                found=[w for w,n in keys.windows() if n.startswith('BtechPort')]
                if len(found)==1:window=found[0];break
                if process.poll() is not None:raise RuntimeError('Intro window failed')
                time.sleep(.02)
            if window is None:raise RuntimeError('Intro window did not appear')
            for key in ('Escape','Shift+k+r','Shift+k+y+r','space',
                        'Escape','Shift+k+y+r','space','Shift+k+y+r','Escape','Return'):
                keys.key(window,key)
                if process.poll() is not None:raise RuntimeError('Escape or intro input closed the game')
            keys.key(window,'Ctrl+Shift+Escape')
            out,err=process.communicate(timeout=10)
            if process.returncode:raise RuntimeError(err)
            replay=subprocess.run([str(ROOT/'build/btech-headless'),'--intro-preview',
                '--replay',str(record),'--frame',str(expected)],cwd=ROOT,check=True,capture_output=True,text=True)
            actual=json.loads(out)
            if actual!=json.loads(replay.stdout) or frame.read_bytes()!=expected.read_bytes():
                raise RuntimeError('Intro SDL input/state/pixels differ from complete replay')
            if actual['mode']!='local-exploration' or actual['credits']!=30035 or record.read_text().splitlines().count('credit-10000')!=3:
                raise RuntimeError(f"Held-Shift sequence or fresh-game branch failed: mode={actual['mode']}, credits={actual['credits']}, sequences={record.read_text().splitlines().count('credit-10000')}")
            audio=json.loads(report.read_text())
            if not audio['opened'] or not audio['nonzero']:
                raise RuntimeError('Intro music did not reach the SDL audio device')
            print('PASS: real Shift K/Y/R in logo, title and question; Escape remains in game, Ctrl+Shift+Escape exits; SDL music and exact replay.',flush=True)
        finally:
            keys.x.XCloseDisplay(keys.display)
            if process.poll() is None:process.terminate();process.wait(timeout=5)
        tail=tmp/'load.actions';tail.write_text('menu\nmenu\nup\naccept\n')
        native=subprocess.run([str(ROOT/'build/btech-port'),'--intro-preview','--smoke-replay',
            '--smoke-fast','--replay',str(tail),'--save-file',str(slot),'--record',str(record),
            '--frame',str(frame)],cwd=ROOT,env=env,check=True,capture_output=True,text=True,timeout=20)
        replay=subprocess.run([str(ROOT/'build/btech-headless'),'--intro-preview','--replay',
            str(record),'--save-file',str(slot),'--frame',str(expected)],cwd=ROOT,check=True,capture_output=True,text=True)
        if json.loads(native.stdout)!=json.loads(replay.stdout) or frame.read_bytes()!=expected.read_bytes():
            raise RuntimeError('Intro saved-game branch differs')
        if json.loads(native.stdout)['mode']!='actions':raise RuntimeError('Yes did not open saved games')
        print('PASS: played-before Yes opens the six saved-game slots; No starts fresh at training grounds.',flush=True)

def cache(env,work):
    """Bounded authentic late-save cache contexts, SDL continuation and pixels."""
    from reference_session import WindowKeys
    binary=ROOT/'build/btech-headless';native=ROOT/'build/btech-port'
    lines=(ROOT/'tests/fixtures/ordinary-cache.actions').read_text().splitlines()
    facts=json.loads((ROOT/'tests/fixtures/ordinary-cache.json').read_text())
    points={c['label']:c['tick'] for c in facts['checkpoints']}
    cases=[('code-terminal-1',['right','left','accept']),('door-2-opening',['idle']*128),
        ('phoenix-screen',['accept']),('map-room',['menu','up','accept']),
        ('white-code-accepted',['idle']*64+['accept']),
        ('ending-start',lines[points['ending-start']:])]
    with tempfile.TemporaryDirectory(prefix='native-cache-',dir=work) as directory:
        tmp=Path(directory);prefix=tmp/'prefix.actions';start=tmp/'start.btp';tail=tmp/'tail.actions';record=tmp/'record.actions'
        for label,actions in cases:
            prefix.write_text('\n'.join(lines[:points[label]])+'\n')
            subprocess.run([str(binary),'--load',str(ROOT/'Original DOS/GAME1'),'--replay',str(prefix),
                '--save',str(start)],cwd=ROOT,check=True,capture_output=True,timeout=20)
            tail.write_text('\n'.join(actions)+'\n');frame=work/f'native-cache-{label}.ppm';expected=tmp/'expected.ppm'
            actual=subprocess.run([str(native),'--load',str(start),'--smoke-replay','--smoke-fast',
                '--replay',str(tail),'--record',str(record),'--frame',str(frame)],cwd=ROOT,
                env=dict(env,SDL_AUDIODRIVER='dummy'),check=True,capture_output=True,text=True,timeout=25)
            wanted=subprocess.run([str(binary),'--load',str(start),'--replay',str(record),'--frame',str(expected)],
                cwd=ROOT,check=True,capture_output=True,text=True,timeout=20)
            if json.loads(actual.stdout)!=json.loads(wanted.stdout) or frame.read_bytes()!=expected.read_bytes():
                raise RuntimeError(label+' cache SDL continuation differs')
            print(f'PASS: native cache {label}, exact recorded input/state/pixels.',flush=True)
        for label in ('map-room','phoenix-screen'):
            prefix.write_text('\n'.join(lines[:points[label]])+'\n')
            subprocess.run([str(binary),'--load',str(ROOT/'Original DOS/GAME1'),'--replay',str(prefix),
                '--save',str(start)],cwd=ROOT,check=True,capture_output=True)
            slot=tmp/'slot.btp';frame=work/f'native-cache-{label}-restore.ppm'
            process=subprocess.Popen([str(native),'--load',str(start),'--save-file',str(slot),'--frame',str(frame)],
                cwd=ROOT,env=dict(env,SDL_AUDIODRIVER='dummy'),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            keys=WindowKeys()
            try:
                window=None
                for _ in range(100):
                    found=[w for w,n in keys.windows() if n.startswith('BtechPort')]
                    if len(found)==1:window=found[0];break
                    if process.poll() is not None:raise RuntimeError('Cache restore window failed')
                    time.sleep(.02)
                if window is None:raise RuntimeError('Cache restore window did not appear')
                keys.key(window,'F5')
                for _ in range(100):
                    if slot.exists():break
                    time.sleep(.02)
                before=json.loads(subprocess.check_output([str(binary),'--load',str(slot)],cwd=ROOT,text=True))
                keys.key(window,'Right');keys.key(window,'Return');keys.key(window,'F9');keys.close_window(window)
                out,err=process.communicate(timeout=10)
                if process.returncode:raise RuntimeError(err)
                state=json.loads(out);delta=state['tick']-before['tick']
                if not 0<=delta<=50:raise RuntimeError('Cache restore clock was unbounded')
                tail.write_text('idle\n'*delta)
                wanted=subprocess.run([str(binary),'--load',str(slot),'--replay',str(tail),'--frame',str(expected)],
                    cwd=ROOT,check=True,capture_output=True,text=True)
                if state!=json.loads(wanted.stdout) or frame.read_bytes()!=expected.read_bytes():
                    raise RuntimeError('Cache F5/F9 failed '+label)
                print(f'PASS: native cache F5/F9 restores {label}, exact state, clock and pixels.',flush=True)
            finally:
                keys.x.XCloseDisplay(keys.display)
                if process.poll() is None:process.terminate();process.wait(timeout=5)

def story(env,work):
    """New hospital and jail visitor tails retain their ordinary campaign prefix."""
    binary=ROOT/'build/btech-headless';native=ROOT/'build/btech-port'
    with tempfile.TemporaryDirectory(prefix='native-story-',dir=work) as directory:
        tmp=Path(directory);prefix=tmp/'prefix.actions';start=tmp/'start.btp';tail=tmp/'tail.actions';record=tmp/'record.actions'
        for kind,label in [('hospital','hospital-menu'),('jail-visitor','jail-visitor-menu'),('hospital-healing','hospital-menu')]:
            lines=(ROOT/f'tests/fixtures/ordinary-{kind}.actions').read_text().splitlines()
            facts=json.loads((ROOT/f'tests/fixtures/ordinary-{kind}.json').read_text())
            tick=next(c['tick'] for c in facts['checkpoints'] if c['label']==label)
            prefix.write_text('\n'.join(lines[:tick])+'\n');tail.write_text('\n'.join(lines[tick:])+'\n')
            initial=['--load',str(ROOT/'Original DOS/GAME2')] if kind=='hospital-healing' else []
            subprocess.run([str(binary),*initial,'--replay',str(prefix),'--save',str(start)],cwd=ROOT,check=True,capture_output=True,timeout=20)
            frame=work/f'native-{kind}.ppm';expected=tmp/'expected.ppm'
            actual=subprocess.run([str(native),'--load',str(start),'--smoke-replay','--smoke-fast',
                '--replay',str(tail),'--record',str(record),'--frame',str(frame)],cwd=ROOT,env=dict(env,SDL_AUDIODRIVER='dummy'),
                check=True,capture_output=True,text=True,timeout=25)
            wanted=subprocess.run([str(binary),'--load',str(start),'--replay',str(record),'--frame',str(expected)],cwd=ROOT,
                check=True,capture_output=True,text=True,timeout=20)
            if json.loads(actual.stdout)!=json.loads(wanted.stdout) or frame.read_bytes()!=expected.read_bytes():
                raise RuntimeError(kind+' companion SDL continuation differs')
            print(f'PASS: native {kind}, {len(lines)-tick+5} recorded SDL inputs through recruitment, exact state/pixels.',flush=True)

def followups(env,work,cases=None):
    """Saved ordinary entrances/thefts exercise actual SDL input and pixels."""
    binary=ROOT/'build/btech-headless';native=ROOT/'build/btech-port'
    cases=cases or [('mayor-newspaper','house-menu','GAME3'),('mayor-chow','house-menu','GAME3'),
        ('cinema','entry','GAME3'),('inventor','entry','GAME3'),('inventor-qualified','entry','GAME5'),
        ('laser-guns','laser-shop-robbery','GAME3'),('prison-theft','impound-yard-start',None),
        ('arena-theft','arena-rented-locust','GAME3'),
        ('spy-replacement','technician-recruitment-wait',None),
        ('alternate-services','entry','GAME3')]
    with tempfile.TemporaryDirectory(prefix='native-followup-',dir=work) as directory:
        tmp=Path(directory);prefix=tmp/'prefix.actions';start=tmp/'start.btp';tail=tmp/'tail.actions';record=tmp/'record.actions'
        for kind,label,source in cases:
            lines=(ROOT/f'tests/fixtures/ordinary-{kind}.actions').read_text().splitlines()
            facts=json.loads((ROOT/f'tests/fixtures/ordinary-{kind}.json').read_text());tick=next(c['tick'] for c in facts['checkpoints'] if c['label']==label)
            prefix.write_text('\n'.join(lines[:tick])+'\n')
            # These tails have menus and confirmations, no numeric amount
            # editors. Compare physical Space against the original Enter
            # replay, rather than replaying a possibly incorrect key mapping.
            tail.write_text('\n'.join('menu' if key=='accept' else key for key in lines[tick:])+'\n')
            initial=['--load',str(ROOT/'Original DOS'/source)] if source else []
            subprocess.run([str(binary),*initial,'--replay',str(prefix),'--save',str(start)],cwd=ROOT,check=True,capture_output=True,timeout=20)
            frame=work/f'native-{kind}.ppm';expected=tmp/'expected.ppm'
            actual=subprocess.run([str(native),'--load',str(start),'--smoke-replay','--smoke-fast',
                '--replay',str(tail),'--record',str(record),'--frame',str(frame)],cwd=ROOT,env=dict(env,SDL_AUDIODRIVER='dummy'),
                check=True,capture_output=True,text=True,timeout=40)
            tail.write_text('\n'.join(lines[tick:]+['idle']*5)+'\n')
            wanted=subprocess.run([str(binary),'--load',str(start),'--replay',str(tail),'--frame',str(expected)],cwd=ROOT,
                check=True,capture_output=True,text=True,timeout=20)
            if json.loads(actual.stdout)!=json.loads(wanted.stdout) or frame.read_bytes()!=expected.read_bytes():raise RuntimeError(kind+' SDL continuation differs')
            print(f'PASS: native {kind}, Space menu selections match ordinary Enter route state/pixels.',flush=True)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--windows',action='store_true',help='Run the Windows SDL build under isolated Wine against Linux headless')
    parser.add_argument('--portability-only',action='store_true',help='Check controls, intro, saves, menus and combat presentation')
    parser.add_argument('--updated-only',action='store_true',help='Check edition selection and Updated purchases')
    parser.add_argument('--project-only',action='store_true',help='Check project loading, weapons, broker and package saves')
    parser.add_argument('--adventure-only',action='store_true',help='Check authored maps, event screens, combat and saves')
    parser.add_argument('--battletech-demo-only',action='store_true',help='Check BattleTech demo screens, saves and complete two-contract route')
    parser.add_argument('--editor-only',action='store_true',help='Check the desktop roster editor and Play launch')
    parser.add_argument('--editor-usability-only',action='store_true',help='Check editor dialogs, drafts and workspace workflows')
    parser.add_argument('--editor-focus-only',action='store_true',help='Check modal focus under KWin on an isolated display/session')
    parser.add_argument('--editor-combat-mission-only',action='store_true',help='Check mission combat groups, actor routes, round timers and Play')
    parser.add_argument('--editor-style-only',action='store_true',help='Check construction coverage, road junctions, roof-only walls, event descriptions and list controls')
    parser.add_argument('--editor-source-only',action='store_true',help='Check modular project conversion, source edits, Save, Build, error navigation and Play')
    parser.add_argument('--editor-capacity-only',action='store_true',help='Check v3 upgrade and large campaign map/event editing, diagnostics, builds and Play')
    parser.add_argument('--editor-mission-only',action='store_true',help='Check region drawing, mission forms, recovery and extraction mission Play')
    parser.add_argument('--construction-library-only',action='store_true',help='Check shared construction/pattern export, import, drawing and revision updates')
    parser.add_argument('--editor-benchmark-only',action='store_true',help='Measure the declared large fixture in a fresh process')
    parser.add_argument('--editor-library-workspace-only',action='store_true',help='Check asynchronous library scope saving and recovery')
    parser.add_argument('--independent-only',action='store_true',help='Check independent quest and saved SDL screens without original files')
    parser.add_argument('--vehicles-only',action='store_true',help='Check vehicles, planets, map, inspection and depot SDL save/load screens')
    parser.add_argument('--map-editor-only',action='store_true',help='Check map painting, event forms, export and Play here')
    parser.add_argument('--editor-visual-only',action='store_true',help='Check original tile previews, visual picker and marker dragging')
    parser.add_argument('--editor-canvas-only',action='store_true',help='Check editable zoom, wheel anchoring and visible drawing tools')
    parser.add_argument('--editor-paint-only',action='store_true',help='Check visible-surface painting, construction details and marker tool isolation')
    parser.add_argument('--editor-play-tile-only',action='store_true',help='Check Play retry and neighbour-aware map tile editing')
    parser.add_argument('--editor-tile-animation-only',action='store_true',help='Check animated terrain selection, preview, cloning and frame timing')
    parser.add_argument('--editor-authoring-only',action='store_true',help='Check human paint, authoring command batches, Undo, stale rejection and Play')
    parser.add_argument('--editor-collaboration-only',action='store_true',help='Check protected human edits, reviewed changes and a live local authoring session')
    parser.add_argument('--editor-campaign-demo-only',action='store_true',help='Check AI8 campaign GUI edits, scoped follow-up, Undo/save and Play')
    parser.add_argument('--editor-world-routes-only',action='store_true',help='Check world-route diagnostics, town/planet navigation and repair')
    parser.add_argument('--editor-checkpoints-only',action='store_true',help='Check saved scenario starts, selection, reports and stale-content errors')
    parser.add_argument('--world-art-editor-only',action='store_true',help='Check jigsaw/city and pixel/animation editing')
    parser.add_argument('--map-construction-only',action='store_true',help='Check building/wall/road tools, tile management, patterns and original-size world creation')
    parser.add_argument('--library-editor-only',action='store_true',help='Check shared library editing/import/export and desktop game launch')
    parser.add_argument('--delivery-only',type=Path,help='Check an unpacked Linux Construction Kit using its bundled runtime')
    parser.add_argument('--construction-kit-only',action='store_true',help='Check service/quest/event and advanced authoring workflows')
    parser.add_argument('--updated-combat-only',action='store_true',help='Check Updated rules settings and held LRM combat saves')
    parser.add_argument('--building-art-only',action='store_true',help='Check Updated building portraits and held saves')
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
    parser.add_argument('--field-only',action='store_true')
    parser.add_argument('--intro-only',action='store_true')
    parser.add_argument('--overhead-only',action='store_true')
    parser.add_argument('--cache-only',action='store_true')
    parser.add_argument('--story-only',action='store_true')
    parser.add_argument('--followups-only',action='store_true')
    parser.add_argument('--arena-only',action='store_true')
    parser.add_argument('--town-only',action='store_true')
    parser.add_argument('--m4-acceptance',action='store_true')
    parser.add_argument('--combat-ui-only',action='store_true')
    parser.add_argument('--combat-pacing-only',action='store_true')
    parser.add_argument('--weapon-effects-only',action='store_true')
    parser.add_argument('--mechit-only',action='store_true')
    parser.add_argument('--island-only',action='store_true')
    parser.add_argument('--controls-only',action='store_true')
    parser.add_argument('--encounters-only',action='store_true')
    parser.add_argument('--completion-only',action='store_true')
    args = parser.parse_args()
    if args.windows:windows_frontend()
    work = ROOT / "work"
    work.mkdir(exist_ok=True)
    read_fd, write_fd = os.pipe()
    with (work / "native-xvfb.log").open("w") as log:
        xvfb = subprocess.Popen([str(ROOT / "local-deps/xvfb/usr/bin/Xvfb"),
            "-displayfd", str(write_fd), "-screen", "0", "1600x1000x24" if args.editor_usability_only or args.editor_focus_only or args.editor_mission_only or args.editor_combat_mission_only or args.editor_style_only or args.editor_source_only or args.editor_capacity_only or args.editor_campaign_demo_only or args.editor_world_routes_only or args.editor_checkpoints_only or args.construction_library_only or args.editor_canvas_only or args.editor_paint_only or args.editor_tile_animation_only or args.editor_authoring_only or args.editor_collaboration_only else "1024x768x24", "-nolisten", "tcp"],
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
            if args.editor_focus_only:
                from editor_focus_smoke import run
                run(env,work)
                return
            if args.editor_combat_mission_only:
                from editor_combat_mission_smoke import run
                run(env,work);return 0
            if args.editor_style_only:
                from editor_style_smoke import run
                run(env,work);return 0
            if args.editor_source_only:
                from editor_source_smoke import run
                run(env,work);return 0
            if args.editor_capacity_only:
                from editor_capacity_smoke import run
                run(env,work);return 0
            if args.editor_mission_only:
                from editor_mission_smoke import run
                run(env,work)
                return
            if args.construction_library_only:
                from construction_library_smoke import run
                run(env,work)
                return
            if args.editor_benchmark_only:
                from editor_benchmark import standalone
                standalone(env,work)
                return
            if args.editor_library_workspace_only:
                from editor_workspace_library_smoke import run
                run(env,work)
                return
            if args.delivery_only:
                subprocess.run([str(args.delivery_only.resolve()/"ConstructionKit"),"--check-runtime"],env=env,cwd="/tmp",check=True,timeout=40)
                return
            if args.editor_usability_only:
                from editor_usability_smoke import run
                run(env,work)
                return
            if args.construction_kit_only:
                from construction_kit_smoke import run
                run(env,work)
                return
            if args.library_editor_only:
                from library_editor_smoke import run
                run(env,work)
                return
            if args.world_art_editor_only:
                from world_art_smoke import run
                run(env,work)
                return
            if args.map_construction_only:
                from map_construction_smoke import run
                run(env,work)
                return
            if args.editor_visual_only:
                from editor_visual_smoke import run
                run(env,work)
                return
            if args.editor_canvas_only:
                from editor_canvas_smoke import run
                run(env,work)
                return
            if args.editor_paint_only:
                from editor_paint_smoke import run
                run(env,work)
                return
            if args.editor_play_tile_only:
                from editor_play_tile_smoke import run
                run(env,work)
                return
            if args.editor_tile_animation_only:
                from editor_tile_animation_smoke import run
                run(env,work)
                return
            if args.editor_authoring_only:
                from editor_authoring_smoke import run
                run(env,work)
                return
            if args.editor_collaboration_only:
                from editor_collaboration_smoke import run
                run(env,work)
                return
            if args.editor_campaign_demo_only:
                from editor_campaign_demo_smoke import run
                run(env,work)
                return
            if args.editor_world_routes_only:
                from editor_world_routes_smoke import run
                run(env,work)
                return
            if args.editor_checkpoints_only:
                from editor_checkpoint_smoke import run
                run(env,work)
                return
            if args.battletech_demo_only:
                from adventure_smoke import run
                run(env,work,battletech=True)
                return
            if args.independent_only or args.vehicles_only:
                from independent_smoke import run
                run(env,work,vehicles=args.vehicles_only)
                return
            if args.map_editor_only:
                from independent_smoke import editor
                editor(env,work)
                return
            if args.project_only:
                from project_smoke import run
                run(env,work);return
            if args.adventure_only:
                from adventure_smoke import run
                run(env,work);return
            if args.editor_only:
                from adventure_smoke import editor
                editor(env,work);return
            if args.updated_combat_only:
                from updated_combat_smoke import run
                run(env,work);return
            if args.updated_only or args.building_art_only:
                from updated_smoke import run
                run(env,work,building_art_only=args.building_art_only);return
            if args.portability_only:
                controls(env,work);diagonals(env,work);intro(env,work)
                menu(env,work);saves(env,work);presentation(env,work)
                combat_ui(env,work);return
            if args.m4_acceptance:
                controls(env,work)
                intro(env,work);menu(env,work);presentation(env,work)
                combat_ui(env,work)
                mechit_ui(env,work)
                cache_island(env,work)
                original_saves(env,work);aftermath(env,work);field(env,work)
                saves(env,work);campaign(env,work);story(env,work);cache(env,work);return
            if args.completion_only:
                completion_panels(env,work)
                followups(env,work,[('cinema','entry','GAME3')]);return
            if args.followups_only:
                followups(env,work);return
            if args.arena_only:
                followups(env,work,[(f'arena-{ownership}-{result}','arena-start','GAME3')
                    for ownership in ('owned','rental') for result in ('loss','win')]+[
                    ('arena-theft','arena-rented-locust','GAME3'),('prison-loss','prison-guards',None)])
                return
            if args.town_only:
                followups(env,work,[('hospital-talk','town-arrival-wait','GAME2')]);return
            if args.controls_only:
                controls(env,work);diagonals(env,work);return
            if args.encounters_only:
                encounter_placement(env,work);return
            if args.combat_ui_only:
                combat_ui(env,work);return
            if args.combat_pacing_only:
                combat_pacing(env,work);return
            if args.weapon_effects_only:
                weapon_effects(env,work);return
            if args.mechit_only:
                mechit_ui(env,work);return
            if args.island_only:
                cache_island(env,work);return
            if args.intro_only:
                intro(env,work);return
            if args.overhead_only:
                overhead(env,work);return
            if args.cache_only:
                cache(env,work);return
            if args.story_only:
                story(env,work);return
            if args.field_only:
                field(env,work);return
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
