# Import and edit a CHI campaign

The C1–C3 and C4.1 implementation imports separate Original and Updated campaigns from the
supported DOS 1.03 files. Each project owns its resources, edition settings and
six save slots. It can run without the original installation after import.
Existing launcher Original/Updated games and their saves remain separate.

**Current editing scope:** all 15 maps, town placements, the native world
generator and jigsaws, entrances, town-walker routes, tiles, sprites, films,
screens, fonts, building portraits, supported audio references and native
dialogue overrides. **Project → CHI scripts** now edits labelled BLD dialogue,
conditions, branches, menus and compatible native operations. Updated also has
its external unit/weapon definitions and an editable broker entrance. Mission
definitions and service settings remain C4.2–C4.3. The Citadel/training
slice is verified against the built-in editions; importing the full resource
set does not establish execution coverage of every campaign branch.
See [progress](CHI_IMPORT_PROGRESS.md).
Original's added-unit list starts empty; its campaign mechs still use exact
compatibility templates rather than normalized library adaptations.

## Import through the launcher or editor

1. Build the application normally and launch `./ConstructionKit` or `./BtechPort`.
2. Choose **Import CHI** in the launcher, or **File → Import CHI campaign** in
   the Construction Kit.
3. Select the original game directory and choose **both**, **original** or
   **updated**. Select a new output folder inside an existing parent directory.
4. Press **Import**. Verification/extraction runs in the background; **Cancel
   import** discards unfinished staging and preserves existing projects.
5. Use **Edit** or **Play** beside a completed project. Both are registered in
   the launcher's game list. **My project → Choose project** also opens either
   `original` or `updated` subfolder, including projects created by the CLI.

The importer verifies all 77 required source files by SHA-256. A different,
incomplete or modified installation produces a specific file/version error.
It copies neither the DOS executable nor personal GAME saves. A failed import
publishes neither profile when Both is selected. Retry into a new destination;
resuming partial extraction is not currently supported.

The generated `IMPORT.json` lists input/output provenance and current editing
limits. It is informational; removing it does not turn the campaign into a
redistributable asset-free project. The manifest's imported dependency remains
an explicit original-derived-content boundary.

## Headless import and play

From the repository root:

```sh
python3 tools/chi_import.py --data "Original DOS" \
  --output "work/My CHI campaigns" --edition both

./build/btech-port --project "work/My CHI campaigns/original"
./build/btech-port --project "work/My CHI campaigns/updated"
```

On Windows, run the Python utility with the installed Python command and use
`build\btech-port.exe`. The importer resolves the platform's `btp-project`
validator automatically. Use `--validator PATH` for an explicit build.

Imported projects do not need the four external resource/cache arguments. Do
not combine `--project` with `--edition`. Updated defaults to Enhanced combat
and retains its supported Legacy selection; Original retains Original rules.

Reimporting creates new project IDs, even for the same edition. Keep the exact
old project for its saves. Normal Original/Updated saves cannot be loaded merely
by selecting an imported project; no automatic save migration is included here.

## Edit native dialogue

Open the project and choose **Project → CHI campaign**. Search/select a native
text ID, edit its text and press **Apply text**. An asterisk marks an override.
**Restore original text** removes the override. Apply/restore use the ordinary
Undo/Redo history; **Save project** persists the result. **Play** builds the
current validated project into its own test snapshot and save namespace.

Line breaks use the original carriage-return format. Text must fit the native
character and length limits; errors leave the previous document intact. This
view edits the 373 native text entries, not text embedded in BLD bytecode. Full
BLD text/control-flow editing is available in **Project → CHI scripts**; see the
[BLD authoring guide](BLD_AUTHORING.md).

The same operation is available without the GUI:

```sh
python3 tools/chi_editor.py --project "work/My CHI campaigns/original" \
  --index 87 --text "Computer control for this campaign?"

python3 tools/chi_editor.py --project "work/My CHI campaigns/original" \
  --index 87 --reset
```

`--text-file FILE` accepts multiline text instead. Changing runtime text changes
the strict content fingerprint; preserve the old revision for its existing saves.
Imported projects also support the existing **Campaign sources and build**
conversion, shared validation, Save/reopen and private playable-package export.

## Edit maps and the world

Choose **Project → CHI maps and world**, or open a local map in the project tree.
The usual Paint, Fill, selection, construction, pattern and contextual pixel
tools work on native maps. Save, Undo/Redo, Changes and protection, libraries
and Play use the same document as command-based edits. A native map's tile
artwork is separate from its movement/collision rule. Painting an ordinary
custom tile uses its terrain category; exact native rule/water properties are
available through `chi.update`.

The map toolbar exposes:

- **World, towns and jigsaws:** preview the original 1,024 × 1,024 world; drag towns to
  64-tile sector origins, edit generator seed/tables and select/edit/clone the
  8 × 8 terrain pieces. The 17 join bindings select the pieces used by the
  original generator. This preserves native generation rather than substituting
  the independent-game random-piece generator. Ctrl + wheel and the zoom box
  change the view.
- **Native map properties:** rename a map and set its origin.
  Moving the Citadel also moves its ruined state. Training returns, native BLD
  outdoor transfers, starport approaches, arena/prison exits and the device
  bearing follow the effective town origins.
- **Door slots:** edit a building name, active state, exact half-step position
  and its existing BLD building reference. The map's entrance markers also drag
  normally. In Updated, the broker marker can move, be renamed or disabled.
- **NPC routes:** name/configure eight town walkers and their native door routes.
  These are pedestrians, not new recruitable story characters.
- **Clone into map slot:** copy a town into another existing native map slot, retaining
  the target's location and stable map/door/NPC identities.

Use the **Start** drawing tool on the Citadel map to move the native starting
position. Starting party, money and story conditions remain C4.

