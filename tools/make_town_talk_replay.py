#!/usr/bin/env python3
"""Wait for an actual town arrival, then use the hospital's original Talk menu."""
from make_late_building_replays import Buildings
import subprocess


def main():
    s=Buildings('GAME2','hospital-talk')
    # Leave room for all five foot soldiers, including the leftmost member.
    s.world_route(1324,1098);s.note('town-arrival-wait')
    if s.state['mode']!='local-exploration':raise RuntimeError('Arrival wait must remain outside every doorway')
    # The original hospital BLD requests category 5. Wait near that doorway
    # for a live walker to arrive, then walk to the clinic during its stay.
    for _ in range(256):
        if any(pair>>4==3 and timer>12 for pair,timer in s.state['npc_pairs']):break
        s.world_route('idle',12)
    else:raise RuntimeError('No town arrival within the bounded wait')
    s.note('town-npc-arrival')
    # NPC room 3 is shared by the hospital's Talk category. It can empty
    # during a one-step cross-town walk; use the ordinary four-step setting
    # and replan after each key, then slow down for the doorway.
    s.advance(['menu','down','accept','accept','down','down','accept'])
    for _ in range(128):
        if s.state['mode']=='entry-confirm':break
        x,y=s.state['campaign']['world']
        if abs(x-1396)+abs(y-1138)<12:
            s.advance(['menu','down','accept','accept','up','up','accept'])
            s.enter(1396,1138);break
        keys=subprocess.check_output([str(s.binary.parent/'btp-world-route'),str(s.slot),'1396','1138','--next'],cwd=s.binary.parent.parent,text=True).splitlines()
        s.advance(keys)
    else:raise RuntimeError('Hospital approach exceeded its input bound')
    if s.state['mode']=='entry-confirm':s.advance(['accept']);s.settle_building()
    s.note('hospital-menu')
    s.advance(['down']*((3-s.state['menu_selected'])%7)+['accept'])
    if s.state['talk_phase']!=2 or not s.state['talk_count']:
        raise RuntimeError('The hospital did not offer the arrived NPC')
    s.note('hospital-talk-menu');s.advance(['accept']);s.note('hospital-talk-reply')
    if s.state['talk_phase']!=3:raise RuntimeError('The NPC reply did not appear')
    s.advance(['accept']);s.note('hospital-talk-return');s.save('hospital-talk')


if __name__=='__main__':main()
