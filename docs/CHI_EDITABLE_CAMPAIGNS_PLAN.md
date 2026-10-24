# Plan for editable Original and Updated CHI campaigns

Recorded **2026-10-23**, against implementation commit `8075156`.

**Status: C1–C3 and C4.1–C4.3 implemented; C4.4–C4.5 and C5 planned.** See the
[progress ledger](CHI_IMPORT_PROGRESS.md) and [import instructions](CHI_IMPORT.md).
This document is the
implementation handoff requested by the owner. It describes five milestones for
creating two separate, editable campaign projects from a user's supplied copy
of BattleTech: The Crescent Hawk's Inception. The existing Original and Updated
games must remain playable and retain their saves.

The intended implementation handoff is to **Sol 6.1**, with an independent
**Astra** audit later. The work and acceptance criteria are model-independent.
The owner authorized the C1–C2 first pass. Later implementation instructions
should name the next milestone or range to execute.

## 1. What the user receives

The launcher and Construction Kit gain **Import CHI campaign**. A user chooses
their original game directory, **Original**, **Updated**, or **Both**, and a
destination. The importer checks the supported game version, prepares the
required resources locally, creates the projects, validates them and offers
**Edit** and **Play**. Routine import must not require DOSBox, shell commands or
manual cache preparation. Equivalent headless operations support automation.

Choosing Both produces two independently editable projects with distinct package
IDs and saves. Each includes the complete campaign, not a demonstration inspired
by it. Original retains the Original edition's rules and presentation. Updated
includes the current Updated edition's roster, broker, optional art and combat
settings, including its Enhanced default and supported Legacy selection.

Users can edit maps and world composition, tile and sprite art, entrances, NPCs,
dialogue, shops, unit definitions, mission settings and story events, then build
and play their result. New content uses the Construction Kit's existing editing
and authoring services. Ordinary campaign alterations must not require editing C.
Adding an entirely new engine mechanic can still require engine work.

Only the importer, schemas, independently written recipes, tests and documentation
belong in the repository. Original-derived assets and campaign data are generated
locally. This includes dialogue, scripts, maps, fonts, audio and image pixels
embedded in JSON, as well as familiar binary and image files.

### Meaning of an exact clone

The first acceptance target is **equivalence to the corresponding current
BtechPort edition**, for unchanged imported content under the same seed and
inputs. Original DOS behavior remains the authority when resolving fidelity
questions. Existing port approximations must remain visible in the evidence
ledger; importing them does not establish complete DOS parity.

Two different properties must be demonstrated:

1. **Behavior preservation:** importing without edits preserves campaign state,
   world generation, rules, timing, presentation and progression.
2. **Authorability:** an ordinary edit actually changes the running campaign,
   survives Save/reopen/build and has useful validation and source navigation.

A project that merely launches the existing hard-coded campaign satisfies neither
the complete authorability requirement nor the final milestone.

## 2. Milestone overview

| Milestone | Deliverable | Depends on | Completion gate |
| --- | --- | --- | --- |
| C1 — Audit and contracts | Complete dependency, provenance, edition, state and editability inventories; defined technical contracts | Current implementation | Every campaign dependency has an extraction/loading/editing strategy; unresolved cases are explicit |
| C2 — Importer and isolation | Headless import, an initial import dialog, independent Original/Updated projects and a working Citadel/training slice | C1 | Both profiles run the slice with matching behavior and isolated saves; cancellation and failed imports preserve user data |
| C3 — World and resources | Editable original world, towns, placements, graphics, animation and resource references | C2 | Unchanged resources match; representative edits reach the player through editor and headless workflows |
| C4 — Story and services | Editable BLD programs, dialogue, campaign settings, services and mission progression, with explicit new-event integration | C2 contracts; C3 for integrated campaign checks | All original scripts and campaign systems are accounted for; unchanged behavior and edited continuations pass |
| C5 — Fidelity and delivery | Complete import wizard, campaign regression evidence, safe distribution checks and user instructions | C1–C4 | Both campaigns complete; editing, recovery, isolation and packaged setup pass the declared platform matrix |

**Recommended first authorization: C1 followed by C2.** Establish a working
Citadel/training example in both profiles before converting the whole campaign.
C4 is the largest uncertainty and should proceed through the smaller increments
below. C3 and C4 can be developed on separate branches once their C2 interfaces
are stable, but integration and shared schema changes should remain sequential.
Parallel agents are optional and require a separate instruction.

## 3. Current implementation and constraints

These findings are from the repository at the recorded baseline. Recheck them
when implementing; do not spend a new session rediscovering the entire project.

