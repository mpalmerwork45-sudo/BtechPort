#!/usr/bin/env python3
"""Execute bounded original combat routines; this is a research tool, not the port.

Reads the hash-checked owner's EXE into private emulated RAM. It neither drives
nor edits DOSBox. Callers explicitly supply test prerequisites. No instructions
are patched and no gameplay implementation from UnBattletech is imported.
Install the optional pinned binary wheel in ignored local-deps/python (see docs).
"""
import struct
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "local-deps/python"))
try:
    from unicorn import Uc, UC_ARCH_X86, UC_MODE_16, UC_HOOK_CODE, UC_HOOK_INSN
    from unicorn.x86_const import (UC_X86_REG_AX, UC_X86_REG_BP, UC_X86_REG_CS,
        UC_X86_REG_DS, UC_X86_REG_ES, UC_X86_REG_IP, UC_X86_REG_SP, UC_X86_REG_SS,
        UC_X86_REG_EFLAGS, UC_X86_INS_IN, UC_X86_INS_OUT)
except ImportError as error:
    raise SystemExit("Optional combat oracle needs Unicorn 2.1.4 in local-deps/python") from error
from exepack import unpack
from prepare_talk import EXE_SHA, IMAGE_SHA

DS, STATE, BUFFER = 0x36db0, 0x28920, 0x1c6c0


