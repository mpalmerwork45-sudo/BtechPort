#!/usr/bin/env python3
"""Rent an arena mech, trigger the original alarm, escape and keep it."""
from make_late_building_replays import Buildings

def position(state):
    u=state['combat']['units'][0]
    return (u['x'],u['y'],u['heat'])

class Arena(Buildings):
    def command(self,item):
        c=self.state['combat']
        if c['phase']!=4:raise RuntimeError('Arena combat menu unavailable: '+str(c['phase']))
        self.advance(['down']*((item-c['selected'])%10)+['accept'])
        if self.state['combat']['phase']==12:self.advance(['accept'])
    def round(self):
        self.command(9)
        for _ in range(2048):
            c=self.state['combat']
            if c['phase']==10:self.advance(['accept'])
            elif c['phase']==9:self.advance(['idle']*4)
            else:break
        else:raise RuntimeError('Arena round did not finish')
    def waypoint(self,x,y):
        self.command(1);u=self.state['combat']['units'][0]
        self.advance(['right']*max(0,x-u['x'])+['left']*max(0,u['x']-x)+
            ['down']*max(0,y-u['y'])+['up']*max(0,u['y']-y)+['accept'])
    def spectator(self):
        self.command(3)
        for weapon in range(3):
            self.advance(['down']*((weapon-self.state['combat']['weapon'])%4))
            self.advance(['accept'])
            if self.state['combat']['phase']==20:self.advance(['accept'])
            for _ in range(24):
                if self.state['combat']['target']==2:break
                self.advance(['down']*((1-self.state['combat']['target_choice'])%3)+['accept'])
            else:raise RuntimeError('Spectator absent from target selector')
            self.advance(['down']*((0-self.state['combat']['target_choice'])%3)+['accept'])
        self.advance(['cancel'])

def main():
    s=Arena('GAME3','arena-theft');s.enter(1286,1078)
    if s.state['mode']!='local-exploration' or s.state['campaign']['mounted']:raise RuntimeError('Starport garage did not park the party')
    s.note('starport-garage-parked');s.enter(1340,1117)
    for _ in range(512):
        if s.state['mode']=='encounter':break
        if s.state['mode']=='impound-yard':s.advance(['idle']*4)
        else:s.settle_building()
    else:raise RuntimeError('Arena rental did not begin combat')
    s.note('arena-rented-locust');print('begin',position(s.state),s.state['yard'],flush=True)
    while s.state['combat']['phase'] in (1,2,3):s.advance(['accept'])
    # Fire on the spectator while still mobile. With the verified live AI,
    # waiting at the western wall lets the opponent destroy the rental's legs.
    s.waypoint(87,97)
    for _ in range(16):
        u=s.state['combat']['units'][0]
        if (u['x'],u['y'])==(87,97):break
        s.round()
        print('move',position(s.state),flush=True)
    else:raise RuntimeError('Arena approach route failed')
    s.note('arena-wall-approach');s.spectator()
    for _ in range(32):
        if s.state['campaign_flags'][35]:break
        s.round();print('shoot',s.state['combat']['event'],position(s.state),s.state['combat']['count'],flush=True)
    else:raise RuntimeError('Arena target did not trigger the alarm')
    s.note('arena-urbanmech-alarm');s.waypoint(66,102)
    for _ in range(32):
        if s.state['mode']!='encounter':break
        s.round();print('escape',s.state['mode'],position(s.state) if s.state['mode']=='encounter' else '',flush=True)
    else:raise RuntimeError('Arena escape did not complete')
    s.settle_building()
    for _ in range(512):
        if s.state['mode']=='local-exploration':break
        if s.state['mode']=='actions':
            # Every checked-out mech needs a pilot before the original Done.
            for member,bay in ((0,0),(1,1),(2,2)):
                n=sum(p[0]!=255 for p in s.state['people'])
                s.advance(['down']*((member-s.state['actions_menu']['selected'])%(n+1))+['accept']+['down']*bay+['accept'])
            n=sum(p[0]!=255 for p in s.state['people']);s.advance(['down']*((n-s.state['actions_menu']['selected'])%(n+1))+['accept'])
            if s.state['mode']=='actions':s.advance(['up','accept'])
        else:s.advance(['accept'])
    else:raise RuntimeError('Arena theft epilogue did not finish')
    s.note('arena-mech-stolen');s.save('arena-theft')

if __name__=='__main__':main()
