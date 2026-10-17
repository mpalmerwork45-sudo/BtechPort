# M5a definitions and M5b project foundation

Implemented 2026-10-17. This completes tasks 1 and 2 of the
[editor roadmap](ENGINE_AND_EDITOR_PLAN.md#13-next-five-tasks-toward-an-editor).
It records editable **CHI-dependent games**. Subsequent increments now add
[maps/events](M5_MAPS_EVENTS_EDITOR.md) and an
[independent demo with the map/event editor](M5_INDEPENDENT_GAME_EDITOR.md).
The explicit original-dependency rules below apply to CHI-profile projects.

## Create, validate and play

Build normally, with the existing two-job limit:

```sh
./scripts/build.sh
```

Export the current 31-model Updated pack into a **new directory**:

```sh
./build/btp-project export work/my-game \
  --roster content/updated/roster.json --combat-data work/combat-data.bin
./build/btp-project validate work/my-game
```

This writes `project.json`, `content.json`, all supplied building portraits and
explicit portrait references. It also copies the source pack's available
README, license, source manifest and artwork attribution. Their source filenames
may differ from the exported layout. Original DOS binaries, graphics, sound and
extracted caches are **not** copied into the project. Export refuses an existing
directory. An interrupted export can leave a partial new directory; validation
will report missing/incomplete inputs.

Edit the JSON files in any text editor, validate again, then play:

```sh
./build/btech-port --project work/my-game \
  --data "Original DOS" \
  --dialogue-data work/talk-data.bin \
  --combat-data work/combat-data.bin \
  --world-data work/world-data.bin
```

Use `btech-headless` with the same arguments for replays. On Windows, use the
corresponding `btp-project.exe`, `btech-port.exe` or `btech-headless.exe` and
native paths. Both frontends use the same loader and validator. Paths passed on
the command line are relative to the working directory; references **inside**
`project.json` are relative to the project directory. All four dependency paths
must be explicit with `--project`, even when they happen to match the old
defaults. `--project` cannot combine with `--edition` or `--export-original`.

The invented [Workshop example](../examples/project-demo/) can be played with
the same command using `--project examples/project-demo`. It has two models and
three weapons, including two different beam weapons using the same visual
behavior. New project mechs are available through the existing Starport broker.
Training and story encounters retain their CHI behavior and original loan mechs.

For validation alone, original files and caches are unnecessary:

```sh
./build/btp-project validate examples/project-demo
./build/btp-project validate-content examples/project-demo/content.json
python3 tools/validate_content.py examples/project-demo
```

The Python command invokes the C validator; it does not implement competing
rules. The C API is in [definitions.h](../port/data/definitions.h) and
[project.h](../port/data/project.h). Errors identify the file, definition ID and
field path where available, for example
`content.json: $.mechs[workshop:rook].movement.walk`.

## Authoring contract

[content-v1.schema.json](../schemas/content-v1.schema.json) describes structural
fields; the shared C loader also validates references, capacities, supported
behaviors and rule consistency. [project-v1.schema.json](../schemas/project-v1.schema.json)
describes the manifest. Unknown fields, duplicate keys/IDs, unsupported equipment,
unresolved references, excessive nesting and inputs over 1 MiB fail explicitly.
The current font/reader supports printable ASCII, including escaped quote,
backslash and slash characters.

| Definition | Supported authoring fields |
| --- | --- |
| Mech | Stable ID, full name, short UI label, mass, movement, armor, structure, limb actuator masks, heat sinks, loadout, price and presentation ID |
| Weapon | Stable ID, full name, short UI label, supported behavior, damage, heat, projectile count, ranges and ammunition ID |
| Ammunition | Stable ID and price per shot; installed capacity is in the mount definition |
| Presentation | Stable ID and explicit original Locust or red Stinger sprite source |
| Services | Stable broker/reload IDs with implemented CHI behavior; purchase prices and reload prices come from definitions |
| Rules | Original compatibility or the existing Updated LRM/planner profile, with its distance scale and minimum/range brackets |
| Portrait | Stable asset ID, building slot and explicit package-relative ANM file |

Full names can contain 95 characters. The existing interface uses separate
15-character mech and 11-character weapon labels; the broker confirmation also
shows the full mech name. Mech labels start with an uppercase letter. No author
assigns a save code or writes a 125-byte record. The new format allows **256
models**, **256 weapons**, **256 ammunition definitions** and **256 sprite
presentation definitions**. The released `btp-chi-roster-v1` adapter retains its
old 32-model/save-code contract unchanged.

Definitions remain immutable during play. Owned damage, crew and ammunition
remain separate game instances. `btp_definitions_compile` is the explicit CHI
adapter; internally the existing campaign still uses its compact records and
package-local handles. These implementation details are absent from authored
JSON. Saves validate the entire package before interpreting those handles.

The supported weapon behaviors are the existing 17 mech weapon families:
lasers, PPC, autocannons, machine gun, flamer, LRM and SRM sizes. Multiple
definitions can share a behavior while having different stats and labels;
combat queries, damage, heat, range displays and queued battle messages resolve
the actual mounted definition. Existing behavior supplies graphics, sound,
cluster rules and ammunition consumption. Merely naming Gauss, ECM, AMS or a
new scripted ability does not implement it, and validation rejects it.

Remaining CHI-profile limits are explicit: four owned mech bays, ten mounted
weapons, the original body locations/component capacities, 20–100 tons,
walking/jumping values up to 12, at most 30 heat sinks, damage up to 20 per
projectile, heat up to 15 per shot and a maximum volley of 255 damage. Projectile
counts must match the selected behavior. Ammo capacity is 1–254 for consuming
weapons; energy mounts use zero. Repairs continue grouping damaged weapons by
their CHI behavior family. Limb actuator values are four-bit masks per limb,
split into named arm/leg fields by the adapter.

Weapon `ranges` are **exclusive map-distance thresholds**, after CHI's target
footprint adjustment, rather than tabletop hex ranges or packed DOS fields.
Export expands the old short/medium values into these effective distances.
With Enhanced rules, LRM families use the shared rule profile's scaled,
inclusive brackets and minimum-range penalty; their individual thresholds
apply in Legacy rules. Changing that shared profile affects all LRMs. New
range/attack algorithms require another implemented behavior/profile version.

## Manifest, assets and dependencies

The manifest supports `chi-original-dos-1.03` as its declared dependency
and `chi-training-v1` as startup, or `authored-adventure-v1` with an explicit
`adventure` JSON reference. See [maps/events/editor](M5_MAPS_EVENTS_EDITOR.md).
It verifies package/version and rule identity
against the referenced definitions. It loads no adjacent roster, combat or art
file by convention: every project file is explicitly referenced. Undeclared
portrait slots use the original art supplied by the declared CHI dependency.

Paths must be portable relative file paths, with exact case and forward slashes.
Traversal, absolute references, symlink/reparse children and reserved Windows
filenames are rejected. Each declared portrait must exist and decode, including
its animation bounds. A failed load preserves the existing content context.
Project definitions and resource staging live on the heap to preserve Windows'
default stack limit. The explicitly supplied dependency paths remain outside
this package-relative path restriction.

## Saving and editing

The only supported policy is **strict-content-v1**. `BTG1` saves bind package ID,
content version and SHA-256 of the exact manifest, definitions and declared
asset bytes. The fingerprint hashes their individual 32-byte SHA-256 digests in
manifest, definitions, optional adventure, then declared-asset order. Parsing and hashing use the
same loaded snapshots, so an edit during loading cannot bind different bytes.
This deliberately
includes whitespace, ordering, labels and cosmetic art: any change requires
restoring the old project to load its saves, or starting a new campaign with a
different save filename. Attribution documents are outside the fingerprint.
The digest is a compatibility check, not a signature or trust mechanism.

Six automatic slots use a separate `-project-PACKAGE_ID` suffix. For example,
the Workshop project's first two default slots are
`work/player-save-project-workshop.btp` and
`work/player-save-project-workshop-2.btp`. Choose another `--save-file` base
when starting a revised content version. Explicit `--save` paths are protected
too: a project cannot overwrite another package/version, Original or Updated
save. Failed loads preserve the current state. No existing user save is rewritten.

Original `BTS1`, Updated `BTU1/BTU2`, their append-only roster compatibility and
original GAME import/export remain available in their existing editions.
Project campaigns currently start fresh; they do not automatically import
Original/Updated saves. Such import needs an explicit stable-ID migration map,
which is deliberately absent from this strict first version.

## Previous formats and next boundary

`btp-chi-roster-v1` and adjacent `combat.json` remain supported compatibility
inputs and export sources. They are not the new authoring contract. The earlier
`btp-units-prototype` example, schema and Python validator are retained as an
[archived experiment](../examples/content-demo/README.md). They were never a
runtime format; their invented construction and sprite semantics are not
silently converted into CHI behaviors. New projects use only `btp-content-v1`.

Roadmap task 3 now supplies [authored maps, entrances, broker stock and saved
event continuations](M5_MAPS_EVENTS_EDITOR.md), together with a small roster
editor. Original BLD remains a compatibility adapter. Task 4 and task 5 now
supply an [independent tiny game, bounded Lua command routes and map/event
desktop editing](M5_INDEPENDENT_GAME_EDITOR.md).

## Verification

`authored-project-content` checks all 31 exported model records, ammunition
prices, sprite selection, movement data and shot queries across both combat
policies and many distances. It checks custom same-behavior weapons against
actual seeded attacks, authored battle text, package-bound save round trips,
failed-load preservation, all six slot names and the 256th broker entry.
`test_project_tools.py` exercises the actual validator/player from another
working directory, export/art/provenance, malformed JSON, capacities, reference
failures, path escapes, edited definitions, and adding a model/weapon using JSON
alone. Existing Original/Updated regressions remain separate.

No new original-game behavior was inferred for this refactor; it reuses
the existing evidence and original regression fixtures. The independent engine
remains GPL-3.0-only. Exporting does not change the source roster/art licenses;
the Updated roster's MegaMek attribution and CC BY-NC-SA 4.0 notice travel with
it. Original proprietary assets still must be supplied separately.

### Completion checks — 2026-10-17

| Check | Result |
| --- | --- |
| Native CTest | All 65 tests pass, including the 64 existing regression cases |
| Python tools | All 46 tests pass, including 13 new project/CLI cases |
| ASan/UBSan/leak checks | Eight selected content, combat, presentation and save suites pass; all 13 project/CLI cases also pass with sanitized executables |
| Windows/Wine | Fourteen selected content, combat, presentation and save suites pass; Windows validator and headless project launch pass |
| Cross-platform saves | A Windows-written project save loads on Linux with an identical canonical state digest |
| SDL, Linux and Windows | Five project checkpoints per platform: training-ground start, broker confirmation, purchase result, custom weapon menu and visible authored battle text; F5/F9 and final frame/state agree with headless |
| Reference guard | All 1,287 entries match the content/mode/mtime baseline |

The affected project/save checks were rerun after the final slot-name and
optional-error-buffer fixes. The SDL cases run through
`python3 tools/native_smoke.py --project-only` and
`python3 tools/native_smoke.py --windows --project-only`; captured frames are
local `work/project-*.ppm` artifacts. The report checkpoint uses the original
wait-for-input combat speed so its text remains visible during F5/F9 checks.

A complete editable export is available locally in **`work/editor-ready`**:
31 models, 16 mounted weapon definitions, 11 portraits and copied attribution.
It is ignored generated content, not an additional shipped pack. Validate it
with `./build/btp-project validate work/editor-ready`, and use it in the play
command above. Existing saves and both reference trees are preserved. No push
was performed.
