#!/usr/bin/env python3
"""Execute original weapon-entry gates with explicit heat/sensor/order inputs.

Display and keyboard waits are observed boundaries; all gate, control-flag and
order writes execute unchanged. Stop before the full weapon list on allowed
paths. This is a controlled routine comparison, not a played combat round.
"""
import json
import struct
import hashlib
from PIL import Image
from combat_oracle import OriginalCombat, ROOT, UC_HOOK_CODE
from make_party_vectors import SNAP
from prepare_talk import EXE_SHA, IMAGE_SHA
from unicorn.x86_const import UC_X86_REG_CS, UC_X86_REG_IP, UC_X86_REG_SS, UC_X86_REG_SP


def main():
    m=OriginalCombat(snapshot=SNAP);messages=[];waits=[];opened=[]
    boundaries={(0x1656,0x281),(0x1656,4),(0x1656,0x388),(0x1656,0x3f5),(0x173d,0x259),(0,0x2a4f)}
    addresses={(m.load+s)*16+o:(s,o) for s,o in boundaries}
    def hook(cpu,address,size,data):
        if address==m.load*16+0xd581:
            opened.append(1);cpu.reg_write(UC_X86_REG_CS,0x6000);cpu.reg_write(UC_X86_REG_IP,0);return
        if address not in addresses:return
        where=addresses[address];sp=cpu.reg_read(UC_X86_REG_SP);ss=cpu.reg_read(UC_X86_REG_SS)*16
        if where==(0x1656,0x3f5):messages.append(m.word(ss+sp+4))
        if where in ((0x173d,0x259),(0,0x2a4f)):waits.append(where)
        off,seg=struct.unpack('<HH',m.read(ss+sp,4))
        cpu.reg_write(UC_X86_REG_SP,sp+4);cpu.reg_write(UC_X86_REG_CS,seg);cpu.reg_write(UC_X86_REG_IP,off)
    m.cpu.hook_add(UC_HOOK_CODE,hook);rows=[]
    orders=bytes([12,13,255,255,255,255,255,255,255,255,255,12])
    for actor in range(4):
        for heat in (0,29,30):
            for sensors in range(3):
                m.reset();messages.clear();waits.clear();opened.clear()
                mech=bytearray(m.template());mech[119]=sensors
                m.write(m.state+0xc724+125*actor,mech);m.write(m.state+0x6e+actor,[heat])
                m.write(m.state+0x3994+actor,[1]);m.write(m.state+0x3800+12*actor,orders)
                m.call(0xd43,4,actor)
                after=m.read(m.state+0x3800+12*actor,12)
                disabled=sum(1<<i for i,(a,b) in enumerate(zip(orders,after)) if a!=255 and b&128)
                # The port stores target IDs and fired bits separately.
                if bytes(b if b==255 else b&127 for b in after)!=orders:
                    raise RuntimeError('Gate unexpectedly replaced a target')
                rows.append('G '+' '.join(map(str,[actor,heat,sensors,len(opened),m.read(m.state+0x3994+actor,1)[0],
                    disabled,len(waits),len(messages),*messages])))
    (ROOT/'tests/fixtures/weapon-warnings-primary.txt').write_text('\n'.join(rows)+'\n')
    (ROOT/'tests/fixtures/weapon-warnings-primary.json').write_text(json.dumps(dict(
        executable_sha256=EXE_SHA,image_sha256=IMAGE_SHA,cases=len(rows),routine='0D43:0004',
        prerequisites='Four actor slots; heat 0/29/30, sensors 0/1/2; automatic flag set; targets 12/13 and a kick at 12.',
        intercepted_boundaries=[f'{s:04X}:{o:04X}' for s,o in sorted(boundaries)],
        stop='Image D581 before weapon-window construction; other paths reach the original far return.',
        comparison='Text pointers, key waits, open/refuse, cleared automatic flag, retained targets and disabled-order bits.'),indent=2)+'\n')
    print('Original weapon-entry cases:',len(rows))
    capture=ROOT/'work/reference-runs/1791961683091068424'
    labels=('damaged-sensors','damaged-sensors-after','destroyed-sensors','destroyed-sensors-after',
            'shutdown','shutdown-after','normal-after-shutdown')
    rows=[];cases=[]
    for i,label in enumerate(labels):
        frame=Image.open(capture/'captures'/f'{label}.png').convert('RGB')
        if frame.size!=(320,200):raise ValueError('Expected original 320x200 capture')
        regions=[(0,0,104,200)]
        if i in (1,6):regions.append((104,96,216,104))
        for x,y,w,h in regions:
            rgb=frame.crop((x,y,x+w,y+h)).tobytes();value=0xcbf29ce484222325
            for b in rgb:value=((value^b)*0x100000001b3)&0xffffffffffffffff
            rows.append(f'W {i} {x} {y} {w} {h} {value:016x}')
            cases.append(dict(case=i,label=label,bounds=[x,y,w,h],rgb_sha256=hashlib.sha256(rgb).hexdigest()))
    (ROOT/'tests/fixtures/weapon-warning-ui-primary.txt').write_text('\n'.join(rows)+'\n')
    (ROOT/'tests/fixtures/weapon-warning-ui-primary.json').write_text(json.dumps(dict(
        executable_sha256=EXE_SHA,image_sha256=IMAGE_SHA,capture_run=capture.name,cases=cases,
        prerequisites='Private GAME3 copy retains three active vehicles, fourth person on foot. '
            'Ordinary encounter and assignment of weapon 0 to ID13. controlled-weapon-warning changes only '
            'actor 0 heat/sensors between pages; original instructions and order writes remain unchanged.',
        comparison='Seven held pages, complete unmasked left panels and two weapon-list crops; '
            'no claim of battlefield equality. Original order 13 becomes 141 after shutdown acknowledgement '
            'and returns to 13 when the normal weapon list is reopened.'),indent=2)+'\n')
    print('Original weapon warning regions:',len(rows))


if __name__=='__main__':main()
