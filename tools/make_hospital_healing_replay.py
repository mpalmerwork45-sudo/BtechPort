#!/usr/bin/env python3
"""Ordinary paid hospital healing from the owner's explicit injured GAME2."""
import json,subprocess
from make_cache_replay import Route,ROOT

def main():
    s=Route('GAME2','hospital-healing');s.note('injured-original-party')
    s.advance(['credit-10000']);s.note('funded-by-owner-shortcut')
    keys=subprocess.check_output([str(ROOT/'build/btp-world-route'),str(s.slot),'1396','1138'],cwd=ROOT,text=True).splitlines()
    s.advance(keys)
    for _ in range(32):
        if s.state['mode']=='building' and s.state['script_status']==1:break
        s.advance(['accept'])
    else:raise RuntimeError('Clinic menu missing')
    s.note('hospital-menu');counts={25:5,27:6,28:7}
    s.advance(['down']*((0-s.state['menu_selected'])%counts[s.state['menu_id']])+['accept'])
    for _ in range(32):
        if s.state['script_status']==1 and s.state['menu_id']==26:break
        s.advance(['accept'])
    else:raise RuntimeError('Doctor menu missing')
    s.note('doctor-choice');before=s.state
    s.advance(['down']*((4-s.state['menu_selected'])%8)+['accept'])
    for _ in range(64):
        if s.state['script_status']==1 and s.state['menu_id'] in counts:break
        s.advance(['accept'])
    else:raise RuntimeError('Healing did not return')
    if s.state['people'][1][15]<=before['people'][1][15] or s.state['credits']>=before['credits']:
        raise RuntimeError('Paid clinic failed to heal injured Rex and charge the doctor')
    s.note('paid-healing-complete')
    count=counts[s.state['menu_id']];s.advance(['down']*((count-1-s.state['menu_selected'])%count)+['accept']);s.note('hospital-exit')
    (ROOT/'tests/fixtures/ordinary-hospital-healing.actions').write_text('\n'.join(s.actions)+'\n')
    (ROOT/'tests/fixtures/ordinary-hospital-healing.json').write_text(json.dumps(dict(
        prerequisite='Original DOS/GAME2 injured party imported normally; owner-authorized 10000-credit shortcut input',
        checkpoints=s.checkpoints,final=s.state),indent=2)+'\n')
    print('Saved paid hospital healing route:',len(s.actions),'ordinary inputs;',before['people'][1][15],'->',s.state['people'][1][15],'health, doctor cost',before['credits']-s.state['credits'])
if __name__=='__main__':main()
