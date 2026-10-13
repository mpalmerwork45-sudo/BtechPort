#!/usr/bin/env python3
"""Ordinary technician spy, inspection, combat resolution and replacement."""
import json,subprocess
from make_later_campaign_replay import Later,ROOT

def main():
    s=Later(ROOT/'tests/fixtures/ordinary-rex.actions')
    s.world_route(1300,1092);s.advance(['accept']*2)
    for _ in range(256):
        if s.state['service']['phase']==8:break
        s.pause()
    else:raise RuntimeError('Technician recruitment unavailable')
    s.note('technician-recruitment-wait')
    for delay in range(16):
        keys=['idle']*delay+['accept'];s.leg.write_text('\n'.join(keys)+'\n')
        after=json.loads(subprocess.check_output([str(s.binary),'--load',str(s.slot),'--replay',str(s.leg)],cwd=ROOT,text=True))
        if after['campaign_flags'][39]:s.advance(keys);break
    else:raise RuntimeError('No spy coin in bounded ordinary key delays')
    for _ in range(512):
        if s.state['mode']=='local-exploration':break
        s.pause()
    else:raise RuntimeError('Spy recruitment did not finish')
    s.note('technician-spy-joined')
    # Parked vehicles have no active mech inspection row. The character
    # choice exposes the spy exactly through the ordinary Space menu.
    s.advance(['menu','down','down','accept','down','down','accept','cancel'])
    s.note('spy-inspected')
    for _ in range(1024):
        if s.state['mode']=='encounter':break
        s.advance(['idle']*4)
    else:raise RuntimeError('No encounter in bounded ordinary outdoor time')
    s.note('spy-combat-offer')
    s.advance(['accept','left','accept','up','up','accept','right','accept'])
    for _ in range(2048):
        if s.state['combat']['phase']==17:break
        if s.state['mode']=='game-over':raise RuntimeError('Party defeated before the spy confrontation')
        s.advance(['idle']*4)
    else:raise RuntimeError('Spy confrontation did not appear')
    s.note('spy-confrontation');s.advance(['accept']);s.note('spy-killed-in-combat')
    if s.state['campaign_flags'][39] or s.state['people'][2][0]!=255:raise RuntimeError('Spy still present')
    if s.state['combat']['phase']==4:s.command(8)
    for _ in range(512):
        if s.state['mode']=='local-exploration':break
        s.pause()
    else:raise RuntimeError('Spy combat aftermath did not finish')
    # Move off the doorway before entering again: the previous building/flee
    # return leaves the party at this exact entrance, not at its approach.
    s.advance(['down']);s.world_route(1300,1092);s.advance(['accept'])
    for _ in range(256):
        if s.state['script_status']==1:break
        s.pause()
    else:raise RuntimeError('Repair shop did not reopen')
    s.advance(['down']*((0-s.state['menu_selected'])%6)+['accept'])
    for _ in range(1024):
        if s.state['service']['phase']==8:break
        s.pause()
    else:raise RuntimeError('Replacement specialist did not offer to join')
    s.note('replacement-technician-joined');s.advance(['accept'])
    for _ in range(256):
        if s.state['script_status']==1:break
        s.pause()
    else:raise RuntimeError('Replacement did not return to the shop menu')
    s.advance(['down']*((5-s.state['menu_selected'])%6)+['accept']);s.note('replacement-shop-exit')
    if s.state['people'][2][0]!=3 or s.state['people'][2][9]!=3 or s.state['campaign_flags'][39]:
        raise RuntimeError('Replacement identity/skill or lifetime spy gate differs')
    s.save_fixture('spy-replacement');print('Input-only spy replacement:',len(s.actions),'inputs')
if __name__=='__main__':main()
