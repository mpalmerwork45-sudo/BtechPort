"""EXEPACK format regression: independent miniature stream + supplied image."""
import hashlib
import struct
import unittest
import runpy
import sys
import tempfile
from unittest import mock
from pathlib import Path
from tools.exepack import unpack
from tools.prepare_talk import extract

ROOT = Path(__file__).resolve().parents[1]


def miniature():
    header = [0x5a4d, 64, 1, 0, 2, 0, 0, 0, 0, 0, 16, 1, 0, 0]
    packed = bytes(range(12)) + bytes([0xab, 148, 0, 0xb1])
    rb = [0, 0, 0, 16, 0, 0, 10, 0x4252]
    return struct.pack("<14H", *header) + bytes(4) + packed + struct.pack("<8H", *rb)


class ExepackTests(unittest.TestCase):
    def test_repeat_and_prefix(self):
        image, info = unpack(miniature())
        self.assertEqual(image, bytes(range(12)) + bytes([0xab]) * 148)
        self.assertEqual((info["runs"], info["prefix_size"]), (1, 12))

    def test_invalid_headers_and_runs(self):
        source = miniature()
        for b in (b"", source[:24], source[:-1]):
            with self.assertRaises(ValueError):
                unpack(b)
        for offset, value in ((0, 0), (62, 0), (45, 0), (45, 161), (47, 0x99)):
            b = bytearray(source)
            b[offset] = value
            with self.assertRaises(ValueError):
                unpack(b)

    def test_supplied_image(self):
        image, info = unpack((ROOT / "Original DOS/BTECH.EXE").read_bytes())
        self.assertEqual(info["input_sha256"], "15a1712682cf1fe50ca9e6a68a4b31d3bef7912401915edf7bb6242be193562a")
        self.assertEqual(len(image), 247216)
        self.assertEqual(hashlib.sha256(image).hexdigest(), "100f0df244e4b0c8693d1b5013fb073f486b35d6f5c538ecd53d03f85ed54bfa")
        anchor = b"BattleTech: The Crescent Hawk's Inception"
        self.assertEqual(image[0x37a88:0x37a88+len(anchor)], anchor)

    def test_native_text_cache_provenance(self):
        source = (ROOT / "Original DOS/BTECH.EXE").read_bytes()
        image, _ = unpack(source)
        cache, metadata = extract(source)
        self.assertEqual(cache, extract(source)[0])
        self.assertEqual((cache[:4],len(cache),len(metadata["strings"])),(b"BTTA",10054,207))
        length,count = struct.unpack_from("<HH",cache,4)
        header = 72+4*count
        self.assertEqual(length+header+2048,len(cache))
        font = metadata["font"]
        self.assertEqual(cache[-2048:],image[font["image_offset"]:font["image_offset"]+2048])
        for i in range(count):
            at,n = struct.unpack_from("<HH",cache,72+4*i)
            origin = metadata["strings"][i]
            body = image[origin["image_offset"]:origin["image_offset"]+n]
            self.assertEqual(cache[header+at:header+at+n],body)
            self.assertEqual(hashlib.sha256(body).hexdigest(),origin["sha256"])
        with self.assertRaises(ValueError):
            extract(miniature())

    def test_world_preparation_without_optional_emulator(self):
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/"world.bin"
            with mock.patch.object(sys,"argv",["prepare_world.py","--output",str(output)]), \
                 mock.patch.object(sys,"path",[str(ROOT/"tools"),*sys.path]), \
                 mock.patch.dict(sys.modules,{"combat_oracle":None,"unicorn":None}):
                runpy.run_path(str(ROOT/"tools/prepare_world.py"),run_name="__main__")
            cache=output.read_bytes()
            self.assertEqual((cache[:4],len(cache)),(b"BTW3",1864))
            self.assertEqual(cache,(ROOT/"work/world-data.bin").read_bytes())


if __name__ == "__main__":
    unittest.main()
