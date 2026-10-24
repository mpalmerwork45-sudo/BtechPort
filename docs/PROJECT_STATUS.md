# Project status — original fidelity and editable projects, 2026-10-24

**C4.5 campaign gate passed; C5 implementation/delivery verified on Linux and Wine.**
Both imported campaigns reach their endings on declared routes (Updated selects
Legacy in Settings). The combined comparison covers 441,246 gameplay ticks per
platform plus service/mission/spatial/quest continuations and multiple units.
The importer has retry/staging recovery, Unicode Windows I/O, and a GUI/CLI
asset-free reconstruction workflow. Actual Linux/Windows archives pass payload
checks; the packaged Linux setup/import/edit/reconstruction/player checks pass.
The later save/death fixes pass 462 Python tests plus three focused migration
checks, and 95 native tests on each platform, followed by five focused checks
after the final dialogue bounds adjustment.

[Acceptance, corrections and limits](CHI_ACCEPTANCE.md),
[sharing recipes](CHI_RECONSTRUCTION.md), [progress](CHI_IMPORT_PROGRESS.md).
Native Windows Tk and independent Astra sign-off remain pending. An Enhanced-only
ending route is unverified. Imported saves remain pinned to exact content.

**Save recovery and original death popup — implemented and verified.** Editor
Play now retains its six slots between launches of the same revision and can
recover vacant slots from matching retained runs. The owner's recent Updated
save is restored with its exact campaign and preserved progress; later edits
and original save files are backed up separately. Jason/Rex death text matches
the original-derived interior pixel hashes, with native popup geometry and a
working replay/quit prompt. A narrow copy updater adds the new text to an old
import without changing its gameplay data or save payload. See
[recovery details](EDITOR_SAVE_GAMES.md),
[death evidence and limits](GAME_OVER_PRESENTATION.md).

The following entries record earlier increments; their then-open milestone
statements are superseded by the current acceptance report.

**C4.4 first increment: map/startup fixes and native script observations — implemented.**
Older imported projects now expose **Local maps (enable editing)** and **World /
towns (enable editing)** directly in the tree. Opening either enables the existing
map tools as one Undoable draft change. Native **Play from start** shows the
logo/title sequence; **Play here** still starts at the selected location.

