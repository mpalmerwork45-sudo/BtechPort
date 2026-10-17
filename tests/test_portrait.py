"""Authoring round trip and actual native broker pixels, without GUI waits."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from anm_audit import decode
from portrait_convert import PALETTE, convert, encode

ART = ROOT / "content/updated/art"


class PortraitExport(unittest.TestCase):
    @unittest.skipUnless((ROOT / "build/btp-building-art-tests").exists(), "build the native tests first")
    def test_native_building_pixels(self):
        with tempfile.TemporaryDirectory(prefix="building-art-") as directory:
            prefix = Path(directory) / "visit"
            subprocess.run([ROOT / "build/btp-building-art-tests", ROOT / "Original DOS",
                ROOT / "work/talk-data.bin", ROOT / "work/combat-data.bin", ROOT / "work/world-data.bin",
                ROOT / "content/updated/roster.json", prefix], cwd=directory, check=True, capture_output=True, timeout=30)
            for name in ("training", "lounge", "prison", "inventor", "cinema", "hospital", "comstar",
                         "clothes", "video-hut", "mayor"):
                with self.subTest(portrait=name), Image.open(f"{prefix}-{name}.ppm") as rendered, Image.open(ART / f"{name}.png") as expected:
                    self.assertEqual(rendered.crop((8, 8, 96, 96)).tobytes(), expected.convert("RGB").tobytes())

    def test_four_bit_round_trip(self):
        # Cross literal packet boundaries with every index, including the two
        # black entries and swapped blues; decode with the independent reader.
        indices = bytes(i % 16 for i in range(88 * 88))
        data = encode(indices)
        result = decode(data)
        self.assertEqual(result["consumed"], len(data))
        self.assertEqual(len(result["frames"]), 1)
        packed = result["frames"][0]["packed"]
        actual = bytes(value for pair in packed for value in (pair >> 4, pair & 15))
        self.assertEqual(actual, indices)

    def test_selected_asset_reproducible(self):
        for name in ("broker", "training", "lounge", "prison", "inventor", "cinema", "hospital", "comstar",
                     "clothes", "video-hut", "mayor"):
            with self.subTest(portrait=name):
                with Image.open(ART / f"{name}-master.png") as source:
                    preview = convert(source)
                with Image.open(ART / f"{name}.png") as saved:
                    self.assertEqual(preview.convert("RGB").tobytes(), saved.convert("RGB").tobytes())
                self.assertEqual(encode(preview.tobytes()), (ART / f"{name}.anm").read_bytes())
                self.assertLess(len(encode(preview.tobytes())), 4096)
        self.assertEqual(PALETTE[5], (85, 85, 255))
        self.assertEqual(PALETTE[9], (0, 0, 170))

    def test_rejected_inputs(self):
        for source in (Image.new("RGB", (90, 88)), Image.new("RGBA", (88, 88))):
            with self.assertRaises(ValueError):
                convert(source)
        for indices in (b"", bytes([16]) * (88 * 88), bytes(88 * 88 - 1)):
            with self.assertRaises(ValueError):
                encode(indices)

    @unittest.skipUnless((ROOT / "build/btp-roster-tests").exists(), "build the native tests first")
    def test_native_broker_pixels(self):
        with tempfile.TemporaryDirectory(prefix="broker-art-") as directory:
            tmp = Path(directory)
            start, replay, frame = tmp / "start.btp", tmp / "inputs.txt", tmp / "frame.ppm"
            subprocess.run([ROOT / "build/btp-roster-tests", ROOT / "Original DOS",
                ROOT / "work/talk-data.bin", ROOT / "work/combat-data.bin", ROOT / "work/world-data.bin",
                ROOT / "content/updated/roster.json", start], cwd=tmp, check=True, capture_output=True, timeout=30)
            replay.write_text("up\naccept\n")
            subprocess.run([ROOT / "build/btech-headless", "--load", start, "--replay", replay,
                "--frame", frame], cwd=ROOT, check=True, capture_output=True, timeout=15)
            with Image.open(frame) as rendered, Image.open(ART / "broker.png") as expected:
                self.assertEqual(rendered.crop((8, 8, 96, 96)).tobytes(), expected.convert("RGB").tobytes())


if __name__ == "__main__":
    unittest.main()
