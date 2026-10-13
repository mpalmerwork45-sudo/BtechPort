#!/usr/bin/env python3
"""Execute the original Phoenix decoder and VGA palette writes in private RAM."""
import hashlib
import json
from combat_oracle import OriginalCombat, ROOT, UC_HOOK_INSN, UC_X86_INS_OUT
from make_party_vectors import SNAP
from prepare_talk import EXE_SHA, IMAGE_SHA

EGA=(0x000000,0x0000aa,0x00aa00,0x00aaaa,0xaa0000,0xaa00aa,0xaa5500,0xaaaaaa,
     0x555555,0x5555ff,0x55ff55,0x55ffff,0xff5555,0xff55ff,0xffff55,0xffffff)


def palette(m,segment):
    m.reset();writes=[]
    def output(cpu,port,size,value,data):
        if port==0x3c0:writes.append(value)
    handle=m.cpu.hook_add(UC_HOOK_INSN,output,None,1,0,UC_X86_INS_OUT)
    try:m.call(0x173d,0x525,0,m.load+segment)
    finally:m.cpu.hook_del(handle)
    if len(writes)!=48 or any(writes[3*i]!=i or writes[3*i+2]!=32 for i in range(16)):
        raise RuntimeError('Unexpected original VGA attribute-controller sequence')
    registers=writes[1::3]
    if any(value not in range(8) and value not in range(16,24) for value in registers):
        raise RuntimeError('Palette is outside the audited EGA colour subset')
    return registers,[EGA[value if value<8 else value-8] for value in registers]


def main():
    m=OriginalCombat(snapshot=SNAP)
    title_registers,title=palette(m,0x27e8)
    control=json.loads((ROOT/'tests/fixtures/title-palette.json').read_text())
    if title!=[r<<16|g<<8|b for r,g,b in control['palette_rgb']]:
        raise RuntimeError('VGA colour model differs from the captured title control')
    registers,colours=palette(m,0x2858)
    source=(ROOT/'Original DOS/ENDMECH.CMP').read_bytes()
    m.reset()
    # Original file reader consumes the two-byte size before this boundary.
    m.write(m.state+0x4614,source[2:])
    m.call(0x173d,0x49d,0x4614,m.state//16,0x244b,m.buffer//16,limit=500000)
    packed=m.read(m.buffer+0x244b,32000)
    rgb=bytes(channel for value in packed for index in (value>>4,value&15)
              for channel in colours[index].to_bytes(3,'big'))
    h=14695981039346656037
    for value in rgb:h=((h^value)*1099511628211)&((1<<64)-1)
    (ROOT/'tests/fixtures/phoenix-palette-primary.txt').write_text(f'F {h:016x}\n')
    facts=dict(executable_sha256=EXE_SHA,image_sha256=IMAGE_SHA,
        resource_sha256=hashlib.sha256(source).hexdigest(),
        caller='14D3:15DD..16A6 selects ENDMECH.CMP and palette 2858:0000',
        executed=['173D:049D original CMP decode','173D:0525 and 187F:022A original VGA palette writes'],
        title_control_registers=title_registers,phoenix_registers=registers,
        phoenix_rgb=[f'{c:06x}' for c in colours],
        unpacked_sha256=hashlib.sha256(packed).hexdigest(),
        rgb_sha256=hashlib.sha256(rgb).hexdigest(),rgb_fnv64=f'{h:016x}',
        confidence='VERIFIED original decoder and palette registers; RGB uses the VGA/EGA colour model checked against the live title capture.',
        limits='This is not a live DOSBox Phoenix screenshot or an execution of the entire cache journey.',
        no_instruction_patches=True)
    (ROOT/'tests/fixtures/phoenix-palette-primary.json').write_text(json.dumps(facts,indent=2)+'\n')
    print('Original Phoenix: 32000 decoded bytes, 16 palette writes, RGB FNV64',f'{h:016x}')


if __name__=='__main__':main()
