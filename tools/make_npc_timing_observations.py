#!/usr/bin/env python3
"""Summarize a fresh, read-only DOSBox idle trace and export numeric frames."""
import argparse,hashlib,json,statistics
from pathlib import Path
from combat_oracle import ROOT
from prepare_talk import EXE_SHA,IMAGE_SHA


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path);args=p.parse_args()
    source=args.run/'npc-idle-timing-frames.json';data=json.loads(source.read_text())
    frames=data['frames'];times=data['sample_seconds'];assert len(frames)==len(times)>=100
    inputs=[json.loads(line)['command'] for line in (args.run/'inputs.jsonl').read_text().splitlines()]
    assert not any(c[0].startswith('controlled-') for c in inputs)
    periods=[];rows=[]
    for i,s in enumerate(frames):
        if i:
            previous=frames[i-1]
            assert (previous['loop_timer']-s['loop_timer'])%256==1
            assert s['phase']==(previous['phase']+1)%3 and s['cursor']==previous['cursor']
            periods.append(times[i]-times[i-1]);assert periods[-1]>0
        values=[s['phase'],s['loop_timer'],*s['rng'],*s['search'],*s['cursor']]
        for n in s['npcs']:values.extend([*n['position'],*n['destination'],n['direction'],*n['pair']])
        assert len(values)==65
        rows.append(','.join(map(str,values)))
    csv='\n'.join(rows)+'\n';(ROOT/'tests/fixtures/npc-idle-timing.csv').write_text(csv)
    (ROOT/'tests/fixtures/npc-idle-timing.json').write_text(json.dumps(dict(
        executable_sha256=EXE_SHA,image_sha256=IMAGE_SHA,run=args.run.name,
        samples=len(frames),complete_steps=len(periods),phase_cycle=3,
        observed_seconds=dict(min=min(periods),median=statistics.median(periods),mean=statistics.mean(periods),max=max(periods)),
        nominal_native_seconds=4*.032,original_idle_retraces=11,
        original_routines='0000:044A resets countdown to ten; 01F4 waits one retrace then decrements until negative; phase advances once per full loop.',
        input_sha256=hashlib.sha256(json.dumps(inputs).encode()).hexdigest(),csv_sha256=hashlib.sha256(csv.encode()).hexdigest(),
        limits='25-second fresh MAP1 idle sample, DOSBox normal core fixed 10000 cycles, 15 ms two-poll observer. Host/emulator timing is not an 8 MHz XT measurement. Native cadence remains approximate.'),indent=2)+'\n')
    print(f'NPC timing: {len(periods)} consecutive frames, median {1000*statistics.median(periods):.3f} ms; native nominal 128 ms')


if __name__=='__main__':main()
