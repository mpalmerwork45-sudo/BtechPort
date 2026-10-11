#!/usr/bin/env python3
"""Run a bounded JSON input/capture script in DOSBox on a private display.

X11 events are sent only to this session's DOSBox window. Scans and snapshots are
read-only. The explicit controlled-talk-context command sets an audited NPC/result
precondition in the child emulator; executable/resource/save files stay unchanged.
All exports are under ignored work/.
"""
import ctypes as c
import json
import os
import shlex
import select
import signal
import struct
import subprocess
import sys
import time
import argparse
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work"


class KeyEvent(c.Structure):
    _fields_ = [("type", c.c_int), ("serial", c.c_ulong), ("send_event", c.c_int),
                ("display", c.c_void_p), ("window", c.c_ulong), ("root", c.c_ulong),
                ("subwindow", c.c_ulong), ("time", c.c_ulong), ("x", c.c_int),
                ("y", c.c_int), ("x_root", c.c_int), ("y_root", c.c_int),
                ("state", c.c_uint), ("keycode", c.c_uint), ("same_screen", c.c_int)]


class Event(c.Union):
    _fields_ = [("key", KeyEvent), ("pad", c.c_long * 24)]


class ClientMessage(c.Structure):
    _fields_ = [("type",c.c_int),("serial",c.c_ulong),("send_event",c.c_int),
                ("display",c.c_void_p),("window",c.c_ulong),("message_type",c.c_ulong),
                ("format",c.c_int),("data",c.c_long*5)]


class WindowKeys:
    def __init__(self):
        self.x = c.CDLL("libX11.so.6")
        self.x.XOpenDisplay.argtypes = [c.c_char_p]
        self.x.XOpenDisplay.restype = c.c_void_p
        self.display = self.x.XOpenDisplay(None)
        if not self.display:
            raise RuntimeError("X11 display unavailable")
        self.x.XDefaultRootWindow.argtypes = [c.c_void_p]
        self.x.XDefaultRootWindow.restype = c.c_ulong
        self.root = self.x.XDefaultRootWindow(self.display)
        self.x.XQueryTree.argtypes = [c.c_void_p, c.c_ulong, c.POINTER(c.c_ulong),
                                     c.POINTER(c.c_ulong), c.POINTER(c.POINTER(c.c_ulong)),
                                     c.POINTER(c.c_uint)]
        self.x.XFetchName.argtypes = [c.c_void_p, c.c_ulong, c.POINTER(c.c_char_p)]
        self.x.XStringToKeysym.argtypes = [c.c_char_p]
        self.x.XStringToKeysym.restype = c.c_ulong
        self.x.XKeysymToKeycode.argtypes = [c.c_void_p, c.c_ulong]
        self.x.XKeysymToKeycode.restype = c.c_uint
        self.x.XSendEvent.argtypes = [c.c_void_p, c.c_ulong, c.c_int, c.c_long, c.POINTER(Event)]
        self.x.XFlush.argtypes = [c.c_void_p]
        self.x.XFree.argtypes = [c.c_void_p]
        self.x.XInternAtom.argtypes = [c.c_void_p,c.c_char_p,c.c_int]
        self.x.XInternAtom.restype = c.c_ulong
        self.x.XCloseDisplay.argtypes = [c.c_void_p]
        self.x.XSetInputFocus.argtypes = [c.c_void_p, c.c_ulong, c.c_int, c.c_ulong]
        self.x.XGetInputFocus.argtypes = [c.c_void_p, c.POINTER(c.c_ulong), c.POINTER(c.c_int)]
        self.x.XRaiseWindow.argtypes = [c.c_void_p, c.c_ulong]
        self.xt = c.CDLL("libXtst.so.6")
        self.xt.XTestFakeKeyEvent.argtypes = [c.c_void_p, c.c_uint, c.c_int, c.c_ulong]

    def windows(self, parent=None, depth=0):
        if depth > 5:
            return []
        root, p, children, n = c.c_ulong(), c.c_ulong(), c.POINTER(c.c_ulong)(), c.c_uint()
        out = []
        if self.x.XQueryTree(self.display, parent or self.root, c.byref(root), c.byref(p), c.byref(children), c.byref(n)):
            ids = [children[i] for i in range(n.value)]
            if children:
                self.x.XFree(children)
            for wid in ids:
                name = c.c_char_p()
                if self.x.XFetchName(self.display, wid, c.byref(name)) and name.value:
                    out.append((wid, name.value.decode(errors="replace")))
                    self.x.XFree(name)
                out.extend(self.windows(wid, depth + 1))
        return out

    def find_dosbox(self):
        matches = [(w, n) for w, n in self.windows() if n.startswith("DOSBox")]
        if len(matches) != 1:
            raise RuntimeError(f"Expected exactly this session's DOSBox window, got {matches}")
        return matches[0][0]

    def key(self, window, names):
        parts = names.split("+")
        codes = []
        for part in parts:
            keyname = {"Ctrl": "Control_L", "Alt": "Alt_L", "Shift": "Shift_L"}.get(part, part)
            code = self.x.XKeysymToKeycode(self.display, self.x.XStringToKeysym(keyname.encode()))
            if not code:
                raise ValueError(f"Unknown key: {names}")
            codes.append(code)
        # Ask the window manager to activate this window (KWin can reject direct
        # focus changes). Source 2 identifies a window-management tool.
        if os.environ.get("BTECH_REFERENCE_VIRTUAL"):
            self.x.XSetInputFocus(self.display,window,1,0)
        else:
            activate=ClientMessage(33,0,1,self.display,window,
                self.x.XInternAtom(self.display,b"_NET_ACTIVE_WINDOW",0),32,(c.c_long*5)(2,0,0,0,0))
            self.x.XSendEvent(self.display,self.root,0,(1<<20)|(1<<19),c.cast(c.byref(activate),c.POINTER(Event)))
        self.x.XFlush(self.display)
        focused, revert = c.c_ulong(), c.c_int()
        for _ in range(40):
            self.x.XGetInputFocus(self.display, c.byref(focused), c.byref(revert))
            if focused.value==window:break
            time.sleep(0.05)
        if focused.value != window:
            raise RuntimeError(f"Focus was refused: {focused.value} != {window}")
        for code in codes:
            if not self.xt.XTestFakeKeyEvent(self.display, code, 1, 0):
                raise RuntimeError("XTEST key press failed")
            self.x.XFlush(self.display)
            time.sleep(0.06)
        for code in reversed(codes):
            self.xt.XTestFakeKeyEvent(self.display, code, 0, 0)
            self.x.XFlush(self.display)
            time.sleep(0.06)