New imports include `chi-spatial.json`. Opening the map tools on a C2 import
adds map support as one reversible document change; **Save project** persists
it. Make a copy first if you need the old imported project's saves: adding the
spatial document or editing runtime content changes strict save identity. There
is no automatic save migration. The launcher's existing built-in games and saves
are separate and are not upgraded by opening these tools.

Native limits are explicit: one 1,024-square world, 15 map slots, 16 entrance
slots and eight walker-route slots per map, origins aligned to 64 tiles. Maps
are at most 64 × 64; Citadel, ruined Citadel, starport and cache corridors retain
64 × 64, and the cache map room retains 32 × 24. The Citadel/starport require
space for their native adjoining battle sectors. All validation errors leave
the last valid project intact. Unrestricted new maps, missions, encounters and
authored event execution are not enabled in imported campaigns yet.

## Edit presentation resources

Choose **Project → CHI resources** or **Art, films, font and audio** on the map toolbar.
Select a resource to preview its effective unsaved content. **Copy / edit**
creates project-owned pixels and opens the existing sprite/pixel editor.
Direction/frame labels use the native sprite layout. You can also assign an
existing image. Animated terrain copies retain their loops and cadence.

The view includes the four terrain banks, animated terrain sheet, sprite sheet,
title/logo/borders, mech/statistics art, tinyland, native font, all 22 films and
available building portraits. Film durations are editable in native retraces;
native frame counts/dimensions remain fixed. Audio settings select the 18
verified speaker programs, playback speed (25–400%) and title music on/off.
This does not introduce a new music/sample scripting language.

Edits use `graphics.json` and optional `chi-presentation.json`. Native
sheet/sprite replacements are quantized to the chosen 16-colour display palette;
custom map images and film/portrait images retain RGBA. The standard art budget
is 1,048,576 pixels across at most 4,096 image definitions. Drawing, cloning and
library transfers retain origin metadata. Editing original-derived pixels does
not change their provenance.

Native previews read the project's own resources; Player setup's external DOS
path is unnecessary. If a local resource is missing or invalid, restore it from
your private backup or use **File → Import CHI campaign** into a new folder.
Reimport does not overwrite or repair edited projects in place.

## Headless spatial and resource editing

The [authoring CLI](AI_AUTHORING_GUIDE.md) and [operation reference](AUTHORING_COMMANDS.md)
use the same validation and history as the GUI:

```sh
python3 tools/author.py inspect "work/My CHI campaigns/original"
python3 tools/author.py inspect "work/My CHI campaigns/original" \
  --query objects --collection maps --limit 15
python3 tools/author.py inspect "work/My CHI campaigns/original" \
  --query objects --collection native-entrances --limit 16
python3 tools/author.py inspect "work/My CHI campaigns/original" \
  --query objects --collection native-resources --limit 30
python3 tools/author.py validate "work/My CHI campaigns/original"
```

Validated command batches support `chi.enable`, `chi.update`, `chi.town.move`,
`chi.jigsaw.bind` and `chi.art.copy`. `chi.update` addresses named world, map,
tile, entrance, NPC, service or presentation records; no binary offsets are
needed. Use the inspected project ID and revision in the ordinary batch envelope.
Native scopes use `chi.maps/<id>`, `chi.tiles/<id>`, `chi.world`, `chi.services`
and `chi.presentation`. Source conversion/build includes these documents as
normal sections. World review and regional protection use the effective native
generator, tile rules and art patches. Authored mission suites/checkpoints are
disabled for imports until their native story bridge is implemented in C4.

## Original-derived art and sharing

Generated CHI campaigns are private local content. Their whole imported resource
set, converted caches and later edited derivatives retain original provenance.
Do not add them to Git or distribute them as though the code's license covered
the original game data. Generated folders include an ignore file.

The application packager validates the indexed project snapshot, excluding
uncommitted/private authoring changes. Last Beacon's public baseline now contains
independently drawn placeholders for 20 original-derived tile images and a
`CHI-TILES.json` reconstruction recipe. The launcher can reconstruct those tiles
into a private cache using the configured original files. It preserves the
distributed project and refuses to overwrite an edited cache.

Of those 20 historical tiles, 17 contained custom pixel edits. Public recipes
restore the recorded original base tiles; they do not reproduce those private
edits. The owner's existing working files were preserved byte-for-byte, with a
backup under ignored `work/chi-import/asset-cleanup/`. Earlier Git history was
not rewritten.

Explicit asset-free export and local reconstruction use:

```sh
python3 tools/asset_provenance.py public-export \
  --project MY_PROJECT --output NEW_PUBLIC_PROJECT

python3 tools/asset_provenance.py reconstruct \
  --project NEW_PUBLIC_PROJECT --output NEW_PRIVATE_PROJECT --data "Original DOS"

python3 tools/asset_provenance.py check-staged
```

Public export rejects imported CHI campaigns, copied caches, declared unknown
origins and original-derived artwork without a supported exclusion/recipe.
For known private variants with an explicit base recipe, public export replaces
the pixels with the placeholder and retains the recipe. This does not grant
rights to other content or detect arbitrary copied art whose provenance was
stripped. Keep origin metadata when cloning/editing/importing assets. Publishing
complete edited campaign recipes will be expanded in later milestones.

## Verification and remaining work

The [contracts](CHI_IMPORT_CONTRACT.md) and [numeric inventory](chi-import-inventory.json)
describe the versioned extension, bounds, profile flags and dependency ownership.
The [progress ledger](CHI_IMPORT_PROGRESS.md) records exact tests, evidence and
platform limits. The [five-milestone plan](CHI_EDITABLE_CAMPAIGNS_PLAN.md) defines
the completed spatial/resource gate and remaining story/service and delivery gates.
