#!/usr/bin/env python3
"""Execute the original BLD VM for clothing and electronics alternatives.

Input, text and panel calls are boundaries; the VM, flag/cash operations and
native party-count action execute unchanged. Only numeric results are saved.
"""
import hashlib,itertools,json
from audit_bld_flow import decrypt,graph
from combat_oracle import OriginalCombat,ROOT,UC_HOOK_CODE
from make_party_vectors import SNAP
from make_combat_vectors import fingerprint
from prepare_talk import EXE_SHA,IMAGE_SHA
from unicorn.x86_const import UC_X86_REG_SS,UC_X86_REG_SP,UC_X86_REG_BP,UC_X86_REG_CS,UC_X86_REG_IP,UC_X86_REG_AX


def main():
    m=OriginalCombat(snapshot=SNAP);rows=[];waits=[];menus=[];product=0;answer=1;visits=0
    boundaries={(0x1656,0x281),(0x1656,0x388),(0x1656,0x3f5),(0x1656,4),
        (0x1656,0xb5e),(0x173d,0x259),(0x173d,0x86a),(0,0x1a13),(0xe31,0x1fdf)}
    absolute={(m.load+s)*16+o:(s,o) for s,o in boundaries}
    def hook(cpu,at,size,data):
        nonlocal visits
        if at not in absolute:return
        ss=16*cpu.reg_read(UC_X86_REG_SS);sp=cpu.reg_read(UC_X86_REG_SP);where=absolute[at]
        if where==(0x173d,0x259):waits.append(m.word(ss+cpu.reg_read(UC_X86_REG_BP)-10))
        if where==(0,0x1a13):cpu.reg_write(UC_X86_REG_AX,answer)
        if where==(0x1656,0xb5e):
            menu=m.word(ss+sp+4)
            if menu in (29,35):
                choice=int(visits>0 or product==2);visits+=1
            elif menu==36:choice=product
            else:raise RuntimeError(f'Unexpected menu {menu}')
            menus.extend((menu,choice));cpu.reg_write(UC_X86_REG_AX,choice)
        off,seg=m.word(ss+sp),m.word(ss+sp+2)
        cpu.reg_write(UC_X86_REG_SP,sp+4);cpu.reg_write(UC_X86_REG_CS,seg);cpu.reg_write(UC_X86_REG_IP,off)
    handle=m.cpu.hook_add(UC_HOOK_CODE,hook)
    for kind,name in ((12,'CLOTHES'),(17,'FROB')):
        script=decrypt((ROOT/f'Original DOS/{name}.BLD').read_bytes())
        if kind==12:
            cases=((n,cash,bought,spy,0,0,0,p,1) for n,cash,bought,spy,p in itertools.product((1,5),(0,34,35,36),range(2),range(2),(0,2)))
        else:
            cases=((n,cash,0,0,v,mapper,viewed,p,yes) for n,cash,v,mapper,viewed,p,yes in itertools.product((1,2,5),(0,5999,6000,6999,7000,20000),range(2),range(2),range(2),range(3),range(2)))
        for n,cash,bought,spy,viewer,mapper,viewed,product,answer in cases:
            m.reset();visits=0;waits.clear();menus.clear();m.write(m.state+0xa0,script)
            flags=bytearray(80);flags[4]=1;flags[30]=bought;flags[39]=spy;flags[48:51]=bytes((viewer,mapper,viewed))
            m.write(m.state+0xd30c,flags);m.write(m.state+0xd370,cash.to_bytes(4,'little'))
            m.word(m.state+0x4584,kind)
            m.write(m.state+0xc614,bytes(v for i in range(8) for v in [i if i<n else 255]+[0]*16))
            m.call(0x7dc,0x1c0,0xa0,m.state//16,limit=300000)
            final=m.read(m.state+0xd30c,80);money=int.from_bytes(m.read(m.state+0xd370,4),'little')
            observed=[final[i] for i in (14,30,36,39,48,49,50)]
            hashes=(fingerprint(bytes(menus)),fingerprint(b''.join(pc.to_bytes(2,'little') for pc in waits)))
            rows.append('S '+' '.join(map(str,(kind,n,cash,bought,spy,viewer,mapper,viewed,product,answer,money,*observed,len(waits))))+f' {hashes[0]:016x} {hashes[1]:016x}')
    m.cpu.hook_del(handle)
    audit=[]
    for path in sorted((ROOT/'Original DOS').glob('*.BLD')):
        nodes=graph(decrypt(path.read_bytes()))
        audit.append(dict(file=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),reachable_nodes=len(nodes),
            native_actions=sorted({int(v['operands'][:2],16) for v in nodes.values() if v['op']=='f5'})))
    (ROOT/'tests/fixtures/alternate-services-primary.txt').write_text('\n'.join(rows)+'\n')
    (ROOT/'tests/fixtures/alternate-services-primary.json').write_text(json.dumps(dict(
        executable_sha256=EXE_SHA,image_sha256=IMAGE_SHA,cases=len(rows),routine='07DC:01C0 original BLD VM, including native actions 10 and 14',
        prerequisites='CLOTHES/FROB supplied as decoded original payloads; explicit cash, party size, purchase/spy/viewer/mapper/viewed flags and menu/yes-no answers. Repeated root menus leave after one transaction.',
        boundaries=sorted(f'{s:04X}:{o:04X}' for s,o in boundaries),
        comparison='Final money/branch flags, ordered menu choices and held-page PC sequence hashes. No original screen/pacing claim. All BLD graphs are a static audit, not execution coverage.',
        bld_graph_audit=audit,no_instruction_patches=True),indent=2)+'\n')
    print('Original alternate service cases:',len(rows),'; BLD graphs:',len(audit))


if __name__=='__main__':main()
