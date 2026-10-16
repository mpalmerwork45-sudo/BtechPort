#!/usr/bin/env python3
"""Execute complete original inventor, house and cinema BLD branches.

Only presentation/input boundaries are supplied. Record numeric final state,
ordered waits/menu choices and requested sound/animation events. Original
bytecode, skill checks, payments and native actions execute unchanged.
"""
import itertools,json
from audit_bld_flow import decrypt,graph
from combat_oracle import OriginalCombat,ROOT,UC_HOOK_CODE
from make_party_vectors import SNAP
from make_combat_vectors import fingerprint
from prepare_talk import EXE_SHA,IMAGE_SHA
from unicorn.x86_const import UC_X86_REG_SS,UC_X86_REG_SP,UC_X86_REG_BP,UC_X86_REG_CS,UC_X86_REG_IP,UC_X86_REG_AX

def main():
    m=OriginalCombat(snapshot=SNAP);rows=[];waits=[];menus=[];events=[];visits=0;seen={};kind=0
    boundaries={(0x1656,0x281),(0x1656,0x388),(0x1656,0x3f5),(0x1656,4),(0x1656,0xb5e),
                (0x173d,0x259),(0x173d,0x86a),(0,0x1a13),(0xe31,0x1fdf),(0,0x48b7),(0,0x19bf)}
    absolute={(m.load+s)*16+o:(s,o) for s,o in boundaries}
    def hook(cpu,at,size,data):
        nonlocal visits
        ss=16*cpu.reg_read(UC_X86_REG_SS);sp=cpu.reg_read(UC_X86_REG_SP);bp=ss+cpu.reg_read(UC_X86_REG_BP)
        if at==(m.load+0x7dc)*16+0x1d7:seen[kind].add(m.word(bp-10))
        if at not in absolute:return
        where=absolute[at]
        if where==(0x173d,0x259):waits.append(m.word(bp-10))
        if where==(0,0x1a13):cpu.reg_write(UC_X86_REG_AX,yes)
        if where==(0x1656,0xb5e):
            menu=m.word(ss+sp+4)
            if menu!=32:raise ValueError(menu)
            item=choice if not visits else 2;visits+=1;menus.extend((menu,item));cpu.reg_write(UC_X86_REG_AX,item)
        if where==(0,0x19bf):events.extend((0,m.word(ss+sp+4)))
        if where==(0,0x48b7):events.extend((1,m.word(ss+sp+4),m.word(ss+sp+6)))
        off,seg=m.word(ss+sp),m.word(ss+sp+2)
        cpu.reg_write(UC_X86_REG_SP,sp+4);cpu.reg_write(UC_X86_REG_CS,seg);cpu.reg_write(UC_X86_REG_IP,off)
    handle=m.cpu.hook_add(UC_HOOK_CODE,hook)
    for kind,name in ((21,'HUT'),(14,'MAYOR'),(16,'THEATER')):
        script=decrypt((ROOT/f'Original DOS/{name}.BLD').read_bytes());seen[kind]=set()
        if kind==21:cases=itertools.product((1,5),(20,),range(2),(0,3,4),(0,3,4),(80,),(0,),(1,))
        elif kind==14:cases=itertools.product((1,5),(20,),range(2),(0,),(0,),(0,1,5,6,76,80),range(3),(1,))
        else:cases=itertools.product((1,5),(0,4,5,6),(0,),(0,),(0,),(80,),(0,),range(2))
        for count,cash,repeat,tech,medic,health,choice,yes in cases:
            m.reset();visits=0;waits.clear();menus.clear();events.clear();m.write(m.state+0xa0,script)
            flags=bytearray(80);flags[4]=1;flags[43 if kind==14 else 53]=repeat
            m.write(m.state+0xd30c,flags);m.write(m.state+0xd370,cash.to_bytes(4,'little'));m.word(m.state+0x4584,kind)
            records=bytearray(v for i in range(8) for v in (i if i<count else 255,8,9,7,0,0,0,0,1,tech if i==count-1 else 0,medic if i==0 else 0,9,8,0,0,health if i==0 else 80,0))
            m.write(m.state+0xc614,records)
            m.call(0x7dc,0x1c0,0xa0,m.state//16,limit=500000)
            final=m.read(m.state+0xd30c,80);money=int.from_bytes(m.read(m.state+0xd370,4),'little')
            hashes=[fingerprint(bytes(menus)),fingerprint(b''.join(pc.to_bytes(2,'little') for pc in waits)),fingerprint(bytes(events)),fingerprint(m.read(m.state+0xc614,136))]
            rows.append('B '+' '.join(map(str,(kind,count,cash,repeat,tech,medic,health,choice,yes,money,final[14],final[43],final[53],final[54],len(waits))))+' '+ ' '.join(f'{h:016x}' for h in hashes))
    m.cpu.hook_del(handle)
    (ROOT/'tests/fixtures/story-branches-primary.txt').write_text('\n'.join(rows)+'\n')
    (ROOT/'tests/fixtures/story-branches-primary.json').write_text(json.dumps(dict(executable_sha256=EXE_SHA,image_sha256=IMAGE_SHA,cases=len(rows),
        routine='07DC:01C0 complete original BLD VM with native party-count, meal and theater-exit actions',
        prerequisites='HUT rank 0/3/4 technician/medic combinations and repeat visits; MAYOR solo/group, three activities, repeats and six health boundaries; THEATER refusal and 0/4/5/6-credit boundaries. Explicit one/five-person parties.',
        comparison='Cash, branch flags, complete party records, ordered menu choices, held-page PCs and requested animation/sound sequence. Presentation calls are boundaries, not pixel/timing evidence.',
        executed_nodes={str(k):sorted(v) for k,v in seen.items()},intercepted_boundaries=sorted(f'{s:04X}:{o:04X}' for s,o in boundaries),no_instruction_patches=True),indent=2)+'\n')
    print('Original complete story branch cases:',len(rows))
if __name__=='__main__':main()