| Area | Existing capability or constraint | Consequence for this work |
| --- | --- | --- |
| Project export | Current export provides definitions and resources for authored projects; it does not reconstruct the whole CHI campaign | Build a campaign importer; do not relabel the current export as one |
| Runtime selection | `chi-training-v1` and `authored-adventure-v1` choose different paths; project parsing imposes startup/adventure constraints | Introduce an explicit, versioned compatibility contract without changing existing package meanings |
| BLD and events | `btp_state_bld()` in `game.c` excludes BLD execution while authored events are enabled | New events cannot be enabled alongside BLD merely by loading an adventure; a deliberate bridge is required |
| Edition behavior | Some broker/menu/unit behavior is inferred from `roster.count` | Exporting an Original roster must not accidentally enable Updated features |
| Unit export | `original_units()` in `tools/project.c` produces useful library adaptations, including repaired/normalized templates and estimated prices | It is not a lossless source for campaign actors, training shells, damaged units or economy |
| BLD size | Local audit reaches 1,816 instructions across 26 BLD files; the largest individual graph is Training at 159 instructions | Static reachability is not branch execution coverage; do not force every instruction into one authored event node |
| Capacity | Current v3 authored limits include 1,024 events, 64 local maps, 16 shops, 64 flags and 16 entrances per map | Measure actual imports and state needs; never truncate or silently drop data to fit |
| World | Original generation uses extracted tables, RNG, city overlays and special map states | Preserve the generator and its consumption of RNG; a visually similar custom world is insufficient |
| Saves | Project saves have strict identity/content checks; supported project revision migration is constrained to authored adventures | No automatic conversion of existing Original/Updated saves into these new campaign projects |
| Authoring | Modular sources, typed commands, review/protection, Undo, source diagnostics, suites and retained Play snapshots exist | Extend these services rather than creating a disconnected importer-only editor |
| Packaging | `delivery.py` can package tracked JSON with embedded graphics; its asset report is an inventory, not clearance | Ignoring original directories alone does not keep original-derived data out of releases |

Relevant starting points:

- [Project loading](../port/data/project.c), [content selection](../port/data/content.c)
  and [original resources](../port/data/resources.c).
- [Game dispatch](../port/core/game.c), [BLD interpreter](../port/core/script.c),
  [story operations](../port/core/story.c), [services](../port/core/service.c),
  [authored services](../port/core/authored_services.c) and
  [events](../port/core/events.c).
- [Original world runtime](../port/core/world.c),
  [world table extraction](../tools/prepare_world.py),
  [BLD analysis](../tools/audit_bld_flow.py) and
  [authored limits](../port/data/adventure_limits.h).
- [Modular sources](CAMPAIGN_SOURCES.md), [campaign capacity](CAMPAIGN_CAPACITY.md),
  [suite authoring](TEST_SUITE_AUTHORING.md), [scenario selection](SCENARIO_SELECTION.md),
  [saved journeys](SAVED_JOURNEYS.md) and [editor responsiveness](EDITOR_RESPONSIVENESS.md).

### Existing provenance issue to resolve

At the baseline, tracked Last Beacon data contains **20 image entries with
CHI-atlas provenance**, recorded in `EDITOR.json` and present in `graphics.json`.
This is present in HEAD, not just in the owner's uncommitted edits. The README
already acknowledges original-derived Last Beacon tiles. C1 must document the
exact dependency closure and C2 must prevent it entering new redistributable
packages. A reconstruction recipe can restore the local experience from the
user's original files.

The owner currently has uncommitted changes in three Last Beacon files. Preserve
them. Any later current-tree cleanup needs a reversible migration that retains
the owner's local result. Rewriting Git history or deleting user projects is
outside these milestones and requires a separate decision. Removing a tracked
payload in a later commit does not remove it from existing history.

## 4. Rules that apply to every milestone

1. Read [PROMPT.md](../PROMPT.md) and current repository instructions first.
   Keep `Original DOS/` and `UnBattletech/` unchanged, including modes and mtimes.
   Use the existing reference guard and keep generated evidence under `work/`.
2. Never overwrite existing projects, saves or user edits. Imports publish into
   new destinations. Reimport produces a new baseline for explicit comparison;
   it must not reset the working project.
3. Keep the normal launcher Original/Updated entries, save locations and current
   supported formats working. No original save is relabelled to bypass project
   compatibility checks.
4. Treat edition, capabilities and rules as explicit settings. A roster count,
   filename or imported tile must not select a gameplay edition by accident.
5. Preserve original-derived provenance through copying, conversion, recoloring,
   cloning, flips and imports into libraries. Unknown origin cannot silently
   become independently authored content.
6. Do not commit original-derived payloads or oracle screenshots, audio, decoded
   text, maps or private saves. Synthetic fixtures, extraction code, hashes and
   genuinely independent metadata can be committed after review.
7. Keep old formats valid. Introduce and document new schema/runtime versions
   when needed; reject unsupported fields and versions with useful diagnostics.
8. Every accepted edit must use shared validation, ownership, revision checks,
   protection and Undo. GUI and automation must operate on the same model.
9. Keep work bounded. Validate file sizes, counts, paths, allocations, instruction
   budgets and execution waits. Measure full imports before increasing limits.
   Avoid large stack objects, especially in Windows test builds.
10. Use the editor's task/cancellation system for expensive work. Tk operations
    stay on the UI thread; stale worker results cannot overwrite newer edits.
    Do not regress the measured snapshot/source-table improvements.
11. Add comments explaining compatibility decisions and temporary workarounds at
    their implementation sites. Unsupported original behavior must produce an
    explicit diagnostic rather than silently doing nothing.
12. Make small commits at the increments below. Stage named files; leave unrelated
    work alone. Keep builds to two compilation jobs, run Linux and Windows builds
    sequentially, and do not push or publish as part of this plan.

