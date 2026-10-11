#!/usr/bin/env python3
"""Input-only fourth/fifth missions and cadet Mechit-Lube visit, no state edits."""
import argparse
import json
import struct
import tempfile
from collections import deque
from pathlib import Path
from verify_m2j import run
from verify_m2 import check
from exepack import unpack
from prepare_talk import DS

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'tests/fixtures'
PATH=BASE/'ordinary-training-combat.actions'
FACTS=BASE/'ordinary-training-combat.json'

def generate(binary,kick=False):
    image,_=unpack((ROOT/'Original DOS/BTECH.EXE').read_bytes())
    answers=struct.unpack_from('<10H',image,DS+0x28ec)
    raw=(ROOT/'Original DOS/MAP1.MTP').read_bytes();terrain=raw[541:]
    entrances=[(raw[389+2*i]&127,raw[421+2*i]&127) for i in range(8)]
    def tile(x,y):
        return 255 if not 0<=x<64 or not 0<=y<64 else terrain[(y&0x78)*64+(y&7)*8+(x&0x78)*8+(x&7)]
    source=BASE/('ordinary-rubble-story.actions' if kick else 'ordinary-combat.actions')
    actions=source.read_text().splitlines();notes=[]
    with tempfile.TemporaryDirectory(prefix='training-combat-',dir=ROOT/'work') as directory:
        tmp=Path(directory);slot=tmp/'state.btp';leg=tmp/'leg.actions'
        state=json.loads(run(binary,'--replay',source,'--save',slot))
        def advance(keys):
            nonlocal state
            leg.write_text('\n'.join(keys)+'\n')
            try:state=json.loads(run(binary,'--load',slot,'--replay',leg,'--save',slot))
            except Exception:
                (ROOT/'work/training-combat-failed.btp').write_bytes(slot.read_bytes());raise
            actions.extend(keys)
            check(state['mode']!='script-error','Unsupported ordinary action at '+str(len(actions)))
        def note(label):
            notes.append({'label':label,'tick':len(actions),'mode':state['mode'],'combat_phase':state['combat']['phase']})
        def route(targets,mech=False):
            start=(state['x_half'],state['y_half']);parents={start:None};queue=deque([start]);goal=None
            for _ in range(20000):
                if not queue:break
                p=queue.popleft()
                if p in targets:goal=p;break
                for action,dx,dy in [('up',0,-1),('right',1,0),('down',0,1),('left',-1,0)]:
                    q=p[0]+dx,p[1]+dy;x,y=q
                    if q in parents or not 0<=x<126 or not 2<=y<128:continue
                    blocked=tile(x//2,(y-2)//2)>=85 or tile(x//2+1,(y-2)//2)>=85 if mech else tile((x+1)//2,y//2)>=85
                    if blocked or (not mech and q in entrances and q not in targets):continue
                    parents[q]=(p,action);queue.append(q)
            check(goal is not None,'No input-only walking route');keys=[]
            while parents[goal] is not None:goal,action=parents[goal];keys.append(action)
            advance(list(reversed(keys)))
        def building(slot):
            route({entrances[slot]});check(state['mode']=='entry-confirm','Missing entrance');advance(['accept'])
        def quiz():
            check(state['mode']=='training-quiz','No ordinary quiz');advance(['accept'])
            for _ in range(3):
                advance(['down']*((answers[state['quiz']['point']]-state['quiz']['selected'])%20)+['accept'])
        def command(n):
            check(state['combat']['phase']==4,'Expected command menu: '+str({k:state['combat'][k] for k in ['phase','goal','round','won','lost']}))
            advance(['down']*((n-state['combat']['selected'])%10)+['accept'])
            if state['combat']['phase']==12:
                note('movement-replace');advance(['accept'])
        def waypoint(x,y,mode,append=False):
            # Replacing a route uses the original movement-mode confirmation;
            # selecting the same mode normally appends another waypoint.
            if not append and state['combat']['goal'][0] and state['combat']['goal'][1]==mode:
                command(0 if mode else 1);advance(['cancel'])
            command(mode);u=state['combat']['units'][0]
            advance((['right']*max(0,x-u['x'])+['left']*max(0,u['x']-x))+
                (['down']*max(0,y-u['y'])+['up']*max(0,u['y']-y)))
            note('movement-'+str(mode));advance(['accept'])
        def fight():
            command(9);advance(['idle']);note('resolving');advance(['idle']*35)
            check(state['combat']['phase'] in [0,4],'Turn did not resolve')
        def arm():
            command(3)
            # The duel uses two medium lasers and the machine guns so the
            # Chameleon can sustain fire without overheating.
            while state['combat']['phase']==6:
                if state['mission']['assignment']>=3 and state['combat']['weapon'] not in [0,4,7,8,9]:
                    advance(['down']);continue
                advance(['accept'])
                if state['combat']['phase']==7:advance(['accept'])
        for assignment in ([2] if kick else [3,4]):
            if assignment>2:
                advance(['idle']*(state['story_flags'][20]*4));building(0);quiz()
                advance(['accept','accept'])
            check(state['menu_id']==7,'Missing loan menu')
            advance(['down']*((2-state['menu_selected'])%3)+['accept']+['idle']*90)
            note('kick-start' if kick else 'robots-start' if assignment==3 else 'duel-start')
            check(state['mission']['assignment']==assignment,'Wrong assignment')
            advance(['accept','accept','accept'])
            if not kick:arm()
            command(4);note('kick-target');advance(['accept']);note('kick-queued')
            if kick:
                for x,y,mode,turns in [(72,77,1,3),(84,85,0,5),(96,93,0,9),(111,89,0,8)]:
                    waypoint(x,y,mode)
                    for _ in range(turns):
                        if state['combat']['won']:break
                        fight()
            elif assignment==3:
                for x,y,mode,turns in [(72,77,1,3),(84,85,2,4),(96,93,0,4)]:
                    waypoint(x,y,mode)
                    if x==72:
                        waypoint(76,77,1,append=True);note('queued-route')
                    for _ in range(turns):
                        if state['combat']['won']:break
                        fight()
            else:
                # Navigate around the training building before approaching the
                # duel. The original steering routine is local, not a BFS.
                for x,y,mode,turns in [(72,77,1,3),(84,85,2,4),(96,93,0,4)]:
                    waypoint(x,y,mode)
                    for _ in range(turns):
                        if state['combat']['won'] or state['combat']['lost']:break
                        fight()
            for turn in range(200):
                if state['combat']['won'] or state['combat']['lost']:break
                c=state['combat'];target=c['units'][c['target']]
                if target['record'][0]==255:
                    command(3);advance(['accept','down','accept','up','accept'])
                    while state['combat']['phase']==6:
                        advance(['accept'])
                        if state['combat']['phase']==7:advance(['accept'])
                    arm()
                if turn%4==0:
                    c=state['combat'];target=c['units'][c['target']];u=c['units'][0]
                    if abs(u['x']-target['x'])>8 or abs(u['y']-target['y'])>4:
                        waypoint(max(1,min(124,target['x']-3)),max(2,min(124,target['y'])),1 if assignment==3 else 0)
                fight()
            if state['combat']['won']!=1:
                (ROOT/'work/training-combat-failed.btp').write_bytes(slot.read_bytes())
                (ROOT/'work/training-combat-failed.json').write_text(json.dumps(state,indent=2)+'\n')
                (ROOT/'work/training-combat-failed.actions').write_text('\n'.join(actions)+'\n')
            check(state['combat']['won']==1,'Ordinary assignment lost or timed out: '+str(assignment))
            note('kick-victory' if kick else 'robots-victory' if assignment==3 else 'duel-victory')
            route({(x,y) for x in range(61) for y in range(73,80)},True);advance(['idle'])
            note('kick-report' if kick else 'robots-report' if assignment==3 else 'duel-report')
            while state['mode']=='building':advance(['accept'])
            check(state['story_flags'][:2]==[assignment+1,1] and state['allowance_cap']==[500,1000,2000][assignment-2],
                'Wrong training reward: '+str([assignment,state['story_flags'][:2],state['allowance_cap']]))
            note('kick-exit' if kick else 'robots-exit' if assignment==3 else 'duel-exit')
        if kick:
            PATH.write_text('\n'.join(actions)+'\n')
            FACTS.write_text(json.dumps({'kind':'ordinary-native-playability','state_edits':False,
                'scope':'Native input-only kick victory; separate from original instruction rules','checkpoints':notes},indent=2)+'\n')
            print(f'Generated {len(actions)} ordinary inputs through kick victory');return
        check(state['recruitment']==1 and state['npc_pairs'][0]==[112,255],'Rick was not invited')
        # The higher allowance funds the original 500-C-bill course naturally.
        for _ in range(200):
            if state['credits']>=500:break
            advance(['idle']*256)
        check(state['credits']>=500,'Allowance did not fund apprenticeship')
        building(5);note('mechit-menu')
        advance(['down']*((0-state['menu_selected'])%6)+['accept']);note('mechit-confirm')
        before=state['credits'];advance(['accept']);note('mechit-trained')
        check(state['credits']==before-500 and state['combat']['technician']==state['combat']['apprentice']==1,'Wrong apprenticeship')
        advance(['accept']);advance(['accept']);note('mechit-repeat')
        check(state['credits']==before-500,'Repeated course charged twice');advance(['accept'])
        for choice,label in [(1,'speed-shop'),(2,'no-mech-repair'),(3,'no-mech-ammo'),(4,'mechit-talk')]:
            advance(['down']*((choice-state['menu_selected'])%6)+['accept'])
            while state['script_status'] in [2,5]:
                if state['talk_phase']==2:advance(['down']*((state['talk_count']-state['talk_selected'])%(state['talk_count']+1))+['accept'])
                else:advance(['accept'])
            note(label)
        advance(['down']*((5-state['menu_selected'])%6)+['accept'])
        while state['mode']=='building':advance(['accept'])
        note('mechit-exit')
        check(state['mode']=='local-exploration','Did not exit Mechit-Lube')
    PATH.write_text('\n'.join(actions)+'\n')
    FACTS.write_text(json.dumps({'kind':'ordinary-native-playability','state_edits':False,
        'scope':'Native input-only campaign route; original rules have separate instruction comparisons','checkpoints':notes},indent=2)+'\n')
    print(f'Generated {len(actions)} ordinary inputs through fourth/fifth victory and Mechit-Lube')

def verify(binary,kick=False):
    facts=json.loads(FACTS.read_text());actions=PATH.read_text().splitlines()
    rows=[json.loads(line) for line in run(binary,'--replay',PATH,'--trace').splitlines()];end=rows[-1]
    for point in facts['checkpoints']:
        s=rows[point['tick']];check(s['mode']==point['mode'] and s['combat']['phase']==point['combat_phase'],point['label']+' differs')
    check(end['story_flags'][:2]==([3,1] if kick else [5,1]) and end['allowance_cap']==(500 if kick else 2000) and
        end['combat']['technician']==(0 if kick else 1),'Completion differs')
    if kick:
        check(any(s['combat']['fired']&2048 for s in rows),'Kick never fired')
        check(all(all(w==255 for w in s['combat']['orders']) for s in rows if s['combat']['phase']),'Kick replay used guns')
    points=[p for p in facts['checkpoints'] if p['label']!='resolving']+[p for p in facts['checkpoints'] if p['label']=='resolving'][::10]
    with tempfile.TemporaryDirectory(prefix='training-combat-restart-',dir=ROOT/'work') as directory:
        tmp=Path(directory);prefix=tmp/'prefix.actions';tail=tmp/'tail.actions';slot=tmp/'state.btp'
        for p in points:
            tick=p['tick'];prefix.write_text('\n'.join(actions[:tick])+'\n');tail.write_text('\n'.join(actions[tick:])+'\n')
            run(binary,'--replay',prefix,'--save',slot)
            resumed=json.loads(run(binary,'--load',slot,'--replay',tail)) if tick<len(actions) else json.loads(run(binary,'--load',slot))
            check(resumed==end,'Fresh-process continuation differs at '+p['label'])
    print(f'PASS: {"ordinary kick victory" if kick else "fourth/fifth missions, walk/run/jump, Mechit-Lube"}; {len(actions)} inputs, {len(points)} save continuations')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--binary',type=Path,default=ROOT/'build/btech-headless');p.add_argument('--generate',action='store_true');p.add_argument('--kick',action='store_true');a=p.parse_args()
    if a.kick:PATH=BASE/'ordinary-kick.actions';FACTS=BASE/'ordinary-kick.json'
    if a.generate:generate(a.binary.resolve(),a.kick)
    verify(a.binary.resolve(),a.kick)
