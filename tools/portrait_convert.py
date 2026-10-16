#!/usr/bin/env python3
"""Convert square artwork to a static 88x88 CHI portrait (PNG preview + ANM).

This is an authoring tool; the player needs neither Pillow nor a PNG loader.
The preview uses the actual portrait display palette, including its blue swap.
"""
import argparse
from pathlib import Path

from PIL import Image

SIDE = 88
# Stored ANM indices are not plain EGA: 1 is also black, 5 is bright blue,
# and 9 is dark blue. Keeping these indices in the PNG makes export reversible.
PALETTE = (
    (0, 0, 0), (0, 0, 0), (0, 170, 0), (0, 170, 170),
    (170, 0, 0), (85, 85, 255), (170, 85, 0), (170, 170, 170),
    (85, 85, 85), (0, 0, 170), (85, 255, 85), (85, 255, 255),
    (255, 85, 85), (255, 85, 255), (255, 255, 85), (255, 255, 255),
)


def convert(source, resample="nearest"):
    if source.width != source.height:
        raise ValueError("Portrait must be square; crop the master deliberately before export")
    rgba = source.convert("RGBA")
    if rgba.getchannel("A").getextrema() != (255, 255):
        raise ValueError("Portrait must be opaque; choose a background before export")
    method = Image.Resampling.BOX if resample == "box" else Image.Resampling.NEAREST
    rgb = rgba.convert("RGB").resize((SIDE, SIDE), method)
    # No dithering: preserve the large cel-shaded areas at this tiny resolution.
    # Equal matches choose the first index, so black is always stored as zero.
    def nearest(color):
        return min(range(16), key=lambda i: sum((a-b)**2 for a, b in zip(color, PALETTE[i])))
    colors = {color: nearest(color) for color in set(rgb.getdata())}
    indices = bytes(colors[color] for color in rgb.getdata())
    preview = Image.frombytes("P", (SIDE, SIDE), indices)
    preview.putpalette([value for color in PALETTE for value in color])
    return preview


def encode(indices):
    if len(indices) != SIDE * SIDE or any(i > 15 for i in indices):
        raise ValueError("ANM requires exactly 88x88 four-bit indices")
    packed = bytes((indices[i] << 4) | indices[i+1] for i in range(0, len(indices), 2))
    header = bytearray(51)
    header[0], header[32], header[50] = ord("A"), 1, 4
    # A single frame is a delta from black. Literal packets avoid ambiguous
    # zero/extended run counts and keep the entire static resource below 4 KiB.
    for at in range(0, len(packed), 127):
        chunk = packed[at:at+127]
        header.append(len(chunk))
        header.extend(chunk)
    return bytes(header)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True, help="ANM destination")
    parser.add_argument("--preview", type=Path, required=True, help="88x88 indexed PNG destination")
    parser.add_argument("--resample", choices=("box", "nearest"), default="nearest")
    args = parser.parse_args()
    with Image.open(args.source) as source:
        preview = convert(source, args.resample)
    encoded = encode(preview.tobytes())
    args.output.write_bytes(encoded)
    preview.save(args.preview, format="PNG", bits=4)
    print(f"88x88 portrait: {len(set(preview.tobytes()))} colors, {len(encoded)} ANM bytes")


if __name__ == "__main__":
    main()
