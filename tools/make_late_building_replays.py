#!/usr/bin/env python3
"""Reach late buildings from original GAME3 using recorded inputs only."""
import json
import subprocess
from pathlib import Path
from make_cache_replay import Route,ROOT

class Buildings(Route):
    def __init__(self,source,stem):
        super().__init__(source,stem);self.source=source
    def world_route(self,x,y):
        self.advance(subprocess.check_output([str(ROOT/'build/btp-world-route'),str(self.slot),str(x),str(y)],cwd=ROOT,text=True).splitlines())
    def enter(self,x,y):
        self.world_route(x,y+2*self.state['campaign']['mounted'])
        if self.state['mode']!='entry-confirm':raise RuntimeError('Building entrance unavailable')
        self.note('entry');self.advance(['accept']);self.settle_building()
    def settle_building(self):
        for _ in range(2048):
            if self.state['mode']=='encounter' or (self.state['mode']=='impound-yard' and self.state['yard']['phase']!=5):return
            if self.state['mode'] in ('local-exploration','actions') or self.state['script_status']==1 or self.state['service']['phase'] in (9,10,11):return
            if self.state['animation']['active'] or self.state['audio']['effects']:self.advance(['idle']*8)
            else:self.advance(['accept'])
        raise RuntimeError('Building presentation did not finish')
    def choose(self,item):
        from audit_bld_flow import COUNTS
        count=COUNTS[self.state['menu_id']]
        self.advance(['down']*((item-self.state['menu_selected'])%count)+['accept']);self.settle_building()
    def save(self,name):
        (ROOT/f'tests/fixtures/ordinary-{name}.actions').write_text('\n'.join(self.actions)+'\n')
        (ROOT/f'tests/fixtures/ordinary-{name}.json').write_text(json.dumps(dict(
            prerequisite=f'Original DOS/{self.source} imported normally; all travel and choices are input only',
            checkpoints=self.checkpoints,final=self.state),indent=2)+'\n')
        print(name,len(self.actions),'inputs',self.state['mode'],flush=True)

def main():
    for item,name in ((0,'mayor-newspaper'),(1,'mayor-holodisk'),(2,'mayor-chow')):
        s=Buildings('GAME3',name);s.enter(1200,1458)
        if s.state['menu_id']!=32:raise RuntimeError('Mayor-house menu unavailable')
        s.note('house-menu');s.choose(item);s.note('selected-house-activity')
        if s.state['mode']=='building' and s.state['menu_id']==32:
            # Reading the newspaper returns to the house menu. Leave via the
            # holodisk activity so the regression also verifies the exit.
            s.choose(1);s.note('house-exit')
        s.save(name)
    s=Buildings('GAME3','cinema');s.enter(690,1674);s.note('cinema-complete');s.save('cinema')
    s=Buildings('GAME3','inventor');s.enter(522,390);s.note('inventor-complete');s.save('inventor')
    s=Buildings('GAME5','inventor-qualified')
    # This owner's save has a malformed fourth vehicle. Leave its two crew
    # on foot through the ordinary allocation menu before travelling; no save
    # bytes, character ranks, quest flags or random seed are edited.
    s.advance(['menu','down','down','accept'])
    for member in (4,3):
        s.advance(['down']*((member-s.state['actions_menu']['selected'])%(sum(p[0]!=255 for p in s.state['people'])+1))+['accept']+['down']*sum(t!=255 for t in s.state['mech_types'])+['accept'])
    s.advance(['cancel']);s.note('qualified-party-on-foot')
    s.enter(522,390);s.note('inventor-qualified-complete')
    if not s.state['campaign_flags'][53] or not s.state['campaign_flags'][54]:raise RuntimeError('Qualified inventor visit did not grant the password')
    s.save('inventor-qualified')
    s=Buildings('GAME3','laser-guns');s.enter(264,1566)
    if s.state['menu_id']!=30:raise RuntimeError('Laser-gun shop menu unavailable')
    s.note('laser-menu');s.advance(['accept'])
    for _ in range(512):
        if s.state['script_status']==6:break
        s.advance(['idle']*8 if s.state['audio']['effects'] else ['accept'])
    else:raise RuntimeError('Laser-shop escape choice unavailable')
    s.note('laser-shop-robbery');s.advance(['right','accept']);s.settle_building()
    for _ in range(128):
        if s.state['service']['phase'] not in (9,10,11):break
        if s.state['service']['phase']==9:s.advance(['accept'])
        elif s.state['service']['phase']==11:s.advance(['accept'])
        else:
            n=sum(p[0]!=255 for p in s.state['people']);member=s.state['service']['mech']
            # Give each issued laser to the corresponding party member; then
            # decline further redistribution of the displaced personal gun.
            s.advance(['down']*((member-s.state['service']['selected'])%(n+1))+['accept'])
            if s.state['service']['phase']==10:
                s.advance(['down']*((n-s.state['service']['selected'])%(n+1))+['accept'])
        s.settle_building()
    else:raise RuntimeError('Laser distribution stalled')
    s.note('laser-purchase-complete');s.save('laser-guns')

if __name__=='__main__':main()
