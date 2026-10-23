"""Package-owned RGBA images: cloning, brush strokes and explicit imports."""
from __future__ import annotations
import copy
from pathlib import Path
import json
from editor_model import EditorError
from world_editing import identity, line, flood

TRANSPARENT = "00000000"
SLOTS = ("player", "npc", "enemy", "locust", "stinger", "wreck")
DEFAULT_COLORS = ("000000", "0000aa", "00aa00", "00aaaa", "aa0000", "aa00aa", "aa5500", "aaaaaa",
                  "555555", "5555ff", "55ff55", "55ffff", "ff5555", "ff55ff", "ffff55", "ffffff")


def new_image(prefix, images, name="New image", kind="tile", width=16, height=16, frames=1):
    if not 1 <= width <= 320 or not 1 <= height <= 200 or not 1 <= frames <= 256:
        raise EditorError("Images are at most 320x200 pixels, with 1..256 animation frames.")
    if kind == "tile" and (width, height) != (16, 16): raise EditorError("Map tiles must be 16x16 pixels.")
    if kind in ("sprite", "icon") and max(width, height) > 64: raise EditorError("Sprites/icons are at most 64x64 pixels.")
    return dict(id=identity(prefix, images, "image"), name=name, kind=kind, width=width, height=height,
                frames=[[TRANSPARENT*width for _ in range(height)] for _ in range(frames)])


def clone_image(image, prefix, images):
    result = copy.deepcopy(image)
    result.update(id=identity(prefix, images, "image"), name=(image["name"][:89] + " copy"))
    return result


def pixels(image, frame=0):
    return [[row[x:x+8] for x in range(0, len(row), 8)] for row in image["frames"][frame]]


def write_pixels(image, frame, rows):
    image["frames"][frame] = ["".join(row) for row in rows]


def transform(image, operation, frame=0, all_frames=False, wrap=False):
    """Transform straight RGBA pixels without resampling or losing alpha.

    Frames share dimensions. Rotating a rectangular animation therefore needs
    all frames selected; rejecting it first keeps the pending edit atomic.
    """
    w, h = image['width'], image['height']
    rotate = operation in ('Rotate right', 'Rotate left')
    shifts = {'Nudge left': (-1, 0), 'Nudge right': (1, 0),
              'Nudge up': (0, -1), 'Nudge down': (0, 1)}
    if operation not in ('Flip X', 'Flip Y', 'Rotate right', 'Rotate left', 'Clear') and operation not in shifts:
        raise EditorError('Unknown pixel transformation.')
    if rotate and w != h:
        if not all_frames and len(image['frames']) > 1:
            raise EditorError('Select All frames to rotate a rectangular animation.')
        if h > 320 or w > 200:
            raise EditorError('The rotated image would exceed the 320x200 image limit.')
    for index in range(len(image['frames'])) if all_frames else [frame]:
        rows = pixels(image, index)
        if operation == 'Flip X': result = [row[::-1] for row in rows]
        elif operation == 'Flip Y': result = rows[::-1]
        elif operation == 'Rotate right': result = [list(row) for row in zip(*rows[::-1])]
        elif operation == 'Rotate left': result = [list(row) for row in zip(*rows)][::-1]
        elif operation == 'Clear': result = [[TRANSPARENT]*w for _ in range(h)]
        else:
            dx, dy = shifts[operation]
            result = [[rows[(y-dy)%h][(x-dx)%w] if wrap or (0 <= x-dx < w and 0 <= y-dy < h)
                       else TRANSPARENT for x in range(w)] for y in range(h)]
        write_pixels(image, index, result)
    if rotate: image['width'], image['height'] = h, w


def editable_tile(art, adventure, index, prefix, decoded):
    """Detach an indexed tile into owned artwork, keeping every map reference.

    The caller commits art and adventure in one shared history entry. Original
    sheets are only read; editing a tile definition changes all its placements.
    """
    from world_editing import upgrade
    tile = adventure['tiles'][index]
    if tile['sheet'] == 'package:art':
        return next(im for im in art['images'] if im['id'] == tile['graphic'])
    from tile_animation import copy_frames
    try: frames = copy_frames(decoded,tile['sheet'],tile['graphic'])
    except (KeyError, IndexError): raise EditorError('Wait for the map graphics preview to load first.')
    im = new_image(prefix, art['images'], tile['id'].split(':')[-1][:80] + ' pixels')
    im.update(frames)
    upgrade(adventure)
    tile.update(sheet='package:art', graphic=im['id'])
    art['images'].append(im)
    return im


