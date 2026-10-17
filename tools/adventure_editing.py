"""Reversible authoring operations; only the C loader decides game legality."""
from __future__ import annotations
import copy
import math
from numbers import Real
from editor_model import EditorError

OPS = ("end", "say", "choice", "if", "flag", "reward", "recruit", "transfer", "shop", "battle", "lua", "finish")


def new_id(document, collection, stem):
    prefix = document.manifest["package_id"]
    existing = {v["id"] if isinstance(v, dict) else v for v in document.adventure[collection]}
    serial = 1
    while f"{prefix}:{stem}-{serial}" in existing:
        serial += 1
    return f"{prefix}:{stem}-{serial}"


def composite(scene):
    rows = [list(row) for row in scene["rows"]]
    for layer in scene["overlays"]:
        ox, oy = layer["at"]
        for y, line in enumerate(layer["rows"]):
            for x, tile in enumerate(line):
                if tile != " " and 0 <= y+oy < len(rows) and 0 <= x+ox < len(rows[0]):
                    rows[y+oy][x+ox] = tile
    return rows


def paint(scene, layer, x, y, key):
    target = scene if layer == 0 else scene["overlays"][layer-1]
    ox, oy = (0, 0) if layer == 0 else target["at"]
    x, y = x-ox, y-oy
    if not 0 <= y < len(target["rows"]) or not 0 <= x < len(target["rows"][0]):
        return
    if key == " " and layer == 0:
        raise EditorError("Transparent erase applies to overlays; choose a base tile.")
    row = target["rows"][y]
    target["rows"][y] = row[:x] + key + row[x+1:]


def event_template(document, op, identity=None):
    a = document.adventure
    end = next((e["id"] for e in a["events"] if e["op"] == "end"), a["events"][0]["id"])
    event = dict(id=identity or new_id(document, "events", "event"), op=op)
    if op in ("say", "choice", "finish"):
        event.update(text="A new chapter begins.", portrait="none")
    if op not in ("end", "finish", "choice", "if", "battle", "lua"):
        event["next"] = end
    if op in ("reward", "recruit", "transfer", "battle", "lua"):
        event["failure"] = end
    if op == "choice": event.update(options=[dict(label="Continue", next=end)], cancel=end)
    if op in ("if", "flag"): event.update(flag=a["flags"][0] if a["flags"] else "", value=1)
    if op == "if": event.update(then=end, **{"else": end})
    if op == "reward": event["credits"] = 100
    if op == "recruit": event["person"] = a["people"][0]["id"]
    if op == "transfer": event.update(map=a["maps"][0]["id"], at=list(a["start"]["at"]))
    if op == "shop": event["shop"] = a["shops"][0]["id"] if a["shops"] else ""
    if op == "battle": event.update(encounter=a["encounters"][0]["id"] if a["encounters"] else "", win=end, loss=end, flee=end)
    if op == "lua": event.update(script=document.manifest.get("scripts", [{}])[0].get("id", ""), routes=[end])
    return event


def copy_adventure(document):
    if document.adventure is None:
        raise EditorError("This project uses the CHI campaign. Open an authored template or create an independent game first.")
    return copy.deepcopy(document.adventure)


def _marker_scene(adventure, scene_index):
    if isinstance(scene_index, bool) or not isinstance(scene_index, int):
        raise EditorError("Choose an existing map before moving a marker.")
    scenes = adventure.get("maps", [])
    if not 0 <= scene_index < len(scenes):
        raise EditorError("The marker's map no longer exists.")
    return scenes[scene_index]