def memory_candidates(pid):
    # Use the unrelocated load-image offset, not the EXEPACK disk offset.
    # Further BIOS/entry checks are required before treating this as guest RAM.
    anchor = b"BattleTech: The Crescent Hawk's Inception"
    candidates = []
    fd = os.open(f"/proc/{pid}/mem", os.O_RDONLY)
    try:
        for line in Path(f"/proc/{pid}/maps").read_text().splitlines():
            fields = line.split()
            lo, hi = (int(v, 16) for v in fields[0].split("-"))
            if "rw" not in fields[1] or hi - lo > 64 * 1024 * 1024:
                continue
            try:
                buf = os.pread(fd, hi - lo, lo)
            except OSError:
                continue
            start = 0
            while True:
                pos = buf.find(anchor, start)
                if pos < 0:
                    break
                candidates.append({"host_anchor": hex(lo + pos), "mapping": fields[0],
                                   "possible_image_base": hex(lo + pos - 0x37a88)})
                start = pos + len(anchor)
    finally:
        os.close(fd)
    return candidates


def snapshot_game(pid, label, output):
    """Resolve DOSBox RAM by the game anchor + independent BIOS checks.

    This address map is specific to the supplied v1.03 image; exports expose raw
    words as well as the provisional logical projection so interpretation can be
    audited. No guest memory is written.
    """
    anchor=b"BattleTech: The Crescent Hawk's Inception"
    anchor_offset=0x37A88
    os.kill(pid,signal.SIGSTOP)
    fd=os.open(f"/proc/{pid}/mem",os.O_RDONLY)
    try:
        ram=None
        load=None
        for line in Path(f"/proc/{pid}/maps").read_text().splitlines():
            fields=line.split()
            lo,hi=(int(v,16) for v in fields[0].split("-"))
            if "rw" not in fields[1] or hi-lo>64*1024*1024:continue
            try:buf=os.pread(fd,hi-lo,lo)
            except OSError:continue
            pos=buf.find(anchor)
            if pos<0:continue
            image=lo+pos-anchor_offset
            for image_load in range(0x1000,0x10000,16):
                base=image-image_load
                if base<lo or base+0x100000>hi:continue
                i=base-lo
                if (buf[i+0x400:i+0x404]==b'\xf8\x03\xf8\x02' and
                    buf[i+0x413:i+0x415]==b'\x80\x02' and
                    buf[i+0x44a:i+0x44c] in (b'\x28\0',b'\x50\0')):
                    candidate=buf[i:i+0x100000]
                    if candidate[image_load:image_load+3]!=b'\x55\x8b\xec':continue
                    ram=candidate;load=image_load//16
                    break
            if ram is not None:break
        if ram is None:raise RuntimeError("Could not resolve guest RAM; no guessed snapshot exported")
        def u16(addr):return struct.unpack_from("<H",ram,addr)[0]
        # Reko's common DS is 3EDB with image base 0800: relative 36DB.
        # 246C (relative 1C6C) is the separate map/graphics buffer, not the
        # selector table. Runtime pointers resolve that buffer explicitly.
        ds=(load+0x36db)*16
        state=u16(ds+0x538a)*16
        ui=u16(ds+0x53a0)*16
        xp=u16(ds+0x538c)*16+0xa44b
        yp=u16(ds+0x538e)*16+0xa44d
        raw_x,raw_y=u16(xp),u16(yp)
        row={"label":label,"load_segment":hex(load),"data_segment":hex(ds//16),
            "state_segment":hex(state//16),"ui_segment":hex(ui//16),
            "cursor_raw":[raw_x,raw_y],"cursor_tile":[(raw_x&127)//2,(raw_y&127)//2],
            "gate":u16(ds+0x150),"suspend":u16(ds+0x14a),
            "credits":struct.unpack_from("<i",ram,state+0xd370)[0],
            "world_active":ram[state+0xd310],"scene_values":list(ram[state+0xd347:state+0xd34f]),
            "adapter_mode":u16(ui+0x4fba),"narrow_panel":u16(ui+0x4fbc),
            "party_x_raw":[u16(state+0x400c+2*i) for i in range(4)],
            "party_y_raw":[u16(state+0x403e+2*i) for i in range(4)]}
        script_segment=u16(ds+0x54b4)
        citadel=(WORK/"dos/CITADEL.BLD").read_bytes()[2:]
        decoded=bytes(((value+41)&255)^233 for value in citadel)
        script_offset=ram.find(decoded)
        row["citadel_payload_guest_offset"]=hex(script_offset) if script_offset>=0 else None
        row["citadel_payload_sha256"]=hashlib.sha256(decoded).hexdigest() if script_offset>=0 else None
        row["script_buffer_segment"]=hex(script_segment)
        row["building_index"]=u16(u16(ds+0x5480)*16+0x3ff8)
        row["story_state_bytes"]=list(ram[state+0xd30c:state+0xd36a])
        payload=(WORK/"dos/MAP1.MTP").read_bytes()[541:]
        map_offset=ram.find(payload)
        row["map1_payload_present"]=map_offset>=0
        row["map1_payload_guest_offset"]=hex(map_offset) if map_offset>=0 else None
        (output/(label+"-ram.bin")).write_bytes(ram)
        (output/(label+"-state.json")).write_text(json.dumps(row,indent=2)+"\n")
        print(json.dumps(row),flush=True)
    finally:
        os.close(fd)
        os.kill(pid,signal.SIGCONT)


def controlled_talk_context(pid, output):
    """Explicit differential-test precondition; this is not an NPC arrival trace.

    Only the eight NPC occupancy pairs and D33A result byte are changed in the
    running working copy. Executable, resources and saved files stay untouched.
    Snapshot resolution remains read-only; edits have a separate audit record.
    """
    snapshot_game(pid, "before-controlled-context", output)
    row = json.loads((output / "before-controlled-context-state.json").read_text())
    ram = (output / "before-controlled-context-ram.bin").read_bytes()
    if row["building_index"] != 1 or row["citadel_payload_guest_offset"] is None or row["world_active"]:
        raise RuntimeError("Talk precondition requires the initial local Citadel menu")
    state = int(row["state_segment"], 16) * 16
    if ram[state + 0xd339] or any(ram[state + 0xd399 + 26*i] for i in range(8)):
        raise RuntimeError("Refusing to replace an active NPC context")
    context = json.loads((ROOT / "tests/fixtures/talk-context.json").read_text())
    pairs = context.get("npc_pairs"); result = context.get("talk_result")
    if not isinstance(pairs,list) or len(pairs) != 8 or not all(isinstance(pair,list) and len(pair) == 2 and
        all(type(v) is int and 0 <= v <= 255 for v in pair) for pair in pairs) or \
        type(result) is not int or not 0 <= result <= 255:
        raise ValueError("Invalid bounded Talk precondition")
    anchor = b"BattleTech: The Crescent Hawk's Inception"
    guest_anchor = int(row["load_segment"], 16)*16 + 0x37a88
    os.kill(pid, signal.SIGSTOP)
    fd = os.open(f"/proc/{pid}/mem", os.O_RDWR)
    try:
        base = None
        for line in Path(f"/proc/{pid}/maps").read_text().splitlines():
            fields = line.split(); lo, hi = (int(v,16) for v in fields[0].split("-"))
            if "rw" not in fields[1] or hi-lo > 64*1024*1024: continue
            try: data = os.pread(fd, hi-lo, lo)
            except OSError: continue
            at = data.find(anchor)
            candidate = lo + at - guest_anchor
            if at >= 0 and candidate >= lo and candidate+len(ram) <= hi and \
                os.pread(fd, 16, candidate+0x400) == ram[0x400:0x410]:
                base = candidate; break
        if base is None: raise RuntimeError("Cannot resolve controlled-precondition RAM")
        changes = [(state+0xd398+26*i, bytes(pair)) for i,pair in enumerate(context["npc_pairs"])]
        changes.append((state+0xd33a, bytes([context["talk_result"]])))
        audit = []
        for addr, value in changes:
            before = os.pread(fd, len(value), base+addr)
            if before != ram[addr:addr+len(value)]: raise RuntimeError("Context changed after precondition snapshot")
            if os.pwrite(fd, value, base+addr) != len(value): raise RuntimeError("Short precondition write")
            audit.append({"guest_offset":hex(addr),"before":list(before),"after":list(value)})
        (output/"controlled-context.json").write_text(json.dumps({"kind":"controlled-precondition",
            "fixture":"tests/fixtures/talk-context.json", "changes":audit},indent=2)+"\n")
    finally:
        os.close(fd); os.kill(pid, signal.SIGCONT)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--script",type=Path,required=True)
    args=parser.parse_args()
    commands=json.loads(args.script.read_text())
    if not isinstance(commands,list) or not 1<=len(commands)<=500:
        raise ValueError("Script must contain 1..500 command lists")
    for parts in commands:
        if not isinstance(parts,list) or not parts or not all(isinstance(p,str) for p in parts):
            raise ValueError("Each command must be a nonempty list of strings")
        if parts[0] in ("shot","screen","snapshot","dump"):
            if len(parts)<2 or not parts[1].replace("-","").replace("_","").isalnum():
                raise ValueError("Capture labels must use letters, digits, hyphens or underscores")
    manifest=json.loads((ROOT/"docs/original-manifest.json").read_text())
    for row in manifest["files"]:
        name=Path(row["path"]).name
        if name.startswith("GAME"):continue # Working saves may be changed by DOS.
        source=WORK/"dos"/name
        if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest()!=row["sha256"]:
            raise RuntimeError(f"Working oracle resource differs from audited original: {name}")
    output=WORK/"reference-runs"/str(time.time_ns())
    output.mkdir(parents=True)
    (WORK/"reference-latest.txt").write_text(str(output)+"\n")
    print("RUN",output,flush=True)
    read_fd, write_fd = os.pipe()
    xvfb_log = (output / "xvfb.log").open("w")
    xvfb = subprocess.Popen([str(ROOT / "local-deps/xvfb/usr/bin/Xvfb"),
        "-displayfd",str(write_fd),"-screen","0","800x600x24","-nolisten","tcp"],
        pass_fds=(write_fd,),stdout=xvfb_log,stderr=subprocess.STDOUT)
    os.close(write_fd)
    if not select.select([read_fd],[],[],10)[0]:
        xvfb.terminate()
        raise RuntimeError("Private virtual display did not start")
    number=os.read(read_fd,32).decode().strip()
    os.close(read_fd)
    os.environ["DISPLAY"]=":"+number
    os.environ["BTECH_REFERENCE_VIRTUAL"]="1"
    capture = output / "captures"
    capture.mkdir(parents=True, exist_ok=True)
    config = output / "dosbox.conf"
    config.write_text(f"""[sdl]
fullscreen=false
output=surface
windowresolution=original
[dosbox]
machine=svga_s3
memsize=16
captures={capture}
[render]
aspect=false
scaler=normal2x
[cpu]
core=normal
cycles=fixed 10000
[mixer]
nosound=true
[autoexec]
mount c \"{WORK / 'dos'}\"
c:
btech.exe
""")
    env = dict(os.environ)
    env["LD_LIBRARY_PATH"] = str(ROOT / "local-deps/dosbox/usr/lib/x86_64-linux-gnu")
    env["SDL_AUDIODRIVER"] = "dummy"
    log = (output / "dosbox.log").open("w")
    process = subprocess.Popen([str(ROOT / "local-deps/dosbox/usr/bin/dosbox"), "-conf", str(config)],
                               env=env, cwd=WORK, stdout=log, stderr=subprocess.STDOUT)
    session_log = (output / "inputs.jsonl").open("w")
    try:
        keys = WindowKeys()
        for _ in range(100):
            if process.poll() is not None:
                raise RuntimeError((output / "dosbox.log").read_text())
            try:
                window = keys.find_dosbox()
                break
            except RuntimeError:
                time.sleep(0.1)
        else:
            raise RuntimeError("DOSBox window not found")
        (WORK / "reference-session.json").write_text(json.dumps({"pid": process.pid, "window": window,
            "harness_pid":os.getpid(),"xvfb_pid":xvfb.pid,"display":os.environ["DISPLAY"]}))
        print(f"READY private_display={os.environ['DISPLAY']} pid={process.pid} window={window}", flush=True)
        for parts in commands:
            if not parts:
                continue
            session_log.write(json.dumps({"time": time.time(), "command": parts}) + "\n")
            session_log.flush()
            try:
                command = parts[0]
                if command == "quit":
                    break
                if command == "key":
                    for key in parts[1:]:
                        keys.key(window, key)
                        time.sleep(0.18)
                elif command == "screen":
                    from PIL import ImageGrab
                    path=capture/(parts[1]+".png")
                    if path.exists():raise ValueError("Capture label already exists")
                    ImageGrab.grab(xdisplay=os.environ["DISPLAY"]).save(path)
                    print(path,flush=True)
                elif command == "wait":
                    delay=float(parts[1])
                    if not 0<=delay<=10:raise ValueError("Wait must be 0..10 seconds")
                    time.sleep(delay)
                elif command == "shot":
                    before = set(capture.glob("*.png"))
                    keys.key(window, "Ctrl+F5")
                    for _ in range(40):
                        new = set(capture.glob("*.png")) - before
                        if new:
                            break
                        time.sleep(0.05)
                    if not new:
                        raise RuntimeError("DOSBox produced no capture")
                    p = sorted(new)[-1]
                    target = capture / (parts[1] + ".png")
                    if target.exists():
                        raise ValueError("Capture label already exists")
                    p.rename(target)
                    print(target, flush=True)
                elif command == "scan":
                    print(json.dumps(memory_candidates(process.pid)), flush=True)
                elif command == "snapshot":
                    snapshot_game(process.pid,parts[1],output)
                elif command == "controlled-talk-context":
                    controlled_talk_context(process.pid, output)
                elif command == "dump":
                    address = int(parts[2], 0)
                    length = int(parts[3], 0)
                    if not 0 < length <= 0x110000:
                        raise ValueError("Dump length outside guest RAM limit")
                    fd = os.open(f"/proc/{process.pid}/mem", os.O_RDONLY)
                    try:
                        data = os.pread(fd, length, address)
                    finally:
                        os.close(fd)
                    dest = output / (parts[1] + ".bin")
                    dest.write_bytes(data)
                    print(f"Read {len(data)} bytes to {dest}", flush=True)
                else:
                    raise ValueError("Commands: key, screen, shot, wait, scan, snapshot, dump, controlled-talk-context, quit")
                print("OK", flush=True)
            except Exception as e:
                print(f"ERROR: {e}", flush=True)
                raise
    except EOFError:
        pass
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        log.close()
        session_log.close()
        xvfb.terminate()
        xvfb.wait(timeout=5)
        xvfb_log.close()


if __name__ == "__main__":
    if len(sys.argv)==2 and sys.argv[1]=="--stop":
        session=json.loads((WORK/"reference-session.json").read_text())
        # Stop only processes recorded by this harness. Verify command lines to
        # avoid acting on a reused PID.
        targets=[(session.get("pid"),"dosbox"),(session.get("xvfb_pid"),"Xvfb")]
        if not session.get("harness_pid"):
            try:
                p=Path(f"/proc/{session['pid']}/stat").read_text().split(') ')[1].split()[1]
                session["harness_pid"]=int(p)
            except FileNotFoundError:pass
        targets.append((session.get("harness_pid"),"reference_session.py"))
        for pid,expected in targets:
            if not pid:continue
            try:
                cmd=Path(f"/proc/{pid}/cmdline").read_bytes().decode(errors="replace")
                if expected not in cmd:raise RuntimeError("Refusing to stop an unrelated PID")
                os.kill(pid,signal.SIGTERM)
            except FileNotFoundError:pass
        print("Stopped recorded reference processes")
    elif len(sys.argv) >= 2 and sys.argv[1] == "--screen":
        from PIL import ImageGrab
        keys = WindowKeys()
        window = keys.find_dosbox()
        x = keys.x
        x.XGetGeometry.argtypes = [c.c_void_p, c.c_ulong, c.POINTER(c.c_ulong),
            c.POINTER(c.c_int), c.POINTER(c.c_int), c.POINTER(c.c_uint),
            c.POINTER(c.c_uint), c.POINTER(c.c_uint), c.POINTER(c.c_uint)]
        x.XTranslateCoordinates.argtypes = [c.c_void_p,c.c_ulong,c.c_ulong,c.c_int,c.c_int,
            c.POINTER(c.c_int),c.POINTER(c.c_int),c.POINTER(c.c_ulong)]
        root, child = c.c_ulong(), c.c_ulong()
        gx, gy, sx, sy = c.c_int(), c.c_int(), c.c_int(), c.c_int()
        w, h, border, depth = c.c_uint(), c.c_uint(), c.c_uint(), c.c_uint()
        x.XGetGeometry(keys.display,window,c.byref(root),c.byref(gx),c.byref(gy),c.byref(w),c.byref(h),c.byref(border),c.byref(depth))
        x.XTranslateCoordinates(keys.display,window,keys.root,0,0,c.byref(sx),c.byref(sy),c.byref(child))
        box=(sx.value,sy.value,sx.value+w.value,sy.value+h.value)
        ImageGrab.grab(bbox=box).save(WORK / (sys.argv[2] if len(sys.argv)>2 else "reference-window.png"))
        print("DOSBox window",window,"box",box)
    elif len(sys.argv) >= 3 and sys.argv[1] == "--key":
        keys = WindowKeys()
        window = keys.find_dosbox()
        for name in sys.argv[2:]:
            keys.key(window,name)
        print("Delivered",sys.argv[2:],"to",window)
    else:
        main()
