#!/usr/bin/env python3
"""Complete original Mechit-Lube services and measured live UI regions.

No instructions are patched. Graphics/key input are explicit far-call
boundaries; all repair, estimate, reload and money instructions execute.
Only numeric observations and hashes are committed. Captures stay in work/.
"""
import argparse
import json
import struct
from pathlib import Path
from combat_oracle import OriginalCombat, ROOT, UC_HOOK_CODE
from make_party_vectors import fingerprint
from prepare_talk import EXE_SHA, IMAGE_SHA
from unicorn.x86_const import (UC_X86_REG_AX, UC_X86_REG_DX, UC_X86_REG_CS,
                              UC_X86_REG_IP, UC_X86_REG_SP, UC_X86_REG_SS)

REPAIR_RUN = ROOT/'work/reference-runs/1791863873862567602'
SERVICE_RUN = ROOT/'work/reference-runs/1791864147791493161'
APPRENTICE_RUN = ROOT/'work/reference-runs/1791865266664660305'
RECRUIT_RUN = ROOT/'work/reference-runs/1791865285111355132'
GYRO_RUN = ROOT/'work/reference-runs/1791876402969678147'


def record(loan, shape):
    raw=(ROOT/'Original DOS/GAME3').read_bytes()
    b=bytearray(raw[0x111+125*loan:0x111+125*(loan+1)])
    if b[0]==255:b[0]=raw[1+0xd452-0xc614+loan]
    if shape==0:
        b[17]=max(0,b[86]-3);b[28]=max(0,b[97]-2)
        for first,last,w in ((51,86,None),(51,86,34)):
            for i in range(first,last):
                if (16<=b[i]<=32) if w is None else b[i]==w:
                    b[i]|=128;break
        b[36]=max(0,b[105]-1)
        for i in range(39,49):
            if b[i]!=255:b[i]=0
    else:
        b[17:38]=b[86:107];b[51:86]=bytes(35)
        if shape==1:
            b[51]=b[52]=145;b[65]=146;b[58]=162
        elif shape==2:
            b[51]=b[52]=160  # original SRM6 estimate's final-index edge case
        elif shape<7:
            b[51]=24;b[52]=31;b[65]=17;b[79]=24
            b[39:49]=bytes([0,0,255,0,255,255,255,255,255,255])
            b[107:117]=bytes([5,3,255,5,255,255,255,255,255,255])
            if shape==4:b[65]|=128
            if shape==5:b[51]|=128
            if shape==6:b[79]|=128
        else:
            b[117:120]=bytes(3)
            if shape<10:b[117+shape-7]=1
    return b


def numeric():
    m=OriginalCombat(snapshot=REPAIR_RUN/'repair-menu')
    boundaries={(0x1656,0x388),(0x1656,0x3f5),(0x1656,0xb5e),
        (0x173d,0x53),(0x173d,0x259),(0,0x1a13),(0,0x28a2),
        (0xe31,0x1fdf),(0xc67,0xb98),(0x14d3,4),
        (0x14d3,0x17ea),(0x14d3,0x1809),(0x14d3,0x181e),(0xd43,0xcde)}
    absolute={(m.load+s)*16+o:(s,o) for s,o in boundaries}
    policy=request=0;questions=menus=0
    def hook(cpu,address,size,data):
        nonlocal questions,menus
        if address not in absolute:return
        call=absolute[address];sp=cpu.reg_read(UC_X86_REG_SP);ss=cpu.reg_read(UC_X86_REG_SS)*16
        off,seg=struct.unpack('<HH',m.read(ss+sp,4))
        if call==(0xc67,0xb98):m.word(m.state+0x68,0);cpu.reg_write(UC_X86_REG_AX,0)
        if call==(0,0x1a13):
            category={0x278:0,0x3a2:1,0x4ce:2,0x7a0:4}.get(off)
            yes=policy!=1 and not (policy==2 and category==0) and not (policy==4 and category==2)
            cpu.reg_write(UC_X86_REG_AX,int(yes));questions+=1
        if call==(0x1656,0xb5e):
            table=m.word(m.ds+0x54bc)*16
            count=m.word(table+0x206)
            cpu.reg_write(UC_X86_REG_AX,count-1 if policy in (1,3) else 0);menus+=1
            if menus>40:raise RuntimeError('Original estimate failed to finish')
        if call==(0xd43,0xcde):
            cpu.reg_write(UC_X86_REG_AX,request);cpu.reg_write(UC_X86_REG_DX,0)
        cpu.reg_write(UC_X86_REG_SP,sp+4);cpu.reg_write(UC_X86_REG_CS,seg);cpu.reg_write(UC_X86_REG_IP,off)
    handle=m.cpu.hook_add(UC_HOOK_CODE,hook);rows=[]
    for loan in range(3):
        for shape in range(3):
            for funds in (0,3,12,300,800,1100,50000):
                for policy in range(5):
                    m.reset();questions=menus=0;m.write(m.state+0xc724,record(loan,shape))
                    m.write(m.state+0xd370,funds.to_bytes(4,'little'));m.call(0x9b8,2,limit=2000000)
                    cash=int.from_bytes(m.read(m.state+0xd370,4),'little')
                    rows.append(f'P {loan} {shape} {funds} {policy} {cash} {questions} {menus} {fingerprint(m.read(m.state+0xc724,125))}')
        for shape in range(3,7):
            for funds in (0,1,2,3,7,20,1000):
                for request in (0,3,999):
                    m.reset();questions=menus=0;m.write(m.state+0xc724,record(loan,shape))
                    m.write(m.state+0xd370,funds.to_bytes(4,'little'));m.call(0x9b8,0x1762,limit=2000000)
                    cash=int.from_bytes(m.read(m.state+0xd370,4),'little')
                    rows.append(f'A {loan} {shape} {funds} {request} {cash} 0 0 {fingerprint(m.read(m.state+0xc724,125))}')
        for shape in range(7,11):
            for funds in (0,50000):
                m.reset();policy=0;questions=menus=0;m.write(m.state+0xc724,record(loan,shape))
                m.write(m.state+0xd370,funds.to_bytes(4,'little'));m.call(0x9b8,2,limit=2000000)
                cash=int.from_bytes(m.read(m.state+0xd370,4),'little')
                rows.append(f'P {loan} {shape} {funds} 0 {cash} {questions} {menus} {fingerprint(m.read(m.state+0xc724,125))}')
    m.cpu.hook_del(handle)
    (ROOT/'tests/fixtures/mechit-primary.txt').write_text('\n'.join(rows)+'\n')
    (ROOT/'tests/fixtures/mechit-primary.json').write_text(json.dumps(dict(
        executable_sha256=EXE_SHA,image_sha256=IMAGE_SHA,cases=len(rows),
        routines=['09B8:0002, complete repair service','09B8:1762, complete ammunition service'],
        snapshot=str(REPAIR_RUN.relative_to(ROOT)/'repair-menu'),
        prerequisites='GAME3 records, active tags restored; three damage shapes, seven balances, five refusal policies. Ammo: working guns, unrelated broken laser, broken first/last gun; zero, three or excessive quantity.',
        intercepted_boundaries=sorted(f'{s:04X}:{o:04X}' for s,o in boundaries),
        comparison='Final 125-byte mech hash, credits, repair confirmations and weapon estimate visits. Graphics/keyboard boundaries are declared; all service instructions execute.'),indent=2)+'\n')
    print('Complete original Mechit-Lube service cases:',len(rows))


