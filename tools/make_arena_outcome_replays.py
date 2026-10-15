#!/usr/bin/env python3
"""Play ordinary arena wins/losses and a prison-guard defeat, without save edits."""
import json
from make_arena_replay import Arena
from make_later_campaign_replay import Later, ROOT


def arena(name, rental, win):
    s = Arena('GAME3', name)
    source = json.loads((ROOT / 'tests/fixtures/ordinary-arena-theft.json').read_text())
    entrance = [c['tick'] for c in source['checkpoints'] if c['label'] == 'entry'][-1]
    s.advance((ROOT / 'tests/fixtures/ordinary-arena-theft.actions').read_text().splitlines()[:entrance])
    s.advance(['accept'])
    confirmations = 0
    for _ in range(256):
        if s.state['mode'] == 'encounter':
            break
        if s.state['yard']['phase'] == 7:
            s.note('owned-mech-choice');s.advance(['accept']);s.note('owned-mech-waiver')
        elif s.state['mode'] == 'impound-yard' or s.state['animation']['active'] or s.state['audio']['effects']:
            s.advance(['idle'] * 8)
        elif s.state['script_status'] == 6:
            s.advance(['right', 'accept'] if confirmations and not rental else ['accept'])
            confirmations += 1
        else:
            s.advance(['accept'])
    else:
        raise RuntimeError('Arena did not start')
    s.note('arena-start');s.advance(['accept', 'accept', 'accept'])
    if rental and win:
        # Two ordinary unarmed turns alter the approach and subsequent rolls.
        # All damage, ammunition and victory still come from live combat.
        s.round();s.round()
    # Leaving weapons unassigned exercises a real defeat for either loan
    # choice, independent of which opponent wins a computer-vs-computer roll.
    if win:
        s.command(5)
    for _ in range(256):
        if s.state['aftermath']['phase'] or s.state['mode'] != 'encounter':
            break
        if s.state['combat']['phase'] == 4:
            s.round()
        else:
            s.advance(['idle'] * 128)
    else:
        raise RuntimeError('Arena result did not arrive')
    if s.state['aftermath']['phase'] != 11 or bool(s.state['combat']['won']) != win:
        raise RuntimeError('Unexpected arena outcome')
    s.note('arena-result');s.advance(['menu']);s.note('arena-cashier');s.settle_building()
    if s.state['mode'] != 'local-exploration' or s.state['people'][0][0] == 255:
        raise RuntimeError('Surviving arena pilot did not return to town')
    s.note('arena-exited');s.save(name)


def prison():
    source = json.loads((ROOT / 'tests/fixtures/ordinary-prison-theft.json').read_text())
    tick = next(c['tick'] for c in source['checkpoints'] if c['label'] == 'impound-yard-start')
    prefix = ROOT / 'work/m4-audit/prison-loss-prefix.actions'
    prefix.write_text('\n'.join((ROOT / 'tests/fixtures/ordinary-prison-theft.actions').read_text().splitlines()[:tick]) + '\n')
    s = Later(prefix);s.note('prison-yard')
    for _ in range(256):
        if s.state['mode'] == 'encounter':break
        s.advance(['idle'] * 8)
    else:raise RuntimeError('Prison guards did not arrive')
    s.note('prison-guards');s.advance(['left', 'accept', 'accept', 'accept'])
    for _ in range(512):
        if s.state['mode'] != 'encounter':break
        s.advance(['idle'] * 128)
    else:raise RuntimeError('Prison combat did not finish')
    for _ in range(128):
        if s.state['mode'] == 'game-over':break
        s.advance(['accept'])
    else:raise RuntimeError('Prison loss did not reach its original ending')
    s.note('prison-loss');s.save_fixture('prison-loss')
    print('prison-loss', len(s.actions), 'ordinary inputs', flush=True)


def main():
    for rental in (False, True):
        for win in (False, True):
            arena(f'arena-{"rental" if rental else "owned"}-{"win" if win else "loss"}', rental, win)
    prison()


if __name__ == '__main__':main()
