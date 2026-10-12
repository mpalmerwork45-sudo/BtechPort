#!/usr/bin/env python3
"""Continue ordinary training checkpoints through the invasion using inputs."""
import json
import sys
from collections import deque
from pathlib import Path
from verify_m2j import run

ROOT=Path(__file__).resolve().parents[1]
class Session:
    def __init__(self,source):
        self.binary=ROOT/'build/btech-headless'
        self.slot=ROOT/'work/m3d-audit/campaign.btp'
        self.leg=ROOT/'work/m3d-audit/campaign.actions'
        self.actions=Path(source).read_text().splitlines();self.notes=[]
        self.state=json.loads(run(self.binary,'--replay',source,'--save',self.slot))
    def advance(self,keys):
        if not keys:return
        self.leg.write_text('\n'.join(keys)+'\n')
        self.state=json.loads(run(self.binary,'--load',self.slot,'--replay',self.leg,'--save',self.slot))
        self.actions.extend(keys)
        if self.state['mode']=='script-error':raise RuntimeError('Script fault: '+str(self.state['fault_pc']))
    def note(self,label):
        self.notes.append({'label':label,'tick':len(self.actions)})
    def route(self,slot):
        raw=(ROOT/f'Original DOS/MAP{self.state["map"]}.MTP').read_bytes();tiles=raw[541:]
        entrances=[(raw[389+2*i]&127,raw[421+2*i]&127) for i in range(8)]
        start=self.state['x_half'],self.state['y_half'];target=entrances[slot]
        parent={start:None};queue=deque([start]);goal=None
        while queue:
            p=queue.popleft()
            if p==target:goal=p;break
            for key,dx,dy in [('up',0,-1),('right',1,0),('down',0,1),('left',-1,0)]:
                q=p[0]+dx,p[1]+dy;x,y=(q[0]+1)//2,q[1]//2
                if q in parent or not 0<=x<64 or not 0<=y<64 or q[0]<0 or q[1]<0:continue
                if tiles[(y&56)*64+(y&7)*8+(x&56)*8+(x&7)]>=85 or q in entrances and q!=target:continue
                parent[q]=(p,key);queue.append(q)
        if goal is None:raise RuntimeError('No walking route')
        keys=[]
        while parent[goal] is not None:goal,key=parent[goal];keys.append(key)
        self.advance(list(reversed(keys)))
    def command(self,n):
        c=self.state['combat']
        if c['phase']!=4:raise RuntimeError('Expected combat menu: '+str(c['phase']))
        self.advance(['down']*((n-c['selected'])%10)+['accept'])
        if self.state['combat']['phase']==12:self.advance(['accept'])
    def waypoint(self,x,y,mode=1):
        if self.state['combat']['goal'][0] and self.state['combat']['goal'][1]==mode:
            self.command(0 if mode else 1);self.advance(['cancel'])
        self.command(mode);c=self.state['combat'];u=c['units'][0]
        self.advance(['right']*max(0,x-u['x'])+['left']*max(0,u['x']-x)+
                     ['down']*max(0,y-u['y'])+['up']*max(0,u['y']-y)+['accept'])
    def round(self):
        self.command(9)
        for _ in range(1024):
            if self.state['combat']['phase']!=9:break
            self.advance(['idle']*4)
        else:raise RuntimeError('Turn stalled')
        self.story_popups()
    def story_popups(self):
        # Original invasion messages interrupt the round and remain explicit
        # ordinary Accept inputs; the intervening O2 movie runs to completion.
        for _ in range(1024):
            if self.state['combat']['phase']!=14:break
            self.advance(['idle']*4 if self.state['animation']['active'] else ['accept'])
        else:raise RuntimeError('Invasion story stalled')

if __name__=='__main__':
    s=Session(ROOT/'tests/fixtures/ordinary-sixth-story.actions')
    pause=int(sys.argv[1]) if len(sys.argv)>1 else 28
    s.advance(['idle']*(s.state['story_flags'][20]*4+pause));s.route(0);s.advance(['accept','accept'])
    from exepack import unpack
    import struct
    from prepare_talk import DS
    image,_=unpack((ROOT/'Original DOS/BTECH.EXE').read_bytes());answers=struct.unpack_from('<10H',image,DS+0x28ec)
    for _ in range(3):
        q=s.state['quiz'];s.advance(['down']*((answers[q['point']]-q['selected'])%20)+['accept'])
    s.advance(['accept','accept'])
    if s.state['menu_id']!=7:raise RuntimeError('Missing loan choice')
    loan=int(sys.argv[2]) if len(sys.argv)>2 else 0
    s.advance(['down']*((loan-s.state['menu_selected'])%3)+['accept'])
    for _ in range(128):
        if not s.state['animation']['active']:break
        s.advance(['idle'])
    if s.state['animation']['active']:raise RuntimeError('Startup did not complete')
    s.note('invasion-start');print('start',s.state['campaign'],s.state['mission'],s.state['npc_rng'])
    if not s.state['campaign']['invasion']:raise RuntimeError('Ordinary seventh branch; extend duel route')
    while s.state['combat']['phase'] in (1,2,3):s.advance(['accept'])
    s.story_popups()
    s.command(8);s.note('jenner-escape-denied');s.advance(['accept'])
    loss=len(sys.argv)>3 and sys.argv[3]=='--loss'
    for x,y in ([(72,77),(84,85),(96,93)] if loss else [(64,105),(80,121),(116,127)]):
        s.waypoint(x,y,2 if loan==1 else 1)
        for _ in range(24):
            if not s.state['combat']['phase']:break
            u=s.state['combat']['units'][0]
            if u['x']==x and u['y']==y:break
            s.round()
        print('leg',x,y,s.state['x_half'],s.state['y_half'],s.state['combat']['lost'])
        if not s.state['combat']['phase']:break
    if s.state['combat']['phase']:raise RuntimeError('Escape did not complete')
    s.note('invasion-result');s.advance(['idle'])
    for _ in range(100):
        if s.state['mode']=='local-exploration':break
        s.advance(['idle']*4 if s.state['animation']['active'] else ['accept'])
    s.note('destroyed-citadel')
    stem='ordinary-invasion-loss' if loss else 'ordinary-invasion'
    (ROOT/f'tests/fixtures/{stem}.actions').write_text('\n'.join(s.actions)+'\n')
    (ROOT/f'tests/fixtures/{stem}.json').write_text(json.dumps({'checkpoints':s.notes,'final':s.state},indent=2)+'\n')
    print('finished',s.state['map'],s.state['campaign'])
