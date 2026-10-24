# Shared Construction Library

**Project → Construction Library** stores tiles, building, wall and road
definitions, plus saved map patterns, independently of any one game. The same library is
available under **Construction tools** in the explorer and from the designers.

## Edit directly in the shared library

Select an entry and choose **Edit in library**, or double-click it. **New shared
design...** creates a Tile, Building, Wall, Road or Pattern directly in the
library. Neither operation imports anything into the open game.

Each entry opens a separate **Library workshop** with a 32 × 24 test canvas
(larger when needed to fit its sample). The canvas starts with clear terrain,
an accessible player position and the design's demonstration arrangement.

- **Edit definition** opens the normal building/wall/road designer or the tile
  pixel editor. Preview cells still support choosing, cloning and editing
  tiles, with surrounding tiles visible for alignment. Animation frames,
  collision, layers and source notes are retained.
- **Draw / stamp design** selects the actual drawing tool. Building styles can
  draw arbitrary footprints and courtyards with different heights; walls use
  0–3 stories; roads connect and choose their corners and junctions. A pattern
  stamps its stored block; a tile paints normally. The tools remain visible
  above the test canvas.
- For a shared **Pattern** (a saved map block), paint changes on the canvas,
  choose **Select** and drag its new rectangle, then **Update pattern from
  selection**. This replaces that pattern in memory and supports Undo.
- **Save shared design** or **Ctrl+S** saves the selected library entry and its
  canvas. Saving from its designer or pixel tab targets the same library
  scope. **Undo/Redo** also stay within that scope. **Workshop actions** offers
  Rename, **Save variant...**, Clear canvas and Close. A variant creates a new
  entry and leaves the current workshop editing the original.
- **Test canvas**, the main **Play** button and F5 play the active library
  workspace, including unsaved edits. Test saves are isolated from game slots.
  Use **Start** on the canvas to move the test player's starting position.

The library bundle contains only the shared definition and its required
tiles/art. Test terrain, extra trial tiles and placed constructions are saved
separately under the library's `workshops/` directory for that exact revision.
Reopening the entry restores its canvas; importing it into a game does not
copy the canvas. Back up the entire library folder to retain both. Exporting
a `.construction.json` file shares the reusable design only.

Closing with **Cancel** preserves unfinished work; discarding closes without
changing the saved entry. Recovery drafts also distinguish construction
workshops from unit-library editors. Concurrent edits use revision checking:
a stale workshop cannot overwrite a newer saved entry.

## Save and reuse a design

1. In a Building, Wall or Road designer, select a set and choose **Save to
   library**. In the project's Pattern Library, select a pattern and use the
   same button. In **Choose a map tile**, use **More → Save tile to shared
   library...** or the tile's right-click menu. Exporting from All tiles does
   not add a tile to the open game's palette merely to share it.
2. Name the shared copy. **New library copy** is the default. To revise an
   existing entry, select it in the shared library and choose **Update selected
   library entry** in the save form. Updates require the same type and the
   revision you loaded.
3. Open another project and **Project → Construction Library**. Filter by
   Tile, Building, Wall, Road or Pattern; search names, tags or descriptions.
4. Choose **Import into project**, or **Import and edit** to open its designer.
   Import is one Undo step. **Save** writes the game normally. A shared Tile
   imports just its definition and artwork; Import and edit opens its pixels.
5. Use the designer's **Draw on map** to draw new shapes with the imported
   building/wall/road parts. For a fixed pattern, use the project Pattern
   Library's **Use on map**.

A construction definition preserves its part assignments, demonstration
footprint and heights. It remains a drawing style: importing a cross-shaped
example does not restrict you to stamping crosses. Patterns instead preserve
their exact rectangular tile arrangement, including empty cells which leave
the destination terrain intact.

The designer shows assigned/required parts. New building and wall styles have
all **47 roof masks, eight side-face bands and the outside tile**; roads have
all **16 connection masks**. **Complete style** fills missing primitive parts
with editable starter artwork and refreshes generated joins from the style's
actual package-owned faces. It preserves explicit assignments and detects
hand-edited join pixels, retaining them as overrides. Existing map placements
keep their tiles until their construction is redrawn; painted details survive.

The part dropdown lists every part, even if the demonstration shape does not
use it. Roads explicitly offer **T-junction - branch north/east/south/west**,
corners, straights, ends and crossroads. The road brush chooses these masks
automatically from neighbouring road cells. The Footprint form also has four
T-shaped examples for editing their appearance.

The Road designer shows four **Right-angle turns** previews above the footprint:
**Turn N/E**, **Turn E/S**, **Turn S/W** and **Turn W/N**. These names identify
the two directions connected by each corner. Four **T-junction tiles** previews
sit above the main road preview: **T North**, **T East**, **T South** and **T
West**, named for the direction of the branch. Both groups remain available
regardless of the saved demonstration shape. The Footprint form also offers
all four turn shapes and all four T shapes.

Click a preview to select its centre tile, then use
**Choose tile**, **Edit pixels** or **Clone tile**; right-click provides the
same actions and **New tile for this part**. Pixel editing shows a 3 × 3 turn/junction
sample using the style's surrounding road tiles. Selecting a junction does not
reshape the saved demonstration footprint. For older incomplete road styles,
**Complete style** adds missing assignments while preserving existing artwork.

