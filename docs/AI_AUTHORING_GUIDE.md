# Authoring games with commands

**Verified through 2026-10-23:** AI6 includes regions, persistent mission state,
combat hooks, reinforcements and escorts. AI7a adds optional modular campaign
sources, deterministic builds and source diagnostics. AI7b adds opt-in larger
campaign budgets with explicit save compatibility. AI8 adds recorded campaign
recipes, Greybank Dispatch and offline CLI delivery. See the
[source/build guide](CAMPAIGN_SOURCES.md), [capacity guide](CAMPAIGN_CAPACITY.md)
and [recipe/delivery guide](CAMPAIGN_RECIPES.md), plus [verification](TESTING.md).

The Construction Kit now supports a model-independent, display-independent
authoring CLI. It edits ordinary projects through the same document,
construction, import, validation and history operations used by the GUI.
The editor remains fully available. Games require no AI service.

This implements **AI1/AI2**, the discovery workflow from **AI3**, bounded
mission analysis/testing from **AI4**, and the collaborative workflow from
**AI5**, **AI6** mission mechanics, **AI7a/AI7b** source/build and capacity support,
and the **AI8** campaign demonstration and CLI delivery.
Arbitrary mission simulation, further engine mechanics and capacity beyond the
documented v3 budgets remain future work. There is no background model or network
service to configure.

For the complete generation/check/play demonstration, run `recipe list`, then
`recipe build --file examples/authoring/greybank/recipe.json --output NEW_DIRECTORY
--check --play`. It records inputs, creates modular sources and an ordinary
playable package, diagnoses/repairs a deliberate deployment error, and runs both
campaign branches with checkpoints. Original resources are supplied separately;
omit `--check --play` to generate without them. Packaged kits provide **Author**
(Linux) and **Author.cmd** (Windows) as console launchers for this same interface.

All project commands accept either an existing `project.json` package or a
`SOURCE.json` source project. Use `source convert PROJECT --output NEW_DIRECTORY`
for deliberate conversion, `source build SOURCE --output NEW_DIRECTORY` for a
playable package, and `source locations SOURCE --id OBJECT` for source ownership.
Conversion preserves the existing project; keep it for its old saves because
canonical compilation changes byte identity. GUI/command Save targets modules,
while exports and player snapshots remain normal packages.

Imported CHI campaigns now also support optional authored quests. Use
`bridge.enable` / `bridge.example`, `bridge.binding` / `bridge.call`, and
`quest.put` / `quest.patch` / `quest.remove` / `quest.connect` in normal batches.
Inspect `native_quests` in summary and query `quest-events`, `quest-maps`,
`quest-encounters`, `bridge-entrances` or `bridge-calls`. Quest scopes use
`quest.events/<id>` and `bridge.entrances/<id>`; they remain separate from native
`chi.maps`. Native startup and existing BLDs still own the campaign.
[Quest authoring](CHI_QUEST_AUTHORING.md) documents the bounded native adapters,
continuations, private example recipe and CLI/GUI verification.

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

For a region-based mission, use
[Argent Recovery](../examples/argent-recovery/README.md). Reproduce it with
`python3 tools/mission_demo.py --output work/my-argent-recovery`.
It records the normal command batch and includes six tested success/failure,
repeat-visit and battle routes. The editor's **Region** drawing tool and
**Mission state** tab edit the same `regions`/`variables` collections available
to `object.put`/`object.patch`; state objectives and `check` events use the
ordinary objective/event editors.

Read [Mission state](MISSION_STATE.md) before writing these definitions.
Region rectangles use local tile coordinates; movement uses half-tiles.
The reference defines event order, once/repeat behavior, counter bounds,
terminal objectives, bounded Lua queries and saved pending triggers.
Scenario assertions include `variable`, `region` and objective state
`inactive`/`active`/`complete`/`failed`. Reinforcements and escort actors are
not part of AI6a.

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

