#!/usr/bin/env python3
"""Take the original jail-visitor fork into the impound yard, using inputs."""
import json
from collections import deque
from pathlib import Path
from make_later_campaign_replay import Later,ROOT

def route(s,x,y):
    data=(ROOT/f'Original DOS/MAP{s.state["map"]}.MTP').read_bytes();width,height=data[3],data[4];raw=data[541:]
    def tile(x,y):return raw[(y//8*(width//8)+x//8)*64+y%8*8+x%8]
    start=s.state['x_half'],s.state['y_half'];goal=x,y;queue=deque([start]);parent={start:None}
    while queue and goal not in parent:
        p=queue.popleft()
        for key,dx,dy in (('up',0,-1),('right',1,0),('down',0,1),('left',-1,0)):
            q=p[0]+dx,p[1]+dy
            if q in parent or not 0<=q[0]<2*width-1 or not 0<=q[1]<2*height or tile((q[0]+1)//2,q[1]//2)>=85:continue
            if q[1]==45 and q[0] in (20,24,28,32) and q!=goal:continue
            parent[q]=(p,key);queue.append(q)
    if goal not in parent:raise RuntimeError('No impound-yard walking route')
    keys=[];p=goal
    while parent[p]:p,key=parent[p];keys.append(key)
    s.advance(list(reversed(keys)))

def main():
    metadata=json.loads((ROOT/'tests/fixtures/ordinary-jail-visitor.json').read_text())
    tick=next(n['tick'] for n in metadata['checkpoints'] if n['label']=='jail-companion-joined')
    prefix=ROOT/'work/m4-audit/jail-theft-prefix.actions'
    prefix.write_text('\n'.join((ROOT/'tests/fixtures/ordinary-jail-visitor.actions').read_text().splitlines()[:tick])+'\n')
    s=Later(prefix);s.note('jail-theft-choice');s.advance(['accept'])
    for _ in range(256):
        if s.state['mode']=='impound-yard':break
        s.pause()
    else:raise RuntimeError('Impound yard did not begin')
    s.note('impound-yard-start')
    for i,x in enumerate((20,24,28)):
        route(s,x,45)
        if s.state['yard']['phase']!=1:raise RuntimeError('Boarding prompt unavailable')
        s.note(f'boarding-mech-{i+1}');s.advance(['accept','accept'])
        for _ in range(512):
            if not s.state['animation']['active'] and not s.state['audio']['effects']:break
            s.advance(['idle']*4)
        else:raise RuntimeError('Mech activation did not finish')
        s.note(f'mech-{i+1}-activation-result');s.advance(['accept'])
    for _ in range(256):
        if s.state['mode']=='actions':break
        s.pause()
    else:raise RuntimeError('Post-theft crew allocation unavailable')
    s.note('prison-crew-allocation')
    # Rex pilots the Locust, the freed agent pilots the Commando, and Jason
    # pilots the stolen Stinger. This also checks return with Jason in bay 3.
    for member,bay in ((1,0),(4,1),(0,2)):
        n=sum(p[0]!=255 for p in s.state['people'])
        s.advance(['down']*((member-s.state['actions_menu']['selected'])%(n+1))+['accept']+['down']*bay+['accept'])
    n=sum(p[0]!=255 for p in s.state['people']);s.advance(['down']*((n-s.state['actions_menu']['selected'])%(n+1))+['accept'])
    for _ in range(256):
        if s.state['mode']=='local-exploration':break
        s.pause()
    else:raise RuntimeError('Prison theft did not return to exploration')
    if s.state['mech_types'][2]!=ord('S') or s.state['people'][0][12]!=2 or not s.state['campaign']['mounted']:raise RuntimeError('Stolen Stinger or Jason allocation was lost')
    s.note('stinger-stolen');s.save_fixture('prison-theft');print('Prison theft:',len(s.actions),'ordinary inputs')

if __name__=='__main__':main()
