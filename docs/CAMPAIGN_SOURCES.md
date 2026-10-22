# Editable campaign modules (AI7a)

**Implemented and verified, 2026-10-22.** An optional source project separates
maps, events, unit definitions, artwork and dialogue into ordinary JSON files.
The Construction Kit and authoring commands use the same document operations
for source projects and existing package projects. The player still loads a
normal validated package; it needs neither Python nor an authoring service.

## Start in the editor

Open **Project → Campaign sources and build**. In an existing package:

1. **Create source copy…** creates a new directory. The current project and its
   unsaved work remain open and unchanged; valid drafts are included in the copy.
2. Open the new directory, which contains `SOURCE.json`.
3. Edit maps, dialogue, units and artwork with the usual tools. **Save** updates
   the owning modules and text files. Undo, recovery drafts and command batches
   use the same document.
4. **Play** compiles a private snapshot. **Build playable package…** creates a
   separate output directory suitable for `btech-port --project DIRECTORY`.

The launcher also accepts a source directory under **My project** and builds a
private package automatically. Its normal save slots follow runtime content,
so changing an authoring note does not hide saved games.

The sources page lists each object's owning file. Double-click a map, event,
unit, image or other supported object to open its normal editor. For collections
without a dedicated object editor, its source path is shown. Validation errors
include source paths; the Problems panel still navigates to the corresponding
object. Build includes current valid drafts without publishing them as Save.

Existing `project.json` projects require no conversion. Do not put `project.json`
beside `SOURCE.json`: that ambiguous pair is refused. Compiled outputs belong in
a separate directory. Build/export require a new destination and preserve any
existing output. Keep the source directory to continue authoring; a built package
is also editable as an independent package, but edits there do not flow upstream.

## Commands

```sh
python3 tools/author.py source convert examples/beacon-demo --output work/my-source
python3 tools/game_editor.py work/my-source
python3 tools/author.py inspect work/my-source
python3 tools/author.py source locations work/my-source --id beacon:welcome
python3 tools/author.py validate work/my-source
python3 tools/author.py source build work/my-source --output work/my-game
./build/btech-port --project work/my-game
```

`locations` is paginated with `--offset` and `--limit` (1..100). `source build`
returns file hashes and the runtime content fingerprint. `SOURCE-MAP.json` in
the output records object ownership and JSON paths; it is not a runtime input.
Ordinary `apply`, `review`, `scenario`, `suite`, render and catalogue commands
accept the source directory. Revisions include source organization, text,
scripts, artwork and editor metadata; requests cannot silently overwrite a
changed module. Closed-project commands cannot inspect unsaved GUI forms—use
the existing explicit local authoring session for that.

## Source layout and ownership

[`campaign-source-v1.schema.json`](../schemas/campaign-source-v1.schema.json)
describes the index. The compiler additionally checks paths, duplicate fields
and IDs, text references, ordering, dependencies and source budgets. The native
loader remains authoritative for gameplay semantics and resource limits.

```json
{
  "format": "btp-campaign-source-v1",
  "schema_version": 1,
  "sections": {
    "manifest": "source/manifest.json",
    "content": "source/content.json",
    "adventure": "source/adventure.json"
  },
  "modules": [
    {"section": "adventure", "collection": "maps", "file": "maps/depot.json"},
    {"section": "adventure", "collection": "events", "file": "missions/relay.json"}
  ],
  "texts": ["text/dialogue.json"],
  "files": {"EDITOR.json": "files/EDITOR.json"},
  "notes": {"brief": "Defend the relay, then escort a transport."}
}
```

This is an index example; each referenced file must contain valid game data.
Sections use the existing package schemas. `manifest` is required alongside
`content`; `adventure`, `art` and `presentation` are optional. The manifest's
`definitions`, `adventure`, `graphics` and `presentation` paths name **runtime
outputs**, not source files. Scripts and binary assets map their runtime paths
through `files`; dependencies must be included explicitly. Original CHI assets
remain an external dependency where declared by the game.