## 5. Proposed architecture and contracts

This section specifies the intended direction. Names of new files, fields and
operations below are proposals, not commands or formats already implemented.
C1 should settle their precise schemas before C2 depends on them.

### 5.1 One reconstruction pipeline and two explicit profiles

Use one verified extraction/reconstruction pipeline. Apply a small Original or
Updated profile during generation. Produce two complete, separately owned source
projects when Both is selected. Do not maintain two unrelated converters or make
the second project depend on the editable files of the first.

Common immutable extraction results may be cached by original-content digest and
extractor version. Editing an imported asset creates or changes a project-owned
copy; it must never modify the shared cache. Building either project resolves its
own effective resources and overrides deterministically.

The profile contract needs explicit rules, supported compatibility features,
startup behavior, roster additions, broker placement/availability and optional
presentation. Keep profile defaults distinct from settings the player may change.
Original must remain Original even when its full unit roster becomes editable.

### 5.2 Source ownership, stable IDs and runtime data

Extend the existing modular-source/build workflow. An illustrative local source
project has the following responsibilities, with final paths decided in C1:

| Source area | Contents |
| --- | --- |
| Manifest and import record | Unique project identity, selected profile, schema versions and supported source fingerprints |
| World and maps | Generator settings/tables or verified references, editable jigsaws, town overlays, tile/collision properties and placements |
| Campaign and missions | Initial state, training definitions, encounter tables, progression conditions and special locations |
| Services and definitions | Shops, prices, recruitment, repairs, unit/weapon/equipment templates and actor-instance overrides |
| Dialogue and BLD sources | Local extracted text, labelled instruction representation, native-action arguments and source maps |
| Presentation | Project-owned graphics, palettes, sprites, animations, sound definitions and provenance records |
| Editor and tests | Normal editor metadata, review/protection state, editable suites and local evidence references |

Separate source roots from generated runtime package roots, as today. Preserve
stable author IDs and explicit mappings to original map, room, unit and script
indices. Do not let reordering a source file change a mission's meaning.

Separate project identity from reconstruction reproducibility: a new import gets
a new identity, while the same inputs/profile produce the same canonical content.
Record intentional identity fields separately in reproducibility comparisons.
Repeated builds of one source project retain its identity and deterministic data.

Pin effective content, interpreter/compiler versions and extraction dependencies
for saves and retained tests. Machine-specific paths are resolution settings, not
campaign identity. Preserve existing fingerprint semantics where possible; any
changed semantics need a versioned format and migration policy.

### 5.3 Original campaign adapter and new event integration

Keep the independently written original interpreter and native campaign behavior
as the initial execution foundation. Add replaceable campaign resources and
settings to that adapter. Do not convert the campaign to the simplified authored
repair/heal/salvage services and assume the results are equivalent.

Represent BLD programs as editable, typed instructions with stable labels,
dialogue references, documented operands and original-offset source maps. A
compiler resolves labels and preserves menu layout, signed byte operations,
jump-table behavior, native calls and wait/resume semantics. Preserve any
unreachable data needed for a lossless unchanged round trip. Unsupported regions
remain identified and preserved; they cannot be silently deleted or executed as
no-ops. A program with unsupported edit semantics is not fully editable yet.

Keep context-sensitive native actions in a named registry. Record the old action
number, relevant building/context, parameters, reads/writes and yield behavior.
Externalize campaign content consumed by these actions; retaining generic engine
mechanics in C is acceptable. Merely wrapping a hard-coded mission in one opaque
action does not meet the mission-editing requirement.

New structured events and bounded Lua use explicit entry/return operations. The
bridge owns serializable continuations, active-program identity, menu state,
pending animation/audio and RNG. No C call stack or opaque Lua stack can be the
only record of where a saved game should resume. Preserve the legacy story byte
window separately from new typed state unless an audited mapping proves lossless.

### 5.4 World generation and editing

Preserve the original world seed, generation tables, coordinate system, jigsaw
selection, edge joins and overlay order. Extract all components needed to expose
the world in the editor. Preserve city placement, entrance coordinate conversion,
ruined Citadel and invasion state, islands and special encounter regions.

Start with the compatible generator plus explicit editable overrides. An editor
view may materialize its result for inspection, but preview generation must not
advance gameplay RNG. Exporting a fixed tile snapshot is not a substitute for
retaining the original generation behavior.

Reuse generic authored worlds/jigsaws only after a differential test establishes
equivalence. If their schema lacks an original feature, extend it or retain an
explicit compatibility component. Record dimensions from the actual original
coordinate/generation code; a local cached sector window is not the whole world.
The imported world must still allow meaningful town moves and terrain edits.

### 5.5 Local content and distribution

Each extracted resource has an origin record: logical source file, source digest,
extraction operation/version, output digest and applicable ownership/license
category. Do not write personal absolute paths into portable public metadata.
Dependencies form a provenance closure, including images embedded in JSON and
resources copied into libraries.