The [shared Construction Library](CONSTRUCTION_LIBRARY.md) provides reusable
building/wall/road styles and patterns with their tile/art dependencies.
Use `catalogue --source construction-library` (optionally
`--construction-library DIRECTORY`) to find a design and its exact bundle file.
`contact-sheet` supports the same source. A `construction.import` operation
can assign an explicit ID, followed in the same batch by `construction.draw`,
`road.draw` or `pattern.place`. Reviews and live sessions capture the imported
bytes. `construction-export PROJECT --id DESIGN` stores a saved project design
in the shared library; updates require an explicit entry/revision.

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
  including generated tiles and editor metadata. Protection rules add object,
  field, local-map and world-region checks; review makes the proposed result inspectable.
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

For reviewed changes, use **Project → Changes and protection** and the workflow
below. The original command-file exchange also remains available:

Use **Project → Export authoring summary** to describe the current document,
including valid pending forms. Prepare the batch against that exported
revision, then choose **Project → Apply authoring command file**.
The editor validates in a worker, applies on its GUI thread, and exposes errors
in its normal Problems view. If the document or form drafts change while the
worker runs, the result is refused. Successful application is unsaved until
Save; one Undo reverses the batch while retaining earlier hand edits.

Closed-project CLI edits must not race an open editor's unsaved work. Use the
file exchange or local session for that document, or close/save it before
using CLI apply. Ordinary disk inspection sees saved revisions; a local
`session snapshot` deliberately includes the open editor's valid forms.

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

## Review changes and preserve human work

Open **Project → Changes and protection**. Its three pages are **Review
changes**, **Protected content** and **Local session**.

1. In **Protected content**, add a named rule for an object, selected fields,
   or a rectangle on a local map or planet. These settings use normal Undo and Save.
2. Export the current summary, or take a live session snapshot. Prepare a
   command batch against that exact revision.
3. **Load commands** builds a separate proposal. It leaves the open
   document and pending forms unchanged. Review object/field changes, paired
   local maps, composed worlds, event-route lists and dependencies. Complete packages and SVG
   previews remain in the review folder.
4. **Checks → Cases → Choose suite** explains suggested regression cases and
   offers selected/full-suite checks. **Checks → Reports → Check mission** runs
   mission analysis. Results belong to that exact candidate, with coverage limits
   and missing-asset diagnostics. Omitted cases are never reported as passed.
5. **Apply changes** revalidates the proposal, collects valid human
   drafts as their own history step, then applies the generated batch as one
   additional step. **Undo** reverses that batch; **Save** publishes it.

**Discard** retains artifacts while preventing application. **Request changes**
records a note for the external author; it does not itself invoke a model.
Protection conflicts require explicitly selecting the named exception before
Apply. Exceptions apply to that one application; the rules remain in place.
Changing groups requires **Recheck groups** before Apply. At narrow
window sizes the proposal list becomes a dropdown; the summary and selection
controls scroll, and the action buttons remain outside the scrolling area.

Object paths use the same notation as write scopes, for example
`adventure.events/beacon:welcome`. Entrances also have the synthetic path
`adventure.entrances/beacon:exchange`. Fields accept names such as `text` or
JSON pointers such as `/enemies/0/definition`. Map regions use **local map-tile**
rectangles `[x,y,width,height]`; `world_region` uses **world tiles** and an explicit
planet ID. They protect the cell layers and referenced
tile/art definitions, so changing a shared tile cannot bypass a painted
region. Manual editing remains possible. Rules constrain supported generated
batches, including the older immediate Apply command.

Rules live in `EDITOR.json.authoring_protection`; see the
[protection schema](../schemas/authoring-protection-v1.schema.json).
Generic generated batches cannot remove or rewrite that policy. Whole world
objects and their fields can also be protected by object path.
[World review and protection](WORLD_REVIEW.md) explains the paired planet views,
town navigation, indirect art/jigsaw changes and the `review world` detail command.
[Scenario selection](SCENARIO_SELECTION.md) covers retained suite inputs,
dependency explanations, `review suggest`, and `review check --suggested/--case`.
This is a collaboration contract,
not an operating-system security boundary against arbitrary file writes.

Closed-project CLI equivalents:

```sh
python3 tools/author.py protection work/my-relay
python3 tools/author.py review prepare work/my-relay --request work/revision.json --output work/review-1 --data 'Original DOS'
python3 tools/author.py review show work/review-1
python3 tools/author.py review check work/review-1 --data 'Original DOS' --dialogue-data work/talk-data.bin --combat-data work/combat-data.bin --world-data work/world-data.bin
python3 tools/author.py review apply work/my-relay work/review-1
```

