#!/usr/bin/env python3
"""Generate town/recruitment/service routes using ordinary input only."""
from pathlib import Path
import json,subprocess
from make_campaign_replay import Session,ROOT
from verify_m2j import run
class Later(Session):
    def world_route(self,x,y):
        self.advance(subprocess.check_output([str(ROOT/'build/btp-world-route'),str(self.slot),str(x),str(y)],cwd=ROOT,text=True).splitlines())
    def wait_outdoors(self,n):self.world_route('idle',n)
    def save_fixture(self,name):
        (ROOT/f'tests/fixtures/ordinary-{name}.actions').write_text('\n'.join(self.actions)+'\n')
        (ROOT/f'tests/fixtures/ordinary-{name}.json').write_text(json.dumps({'checkpoints':self.notes,'final':self.state},indent=2)+'\n')
    def pause(self):self.advance(['idle']*8 if self.state['animation']['active'] else ['accept'])
def main():
    s=Later(ROOT/'tests/fixtures/ordinary-invasion.actions');s.world_route(1286,1080);s.advance(['accept']*3)
    if s.state['mode']!='local-exploration' or s.state['map']!=2:raise RuntimeError('Garage transition failed')
    s.note('parked-in-starport');s.save_fixture('starport')
    s.world_route(1370,1088);s.advance(['accept']*3);s.note('civilian-clothing')
    s.world_route(1394,1116);s.advance(['accept']*4);s.wait_outdoors(s.state['campaign_flags'][29]*4)
    s.advance(['right','left','accept'])
    for _ in range(100):
        if s.state['mode']=='encounter':break
        if s.state['mode']=='script-error':raise RuntimeError('Inauguration fault')
        if s.state['animation']['active'] and not any(n['label']=='rex-crest' for n in s.notes):s.note('rex-crest')
        s.pause()
    else:raise RuntimeError('Rex sequence stalled')
    s.advance(['accept']*3);s.command(8);s.note('rex-and-commando');s.save_fixture('rex')
    s.world_route(1300,1092);s.advance(['accept']*2)
    for _ in range(100):
        if s.state['service']['phase']==8:break
        s.pause()
    else:raise RuntimeError('Technician sequence stalled')
    # Try actual key delays; no save payload or random state is edited.
    leg=ROOT/'work/m3d-audit/agent-delay.actions'
    for delay in range(16):
        keys=['idle']*delay+['accept'];leg.write_text('\n'.join(keys)+'\n')
        result=json.loads(run(s.binary,'--load',s.slot,'--replay',leg))
        if not result['campaign_flags'][39]:s.advance(keys);break
    else:raise RuntimeError('No non-hostile agent timing in bounded key delays')
    s.note('technician-joined');print('technician',s.state['mode'],s.state['menu_id'],s.state['service'],s.state['campaign_flags'][32:40])
    def menu(n):
        s.advance(['down']*((n-s.state['menu_selected'])%6)+['accept'])
    menu(2);s.advance(['accept']);s.note('partial-armour-repair')
    # The original service asks for each damaged area, then returns directly
    # to the BLD. There are no generic repair categories or eleven-bin menu.
    for _ in range(100):
        if not s.state['service']['phase']:break
        s.pause()
    else:raise RuntimeError('Original repair sequence did not finish')
    menu(3);s.advance(['accept'])
    if s.state['service']['phase']==5:s.advance(['1'])
    s.note('partial-ammo-amount')
    if s.state['service']['phase']==5:s.advance(['0','accept'])
    s.note('ammo-purchase-boundary')
    for _ in range(100):
        if not s.state['service']['phase']:break
        s.pause()
    else:raise RuntimeError('Original ammunition sequence did not finish')
    menu(1);s.advance(['accept'])
    for _ in range(10):
        if s.state['service']['phase']==3:break
        s.advance(['accept'])
    else:raise RuntimeError('Speed Shop offer did not reach confirmation')
    s.advance(['accept','accept']);s.note('speed-shop-no-funds');menu(5)
    s.save_fixture('services')
    print('Saved ordinary Starport, Rex and technician routes')
if __name__=='__main__':main()
