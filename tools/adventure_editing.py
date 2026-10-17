"""Reversible authoring operations; only the C loader decides game legality."""
from __future__ import annotations
import copy
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
