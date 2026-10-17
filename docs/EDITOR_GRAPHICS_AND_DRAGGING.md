# Visual map editing and marker dragging — 2026-10-17

The editor now shows actual terrain on the map and in a thumbnail palette.
Markers can be moved directly on the canvas. The main and map windows share
a restrained light theme, clearer toolbar groups, consistent spacing and
scrollable forms/lists that fit their supported minimum sizes.

Open the BattleTech demo:

```sh
python3 tools/game_editor.py examples/battletech-demo
```

Use **New project** to make your own copy, then **Maps / events**.

## Tiles and artwork

- **Tile palette:** select a thumbnail, choose **Paint**, and draw on the map.
  Painting a stroke remains one undo operation. **Collision / terrain** toggles
  the rule overlay without changing the art or collision definitions.
- **Edit tile → Choose graphic…:** browse every graphic in the normal terrain
  or destroyed-Citadel sheet, choose a thumbnail and **Use graphic**, then Apply
  the definition. The form shows a larger preview. Package-owned tiles use the
  same picker with their own palette. **Duplicate** makes a new tile definition
  when the new graphic should not replace an existing one throughout the map.
- **Player setup → Original game folder:** choose the original resource folder
  for a CHI project. Saving setup reloads open map previews; **Reload graphics**
  is also available on the map toolbar. A missing resource displays guidance
  and keeps terrain/key fallback editing available. Independent projects read
  their declared presentation snapshot and need no original files.

The map preview and picker use the gameplay terrain palette, with nearest-pixel
scaling at 16/24/32-pixel map zoom. Both `chi:land` and `chi:destroyed` provide
250 static tiles. Animated terrain is shown as its source tile; the runtime
continues to animate it. Overlay compositing is unchanged.

The C `btp-project preview-tiles --data DIRECTORY --sheet SHEET` command reads
the existing resource loader and emits a fixed binary P6 atlas over its pipe.
The frontend's map palette supplies the colors; there is no second Python
decoder or palette mapping. The editor bounds pipe output and time, keeps
decoded art in memory, and adds no original art to projects, exports or preview
cache files. It requires the updated `btp-project` executable built with the
repository. Runtime application dependencies remain Python/Tk; Pillow is used
only by the existing GUI screenshot checks.

## Moving and editing markers

Click and drag an existing **door, NPC, party spawn, enemy or campaign start**.
Grabbing its label works too, preserving the initial pointer offset. Markers
take priority over painting; **Move markers** is useful when selecting empty
ground should not paint. A ring shows the selected marker, and the sidebar
lists all placed markers, including individual encounter enemies.

Movement snaps to half-tile coordinates and stays within the map. Releasing
creates one undo operation. **Escape** or Undo during an unfinished drag
cancels it; clicking without movement creates no edit. Scroll position and
zoom are included in pointer conversion. Selecting an overlapping marker in
the sidebar chooses which one the next drag will move.

Double-click a marker or its sidebar entry to edit its details. Moving an
encounter's party spawn leaves its enemies in place; each enemy can be moved
individually. IDs, events, definitions and other coordinates stay unchanged.
Deleting an enemy removes only that enemy; deleting a party marker removes
its encounter. The campaign start is moved or edited, rather than deleted.

Two doors/NPCs cannot occupy the same coordinate. Other placement rules remain
the shared C validator's responsibility: **Validate/Save** catches blocked
spawns, invalid formations and unresolved references. This permits an author
to move terrain and markers as one unfinished edit without duplicating game
collision logic in the GUI. Failed validation preserves disk files.

These UI changes do not edit the shipped game packages or change their strict
save fingerprints. Authored edits still require a fresh campaign, as before.
The scene-composition tools still need multi-tile stamps, selection/group moves
and formation-footprint overlays; this increment provides visual tile selection
and individual marker manipulation.

## Verification

| Check | Result |
| --- | --- |
| Full native CTest | **69/69**, 43.68 s |
| Full Python suite | **88/88**, 3.20 s |
| Focused Windows/Wine CTest | **3/3**, 0.89 s |
| Focused ASan/UBSan/LeakSanitizer | **3/3**, 1.48 s |
| Tile tests using sanitized decoder | **8/8** |
| Windows vs Linux preview output | Both 196,623-byte atlases identical |
| Linux Tk main editor | Forms, loadouts, undo/redo, save/reopen and player launch pass |
| Linux Tk map/event workflow | Painting, overlays, events, placement, export and Play here pass |
| Linux Tk visual workflow | Original map/thumbnail colors, picker, all marker kinds, zoom/scroll, cancel, bounds, history and save/reopen pass |

The visual workflow also checks missing-art fallback/reload, main-window Undo
during a drag, last graphic 249 on the destroyed sheet, and visible controls
at main-window 940×690/map-window 960×650. Screenshots were inspected at
1024×768; private-display snapshots remain under ignored
`work/editor-graphics-{main,map,picker,drag}.png`.

Python tests cover malformed/truncated RGB output, whitespace-valued pixels,
binary atlas indexing, pipe limits/timeouts, package snapshot art, stable marker
references, preserved IDs/events, duplicate positions and atomic single-drag
history. Reference file metadata remains unchanged. Native/Windows builds are
warning-free; sanitizer compilation retains the two earlier renderer conversion
warnings, with no runtime sanitizer errors.

```sh
python3 -m unittest discover -s tests -p 'test_editor_tiles.py'
python3 -m unittest discover -s tests -p 'test_marker_editing.py'
python3 tools/native_smoke.py --editor-visual-only
python3 tools/native_smoke.py --map-editor-only
python3 tools/native_smoke.py --editor-only
```

The same Python/Tk GUI source and binary decoder are supplied for Windows.
Native Windows desktop GUI interaction remains unverified; Wine decoder
equality and CTest checks do not establish that separate result. No new original
gameplay equivalence claims are made by this UI increment.