def ui():
    from PIL import Image
    rows=[];metadata=[]
    base=['up','accept','down','down','accept']
    cases=[('repair',REPAIR_RUN,'repair-selection',base),
           ('repair',REPAIR_RUN,'repair-components',base+['accept'])]
    cases.extend(('repair',REPAIR_RUN,f'repair-step-{i}',base+['accept']*(i+1)) for i in range(1,7))
    a=['up','accept','down','down','down','accept']
    cases.extend([('repair',SERVICE_RUN,'ammo-real-choice',a),('repair',SERVICE_RUN,'ammo-prompt',a+['accept']),
                  ('repair',SERVICE_RUN,'ammo-clamp',a+['accept','9','9','9','accept'])])
    a=['up','accept']
    for name,keys in [('apprentice-character',['accept']),('apprentice-price',['accept']),
        ('apprentice-decline',['right','accept']),('apprentice-paid',['accept']*4),
        ('speed-description',['accept','down','accept']),('speed-services',['accept']),
        ('speed-list',['accept']),('speed-stock-offer',['down','accept']),('speed-purchased',['accept'])]:
        a+=keys;cases.append(('apprentice',APPRENTICE_RUN,name,a.copy()))
    # The live joining record is fixed by the original name-derived seed;
    # its held page is unaffected by the number of presentation ticks.
    cases.append(('recruit',RECRUIT_RUN,'recruit-agent',['up','accept','accept','accept']+['idle']*96))
    cases.extend([('gyro',GYRO_RUN,'gyro-selection',base),
                  ('gyro',GYRO_RUN,'gyro-result',base+['down','down','accept'])])
    for i,(kind,run,name,actions) in enumerate(cases):
        image=Image.open(run/'captures'/f'{name}.png').convert('RGB')
        right=fingerprint(image.crop((104,0,320,200)).tobytes())
        footer=fingerprint(image.crop((0,100,104,200)).tobytes())
        rows.append(f'U {i} {kind} {right} {footer} '+','.join(actions))
        metadata.append(dict(index=i,label=name,run=str(run.relative_to(ROOT)),right=right,footer=footer,
                             screenshot_sha256=__import__('hashlib').sha256((run/'captures'/f'{name}.png').read_bytes()).hexdigest()))
    (ROOT/'tests/fixtures/mechit-ui-primary.txt').write_text('\n'.join(rows)+'\n')
    (ROOT/'tests/fixtures/mechit-ui-primary.json').write_text(json.dumps(dict(
        executable_sha256=EXE_SHA,image_sha256=IMAGE_SHA,regions=metadata,
        prerequisites='Private GAME3 copies at the Mechit-Lube door. People on foot, active vehicle tags; defined damage. Apprenticeship clears Jason\'s learned bit and Commando refit bit; recruitment uses parked flag 24 and the actual Rex/no-skilled-technician gate. Gyro case restores all repairable systems and sets byte 118 of the last listed mech to one.',
        comparison='Complete 216x200 right dialog and 104x100 party footer. Original animated portraits are outside these regions; the held recruitment frame also matches all 320x200 pixels.'),indent=2)+'\n')
    print('Original Mechit-Lube screen pairs:',len(rows))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--ui-only',action='store_true');args=parser.parse_args()
    if not args.ui_only:numeric()
    ui()