Provide distinct outcomes: a private playable package using local original data,
and a redistributable recipe/mod containing permitted material. Exclude original
payloads from the latter by default, and report excluded dependencies clearly.
A transformation recipe is not automatically safe: literal copied dialogue or
pixels inside it are still original-derived. Unknown provenance blocks that
export until resolved. Keep existing independently created art and separately
licensed roster content correctly attributed; the code's GPL license does not
license every asset.

Normal application/repository packaging must enforce the same boundary. A
generated-project ignore file is useful, but insufficient without staged-file
and distribution checks. Once an import is complete, test offline play from its
resolved local resources; no runtime AI service or emulator should be required.

## 6. C1 — Import and provenance audit

**Goal:** remove the architectural unknowns before bulk conversion. This is an
engineering audit with executable measurements and contracts, not another broad
wishlist. No campaign is claimed imported at this milestone.

### C1.1 Capture the baseline

- Record commit, working-tree status and reference-guard result. Record hashes
  of any unrelated dirty files; do not stage or change them.
- Inventory the current supported Original/Updated entry points, resource paths,
  cache versions, saves and launcher behavior.
- Select a small set of existing deterministic fixtures for the initial slice
  and a campaign regression list for C5. Reuse fixtures where possible.
- Store private observations under `work/`; public evidence contains commands,
  fingerprints, coverage summaries and limitations without extracted payloads.

### C1.2 Inventory all campaign inputs and state

Create a machine-readable inventory and a readable summary. For every resource
and native campaign setting record: original source or current code owner,
loader/consumer, profile applicability, decoded type, edit surface, generated
output, validation, save implications, provenance and verification status.

Cover all maps/overlays, BLD programs, text, art, palettes, fonts, sprites,
animations, music/effect programs, world tables, map-room data, entrances,
walking NPCs, combat templates, encounters, recruitment and special story actors.
Include executable-derived data already extracted by existing tools.

Enumerate BLD native actions and their contexts, the legacy story state window,
held menus/animations and mission progression. Trace campaign constants currently
in `game`, `story`, `service`, `training`, `campaign`, `cache` and related code.
Every item needs one disposition: editable source, generic engine behavior,
compatibility data, or explicitly unresolved work with an owner milestone.

### C1.3 Establish profile and format contracts

- Find every feature gate inferred from roster presence; replace none during the
  audit, but specify the explicit flags and their Original/Updated defaults.
- Separate immutable unit definitions from mutable/damaged instances and special
  training actors. Document what the library exporter normalizes and how the
  importer will avoid that loss.
- Measure real map, entrance, service, instruction, variable and graphics counts.
  Compare with source, runtime, editor and save capacities. Record memory/build
  size implications and Windows stack exposure before proposing limit changes.
- Specify the compatibility startup/content extension, source ownership,
  resource overrides, stable-ID mappings, provenance schema and save identity.
- Specify BLD round-trip/source-map requirements and the event bridge's
  continuation/state contract. Identify one difficult example for early testing.

### C1.4 Audit distribution and design cleanup

- Inventory tracked/staged files, generated artifacts and packaging inputs for
  original-derived material, including nested pixel arrays and library entries.
- Account for the 20 known Last Beacon images and any further findings. Design
  an extraction/reconstruction migration preserving the owner's local edits.
- Define negative fixtures proving that raw originals, converted assets, copied
  dialogue and unknown provenance cannot enter redistributable output silently.
- Record historical repository exposure separately; do not rewrite history.

### C1.5 Deliver and gate

Deliver a contract document/schema draft, the inventory, a dependency graph,
profile comparison and a prioritized parity suite. Begin
`docs/CHI_IMPORT_PROGRESS.md` when implementation starts, recording these results
and the next exact increment. Link private evidence by path and digest.

**Gate:** all 26 known BLD files and every referenced resource family are
accounted for; supported input fingerprints are explicit; no campaign system is
implicitly assumed to come from the current definition export. Unknowns have a
bounded experiment and blocking milestone. C2 can start only once its loading,
profile, identity and source contracts are sufficiently resolved.

Suggested commits: inventory/baseline; schema and compatibility contracts;
provenance audit and verification plan. An independent architecture/provenance
review is useful here, before interfaces become expensive to change.

## 7. C2 — Shared importer, isolation and first playable slice

**Goal:** generate real project-owned inputs and prove they execute correctly in
both profiles. Full campaign editability remains C3/C4 work.

### C2.1 Implement bounded extraction and generation

- Add a reusable import service and headless entry point. Accept source directory,
  output parent, profile selection and explicit import settings. CLI spelling is
  finalized with the service; do not document unimplemented commands as usable.
- Validate the supported original version by content fingerprints, not names
  alone. Reuse verified decoders and cache preparation. Unsupported/incomplete
  sources fail with a precise missing-file or version report.
- Hash inputs, use a private staging directory, validate generated content and
  publish only completed projects. Detect source changes during extraction.
- For Both, publish a consistent pair under a new parent or use an explicit
  transaction record. A cancelled/failing job must not present a partial project
  as successful. Resume only stages whose inputs and outputs still verify.
- Refuse occupied destinations and path escapes, including symlink/reparse
  cases. Do not overwrite originals, shared caches, saves or user source files.
- Emit a reproducible import manifest, provenance closure and capability report
  distinguishing editable, compatibility-only and not-yet-exposed content.

