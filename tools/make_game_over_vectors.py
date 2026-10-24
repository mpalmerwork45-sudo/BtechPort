"""Observe original essential-character death text in native popup window 7.

Two explicit casualty prerequisites execute unmodified 0000:04A4..04DB until
the popup's keyboard/delay boundary. Only hashes and glyph geometry are public;
original text/pixels remain in ignored work. No executable code is patched.
"""
import json
from combat_oracle import OriginalCombat,ROOT,UC_HOOK_CODE
from make_party_vectors import SNAP
from make_aftermath_vectors import span
from make_battle_text_vectors import fnv
from make_phoenix_palette_vectors import EGA
from prepare_talk import EXE_SHA,IMAGE_SHA,FONT
from unicorn.x86_const import UC_X86_REG_SS,UC_X86_REG_SP

def main():
    m=OriginalCombat(snapshot=SNAP);rows=[];private=[];draws=[];fragments=[];stopped=False;window=[]
    def hook(cpu,at,size,data):
        nonlocal stopped
        st=cpu.reg_read(UC_X86_REG_SS)*16+cpu.reg_read(UC_X86_REG_SP)
        if at==(m.load+0x1656)*16+0x281:window.append(m.word(st+4))
        elif at==(m.load+0x1656)*16+0x3f5:
            ptr=m.word(st+4)+16*m.word(st+6);fragments.append(m.read(ptr,512).split(b'\0')[0])
        elif at==(m.load+0x173d)*16+0xd5:
            ptr=m.word(st+4)+16*m.word(st+6)
            draws.append((m.word(st+8),m.word(st+10),m.word(st+12),m.read(ptr,512).split(b'\0')[0]))
        elif at==(m.load+0x173d)*16+0x86a:stopped=True;cpu.emu_stop()
    m.cpu.hook_add(UC_HOOK_CODE,hook)
    folder=ROOT/'work/jason-death';folder.mkdir(exist_ok=True)
    for victim in (0,1):
        m.reset();draws.clear();fragments.clear();window.clear();stopped=False
        m.word(m.ds+0x14a,0);m.write(m.state+0xc614,[255 if victim==0 else 0])
        try:span(m,0,0x4a4,0x4db,{})
        except RuntimeError:
            if not stopped:raise
        if not stopped or window!=[7]:raise RuntimeError('Unexpected original death popup boundary.')
        pixels=bytearray(200*40*3)
        for x,y,color,raw in draws:
            for i,ch in enumerate(raw):
                for dy in range(8):
                    for dx in range(8):
                        xx=(x-14+i)*8+dx;yy=(y-10)*8+dy
                        if 0<=xx<200 and 0<=yy<40:
                            c=EGA[color] if m.image[FONT+8*ch+dy]&(128>>dx) else 0
                            p=(yy*200+xx)*3;pixels[p:p+3]=c.to_bytes(3,'big')
        text=b''.join(fragments);rows.append(f'{victim} {fnv(text):016x} {fnv(pixels):016x}')
        private.append(dict(victim=victim,draws=[dict(x=x,y=y,color=c,text=t.decode('ascii')) for x,y,c,t in draws]))
        (folder/f'original-{victim}.ppm').write_bytes(b'P6\n200 40\n255\n'+pixels)
    (folder/'draws.json').write_text(json.dumps(private,indent=2)+'\n')
    (ROOT/'tests/fixtures/game-over-primary.txt').write_text('\n'.join(rows)+'\n')
    (ROOT/'tests/fixtures/game-over-primary.json').write_text(json.dumps(dict(executable_sha256=EXE_SHA,image_sha256=IMAGE_SHA,
        cases=2,routines=['0000:04A4..04DB','14D3:17C6/17EA','1656:03F5','173D:00D5'],
        prerequisites='Audited mixed-party RAM snapshot; explicit essential-character casualty byte and main-loop death flag.',
        held_boundary='173D:086A before keyboard/delay; no key input, instruction patches or gameplay reconstruction.',
        comparison='Original text stream and 200x40 RGB interior at x112,y80; native popup window 7. Surrounding battlefield pixels are not established by this crop.'),indent=2)+'\n')
    print('Recorded two original death-popup text/pixel hashes.')

if __name__=='__main__':main()
