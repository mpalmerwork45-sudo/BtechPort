#!/usr/bin/env python3
"""Input-only cache/ending route from the owner's explicit late-game GAME1.

Routes read real native saves, never edit cursor/flags/RNG or puzzle state.
"""
import json,struct,subprocess
from pathlib import Path
from combat_oracle import ROOT
from exepack import unpack

class Route:
    def __init__(self,source='GAME1',stem='cache-route'):
        self.work=ROOT/'work/m4-audit';self.work.mkdir(exist_ok=True)
        self.slot=self.work/f'{stem}.btp';self.leg=self.work/f'{stem}.actions'
        self.binary=ROOT/'build/btech-headless';self.actions=[];self.checkpoints=[]
        self.state=json.loads(subprocess.check_output([str(self.binary),'--load',str(ROOT/'Original DOS'/source),'--save',str(self.slot)],cwd=ROOT,text=True))
    def advance(self,actions):
        if not actions:return
        self.leg.write_text('\n'.join(actions)+'\n')
        self.state=json.loads(subprocess.check_output([str(self.binary),'--load',str(self.slot),
            '--replay',str(self.leg),'--save',str(self.slot)],cwd=ROOT,text=True))
        self.actions.extend(actions)
        if self.state['mode']=='script-error':raise RuntimeError('Cache script fault '+str(self.state['fault_pc']))
    def note(self,label):self.checkpoints.append(dict(label=label,tick=len(self.actions),state=self.state))
    def settle(self):
        for _ in range(256):
            if self.state['mode']=='ending':return
            if self.state['mode']=='cache' and self.state['cache']['phase']==0:return
            if self.state['cache']['phase']==7 and not any(c['label']=='phoenix-screen' for c in self.checkpoints):self.note('phoenix-screen')
            if self.state['animation']['active'] or self.state['audio']['effects']:self.advance(['idle']*16)
            else:self.advance(['accept'])
        raise RuntimeError('Cache presentation did not settle')
    def route(self,kind,index=0,probe=False):
        result=subprocess.run([str(ROOT/'build/btp-cache-route'),str(self.slot),kind,str(index)],cwd=ROOT,capture_output=True,text=True)
        if probe:return result.returncode==0
        if result.returncode:raise RuntimeError(result.stderr)
        self.advance(result.stdout.splitlines())

def main():
    s=Route();image,_=unpack((ROOT/'Original DOS/BTECH.EXE').read_bytes());ds=0x36db0
    requirements=[image[ds+p:ds+p+12] for p in (0x2492,0x249e,0x24aa)]
    # This late original save already has disk/password prerequisites. Its
    # native import uses the existing documented deterministic RNG context.
    keys=subprocess.check_output([str(ROOT/'build/btp-world-route'),str(s.slot),'776','780'],cwd=ROOT,text=True).splitlines()
    s.advance(keys)
    if s.state['mode']!='entry-confirm':raise RuntimeError('Cache entrance unreachable')
    s.note('cache-entrance');s.advance(['accept']);s.settle();s.note('cache-instructions-complete')
    if s.state['mode']!='cache' or not s.state['cache']['active']:raise RuntimeError('Cache did not open')
    opened=[]
    while len(opened)<11:
        chosen=None
        for door in range(11):
            if door in opened:continue
            if s.route('door',door,probe=True) and all(s.route('terminal',requirements[c][door]-1,probe=True) for c in range(3)):
                chosen=door;break
        if chosen is None:
            if not s.state['cache']['hall'] and s.route('secret',probe=True):
                s.route('secret');s.settle();s.note('secret-passage');continue
            raise RuntimeError('No accessible door code set; opened '+str(opened))
        for color in range(3):
            term=requirements[color][chosen]-1;s.route('terminal',term)
            if s.state['cache']['phase']!=2:raise RuntimeError('Code terminal did not prompt')
            s.note(f'code-terminal-{term+1}');s.advance(['accept'])
        s.route('door',chosen);s.note(f'door-{chosen+1}-opening');s.settle();opened.append(chosen)
        s.note(f'door-{chosen+1}-open')
        print('Opened door',chosen+1,'after',len(s.actions),'ordinary inputs',flush=True)
    if not s.state['cache']['hall']:
        s.route('secret');s.settle();s.note('secret-passage')
    s.route('phoenix');s.settle();s.note('phoenix-inspected')
    s.route('room');s.settle();s.note('map-room')
    # Exercise the original rejection/reset before entering the correct code.
    s.route('submit');s.note('wrong-password');s.settle()
    for index in struct.unpack_from('<7H',image,ds+0x241e):
        s.route('symbol',index);s.note(f'password-symbol-{index}')
        while s.state['audio']['effects']:s.advance(['idle']*8)
    s.route('submit');s.note('white-code-accepted');s.settle()
    if not s.state['cache']['white']:raise RuntimeError('White code not accepted')
    s.route('exit');s.settle();s.note('map-room-exit')
    s.route('power');s.settle();s.note('hyperpulse-power')
    s.route('found');s.settle();s.note('cache-found')
    s.route('generator');s.note('ending-start');s.settle();s.note('ending-complete')
    if s.state['mode']!='ending':raise RuntimeError('Original ending did not finish')
    (ROOT/'tests/fixtures/ordinary-cache.actions').write_text('\n'.join(s.actions)+'\n')
    (ROOT/'tests/fixtures/ordinary-cache.json').write_text(json.dumps(dict(
        prerequisite='Original DOS/GAME1 imported normally; explicit late-game disk/password and trained-party context',
        route='Ordinary world travel, original entrance/instructions, all eleven security doors, secret passage, Phoenix display, MAP15 rejection/correct code, power, parts and ending',
        doors=opened,checkpoints=s.checkpoints,final=s.state),indent=2)+'\n')
    print('Saved cache-to-ending route:',len(s.actions),'ordinary inputs')
if __name__=='__main__':main()