A module contains an array appended to its named collection. Conversion gives
each named object a separate stable filename, grouped by section and collection.
Authors may combine related events into one mission file, or reorganize module
paths by editing the index. There is no implicit globbing or include execution.
Unlisted files do not enter the build. Lists concatenate in declared module
order, after the base section's collection. IDs remain unchanged.

GUI and command edits return existing objects to their original owner file.
New objects enter the last module for their collection, or the base section
when there is no module. Removed objects leave an empty module. Optional
sections remain owned when their runtime manifest reference is removed, allowing
Undo/Redo of an artwork import without deleting author files. If a collection
is reordered across modules, the compiler writes an explicit
`order: {"adventure.events": ["namespace:first", "namespace:second"]}` table.
Every ID in that collection must occur exactly once in the ordering table.
Arrays are not sorted by name: their order affects native handles and saves.

Dialogue can use `{"$text": "relay:briefing.text"}` in place of a string. A text
file maps that key to the actual text. Conversion extracts event `text` and
`prompt` fields. GUI edits update the referenced string while preserving its
link. A shared text key must have a consistent value across all its uses; an
edit that makes those uses disagree is refused. Give independent dialogue
separate text keys rather than depending on last-writer behavior. The source
format reserves dictionaries containing `$text` for these references.

Source JSON is UTF-8, and generated JSON uses deterministic ASCII escaping and
sorted object keys. Source formatting is preserved for unchanged source files.
Inputs are limited to **4,096 declared files and 128 MiB total**. The limits are
reported by `author.py capabilities`. Symlinks, traversal paths, duplicate JSON
fields, non-finite numbers and conflicting file ownership are refused.

## Saves, provenance and recovery

Source compilation canonicalizes JSON. Converting an old package therefore
usually changes its exact runtime fingerprint even when its logical content is
equivalent. **Keep the original package for existing saves.** Use a new campaign
for the compiled copy, or deliberately use the existing save migration tool;
conversion does not migrate or overwrite saves automatically.

Repeated builds with equivalent runtime data produce identical runtime bytes.
Whitespace, source filenames, grouping, index `notes`, `EDITOR.json` descriptions,
layout and protection rules do not change gameplay saves. Text shown in the
game, map data, definitions, artwork, scripts and runtime array ordering do.
The native strict-content save policy continues to refuse incompatible content.

Existing provenance metadata and the usual README, credits, licence and source
documents travel with conversion and builds. A CHI-dependent package continues
to require the player's own original resources. Both supplied reference
directories remain read-only.

Save validates a complete compiled candidate first, then journals changes to
source files together. A crash rolls back the source transaction on reopening.
Concurrent external changes are refused. Recovery drafts retain both the
compiled baseline and raw source baseline; recovering into a copy retains
source ownership. Build stages and validates its output before publication.

## Reproducible two-planet example

```sh
python3 tools/source_campaign_demo.py --output work/my-cairn-planets --verify
python3 tools/game_editor.py work/my-cairn-planets/source
./build/btech-port --project work/my-cairn-planets/game
```

This creates a separate **Cairn Planets** project using Cairn Passage's tested
defence and escort missions. Its three local maps are placed over two 256 × 256
tile jigsaw planets. The generator records its command batch, creates modular
sources, compiles two packages and compares their runtime hashes. `--verify`
runs the ordinary-input two-mission route with checkpoints. It needs the normal
original resource paths and prepared caches. The user's Last Beacon is not
changed.

This is a source/build and composition demonstration, not a new long campaign
or proof of all world routes. Source conversion preserves the input adventure
version and its limits. **AI7b is now delivered:** an explicit v3 upgrade enables
larger campaigns. See [capacities, measured fixtures and save compatibility](CAMPAIGN_CAPACITY.md).
Native Windows Tk behavior remains unverified; Windows runtime packages are
checked separately under Wine. See [verification](TESTING.md#ai7a-campaign-source-modules--2026-10-22).
