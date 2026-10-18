"""Tile loops and a shared preview clock; previewing never edits the project."""
from __future__ import annotations
from typing import NamedTuple
import time


class TileLoop(NamedTuple):
    frames: tuple
    ticks: int = 8


class TileGraphics(dict):
    """Static atlas API with separate loops, so bank/index references stay stable."""
    def __init__(self, values=(), animations=None):
        super().__init__(values)
        self.animations = dict(animations or {})

    def update(self, other):
        self.animations = {key: loop for key, loop in self.animations.items() if key[0] not in other}
        self.animations.update(getattr(other, 'animations', {}))
        super().update(other)

    def pop(self, key, default=None):
        self.animations = {k: loop for k, loop in self.animations.items() if k[0] != key}
        return super().pop(key, default)


def tile_loop(decoded, sheet, graphic):
    return getattr(decoded, 'animations', {}).get((sheet, graphic))


def copy_frames(decoded, sheet, graphic):
    """Copy a source tile without flattening its animation or losing its cadence."""
    loop = tile_loop(decoded, sheet, graphic)
    frames = loop.frames if loop else [decoded[sheet][graphic]]
    result = dict(frames=[[''.join(c.lstrip('#') + 'ff' for c in row) for row in frame] for frame in frames])
    if loop:
        result['frame_ticks'] = loop.ticks
    return result


def loop_label(decoded, sheet, graphic):
    loop = tile_loop(decoded, sheet, graphic)
    return f'Animated: {len(loop.frames)} frames, {loop.ticks * 32} ms/frame' if loop else 'Static tile'


def put_tile(image, rows, size):
    image.put(' '.join('{' + ' '.join(rows[y * 16 // size][x * 16 // size] for x in range(size)) + '}' for y in range(size)))


class TilePreviewClock:
    """Update cached PhotoImages in place, shared by maps, designers and pickers.

    No full-canvas redraw, geometry reset, dirty flag or Undo entry is needed.
    Only an animated image whose frame changed incurs a Tk pixel upload.
    """
    def __init__(self, owner):
        # Model/decoder helpers also run on systems without a Tk installation.
        import tkinter as tk
        self.owner = owner
        self.enabled = tk.BooleanVar(master=owner.window, value=True)
        self.last = {}
        self.job = owner.window.after(32, self.tick)
        owner.window.bind('<Destroy>', self.destroyed, add='+')

    def frame(self, loop, now=None):
        return int((time.monotonic() if now is None else now) * 1000 / (32 * loop.ticks)) % len(loop.frames) if self.enabled.get() else 0

    def refresh(self, now=None):
        now=time.monotonic() if now is None else now
        for key, image in self.owner.images.items():
            loop = tile_loop(self.owner.graphics, *key[:2])
            if not loop:
                continue
            frame = self.frame(loop, now)
            if self.last.get(key) != (str(image), frame):
                put_tile(image, loop.frames[frame], key[2])
                self.last[key] = (str(image), frame)
        # Removing/refreshing artwork releases the previous cache generations.
        self.last = {key: value for key, value in self.last.items() if key in self.owner.images}

    def tick(self):
        self.job = None
        if self.owner.window.winfo_exists():
            self.refresh()
            self.job = self.owner.window.after(32, self.tick)

    def destroyed(self, event):
        if event.widget == self.owner.window and self.job is not None:
            self.owner.window.after_cancel(self.job)
            self.job = None
