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

Map, world and jigsaw tools are visible buttons above their canvases; the active
tool is highlighted. Ctrl + mouse wheel zooms around the pointer. Editable Zoom
dropdowns accept percentages (Enter applies); tile/pixel scales snap to whole
pixels. Event graphs, sprite editors and construction footprints/previews use
the same controls. Canvas edges limit scrolling. Zoom does not change game data.

- **Browse all...** selects any original/package tile and creates a tile definition
  when necessary. Tile definitions set collision separately from their appearance.
  Paint, line, rectangle, flood fill, eyedropper, selection/copy/paste and marker
  dragging share document Undo/Redo. A mouse gesture is one undo step. The
  blinking mouse square marks the tile that clicking will paint. **Edit pixels**
  opens its artwork; **Clone** creates an independently editable copy. Original
  indexed artwork is copied into the package before editing and its logical
  tile definition is updated, preserving all map placements.
  **Paint on: Visible tiles** edits the visible surface by default, including
  building overlays. **Base** and individual overlays remain explicit targets.
  Palette clicks return from construction/marker tools to Paint; Move markers
  is required for dragging labels, so they cannot intercept painting.
- **World / jigsaws → Create world** creates explicitly placed 8×8-tile pieces.
  New/clone/paint jigsaws, stamp them over the world, or paint individual tile
  patches. **Place city** overlays a local map at tile coordinates; **Move city**
  drags it, and **Edit city** opens its detailed map and entrances. **Play here**
  starts a fresh isolated playtest at the clicked world position.
  The planet selector switches between worlds; **Create world** adds another,
  and **Rename** edits its name. Transfer events connect their local maps.
- **Graphics / sprites** creates/imports/clones package images. Double-click an
  image for pencil/line/rectangle/fill/erase, RGBA colors, frame editing, preview
  and undo. Flip X/Y, rotate left/right, nudge, wrap, clear and grid controls
  operate on one frame or all frames. Apply commits the staged image to shared
  document history. Right-clicking an animated roster preview also opens these
  tools or selects a different sprite for that unit.
  Sprites open the [dedicated sprite editor](SPRITE_EDITOR.md), with labelled
  directions/poses, thumbnails, previous/next controls, independent playback,
  frame copy/paste and a faint previous-frame guide. Shared original poses are
  identified explicitly. Tiles/screens retain the general frame controls.
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

## Buildings, walls and roads

Open **Construction tools** in the project explorer, **Project > Building/Wall/
Road designer**, or **Map actions > Construct**. Each designer has named part
sets saved with the project. Reopening it returns to its existing tab. The map
editor's **Building**, **Wall** and **Road** buttons select a drawing mode and
reveal its **Construct** settings. Select a named tile style, then draw the
actual shape on the map. **Edit style...** opens the selected part set. When
that type has no style, its designer opens first; **Draw on map** returns to
the brush. The tool buttons remain visible while construction settings are
hidden for ordinary tile/marker editing.

Choose **Shape** (Brush, Line, Rectangle, Courtyard or Erase), **Stories** and
**Width**, then drag on the map. Rectangle fills a footprint; Courtyard creates
a hollow ring with the chosen thickness. Overlapping strokes extend one object
into arbitrary outlines. Shift + right-drag erases the selected shape; painting a new
height over a section creates stepped roofs. The live preview recalculates
outside edges, inner corners, roof levels and visible wall faces. A fixed
projection datum prevents existing floors shifting when another floor is raised.

**New building / New wall** starts a separate footprint. Select a saved object
in the dropdown beside Width to continue drawing it, including after reopening.
Each stroke rebuilds only that object's overlay and is one Undo operation,
including any newly required tile variants. Erasing an interior reveals the
underlying terrain; erasing the whole footprint removes its overlay. Escape
cancels the unfinished stroke, or leaves the tool if no stroke is pending.
Buildings allow **1–32 stories** and walls **1–3**, subject to the map bounds:
the footprint and projected faces must fit completely. Red preview outlines
indicate an invalid edge. Invalid drawing cannot silently clip the building.