### C2.2 Add explicit runtime profile and resource overrides

- Implement the versioned project compatibility adapter from C1. Existing
  project startup modes and normal editions retain their meanings.
- Load project-owned overrides for the first slice, with explicit documented
  fallback only for content still awaiting conversion. Final C5 imports must
  have no hidden campaign-content fallback to hard-coded settings.
- Replace roster-count feature selection at the audited sites with capabilities
  while preserving built-in behavior. Check that Original's exported definitions
  do not enable the broker or Enhanced rules.
- Load exact templates and actor state for training; preserve the inert shell,
  damage, mission equipment, costs and original ordinal mappings.
- Include the Updated additions through a profile overlay with correct licenses
  and original-derived dependency tracking.

### C2.3 Prove isolation and introduce the import dialog

- Assign separate package IDs/save namespaces to both generated projects and
  register them as user projects. Do not replace normal launcher game entries.
- Add the first wizard: source, edition choice, destination, progress/cancel,
  diagnostics and completed-project Edit/Play links. Keep extraction logic out
  of GUI callbacks; use the shared service and task model.
- Prove six save slots work separately for each imported project and both normal
  editions. Record existing save hashes before/after; do not migrate them.
- Test editing one profile, shared-cache copy-on-edit and independent reimport.
  Changes must not leak to the other project or a built-in edition.
- Add provenance enforcement for new generated projects and application delivery.
  Implement the agreed reversible current-tree asset reconstruction approach
  without including the owner's original-derived local payloads in commits.

### C2.4 Verify the Citadel/training slice

Use the actual original Citadel, world edge, training entrance and first mission.
Include startup/intro choice, a training briefing, unit startup, manual and
computer control paths as applicable, completion/failure, return to base and
save/reload at a yielded message or menu. Include one nearby shop and a visible
dialogue or price edit to prove overrides reach the native campaign path.

Run identical seeded inputs against the built-in Original and its import, then
Updated and its import. Compare normalized gameplay state, RNG, map/actor
positions, active script location and presentation milestones. Package IDs make
cross-project save envelopes intentionally different; do not compare those as
if they should be byte-identical.

**Gate:** both generated projects play the slice and its edited variation;
normal games and saves still work; malformed input, cancellation, existing
destination and source-change tests preserve prior state. Report unexposed
campaign content plainly. Passing C2 does not mean the full campaign is editable.

Suggested commits: extraction service; project/profile adapter; save isolation;
wizard; provenance enforcement/migration; retained slice evidence. This is the
recommended first implementation stopping point for a review.

## 8. C3 — Editable world, maps and presentation resources

**Goal:** expose the full campaign's spatial and presentation data through the
Construction Kit, preserving both the unedited result and ordinary editability.

### C3.1 Import complete maps and world composition

- Convert every original local map and relevant alternate state, with tile
  references, graphics-set selection, collision/water semantics, entrances,
  place/room IDs, NPC positions/routes and actor placement metadata.
- Expose world dimensions, seed, generator inputs, jigsaws, town placements and
  transition rules. Preserve exact coordinate transforms and overlay priority.
- Include ruined Citadel/invasion transitions, cache island and access rules,
  town boundaries, encounter exclusions and exploration/discovery state.
- Wire map edits into the original adapter so terrain queries, party followers,
  combat placement, water depth and drawing consult the same effective map.
- Add duplicate/move/rename operations with stable references and useful limits.
  A new entrance may reference an existing script now; new mission wiring comes
  in C4. Do not hard-code original coordinates as uneditable special cases.

### C3.2 Import art and animation for editing

- Expose tiles, unit and infantry sprites, direction/frame metadata, animation
  timing, palettes, portraits, building pictures, full-screen art and fonts in
  the existing pickers and editors.
- Preserve indices, transparency, animation ordering, palette selection and
  original dimensions. Retain force-field/vegetation behavior and special
  graphics switches rather than importing only a still frame.
- Make local edit/clone/import operations update project-owned assets and their
  provenance. Drawing over an imported image keeps its derived origin.
- Expose supported sound/music/effect references and timing parameters without
  replacing the original playback programs with guessed approximations. Reuse
  existing verified extraction; never package executable code as a shortcut.
- Extend libraries, structure tools and pattern transfers to retain provenance
  through their full dependency closures. Imported campaigns should be usable
  with the same tile, building, road, wall and sprite workflows as other games.

### C3.3 Integrate editor and headless authoring

Use ordinary map/world views, contextual tile editing, animation previews,
source navigation, project build and Play. Add imported IDs and properties to
catalogue/search/inspect and validated commands. A headless author must be able
to find and change a town or entrance without knowing binary offsets.

Support Undo/Redo, Save/reopen, source ownership, protected regions, review
previews and conflict diagnostics. Handle missing local original dependencies
with a repair/import action; do not show a broken canvas or quietly substitute
unrelated assets. Large worlds must load/preview through bounded jobs.

### C3.4 Verify equivalence and edit workflows

- Compare all imported map cells/properties and generator table digests, then
  rendered crops across all graphics sets and important boundary joins.
