#!/usr/bin/env python3
"""Original apprenticeship effects and post-building VIEWDISK dispatch."""
import json,struct
from combat_oracle import OriginalCombat,ROOT,UC_HOOK_CODE,UC_X86_REG_CS,UC_X86_REG_IP,UC_X86_REG_BP,UC_X86_REG_SP,UC_X86_REG_SS,UC_X86_REG_DS
from make_party_vectors import SNAP
from make_combat_vectors import fingerprint
from prepare_talk import EXE_SHA,IMAGE_SHA

def main():
    m=OriginalCombat(snapshot=SNAP);route=json.loads((ROOT/'tests/fixtures/ordinary-fresh-campaign.json').read_text())
    notes={n['label']:n for n in route['checkpoints']};rows=[];calls=[]
    for action,member,before,after in ((15,2,'apprenticeship-offer','technician-qualified'),(21,3,'medical-seminar-offer','medic-qualified')):
        first=notes[before]['state'];last=notes[after]['state'];m.reset()
        m.write(m.state+0xc614,bytes(v for p in first['people'] for v in p));m.write(m.state+0xd31a,[member])
        m.write(m.state+0xd370,first['credits'].to_bytes(4,'little'));m.call(0x14d3,4,action)
        people=m.read(m.state+0xc614,136);cash=int.from_bytes(m.read(m.state+0xd370,4),'little')
        if people!=bytes(v for p in last['people'] for v in p) or cash!=last['credits']:raise RuntimeError('Fresh apprenticeship disagrees with original')
        rows.append(f'T {notes[after]["tick"]} {cash} {fingerprint(people):016x}')
    boundaries={(0x7dc,8),(0x1656,0x281),(0x1656,0x388),(0x1656,0x3f5),(0x14d3,0x17ea),(0x173d,0x259)}
    absolute={(m.load+s)*16+o:(s,o) for s,o in boundaries}
    def hook(cpu,address,size,data):
        if address not in absolute:return
        sp=cpu.reg_read(UC_X86_REG_SP);ss=cpu.reg_read(UC_X86_REG_SS)*16
        if absolute[address]==(0x7dc,8):calls.append(m.word(ss+sp+4))
        off,seg=struct.unpack('<HH',m.read(ss+sp,4));cpu.reg_write(UC_X86_REG_SP,sp+4)
        cpu.reg_write(UC_X86_REG_CS,seg);cpu.reg_write(UC_X86_REG_IP,off)
    handle=m.cpu.hook_add(UC_HOOK_CODE,hook)
    for kind in (8,19):
        for count in (1,2,5):
            for viewer in range(2):
                for viewed in range(2):
                    m.reset();calls.clear();m.write(m.state+0xc614,bytes(v for i in range(8) for v in [i if i<count else 255]+[0]*16))
                    m.write(m.state+0xd33c,[viewer]);m.write(m.state+0xd33e,[viewed]);bp=0x7f000;m.word(bp+6,kind)
                    for reg,value in ((UC_X86_REG_CS,m.load+0x7dc),(UC_X86_REG_IP,0xc3),(UC_X86_REG_DS,m.ds//16),
                            (UC_X86_REG_SS,0x7000),(UC_X86_REG_BP,0xf000),(UC_X86_REG_SP,0xee00)):m.cpu.reg_write(reg,value)
                    m.cpu.emu_start((m.load+0x7dc)*16+0xc3,(m.load+0x7dc)*16+0x15d,count=2000000)
                    if m.cpu.reg_read(UC_X86_REG_IP)!=0x15d or calls not in ([],[18]):raise RuntimeError(f'Unverified child story request: {kind,count,viewer,viewed}, calls={calls}, CS={m.cpu.reg_read(UC_X86_REG_CS)-m.load:x} IP={m.cpu.reg_read(UC_X86_REG_IP):x}')
                    rows.append(f'D {kind} {count} {viewer} {viewed} {len(calls)}')
    m.cpu.hook_del(handle)
    (ROOT/'tests/fixtures/campaign-checkpoints-primary.txt').write_text('\n'.join(rows)+'\n')
    (ROOT/'tests/fixtures/campaign-checkpoints-primary.json').write_text(json.dumps(dict(
        executable_sha256=EXE_SHA,image_sha256=IMAGE_SHA,cases=len(rows),
        routines=['14D3:0004 actions 15/21','07DC:00C3..015D'],
        prerequisites='Actual input-only fresh-route apprenticeship records/cash; selected technician/medic. Building 8/19 with 1/2/5 people and viewer/viewed flags.',
        intercepted_boundaries=[f'{s:04X}:{o:04X}' for s,o in sorted(boundaries)],
        comparison='Complete character records/cash at two fresh checkpoints; actual original child VIEWDISK request. Child script itself remains a separate boundary, not a whole DOS campaign replay.'),indent=2)+'\n')
    print('Original fresh-route/checkpoint cases:',len(rows))
if __name__=='__main__':main()