def brush(image, frame, start, end, color, tool="Pencil"):
    if len(color) != 8 or any(c not in "0123456789abcdef" for c in color): raise EditorError("Color needs eight RGBA hexadecimal digits.")
    rows = pixels(image, frame)
    if tool == "Fill": flood(rows, *end, color)
    else:
        if tool == "Rectangle":
            x0, x1 = sorted((start[0], end[0])); y0, y1 = sorted((start[1], end[1]))
            points = ((x,y) for y in range(y0,y1+1) for x in range(x0,x1+1))
        else: points = line(*start,*end)
        for x,y in points:
            if 0 <= x < image["width"] and 0 <= y < image["height"]: rows[y][x] = color
    write_pixels(image, frame, rows)


def display_rows(image, frame=0, checker=True):
    result = []
    for y, row in enumerate(pixels(image, frame)):
        colors = []
        for x, rgba in enumerate(row):
            alpha = int(rgba[6:], 16)
            below = 190 if checker and (x//4+y//4)%2 else 225
            colors.append("#" + "".join(f"{(int(rgba[k:k+2],16)*alpha+below*(255-alpha)+127)//255:02x}" for k in (0,2,4)))
        result.append(tuple(colors))
    return tuple(result)


def import_image(path, prefix, images, kind="screen", frame_width=None, frame_height=None):
    """Import a whole image or split a sheet, preserving straight alpha.

    Pillow is optional for using the editor; this explicit import command
    reports how to install it when PNG/JPEG/BMP/GIF import is requested.
    No resize or palette quantization is performed behind the author's back.
    """
    try:
        from PIL import Image
    except ImportError as exc:
        raise EditorError("Image import needs Pillow: install your distribution's python3-pil package, or pip install Pillow in your Python environment.") from exc
    try:
        with Image.open(Path(path)) as source:
            w, h = source.size
            if w*h > 1048576: raise EditorError("Imported sheet exceeds the total 1,048,576-pixel budget.")
            fw, fh = frame_width or w, frame_height or h
            if fw < 1 or fh < 1 or w%fw or h%fh: raise EditorError("Frame dimensions must divide the whole sprite sheet exactly.")
            count = w//fw*(h//fh)
            result = new_image(prefix, images, Path(path).stem[:95], kind, fw, fh, count)
            source = source.convert("RGBA")
            result["frames"] = []
            for top in range(0,h,fh):
                for left in range(0,w,fw):
                    raw = source.crop((left,top,left+fw,top+fh)).tobytes()
                    result["frames"].append([raw[y*fw*4:(y+1)*fw*4].hex() for y in range(fh)])
            return result
    except (OSError, ValueError) as exc:
        raise EditorError(f"Cannot import image: {exc}") from exc


def original_sprite(document, settings, first=0, frames=16):
    from editor_model import resource_settings
    settings=resource_settings(document,settings)
    from editor_tiles import _capture_preview
    if not settings.get("data"): raise EditorError("Configure the Original game folder in Player setup first.")
    command = [str(document.validator), "source-sprite", "--data", str(Path(settings["data"]).resolve()),
               "--sprite", str(first), "--frames", str(frames)]
    try: return json.loads(_capture_preview(command))
    except (ValueError, UnicodeError) as exc: raise EditorError("The original sprite decoder returned invalid image data.") from exc


def import_tiles(path, prefix, images):
    """A large tile sheet becomes independent editable tiles, not 32 frames."""
    try:
        from PIL import Image
    except ImportError as exc:
        raise EditorError("Image import needs Pillow (python3-pil).") from exc
    result=[]
    with Image.open(path) as source:
        w,h=source.size
        if w%16 or h%16 or not w or not h or w*h>1048576:
            raise EditorError('Tile sheets must be multiples of 16 pixels and at most 1,048,576 pixels.')
        if len(images)+w//16*(h//16)>4096:raise EditorError('The image library holds at most 4096 images.')
        source=source.convert('RGBA')
        for y in range(0,h,16):
            for x in range(0,w,16):
                im=new_image(prefix,[*images,*result],f'{Path(path).stem[:70]} {x//16},{y//16}')
                raw=source.crop((x,y,x+16,y+16)).tobytes()
                im['frames']=[[raw[row*64:(row+1)*64].hex() for row in range(16)]];result.append(im)
    return result


def bind(art, slot, image_id):
    if slot not in SLOTS: raise EditorError("Choose a supported sprite slot.")
    art["bindings"] = [v for v in art["bindings"] if v["slot"] != slot]
    if image_id != "none": art["bindings"].append(dict(slot=slot, image=image_id))