**Save / Ctrl+S** persists styles, map footprints/heights, art and compiled terrain
together. The editor stores footprint records in `EDITOR.json`; the game uses
ordinary overlay tiles, with no new runtime dependency. Hand-painted tile
details made through the drawing/cut/paste tools are retained with the footprint
in the same Undo step. Rebuilding keeps those details where the cells still
belong to the projected shape; removing a section removes its details too.
Untracked external changes or layer rearrangements still trigger the stale-layer
guard instead of silently replacing them. Tile pixel edits remain shared.

To configure the style's demonstration shape and component tiles in its designer:

1. **Footprint...** starts a rectangle, cross, L shape, courtyard, line or empty
   grid, up to 32 × 32 cells. Walls and roads use thin cross/L presets.
2. Paint the footprint at the desired height. Left-drag draws; right-drag erases.
   Height **0** erases, buildings support **1–32 storeys**, walls **1–3**, and roads
   occupy one level. Painting different heights creates stepped roofs.
3. The live preview projects walls down and right in the CHI view. It resolves
   exposed roof edges, inward corners, south/east faces and top/middle/base
   bands. **Fit** shows the whole result; larger zooms allow detailed inspection.
4. Right-click a preview cell to **Choose tile**, **New tile for this part**,
   **Clone tile for this part**, **Edit tile pixels** or open **Tile properties**.
   Editing or cloning opens a 3 × 3 tile canvas using this exact preview cell's
   surroundings, including faces/corners. The centre is editable; the neighbours
   remain read-only and repeated placements of the same artwork update live.
   The buttons below the preview use the last clicked cell, or the first visible
   placement of a part selected from the list. Unused parts have empty neighbours.
   New/cloned images and their tile definitions enter the artwork library and
   map palette automatically. Choose/Edit/Clone are also below the preview and
   in its Inspector. **Choose tile** offers **Project tiles** and **All tiles**
   for buildings, walls and roads. All tiles includes every loaded sheet, with
   an optional sheet filter. Choosing an unregistered graphic adds it to the
   project palette automatically; choosing it again reuses its existing tile.
   Registration and the part assignment share one Undo operation. The chooser
   remembers its last collection, sheet filter, selection and scroll position
   per project, with separate positions for each collection/sheet. Preferences
   survive editor restarts and are stored outside the game data.
5. **Draw on map** arms the style for free drawing; the demonstration footprint
   remains in the designer. **Save pattern** stores that particular demonstration
   shape for optional stamping from the Pattern Library. Add entrances/events
   to completed map buildings with the usual marker tools.

Part assignments are shared by matching cells in that set. Editing a tile changes
every placement using its ID. Clone the tile for an independent variant. **New
set** creates independent preset art; **Duplicate** initially shares the original
set's tile references. **Footprint...** replaces the shape; ordinary height
painting and shape changes are undoable. New part roles receive editable default
artwork; old assignments remain available in the part selector for reuse.

The included roof, facade, brick and road graphics are small procedural editor
presets. They are not recovered original CHI building artwork. Assign original
tiles from your supplied game, your own tiles, or edited copies to customize a
set. Exterior wedges have a painted green ground background because game map
layers flatten to one tile per cell; edit those part pixels for another ground
surface. Heights describe the drawn exterior, not a new elevation/combat system.
Interior floors remain separate local maps linked by entrance/transfer events.

The Road designer also provides **Draw connecting roads**. Drag on the map:
straight sections, bends, ends, T junctions and crossroads are selected from
the set's 16 north/east/south/west connection patterns. Existing roads in that
set and selected layer reconnect as the stroke crosses them. A complete stroke
is one Undo operation. Width supports 1–8 tiles; Rectangle and Courtyard draw
larger areas or connected road rings. Shift + right-drag erases roads from this style,
updating neighbouring junctions. Base-layer road erasure uses the first clear
terrain tile; overlay erasure reveals the layer below. Slanting strokes form
connected orthogonal steps. Road tiles default to clear terrain; building and wall
parts default to blocking wall terrain. **Tile properties** changes collision
separately from the artwork.

