#!/usr/bin/env python3
"""Original depth-boundary decisions, with the display call intercepted."""
import json
from combat_oracle import OriginalCombat,ROOT,UC_HOOK_CODE
from make_party_vectors import SNAP
from make_aftermath_vectors import span
from make_city_edge_vectors import span as paint_span
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
    # Real MAP13 cave/island over generated water. Let the original paint its
    # block into the appropriate neighbouring sector before it computes 1314
    # descriptors and applies exactly the same original depth decision.
    cave=(ROOT/'Original DOS/MAP13.MTP').read_bytes()
    island=[];m.reset();m.write(m.ds+0x4fc0,(0x020304).to_bytes(3,'little'))
    noise=bytes(m.call(0x187f,0xbc0)&255 for _ in range(256))
    for x in (-17,-16,-1,0,7,15,16):
        for y in (-17,-16,-1,0,7,15,16):
            for dx,dy in ((0,-1),(1,-1),(1,0),(1,1),(0,1),(-1,1),(-1,0),(-1,-1)):
                m.reset();warn.clear();wx,wy=768+x,768+y;sx,sy=wx//128,wy//128
                m.write(m.buffer+0x9fb,noise);m.call(0x187f,0x104e,16*sy+sx)
                m.write(m.buffer+0x101d,cave[541:])
                paint_span(m,0,0x3050,0x30bb,m.ds//16,
                    {6:4+(6-sx)+3*(6-sy),-12:0,-8:0,-2:cave[3]//8,-10:cave[4]//8})
                paint_span(m,0x187f,0x1886,0x18d7,m.buffer//16)
                px,py=(sx<<8)|(wx&127),(sy<<12)|(wy&127)
                m.call(0x187f,0x1314,px,py);m.word(m.buffer+0xa44b,px);m.word(m.buffer+0xa44d,py)
                span(m,0,0x1c24,0x1cc1,{6:dx,8:dy,-4:0})
                island.append(f'C {wx} {wy} {dx} {dy} {int(bool(warn))}')
    m.cpu.hook_del(h)
    (ROOT/'tests/fixtures/world-water-primary.txt').write_text('\n'.join(rows)+'\n')
    (ROOT/'tests/fixtures/world-island-water-primary.txt').write_text('\n'.join(island)+'\n')
    (ROOT/'tests/fixtures/world-water-primary.json').write_text(json.dumps(dict(
        executable_sha256=EXE_SHA,image_sha256=IMAGE_SHA,cases=len(rows),island_cases=len(island),
        routine='0000:1C24..1CC1; caller supplies signed direction and the nine descriptors from 187F:1314',
        intercepted_boundary='At 1CA1 stop before display-only popup calls; no instructions or decisions patched.',
        warning='DS:0410',comparison='Water rejection for eight directions, boundary/interior positions and six depth descriptors',
        island='Original MAP13 descriptor painting 0000:3050..30BB and 187F:1886, real generated seed 0x020304, 1314 descriptors and the original depth decision. The displayed land overrides the generated-water underlay.'),indent=2)+'\n')
    print('Primary water boundary cases:',len(rows),'real island cases:',len(island))
if __name__=='__main__':main()
