"""Read-only tile previews from the game's decoder or package presentation.

The editor keeps decoded original art in memory. It never adds that art to a
project, its exports, or a preview cache on disk. CHI tile decoding and its
palette belong to the shared C tool, so previewing cannot drift into a second
Python implementation of the original graphics formats.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import threading

from editor_model import EditorError
from tile_animation import TileGraphics, TileLoop


TilePixels = tuple[tuple[str, ...], ...]
TileSet = tuple[TilePixels, ...]
CHI_SHEETS = ("chi:land", "chi:destroyed")
CHI_IMPORT_SHEETS = (*CHI_SHEETS,"chi:cache","chi:maproom")
ATLAS_SIZE = 256
TILE_SIZE = 16
CHI_TILE_COUNT = 250
MAX_HEADER = 128
MAX_PREVIEW = ATLAS_SIZE * ATLAS_SIZE * 3 + MAX_HEADER
MAX_ERROR = 16 * 1024


def _capture_preview(command: list[str], timeout: float = 15, max_preview=MAX_PREVIEW) -> bytes:
    """Capture a small binary atlas with bounded pipes on Windows and Linux.

    Separate readers prevent an error stream from blocking the art stream.
    Both stop the child if its output exceeds the deliberately small format.
    This also avoids writing decoded original art to temporary files.
    """
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, stdin=subprocess.DEVNULL)
    except OSError as exc:
        raise EditorError(f"Cannot run the shared tile preview tool: {exc}") from exc
    output = [bytearray(), bytearray()]
    overflow = threading.Event()
    failures = []

    def read_pipe(index, stream, limit):
        try:
            while True:
                block = stream.read(min(65536, limit + 1 - len(output[index])))
                if not block:
                    return
                output[index].extend(block)
                if len(output[index]) > limit:
                    overflow.set()
                    process.kill()
                    return
        except OSError as exc:
            failures.append(exc)

    threads = [threading.Thread(target=read_pipe, args=(index, stream, limit), daemon=True)
               for index, stream, limit in [(0, process.stdout, max_preview),
                                            (1, process.stderr, MAX_ERROR)]]
    for thread in threads:
        thread.start()
    timed_out = False
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        process.kill()
        process.wait()
    for thread in threads:
        thread.join(timeout=1)
    # The trusted decoder does not spawn children. Treat an unexpectedly held
    # pipe as a failed preview rather than keeping the GUI waiting indefinitely.
    readers_stuck = any(thread.is_alive() for thread in threads)
    if not readers_stuck:
        process.stdout.close()
        process.stderr.close()
    if timed_out:
        raise EditorError("The shared tile preview tool took too long to respond.")
    if overflow.is_set():
        raise EditorError("The shared tile preview tool exceeded its output limit.")
    if readers_stuck or failures:
        raise EditorError("Cannot read the shared tile preview tool's output.")
    if process.returncode:
        detail = bytes(output[1]).decode("utf-8", errors="replace").strip()
        raise EditorError(detail or "The shared tile preview tool could not decode the original graphics.")
    return bytes(output[0])


def decode_atlas(data: bytes) -> TileSet:
    """Accept only the fixed 256x256, 8-bit RGB P6 preview protocol."""
    invalid = "The shared tile preview tool returned an invalid RGB tile atlas."
    if not isinstance(data, bytes) or len(data) > MAX_PREVIEW:
        raise EditorError(invalid)
    cursor = 0

    def token():
        nonlocal cursor
        while cursor < len(data) and cursor < MAX_HEADER:
            if data[cursor] in b" \t\r\n\v\f":
                cursor += 1
            elif data[cursor] == ord("#"):
                end = data.find(b"\n", cursor, MAX_HEADER)
                if end < 0:
                    raise EditorError(invalid)
                cursor = end + 1
            else:
                break
        start = cursor
        while cursor < len(data) and cursor < MAX_HEADER and data[cursor] not in b" \t\r\n\v\f#":
            cursor += 1
        if cursor == start or cursor >= MAX_HEADER:
            raise EditorError(invalid)
        return data[start:cursor]

    if [token() for _ in range(4)] != [b"P6", b"256", b"256", b"255"]:
        raise EditorError(invalid)
    if cursor >= len(data) or data[cursor] not in b" \t\r\n\v\f":
        raise EditorError(invalid)
    # Consume the header's separator, not arbitrary whitespace: the first RGB
    # component may itself be 0x0a or 0x20 and must remain a pixel byte.
    cursor += 2 if data[cursor:cursor + 2] == b"\r\n" else 1
    if cursor > MAX_HEADER or len(data) - cursor != ATLAS_SIZE * ATLAS_SIZE * 3:
        raise EditorError(invalid)
    raster = memoryview(data)[cursor:]
    tiles = []
    for index in range(CHI_TILE_COUNT):
        tile_x, tile_y = index % 16 * TILE_SIZE, index // 16 * TILE_SIZE
        rows = []
        for y in range(TILE_SIZE):
            start = ((tile_y + y) * ATLAS_SIZE + tile_x) * 3
            rows.append(tuple("#" + bytes(raster[start + x * 3:start + x * 3 + 3]).hex()
                              for x in range(TILE_SIZE)))
        tiles.append(tuple(rows))
    return tuple(tiles)


def load_original_atlas(validator: Path, data: Path, sheet: str) -> TileSet:
    """Ask the same C decoder/palette used by gameplay for a CHI tile sheet."""
    if sheet not in CHI_IMPORT_SHEETS:
        raise EditorError(f"Unsupported original tile sheet: {sheet}")
    validator, data = Path(validator), Path(data)
    if not validator.is_file():
        raise EditorError("Build or configure an existing btp-project tool before previewing original tiles.")
    if not data.is_dir():
        raise EditorError("Configure an existing Original data path in Player setup to preview CHI tiles.")
    command = [str(validator.resolve()), "preview-tiles", "--data", str(data.resolve()), "--sheet", sheet]
    return decode_atlas(_capture_preview(command))


def load_original_animations(validator: Path, data: Path, project=False):
    """The C tool supplies both the verified tile substitution and its pixels."""
    from art_editing import display_rows
    raw = _capture_preview([str(Path(validator).resolve()), 'terrain-animations', '--project' if project else '--data', str(Path(data).resolve())])
    try:
        source = json.loads(raw)
        ticks = source['frame_ticks']
        if type(ticks) is not int or not 1 <= ticks <= 255 or not 1 <= len(source['tiles']) <= 250:
            raise ValueError('Invalid duration/count')
        result = {}
        for tile in source['tiles']:
            graphic, frames = tile['graphic'], tile['frames']
            if type(graphic) is not int or not 0 <= graphic < 250 or ('chi:land', graphic) in result or len(frames) != 3:
                raise ValueError('Invalid tile/frames')
            if any(len(frame) != 16 or any(not isinstance(row, str) or len(row) != 128 or
                   any(c not in '0123456789abcdef' for c in row) for row in frame) for frame in frames):
                raise ValueError('Invalid pixels')
            image = dict(width=16, height=16, frames=frames)
            result['chi:land', graphic] = TileLoop(tuple(display_rows(image, n) for n in range(3)), ticks)
        return result
    except (KeyError, TypeError, ValueError) as exc:
        raise EditorError('The shared tool returned invalid terrain animation data. Rebuild btp-project.') from exc


def _package_tiles(document) -> TileSet:
    try:
        art = json.loads(document.snapshot[document.manifest["presentation"]])
        palette, source = art["palette"], art["tiles"]
        if not isinstance(palette, list) or len(palette) != 16:
            raise ValueError("Palette must have 16 colors")
        if any(not isinstance(color, str) or len(color) != 6 or
               any(c not in "0123456789abcdef" for c in color) for color in palette):
            raise ValueError("Invalid RGB palette")
        if not isinstance(source, list) or not 1 <= len(source) <= 64:
            raise ValueError("Invalid tile count")
        tiles = []
        for tile in source:
            if not isinstance(tile, list) or len(tile) != TILE_SIZE:
                raise ValueError("Invalid tile rows")
            rows = []
            for row in tile:
                if not isinstance(row, str) or len(row) != TILE_SIZE or any(c not in "0123456789abcdef" for c in row):
                    raise ValueError("Invalid tile pixels")
                rows.append(tuple("#" + palette[int(pixel, 16)] for pixel in row))
            tiles.append(tuple(rows))
        return tuple(tiles)
    except (KeyError, TypeError, ValueError) as exc:
        raise EditorError("The package presentation does not contain valid 16x16 tile graphics.") from exc


def load_tiles(document, settings: dict, sheet: str | None = None) -> dict[str, TileSet]:
    """Load all editable sheets (or one sheet) without changing the document.

    Each tile contains 16 rows of 16 '#rrggbb' strings ready for PhotoImage.put.
    Original projects load both sheets so changing a definition's graphic or
    sheet can preview every original tile, including presently unused art.
    Independent projects use their validated, already loaded presentation
    snapshot and do not require any player settings or original decoder call.
    """
    if document.manifest["requires"] == "none":
        if sheet not in (None, "package:tiles"):
            raise EditorError(f"An independent project cannot preview tile sheet {sheet}.")
        result = TileGraphics({"package:tiles": _package_tiles(document)})
        if sheet is None: result.update(art_tiles(document))
        return result
    if document.manifest['requires']=='chi-local-dos-1.03':
        from chi_resources import tile_atlases
        return tile_atlases(document,sheet)
    from editor_model import resource_settings
    settings=resource_settings(document,settings)
    sheets = CHI_SHEETS if sheet is None else (sheet,)
    if not settings.get("data"):
        raise EditorError("Configure an existing Original data path in Player setup to preview CHI tiles.")
    result = TileGraphics({name: load_original_atlas(document.validator, Path(settings["data"]), name) for name in sheets})
    if 'chi:land' in sheets:
        result.animations.update(load_original_animations(document.validator, Path(settings['data'])))
    if sheet is None: result.update(art_tiles(document))
    return result


def art_tiles(document):
    from art_editing import display_rows
    images = [im for im in getattr(document, "art", {}).get("images", []) if im['kind']=='tile']
    return TileGraphics({"package:art": {im["id"]: display_rows(im) for im in images}},
        {('package:art', im['id']): TileLoop(tuple(display_rows(im, n) for n in range(len(im['frames']))), im.get('frame_ticks', 8))
         for im in images if len(im['frames']) > 1}) if images else TileGraphics()
