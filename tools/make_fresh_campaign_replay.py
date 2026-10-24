#!/usr/bin/env python3
"""Fresh-game inputs through companions, apprenticeships, disk, hut and ending.

Only the owner's authorized credit shortcut is used. No original save import,
quest flags, ranks, coordinates, puzzle cards or random seed are edited.
"""
import json
import subprocess
from make_late_building_replays import Buildings,ROOT
from make_cache_replay import finish

class Fresh(Buildings):
    def __init__(self):
        self.source='fresh game';self.work=ROOT/'work/m4-audit';self.slot=self.work/'fresh-campaign.btp'
        self.leg=self.work/'fresh-campaign.actions';self.binary=ROOT/'build/btech-headless';self.checkpoints=[]
        prefix=ROOT/'tests/fixtures/ordinary-jail-visitor.actions';self.actions=prefix.read_text().splitlines()
        self.state=json.loads(subprocess.check_output([str(self.binary),'--replay',str(prefix),'--save',str(self.slot)],cwd=ROOT,text=True))
        if len([p for p in self.state['people'] if p[0]!=255])!=5:raise RuntimeError('Fresh companions did not join')
        self.note('fresh-trained-party')
        self.travel_crew();self.note('fresh-travel-crew')
    def travel_crew(self):
        if self.state['campaign']['mounted']:return
        if self.state['map']==2:
            # Walking out of a Starport shop requires the actual garage
            # checkout. Allocation alone does not move the parked vehicles.
            for _ in range(3):
                self.world_route(1297,1077);self.advance(['accept'])
                for _ in range(256):
                    if self.state['mode'] in ('actions','local-exploration'):break
                    self.advance(['idle']*8 if self.state['animation']['active'] or self.state['audio']['effects'] else ['accept'])
                if self.state['mode']=='actions':break
            else:raise RuntimeError('Original garage checkout did not open')
        else:
            if self.state['map']:
                raw=(getattr(self,'original_data',ROOT/'Original DOS')/f'MAP{self.state["map"]}.MTP').read_bytes()
                ox=self.state['campaign']['world'][0]//128*128
                self.world_route(ox+2*raw[3]+16,self.state['campaign']['world'][1])
            self.advance(['menu','down','down','accept'])
        for member,bay in ((0,0),(1,1)):
            n=sum(p[0]!=255 for p in self.state['people'])
            self.advance(['down']*((member-self.state['actions_menu']['selected'])%(n+1))+['accept']+['down']*bay+['accept'])
            if self.state['actions_menu']['phase']==17:self.advance(['accept'])
        if self.state['campaign']['building']==8 and self.state['mode']=='actions':
            n=sum(p[0]!=255 for p in self.state['people'])
            self.advance(['down']*((n-self.state['actions_menu']['selected'])%(n+1))+['accept']);self.settle_building()
        else:self.advance(['cancel'])
        if not self.state['campaign']['mounted']:raise RuntimeError('Jason did not board his owned mech')
    def enter(self,x,y):
        # Starport's ordinary garage parks the vehicles before town services.
        # The normal collision gate no longer allows a mech across roofs to
        # reach these small shop doorways.
        starport=x//128==10 and y//128==8
        if not starport and self.state['campaign_flags'][24]:self.travel_crew()
        if starport and self.state['campaign']['mounted']:
            self.world_route(1286,1080);self.advance(['accept'])
            for _ in range(256):
                if self.state['mode']=='local-exploration':break
                self.advance(['idle']*8 if self.state['animation']['active'] or self.state['audio']['effects'] else ['accept'])
            else:raise RuntimeError('Starport garage did not finish parking')
        elif self.state['campaign']['mounted']:
            if self.state['map']:
                raw=(getattr(self,'original_data',ROOT/'Original DOS')/f'MAP{self.state["map"]}.MTP').read_bytes()
                ox=self.state['campaign']['world'][0]//128*128
                self.world_route(ox-32,self.state['campaign']['world'][1])
            self.advance(['menu','down','down','accept'])
            for member,bay in ((1,0),(4,1),(0,sum(t!=255 for t in self.state['mech_types']))):
                n=sum(p[0]!=255 for p in self.state['people'])
                self.advance(['down']*((member-self.state['actions_menu']['selected'])%(n+1))+['accept']+['down']*bay+['accept'])
                if self.state['actions_menu']['phase']==17:self.advance(['accept'])
            n=sum(p[0]!=255 for p in self.state['people'])
            self.advance(['down']*((n-self.state['actions_menu']['selected'])%(n+1))+['accept'])
        super().enter(x,y)
    def settle_building(self):
        for _ in range(2048):
            if self.state['mode']=='local-exploration' or self.state['script_status'] in (1,6):return
            if self.state['service']['phase'] in (7,9,10,11) or self.state['service']['action']==32:return
            self.advance(['idle']*8 if self.state['animation']['active'] or self.state['audio']['effects'] else ['accept'])
        raise RuntimeError('Fresh building did not settle')
    def upgrade(self,x,y,member,skill):
        self.enter(x,y);self.choose(0 if skill==9 else 1)
        if skill==10 and self.state['script_status']==6:
            self.note('medical-seminar-offer');self.advance(['accept']);self.settle_building()
        if self.state['service']['phase']!=7:raise RuntimeError('Apprenticeship character choice unavailable')
        n=sum(p[0]!=255 for p in self.state['people'])
        self.advance(['down']*((member-self.state['service']['selected'])%n)+['accept']);self.settle_building()
        if self.state['script_status']==6:
            self.note('apprenticeship-offer');self.advance(['accept']);self.settle_building()
        if self.state['people'][member][skill]!=4:raise RuntimeError('Actual apprenticeship did not earn rank four')
        self.note('technician-qualified' if skill==9 else 'medic-qualified')
        from audit_bld_flow import COUNTS
        self.choose(COUNTS[self.state['menu_id']]-1)

def main():
    s=Fresh();s.advance(['credit-10000']);s.note('owner-authorized-funding')
    s.upgrade(1300,1092,2,9);s.upgrade(1184,1443,3,10)
    s.enter(1553,1545);s.settle_building();s.note('jeremiah-holodisk-viewed')
    if not s.state['campaign_flags'][50]:raise RuntimeError('Ruined barracks did not play VIEWDISK')
    s.enter(522,390);s.settle_building();s.note('tellhim-password-earned')
    if not all(s.state['campaign_flags'][i] for i in (53,54)):raise RuntimeError('Qualified party did not earn the cache password')
    finish(s,'fresh-campaign',prerequisite='Fresh first-time start; six training assignments, Jenner escape, Rex/technician/medic/prison companions, paid rank-four apprenticeships and original VIEWDISK/HUT prerequisites. Owner-authorized money shortcut inputs only; no save import or state/RNG edits.')
if __name__=='__main__':main()
