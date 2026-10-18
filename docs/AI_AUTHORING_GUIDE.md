# Authoring games with commands

**Development checkpoint:** the next catalogue/visual/mission-checking pass is
in progress and paused at the user's request. New `catalogue`, `contact-sheet`,
`animation`, `graph`, `world-preview`, `lint` and `suite` commands are present;
the expanded scenario policies still need route verification. Consult the
[handoff](AI_AUTHORING_HANDOFF.md) before resuming development. The completed
first-pass instructions below describe the earlier verified milestone.

The Construction Kit now supports a model-independent, display-independent
authoring CLI. It edits ordinary projects through the same document,
construction, import, validation and history operations used by the GUI.
The editor remains fully available. Games require no AI service.

This implements the first pass of **AI1 and AI2**, with a small map-preview and
mission-test workflow from AI3/AI4. Live remote editor sessions, protected
regions, asset contact sheets/search, arbitrary mission simulation and new
mission mechanics remain later milestones. There is no background model or
network service to configure.

## Start here

Build using the normal [README instructions](../README.md). Python 3.10+ is
needed for authoring; Pillow is needed only for bitmap import. The headless
commands need neither Tk nor a display. All commands emit JSON, with nonzero
exit status for errors or failed scenarios. The native tool paths can be
overridden using `--validator` and `--runner` (or `BTP_PROJECT_TOOL`). Windows
automatically uses the `.exe` filenames.

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

## Preview and test

Render the composed map with the editor's actual graphics decoder:

```sh
python3 tools/author.py render work/my-relay --map relay:town --output work/relay-map.ppm --data "Original DOS"
```

`--collision` tints impassable wall tiles; `--tick 8` selects an animation time.
Output is a full-map PPM. It represents map tiles, not runtime actors or a
reachability proof. Output paths must be outside the project and must be new.

Run the recorded mission route:

```sh
python3 tools/author.py scenario work/my-relay --file examples/authoring/relay-contract.scenario.json --output work/relay-check --data "Original DOS" --dialogue-data work/talk-data.bin --combat-data work/combat-data.bin --world-data work/world-data.bin
```

The new output directory contains a private exact project snapshot,
`report.json`, per-step named state, event trace, logical-input replay,
screenshots and saves. Failure retains the same evidence and exits nonzero.
Reports pin the project revision, scenario hash and runner hash. Optional
scenario `expected_revision` refuses stale content. The initial RNG state is
the ordinary runtime default; arbitrary seed sweeps are not implemented.

Available scenario actions are `pages`, `walk` to an entrance ID, `enter`,
`choose` by displayed label, ordinary `input`, `battle` using computer control,
`checkpoint`, `capture` and `assert`. Assertions cover credits, flags, event,
map, phase, party count and objective status. Checkpoints perform real save/load
and compare complete serialized state. Walk uses the existing whole-party
movement helper; combat runs real ticks. No action teleports, grants rewards,
sets flags or forces a win. Runs are bounded to 256 steps, 120,000 ticks and
45 seconds. Full branch coverage, balance sweeps and static reachability
analysis remain AI4 work.

Export a validated ordinary package with:

```sh
python3 tools/author.py export work/my-relay --output work/relay-export
```

Changed gameplay content still uses strict save compatibility. Authoring
receipts and editor-only metadata do not invalidate game saves. This pass adds
no automatic saved-game migration.