Use `protection PROJECT --file RULE.json --expected-revision HASH` to add/update
a rule deliberately, or `--remove RULE_ID` to remove it. CLI application saves
the project; the GUI application waits for normal Save. `review apply` accepts
repeatable `--override RULE_ID` for deliberate exceptions. When the project is
open, use its local session so pending GUI drafts participate.

An optional batch `groups` field partitions every operation exactly once:

```json
"groups": [
  {"id": "definitions", "label": "Required unit", "operations": [0]},
  {"id": "encounter", "label": "New opponent", "operations": [1],
   "requires": ["definitions"]},
  {"id": "road", "label": "Road extension", "operations": [2]}
]
```

Indices are zero-based. Selecting `encounter` includes `definitions`; the
combination still passes the shared C validator. Missing references fail even
if a dependency was omitted from `requires`. Without groups, the batch is one
group. Recheck with `review recheck PROJECT REVIEW --output NEW_REVIEW --group
encounter`. Partial applications get their own retry receipt.

Construction footprints, styles, pixel layers, event layout and annotations
remain authoring data. Compatible roof/face details survive regeneration.
Displaced details are listed with construction, map, position and tile; a
protected affected region blocks application unless explicitly overridden.

## Connect an external author to the open editor

Choose **Project → Local authoring session**, enter a brief, constraints and
allowed write paths, then **Start session**. **Copy connection path** supplies
the local directory used by the CLI. The default is **Review each proposal**.
**Apply within declared scope** is an explicit opt-in: valid, conflict-free
proposals apply automatically, while protected conflicts remain for review.
Natural-language constraints communicate intent; actual diffs, declared scopes,
revisions and protection rules are enforced by code.

```sh
# Replace SESSION_PATH with the copied path; quote it if it contains spaces.
python3 tools/author.py session status SESSION_PATH
python3 tools/author.py session snapshot SESSION_PATH --job-id brief-1 --wait 30
python3 tools/author.py session propose SESSION_PATH --request work/revision.json --job-id revision-1 --wait 30
python3 tools/author.py session wait SESSION_PATH revision-1 --seconds 30
python3 tools/author.py session cancel SESSION_PATH revision-1
```

The snapshot result names an ordinary staged package, revision and summary.
Inspect/export previews from that snapshot. A proposal's `project_id` is the
open game's identity and its `expected_revision` is the snapshot revision.
Import paths are resolved relative to the request file, captured immediately,
and hashed. Reusing a job ID requires identical request and import bytes.
Polling never needs terminal input; `--wait` is bounded to 60 seconds.

The transport is a private local JSON-file inbox, with no listening network
port, provider dependency or embedded model. The editor owns the document;
workers receive detached data and publication happens on the GUI thread.
Local sessions also work in an explicitly opened Unit Library editing scope.
Saving that scope publishes to the library through its normal library Save
path; importing a design into a game remains a separate operation. Library
Save replaces its temporary editing package, so start a fresh session for
further library work after saving.

**Local session** shows queued/running/finished jobs. Double-click one to open
its review or see its snapshot result. Cancellation does not publish unfinished
work. Closing the review tab preserves the session and proposals; closing or
replacing its project/library scope stops the session. Save and Play remain
ordinary editor actions and do not require a connected author.

If human work changes during a job, the result becomes stale or its application
is refused. Request a new snapshot and revise the request with knowledge of
those edits. Invalid GUI fields stay visible and prevent snapshot/application.
After a crash, reviews and artifacts remain on disk, unsaved human work uses
the existing recovery flow, and expired sessions report interruption. Start a
new session explicitly; queued work is not automatically resumed. Journalled
save recovery and retry receipts handle interrupted publication.

Current bounds: 512 operations per batch, **2 MiB per reviewed request**,
256 preservation rules, 64 change groups, eight queued/running jobs, 256 jobs
per session, 16 MiB per import and 64 MiB total captured imports. The Changes
view remembers up to 512 review paths. It renders the first eight changed
local maps, with all other changes retained in packages and field comparisons.
Changed worlds get paired overviews capped at 1024×1024 pixels per side and up
to 64 requested detail crops per review. World protection rectangles can total
4,194,304 tiles, counting overlapping rules.
Each review supports 32 linked check reports. Display excerpts share a 4 MiB
budget; complete values remain in the snapshots. Oversized review records fail
without application. These bounds are also exposed by `capabilities`.

