#!/usr/bin/env python3
"""Original depth-boundary decisions, with the display call intercepted."""
import json
from combat_oracle import OriginalCombat,ROOT,UC_HOOK_CODE
from make_party_vectors import SNAP
from make_aftermath_vectors import span
from prepare_talk import EXE_SHA,IMAGE_SHA
from unicorn.x86_const import UC_X86_REG_IP

def main():
    m=OriginalCombat(snapshot=SNAP);rows=[];warn=[]
    def popup(cpu,address,size,data):
        if address==m.load*16+0x1ca1:
            warn.append(1);cpu.reg_write(UC_X86_REG_IP,0x1cc1)
    h=m.cpu.hook_add(UC_HOOK_CODE,popup)
    for x in (0,7,15):
        for y in (0,7,15):
            for dx,dy in ((0,-1),(1,-1),(1,0),(1,1),(0,1),(-1,1),(-1,0),(-1,-1)):
                for descriptor in (0,14,15,16,31,144):
                    m.reset();warn.clear();m.word(m.buffer+0xa44b,0xc00+x);m.word(m.buffer+0xa44d,0xc000+y)
                    m.write(m.buffer+0x7a4,bytes([descriptor])*9)
                    span(m,0,0x1c24,0x1cc1,{6:dx,8:dy,-4:0})
                    rows.append(f'W {x} {y} {dx} {dy} {descriptor} {int(bool(warn))}')
    m.cpu.hook_del(h)
    (ROOT/'tests/fixtures/world-water-primary.txt').write_text('\n'.join(rows)+'\n')
    (ROOT/'tests/fixtures/world-water-primary.json').write_text(json.dumps(dict(
        executable_sha256=EXE_SHA,image_sha256=IMAGE_SHA,cases=len(rows),
        routine='0000:1C24..1CC1; caller supplies signed direction and the nine descriptors from 187F:1314',
        intercepted_boundary='At 1CA1 stop before display-only popup calls; no instructions or decisions patched.',
        warning='DS:0410',comparison='Water rejection for eight directions, boundary/interior positions and six depth descriptors'),indent=2)+'\n')
    print('Primary water boundary cases:',len(rows))
if __name__=='__main__':main()
