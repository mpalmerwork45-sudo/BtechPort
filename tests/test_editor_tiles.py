"""Tile preview transport and package art stay in memory and use real decoders."""
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from editor_model import EditorError
from editor_tiles import (CHI_SHEETS, MAX_PREVIEW, _capture_preview,
                          decode_atlas, load_original_atlas, load_tiles)

TOOL = Path(os.environ.get("BTP_PROJECT_TOOL", ROOT / "build/btp-project"))


def atlas_bytes():
    # Distinct tile rows/columns expose index or stride errors at atlas edges.
    return b"P6\n256 256\n255\n" + bytes(value for y in range(256)
                                           for x in range(256) for value in (x, y, (x + y) % 256))


class EditorTileTests(unittest.TestCase):
    def test_binary_atlas_positions_and_whitespace_first_pixel(self):
        tiles = decode_atlas(atlas_bytes())
        self.assertEqual(len(tiles), 250)
        self.assertEqual(tiles[0][0][0], "#000000")
        self.assertEqual(tiles[15][15][15], "#ff0f0e")
        self.assertEqual(tiles[16][0][0], "#001010")
        self.assertEqual(tiles[249][15][15], "#9fff9e")
        source = atlas_bytes()
        offset = len(b"P6\n256 256\n255\n")
        source = source[:offset] + b"\n \r" + source[offset + 3:]
        self.assertEqual(decode_atlas(source)[0][0][0], "#0a200d")
        self.assertEqual(decode_atlas(b"P6\r\n# in-memory preview\r\n256 256\r\n255\r\n" + source[offset:])[0][0][0], "#0a200d")

    def test_rejects_truncated_wrong_dimensions_and_non_rgb(self):
        valid = atlas_bytes()
        for bad in [valid[:-1], valid + b"x", valid.replace(b"256 256", b"255 256", 1),
                    valid.replace(b"P6", b"P3", 1), valid.replace(b"255\n", b"65535\n", 1),
                    b"P6\n#" + b"x" * 200 + b"\n256 256\n255\n" + valid[-196608:],
                    valid + b"x" * MAX_PREVIEW]:
            with self.subTest(prefix=bad[:30]):
                with self.assertRaisesRegex(EditorError, "invalid RGB"):
                    decode_atlas(bad)

    def test_package_reads_snapshot_without_tool_or_original_files(self):
        art = json.loads((ROOT / "examples/beacon-demo/presentation.json").read_bytes())
        document = SimpleNamespace(manifest={"requires": "none", "presentation": "art.json"},
                                   snapshot={"art.json": json.dumps(art).encode()})
        before = copy.deepcopy(document.snapshot)
        with patch("editor_tiles._capture_preview", side_effect=AssertionError("No subprocess for independent art")):
            result = load_tiles(document, {})
        tile = result["package:tiles"][0]
        self.assertEqual(tile[0][0], "#" + art["palette"][int(art["tiles"][0][0][0], 16)])
        self.assertEqual(document.snapshot, before)
        with self.assertRaisesRegex(EditorError, "independent"):
            load_tiles(document, {}, "chi:land")

    def test_malformed_package_art_does_not_guess_or_fall_back(self):
        base = json.loads((ROOT / "examples/beacon-demo/presentation.json").read_bytes())
        for mutate in [lambda art: art["palette"].__setitem__(0, "GGGGGG"),
                       lambda art: art["tiles"][0].__setitem__(0, "bad"),
                       lambda art: art.__setitem__("tiles", [])]:
            art = copy.deepcopy(base)
            mutate(art)
            document = SimpleNamespace(manifest={"requires": "none", "presentation": "art.json"},
                                       snapshot={"art.json": json.dumps(art).encode()})
            with self.assertRaisesRegex(EditorError, "package presentation"):
                load_tiles(document, {})

    def test_original_requires_explicit_existing_paths(self):
        document = SimpleNamespace(manifest={"requires": "chi-original-dos-1.03"}, validator=TOOL)
        with self.assertRaisesRegex(EditorError, "Player setup"):
            load_tiles(document, {})
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(EditorError, "btp-project"):
                load_original_atlas(root / "missing", root, "chi:land")
            with self.assertRaisesRegex(EditorError, "Player setup"):
                load_original_atlas(Path(sys.executable), root / "missing", "chi:land")
            with self.assertRaisesRegex(EditorError, "Unsupported"):
                load_original_atlas(Path(sys.executable), root, "package:tiles")

    def test_all_original_sheets_use_shared_command_and_no_cache_files(self):
        document = SimpleNamespace(manifest={"requires": "chi-original-dos-1.03"}, validator=Path(sys.executable))
        with tempfile.TemporaryDirectory(prefix="btp-tile paths-") as directory:
            data = Path(directory)
            with patch("editor_tiles._capture_preview", return_value=atlas_bytes()) as call:
                result = load_tiles(document, {"data": str(data)})
            self.assertEqual(tuple(result), CHI_SHEETS)
            self.assertEqual(call.call_count, 2)
            for sheet, invocation in zip(CHI_SHEETS, call.call_args_list):
                self.assertEqual(invocation.args[0], [str(Path(sys.executable).resolve()), "preview-tiles",
                                                     "--data", str(data.resolve()), "--sheet", sheet])
            self.assertEqual(list(data.iterdir()), [])

    def test_transport_limits_and_errors(self):
        with self.assertRaisesRegex(EditorError, "output limit"):
            _capture_preview([sys.executable, "-c", f"import sys; sys.stdout.buffer.write(b'x'*{MAX_PREVIEW + 1})"])
        with self.assertRaisesRegex(EditorError, "output limit"):
            _capture_preview([sys.executable, "-c", "import sys; sys.stderr.write('x'*17000)"])
        with self.assertRaisesRegex(EditorError, "took too long"):
            _capture_preview([sys.executable, "-c", "import time; time.sleep(2)"], timeout=0.03)
        with self.assertRaisesRegex(EditorError, "missing LAND"):
            _capture_preview([sys.executable, "-c", "import sys; sys.stderr.write('missing LAND'); sys.exit(1)"])

    @unittest.skipUnless(TOOL.is_file() and (ROOT / "Original DOS").is_dir(), "Native tool and original data required")
    def test_real_shared_decoder_both_sheets(self):
        before = {path.name: (path.stat().st_size, path.stat().st_mtime_ns)
                  for path in (ROOT / "Original DOS").iterdir()}
        land = load_original_atlas(TOOL, ROOT / "Original DOS", "chi:land")
        destroyed = load_original_atlas(TOOL, ROOT / "Original DOS", "chi:destroyed")
        self.assertEqual(len(land), 250)
        self.assertEqual(len(destroyed), 250)
        self.assertNotEqual(land, destroyed)
        self.assertGreater(len({color for tile in land for row in tile for color in row}), 8)
        self.assertEqual(before, {path.name: (path.stat().st_size, path.stat().st_mtime_ns)
                                  for path in (ROOT / "Original DOS").iterdir()})


if __name__ == "__main__":
    unittest.main()
