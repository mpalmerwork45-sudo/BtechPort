#!/usr/bin/env python3
"""Read-only BLD control graph audit. Explicit variable branch-table extents."""
import argparse,json,struct
from pathlib import Path
def decrypt(raw):
    if len(raw)<2 or int.from_bytes(raw[:2],"little")!=len(raw)-2:raise ValueError("Invalid BLD length")
    return bytes(((v+41)&255)^233 for v in raw[2:])
COUNTS={7:3,8:5,9:4,10:3,11:3,12:4,13:6,14:5,15:4,16:7,17:4,18:3,19:3,21:6,24:2,25:5,26:8,27:6,28:7,29:2,30:3,31:2,35:2,36:2}
def graph(b):
    todo=[0];nodes={}
    def word(p):return int.from_bytes(b[p:p+2],'little')
    while todo:
        pc=todo.pop()
        if pc in nodes:continue
        if not 0<=pc<len(b):raise ValueError(f'Bad BLD target {pc}')
        op=b[pc];n=1;targets=[];extra={}
        if op==0xfc:
            end=b.index(0,pc+1);n=end-pc+1;extra['text']=b[pc+1:end].decode('ascii')
        elif op==0xf9:
            count=COUNTS.get(b[pc+1]);extra['menu']=b[pc+1]
            if not count:raise ValueError(f'Unknown menu {b[pc+1]} at {pc}')
            n=2+2*count;targets=[word(pc+2+2*i) for i in range(count)]
        elif op==0xf3:
            # The next payload region starts at the smallest forward target.
            p=pc+2;first=word(p);values=[]
            while p+2<=first:
                v=word(p)
                if not pc+2<=v<len(b):break
                values.append(v);first=min(first,v);p+=2
            n=p-pc;targets=values;extra['flag']=b[pc+1]
        elif op in (0xf7,):n=4;targets=[word(pc+2),pc+n];extra['flag']=b[pc+1]
        elif op in (0xf6,0xf8,0xeb,0xec):
            n=3;targets=[word(pc+1)]
            if op!=0xf8:targets.append(pc+n)
        elif op==0xe8:n=4;targets=[word(pc+2),pc+n]
        elif op in (0xed,0xef):n=5;targets=[word(pc+3),pc+n]
        elif op in (0xf0,0xf1,0xf4,0xea):n=3
        elif op in (0xfe,0xfa,0xf5,0xe9,0xe4):n=2
        elif op in (0xee,0xe5):n=3
        elif op in (0xe6,0xe7):n=5
        elif op in (0xfd,0xfb,0xf2,0xff):pass
        else:raise ValueError(f'Unknown opcode {op:02x} at {pc}')
        if pc+n>len(b):raise ValueError(f'Truncated {pc}')
        if not targets and op!=0xff:targets=[pc+n]
        nodes[pc]={'op':f'{op:02x}','operands':b[pc+1:pc+n].hex(),'targets':targets,**extra};todo.extend(targets)
    return nodes
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('bld',type=Path);p.add_argument('--output',type=Path);args=p.parse_args()
    b=decrypt(args.bld.read_bytes());nodes=graph(b)
    if args.output:args.output.write_text(json.dumps(nodes,indent=2)+'\n')
    for pc,node in sorted(nodes.items()):
        if node['op'] not in ('fc','fd','fe','fb'):print(pc,node)
    print('Reachable control nodes:',len(nodes))