## Pattern Library and terrain blocks

Use **Select** and drag a local-map rectangle, then **Ctrl+C** to copy visible
terrain, **Ctrl+X** to cut the Paint on target, or **Ctrl+V** and click to paste.
The default Visible tiles target changes the displayed surface across layers;
Fill also follows the visible connected region. Cut fills a visible/base-layer
selection with the first clear tile and clears an explicitly selected overlay
to transparent cells. Paste uses stable tile IDs, preserving the clipboard when
the palette upgrades beyond character keys. Empty pattern cells leave the
destination alone. The complete block must fit in its destination layer.

**Map actions > Patterns > Save selection** stores the rectangle in the
**Pattern Library**. Designers can **Save pattern** directly. The library offers
visual selection, placement, rename, clone, removal, import and export. Removal
deletes the saved pattern, leaving placed instances and artwork intact. Local
placements can use a new overlay. Choose a destination map before opening the
library; opening it through the world/jigsaw **Patterns...** button instead
targets that editor. Blocks are limited to 64 × 64 tiles.

Patterns are persisted in the project's `EDITOR.json`, alongside construction
sets, so ordinary project Save/Export retains them. `.pattern.json` exports carry
used tile definitions, owned artwork, pixel layers, labels and recorded tile
origins. Import remaps conflicting IDs and is one undoable operation. Original
sheet references require a CHI project; source-package indexed tiles must be
cloned to owned pixels before sharing with another package. Copying original
pixels does not change their origin or rights. **Assets and dependencies**
identifies recorded original tile copies, including clones of clones.

World terrain supports **Select**, Ctrl+C/Ctrl+X/Ctrl+V and the same library.
Paste adds tile patches over jigsaws. It rejects overlap with cities, whose
visible terrain belongs to their local map. Cutting world terrain leaves a
clear-tile patch. **Erase patch** restores the generated/stamped terrain below.

Jigsaws keep their 8 × 8 format. Their editor provides Paint, Line, Rectangle,
Fill, Eyedropper and Paste, a visual **Choose tile...** browser and a right-click
cell menu for New/Clone/Edit/Properties. Changing a preview cell assigns its new
tile to that cell and selects it as the brush. Save a complete jigsaw through
**Patterns... > Save selection**, or paste a stored block no larger than 8 × 8.

## Tile management and world creation

**Browse all... / Choose a map tile** now provides Add, Clone, Edit pixels,
Properties and Remove. **More > Clone ALL tiles in this view to project tiles**
copies the selected project palette, sheet or All tiles collection (excluding
hidden source graphics), with independent editable pixels and one Undo entry.
Existing collision definitions are preserved; unregistered original
graphics get terrain-band defaults that can be refined in Properties.

Deleting a project tile checks references in maps, jigsaws, patterns, building
stamps and construction sets, and offers a compatible replacement. Original
source-sheet graphics are immutable: Remove hides a source cell from this
project's chooser, and **More > Restore hidden source graphics** restores it.
Editing an original graphic creates package pixels. No reference file is changed.

**Create world** defaults to **128 × 128 jigsaws = 1024 × 1024 tiles**, matching
the original engine bounds in `port/core/world.c`. The visible **Create world**
button stays outside the scrolling form. On the first world, **Place current
local maps as cities** defaults to Yes; their existing positions must fit and
not overlap. Existing worlds are not resized automatically.

The current player shares **256 discovery sectors** across worlds and unplaced
local maps. An original-size world consumes that space; place its local maps as
cities. For several planets, choose smaller dimensions within the shared budget.
Each world uses 8–128 jigsaws per side in multiples of eight. Up to 16 planets,
4096 tiles, 1024 jigsaws and 1,048,576 owned artwork pixels remain the runtime
bounds. The new tools use the existing validated game formats and shared Save,
Undo/Redo and crash-recovery paths.

Actual Linux model, GUI, player-render and recovery evidence is recorded in
[Testing](TESTING.md#map-construction-and-tile-workflow--2026-10-18). Native Windows
Tk interaction remains unverified.

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
