# Authoring games with commands

**Verified through 2026-10-19:** shared asset search and visual exports, native
mission checks, and seeded gameplay suites extend the original transactional
authoring pass. See [verification and remaining limits](TESTING.md#ai-authoring-discovery-and-mission-testing--2026-10-19).

The Construction Kit now supports a model-independent, display-independent
authoring CLI. It edits ordinary projects through the same document,
construction, import, validation and history operations used by the GUI.
The editor remains fully available. Games require no AI service.

This implements **AI1/AI2**, the discovery workflow from **AI3**, and bounded
mission analysis/testing from **AI4**. Live remote editor sessions, protected
regions, arbitrary mission simulation and new mission mechanics remain later
milestones. There is no background model or network service to configure.

## Start here

Build using the normal [README instructions](../README.md). Python 3.10+ is
needed for authoring; Pillow is needed only for bitmap import. The headless
commands need neither Tk nor a display. All commands emit JSON, with nonzero
exit status for errors or failed scenarios. The native tool paths can be
overridden using `--validator`, `--runner` and `--analyzer` (or `BTP_PROJECT_TOOL`
for the validator). Windows automatically uses the `.exe` filenames.

```sh
python3 tools/author.py capabilities
python3 tools/author.py inspect examples/relay-contract
python3 tools/author.py inspect examples/relay-contract --query objects --collection mechs --limit 5
python3 tools/author.py inspect examples/relay-contract --query routes --limit 30
python3 tools/author.py inspect examples/relay-contract --query map --id relay:town --rect 10 3 8 8
python3 tools/author.py validate examples/relay-contract
```

`capabilities` reads limits from the installed C validator and reports its binary
hash, API version, coordinate spaces, event operations, Lua API and every edit
operation's schema/example. It explicitly reports unsupported features. The
summary includes starting party, objectives, maps, worlds, animated tiles,
capacity usage and a project revision. `objects`, `object`, `usages`, `map`,
`routes` and `inventory` are read-only queries. Lists use `--offset`/`--limit`
(maximum 100); map rectangles are at most 32 × 32 tiles. Object queries summarise
pixel arrays and map grids instead of dumping them. The animated-tile summary
shows the first 30; use the paginated images query for the remainder.

`inventory` reports package files/hashes and provenance. Original CHI resources
are optional for inspection/validation. Rendering or playing a CHI-dependent
project needs the user's original assets and prepared caches. Missing original
preview assets return `dependency.unavailable`, without altering the project.
An interrupted editor save returns `recovery.required` on read-only commands;
open it normally to recover before inspecting again.

## Create a playable mission through commands

[Relay Contract](../examples/relay-contract/README.md) was produced by this
[99-operation request](../examples/authoring/relay-contract.commands.json).
It uses a Phoenix Hawk and Trebuchet, a Jenner encounter, depot/workshop,
an objective, victory/defeat/retreat continuations and a once-only payment.
Unit imports retain their existing source documents and CHI adaptations.

To reproduce it in a new directory:

```sh
python3 tools/author.py create work/my-relay --template examples/adventure-demo --id relay-contract --title "BattleTech - Relay Contract" --request examples/authoring/relay-contract.commands.json
python3 tools/game_editor.py work/my-relay
```

An initial creation request uses `expected_revision: "new"`; the CLI resolves
that against the staged new project. The entire package appears only after the
batch validates. Existing destinations are refused. Add `--dry-run` to check
creation without creating the destination. For an independent starting point,
use `--template examples/beacon-demo` and a request written for that template.
Templates retain their stable content IDs when given a new package identity.

To launch the supplied example, open the launcher and select
**Relay Contract (command-created)**, or run:

```sh
./build/btech-port --project examples/relay-contract
```

Run that from the repository root so normal CHI resource defaults resolve.
The generated example is separate from the user's improved Last Beacon.

## Edit an existing project

Inspect first, then put its exact `revision` into a request file:

```json
{
  "api_version": 1,
  "request_id": "revise-briefing-001",
  "project_id": "relay-contract",
  "expected_revision": "REPLACE_WITH_THE_64_CHARACTER_REVISION_FROM_INSPECT",
  "label": "Clarify the relay briefing",
  "scope": ["adventure.events/relay:briefing"],
  "operations": [
    {
      "op": "object.patch",
      "collection": "events",
      "id": "relay:briefing",
      "changes": {"text": "Follow the south road. Clear the Jenner, then return here for payment."}
    }
  ]
}
```

```sh
python3 tools/author.py apply work/my-relay --request briefing.json --dry-run
python3 tools/author.py apply work/my-relay --request briefing.json
```

`--request -` accepts standard input; no shell interpolation of JSON is needed.
Relative import paths resolve beside the request file (current directory for
stdin). Requests may read supplied image, unit and Lua files, but cannot write
arbitrary paths. Ordinary operations operate inside the selected project.

Use `object.put` with `mode: "create"` (default) or `"replace"` for a complete
object; `object.patch` updates only the stated top-level fields. A nested array
or dictionary supplied in `changes` replaces that entire field. There is no
implicit deep merge. Object IDs are immutable; cloning creates a new ID.
Definitions follow the corresponding [project schemas](../schemas/).

The [generated operation reference](AUTHORING_COMMANDS.md) covers maps,
worlds/jigsaws, city placement, buildings/walls/roads, patterns, entrances,
markers, people, encounters, dialogue, objectives/services, unit imports,
weapons/equipment, images/sprite tracks, tile animation and bounded Lua imports.
Use `object.put` for an event/objective/definition or jigsaw; `object.patch` for
its fields. New mission engine features cannot be invented by adding a JSON
key or Lua function.

For services, create ordinary `repair`, `rearm`, `heal` or `salvage` events with
explicit `next`, `failure` and `unchanged` branches. An objective references
declared active/complete flags. Lua exposes only `game.flag`, `game.credits` and
`game.command`; event nodes must declare possible continuations. `script.import`
compiles the source through the C loader before publication. No OS/library API
or arbitrary script-driven combat controller is exposed.

### Transaction and preservation guarantees

- A whole batch runs on a detached candidate, then passes the shared C loader.
  Forward references between newly created objects are allowed. Failed or
  cancelled batches leave game files and live history unchanged.
- Dry-run and apply use the same transformations. Results identify changed
  objects/fields, base/result revisions and outputs such as generated IDs.
- Revisions include authored JSON, artwork, scripts and editor metadata.
  Changes made since inspection cause `revision.conflict`. Re-inspect, review
  the human changes, and prepare a new request; never blindly replace a stale
  revision with the newest hash while retaining an obsolete whole-map record.
- Scope entries identify a section, collection or object, for example
  `adventure.maps/relay:town`, `adventure.events`, `art` or `editor.map_patterns`.
  `"*"` permits the entire project. Scope is checked against the **actual diff**,
  including generated tiles and editor metadata. It is a write-scope guard,
  not a protected-region/review system.
- Successful request hashes and outcomes live in `AUTHORING.json`, outside
  gameplay/save identity. Retries return `already_applied`; reusing an ID with
  different JSON or import bytes fails. Undo retains the receipt, so a delayed
  retry cannot recreate an intentionally undone edit. `matches_result` says
  whether current content still matches the original result.
- Receipts have bounds of 512 requests / 16 MiB. They are never silently evicted.
  Creating a new project identity from a template starts fresh; exporting the
  same package preserves receipts. Do not edit the receipt file manually.
- CLI publication and GUI Save share an OS writer lock, disk-change checks and
  the existing durable rollback journal. Locks live outside the package and
  release automatically after a crash. Recovery rolls back incomplete files
  and their receipt together. Other applications' conflicting edits are reported.
- A batch is one Undo/Redo action in the open GUI. CLI processes do not keep a
  persistent Undo stack across invocations; use a private project copy or Git
  for longer-lived revision history.
- `--cancel-file PATH` cancels at transaction checkpoints when that file exists.
  Ctrl+C interrupts the command. Publication already in progress uses normal
  save recovery. Requests are bounded to 512 operations / 16 MiB, with an
  operation-loop deadline and a separately bounded C validation call.

### Working with the editor

Use **Project → Export authoring summary** to describe the current document,
including valid pending forms. Prepare the batch against that exported
revision, then choose **Project → Apply authoring command file**.
The editor validates in a worker, applies on its GUI thread, and exposes errors
in its normal Problems view. If the document or form drafts change while the
worker runs, the result is refused. Successful application is unsaved until
Save; one Undo reverses the batch while retaining earlier hand edits.

Closed-project CLI edits must not race an open editor's unsaved work. Use the
file exchange above for that document, or close/save it before using CLI apply.
The CLI detects disk revisions; it cannot read another process's unsaved forms.
No live remote session is implemented in this pass.

**Project → Content catalogue** searches project assets, the shared Unit Library
or the tile atlas. It shows artwork, animated unit movement, dependencies and
editable names/tags/descriptions/edge notes. **Use on map** selects a tile,
pattern or construction style; selecting unregistered tile artwork creates a
palette definition. Use the Unit Library's normal import controls for units.
**Previous 100 / Next 100** pages through matches. Queries and source choices
survive tab restoration; edits refresh previews. Original resources are needed
to preview CHI art. Search and preview leave project data and history unchanged;
metadata edits use normal Undo/Save. Library metadata is edited in the library's
own editing scope.

**Project → Check mission** runs against the current document and valid drafts.
It rejects results made stale by later edits, places findings in Problems and
opens the relevant map location or event when a finding is activated. Rerun
after a repair; resolved mission findings clear without erasing unrelated errors.

## Find content without guessing IDs

The CLI and human pickers share search semantics. Terms are combined with AND;
quote phrases containing spaces. Text fields use case-insensitive substring
matching. Numeric fields accept `:`, `=`, `<`, `<=`, `>` and `>=`.

```sh
python3 tools/author.py catalogue work/my-relay --query 'kind:mech weapon:lrm mass<=55'
python3 tools/author.py catalogue work/my-relay --source library --query 'kind:mech class:light weapon:lrm'
python3 tools/author.py catalogue work/my-relay --source all --query 'kind:tile animated:true' --data 'Original DOS' --offset 0 --limit 30
```

Sources are `project` (default), `library`, `atlas` or `all`. `--library DIR`
selects an existing library; browsing never creates or seeds it. Atlas queries
decode the available source sheets and need original assets for CHI projects.
Pass `--data` to check animation on original project tile references too;
without decoding, their records explicitly report `animation_checked: false`.
Results have stable `id`/source-qualified `key`, dependencies and pagination
(`next_offset`, maximum 100 items). They contain summaries rather than pixels.

| Fields | Meaning |
| --- | --- |
| `kind`, `collection`, `id`, `key`, `name`, `source` | Asset type, owning collection and identity |
| `class`, `movement`, `weapon`, `role` | Unit mass class, movement type, armament and derived role |
| `dependency`, `tag`, `terrain`, `animated` | Resource requirements and authored/use metadata |
| `mass`, `price`, `walk`, `jump`, `damage`, `range` | Numeric unit/weapon properties |
| `frames`, `frame_ticks` | Animation frame count and duration in 32 ms ticks |

Derived roles such as `missile-support` are labelled heuristics from loadout and
movement, separate from authored descriptions. They do not assert tactical
doctrine or tabletop legality. Unit records list the weapons, ammunition,
equipment, presentation and owned images needed for dependency-complete import.
The existing library import/export rules retain source attribution.

Use the revision-checked `asset.annotate` operation for project asset names,
descriptions, tags and north/east/south/west connecting-edge notes. These live
in `EDITOR.json`; tile copies and unit library transfers retain relevant notes.
Atlas IDs such as `atlas:chi-land-105` can be annotated without owning their
pixels. `capabilities` lists the installed search fields and bounds.

## Coordinate and capacity rules

| Space | Unit | Used by |
| --- | --- | --- |
| `map_tile` | 16 × 16 pixels, local origin | Rows, painting, overlays, footprints, patterns |
| `movement` | 8 × 8 pixels, local origin | Start, entrances, encounter units, transfer destinations |
| `world_tile` | 16 × 16 pixels, planet origin | City origins and world patches |
| `jigsaw` | 8 × 8 map tiles | World piece grid and world painting |

Map `(10, 6)` and movement `(10, 6)` are different positions. Mech and party
footprints require clearance beyond an entrance's contact point; validation and
ordinary-input tests use actual engine collision. `map.paint` defaults to the
visible surface (`layer: -1`), with `0` for base and `1+` for overlays. Building
detail edits are retained by the same metadata reconciliation as manual paint.

Installed limits include 16 local maps (16..64 tiles per side), 16 encounters,
16 entrances per map, five choices plus cancel, 256 event nodes, 64 flags and
32 objectives. Art allows 4096 images / 1,048,576 total pixels / 512 action
tracks. Worlds share sector and discovery budgets, including unplaced local
maps. A default world uses the original 128 × 128 jigsaws; choose smaller worlds
when placing multiple planets or retaining separate interiors. The C validator
is authoritative when budgets interact.

The schema audit corrected missing services/objectives/person art, sprite action
tracks, lowercase pixel encoding and local-map dimensions. Structural schema
validation does not prove reference integrity, terrain clearance, text wrapping,
animation frame references/duration, deployment or save compatibility.
Those remain C checks. Original BLD/campaign behavior is unchanged.

## Export visual feedback

Render the composed map with the editor's actual graphics decoder:

```sh
python3 tools/author.py render work/my-relay --map relay:town --output work/relay-map.ppm --data "Original DOS"
```

PPM retains the original full-map workflow. For labels, regions and overlays,
choose `.svg`:

```sh
python3 tools/author.py contact-sheet work/my-relay --query 'kind:mech' --limit 12 --columns 3 --data 'Original DOS' --output work/relay-units.svg
python3 tools/author.py render work/my-relay --map relay:town --rect 0 0 32 24 --overlays collision entrances formations grid --data 'Original DOS' --combat-data work/combat-data.bin --output work/relay-map.svg
python3 tools/author.py graph work/my-relay --id relay:battle --depth 2 --output work/relay-events.svg
```

Contact sheets contain up to 32 labelled assets. Their JSON manifests include
source-qualified keys, frame counts, timing, dependencies and pixel hashes.
SVGs embed PNG pixels, so they are standalone viewable artifacts. No extra
imaging dependency is needed for export. Unsupported/missing artwork is labelled
unavailable. Changed artwork produces new content hashes.

`animation PROJECT --id KEY --output NEW.svg` exports up to 32 frames per strip;
use `--frame-offset`/`--frames` for the next segment. `--direction 0..7` uses the
sprite editor's eight facings (0 up, 4 down). `--action` selects an existing
`idle`, `walk`, `fire`, `jump`, `damage` or `destruction` track. JSON includes
frame IDs, facing/phase descriptions, per-frame ticks and authored sound cues.
Missing tracks are reported rather than invented. Movement is labelled
step-driven; its illustrative preview cadence is not a gameplay speed claim.
Tile/action durations use the actual authored timing.

Map and world rectangles are in their respective **tile** coordinates, at most
64 × 64. `--collision` tints wall tiles; `--tick 8` selects tile animation time.
Formation overlays show initial-party footprints and require the combat cache
for CHI projects. They are visual aids, separate from the native movement check.
`world-preview PROJECT --world ID --rect X Y W H --output NEW.svg` composes
jigsaws, terrain patches and local city overlays with labelled city boundaries.
Use `inspect --query objects --collection worlds` to find world IDs. The focused
event graph accepts `--depth 0..4`; omitting `--id` shows all explicit nodes.

All visual output paths must be new and outside the project. Rendering does not
edit artwork, graph layout, game data or Undo history.

## Check mission geometry and event routes

```sh
python3 tools/author.py lint work/my-relay --data 'Original DOS' --dialogue-data work/talk-data.bin --combat-data work/combat-data.bin --world-data work/world-data.bin --output work/relay-lint.json
```

`lint` combines explicit event-graph checks with `btp-author-analyze`, which uses
the actual C movement, terrain and door-contact rules for the initial whole
party. It checks local arrivals, entrance access, deployment footprints, enemy
overlap and friendly/enemy separation. Graph checks find missing/disconnected
links, suspicious synchronous cycles and missing objective flag writers;
objectives whose explicit completion routes lie behind sealed doors get a
warning where the graph can establish that connection.

`--static-only` skips native navigation. Missing dependencies, world navigation,
arbitrary conditions/Lua and later changes to party composition remain labelled
unknown or limited coverage. The checker does not prove every mission is
solvable. It validates an exact detached snapshot, has a 25-second native bound
and never changes the project. Errors fail the command; warnings need review
alongside the report's coverage description.

## Test ordinary gameplay routes

Run the recorded mission route:

```sh
python3 tools/author.py scenario work/my-relay --file examples/authoring/relay-contract.scenario.json --output work/relay-check --data "Original DOS" --dialogue-data work/talk-data.bin --combat-data work/combat-data.bin --world-data work/world-data.bin
```

The new output directory contains a private exact project snapshot,
`report.json`, per-step named state, event trace, logical-input replay,
screenshots and saves. Failure retains the same evidence and exits nonzero.
Reports pin the project revision, scenario hash and runner hash. Optional
scenario `expected_revision` refuses stale content. A scenario `seed` is a
24-bit integer (1..16777215), applied before the first event as three little-endian
RNG bytes. Omission preserves the ordinary default, `11223583` = bytes
`31,66,171`. Reproduce with the saved `scenario.json` and exact staged content;
the input replay alone does not initialize its seed.

Available scenario actions are `pages`, `walk` to an entrance ID, `enter`,
`choose` by displayed label, ordinary `input`, `battle`, `checkpoint`, `capture`
and `assert`. Battle policies are `computer` (real combat AI), `hold` (end turns
without attacking) and `retreat` (normal Flee command). `until_round: 1` stops
during a fight for a checkpoint, then a later battle step resumes it.
Checkpoints perform real save/load and compare complete serialized state; they
do not provide arbitrary cross-project or changed-content resume.

Assertions cover credits, flags, event, map, phase, objectives, owned/available
units, party survival/health, armour, structure, ammunition and battle outcome/
round bounds. Walk uses whole-party movement; combat runs real ticks. No action
teleports, grants rewards, sets flags or forces an outcome. Reports retain
visited events and unambiguously observed branch labels; same-target branches
and opaque Lua are not claimed as covered. `combat.jsonl` records policy,
outcome, rounds, losses and reductions before ordinary battle cleanup. Energy/
unused ammunition sentinels are excluded; destroyed ammunition still counts
as lost ammunition, so this is not solely a shot counter.

Run the [recorded suite](../examples/authoring/scenarios/README.md):

```sh
python3 tools/author.py suite work/my-relay --file examples/authoring/scenarios/relay.suite.json --output work/relay-suite --data 'Original DOS' --dialogue-data work/talk-data.bin --combat-data work/combat-data.bin --world-data work/world-data.bin
```

Eight cases cover three victory seeds, decline/cancel, building/encounter
cancellation, retreat, natural defeat, mid-combat saves, repeat rewards and
unaffordable repairs. The last case declares a validated low-funds setup batch
on a private copy. Its report says `validated_fixture` and records source revision
and recipe hash, distinguishing it from an ordinary new-game route. The actual
play then uses normal inputs. Source projects remain untouched.

Add `--case victory` (repeatable) to rerun affected cases after repairing a
mission. Suite reports retain each case/seed and separate combat samples by
case/policy. Sample counts, rounds, losses and resource reductions describe only
those inputs, not general balance. Each run is bounded to 256 steps, 120,000
ticks and 45 seconds; a suite has at most 16 cases, 32 runs, eight seeds per case
and 300 seconds total. `--cancel-file PATH` or Ctrl+C stops the active player
and retains partial evidence; cancellation exits 130. Use a new output directory
for every run.

## Reproduce the discovery and repair demonstration

```sh
python3 tools/authoring_demo.py --output work/my-authoring-lab
./build/btech-port --project work/my-authoring-lab/game
python3 tools/game_editor.py work/my-authoring-lab/game
```

With CHI resources/caches prepared, this creates a separate playable Relay
Authoring Lab. It searches the attributed numeric catalogue for a light LRM
unit, imports a Firefly FFL-4A with its dependencies, tags industrial construction
and road assets, and creates/clones an editable three-frame force field. It
exports contact sheets, animation strips, a map and an event graph, deliberately
breaks deployment, diagnoses it, repairs through a revision-checked batch and
reruns the three affected victory seeds. Exact requests and both failing/passing
reports remain beside the new game. Existing games and the shared library are
read-only inputs. No model/provider or network connection is used.

## Export and save compatibility

Export a validated ordinary package with:

```sh
python3 tools/author.py export work/my-relay --output work/relay-export
```

Changed gameplay content still uses strict save compatibility. Authoring
receipts and editor-only metadata do not invalidate game saves. This pass adds
no automatic saved-game migration.
