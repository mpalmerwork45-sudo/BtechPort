#!/usr/bin/env python3
"""Check internal save files, process restart and continued logical state."""
import argparse
import binascii
import json
import struct
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def run(binary, *args, ok=True):
    result = subprocess.run([str(binary),*map(str,args)],cwd=ROOT,capture_output=True,text=True,timeout=20)
    if (result.returncode == 0) != ok:
        raise RuntimeError(result.stderr or "Unexpected save/load result")
    return json.loads(result.stdout) if result.returncode == 0 else result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary",type=Path,default=ROOT/"build/btech-headless")
    args = parser.parse_args(); binary = args.binary.resolve()
    work = ROOT/"work"; work.mkdir(exist_ok=True)
    cases = [("reference-bank",t,[]) for t in (0,330,332,334,335,336,339,344,414)]
    cases += [("reference-bank-rates",2242,[]),("citadel-katrina",8,[]),
        ("citadel-hall",9,[]),("citadel-arrival",2612,[]),("reference-shops",3059,[])]
    cases += [("reference-"+shop+"-talk",t,["--shop-talk-checkpoint",shop])
        for shop in ("armor","weapon") for t in (0,1,6,14)]
    course = json.loads((ROOT/"tests/fixtures/reference-class-funded.json").read_text())
    pauses = ("tuition-class-intro","tuition-class-menu","tuition-paid","tuition-completed",
        "tuition-cooldown","tuition-exit","tuition-clock24","tuition-next-menu","tuition-next-refusal")
    cases += [("reference-class-funded",r["tick"],[]) for r in course["checkpoints"] if r["label"] in pauses]
    with tempfile.TemporaryDirectory(prefix="m2g-",dir=work) as directory:
        tmp = Path(directory); slot = tmp/"slot.btp"; actions = tmp/"prefix.actions"
        tail = tmp/"tail.actions"; tail.write_text("idle\n"*1024)
        for stem,tick,initial in cases:
            lines = (ROOT/"tests/fixtures"/(stem+".actions")).read_text().splitlines()[:tick]
            actions.write_text("\n".join(lines)+( "\n" if lines else ""))
            before = run(binary,*initial,"--replay",actions,"--save",slot)
            restored = run(binary,"--load",slot)
            if before != restored: raise RuntimeError(f"Restart differs: {stem}/{tick}")
            resumed = run(binary,"--load",slot,"--replay",tail)
            whole = tmp/"whole.actions"; whole.write_text(actions.read_text()+tail.read_text())
            uninterrupted = run(binary,*initial,"--replay",whole)
            if resumed != uninterrupted: raise RuntimeError(f"Continuation differs: {stem}/{tick}")
        valid = slot.read_bytes(); damaged = tmp/"damaged.btp"
        mutations = [b"",valid[:-1],valid+b"x"]
        for offset in (0,4,8,12,16):
            data = bytearray(valid); data[offset] ^= 1; mutations.append(data)
        # An invalid state with an independently computed, valid CRC must fail.
        data = bytearray(valid); data[16+344] = 4
        struct.pack_into("<I",data,8,binascii.crc32(data[16:]))
        mutations.append(data)
        data = bytearray(valid); data[16+384] = 5
        struct.pack_into("<I",data,8,binascii.crc32(data[16:]))
        mutations.append(data)
        for data in mutations:
            damaged.write_bytes(data); run(binary,"--load",damaged,ok=False)
        # A real M2g envelope and BTP7 payload migrate without fictional skill
        # progress. Recompute its CRC independently of the C writer.
        baseline = run(binary,"--save",slot)
        old = bytearray(slot.read_bytes()[:16+384]); old[16:20] = b"BTP7"; old[20] = 7
        struct.pack_into("<I",old,4,384); struct.pack_into("<I",old,8,binascii.crc32(old[16:]))
        damaged.write_bytes(old)
        if run(binary,"--load",damaged) != baseline: raise RuntimeError("M2g save migration differs")
        slot.write_bytes(valid)
        run(binary,"--load",tmp/"missing.btp",ok=False)
        pending = Path(str(slot)+".tmp"); pending.write_bytes(b"KEEP")
        run(binary,"--save",slot,ok=False)
        if slot.read_bytes() != valid or pending.read_bytes() != b"KEEP":
            raise RuntimeError("Failed save modified the existing slot/pending file")
        destination = tmp/"directory"; destination.mkdir()
        run(binary,"--save",destination,ok=False)
        if Path(str(destination)+".tmp").exists(): raise RuntimeError("Failed rename left a pending save")
        run(binary,"--load",slot,"--conversation-checkpoint",ok=False)
    print(f"PASS: {len(cases)} process-restart states and 1024-tick continuations; M2g migration, damaged/missing files, semantic validation and failed-save preservation.")

if __name__ == "__main__": main()