- Test the canonical original seed plus a small fixed seed set. Compare terrain
  and RNG results, town placement and streaming order where relevant. State
  clearly which seeds and regions were executed versus structurally compared.
- Check original and ruined Citadel edges, starport approaches, water near the
  cache, force fields, infantry/mech formation and combat/exploration transitions.
- Demonstrate moving a town, editing a jigsaw, changing a blocked tile, moving an
  entrance, adding an NPC route, cloning a sprite and changing an animation.
  Validate/build/play, Undo/Redo and reopen each retained example.
- Confirm edits to one project or library copy leave the other imported project,
  normal games and immutable cache unchanged.

**Gate:** the full campaign's spatial/resource inventory has usable edit surfaces;
unedited data has differential evidence; representative changes affect actual
play, collision and event placement. Any representation that only previews but
does not affect runtime fails this gate.

Suggested commits: map conversion; generator/overlay overrides; graphics and
animation ownership; editor/authoring operations; world/resource evidence.

## 9. C4 — Editable story, services and campaign progression

**Goal:** make the entire existing campaign's content editable while preserving
its interpreter semantics and specialized interactions. Complete these increments
in order; keep each playable before expanding the next.

### C4.1 BLD source representation and round-trip compiler

- Implement the typed source format, instruction validation, stable labels and
  original-to-source-to-compiled location maps agreed in C1.
- Decode all 26 programs. Preserve control flow, menu selectors/layout, text
  operands, native contexts, byte arithmetic, waits and animation commands.
- Compile unchanged sources back to byte-identical programs where the format
  permits it. Explain and prove any necessary normalization with semantic tests;
  never discard unreachable/unknown data merely because a graph walk omits it.
- Exercise malformed branches, unknown operands, oversized text/programs,
  recursion/loops and invalid native calls with clear failure locations.
- Add an editor view with readable descriptions, editable dialogue/parameters
  and explicit compatibility operations. Visual grouping must not consume one
  authored event ID for every low-level BLD instruction.
- A parser-only or hidden raw-file representation is insufficient: test actual
  text, condition, branch, menu and action edits through the editor and CLI.

### C4.2 Named native actions and service content

Build the native-action registry and externalize its content parameters without
changing original flow. Inventory every used context/action combination, not
just the highest numeric action ID. Each entry documents requirements, outputs,
state mutations, error behavior and possible yields.

Expose shop inventory/prices and purchase recipient selection; repair/rearm/heal
costs and messages; recruitment and spy replacement rules; prison/starport theft;
training selection; garage/mech assignment; broker inventory; theatre, inventor,
Comstar, meal/newspaper and other building interactions found by C1.

Keep exact current service behavior: menus, text placement, per-mech weapon lists,
damage eligibility, charges, party changes and save continuation. Existing authored
service helpers may share mechanics only after equivalent behavior is proven.
Do not substitute simplified services just to make the inventory appear complete.

### C4.3 Mission and campaign settings

Implemented through the [mission editor/CLI](CHI_MISSION_AUTHORING.md).
The [coverage ledger](CHI_CAMPAIGN_COVERAGE.md) records all C1 systems,
editable fields, runtime consumers and bounded verification.

Externalize training mission definitions, opponents/instances, allowed controls,
outcomes, return messages, spawn/retreat rules and story effects. Include the
invasion transition, four Jenner attackers, ruined graphics switch and escape.

Expose encounters and their choices/rewards/salvage, starport restrictions, arena
flow, cache access/contents, special actors and the ending sequence. Replace
campaign-specific coordinates, text, quantities and conditions with validated
references/fields while retaining generic combat and rendering code in C.

Create a coverage table for every inventoried campaign system: source location,
editable fields, runtime consumer, editor/CLI operation, preserved behavior and
verification case. An unexposed hard-coded campaign rule is a remaining task,
not a completed import simply because its native function still runs.

### C4.4 Bridge new events and saved continuations

- Implement explicit BLD/native-to-authored and authored-to-compatibility calls
  with bounded nesting, validation and defined return behavior.
- Keep waits, choices, combat results and animation/audio sequencing owned by
  serializable engine state. Define abort, failure, cancellation and re-entry.
- Test saving during a BLD menu, service interaction, event wait, battle outcome
  and a call across the bridge. Reload the same pinned package and resume once,
  without duplicate purchases/rewards or skipped effects.
- Resolve diagnostic and coverage locations back to editable sources. Extend the
  current authored-event observer to measure BLD/native branches explicitly;
  do not infer their execution from authored event counts.
- Provide one ordinary new quest example that starts at an added entrance,
  uses original campaign state, runs a new event/encounter and returns to normal
  exploration. It must be buildable through GUI and headless operations.

### C4.5 Campaign verification and gate

Run targeted suites for each service/mission increment, plus cross-profile checks
of changed compatibility code. Preserve RNG consumption and sequencing. Retain
a playable complete route through both imported campaigns before entering C5.

**Gate:** all 26 scripts and all C1 campaign systems have explicit dispositions;
the existing campaign's content is editable; representative additions work;
saved continuations and full progression pass. Unknown opcode/native semantics
needed by the campaign block completion. Explicitly unsupported *new* mechanics
may remain documented engine limitations.

