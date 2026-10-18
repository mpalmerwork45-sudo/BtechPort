# BattleTech Construction Kit workspace

The editor now keeps maps, units, library designs, artwork and events in one
tabbed window. The separate SDL game window is used for playtesting.

## Start editing

Run `./BtechPort` on Linux or `BtechPort.cmd` on Windows and choose **Open editor**,
**New project** or **Unit Library**. From a checkout, this opens a project directly:

```sh
python3 tools/game_editor.py examples/battletech-demo
```

Use **New project** to make your own copy of a template. Choose the project name,
template and destination together. The independent Beacon and Vehicle lab
templates need no original game files; BattleTech templates use the original
files configured under **Project > Player setup**. Build the player and validator
with the launcher's **Build application** before editing if they are missing.

The welcome tab also lists recent projects. Opening another project reviews
unfinished work first. Separate editor processes can open separate games;
external-file checks prevent one from silently overwriting the other's changes.

## Find your way around

- **Project explorer:** search names or IDs; open units, weapons, equipment,
  worlds, local maps, events, artwork or the shared Unit Library.
- **Editor tabs:** reopening an asset selects its existing tab. **Open tabs**
  finds tabs that no longer fit across the top. **Back/Forward** restores the
  selected object and its view position.
- **Inspector:** properties and actions for the current selection. Sprite
  palettes/layers and event fields appear here. Scroll when more fields are
  available than fit in the panel.
- **Problems:** persistent errors, including the scope that failed. Double-click
  a row to return to its editor; field errors also stay beside their inputs.
- **Output:** validation results, background-operation timing and playtest paths.
  Select and copy text here when diagnosing a problem.

Drag panel dividers to resize them. **View** can hide the explorer, inspector or
Problems/output, change interface scale, or **Reset layout**. Layout, open
project tabs, zoom and selection are remembered separately from game content.
On a small display at 150–200%, the explorer initially collapses to leave more
room for editing; reopen it through View. Menus and scrollable fields keep less
frequent controls available. Tooltips explain compact controls.

## Maps, worlds and entrances

Open a local map from the explorer. The **Tiles** sidebar contains actual graphic
previews. Select a tile, then paint on the map. **Browse all...** opens the full
graphic chooser. **Tile actions** or the tile's context menu provides pixel
editing, properties and cloning. Double-click a tile to edit its pixels.
The chooser also adds/removes tiles and provides **More > Clone ALL tiles in
this sheet to project tiles**. These are independent editable copies, grouped
into one Undo operation.

The Tool selector includes paint, line, rectangle, fill, eyedropper, selection,
paste and marker tools. **Map actions** contains map/layer properties, building
stamps, collision and starting-formation overlays, graphics reload and setup.
Right-click the map to sample its tile. Select a rectangle and use Ctrl+C/Ctrl+X/
Ctrl+V on the canvas to copy, cut and paste. Copy captures visible terrain;
Cut clears the selected layer. A stroke or marker drag is one Undo operation;
Escape cancels the unfinished gesture.

