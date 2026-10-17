"""Stable tile IDs, explicit jigsaws and world/city composition for authoring.

These operations only edit detached JSON. The player validates the candidate
and independently compiles the same layers before it can be saved or played.
"""
from __future__ import annotations
import copy
from collections import deque
from adventure_editing import composite, paint
from editor_model import EditorError


def token(tile):
    return tile.get("key", tile["id"])


def upgrade(adventure):
    """Losslessly remove the old character palette limit, in an undoable edit."""
    if adventure["schema_version"] == 2:
        return
    keys = {t["key"]: t["id"] for t in adventure["tiles"]}
    for scene in adventure["maps"]:
        for layer in [scene, *scene["overlays"]]:
            layer["rows"] = [[keys[c] if c != " " else " " for c in row] for row in layer["rows"]]
    for tile in adventure["tiles"]:
        tile.pop("key", None)
    adventure.update(format="btp-adventure-v2", schema_version=2, jigsaws=[])


def identity(prefix, values, stem):
    existing = {v["id"] for v in values}
    serial = 1
    while f"{prefix}:{stem}-{serial}" in existing:
        serial += 1
    return f"{prefix}:{stem}-{serial}"


def graphic_tile(adventure, prefix, sheet, graphic, terrain="clear", mini_color=2):
    for tile in adventure["tiles"]:
        if tile["sheet"] == sheet and tile["graphic"] == graphic:
            return token(tile)
    if len(adventure["tiles"]) >= 4096:
        raise EditorError("The tile library is full (4096 definitions).")
    upgrade(adventure)
    value = identity(prefix, adventure["tiles"], "tile")
    adventure["tiles"].append(dict(id=value, sheet=sheet, graphic=graphic, terrain=terrain, mini_color=mini_color))
    return value


def line(x0, y0, x1, y1):
    """Integer Bresenham line also closes gaps between mouse-motion samples."""
    dx, dy = abs(x1-x0), -abs(y1-y0)
    sx, sy, error = 1 if x0 < x1 else -1, 1 if y0 < y1 else -1, dx+dy
    while True:
        yield x0, y0
        if x0 == x1 and y0 == y1:
            return
        twice = 2*error
        if twice >= dy: error += dy; x0 += sx
        if twice <= dx: error += dx; y0 += sy


def draw(scene, layer, start, end, value, tool="Paint"):
    if tool == "Rectangle":
        x0, x1 = sorted((start[0], end[0])); y0, y1 = sorted((start[1], end[1]))
        points = ((x, y) for y in range(y0, y1+1) for x in range(x0, x1+1))
    else: points = line(*start, *end)
    for x, y in points: paint(scene, layer, x, y, value)


def flood(rows, x, y, value):
    if not 0 <= y < len(rows) or not 0 <= x < len(rows[0]): return
    old = rows[y][x]
    if old == value: return
    pending = deque([(x, y)])
    while pending:
        xx, yy = pending.pop()
        if 0 <= yy < len(rows) and 0 <= xx < len(rows[0]) and rows[yy][xx] == old:
            rows[yy][xx] = value
            pending.extend(((xx-1, yy), (xx+1, yy), (xx, yy-1), (xx, yy+1)))


def fill(scene, layer, x, y, value):
    target = scene if layer == 0 else scene["overlays"][layer-1]
    ox, oy = (0, 0) if layer == 0 else target["at"]
    if value == " " and layer == 0: raise EditorError("Transparent erase applies to overlays.")
    rows = [list(r) for r in target["rows"]]
    flood(rows, x-ox, y-oy, value)
    target["rows"] = ["".join(r) for r in rows] if isinstance(target["rows"][0], str) else rows


def create_world(adventure, prefix, width=32, height=32, name="World"):
    if not 8 <= width <= 128 or not 8 <= height <= 128 or width % 8 or height % 8:
        raise EditorError("World dimensions are 8..128 jigsaws, in multiples of eight. Each jigsaw is 8x8 tiles.")
    upgrade(adventure)
    if not adventure["jigsaws"]:
        add_jigsaw(adventure, prefix, name="Open ground")
    piece = adventure["jigsaws"][0]["id"]
    existing=all_worlds(adventure)
    if len(existing)>=16:raise EditorError('A project supports up to 16 planets.')
    if sum(len(w['pieces'])*len(w['pieces'][0]) for w in existing)+width*height>16384:
        raise EditorError('Planets share a total of 256 sectors (1,048,576 tiles). Choose a smaller world.')
    world=dict(id=identity(prefix,existing,'world') if existing else f'{prefix}:world',name=name,pieces=[[piece]*width for _ in range(height)],patches=[],cities=[])
    if existing:
        adventure.pop('world',None);adventure['worlds']=[*existing,world]
    else:adventure['world']=world
    return world['id']