Suggested commits: BLD IR/compiler; BLD editor and source maps; native-action
registry; service groups; mission groups; event bridge and persistence; new-quest
demonstration and campaign evidence. Review the bridge/persistence design before
expanding to every service, since mistakes there are expensive to repeat.

## 10. C5 — Fidelity, setup and distribution verification

**Goal:** a user with the original files can reliably obtain, edit and play both
campaigns, with evidence for the supported scope and no original assets shipped
by the application distribution.

### C5.1 Finish the setup and recovery experience

- Complete the wizard's source/version guidance, edition explanations, resource
  configuration, progress, cancellation, retries and finished-project actions.
- Test a fresh application setup with no prepared caches; paths with spaces,
  non-ASCII user directories, moved project roots and offline operation.
- Verify missing/corrupt files, wrong versions, unavailable destinations,
  read-only locations, interrupted staging and changed inputs produce actionable
  errors without damaging originals or existing work.
- Test the packaged application as delivered, not only a developer checkout.
  Establish behavior when the original install is later unavailable: completed
  project-owned resources should play; unavailable external dependencies must
  be identified and repairable, never silently replaced.
- Ensure build/Play uses the current validated source revision, preserves dirty
  forms correctly and does not replay stale validation failures.

### C5.2 Run the campaign and editing acceptance matrix

| Area | Required evidence |
| --- | --- |
| Startup and profiles | Correct intro/menu order, Original feature defaults, Updated broker/roster/art and Enhanced/Legacy settings |
| Training | All missions; shell behavior; movement/physical attacks; pass/fail; return popup; final invasion and escape |
| World and towns | Original world dimensions/generation; joins; entrances; NPCs; water; discovery; intact/ruined graphics; full-party movement |
| Services | Shops/recipient assignment; repair/rearm/heal; recruitment/spy replacement; garage/assignment; both thefts; special buildings |
| Combat | Encounter choice/description; valid placement; starport restrictions; computer-control interruption; victory/salvage; arena exit |
| Presentation | Critical menus, text bounds, portraits/palettes, sprite/terrain animations, audio event order and completion |
| Campaign ending | Cache/story prerequisites, final route and correct post-ending behavior |
| Saves | Six slots per imported project; normal edition saves preserved; save/reload at held menus, effects, combat and bridged events |
| Editing | Terrain/town/entrance/NPC, sprite/animation, dialogue/branch, shop/price, unit/weapon, mission and new quest edits |
| Isolation | Original vs Updated imports; two copies of one profile; libraries/cache; reimport; normal games unaffected |
| Distribution | No original-derived payload in clean application build or redistributable recipe/mod; local import supplies required content |

Use the original-compatibility inventory to expand this matrix into named cases,
not just a single smoke test per row. Complete one bounded end-to-end route per
profile and use checkpoints for branch/service regressions. Include a party with
multiple units and an Updated-only unit; one starting Locust is not enough.

Compare built-in and imported behavior at meaningful state boundaries. Preserve
pixel/audio evidence privately. Compare rendered regions and sound event/sample
traces according to existing timing evidence; do not claim that automated audio
checks establish physical XT speaker equivalence.

Run existing Python/native regression and the affected GUI journeys. Build Linux
and Windows sequentially. Compare the same imported content under Linux and Wine
with pinned seeds and same-project save/state checks. Separately test the native
Windows launcher/Tk wizard and editor when available. Wine/native-player success
does not prove native Windows GUI behavior; record it as UNKNOWN until observed.

### C5.3 Enforce provenance and document the result

- Exercise clean-tree/application packaging and generated mod/recipe export
  against the negative fixtures from C1. Inspect actual output archives and
  nested data, not just a policy flag or filename list.
- Ensure original-derived test artifacts and generated campaign sources are
  ignored locally and rejected by the repository/distribution guard when staged
  or packaged by mistake. Document limitations of detection and origin metadata.
- Validate the Last Beacon reconstruction path from a clean checkout plus local
  original files, while preserving the owner's separate local working project.
- Document import/edit/build/play, both profiles, resource requirements, separate
  saves, reimport, backup, sharing and unsupported source versions.
- Publish an editability reference and a fidelity/coverage ledger distinguishing
  VERIFIED, INFERRED, APPROXIMATE and UNKNOWN. Static inclusion, successful load,
  observed execution and branch coverage are different claims.
- Make independent Astra audit findings actionable; fix blockers and rerun the
  affected checks before marking C5 complete.

**Gate:** both complete campaigns work and can be meaningfully altered; profile
and save isolation hold; setup and recovery work on each claimed platform; the
distribution contains only permitted materials. State all unresolved fidelity
and platform limits. Missing native Windows GUI evidence blocks a claim that
that workflow is verified, rather than being disguised by a Wine result.

Suggested commits: final wizard/recovery; full acceptance fixtures; distribution
guards and reconstruction evidence; user documentation; audit fixes/evidence.

## 11. Verification without replaying everything after every edit

Use existing retained suites, dependency selection, saved journeys and source
review. Add imported-script/native-action dependencies to that machinery rather
than building an unrelated test runner.

