#!/usr/bin/env python3
"""Hash live DOS victory/loot panels; proprietary frames remain in work/."""
import hashlib,json
from pathlib import Path
from PIL import Image
from prepare_talk import EXE_SHA,IMAGE_SHA
ROOT=Path(__file__).resolve().parents[1]
RUN=ROOT/'work/reference-runs/1791877416552610064'
def main():
    rows=[];cases=[]
    for phase,label in ((5,'victory-17'),(8,'victory-18'),(9,'victory-19'),(3,'victory-20'),(4,'loot-0')):
        pixels=Image.open(RUN/'captures'/f'{label}.png').convert('RGB').crop((104,112,320,200)).tobytes()
        value=0xcbf29ce484222325
        for b in pixels:value=((value^b)*0x100000001b3)&0xffffffffffffffff
        rows.append(f'P {phase} {value:016x}')
        cases.append(dict(phase=phase,capture=label,rgb_sha256=hashlib.sha256(pixels).hexdigest()))
    (ROOT/'tests/fixtures/aftermath-ui-primary.txt').write_text('\n'.join(rows)+'\n')
    (ROOT/'tests/fixtures/aftermath-ui-primary.json').write_text(json.dumps(dict(
        executable_sha256=EXE_SHA,image_sha256=IMAGE_SHA,snapshot=str(RUN.relative_to(ROOT)),
        comparison='Every RGB pixel of the 216x88 lower-right panel, including border, scroll, colours and selection.',
        prerequisite='Private GAME3 copy with active owned vehicles; live DOS computer-controlled fight. Rex technician rank 2, one enemy mech wreck, 216 scrap C-bills, 71 pocket C-bills (287 total credit delta); loot recipient row 3 and original four personal weapons.',
        routines=['103B:10A3..12F9','05AB:0002','05AB:094B'],cases=cases),indent=2)+'\n')
    print('Original victory/loot panels:',len(cases))
if __name__=='__main__':main()