def all_worlds(adventure):
    return adventure.get('worlds', [adventure['world']] if 'world' in adventure else [])


def get_world(adventure,world_id=None):
    values=all_worlds(adventure)
    if not values:raise EditorError('Create a world first.')
    return next((w for w in values if w['id']==world_id),values[0])


def add_jigsaw(adventure, prefix, rows=None, name="New jigsaw"):
    upgrade(adventure)
    if len(adventure["jigsaws"]) == 1024: raise EditorError("The jigsaw library is full (1024 definitions).")
    value = identity(prefix, adventure["jigsaws"], "jigsaw")
    adventure["jigsaws"].append(dict(id=value, name=name, rows=copy.deepcopy(rows) if rows else [[adventure["tiles"][0]["id"]]*8 for _ in range(8)]))
    return value


def world_size(adventure,world_id=None):
    pieces = get_world(adventure,world_id)["pieces"]
    return 8*len(pieces[0]), 8*len(pieces)


def patch_cells(world):
    result = {}
    for patch in world["patches"]:
        ox, oy = patch["at"]
        for y, row in enumerate(patch["rows"]):
            for x, value in enumerate(row): result[x+ox, y+oy] = value
    return result


def set_patch(world, cells):
    """Coalesce brush samples into horizontal runs, with no duplicate layers."""
    patches = []; pending = sorted(cells, key=lambda p: (p[1], p[0])); index = 0
    while index < len(pending):
        x, y = pending[index]; row = [cells[x, y]]; index += 1
        while index < len(pending) and pending[index] == (x+len(row), y) and len(row) < 64:
            row.append(cells[pending[index]]); index += 1
        patches.append(dict(at=[x, y], rows=[row]))
    if len(patches) > 4096: raise EditorError("Too many isolated world patches; use reusable jigsaws for broad terrain changes.")
    world["patches"] = patches


def world_tile(adventure, x, y, include_cities=True, patches=None, pieces=None, cities=None, world_id=None):
    w, h = world_size(adventure,world_id)
    if not 0 <= x < w or not 0 <= y < h: return None
    world = get_world(adventure,world_id)
    if include_cities:
        for scene in cities if cities is not None else adventure["maps"]:
            if scene["id"] not in world["cities"]: continue
            ox, oy = scene["origin"]
            if 0 <= x-ox < len(scene["rows"][0]) and 0 <= y-oy < len(scene["rows"]):
                return composite(scene)[y-oy][x-ox]
    patches = patch_cells(world) if patches is None else patches
    if (x, y) in patches: return patches[x, y]
    pieces = {p["id"]: p for p in adventure["jigsaws"]} if pieces is None else pieces
    return pieces[world["pieces"][y//8][x//8]]["rows"][y%8][x%8]


def assign_city(adventure, map_id, at=None, enabled=True, world_id=None):
    world=get_world(adventure,world_id)
    scene = next(m for m in adventure["maps"] if m["id"] == map_id)
    if enabled:
        if at is not None: scene["origin"] = list(at)
        if any(w is not world and map_id in w['cities'] for w in all_worlds(adventure)):
            raise EditorError('This city is on another planet. Remove that placement first, or clone the local map.')
        w, h = world_size(adventure,world_id); x, y = scene["origin"]
        if x < 0 or y < 0 or x+len(scene["rows"][0]) > w or y+len(scene["rows"]) > h:
            raise EditorError("The whole city must fit inside the world.")
        for other in adventure["maps"]:
            if other is scene or other["id"] not in world["cities"]: continue
            ox, oy = other["origin"]
            if x < ox+len(other["rows"][0]) and ox < x+len(scene["rows"][0]) and y < oy+len(other["rows"]) and oy < y+len(scene["rows"]):
                raise EditorError("City rectangles cannot overlap.")
        if map_id not in world["cities"]: world["cities"].append(map_id)
    elif map_id in world["cities"]: world["cities"].remove(map_id)
