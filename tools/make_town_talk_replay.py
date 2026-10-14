#!/usr/bin/env python3
"""Wait for an actual town arrival, then use the hospital's original Talk menu."""
from make_late_building_replays import Buildings


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
    s.enter(1396,1138);s.note('hospital-menu')
    s.advance(['down']*((3-s.state['menu_selected'])%7)+['accept'])
    if s.state['talk_phase']!=2 or not s.state['talk_count']:
        raise RuntimeError('The hospital did not offer the arrived NPC')
    s.note('hospital-talk-menu');s.advance(['accept']);s.note('hospital-talk-reply')
    if s.state['talk_phase']!=3:raise RuntimeError('The NPC reply did not appear')
    s.advance(['accept']);s.note('hospital-talk-return');s.save('hospital-talk')


if __name__=='__main__':main()