Walls default to **0 stories**, rendering only connected roof/top tiles. Heights
1..3 add side faces. Erase and Shift/right-drag remain separate actions. For
automation, `construction.draw` accepts `stories:0` for walls. A style's demo
footprint retains 0 as empty and uses **-1 for a roof-only wall cell**, preserving
older definitions; actual map construction cells store the displayed height 0.

Joined animation keeps source timing, with at most 256 combined frames. If a
needed face references original/indexed artwork, explicitly clone it into
project pixels or assign the join's tile: the generator never silently embeds
original assets. Complete coverage means all roles are assigned, not that an
artist has reviewed the appearance of every combination.

Imported copies are independent of the library. Later library revisions do not
silently alter games. Revise an entry directly in its workshop, or edit a
project copy and save it back explicitly. Conflicting tile/image IDs are remapped rather than replacing
existing pixels, collision definitions or editing layers. Identical assets
with identical metadata may be reused within a project.

## What travels with it

- Every referenced tile definition, including collision and minimap colour.
- Referenced package tile images, all animation frames and frame durations.
- Pixel editing layers, tile names, source notes and catalogue descriptions/tags.
- Available source-credit documents, preserved on further imports/exports.

Unrelated maps, characters, events, scripts and images are excluded. Import
validates the destination with the same native loader as the game; a failure
leaves the project and its history unchanged.

Independent indexed palette tiles are converted to their actual RGBA pixels
when exported, so a different project's palette cannot change their appearance.
Original land/destroyed atlas references remain references. Such an entry is
labelled **chi** and requires a CHI-dependent destination. A workshop can use
the open imported CHI project's locally decoded atlases to show these tiles
without a separate DOS-path setting. Explicitly cloning/editing original art
creates a local pixel copy with source metadata; cache/map-room tiles are also
materialized locally because external projects cannot address those banks.
These local original-derived pixels are not redistributable original assets.
Source attribution does not grant asset rights.

The default local folder is `work/construction-library/`. **Library folder...**
selects another persistent location. **Export bundle...** and **Load bundle...**
transfer `.construction.json` files between library folders or machines.
Loading a bundle creates a new shared copy. The old project-level
`.pattern.json` import/export remains available; import one into a project
Pattern Library, then **Save to library** to share it in the new system.

The library is user data outside Git; back up the selected folder. Closing a
tab, switching projects, deleting an imported copy or undoing an import does
not delete its shared entry. Library writes use a process lock, revision
check and atomic file replacement.

## For AI and other automated authors

No model or GUI is required. Search and contact sheets use the existing
authoring interface:

Project and library construction catalogue records include `coverage`, with
missing role names/counts. `construction.complete` takes `style` and optional
`refresh` (default true), using the same atomic completion as the editor.

```sh
python3 tools/author.py catalogue examples/battletech-demo \
  --source construction-library --query 'construction_kind:Building' --limit 20

python3 tools/author.py contact-sheet examples/battletech-demo \
  --source construction-library --data 'Original DOS' \
  --output work/shared-buildings.svg

python3 tools/author.py construction-export examples/battletech-demo \
  --id battletech-beacon:construction-3
```

Use `--construction-library DIRECTORY` to select the same folder as the editor.
Catalogue results provide the entry ID, revision, type, compiled preview size,
tile/image counts, dependency, description and exact bundle `file`. Reads do
not create a missing library. Contact sheets embed a static view of the stored
example; the bundle retains any tile animation.

For a batch, supply the returned file path to `construction.import`.
Give it an explicit new project ID, then use that ID in later commands:

```json
[
  {"op":"construction.import","file":"library/depot.construction.json",
   "id":"mission:depot-style"},
  {"op":"construction.draw","map":"mission:town","style":"mission:depot-style",
   "start":[4,4],"end":[9,9],"shape":"Courtyard","stories":3}
]
```

These operations belong inside the usual revision-checked request; paths
resolve relative to the request file. Importing a Road works with `road.draw`;
importing a Pattern works with `pattern.place`. Commands, GUI imports,
reviewed proposals and live authoring sessions share the same implementation.
Reviews retain the exact bundle bytes, so changes to an external library
cannot alter an already reviewed import.

Export refuses an existing entry unless you request `--variant` for a new
copy, or supply `--entry ENTRY_ID --expected-revision N` for an update.
These exports read saved project files; GUI **Save to library** includes valid
unsaved edits and drafts from its project snapshot.

The format is
[construction-library-v1.schema.json](../schemas/construction-library-v1.schema.json).
An entry is limited to 16 MiB; its tile/image closure observes the normal
4,096-definition and 1,048,576-pixel game budgets. Each library can contain up
to 4,096 entries. Source/project budgets are rechecked on import.

## Verification

[Testing](TESTING.md#shared-construction-library--2026-10-20) records cross-project
imports, real drawing from imported rules, pattern preservation, animation and
layer round trips, collision remapping, explicit updates, source preservation,
Undo/Redo, draft recovery, schema checks and headless authoring.

The direct-workshop pass adds five model tests in
`tests/test_construction_workshop.py` for tile/animation provenance, isolated
canvas persistence, stale revision rejection, variants, discarded edits and
pattern recapture. `python3 tools/construction_workshop_smoke.py` exercises
real GUI drawing for all three construction types, pixel painting, global
Save/Play targeting, save/reopen, pattern updates, cancel/discard/recovery,
animated tiles and creation of shared tiles. Its screenshots are written to
`work/construction-workshop-proof/`.
