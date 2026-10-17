# World, graphics and drawing editor

This increment extends authored projects. Original/Updated CHI campaigns and
both reference directories remain separate and unchanged.

Implementation milestones:

1. Versioned, validated tile IDs beyond the old character/byte palette; a
   package-owned RGBA graphics library and reversible, atomic editor saves.
2. Editable 8x8-tile jigsaws and a broader world made from them, with local
   city maps overlaid at their authored world coordinates. Ordinary travel,
   collision, entrances, the overhead map and saves use the same composition.
3. A graphics browser, import/clone controls and a pixel/frame editor. Tiles,
   unit sprites, entrance icons and full-screen event pictures can use owned
   graphics. Imports are explicitly authored package assets.
4. Map/world drawing tools and placement controls, undo/redo and playtesting.
   Existing hand-edited demo content is preserved.
5. Shared-validator, ordinary-input, save/load, rendering and GUI checks;
   native, Windows and sanitizer verification, documentation and local commits.

Acceptance distinguishes independently authored features from original-game
fidelity. Reusable jigsaws in a custom world are explicitly placed; this first
authoring increment does not silently run CHI's procedural generator or change
the original world's seed. Limits and actual verification results follow below.

## Using the tools

Run `python3 tools/game_editor.py examples/beacon-demo` (or your own project).
Use **New project** to make an independent copy. Open **Maps / events**.

- **Browse all...** selects any original/package tile and creates a tile definition
  when necessary. Tile definitions set collision separately from their appearance.
  Paint, line, rectangle, flood fill, eyedropper, selection/copy/paste and marker
  dragging share document Undo/Redo. A mouse gesture is one undo step. The
  blinking mouse square marks the tile that clicking will paint. **Edit pixels**
  opens its artwork; **Clone** creates an independently editable copy. Original
  indexed artwork is copied into the package before editing and its logical
  tile definition is updated, preserving all map placements.
- **World / jigsaws → Create world** creates explicitly placed 8×8-tile pieces.
  New/clone/paint jigsaws, stamp them over the world, or paint individual tile
  patches. **Place city** overlays a local map at tile coordinates; **Move city**
  drags it, and **Edit city** opens its detailed map and entrances. **Play here**
  starts a fresh isolated playtest at the clicked world position.
  The planet selector switches between worlds; **Create world** adds another,
  and **Rename** edits its name. Transfer events connect their local maps.
- **Graphics / sprites** creates/imports/clones package images. Double-click an
  image for pencil/line/rectangle/fill/erase, RGBA colors, frame cloning, preview
  and undo. Flip X/Y, rotate left/right, nudge, wrap, clear and grid controls
  operate on one frame or all frames. Apply commits the staged image to shared
  document history. Right-clicking an animated roster preview also opens these
  tools or selects a different sprite for that unit.
  PNG/JPEG/BMP/GIF imports need Pillow (`python3-pil`); sprite-sheet frame sizes
  must divide the input exactly. **Tile sheet** imports all 16×16 cells as
  separate images, including sheets with more than 256 tiles.
- **Use as map tile** adds a library image to the paint palette. Entrance forms
  can assign an icon; say/choice/finish events accept a portrait image, and
  **picture** events show a full-screen image until Space/Enter continues.
  Sprite roles replace player/NPC/enemy/walker/wreck graphics. **Copy original**
  decodes a local original sprite into an editable package copy; it does not
  modify the originals or grant redistribution rights to copied artwork.

Save validates the complete candidate with the C player before writing. A
rollback journal protects updates to the manifest, maps, definitions and new
graphics file together. External edits are preserved and reported. Undo also
reverses automatic v1-to-v2 map conversion.

## Formats and bounds

`btp-adventure-v2` uses stable tile IDs in row arrays. Existing v1 character maps
still load unchanged. Limits: 4,096 tiles, 1,024 jigsaws, 16 local maps (each at
most 64×64 tiles), and up to 16 worlds, each 64–1,024 tiles wide/high in 64-tile
increments. Worlds share 256 compiled sectors (1,048,576 terrain tiles total)
and a 16,384-cell discovery budget; unplaced local maps reserve their own
discovery cells. Cities use map origins and cannot overlap within a planet.
The same coordinates can be used on different planets. Explicit patches override jigsaws;
city maps and their local overlays override patches. This is a new authoring
format, not an import/export editor for original MTP files or their terrain-join
descriptors. CHI's original procedural world generator is unchanged.

The optional project `graphics` file uses `btp-art-v1`: RGBA hex scanlines,
1–32 frames/image, 16×16 tiles, up to 64×64 sprites/icons and 320×200 screens.
There are at most 4,096 images and 1,048,576 pixels across all frames. Event
portraits must fit 88×88. Adventure/art files have a 16 MiB/300,000-node bound.
Runtime sector handles and tile IDs are 16-bit; authored saves use BTPn/v49.
Each planet has separate exploration, overhead-map bounds and saved identity.
Package fingerprints include the graphics file. Edited content requires a fresh
playtest; existing saves continue to require their exact package.

## Verification, first editor increment

**VERIFIED by automated tests:** 69/69 native C tests; 20 Python editor tests,
including new large tile/jigsaw/world traversal, last-sector save/load,
composition, malformed references, picture pixels, image cloning and interrupted
multi-file-save recovery. Real Tk checks pass for original tile/marker tools and
the new pixel/frame, world, city-drag and save/reopen workflows. Screenshot:
`work/world-art-editor.png` (local evidence). Platform checks are recorded with
the next unit/vehicle increment; native verification is not a Windows claim.

The [vehicle and planet increment](M5_VEHICLES_AND_PLANETS.md) extends this
checkpoint with multiple worlds, new definitions/equipment, per-unit graphics,
ten editable vehicle presets, direct tile editing and the typography corrections.
Its final platform and GUI results are in [TESTING](TESTING.md).