**Project → CHI script coverage** reads automatic Play traces, shows declared
and observed instructions/branches for all 26 BLD programs and opens source
labels. Native service entries/returns are measured; their internal C branches
remain unknown. Traces are pinned to the exact content revision and do not
change save bytes. [Usage](CHI_NATIVE_COVERAGE.md),
[verification](TESTING.md#native-import-usability-and-script-observation--2026-10-24).

**433 Python tests and 94 native tests on Linux and Windows/Wine pass**, followed
by six focused Python checks after final reporting adjustments. Both Linux GUI
journeys pass. Six replays match Linux/Windows state, saves, frames and trace
bytes over 269,500 ticks per platform. Both references, three pending owner
files and twenty normal saves remain unchanged. Native Windows Python/Tk
remains UNKNOWN.

Implementation commit: `dc51109`. Generated projects, traces and original-derived
resources remain private; no proprietary payloads are included in this change.

**C4.4 is not complete.** The mixed BLD/authored-event runtime, saved returns and
added-quest example remain [C4.4b–c](CHI_EVENT_BRIDGE_DESIGN.md). Registered
imports are not silently upgraded. Reported building-screen differences have
not been reproduced in the tested port/import routes; those comparisons do not
establish pixel equivalence to DOS for every screen.

**C4.3: native mission and campaign settings — implemented and verified.**
**Project → CHI missions and campaign** exposes 837 typed settings and 65 mech
roles: initial state, training/opponents/outcomes, recognition/driving/recovery,
invasion, encounters/rewards/salvage, Rex, prison, arena and cache/ending. Native
mechanics and saved continuations remain in the existing engine. GUI/CLI,
source builds, scopes/protection, Undo/Save/recovery and Problems share the
same model. [Usage](CHI_MISSION_AUTHORING.md),
[all-system coverage](CHI_CAMPAIGN_COVERAGE.md).

**427 Python tests and 94 native tests on Linux and Windows/Wine pass.** Nine
focused Python and 33 native Linux cases pass after final catalogue additions.
Both profiles retain the 108,156-tick built-in comparison and all 52 BLD bytes.
Defaults match C4.2 for **365,690 gameplay/RNG ticks per platform**, including
the complete fresh-game route. Seven edited journeys per profile pass 70 held
save/reload/render checkpoints per platform; all 26 final Linux/Windows save
pairs match exactly. Mission, BLD and service Linux GUI journeys pass. Native
Windows Python/Tk remains UNKNOWN. [Verification](TESTING.md#native-mission-authoring--2026-10-24).

Implementation commit: `19a2db9`. Both reference trees, three pending owner files
and twenty normal saves remain unchanged. No original-derived resources or
generated campaigns are committed. Older imports enable mission editing as one
Undoable change; preserve their prior content revision for old imported saves.
Registered projects are not silently upgraded. C4.4–C4.5 and C5 remain open.

**C4.2: native service content and action registry — implemented and verified.**
**Project → CHI services** exposes 156 typed settings, Updated broker stock and
47 named native actions covering all 76 observed action/building pairs. Prices,
repairs, healing, recruitment/spy settings, theft/garage policies, market values
and other building costs use the existing native state machines. Price text and
BLD fee operands can share parameter references. GUI/CLI commands, source builds,
scoping/protection, Undo/Save, draft recovery and problem navigation share the
same validated documents. [Usage](CHI_SERVICE_AUTHORING.md).

**418 Python tests and 93 Linux native tests pass.** All 93 Windows native tests
pass under Wine, followed by ten focused checks after the final world-market
caller/bounds adjustments. Both profiles retain the 108,156-tick built-in
comparison. Comparing the new defaults to C4.1 imports passes 214,544 ticks per
platform; all 52 BLD files remain byte-identical. Edited class, purchase, healing
and prison continuations pass on both platforms, with all 18 paired held saves
identical. Linux service and existing BLD GUI journeys pass. Native Windows
Python/Tk remains UNKNOWN. [Verification](TESTING.md#native-service-authoring--2026-10-24).

Both reference trees, three pending owner files and twenty normal saves remain
unchanged. No proprietary resources or generated campaigns are committed. New
imports include service support; older imports enable it as one Undoable change
and retain their old content revision for old saves. Registered projects are
not silently upgraded. C4.3–C4.5 and C5 remain open.

**C4.1: labelled BLD source and compilation — implemented and verified.**
Imported Original and Updated projects now expose all 26 building programs in
**Project → CHI scripts**. Dialogue, conditions, branches, native menu choices
and supported compatibility actions use typed fields and stable labels. The
GUI and headless commands share validation, Undo/Redo, source modules, recovery,
problem navigation and Save/Play. Unchanged sources reproduce every original
BLD byte, including preserved unreachable data. Native service continuations
resolve relocated instruction starts and return boundaries.

**410 Python tests and all 92 native tests on Linux and Windows/Wine pass.**
Both editions retain the 108,156-tick unedited comparison. Edited programs pass
214,544 gameplay/RNG ticks per platform; all eleven paired held saves match
byte-for-byte. A real building-entry journey proves dialogue, condition, jump,
menu and native-action edits. The Linux GUI editing/recovery/Play journey passes;
native Windows Python/Tk remains UNKNOWN. [Usage](BLD_AUTHORING.md),
[evidence and limits](TESTING.md#labelled-bld-authoring--2026-10-24).

Original-derived sources/evidence remain private. Both reference trees, the
three pending owner files and twenty observed normal saves are unchanged.
Enabling source on an older import changes its strict content identity: retain
the old project revision for its existing imported saves. Existing registered
projects are not silently upgraded. C4.2–C4.5 and C5 remain open.

**C3: native CHI spatial and presentation authoring — implemented and verified.**
Imported campaigns now expose all 15 maps, the 1,024-square native world,
generator/jigsaw inputs, town placements, building entrances, town-walker routes
and presentation resources. The regular map/construction/pattern/pixel/sprite
tools, shared Undo/Save, modular sources, headless authoring and world review/
protection operate on these effective native documents. Edited data reaches
collision, world composition and playback while retaining native BLD execution.

**400 Python tests and all 91 native tests on Linux and Windows/Wine pass.**
All map structures/cells and bank edge crops match; whole-world terrain matches
at three declared seeds in both invasion states for both profiles. Depth crossing
uses a sampled grid. Fifteen retained edits pass native checks on both platforms;
edited film held saves match byte-for-byte. Unedited profiles still match the
108,156-tick baseline, and a moved Citadel matches 44,192 local gameplay/RNG
ticks. Both Linux GUI import and map/resource authoring journeys pass. Native
Windows Python/Tk remains UNKNOWN. [Usage and save identity](CHI_IMPORT.md),
[evidence and limits](TESTING.md#chi-spatial-and-presentation-authoring--2026-10-23).

No original-derived assets are committed. Both reference trees, three pending
owner files and twenty observed normal saves remain unchanged. Existing C2
projects can enable map tools as one Undoable change; retain their old revision
for old imported saves. Native story/mission/service authoring remains C4.

**C1–C2: editable CHI import first pass — implemented and verified.**
[Import CHI](CHI_IMPORT.md) creates separately owned Original/Updated projects
from supported DOS 1.03 files, with explicit edition features, local resources,
isolated saves and native-dialogue editing. Full world/BLD/mission editing
remains C3–C4. Both profiles match built-ins for **108,156 combined replay ticks**
on Linux and under Wine, including rendered checkpoints and held saves. Exact
Linux/Windows saves, state and final frames also match for the retained combat
route. **383 Python and 91 native regression tests pass**; the Linux GUI import,
Undo/Redo, Save/reopen, Play and cancellation journey passes. Five affected
Windows regression cases pass under Wine. Native Windows Python/Tk remains UNKNOWN.

The public Last Beacon baseline excludes 20 original-derived tile payloads and
provides original-base reconstruction recipes. Seventeen had private pixel
edits; their exact local versions and all three pending owner files are preserved.
Application delivery checks indexed project snapshots before copying; new local
CHI imports cannot pass redistributable export. Historical Git content was not
rewritten. [Contracts and remaining limits](CHI_IMPORT_CONTRACT.md),
[progress](CHI_IMPORT_PROGRESS.md), [verification](TESTING.md#chi-campaign-import-first-pass--2026-10-23).

**Batch 1: test authoring and coverage — implemented and verified.**
[The suite workspace](TEST_SUITE_AUTHORING.md) stores editable test definitions
with the project, including source-project Save/reopen, draft recovery and Undo.
It supports portable imports/exports, seed sweeps, fixtures/checkpoints, honest
entrance/map/world/objective starters and retained native selected/full checks.
Declared, observed, unvisited, unrun and unknown evidence remain distinct;
failures navigate to their map/world position or referenced object. Linux and
Windows builds, native regression, Python regression and the GUI journey pass.
The independent suite also matches Linux/Windows save bytes under Wine. See
[verification](TESTING.md#suite-authoring-and-coverage--2026-10-23).

**Batch 2: measured editor responsiveness — implemented.**
[The comparison](EDITOR_RESPONSIVENESS.md) records normal snapshots falling from
282 to 25 ms and Undo/Redo from 1,088 to 18 ms on the 40-map/403-event source
campaign. Worker copies omit unused history, empty draft flushes avoid a full
transaction, and the source/table views avoid repeated reconstruction. Pending
fields retain full rollback protection. The source editing/build/Play journey,
sorting, cancellation, stale results and Save/reopen pass; **373 Python tests
pass**. First-time and pending-field work can still exceed 100 ms.

**AI4/AI5 review-linked scenario selection — implemented and verified, 2026-10-23.**
[Scenario selection](SCENARIO_SELECTION.md) inventories explicit dependencies on
both review revisions, explains suggested cases and runs selected/full suites
against the retained candidate. Changes → Checks and the CLI share hash-pinned
suite inputs, exact revision checks, seeds, cancellation and native artifacts.
Unknown dependencies recommend the full suite; omitted cases are never called
passed. Ordinary validation, protection, Undo and Save remain in force.

Implementation: `e7b7a2e`. **359 Python tests and 91 native tests pass**, followed
by 15 focused selection and 10 suite checks after final bounded-input/summary
adjustments. The new GUI journey and existing collaboration regression pass;
Linux/Windows builds pass. The independent fixture selects the expected cases
for a local briefing, shared tile/unit and town move. Selected seed runs match
the full suite's native state, coverage, exact saves and ordinary-input replay.
Windows/Wine matches the first selected case. The five-run suite takes 0.1445 s
versus 0.0539 s for two selected runs on that fixture, excluding dependency/input
capture; broader speedup is not implied. [Evidence](TESTING.md#review-linked-scenario-selection--2026-10-23).

The user's three pending Last Beacon files and both reference directories are
unchanged. Gameplay/save formats remain unchanged. Native Windows Python/Tk
interaction remains **UNKNOWN**.

**Next external checks:** native Windows launcher/Tk and the independent Astra
review. Preserve the coverage limits in [acceptance](CHI_ACCEPTANCE.md) when
expanding campaign cases or adding native quest adapters.

**AI5 world-review extension — implemented and verified, 2026-10-23.**
[World review and regional protection](WORLD_REVIEW.md) adds paired composed
planet previews, full-pixel detail crops, changed-town/terrain navigation and
named world-tile preservation rectangles. Indirect jigsaw, tile, palette and
owned-art changes are included. The planet editor can protect a dragged
selection; Changes uses existing groups, explicit exceptions, Undo and Save.
The CLI exposes the same retained paired crops through `review world`.

Implementation: `a03641d`. **344 Python tests and 91 native tests pass.**
The new GUI journey and existing Last Beacon collaboration regression pass.
The two-planet demonstration preserves a pond while moving a port and changing
terrain, then verifies Undo/Redo, Save/reopen and whole-party travel on both
planets. The Windows runner under isolated Wine matches Linux state and exact
save bytes. A 1024×1024 planet review/protection check takes **1.13 s / 38,400 KiB
maximum RSS** on the declared fixture. [Evidence](TESTING.md#world-review-and-regional-protection--2026-10-23).
The two reference directories and three pending Last Beacon files are preserved.
Game/save formats remain unchanged. Native Windows Python/Tk remains **UNKNOWN**.

The subsequently proposed scenario-selection extension is delivered above.

**AI4 saved-journey extension — implemented and verified, 2026-10-23.**
[Saved journeys](SAVED_JOURNEYS.md) start scenarios from explicitly pinned saves
with native exact-content/checksum validation and preserved RNG. Named checkpoints,
CLI/suite starts and **Play options → Checkpoints and trace** share the workflow.
Reports retain initial state and reproduction inputs, separate continuation
coverage, and label midbattle measurements. Scenario checks test the current
project; manual actions and interactive Play can use the historical snapshot.

Implementation: `1681942`. **330 Python tests and 91 native tests pass**, with
eight focused checkpoint tests also passing ASan/UBSan/LSan. The GUI journey
checks selection, reports, Play, ordinary actions and visible stale-content
errors. World Survey, the later Cairn escort and a round-2 defence continuation
all produce **identical final save bytes and input suffixes** to full journeys;
Windows/Wine matches Linux for all three. The escort continuation skips
**2,509 of 4,458 logical ticks**. [Evidence](TESTING.md#saved-journey-scenarios--2026-10-23).
Both reference directories and the three pending Last Beacon files are preserved.
Game/save formats are unchanged. Native Windows Python/Tk remains **UNKNOWN**.

The subsequently proposed world-review/protection extension is delivered above.

**AI4 world-route extension — implemented and verified, 2026-10-23.**
[World-route verification](WORLD_ROUTE_VERIFICATION.md) adds bounded native
searches through jigsaws, town overlays and sector boundaries. Scenarios walk to
source entrances or map/world coordinates and assert world position, whole-party
formation and per-planet discovery. Transfers use ordinary game events, and
checkpoints compare the complete saved continuation. Editor Problems opens the
source town/entrance or the correct planet with a persistent location marker.

The independent World Survey journey uses three mechs, a tracked vehicle and
two infantry across two planets. Tests also cover maximum-size worlds, narrow
paths, multi-step collision, unexpected region events and unknown coverage when
a search budget expires. **322 Python tests, 91 native tests, 12 sanitizer tests
and the GUI journey pass.** The Windows runner under isolated Wine produces
identical state and save bytes to Linux. [Evidence](TESTING.md#world-route-verification--2026-10-23).
Implementation: `1a9c51b`. Original/Updated gameplay and save formats are unchanged;
the user's three Last Beacon files and both reference directories are preserved.

The subsequently proposed saved-journey extension is delivered above.

**AI8 campaign demonstration and delivery — implemented, 2026-10-23.**
Select **Greybank Dispatch (campaign)** in the launcher. Its depot, alternative
assault/recovery contracts, timed defence and vehicle escort span five maps
and 104 events. [Recorded recipes](CAMPAIGN_RECIPES.md) generate normal editable
content and modular sources, retain exact inputs/provenance, diagnose/repair a
deployment error and reproduce the playable fingerprint. Both opening routes,
services, failure/retreat routes and checkpoints pass in eight scenario runs.
The scripted GUI journey preserves manual terrain/dialogue through a scoped
follow-up, Undo/Redo, Save/reopen and Play.

**Author** / **Author.cmd** now ship with Linux/Windows Construction Kit
distributions. No model/provider or network service is required. The installed
Linux GUI/CLI and native-only independent game checks pass; the Windows native
campaign routes pass under isolated Wine. **310 Python and 91 native tests
pass.** Native Windows Python/Tk remains **UNKNOWN**, and Windows packaging
still requires an installed or explicitly supplied full Python runtime.
See [verification](TESTING.md#ai8-recorded-campaign-and-delivery--2026-10-23).
The user's Last Beacon edits and both reference directories remain unchanged.

The subsequently proposed world-route extension is now delivered above.

**AI7b campaign capacity — implemented and verified, 2026-10-22.** Runtime
0.2.0 adds opt-in adventure v3: **64 local maps, 64 encounters, 1,024 events,
128 objectives and 128 variables**. Use **Project → Campaign sources and build
→ Upgrade campaign limits**, or the shared `campaign.upgrade` command. Existing
projects keep their format. Original/Updated and old authored saves still load;
v3 uses explicit save v52 and requires a new campaign after a format upgrade.
See [limits, compatibility and measurements](CAMPAIGN_CAPACITY.md).

The generated independent Frontier Circuit completes 20 contracts and checkpoints
across two planets, with identical Linux/Wine save bytes. Maximum/beyond-limit,
high-handle, journal page 128, old-save, corruption and editor journeys pass.
The user's three Last Beacon edits and both reference directories remain intact.
AI8 follows above with campaign recipes and delivery. General
unbounded whole-campaign navigation and native Windows Tk remain unverified.

**AI7a modular campaign sources — implemented, 2026-10-22.** Optional
`SOURCE.json` projects share GUI/CLI editing, journalled Save, Undo and recovery.
Maps, events, definitions, artwork and text compile deterministically to the
existing native package format. Errors retain source files/object paths;
**Project → Campaign sources and build** supplies conversion, object navigation
and Build. Existing packages remain unchanged. See the
[source guide](CAMPAIGN_SOURCES.md) and [test evidence](TESTING.md).

The separate Cairn Planets recipe builds two identical runtime packages from
387 source files, three local maps and two jigsaw planets. Its full defence and
escort route passes on Linux and under Wine, with checkpoints. Source notes
and formatting preserve save identity; conversion of a legacy package requires
a new campaign or deliberate save migration. Runtime/save layouts are unchanged.

AI7b followed with the optional capacity extension described above; AI8 is now
delivered. Declared world travel is now checked as recorded above; exhaustive
campaign solvability and native Windows Tk remain **UNKNOWN**.

**AI6b/AI6c and construction coverage — implemented, 2026-10-21.**
[Cairn Passage](../examples/cairn-passage/README.md) now combines timed relay
protection, reserve waves, an allied guard, a protected vehicle route, losses,
retreat and optional save version 51. Editor forms, command schemas, Lua queries
and scenario assertions share the native engine. [Semantics and limits](COMBAT_MISSIONS.md)
and [test evidence](TESTING.md) distinguish bounded verification from general AI balance.

Construction styles expose all roof/face roles and road connections, compose
joins from owned artwork, preserve hand edits and travel through the library.
All four T junctions are editable. Walls support 0..3 stories; zero renders only
top tiles. Event graph descriptions now include all 54 Last Beacon events.
Tables support ascending/descending/original order and dropdowns support typing.
Unit Library model names are uppercase while designation codes remain intact.

**AI7a, AI7b and AI8 are delivered above.** Further capacity changes and
world-spanning verification remain future work.
Native Windows Tk remains **UNKNOWN**; Windows runtime checks use isolated Wine.

## Earlier deliveries

**AI5 collaborative authoring — VERIFIED, 2026-10-20:** **Project → Changes and
protection** now reviews actual object/field changes, paired local maps, event
routes, dependencies and candidate checks. Preserve whole objects, selected
fields and local map regions; accept validated groups or approve named
exceptions. Compatible human construction detail survives, and displaced
detail is reported.

**Project → Local authoring session** connects an external author through a
local file inbox. Snapshot valid GUI drafts, submit revision/scoped proposals,
inspect/cancel jobs and apply through shared history. Review is the default.
Opt-in application still enforces protection and scope. Closing the review tab
retains work; replacing the project stops its session. Unit Library editing
has a separate scope and Save target.

The Last Beacon completion gate passes on a copy: human GUI dialogue, roof
paint and door movement survive a CLI encounter/road revision and one Undo.
The revised copy passes the full native two-contract route. **240 Python tests,
80 native tests, the new collaboration GUI journey and existing authoring GUI
regression pass.** Interrupted save, stale work, cancellation, invalid fields,
recovery and project/library isolation are covered. Both reference directories
and the user's three pre-existing working-tree edits remain unchanged.
See [verification](TESTING.md#ai5-collaborative-authoring--2026-10-20) and the
[author guide](AI_AUTHORING_GUIDE.md#review-changes-and-preserve-human-work).
Native Windows Tk remains **UNKNOWN**.

**Historical next step (now delivered): AI6a**, named mission regions, persistent variables/
counters and explicit objectives. AI tools already expose jigsaw worlds,
generation/painting, town placement and world previews. Larger campaign
capacity is AI7; world-spanning navigation verification remains future work.

**AI discovery and mission testing — VERIFIED, 2026-10-19:** approved steps
1–4 are complete in `f519114` and `d88ecd3`, following checkpoint `4ad570e`.
Project/library/atlas search, editable tags, dependency/provenance summaries,
labelled contact sheets, animation strips and map/world/event previews share
the editor's assets and operations. **Project → Content catalogue** exposes
them to human authors. **Project → Check mission** adds explicit event/objective
lint and actual C whole-party local navigation/deployment checks, with findings
that open their map/event and clear after repair. Stale results are refused.

The recorded suite passes **10/10 runs** across eight cases, including three
victory seeds, mid-combat save/reload, real retreat, natural defeat, once-only
rewards, cancellation paths and an explicit validated low-funds fixture.
Reports retain exact content, seed, traces, branches and combat reductions.
A separate playable **Relay Authoring Lab** imports a searched Firefly, creates
an animated barrier, exports visual evidence, deliberately breaks deployment,
diagnoses it, repairs through commands and passes the three affected victory
seeds. Run `python3 tools/authoring_demo.py --output work/my-authoring-lab` to
reproduce it; the checked local copy is `work/authoring-lab-20261019/game`.

Full Python tests **218/218**, native tests **80/80**, expanded real-editor
smoke and Windows authoring routes under Wine **8/8** pass. Native and Windows
analysis/player tools build with two compiler jobs. Reference guard:
**1,287 entries unchanged**; the three pre-existing Last Beacon working-tree
files still match the session baseline and remain outside these commits.
See [verification](TESTING.md#ai-authoring-discovery-and-mission-testing--2026-10-19)
and the updated [author guide](AI_AUTHORING_GUIDE.md).

Coverage is bounded to declared routes/seeds/policies and initial-party local
geometry. Arbitrary Lua, world navigation, later party compositions, general
balance and native Windows Tk remain **UNKNOWN**. AI5 was delivered subsequently
above; richer mechanics remain future work.
The [pause handoff](AI_AUTHORING_HANDOFF.md) is retained as historical context.

**AI authoring first pass — VERIFIED:** implementation commit `4f1ff6f`;
[author guide](AI_AUTHORING_GUIDE.md).
API v1 provides compiled capability discovery, bounded project/usage/map/route
queries, structured diagnostics and shared editing commands. Whole batches
validate through C, check revisions/write scope, record retry receipts and
publish through the editor's journal. GUI command-file exchange preserves
manual work, supports one-step Undo/Redo and refuses stale results. No model
or network service is needed.

The separate **Relay Contract** example is created by 99 recorded commands.
Its 39-step ordinary-input scenario completes a two-mech battle, workshop
visit, once-only payment, objective and multiple save/reloads. Full-map previews
use the editor decoder. Native tests **73/73** and Python tests **188/188** pass;
the real GUI paint/batch/Undo/save/Play journey passes. Windows targets build;
the Windows scenario passes under isolated Wine. Native Windows Tk remains
**UNKNOWN**. See [verification](TESTING.md#ai-authoring-first-pass--2026-10-18).

The subsequent discovery/testing results above extend this first pass.
AI5 adds protected review/local sessions above; richer campaign mechanics remain
in [AI6–AI8](AI_AUTHORING_PLAN.md). Authoring work used separate projects and
disposable test copies. Subsequent Last Beacon
artwork/map edits in the working tree were left untouched and outside these
commits. Both reference directories remain unchanged.

**User's Last Beacon revision — VERIFIED:** `bed75e9` preserves the revised
maps and editable artwork together with `EDITOR.json` (construction sets,
footprints, tile names, source provenance and pixel layers). The package has
three maps, 197 tile definitions, 128 images and 54 event nodes. Shared C
validation and the full `battletech-demo-contracts` route pass. People, shops,
encounters, flags and event definitions remain as in the preceding revision.
The map files were committed as supplied, without regenerating them. See
[Testing](TESTING.md#last-beacon-user-revision-and-ai-authoring-plan--2026-10-18).

**Authored terrain animation — VERIFIED:** original animated `chi:land` tiles
now use their existing three-frame cycle on custom maps, including the four
animated source tiles currently referenced by the user's demo. The editor
animates map, palette, chooser, construction and jigsaw tile images in place.
**Animated only**, **A** badges and frame/duration details make loops selectable;
**Animate tiles** pauses previews without changing the project. Clone/Edit
preserves original frames and timing; custom tiles expose **Frame time** and
the existing frame editor. Both runtime presentations support optional
`frame_ticks`, retaining old packages' default duration. Destroyed tiles keep
their static bank. Native tests **72/72** and Python tests **174/174** pass;
the private-display animation and Play/context journeys pass. Original decoder
and source references remain read-only. Timing follows the existing native
32 ms clock; this is not a new hardware-timing measurement of DOS.

**Play retries and contextual tile editing — VERIFIED:** Play checks the latest
draft again when edits change during preparation, clears obsolete validation
errors, and surfaces player startup failures with their logs. The top-right
Play button launches directly; Play options contains the other launch/stop
commands. Corrected entrances can launch without saving or restarting.

Map right-click **Edit tile pixels** and building/wall/road/jigsaw preview editing
show a 3 × 3 neighbourhood with an editable centre. Repeated artwork updates live;
other tiles remain read-only. The clicked projected cell supplies construction
context, including corners/faces. Clone, Undo/Redo, zoomed painting and save/reopen
pass. Local-map footprint erasure now uses **Shift + right-drag**; the designer's
footprint grid retains ordinary right-drag. **169/169 Python tests**, the new
Play/tile GUI journey and existing workspace, world/art, construction and canvas
checks pass. Both reference directories and the user's demo remain separate.

**Visible tile painting — VERIFIED:** the default **Paint on: Visible tiles**
replaces displayed ground/building tiles. The previous Base default hid strokes
under generated buildings, including a water tile found in the user's saved
map. Paint/Line/Rectangle/Fill/Paste/Cut and roads share the visible-surface
target; explicit Base/Overlay editing remains available. Markers only drag in
**Move markers** mode. Palette clicks select Paint when leaving a construction
or marker tool. Hand-painted construction details persist through Undo,
save/reopen and footprint reshaping while their projected cells remain.

The old **preview** marker was the last clicked Play here position. It is now
**Playtest start**, displayed only for that tool; the game's START is separate.
World tile selection activates Tile and strokes skip city overlays with a
local-map explanation. **164/164 Python tests** and the new mouse-driven
painting journey pass; detailed results are in [Testing](TESTING.md#visible-tile-painting--2026-10-18).

**Canvas controls:** Ctrl + mouse wheel zooms around the pointer on maps, worlds,
event graphs, jigsaws, tile/sprite canvases and construction footprints/previews.
Editable percentage dropdowns share safe input handling; construction preview
Fit and graph Fit stay synchronized. Local/world/jigsaw drawing tools are now
always-visible, wrapping buttons with a selected state. Building/Wall/Road
settings appear when their tool is active. Zoom stays outside game data/Undo.

**VERIFIED:** 158/158 Python tests, the new Linux canvas interaction journey,
existing visual-map, construction, world/art and workspace journeys, including 100/150/200%
interface scaling. Tests exposed a separate Unit Library preview dependency on
the editable demo; previews now build their own neutral map. Reference entries
remain **1,287/1,287 unchanged** and user demo edits remain separate. See the
[canvas verification](TESTING.md#canvas-zoom-and-visible-tools--2026-10-18).
Native Windows/macOS wheel input remains **UNKNOWN**; Windows MouseWheel and
Linux Button-4/5 event forms are exercised through Linux Tk.

The requested [map construction tools](M5_WORLD_ART_EDITOR.md#buildings-walls-and-roads)
are implemented: editable building/height and 1–3-storey wall part sets,
connecting road brushes, right-click preview tile creation/cloning/editing,
whole-sheet tile cloning, a persistent/exportable Pattern Library, local/world
terrain cut/copy/paste and expanded jigsaw drawing. New worlds default to the
original 1024 × 1024 dimensions. Shared forms, asset pickers and several preview
panes reserve their actions before the scrolling body so confirmation buttons
remain accessible.

The preview chooser now exposes **Project tiles** and **All tiles**, including
sheet filtering. Building/wall/road choices automatically register missing
graphics in the palette and reuse existing definitions. **VERIFIED:** all three
designer journeys, atomic Undo, cancellation, save/reopen, minimum-size controls,
**11/11 construction tests**, and the existing construction GUI/game-output check.

The map editor's **Construct** row now draws editable footprints using saved
tile styles: Brush, Line, Rectangle, Courtyard and Erase; buildings support
1–32 stories and walls 1–3 within map bounds. Subsequent strokes extend the same
object, erase holes or raise/lower sections; roofs, corners and visible faces
regenerate together. **New building / New wall** starts another object, and a
footprint selector resumes saved objects. Roads support width, shaped strokes
and neighbour-aware erasure. Styles and map footprints persist independently
through Save/reopen; the player uses compiled ordinary overlays.

**VERIFIED for direct drawing:** **157/157 Python tests**, live map box/cross/
courtyard/mixed-height/wall drawing, atomic Undo, resumed editing after reopening,
unfinished-stroke recovery and matching SDL/headless output for the drawn
courtyard. Map bounds and existing manually painted layers are protected.
Existing tile-browser and workspace GUI journeys pass, including event-inspector
draft saving alongside the new map-drawing drafts. The chooser
remembers per-project collection/filter, selections and scroll positions across
restarts, outside game data/history. Workspace tabs offer right-click **Close**
through the existing draft safeguards.

**VERIFIED for the preceding construction milestone:** **151/151 Python**, **72/72 native CTests**,
new Linux GUI authoring/save/reopen/recovery journeys, existing world/art and
workspace journeys, Clone ALL of an actual 250-tile CHI sheet, and matching
SDL/headless state and frame for a constructed game. **1,287 reference entries
are unchanged**. [Testing](TESTING.md#map-construction-and-tile-workflow--2026-10-18)
records commands and evidence. Heights generate ordinary map tiles; interior
storeys remain separate maps/events. New preset artwork is procedural editor
art, not original CHI artwork. Existing limits include the shared 256-sector
world/discovery budget. Native Windows Tk remains **UNKNOWN**; the engine was
not changed or rebuilt for this editor increment.

The approved [editor usability stages UI1–UI5](EDITOR_USABILITY_PLAN.md) are
implemented. The [workspace guide](EDITOR_WORKSPACE.md) covers the tabbed editor,
explorer/Inspector, Problems, direct asset navigation, scoped project/library
saves, labelled Undo/Redo and private draft recovery. UI5 adds bounded background
tasks, stale-validation protection, isolated Play/Stop and library preview,
scrollable/reflowing controls, scale settings, tooltips and keyboard help.

**VERIFIED at UI5:** 141 Python tests, 72 native CTests and 72 Windows/Wine CTests pass.
Linux GUI journeys cover independent save targets, partial Save All, invalid
fields/art recovery, missing-source recovery into a copy, edits during durable
writes, simulated write failure, navigation and real SDL Play/Stop. KWin checks
cover modal stacking, restored focus/grabs and minimize/restore on an isolated
desktop. Scaling captures cover 100%, 150% and 200%. Larger-fixture timings and
package checks are recorded in [TESTING](TESTING.md#editor-workspace-ui5--2026-10-18).
**UNKNOWN:** native Windows Tk and physical multi-monitor interaction. Wine
engine success does not close those GUI verification gates.

**BattleTech Construction Kit** is the editor/launcher name. The authorized
[five editor milestones](EDITOR_COMPLETION_MILESTONES.md) are implemented with
bounded verification: transactional service buildings; connected events,
objectives/journal and checkpoints; building/world/pixel tools; named unit
animations, equipment guidance and individual infantry sprites; and
[distribution, asset reports and explicit save migration](CONSTRUCTION_KIT_DELIVERY.md).
Broker navigation separates **Mechs** (weight classes) from **Vehicles** (one
scrolling list). Unit Library sprite editing preserves editable layers and actions.

Linux engine/model/GUI and bundled-runtime checks pass. Windows cross-build,
Wine engine/SDL and sanitizer checks pass; native Windows Tk remains unverified.
Migration accepts cosmetic changes and append-only definitions with unchanged
existing gameplay/ordinals. Construction remains the bounded CHI adapter, not a
complete tabletop unit designer. Exact limits are in the feature guides.

The [shared Unit Library and launcher](UNIT_LIBRARY_AND_LAUNCHER.md) now provide
82 blueprints (66 mechs, ten vehicles, six infantry templates), editable directly
in the library and copied between games with dependency closure, explicit
updates/variants and source attribution. Infantry properties are also available
in the main roster editor. The desktop launch window starts Original/Updated,
the demos and custom games, resumes F5 saves, opens the editor/library and builds
the application with two jobs. Linux and Windows entry scripts are included.
Fresh checks and portability bounds are in [TESTING](TESTING.md#unit-library-and-desktop-launcher).

The [25 new classic mech presets](../content/catalogues/mechs/README.md) use pinned
MegaMek records with documented CHI conversions and retained data attribution.
Library defaults now consistently assign Locust to reverse-jointed chassis,
red Stinger to the others, and original infantry animation to character
templates. A one-time migration preserves author statistics/custom artwork;
already-imported projects require an explicit replacement to adopt changes.

The [sprite editor](SPRITE_EDITOR.md) now has movement directions, named poses,
frame thumbnails, previous/next navigation, copy/paste, onion skin and playback
that leaves the editing selection in place. It displays the original shared
gaits and the new eight-direction sheets correctly. Its guide records the
new action tools and remaining bounds.

**BattleTech: Last Beacon 1.1.0** adds all ten vehicle presets to the existing
Mech exchange, alongside the nine mechs, with independent directional graphics.
Existing hand-edited demo terrain and doorway placement are preserved. A fresh
demo game is required because the package content changed. Fresh verification:
**109/109 Python**, **3/3 focused native suites**, the real Linux sprite-editor
workflow and **15/15 Linux SDL demo save/load screens**, plus the completed
two-contract route. See [follow-up evidence](TESTING.md#sprite-workflow-and-battletech-demo-vehicles).

[World/art editing](M5_WORLD_ART_EDITOR.md) and
[vehicles/multiple planets](M5_VEHICLES_AND_PLANETS.md) are implemented as bounded
authoring features: 4,096 tile definitions, 1,024 jigsaws, up to 16 planets
sharing 256 world sectors, city overlays, separate discovery and transfers.
The editor paints/clones actual tile pixels, flips/rotates/nudges frames, imports
images, edits animation frames and shows an animated unit preview with sprite
context actions. New mech/weapon/heat-sink/jump-jet definitions and ten sourced
vehicle presets are available. The asset-free
[Vehicle proving ground](../examples/vehicle-lab/README.md) exercises two planets,
three starting vehicles, a depot and a live battle. Vehicle construction and
critical rules remain explicitly approximate.

The preceding full world/art/vehicle verification: **70/70 native CTests**, **103/103 Python tests**,
**9/9 focused Wine** and **9/9 sanitizer suites**, plus **15 Python editor tests
with sanitized binaries**. All four Linux Tk workflows pass. Linux and Windows
SDL each pass seven vehicle/map/inspection/combat/depot F5/F9 checks against
headless state and full-frame pixels. Native Windows Tk remains unverified.
The strict reference guard reports only the addition of
`vscode-merge-base = origin/main` in `UnBattletech/.git/config` and the associated
Git directory/config timestamps; removing that line in memory reproduces the
baseline hash. All original assets and reference research/source files match.
The reference directories and baseline were not edited to conceal this metadata
difference. See [verification details](TESTING.md#world-art-vehicles-and-planets).

[Visual editor improvements](EDITOR_GRAPHICS_AND_DRAGGING.md) add real CHI tile
previews and thumbnails, a full-sheet graphic picker, drag-and-drop markers and
a refreshed desktop layout. Every drag is one undo step. The editor decodes
supplied art in memory through the gameplay palette and adds no original art
to custom packages. Full native **69/69**, Python **88/88**, focused Wine and
sanitizer checks, and all three Linux Tk workflows pass. Windows atlas output
matches Linux; native Windows Tk interaction remains unverified.

[Authored walking](AUTHORED_WALKING.md) now keeps all active mechs/infantry in
the original compact formation, tests entrances against each member's ground
position and preserves one gait increment per 1/2/4-step key. It removes the
generated-world water test from custom-scene followers and fixes stale mounted
positions in the asset-free renderer. Existing demo package fingerprints and
saves are retained. The full native suite passes **69/69** and Python **69/69**;
the linked evidence records focused Windows/sanitizer and real-input SDL checks.

The main authored play demo is now **[BattleTech: Last Beacon](BATTLETECH_DEMO.md)**:
three maps, nine mech variants and ten vehicles, a Phoenix Hawk/Trebuchet starting team,
two mercenary contracts, recruitment, trading and two endings, using supplied
original graphics/sounds and Enhanced combat. Authored character names now work
through the CHI renderer's menus and combat text. Run
`sh scripts/play-battletech-demo.sh`. The independent asset-free example remains
an editor template. Tile palettes, stamps and pixel editing are now implemented;
authored repair/reload/salvage services and richer event authoring are next.

Editor-roadmap tasks 1–5 now provide a shared authoring contract, validator,
31-model export, 256-model project catalogue, per-mount weapon definitions and
an explicit CHI-dependent project loader with strict package saves. See
[implementation, commands and limits](M5_AUTHORING_PROJECTS.md). This is the M5b
foundation plus authored maps/events and saved command continuations. The
desktop GUI now edits rosters, maps and events, validates, saves, exports and
launches these projects. See
[maps/events/editor](M5_MAPS_EVENTS_EDITOR.md) for the playable Frontier example,
commands, tests and limits, and the
[independent game/editor guide](M5_INDEPENDENT_GAME_EDITOR.md) for Last Beacon,
which uses its own assets/font/sounds and a bounded Lua command route without
original files or caches. The first useful editor is implemented within those
bounds; richer scripting and packaging remain future work. Pixel/frame and
multi-planet world authoring are now implemented as described above.
The original campaign remains playable.

The independent C11/SDL2 port has playable implementations of the authorized
M4a–M4e increments and the subsequent building, theft, encounter, recruitment and
presentation requests. A recorded 75,573-input route now starts with a new cadet
and reaches the cache ending through the actual training, companion, disk and
password prerequisites. It uses the authorized money shortcut. M4 as a complete
reproduction of every original campaign branch remains unfinished.

See [M4 evidence](M4_PROGRESS.md), [follow-up evidence](M4_FOLLOWUPS_EVIDENCE.md)
and [current fidelity work](M4_FIDELITY_EVIDENCE.md)
the [earlier acceptance sweep](M4_ACCEPTANCE_SWEEP.md)
the [previous completion sweep](M4_COMPLETION_SWEEP.md)
and the [latest cadence and portability sweep](M4_PORTABILITY_SWEEP.md)
for original routines, explicit prerequisites and confidence limits. README
credits the reverse-engineering contributors and explicitly discloses AI use
with **OpenAI Sol 6.1 and Astra**. The independent code and documentation are
GPL-3.0-only; the original game's source code is not used, and its assets are
not distributed. Runners must supply their own original files.
Reference directories are immutable; original assets and emulator RAM stay in
ignored work files. Local commits remain on `main`, with no push.

The latest [combat pacing correction](COMBAT_PACING.md) removes the misplaced
speed pause between movement steps and applies it after each attack, matching
48 complete original-wave observations. Graphics-off skips hidden animation
waits, and speed 5 holds attacks rather than movement. The controlled default
movement-only wave falls from 3.904 s to 0.384 s; this is a native comparison,
not a claim of cycle-exact XT timing. Save formats and numeric rules are unchanged.
The following [weapon/fire presentation audit](WEAPON_PRESENTATION.md) adds
2,400 original weapon sequences and 720 fire/debris redraw observations, fixes
sound/pose order and trajectory/impact rendering, and makes flames follow map
redraws. Fire and wrecks remain visible outdoors. That increment wrote v44, with
older held presentation/PCM support. All **63 native suites**, **32 Python
tests**, seven focused sanitizer/Wine suites per platform and five SDL
effect/fire F5/F9 scenarios per platform pass in their recorded bounds.
The [movement/LRM implementation](MECH_MOVEMENT_AND_LRM_AI.md) preserves those
1,872 movement-budget cases and implements LRM1–LRM5: explicit saved profiles,
LRM minimum-range penalties, usable-loadout positioning, sustainable volleys
and live firing decisions. Fresh Updated campaigns default to Enhanced;
existing Updated/imported saves remain Legacy until changed outside combat.
Original retains its rules and planner. Enhanced uses BTPj/v45 inside BTU2,
with a semantic combat fingerprint; ordinary Legacy/Original states remain
v44. A missing optional rules file selects Legacy for a new pack.
The deterministic planner is local C code, with no model calls. The
[release verification record](TESTING.md#updated-combat-release) covers the
full regression suite, seeded comparisons, Windows, sanitizers and SDL saves.

## Milestones

| Gate | Bounded result |
|---|---|
| M0 | Original inventory/runtime/research audit and C11/SDL2 decision |
| M1 | Independent native MAP1 exploration and collision |
| M2a–M2d | Citadel/Hall/Katrina, NPC travel and original dialogue |
| M2e–M2h | Weapons/armour, ComStar, saved continuations and paid classes |
| M2i–M2m | Original sprites, lounge, diagonals, first two missions/rest and animations |
| M3a–M3c | Weapons/Kick, walk/run/jump, six training assignments, Rick/device, paths/electricity and live combat |
| M3d–M3h | Invasion, destroyed Citadel, generated world, Starport, Rex, party/technician services and original music |
| M4a | Encounter aftermath, cash/salvage, ejection and character-loss comparisons |
| M4b | Formations, allocation, transfers, field healing and technician effects |
| M4c | Hospital/jail companions and treatment; hut, cinema, laser shop, house and two theft routes |
| M4d | Original cache puzzle/ending from GAME1, including eleven doors and MAP15 |
| M4e | Six original-save imports/exports, six internal slots, original intro/menu/inspection/map, sequential sound and outtakes |
| Owner follow-ups | Four Jenners/ruins escape, purchase recipients, armour repair, original crew/inspection/engagement/Speed Shop selectors, world seed/city alignment, all-party collision and gait, replacement recruits and spy confrontation |
| Fresh campaign | New-cadet input route through training, companions, paid apprenticeships, holodisk, password and cache ending; original checks at selected prerequisites |
| Remaining original campaign | Additional branches and broader DOS combat/presentation parity |
| M5 | Preparation, Updated roster, definitions/projects, authored maps/events, independent miniature game, bounded Lua and first roster/map/event editor implemented; rich authoring remains in the [plan](ENGINE_AND_EDITOR_PLAN.md) |
| Updated LRM1–LRM5 | Saved Enhanced/Legacy profiles, LRM minimum range, weapon-aware positioning and volleys, live firing checks and release verification |

The owner-requested [engine and editor plan](ENGINE_AND_EDITOR_PLAN.md) records
the future authoring direction separately from the remaining original fidelity
work. [M5-P1–P5 are implemented](M5_PREPARATION.md): shared content ownership,
named unit/weapon/presentation/refit lookups, original action dispatch, isolated
persistence and an offline schema/sample. That preparation preserved BTPe/v40
saves; its 41 Windows SDL and eleven Linux Mech-It checks remain recorded in
the preparation evidence. Current authoring verification is recorded in the
[maps/events guide](M5_MAPS_EVENTS_EDITOR.md#verification).
The [M5a CHI roster slice](M5A_ROSTER_SLICE.md) now supplies the pre-logo
Original/Updated selector and 31 playable external models/variants, with broker,
encounter and save support. The early general-schema sample remains an offline
prototype; current project schemas are consumed by the shared C loader. M5a,
M5b's independent miniature game and the first M5c roster/map/event GUI are
implemented. Richer events and scripting tools remain **proposed**; the current
world/art and vehicle guides describe the implemented asset/animation tools.
The broker occupies an unused Starport building, offers buying/selling with
four owned bays, and groups stock into Light, Medium, Heavy and Assault classes,
sorted by tonnage/name with eight-row scrolling. Inspection bars fit their
original wells even for assault models. Pack 0.4.0 adds Ostsol OTL-4D, Javelin
JVN-10N, Cicada CDA-2A, Clint CLNT-2-3T, Hermes II HER-2S, Whitworth WTH-1,
UrbanMech UM-R60 and Ostroc OSR-2C. All 23 previous definitions are unchanged.
The 0.1.0, 0.2.0 and 0.3.0 saves load automatically, including held/scrolled
broker menus and confirmations. Ordinary Legacy/Original states still use v44;
Enhanced and the settings pages use v45; held category menus use v46. Edition envelopes and
slot namespaces remain separate.
The [pack guide](../content/updated/README.md) records source statistics,
temporary sprites, authored prices and adaptation limits. The original story
LAM and training Jenners retain their original definitions.
The [five editor tasks](ENGINE_AND_EDITOR_PLAN.md#13-next-five-tasks-toward-an-editor)
now have all five bounded steps implemented. Their gates and remaining limits
are recorded in the independent game/editor guide.
The broker now has [new AI-generated artwork](../content/updated/art/README.md)
and the other buildings' description/compact-choice layout. The selected male
salesman master, final prompt, exact 88×88 preview and ANM are included, along
with a reproducible converter. Ten further static illustrations cover the
Training Center, lounge, prison, inventor's hut, cinema, hospital, ComStar,
clothes shop, Video Hut and mayor's house.
Optional pack-local art does not change roster fingerprints or saves; older
packs retain each original presentation. Explicit BLD animations and held
frames take priority. General custom-building manifests and animated new
portraits remain future work.
The preceding roster/art checks passed native **60/60**, Python **32/32**, and five focused
sanitizer and Windows suites each. Linux and Windows SDL each pass **34/34** selector/trading
scenarios and **10/10** building visits, exact portrait crops, F5/F9 and full-frame
restore. Actual building screens were visually reviewed; all pixels
outside the new portraits and the original script continuations are compared.
Missing/malformed-art behavior, cinema scene priority and the training quiz
are also covered. See the [recorded evidence](M5A_ROSTER_SLICE.md).
At the owner's request, a commented **temporary** formation recovery now applies
in both editions after scene/menu exits and excessive separation. It keeps
parked/wrecked mechs inactive. Its removal TODO targets the underlying follower
route search; it is explicitly a gameplay workaround, not DOS parity evidence.
The [inventory](CONTENT_INVENTORY.md) records the
remaining compiled assumptions and concrete independent-game prerequisites.

## Play and verify

```sh
./scripts/build.sh
./build/btech-port --data "Original DOS"
./build/btech-port --load "Original DOS/GAME3"
./scripts/test.sh
./scripts/test-sanitize.sh
python3 tools/native_smoke.py --m4-acceptance
python3 tools/native_smoke.py --followups-only
```

Arrows/keypad move and select; two perpendicular arrows move diagonally.
Enter or Space confirms. Space outdoors opens party/settings/save/map actions;
Space also selects highlighted menu entries. F4 opens the explored overhead
map, F5/F9 save/load the selected slot, and F3 toggles diagnostics. Escape
declines or clears an amount; Ctrl+Shift+Escape closes. Holding Shift while
pressing K, Y, R adds 10,000 credits, including in the intro.

The Infocom/Westwood screen precedes the title/music and played-before question.
Yes opens saves; No starts training. Original GAME saves can be imported, and
an imported save can be exported outdoors with `--export-original work/GAME3`.
Six internal slots preserve active menus, animation/audio, combat and theft
state. `--save-file FILE` changes their base name. Failed loads preserve play.

The garage opens the original crew allocator during checkout. Jason can occupy
any assigned mech bay. Random encounters describe the attacking force and ask
whether to engage. No consumes the original RNG draw: three of four low-bit
outcomes evade; failure shows the original notice before combat settings.
Successful pre-combat evasion produces no loot or cash.

## Verification and limits

The current build has **57 CTest suites**, passing on Linux, under
ASan/UBSan/LeakSanitizer and under Windows/Wine. The content-lifetime suite now
has 100 checks. Nineteen Python tool tests pass, including fourteen new authoring
cases. The P2–P4 fresh-campaign, spy-replacement and service routes match a
retained pre-refactor player at every canonical trace record and in final
save/frame bytes. See [preparation verification](M5_PREPARATION.md) for scope,
commands and interactive checks.
The earlier fidelity sweep established:

- **133 original combat waves** in four town contexts, including two complete
  MAP4 victories and two Starport traces bounded at 64 waves each. Two MAP4
  initial formations also match. This corrected enemy infantry avoidance and
  heat accounting on the winning wave.
- **384 complete salvage loops / 552 held pages**, comparing retry order,
  records, RNG, text and every pixel of each 200-by-72 text interior.
- **10,512 collision/doorway decisions**, covering all 13 towns, 84 doorways,
  eight directions and three party configurations. The cache corpus now has
  **534 original cases**, plus saved entry/exit with one through eight people
  and recovery of demonstrably invalid older follower positions.
- **928 original clothing/electronics visits**, a static audit of all 26 BLD
  control graphs and a 769-input ordinary service route. Static graph coverage
  does not establish execution of every story branch.
- **256 original brief/verbose combat reports**, including all pixels in the
  88-by-88 upper-left text area. A live original Phoenix LAM capture matches
  all **64,000 RGB pixels**.

The previous five-area sweep added eight complete outdoor/arena/prison
encounters (24 waves), 384 death/ejection report cases (256 pixel comparisons),
three complete live salvage result panels, 5,760 cache formation/contact cases,
2,400 saved formation steps and 124 complete inventor/house/theatre branches.
Seventeen theatre film/text panels now match the original scrolling text engine,
fixing overflow near the end. Sixty-six animation executions and all six combat
speed settings expose and correct missing opening holds and overly fast tactical
steps. The latest sweep corrects outdoor cadence to eleven nominal VGA retraces,
with immediate keyboard updates and saved fractional phases. It adds four
complete Starport/MAP4 victories (20 waves), twelve quiet-ejection pixel cases,
2,582 viewport visibility cases, 768 continuous original cache movement inputs,
and expands the HUT/MAYOR/THEATER corpus to 248 branches. A newly observed
original enemy-kick/map-memory interaction is now reproduced.

Computer assigns only the selected unit and leaves the menu open. Next Mech
allows separate assignments; Begin Fight starts the wave. Space stops continuous
play after the current wave while retaining assignments. Manual movement or
weapon editing returns the selected actor to manual control. Original command
loop comparisons and saved/native input checks cover this distinction.
Space selects on all held combat menus, including movement destinations and
replace-order prompts; during a running wave or outtake it interrupts instead.

The fresh ending and **58,886-input** spy/replacement routes restore and continue
before every input. The new native service tail joins the existing house,
cinema, hut, laser shop, theft and replacement checks. Nineteen held combat pages
exercise F5/F9; the cache check includes the Phoenix display, map room and ending.
Current verification and exact timings are recorded in [TESTING.md](TESTING.md).
That sweep passed all 56 Linux, sanitizer and Windows/Wine suites, along with five Python
tests and 41 Windows SDL checks (including 19 held combat F5/F9 pages).
The Windows build is checked under isolated Wine against Linux state/pixels;
physical Windows hardware and an actual XT speaker recording remain untested.

**VERIFIED in these bounds:** numeric rules, resource interpretation, original
BLD branches, compared text/pixels and saved/native continuations.
**APPROXIMATE:** DOS busy-loop cadence, broader encounter AI/initiative, some
layouts and exact DOS recovery of irregular saved follower paths. NPC idle updates now average eleven nominal 70 Hz retraces; host scheduling
and exact hardware clock rates remain approximate. Animation retrace
requests match within the 32 ms native tick. Combat speed waits now occur after
attacks, with movement and graphics-off waits checked by the
[pacing audit](COMBAT_PACING.md). Weapon poses, trajectories, impact positions,
sound order and explicit retrace requests have the subsequent
[presentation audit](WEAPON_PRESENTATION.md); CPU-dependent drawing time
remains approximate. Audio
uses original effect programs and a nominal 8 MHz 8088 timing model; physical speaker response and
exact hardware calibration remain **UNKNOWN** without a reference recording.

New random encounters cannot place enemies in disconnected areas behind town
walls. Infantry uses the correct ground sample, and enemy mechs cannot spawn
inside Starport even when the party is outside. **Owner-requested correction:**
the reachability guard extends the original terrain-only scan; it is not claimed
as original behavior. Twenty-five bounded original placement observations record
that distinction. If no candidate can be placed, exploration continues. Existing
saved fights retain their already placed units; arena/story fights are separate.

Ordinary Legacy/Original saves are **BTPi/v44**, with a 20,480-byte payload inside the Original
BTS1 or Updated BTU1 length/CRC envelope. Older v40-v43 held effects retain
their stage meanings; new queues use the verified presentation sequence.
Enhanced and held combat-rule settings use BTPj/v45 in BTU2, with saved policy
and a semantic rules fingerprint. The payload size remains 20,480 bytes.
The discovery marker and held spy confrontation are saved.
Salvage inspection history and queued/held battle reports persist too, retaining
actor names and results before later attacks change their records. v39 adds
casualty flags; v38 reports migrate without inventing death notices. v40 adds
fractional outdoor clocks and retained quiet-mode headers/ejection cursors.
Earlier clock phases migrate without changing RNG; missing old headers cannot
be reconstructed.
Current local caches are **BTTA/v24** (373 strings), BTCC/v12 and BTW3; the world seed is the
original startup value `0x020304`, rather than the former research seed.
Older saves migrate their represented fields; absent direction/exploration
history cannot be reconstructed. Old ambiguous decorative wreck/fire marks
are cleared on migration; v34 stores their actual world sectors. Build and play need no emulator. Optional
oracle tools execute bounded original instructions and commit numeric results
and source hashes only.

## Remaining original-fidelity tasks

The authorized cadence/encounter/quiet-text/cache/Windows sweep is complete
within [its documented bounds](M4_PORTABILITY_SWEEP.md). Proposed follow-ups:

1. Check the Windows build on actual Windows hardware, including keyboard
   layouts, physical audio output and a distributable executable-only package.
2. Compare complete combat frames and projectile/beam timing, extending the
   now-verified text interiors and viewport visibility rules.
3. Compare additional complete encounters in other towns and with different
   equipment, including mixed-party defeats and ejections.
4. Execute the remaining service/story branches identified by the 26-BLD audit;
   static graph coverage is not execution coverage.
5. Extend continuous original cache comparisons through terminal and door
   interactions with multiple party members, beyond the floor-only path corpus.

Physical 8 MHz XT speaker calibration also needs an appropriate recording.

The separate authoring direction next proceeds to richer commands/scripts and
asset/animation tools, as defined in the
[engine/editor plan](ENGINE_AND_EDITOR_PLAN.md). Authored feature completion
does not imply that these original-fidelity tasks are complete.
