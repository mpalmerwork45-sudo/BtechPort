#!/usr/bin/env python3
"""Audit the current roster's movement dimensions against original instructions."""
import json
from combat_oracle import OriginalCombat, ROOT, STATE
from prepare_talk import EXE_SHA, IMAGE_SHA


def main():
    m=OriginalCombat()
    roster=json.loads((ROOT/'content/updated/roster.json').read_text())
    models=[('original-loan-'+str(i),m.template(i)[49],m.template(i)[50]) for i in range(3)]
    models += [(v['id'],v['walk'],v['jump']) for v in roster['mechs']]
    rows=['# Original 103B:22BC movement budget; walk jump mode heat left_leg right_leg expected.']
    for name,walk,jump in models:
        for mode in range(3):
            for heat in (0,5,10,20,29,30):
                for left,right in ((207,207),(199,207),(200,207),(0,0)):
                    m.reset();record=bytearray(m.template(0));record[49]=walk;record[50]=jump
                    record[36]=left;record[37]=right;m.write(STATE+0xc724,record);m.write(STATE+0x6e,[heat])
                    m.call(0x103b,0x22bc,0,mode)
                    rows.append('M '+' '.join(map(str,(walk,jump,mode,heat,left,right,m.word(STATE+0x3770)))))
    (ROOT/'tests/fixtures/extended-movement-primary.txt').write_text('\n'.join(rows)+'\n')
    (ROOT/'tests/fixtures/extended-movement-primary.json').write_text(json.dumps(dict(
        executable_sha256=EXE_SHA,image_sha256=IMAGE_SHA,cases=len(rows)-1,routine='103B:22BC',
        models=[dict(id=name,walk=walk,jump=jump) for name,walk,jump in models],
        prerequisites='Original loan record with each model\'s walk/jump bytes; three movement modes, six heat levels and four actuator states. No path/collision or time assumptions.',
        comparison='Original numeric movement allowance; the expanded models themselves are authored content, not original units.',
        no_instruction_patches=True),indent=2)+'\n')
    print(f'Original movement allowances: {len(rows)-1} cases across {len(models)} model dimensions')


if __name__=='__main__':main()
