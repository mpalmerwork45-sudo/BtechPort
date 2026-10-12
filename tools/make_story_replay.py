#!/usr/bin/env python3
"""Continue ordinary Starport inputs through the hospital companion and kits."""
import json
from make_later_campaign_replay import Later,ROOT,run

def main():
    s=Later(ROOT/'tests/fixtures/ordinary-services.actions')
    # Explicit owner-authorized credit shortcut, through the ordinary core input.
    s.advance(['credit-10000']);s.note('funded-by-owner-shortcut')
    s.world_route(1297,1077)
    for _ in range(64):
        s.advance(['accept'])
        if s.state['mode']=='local-exploration' and not s.state['campaign_flags'][24]:break
    else:raise RuntimeError('Garage checkout failed')
    s.note('garage-checkout')
    # Put Rex at the controls; Jason can enter town on foot while his party
    # retains the checked-out records. This is ordinary allocation input.
    s.advance(['menu','down','down','accept','down','accept','accept','accept'])
    s.advance(['up','accept','down','down','down','down','accept','cancel'])
    if s.state['campaign']['mounted']:raise RuntimeError('Jason did not dismount')
    s.note('walking-with-rex-piloting');s.world_route(1184,1443)
    for _ in range(16):
        if s.state['mode']=='building' and s.state['menu_id'] in (25,27,28):break
        s.advance(['accept'])
    else:raise RuntimeError('Hospital menu unavailable')
    s.note('hospital-menu');count={25:5,27:6,28:7}[s.state['menu_id']]
    s.advance(['down']*((2-s.state['menu_selected'])%count)+['accept'])
    for _ in range(128):
        if s.state['service']['phase']==8:break
        s.pause()
    else:raise RuntimeError('Hospital companion unavailable')
    s.note('hospital-companion-pause')
    for delay in range(16):
        keys=['idle']*delay+['accept'];s.leg.write_text('\n'.join(keys)+'\n')
        result=json.loads(run(s.binary,'--load',s.slot,'--replay',s.leg))
        if not result['campaign_flags'][39]:s.advance(keys);break
    else:raise RuntimeError('No peaceful companion delay in bounded inputs')
    for _ in range(16):
        if s.state['mode']=='building' and s.state['menu_id']==28:break
        s.pause()
    else:raise RuntimeError('Medic did not unlock surgery-kit menu')
    s.note('hospital-companion-joined')
    for selection,label in ((4,'medical-kit'),(5,'field-surgery-kit')):
        s.advance(['down']*((selection-s.state['menu_selected'])%7)+['accept'])
        for _ in range(16):
            if s.state['script_status']==6:break
            s.pause()
        else:raise RuntimeError('Kit offer did not ask confirmation')
        s.advance(['accept'])
        for _ in range(16):
            if s.state['mode']=='building' and s.state['menu_id']==28 and s.state['script_status']==1:break
            s.pause()
        else:raise RuntimeError('Kit purchase did not return')
        s.note(label)
    s.advance(['down']*((6-s.state['menu_selected'])%7)+['accept']);s.note('hospital-exit')
    s.save_fixture('hospital');print('Saved ordinary hospital companion and two-kit route:',len(s.actions))
    s.world_route(1668,925)
    for _ in range(32):
        if s.state['script_status']==1 and s.state['menu_id']==31:break
        s.pause()
    else:raise RuntimeError('Jail visitor menu unavailable')
    s.note('jail-visitor-menu');s.advance(['accept'])
    for _ in range(256):
        if s.state['service']['phase']==8:break
        s.pause()
    else:raise RuntimeError('Jail companion unavailable')
    s.note('jail-companion-pause')
    for delay in range(16):
        keys=['idle']*delay+['accept'];s.leg.write_text('\n'.join(keys)+'\n')
        result=json.loads(run(s.binary,'--load',s.slot,'--replay',s.leg))
        if not result['campaign_flags'][39]:s.advance(keys);break
    else:raise RuntimeError('No peaceful jailbreak delay in bounded inputs')
    for _ in range(64):
        if s.state['script_status']==6:break
        s.pause()
    else:raise RuntimeError('Jail mech choice unavailable')
    s.note('jail-companion-joined');s.advance(['right','accept'])
    for _ in range(32):
        if s.state['mode']=='local-exploration':break
        s.pause()
    if s.state['mode']!='local-exploration':raise RuntimeError('Declining impound-yard run failed')
    s.note('jail-exit');s.save_fixture('jail-visitor');print('Saved ordinary jailbreak companion / declined impound-yard route:',len(s.actions))
if __name__=='__main__':main()
