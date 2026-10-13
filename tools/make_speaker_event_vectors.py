#!/usr/bin/env python3
"""Record ordered original tone/noise periods, with explicit nominal XT timing."""
import json
import struct
from combat_oracle import OriginalCombat, ROOT, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_DX
from make_party_vectors import SNAP
from make_speaker_timing_vectors import observe
from prepare_talk import EXE_SHA


def pit(cycles):
    return (cycles*1193182+4000000)//8000000


def main():
    m=OriginalCombat(snapshot=SNAP);timer=OriginalCombat(snapshot=SNAP)
    events=[];pending=[];cache={};rows=[];details=[]
    def event(cpu,address,size,data):
        relative=address-16*m.load
        if relative in (0x18105,0x18378):
            sweep=relative==0x18378
            divisor=m.word(m.state+(0x3ff6 if sweep else 0x3984))
            duration=m.word(m.state+(0x3246 if sweep else 0xe48c))
            # Sweeps program PIT divisor zero as 65536; only the separate
            # sustained-tone helper treats its zero argument as a rest.
            if sweep or divisor:events.append((1,divisor,0,('delay',duration,1 if sweep else 50)))
        else:
            # Observe the actual DX/mask/base at the LOOP helper, before CX
            # is consumed. Both calibration calls must see the same period.
            loops=(cpu.reg_read(UC_X86_REG_DX)&m.word(m.buffer+0x254))|m.word(m.buffer+0x256)
            pending.append(loops or 65536)
            if len(pending)==2:
                if pending[0]!=pending[1]:raise RuntimeError('Noise calibration changed period')
                events.append((2,0,int(bool(m.speaker&2)),('noise',*pending)));pending.clear()
    for address in (0x18105,0x18378,0x188b0):
        m.cpu.hook_add(UC_HOOK_CODE,event,None,16*m.load+address,16*m.load+address)
    for program in range(1,19):
        m.reset();m.speaker=0;m.word(m.ds+0x5006,2);events.clear();pending.clear()
        m.call(0x17c5,2,program,limit=40000000)
        if pending:raise RuntimeError('Incomplete original noise period')
        h=14695981039346656037;total=0;minimum=None;maximum=0
        for kind,divisor,level,delay in events:
            if delay[0]=='delay':
                key=delay[1:]
                if key not in cache:cache[key]=observe(timer,*key)[0]
                clocks=cache[key]
            else:
                # Same published nominal caller/LOOP model as sounds.c;
                # only the observed loop counts and order are primary facts.
                clocks=pit(641+sum(566+17*loops for loops in delay[1:]))
            for value in struct.pack('<BHB I',kind,divisor,level,clocks):
                h=((h^value)*1099511628211)&((1<<64)-1)
            total+=clocks;minimum=clocks if minimum is None else min(minimum,clocks);maximum=max(maximum,clocks)
        rows.append(f'E {program} {len(events)} {h:016x} {total}')
        details.append(dict(program=program,events=len(events),active_pit_clocks=total,
            nominal_active_seconds=round(total/1193182,6),minimum_period=minimum,maximum_period=maximum))
        print(rows[-1],flush=True)
    (ROOT/'tests/fixtures/speaker-events-primary.txt').write_text('\n'.join(rows)+'\n')
    (ROOT/'tests/fixtures/speaker-events-primary.json').write_text(json.dumps(dict(
        executable_sha256=EXE_SHA,snapshot=str(SNAP),programs=details,
        boundaries=['18105/18378 tone delay entry','187F:00A9 actual noise LOOP inputs'],
        comparison='Ordered tone divisors, speaker noise levels and nominal periods for all eighteen isolated programs.',
        timing='Calibration 2; nominal 8 MHz 8088. Tone loops are executed by the original timing oracle; noise LOOP/caller clocks use the existing documented model.',
        limits='Silence/call overhead outside these intervals, prefetch, interrupts and physical speaker filtering are not measured. These are not hardware recordings.',
        no_instruction_patches=True),indent=2)+'\n')


if __name__=='__main__':main()