**Construction tools** in the explorer, or **Project**, opens the Building,
Wall and Road designers and the **Pattern Library**. Paint a footprint with
heights, customize its generated parts by right-clicking preview tiles, and
choose **Use on map**. Buildings/walls paste as separate overlays; their parts
remain normal editable tiles. The road brush connects endpoints and junctions.
The Pattern Library stores reusable terrain blocks with the project and imports/
exports `.pattern.json` files. The [construction guide](M5_WORLD_ART_EDITOR.md#buildings-walls-and-roads)
explains part sets, storeys, collision, block placement and jigsaw editing.

Use the **Markers** sidebar or click a marker on the canvas to select it. Drag
to move it, double-click to edit it, or use the Inspector to open an entrance's
event and transfer destination. Marker coordinates snap to the game's half-tile
positions; painting uses whole tiles. The **People, shops and start** page edits
people, stock and the starting party.

Open a planet under **Worlds / planets** to paint its jigsaw sectors and position
city overlays. A city opens its local map directly. The world view has its own
brush; jigsaw editing opens another tab with drawing tools and a cell context
menu for choosing/creating/cloning/editing tiles. New worlds default to
**1024 × 1024 tiles**, the original CHI dimensions. The creation form can place
current local maps as cities. See the [world/art guide](M5_WORLD_ART_EDITOR.md)
for format limits, generation, multiple planets and graphic import.

## Units and the shared library

Choose a mech, vehicle or infantry character to edit its properties and watch
its animated preview. **Edit sprite** and **Choose sprite** are available in the
Inspector and preview context menu. Editing artwork opens its own tab directly.
Weapons and equipment use the same project scope and shared history.

**Project > Unit Library** opens the shared catalogue. Edit a library design in
its own labelled tab, including its sprite. Project and library designs with
the same ID still have separate drafts, Undo histories and save destinations.
Import designs into a game explicitly; updating a library design does not
silently replace copies already imported into games.

Use **Play > Preview library design** or **Preview design** in its Inspector to
try the active library design in its small preview scene. F5 still starts the
open game project.

Library loading, imports and exports show progress in the workspace. Import
validates a detached candidate before updating the game. The
[library guide](UNIT_LIBRARY_AND_LAUNCHER.md) covers variants, replacement,
dependencies and source credits.

## Artwork and animation

The main area is the pixel canvas. Tools, transforms and selection commands sit
above it; the Inspector holds colour, layers, animation settings and preview.
The frame strip below the canvas identifies direction, movement frame and the
underlying image. Drag the divider to give the canvas or strip more space.

Paint, fill, clone, flip, rotate, nudge, edit layers and copy/paste frames using
the existing art tools. Onion skin and playback help compare adjacent frames.
Completed strokes and frame/layer operations join the active scope's history.
Other clean previews refresh after changes. An unfinished field remains yours
until applied or discarded; refreshing another view does not overwrite it.

Editing original artwork first makes an explicit package copy. Its origin is
still original game art. The [sprite guide](SPRITE_EDITOR.md) explains shared
original gaits, directional sheets, named actions and 32 ms animation ticks.

## Events and dialogue

Open an event from the explorer or an entrance. Select a graph node to edit its
fields in the Inspector. **Nearby events** shows the selected event, its callers
and nearby outgoing branches; **All events** shows the full graph. Use Zoom and
**Fit**, or **Arrange** for an undoable automatic layout. Dragging a node retains
your manual arrangement.

Drag a named output to its destination node to connect it. **Connect** provides
a form alternative. **Dialogue** adds a branch to a choice event. **More** opens
objectives or checkpoints. Selecting another event applies valid pending fields;
invalid input keeps its error and remains available for correction.

Before deleting an asset, the editor shows its usages. Choose a compatible
replacement where supported, or update the references first. The replacement
and deletion form one validated Undo operation. Arbitrary references inside Lua
still require manual review; the editor does not rewrite script source.

## Save, close and Undo

| Command | What it saves |
| --- | --- |
| **Save / Ctrl+S / Save active scope** | The project or library design owning the active tab |
| **File > Save project** | Valid pending work across all project tabs and forms |
| **File > Save all** | Each dirty project/library scope, reporting failures separately |

The title and tabs show `*` for unsaved work. Applying a field or drawing a
stroke updates the in-memory document; Save validates and writes it. An invalid
field prevents that scope's save and retains its drafts. Save All can successfully
save one scope while another needs correction; it reports this partial outcome.

Validation runs in the background. If you edit while save validation is running,
the editor asks you to save again and writes nothing from the outdated candidate.
Once the durable write starts, it finishes safely. Edits made during that write
remain marked unsaved. A failed write retains the current work for retry; external
file changes are rejected rather than silently overwritten.

Closing a tab with a local draft offers Apply, Discard or Cancel. Applied edits
remain in memory even when their tab closes. Closing the whole editor reviews
dirty scopes together; Cancel or a failed save keeps work open. Closing a library
design also closes its dependent sprite tabs safely.

Undo first handles text in the focused input or an unfinished gesture, then
the active scope's labelled history. History is bounded; it is not a permanent
version archive. Library designs and the game have independent histories.

## Recover unfinished work

The editor checks changed drafts approximately every two seconds and writes
recovery data in the background. This includes invalid field text and unfinished
artwork. Recovery never publishes those drafts into the playable package.

On reopening a project or library design, choose **Recover**, **Review fields**
or **Discard recovery**. **File > Recovery drafts** revisits records later. If
the files changed externally, recover into an empty directory to preserve both
versions. The same **Recover into copy** action works when the original project
or library entry is missing. Save or close your current project before opening
the copy. Correct recovered invalid fields and use normal Save when ready.

A recovered copy has its own recovery identity. The source recovery record
remains available until explicitly discarded. If a field's view cannot be
reconstructed, its raw data remains in Output and the recovery record for review.
Closing the recovery prompt postpones the choice and protects its existing data.

Default editor state is `work/roster-editor`: `workspace.json` contains layout,
`recovery/` contains private drafts, and `play-snapshots/` contains test runs.
`--state-dir PATH` selects another location. None enters exported game content or
its save fingerprint. Recovery records are capped at 128 MiB; the editor reports
oversized records. A crash may lose edits since the last completed write.

## Play and deliver

Use **Play from start** (F5), **Play from here** on the selected map position,
or **Checkpoints and trace**. The editor validates a separate snapshot and starts
the SDL player from it. Test saves, player output and event traces stay in that
run's private directory; the path is reported in Output. Pending editor work and
ordinary gameplay saves stay available.

**Stop test** cancels that session's preparation or terminates its player process.
It leaves unrelated tasks and separately launched games running. The workspace
returns to the foreground after the player exits. **Project > Cancel background
tasks** requests cancellation where safe; an active durable save finishes first.

**File > Export game** creates a validated package in a new directory.
**Project > Assets and dependencies** gives the asset/provenance inventory;
**Project > Migrate an old save** provides explicit compatibility-checked save
migration. See the [delivery guide](CONSTRUCTION_KIT_DELIVERY.md).

## Keyboard reference

| Shortcut | Action |
| --- | --- |
| Ctrl+S | Save active scope |
| Ctrl+Z | Undo |
| Ctrl+Y or Ctrl+Shift+Z | Redo |
| Ctrl+Tab | Next tab |
| Ctrl+W | Close active tab |
| Ctrl+Shift+P | Find a command |
| F5 | Play project from start |
| Escape | Cancel the current drawing/drag gesture |
| Ctrl+C / Ctrl+V over the map | Copy selected tiles / choose Paste |

Modal forms keep their own key handling. Enter/Space activate focused buttons.
**Help > Shortcuts and help** also opens an in-application reference in Output.

## Verification limits

Linux Tk journeys, an isolated KWin desktop, scaling captures, bundled-runtime
launching and native engine tests are recorded in [TESTING](TESTING.md).
Windows engine cross-build/Wine checks pass. **Native Windows Tk interaction and
physical multi-monitor behaviour remain UNKNOWN**; they need checks on those
desktops. The refactor changes editor workflows, not Original/Updated combat
rules or package schemas.