def scene_markers(adventure, scene_index):
    """Return detached marker descriptions in drawing/list order.

    A ref is (kind, map ID, object ID, enemy index or None). IDs keep a door
    or encounter selected when its collection is reordered; the map ID stops
    an in-progress drag from affecting a different map. Enemy records have
    no authored IDs, so their index is valid until the enemy list is edited.
    Coordinates and labels are copies, never mutable document references.
    """
    scene = _marker_scene(adventure, scene_index)
    map_id = scene["id"]
    markers = []

    def append(kind, identity, at, label, enemy_index=None):
        markers.append(dict(ref=(kind, map_id, identity, enemy_index),
                            at=list(at), label=label))

    for door in scene.get("entrances", []):
        kind = "npc" if "person" in door else "entrance"
        append(kind, door["id"], door["at"],
               ("NPC " if kind == "npc" else "Door ") + door["name"])
    for encounter in adventure.get("encounters", []):
        if encounter["map"] != map_id:
            continue
        name = encounter["id"].split(":")[-1]
        append("party", encounter["id"], encounter["party_at"],
               f"Fight {name} / party")
        for index, enemy in enumerate(encounter["enemies"]):
            definition = enemy["definition"].split(":")[-1]
            append("enemy", encounter["id"], enemy["at"],
                   f"Fight {name} / enemy {index + 1}: {definition}", index)
    start = adventure.get("start", {})
    if start.get("map") == map_id:
        append("start", "start", start["at"], "START")
    return markers


def move_marker(adventure, scene_index, ref, at):
    """Move exactly one marker, returning whether its coordinate changed.

    The UI can update a detached drag preview repeatedly, then submit that
    snapshot once for undo. Movement snaps to the nearest half-tile position
    and rejects out-of-map destinations and overlapping entrances. Terrain
    and full formation legality still belong to the shared C validator.
    No document data changes on an invalid or stale reference.
    """
    scene = _marker_scene(adventure, scene_index)
    if not isinstance(ref, (tuple, list)) or len(ref) != 4:
        raise EditorError("The marker selection is stale; select it again.")
    ref = tuple(ref)
    kind, map_id, identity, enemy_index = ref
    if (kind not in ("entrance", "npc", "party", "enemy", "start")
            or not isinstance(map_id, str) or not isinstance(identity, str)
            or (kind == "enemy" and (isinstance(enemy_index, bool)
                or not isinstance(enemy_index, int) or enemy_index < 0))
            or (kind != "enemy" and enemy_index is not None)):
        raise EditorError("The marker selection is stale; select it again.")
    if map_id != scene["id"]:
        raise EditorError("The marker belongs to a different map; select it again.")
    if len([m for m in scene_markers(adventure, scene_index) if m["ref"] == ref]) != 1:
        raise EditorError("The marker selection is stale; select it again.")
    if not isinstance(at, (tuple, list)) or len(at) != 2:
        raise EditorError("A marker needs an x and y coordinate.")
    snapped = []
    for value in at:
        try:
            if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
                raise ValueError
            snapped.append(math.floor(value + 0.5))
        except (ValueError, OverflowError, TypeError) as exc:
            raise EditorError("Marker coordinates must be finite numbers.") from exc
    width, height = len(scene["rows"][0]) * 2, len(scene["rows"]) * 2
    if not 0 <= snapped[0] < width or not 0 <= snapped[1] < height:
        raise EditorError("The marker must stay inside the map.")

    if kind in ("entrance", "npc"):
        matches = [door for door in scene["entrances"] if door["id"] == identity]
        if len(matches) != 1:
            raise EditorError("The marker ID is ambiguous; fix duplicate IDs before moving it.")
        record = matches[0]
        coordinate = "at"
        if any(door is not record and door["at"] == snapped for door in scene["entrances"]):
            raise EditorError("Another entrance or NPC already occupies that position.")
    elif kind in ("party", "enemy"):
        encounter = next(e for e in adventure["encounters"]
                         if e["id"] == identity and e["map"] == map_id)
        record = encounter if kind == "party" else encounter["enemies"][enemy_index]
        coordinate = "party_at" if kind == "party" else "at"
    else:  # The exact ref check above permits only the fixed campaign-start ref.
        record, coordinate = adventure["start"], "at"
    if record[coordinate] == snapped:
        return False
    record[coordinate] = snapped
    return True
