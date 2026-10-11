#!/usr/bin/env python3
"""Execute bounded original combat routines; this is a research tool, not the port.

Reads the hash-checked owner's EXE into private emulated RAM. It neither drives
nor edits DOSBox. Callers explicitly supply test prerequisites. No instructions
are patched and no gameplay implementation from UnBattletech is imported.
Install the optional pinned binary wheel in ignored local-deps/python (see docs).
"""
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "local-deps/python"))
try:
    from unicorn import Uc, UC_ARCH_X86, UC_MODE_16
    from unicorn.x86_const import (UC_X86_REG_AX, UC_X86_REG_BP, UC_X86_REG_CS,
        UC_X86_REG_DS, UC_X86_REG_ES, UC_X86_REG_IP, UC_X86_REG_SP, UC_X86_REG_SS,
        UC_X86_REG_EFLAGS)
except ImportError as error:
    raise SystemExit("Optional combat oracle needs Unicorn 2.1.4 in local-deps/python") from error
from exepack import unpack
from prepare_talk import EXE_SHA, IMAGE_SHA

DS, STATE, BUFFER = 0x36db0, 0x28920, 0x1c6c0


class OriginalCombat:
    def __init__(self, source=None):
        source = source or ROOT / "Original DOS/BTECH.EXE"
        self.image, metadata = unpack(source.read_bytes())
        if metadata["input_sha256"] != EXE_SHA or metadata["image_sha256"] != IMAGE_SHA:
            raise ValueError("Combat addresses require the audited original executable")
        self.cpu = Uc(UC_ARCH_X86, UC_MODE_16)
        self.cpu.mem_map(0, 0x110000)
        self.reset()

    def reset(self):
        self.cpu.mem_write(0, self.image)
        # Text verbosity is a test prerequisite; numeric rules are unmodified.
        self.write(DS+0x2e38, b"\0\0")

    def write(self, address, data):
        self.cpu.mem_write(address, bytes(data))

    def read(self, address, length):
        return bytes(self.cpu.mem_read(address, length))

    def word(self, address, value=None):
        if value is not None:
            self.write(address, struct.pack("<H", value & 65535))
        return struct.unpack("<H", self.read(address, 2))[0]

    def call(self, segment, offset, *arguments):
        cpu = self.cpu
        for register, value in ((UC_X86_REG_CS, segment), (UC_X86_REG_IP, offset),
                (UC_X86_REG_DS, DS//16), (UC_X86_REG_ES, STATE//16),
                (UC_X86_REG_SS, 0x7000), (UC_X86_REG_SP, 0xf000),
                (UC_X86_REG_BP, 0xff00), (UC_X86_REG_EFLAGS, 2)):
            cpu.reg_write(register, value)
        self.write(0x7f000, struct.pack("<"+"H"*(2+len(arguments)),
            0, 0x6000, *(a & 65535 for a in arguments)))
        cpu.emu_start(segment*16+offset, 0x60000, count=200000)
        if cpu.reg_read(UC_X86_REG_CS) != 0x6000 or cpu.reg_read(UC_X86_REG_IP):
            raise RuntimeError(f"Original routine {segment:04x}:{offset:04x} exceeded instruction bound")
        return cpu.reg_read(UC_X86_REG_AX)

    def dice(self, seed, count=2):
        self.write(DS+0x4fc0, seed)
        value = self.call(0, 0x19dd if count == 2 else 0x19f3)
        return value, list(self.read(DS+0x4fc0, 3))

    def template(self, choice=0):
        # Three loan records, selected by the original TRAINING.BLD routine.
        address = (0x28170, 0x281ed, 0x28364)[choice]
        return self.image[address:address+125]


if __name__ == "__main__":
    oracle = OriginalCombat()
    print("Original 0000:19DD dice:", oracle.dice([70, 54, 210]))
