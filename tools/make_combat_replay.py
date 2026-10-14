#!/usr/bin/env python3
"""Ordinary native third-assignment playthrough; no state or RNG edits."""
import argparse
import json
import tempfile
from collections import deque
from pathlib import Path
from verify_m2j import run
from verify_m2 import check

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'tests/fixtures'
PATH=BASE/'ordinary-combat.actions'
FACTS=BASE/'ordinary-combat.json'

def generate(binary):
    actions=(BASE/'ordinary-rubble-story.actions').read_text().splitlines();notes=[]
    with tempfile.TemporaryDirectory(prefix='combat-play-',dir=ROOT/'work') as directory:
        tmp=Path(directory);slot=tmp/'state.btp';leg=tmp/'leg.actions'
        state=json.loads(run(binary,'--replay',BASE/'ordinary-rubble-story.actions','--save',slot))
        def advance(keys):
            nonlocal state
            leg.write_text('\n'.join(keys)+'\n');state=json.loads(run(binary,'--load',slot,'--replay',leg,'--save',slot));actions.extend(keys)
        def note(label):
            notes.append({'label':label,'tick':len(actions),'mode':state['mode'],'combat_phase':state['combat']['phase']})
        def choose(n):advance(['down']*((n-state['combat']['selected'])%10)+['accept'])
        def waypoint(x,y):
            choose(0);u=state['combat']['units'][0]
            advance((['right']*(x-u['x']) if x>=u['x'] else ['left']*(u['x']-x))+
                    (['down']*(y-u['y']) if y>=u['y'] else ['up']*(u['y']-y)))
            if not any(r['label']=='route-preview' for r in notes):note('route-preview')
            advance(['accept'])
            if not any(r['label']=='route-confirmed' for r in notes):note('route-confirmed')
        def turns(count):
            for _ in range(count):
                if state['combat']['won']:return
                choose(9);advance(['idle'])
                if state['combat']['phase']==9:note('resolving')
                for _ in range(64):
                    if state['combat']['phase']!=9:break
                    advance(['idle']*8)
        advance(['down']*((3-state['menu_selected'])%3)+['accept'])
        for _ in range(128):
            if not state['animation']['active']:break
            advance(['idle'])
        check(not state['animation']['active'],'Startup did not complete')
        note('computer');advance(['accept']);note('messages');advance(['accept']);note('graphics');advance(['accept']);note('orders')
        waypoint(72,77);turns(4);waypoint(84,85);turns(5)
        choose(3);note('weapons');advance(['down','down','accept']);note('target');advance(['accept']);note('assigned');advance(['down','accept'])
        turns(2);waypoint(96,93);turns(9);waypoint(110,89);turns(80)
        check(state['combat']['won']==1,'Ordinary combat route did not win')
        note('victory')
        check(state['mission']['phase']==7,'Missing original return-to-base message');note('return-to-base');advance(['accept'])
        raw=(ROOT/'Original DOS/MAP1.MTP').read_bytes()[541:]
        def tile(x,y):return 255 if not 0<=x<64 or not 0<=y<64 else raw[(y&0x78)*64+(y&7)*8+(x&0x78)*8+(x&7)]
        start=(state['x_half'],state['y_half']);parents={start:None};queue=deque([start]);goal=None
        while queue:
            x,y=queue.popleft()
            if x<=60 and 73<=y<=79:goal=(x,y);break
            for action,dx,dy in (('up',0,-1),('right',1,0),('down',0,1),('left',-1,0)):
                q=x+dx,y+dy;qx,qy=q
                if q in parents or not 0<=qx<126 or not 2<=qy<128:continue
                if tile(qx//2,(qy-2)//2)>=85 or tile(qx//2+1,(qy-2)//2)>=85:continue
                parents[q]=((x,y),action);queue.append(q)
        check(goal is not None,'No instructor return route');keys=[]
        while parents[goal] is not None:goal,action=parents[goal];keys.append(action)
        advance(list(reversed(keys))+['idle']);note('report')
        check(state['story_flags'][:2]==[3,1] and state['allowance_cap']==500,'Third success result differs')
        advance(['accept']);note('exit');check(state['mode']=='local-exploration','Did not exit training')
    PATH.write_text('\n'.join(actions)+'\n');FACTS.write_text(json.dumps({'kind':'ordinary-native-playability','state_edits':False,
        'scope':'Native input-only success; separate from controlled original turn comparisons','checkpoints':notes},indent=2)+'\n')
    print(f'Generated {len(actions)} ordinary native actions through combat victory, report and exit')

def verify(binary):
    rows=[json.loads(line) for line in run(binary,'--replay',PATH,'--trace').splitlines()]
    facts=json.loads(FACTS.read_text())
    for point in facts['checkpoints']:
        s=rows[point['tick']];check(s['mode']==point['mode'] and s['combat']['phase']==point['combat_phase'],point['label']+' differs')
    origin=next(s['combat']['units'][1] for s in rows if s['combat']['phase'])
    for s in rows:
        c=s['combat']
        if c['phase'] and c['units'][1]['record'][0]!=255:
            enemy=c['units'][1]
            check([enemy['x'],enemy['y'],enemy['direction']]==[origin['x'],origin['y'],origin['direction']],
                  'Training shell moved or turned')
    effects=[s for s in rows if s['combat']['flash']]
    check(effects,'Combat graphics produced no firing indicator')
    end=rows[-1];check(end['story_flags'][:2]==[3,1] and end['allowance_cap']==500 and end['mode']=='local-exploration','Third completion differs')
    checks=[r for r in facts['checkpoints'] if r['label']!='resolving']
    checks += [r for r in facts['checkpoints'] if r['label']=='resolving'][::4]
    checks.append({'label':'firing-effect','tick':effects[0]['tick']})
    actions=PATH.read_text().splitlines()
    with tempfile.TemporaryDirectory(prefix='combat-restart-',dir=ROOT/'work') as directory:
        tmp=Path(directory)
        for index,point in enumerate(checks):
            tick=point['tick'];prefix=tmp/'prefix.actions';tail=tmp/'tail.actions';slot=tmp/'save.btp'
            prefix.write_text('\n'.join(actions[:tick])+'\n');tail.write_text('\n'.join(actions[tick:])+'\n')
            args=['--frame',ROOT/('work/combat-'+point['label']+'.ppm')] if point['label'] in (
                'weapons','orders','route-preview','route-confirmed','firing-effect') else []
            run(binary,'--replay',prefix,'--save',slot,*args)
            resumed=json.loads(run(binary,'--load',slot,'--replay',tail)) if tick<len(actions) else json.loads(run(binary,'--load',slot))
            check(resumed==end,'Fresh-process continuation differs at '+point['label'])
    print(f'PASS: ordinary combat victory/report/exit, {len(actions)} inputs, {len(checks)} fresh-process save continuations')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--binary',type=Path,default=ROOT/'build/btech-headless');p.add_argument('--generate',action='store_true');args=p.parse_args()
    if args.generate:generate(args.binary.resolve())
    verify(args.binary.resolve())
