#!/usr/bin/env python3
"""Report original LRM to-hit requirements at explicit close/medium distances."""
import json
from combat_oracle import OriginalCombat, ROOT
from prepare_talk import EXE_SHA, IMAGE_SHA


def main():
    m=OriginalCombat();samples=[]
    for weapon in range(25,29):
        for target_x in (66,68,76,86,106,120):
            shot=m.shot(weapon,-1,0,0,0,6,0,0,123456,target_x=target_x)
            samples.append(dict(weapon=weapon,attacker=[64,64],target=[target_x,64],needed=shot['needed']))
    result=dict(executable_sha256=EXE_SHA,image_sha256=IMAGE_SHA,
        routine='12E8:0239..0CD3 original attack span via OriginalCombat.shot; original 0E31:0F24 range routine',
        prerequisites='Intact original loan record with one selected LRM; stationary, zero heat/skill/target movement/cover, facing 6, seed 123456; target remains a mech.',
        limits='Controlled hit requirement, not whole campaign tactics or tabletop rules. This call assumes visibility and attack admission have already succeeded.',
        samples=samples,no_instruction_patches=True)
    destination=ROOT/'work/weapon-presentation/lrm-rules.json';destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
