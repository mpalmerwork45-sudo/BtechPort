#!/usr/bin/env python3
"""Hash three live original salvage result panels, including their borders."""
import hashlib,json
from PIL import Image
from combat_oracle import ROOT
from prepare_talk import EXE_SHA,IMAGE_SHA

def main():
    rows=[];sources=[]
    for notice,run,label in ((0,'1792123964150497153','salvage-live-result'),
        (1,'1792124535589537852','salvage-confirmed-failure'),(2,'1792124535589537852','salvage-confirmed-none')):
        source=ROOT/'work/reference-runs'/run/'captures'/f'{label}.png'
        im=Image.open(source).convert('RGB');assert im.size==(320,200)
        rgb=im.crop((104,112,320,200)).tobytes();h=0xcbf29ce484222325
        for b in rgb:h=((h^b)*0x100000001b3)&0xffffffffffffffff
        rows.append(f'L {notice} {h:016x}');sources.append(dict(notice=notice,run=run,label=label,rgb_sha256=hashlib.sha256(rgb).hexdigest()))
    (ROOT/'tests/fixtures/salvage-live-primary.txt').write_text('\n'.join(rows)+'\n')
    (ROOT/'tests/fixtures/salvage-live-primary.json').write_text(json.dumps(dict(executable_sha256=EXE_SHA,image_sha256=IMAGE_SHA,
        cases=sources,comparison='All 216x88 lower-right panel pixels, border and original success/failure/no-wreck text.',
        prerequisites='Supplied GAME3 party, controlled next-encounter mask/RNG and Rick on foot with pilot rank 3 and technician rank 4 (success) or 3 (failure). Ordinary movement and complete manual waves with four Computer assignments. At the held failure offer, the actual enemy Wasp wreck engine is set to destroyed (3). Audit bytes and all RAM/captures remain in work.',
        limits='Controlled presentation contexts, not natural acquisition of these ranks. Captures from the incomplete first failure attempt are excluded.',no_instruction_patches=True),indent=2)+'\n')
    print('Live original salvage panels:',len(rows))
if __name__=='__main__':main()