The automated collaboration demonstration uses a private **copy** of Last
Beacon. It paints a roof, moves a doorway and edits dialogue through the GUI,
protects those edits, submits a road/encounter revision from another CLI process,
reviews it, and checks Undo, Save, Play and recovery. Reproduce with
`python3 tools/native_smoke.py --editor-collaboration-only` after preparing
the normal original-resource caches. `work/collaboration-lab/latest.json`
locates the retained playable copy. Source Last Beacon files are unchanged.

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

Adventure v1/v2 retain 16 local maps, 16 encounters, 256 events and 32 objectives
and variables. Runtime 0.2.0's explicit `campaign.upgrade` command enables v3:
**64 maps, 64 encounters, 1,024 events, 128 objectives and variables**. Upgrade
changes save identity and requires a new campaign. `inspect` reports limits for
the current format; `capabilities` includes old-format overrides and requirements.
See [the capacity guide](CAMPAIGN_CAPACITY.md) for the upgrade and measured fixture.
Local maps still allow 16..64 tiles per side, 16 entrances per map, five choices
plus cancel and 64 flags. Art allows 4096 images / 1,048,576 total pixels / 512 action
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

AI tools can already author the broader world and its towns:
`world.create` creates a planet, `object.put` defines jigsaws, `world.generate`
uses a declared seed and piece weights, `world.paint` places pieces,
`world.patch` draws terrain tiles, and `city.place` overlays a local town map.
Several worlds are supported within the runtime's compiled/shared capacity.
Query remaining capacity before expanding a project. The review's map tab
shows local maps; use `world-preview` for a composed world/city image and the
field comparison for the underlying world changes. AI7b supplies the documented
larger campaign capacities; [world-route verification](WORLD_ROUTE_VERIFICATION.md)
now covers declared travel through composed towns/sectors and between planets.

All visual output paths must be new and outside the project. Rendering does not
edit artwork, graph layout, game data or Undo history.

## Check mission geometry and event routes

```sh
python3 tools/author.py lint work/my-relay --data 'Original DOS' --dialogue-data work/talk-data.bin --combat-data work/combat-data.bin --world-data work/world-data.bin --output work/relay-lint.json
```

`lint` combines explicit event-graph checks with `btp-author-analyze`, which uses
the actual C movement, terrain and door-contact rules for the initial whole
party. It checks local/world arrivals, entrance access, deployment footprints, enemy
overlap and friendly/enemy separation. Graph checks find missing/disconnected
links, suspicious synchronous cycles and missing objective flag writers;
objectives whose explicit completion routes lie behind sealed doors get a
warning where the graph can establish that connection.

World floods cap each planet at 262,144 positions and report incomplete scans
as unknown. `--static-only` skips native navigation. Missing dependencies,
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

Available scenario actions are `pages`, `walk` to an entrance ID or explicit
map/world movement coordinates, `enter`,
`choose` by displayed label, ordinary `input`, `battle`, `checkpoint`, `capture`
and `assert`. Battle policies are `computer` (real combat AI), `hold` (end turns
without attacking) and `retreat` (normal Flee command). `until_round: 1` stops
during a fight for a checkpoint, then a later battle step resumes it.
Checkpoints perform real save/load and compare complete serialized state; they
may have a unique `name` to retain separate files. A top-level `checkpoint`
with `file` and `sha256` starts from an exact saved input, preserving RNG and
skipping opening events. It cannot accompany `seed`, and suite checkpoint cases
reject seed sweeps. Paths are relative to the scenario file. The editor exposes
the same checks in **Play options → Checkpoints and trace**. See
[saved journeys](SAVED_JOURNEYS.md) for setup, reproduction and midbattle metric
boundaries. Cross-project or changed-content resume is refused.

Assertions cover credits, flags, event, map, phase, objectives, owned/available
units, party survival/health, armour, structure, ammunition and battle outcome/
round bounds. World identity/position, compact formation and per-planet
discovery assertions are documented in [World routes](WORLD_ROUTE_VERIFICATION.md).
Walk uses whole-party movement; combat runs real ticks. No action
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
