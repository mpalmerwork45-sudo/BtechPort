#!/usr/bin/env python3
"""Execute the original mech viewer and record numeric presentation projections.

The real 05AB:1AFE body, component/bar helpers and text selection execute.
Only graphics/device boundaries are intercepted. Owner text and screenshots
are not written into the fixture; fonts come directly from the audited EXE.
"""
import json
from combat_oracle import OriginalCombat,ROOT,UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_CS,UC_X86_REG_IP,UC_X86_REG_SP,UC_X86_REG_SS
from prepare_talk import FONT,EXE_SHA,IMAGE_SHA
from make_party_vectors import SNAP

PALETTE=(0x000000,0x0000aa,0x00aa00,0x00aaaa,0xaa0000,0xaa00aa,0xaa5500,0xaaaaaa,
         0x555555,0x5555ff,0x55ff55,0x55ffff,0xff5555,0xff55ff,0xffff55,0xffffff)

def prerequisite(record,variant):
    m=bytearray(record)
    if variant:
        m[117:120]=bytes((1,1,1) if variant==1 else (3,2,2))
        m[36:38]=bytes((0x8c,0) if variant==1 else (0,0))
        for i in range(51,86):
            if m[i]==34:m[i]|=128
        if variant==1:m[51]|=128
        else:m[17:28]=bytes(11);m[28:36]=bytes([1])*8;m[38]=0
    return m

def observe(machine,record,people,heat):
    m=machine;m.reset();m.word(m.state+0x4594,1)
    m.write(m.state+0xc724,record);m.write(m.state+0xc614,people)
    m.write(m.state+0x6e,bytes([heat]));m.word(m.ds+0x1218,0);m.word(m.ds+0x121c,0)
    draws=[];stopped=[]
    targets={0x173d0+0xd5:'text',0x173d0+0x1fb:'fill',0x173d0+0x31c:'rect',
        0x187f0+0x275c:'tile',0x173d0+0x49d:'background',0x187f0+0xd1:'free',
        0x187f0+0x245c:'copy',0x173d0+0x86a:'flush',0x173d0+0x525:'cursor',
        0x187f0+0x260:'vga-copy',0x173d0+6:'wait',0x28cc:'layout',0x173d0+0x6c3:'border'}
    def hook(cpu,address,size,data):
        relative=address-m.load*16
        if relative==0x7d1c:stopped.append(True);cpu.emu_stop();return
        if relative not in targets:return
        ss=cpu.reg_read(UC_X86_REG_SS)*16;sp=cpu.reg_read(UC_X86_REG_SP);kind=targets[relative]
        args=[m.word(ss+sp+4+2*i) for i in range(6)]
        if kind=='text':
            at=args[1]*16+args[0];value=bytearray()
            for i in range(512):
                c=m.read(at+i,1)[0]
                if not c:break
                value.append(c)
            else:raise ValueError('Unterminated primary viewer text')
            draws.append((kind,args[2:6],bytes(value)))
        elif kind=='fill':draws.append((kind,args[:5],None))
        off,seg=m.word(ss+sp),m.word(ss+sp+2)
        cpu.reg_write(UC_X86_REG_SP,sp+4);cpu.reg_write(UC_X86_REG_CS,seg);cpu.reg_write(UC_X86_REG_IP,off)
    handle=m.cpu.hook_add(UC_HOOK_CODE,hook)
    try:
        try:m.call(0x5ab,0x1afe,0,limit=100000)
        except RuntimeError:
            if not stopped:raise
        if not stopped:raise RuntimeError('Viewer did not reach bounded first-frame endpoint')
    finally:m.cpu.hook_del(handle)
    font=m.image[FONT:FONT+2048];left=[0]*(128*200);fills=[]
    for kind,args,value in draws:
        if kind=='fill':
            fills.append(args)
            x0,y0,x1,y1,color=args
            for y in range(max(0,y0),min(199,y1)+1):
                for x in range(max(0,x0),min(127,x1)+1):left[y*128+x]=PALETTE[color]
        else:
            col,row,color,background=args;start=col
            for c in value:
                if c==13:col=start;row+=1;continue
                for y in range(8):
                    for x in range(8):
                        px,py=8*col+x,8*row+y
                        if 0<=px<128 and 0<=py<200:
                            left[py*128+px]=PALETTE[color if font[8*c+y]&(128>>x) else background]
                col+=1
    h=0xcbf29ce484222325
    for pixel in left:
        for shift in (16,8,0):h=((h^((pixel>>shift)&255))*0x100000001b3)&0xffffffffffffffff
    return h,fills

def main():
    m=OriginalCombat(snapshot=SNAP);rows=['# Executed 05AB:1AFE first frame: left RGB FNV and inclusive rectangle calls.']
    for slot in range(1,7):
        b=(ROOT/f'Original DOS/GAME{slot}').read_bytes();record=bytearray(b[0x111:0x111+125])
        if record[0]==255:record[0]=b[0xe3f] # Explicitly activate the stored record for the viewer caller.
        for variant in range(3):
            heat=(0,12,30)[variant];left,fills=observe(m,prerequisite(record,variant),b[1:137],heat)
            rows.append(f'V {slot} {variant} {heat} {left:016x} {len(fills)} '+' '.join(str(v) for a in fills for v in a))
    (ROOT/'tests/fixtures/mech-view-primary.txt').write_text('\n'.join(rows)+'\n')
    (ROOT/'tests/fixtures/mech-view-primary.json').write_text(json.dumps(dict(
        executable_sha256=EXE_SHA,image_sha256=IMAGE_SHA,body='05AB:1AFE..225F',
        helpers=['05AB:164C','05AB:1858'],cases=18,prerequisites='GAME1..6 first owned record, activated stored kind when needed; explicit damage and heat variants',
        comparison='Full left 128x200 RGB projection from original text/rectangle calls and all filled pixels; bitmap and hardware calls intercepted, not a full DOS screenshot'),indent=2)+'\n')
    print('Primary mech-view cases:',len(rows)-1)
if __name__=='__main__':main()