| Change | Smallest useful verification before committing |
| --- | --- |
| Extractor/schema | Synthetic valid/invalid cases, deterministic output and private original-input round trip |
| Profile/loading/save identity | Both-profile slice, normal editions, namespace/digest rejection and preserved old save hashes |
| Map/graphics edit path | Relevant map/world regions, collision/placement, visual crop, Undo and Save/reopen/build |
| BLD compiler/native service | Instruction/branch cases, one affected building route, yielded save/reload and profile comparison |
| Event bridge/persistence | Both directions, nested/error paths, saved continuation and no duplicate effects |
| Packaging/wizard | Clean install/import, failure/cancel recovery, archive provenance and affected GUI journey |

At milestone boundaries, run the broader declared regression set. Repeat it
after a material shared change or failure, not after every prose or isolated UI
edit. Reuse original DOS oracle evidence where applicable; make new bounded
oracle observations for disagreements and unknown semantics. Do not automate
repeated full-campaign DOS sessions merely to rediscover known behavior.

Keep baseline and candidate content hashes with each test. A checkpoint from a
normal edition is not automatically a valid imported-project save: use recorded
actions, explicitly equivalent test starts or a separately validated test-only
mapping. Never bypass production save checks to make a fixture pass.

For each comparison record inputs, seed, selected cases, actual executed cases,
observed coverage, state/RNG assertions and limitations. A declared dependency
or a graph edge is not evidence that a branch executed. Unknown dependencies
require broader checks. Set finite time/tick/step budgets and retain failed
reproductions so the next session can continue without repeating discovery.

## 12. Implementation handoff and independent audit

### Per-increment working record

Maintain `docs/CHI_IMPORT_PROGRESS.md` once implementation begins. Each increment
records: scope and contract changes; commits; tests and results; private evidence
paths/digests; unresolved findings; preserved user/reference state; and the next
concrete action. Update milestone status only when its gate passes.

Document enough to resume from a fresh session. Avoid pasting full extracted
scripts, assets or long terminal transcripts into tracked handoff files. Read
only relevant source modules for the next increment and use targeted searches.
Treat this plan's baseline facts as starting points to verify, not permanent
truth if the repository has moved on.

When an authorized milestone range is in progress, routine implementation choices
and successful gates do not need repeated permission. Stop for a decision only
where scope or destructive action genuinely requires one. If the task is stopped
between sessions, preserve a playable checkpoint and record any failing case
precisely; do not mark it passed to obtain a clean summary.

### Suggested first implementation instruction

> Read PROMPT.md, docs/CHI_EDITABLE_CAMPAIGNS_PLAN.md and current project status.
> Implement C1, then C2, in the documented increments. Preserve the two reference
> directories, existing saves and unrelated user changes. Create the progress
> ledger, commit each verified increment and stop after the C2 Citadel/training
> gate. Do not begin full C3/C4 conversion or rewrite Git history. Keep imported
> assets and private evidence out of commits. Report completed gates, limitations,
> commit IDs and the next recommended step. Do not push.

Later handoffs can authorize C3, the individual C4 increments, then C5. The main
reason to split C4 is its state and native-service complexity, not an expectation
that every field requires another user approval.

### Astra review checkpoints

| Checkpoint | Independent review focus |
| --- | --- |
| After C1/C2 | Complete resource accounting, exact unit instances, explicit edition gates, cache/project isolation, provenance and staging safety |
| During C4, before broad expansion | BLD round trips, byte semantics, native context, authorability, event bridge and save continuation |
| Before C5 completion | Actual campaign evidence, failed/unknown coverage, clean distribution, platform claims, preserved built-in behavior and user work |

Suggested audit instruction:

> Audit the implementation against docs/CHI_EDITABLE_CAMPAIGNS_PLAN.md and its
> progress ledger. Inspect code and retained evidence independently. Prioritize
> data loss, original-derived content entering commits/releases, silent profile
> changes, script/continuation errors, hidden hard-coded campaign content and
> claims unsupported by executed tests. Reproduce focused failures where useful;
> preserve reference directories and user files. Report findings with severity,
> file locations, reproduction and the milestone gate affected. Do not make
> implementation changes unless separately requested.

An audit should challenge the equivalence and editing claims, not merely confirm
that the importer produces files. A campaign which cannot change its missions,
a copied asset which lost its provenance, or a held script which cannot resume
is a functional failure even when a new-game screenshot looks correct.

## 13. Work deliberately outside these five milestones

- Automatic migration of existing normal Original/Updated saves into imported
  campaigns. A later explicit migration can be designed once state mappings are
  stable; existing supported migration tools must continue working meanwhile.
- Universal import of other DOS versions or unrelated Westwood games. Support
  the audited original version first and diagnose others accurately.
- Replacing every compatibility operation with Lua or removing the legacy BLD
  interpreter. Dual scripting with explicit integration is sufficient here.
- Implementing new gameplay mechanics unrelated to making these campaigns
  editable, or fixing every inherited DOS-fidelity gap during conversion.
- Shipping original content, granting rights to it, rewriting repository history,
  deleting user projects, or publishing a release automatically.

These boundaries keep the deliverable concrete: **two complete, separately
editable CHI campaigns, generated locally, with preserved baseline behavior and
a practical route from an edit to a playable game.**