class OriginalCombat:
    def __init__(self, source=None, snapshot=None):
        source = source or ROOT / "Original DOS/BTECH.EXE"
        self.image, metadata = unpack(source.read_bytes())
        if metadata["input_sha256"] != EXE_SHA or metadata["image_sha256"] != IMAGE_SHA:
            raise ValueError("Combat addresses require the audited original executable")
        self.cpu = Uc(UC_ARCH_X86, UC_MODE_16)
        self.cpu.mem_map(0, 0x110000)
        self.retrace=0;self.speaker=0;self.device_error=None
        def input_port(cpu,port,size,data):
            if port==0x61:return self.speaker
            if port!=0x3da:
                self.device_error=f'Unaudited device read {port:04x}';cpu.emu_stop();return 0
            self.retrace^=8
            return self.retrace
        def output_port(cpu,port,size,value,data):
            if port==0x61:self.speaker=value
        self.cpu.hook_add(UC_HOOK_INSN,input_port,None,1,0,UC_X86_INS_IN)
        self.cpu.hook_add(UC_HOOK_INSN,output_port,None,1,0,UC_X86_INS_OUT)
        self.load, self.ds, self.state, self.buffer = 0, DS, STATE, BUFFER
        self.snapshot = None
        if snapshot:
            prefix = Path(snapshot)
            metadata = json.loads(Path(str(prefix)+"-state.json").read_text())
            self.load = int(metadata["load_segment"],16)
            self.ds, self.state, self.buffer = DS+16*self.load, STATE+16*self.load, BUFFER+16*self.load
            self.snapshot = Path(str(prefix)+"-ram.bin").read_bytes()
            if len(self.snapshot) != 0x100000:
                raise ValueError("Expected a one-megabyte original DOS snapshot")
        self.reset()

    def reset(self):
        self.cpu.mem_write(0, self.snapshot or self.image)
        # Text verbosity is a test prerequisite; numeric rules are unmodified.
        self.write(self.ds+0x2e38, b"\0\0")

    def write(self, address, data):
        self.cpu.mem_write(address, bytes(data))

    def read(self, address, length):
        return bytes(self.cpu.mem_read(address, length))

    def word(self, address, value=None):
        if value is not None:
            self.write(address, struct.pack("<H", value & 65535))
        return struct.unpack("<H", self.read(address, 2))[0]

    def call(self, segment, offset, *arguments, limit=200000):
        cpu = self.cpu
        segment += self.load
        for register, value in ((UC_X86_REG_CS, segment), (UC_X86_REG_IP, offset),
                (UC_X86_REG_DS, self.ds//16), (UC_X86_REG_ES, self.state//16),
                (UC_X86_REG_SS, 0x7000), (UC_X86_REG_SP, 0xf000),
                (UC_X86_REG_BP, 0xff00), (UC_X86_REG_EFLAGS, 2)):
            cpu.reg_write(register, value)
        self.write(0x7f000, struct.pack("<"+"H"*(2+len(arguments)),
            0, 0x6000, *(a & 65535 for a in arguments)))
        cpu.emu_start(segment*16+offset, 0x60000, count=limit)
        if self.device_error: raise RuntimeError(self.device_error)
        if cpu.reg_read(UC_X86_REG_CS) != 0x6000 or cpu.reg_read(UC_X86_REG_IP):
            raise RuntimeError(f"Original routine {segment:04x}:{offset:04x} exceeded instruction bound at "
                               f"{cpu.reg_read(UC_X86_REG_CS):04x}:{cpu.reg_read(UC_X86_REG_IP):04x}")
        return cpu.reg_read(UC_X86_REG_AX)

    def dice(self, seed, count=2):
        self.write(DS+0x4fc0, seed)
        value = self.call(0, 0x19dd if count == 2 else 0x19f3)
        return value, list(self.read(DS+0x4fc0, 3))

    def template(self, choice=0):
        # Three loan records, selected by the original TRAINING.BLD routine.
        address = (0x28170, 0x281ed, 0x28364)[choice]
        return self.image[address:address+125]

    def shot(self, weapon, movement, steps, skill, heat, facing, cover, variant, seed):
        """Bounded 12E8:0239..0CD3 shot span, with explicit caller locals.

        Range/visibility have already succeeded at this entry. Stop before
        destruction cleanup or graphics. No executable instructions are edited.
        """
        self.reset(); a=bytearray(self.template()); t=bytearray(self.template())
        a[51:86]=bytes(35);a[51]=weapon+1;a[39]=200;a[121]=0
        if variant:
            t[17:36]=bytes([1])*19;t[36:38]=bytes(2)
        self.write(self.state+0xc724,a);self.write(self.state+0xc918,t)
        self.write(self.state+0x32c6,[movement & 255]);self.write(self.state+0x6e,[heat])
        self.write(self.state+0xc618,bytes([skill])*5)
        self.write(self.state+0x396c+12,[facing]);self.write(self.state+0x32ae+12,[cover])
        self.write(self.state+0x3750+12,[0]);self.write(self.state+0x45ce+12,[0])
        self.write(self.state+0x92,[0]);self.word(self.state+0xe484,0);self.write(self.state+0x3986,[0])
        self.write(self.ds+0x4fc0,seed.to_bytes(3,'little'))
        self.word(self.buffer+0xa44b,0xc40);self.word(self.buffer+0xa44d,0xc040)
        self.word(self.state+0x401c,0xc44);self.word(self.state+0x404e,0xc040)
        distance=self.call(0xe31,0xf24,12,weapon)
        bp=0x7f000; self.write(bp-0x100,bytes(0x120))
        for offset,value in ((-2,0),(-0x42,0),(-0x28,12),(-0x48,weapon),(-0x5c,distance),(-0x60,2)):
            self.word(bp+offset,value)
        self.write(bp-0x78+12,[steps])
        for register,value in ((UC_X86_REG_CS,self.load+0x12e8),(UC_X86_REG_IP,0x239),
                (UC_X86_REG_DS,self.ds//16),(UC_X86_REG_ES,self.state//16),
                (UC_X86_REG_SS,0x7000),(UC_X86_REG_BP,0xf000),(UC_X86_REG_SP,0xee00)):
            self.cpu.reg_write(register,value)
        observed={}
        def watch(cpu,address,size,data):
            offset=address-(self.load+0x12e8)*16
            if offset==0xa42: observed['location']=self.word(bp-0x60);observed['damage']=self.word(bp-0x7c)
            if offset in (0xc12,0xcb2): observed['dead']=1;cpu.emu_stop()
        hook=self.cpu.hook_add(UC_HOOK_CODE,watch)
        self.cpu.emu_start((self.load+0x12e8)*16+0x239,(self.load+0x12e8)*16+0xcd3,count=200000)
        self.cpu.hook_del(hook)
        if self.cpu.reg_read(UC_X86_REG_IP) not in (0xcd3,0xc12,0xcb2):
            raise RuntimeError('Shot exceeded instruction bound')
        return dict(needed=self.word(bp-0x30),hit=self.word(bp-0x56),
            location=observed['location'],damage=observed['damage'],dead=observed.get('dead',0),
            toppled=self.read(self.state+0x3986,1)[0],rng=int.from_bytes(self.read(self.ds+0x4fc0,3),'little'),
            target=self.read(self.state+0xc918,125),ammo=self.read(self.state+0xc724+39,1)[0],
            pool=self.read(self.state+0x92,1)[0])


if __name__ == "__main__":
    oracle = OriginalCombat()
    print("Original 0000:19DD dice:", oracle.dice([70, 54, 210]))
