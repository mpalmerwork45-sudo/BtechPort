# Editable CHI import progress

Authorization: C1/C2 first pass, followed by C3, 2026-10-23. See the
[milestone plan](CHI_EDITABLE_CAMPAIGNS_PLAN.md) and [contracts](CHI_IMPORT_CONTRACT.md).

## C1 — Audit and contracts

**Implemented structural audit.** `tools/chi_audit.py` generates the committed
numeric/fingerprint inventory: 77 supported source files, 76 resource copies,
26 BLDs, 1,816 reachable instructions, all native actions 1–47 with their script
contexts, maximum script 8,499 bytes and maximum 12 populated entrances. Native
capability sizes and dependency/editability dispositions are recorded in the
contracts. Existing Original/Updated save and resource paths are retained.

**Preservation baseline:** private `work/chi-import/baseline.json` records HEAD
and hashes of the three pending Last Beacon files. Reference guard verifies
1,287 entries unchanged in content/mode/mtime against
`work/reference-before-map-construction.json`.

**Provenance:** 20 original-derived Last Beacon tile images existed in the C1
baseline. C2 replaces only their public baseline payloads with placeholders.
Seventeen had custom pixel edits; recipes restore original bases, and the exact
derivatives remain private. The three dirty owner files are unchanged. No history rewrite.
Generated CHI projects remain local; typed assets, caches and native dialogue
remain original-derived through edits. Detection limits are explicit.

**C1 gate:** contracts resolve C2 loading/profile/identity, resource budgets,
state preservation, initial edit surface and transaction behavior. Full map and
BLD/native authoring remains C3/C4 with concrete owners/verification. Static audit
is VERIFIED; re-verifying every original branch is not claimed.

## C2 — Importer and first slice

**Resource/import foundations implemented.** The opt-in project extension owns
79 runtime files; the validator hashes and decodes the same bounded snapshots.
Original/Updated features are explicit. Original retains an empty additions
container and exact cache templates; Updated exports its current definitions/art.
The shared headless importer checks all 77 fingerprints, stages both projects
and publishes their new parent without replacement. Completed projects run with
every external resource path absent. Native text overrides participate in the
ordinary document history, strict fingerprint, source conversion and build.

**Verified:** the two imports match their built-in editions for 108,156 total
gameplay ticks across ordinary training/combat and mission pass/fail fixtures,
including rendered checkpoints and held-script save/reload. Twelve slot
round-trips pass with cross-profile/normal-save rejection. Four affected native
regression tests pass. Private evidence: `work/chi-import/parity-linux.log`,
`native-focused.log`, `first-import.json`; Linux build uses `/usr/bin` tools to
avoid the development host's older Conda linker.

**C2 gate passed.** The launcher/editor import view creates both projects with
progress/cancel and Edit/Play actions. Project → CHI campaign edits native text
through shared validation/history. The real Linux GUI journey passes import,
text edit, Undo/Redo, Save/reopen, native Play without external original paths,
Stop and cancellation. Public export rejects imported resources, caches,
declared unknown/original-derived text and artwork lacking an exclusion recipe.
Application packaging uses indexed project snapshots, excluding private
uncommitted art. All nine packaged examples pass the payload checks.
Completed GUI imports persist both launcher registrations. Native multiline/CR
and colour markers 6/15 have a dedicated JSON reader mode, leaving existing
authoring formats strict; native decoded bytes and popup pixels are checked.

**Final verification:** 383 Python tests and 91 Linux native tests pass. The
same 108,156-tick comparison and twelve project slots pass under Wine. Five
affected Windows regression tests pass. For the retained 6,637-action combat
route, both profiles produce identical Linux/Windows JSON state, save bytes and
frames (`work/chi-import/cross-platform.json`). Intro logo/title/question pixels
and state are also compared in the native parity helper.

Negative checks cover occupied destinations, symlinks, bad fingerprints,
source changes, cancellation after the first profile, publication races,
reimport identity, malformed text/unknown fields, resource edits invalidating
saves and removed provenance metadata. Source conversion/build and private
tile reconstruction/cache-conflict checks pass. Twenty observed normal save
files predate the C1 baseline; their hashes/mtimes are retained for final
preservation checking alongside the two reference trees and three user files.

Implementation commits: C1 `63b9b41`; C2 resource/runtime foundation `7a10e83`;
GUI and provenance boundary `293cc4d`. Final verification and usage are recorded
here and in the [instructions](CHI_IMPORT.md).
Completion/setup commit: `a4d8981`. A freshly packaged Linux kit imports both
profiles with its bundled Python and plays them with its bundled native runner
from a directory without original files/caches. Its nine example projects and
2,398 observed files contain no recognized original payloads or cache headers;
see `work/chi-import/packaged-verification.json`. Runtime-generated Python
bytecode is included in that observed count, not the build's original inventory.
Final Linux/Wine parity reruns pass (`parity-final-linux.log` and
`parity-final-windows.log`). Windows also passes the empty-added-roster settings
save and exact multiline/colour-byte proof. All three owner files and twenty
observed normal saves retain their recorded bytes/mtimes; both reference trees
retain all 1,287 recorded content/mode/mtime entries.

**Limits:** native Windows Python/Tk remains UNKNOWN. Full campaign branches,
all-seed world equivalence, complete BLD/service/mission authoring and general
asset-free edited-campaign recipes remain C3–C5. Current code preserves inherited
compatibility behavior; it does not establish complete DOS parity. No old
normal-game save migration is provided. Partial extraction resumes by retrying
into a new destination. No full editable-campaign claim is made.

## C3 — Spatial and presentation authoring

The native adapter now reads versioned `chi-spatial.json` and optional
`chi-presentation.json`. It retains the original generator and BLD interpreter.
All 15 maps, their native header bytes, room/door slots, NPC routes, four tile
banks, terrain join pieces, generator tables and seed have a shared editable
model. Map artwork and collision are separate; custom world handles retain
16 bits. Native maps use the regular painting, construction, pattern, pixel and
jigsaw tools through a reversible projection, never an authored-event startup.

Resource copies use the game decoder on the current unsaved project. Sprite,
screen, font, film and building portrait overrides reach native playback; film
timing and verified sound-program references are editable. Updated's virtual
broker entrance can move, be renamed or disabled. Clones and library dependencies
retain original-derived provenance. Modular sources include the new formats.

**VERIFIED:** all 15 native map structures/cells and graphics-bank centre/edge
crops match the built-in resource path. All 1,048,576 world terrain cells match
for seeds `0x020304`, `1` and `0xabcdef`, before/after invasion, in both profiles
on Linux and Wine. Depth crossing is separately sampled every 16 half-steps,
not exhaustively at every possible step. Generator state/tables match. These
are differential checks against the built-in port generator, not new DOS runs
for every seed. The full C2 comparison still passes: 108,156 gameplay ticks,
RNG/script state/rendered checkpoints, intro screens and twelve isolated slots.

Fifteen retained edits pass native checks on Linux and Wine: blocked ground,
door movement, NPC routes, a moved town/Citadel/starport, broker placement, a
custom 16-bit jigsaw, sprite/film/title/portrait/font/audio changes and force-field
animation. Each example is validated, Undo/Redo checked and saved/reopened.
An edited startup film survives a real training-route held save, with identical
Linux/Windows save bytes. A moved Citadel completes all 44,192 local gameplay/RNG
ticks of that fixture. World review generates a real moved-town crop; protected
regions detect generator, exact native rule and sheet-pixel changes.

**C3 gate passed.** The real Linux GUI journey passes normal map painting,
Undo/Redo, all maps/four banks, moved-town preview, jigsaw drawing, native sprite
editing, Save/reopen and Play with external DOS paths absent. The existing
import/dialogue/cancel journey still passes. **400 Python tests, 91 Linux native
tests and all 91 Windows native tests under isolated Wine pass.** Builds are
sequential with two jobs; native Windows Python/Tk remains UNKNOWN.

Private evidence: `work/chi-import/c3-evidence-final/evidence.json`,
`c3-windows-evidence.json`, `c3-python-regression.log`, `c3-native-regression.log`,
`c3-native-windows.log`, `c3-parity-final-linux.log`, the two
`c3-spatial-final-*-linux.log` files and `work/chi-spatial-gui.json`.
Generate fresh editable examples using `tools/chi_spatial_evidence.py` into a
new ignored folder. No decoded maps, text, art, caches or saves are committed.
Both reference trees retain 1,287 content/mode/mtime entries, the three dirty
owner files retain their exact hashes and all 20 observed normal saves retain
their bytes/mtimes. Existing registered C2 projects are not silently upgraded.

Native limits remain explicit: one 1,024-square world, 15 map slots, 16 entrance
slots, eight route slots and 64-tile town origin alignment. Citadel/starport and
cache interior dimensions preserve their native service contracts. A town clone
replaces terrain in a chosen existing slot. New unrestricted story/mission state
and authored event execution remain C4. Native sheet/sprite replacement pixels
use their selected 16-colour palette; owned map artwork retains full RGBA.

Enabling C3 map support on an older import changes its strict content fingerprint;
retain the old project/revision for its old imported saves. Ordinary games/saves
are separate. C4 is next: BLD source/control flow, native service and mission
definitions, recruitment and saved continuations. General edited-campaign
reconstruction recipes and complete campaign acceptance remain C5.

## C4.1 — Labelled BLD sources and compiler

**C4.1 gate passed, 2026-10-24.** All 26 native programs have typed labelled
source, original/source/compiled locations and a two-pass native compiler.
Unreachable byte ranges remain explicit immutable data. Both imports reproduce
all 52 encrypted BLD files exactly. Runtime compilation uses the same validator;
the original `chi/*.BLD` files remain immutable baselines. Compiler contract,
source and actual compiled payloads participate in strict save identity.

The Construction Kit's **Project → CHI scripts** view edits dialogue,
conditions, assignments, branches, native menu destinations and supported
compatibility actions. It includes readable operation names, original/current
offsets, source locations, insertion/cloning, draft recovery, compiler problem
navigation and shared Undo/Save/Play. The CLI exposes the same commands and
program-level scopes. Modular sources split programs into owned files. Existing
imports can enable source as one Undoable edit; their old saves require their
old content revision. Registered C2 projects are deliberately left unchanged.

**VERIFIED:** Linux and Windows/Wine each pass 214,544 edited-program
gameplay/RNG ticks across both profiles: funded class, bank, training combat,
ordinary services and alternate services. Comparisons normalize only expected
text spans and relocated byte addresses; the remaining encoded gameplay state
must match. Held saves exercise class, bank, menu, checkpoint and mid-invasion
continuations. All eleven final Linux/Windows save pairs are byte-identical.
The invasion proof also exposed and fixed script ownership: the active training
program remains selected when the visible Citadel switches to its ruined map.

A separate real armour-shop entry proves all five required edits: dialogue,
condition, jump, menu choice and native action. Both platforms reload the
waiting text/menu continuations and reject that save against the other content
revision. The unchanged C2 comparison passes again on Linux and Wine: 108,156
ticks, rendered checkpoints, native state/RNG, intro screens and twelve isolated
slots. These are comparisons against the built-in port, plus byte identity
against private original BLD files; they do not establish every DOS branch.

**410 Python tests, 92 Linux native tests and all 92 Windows native tests under
isolated Wine pass.** The Linux GUI journey passes typed edits, Undo/Redo,
invalid operand/menu rollback, draft recovery, source-label navigation,
Save/reopen and native Play without external resource paths. Builds pass with
two jobs and no warnings. Native Windows Python/Tk remains UNKNOWN.

Private evidence: `work/chi-import/c41-evidence-final/evidence.json`,
`linux-final.json`, `windows-final.json`, `cross-platform-held-saves.json` and
`parity-final.json`; regression logs use `work/chi-import/c41-*`. The GUI report
is `work/chi-bld-gui.json` and capture `work/chi-bld-editor.png`. Regenerate
examples with `tools/chi_bld_evidence.py` into a new ignored directory. Foundation
implementation is committed as `d624edd`; the following commit records editor
and command integration with the completed verification ledger.

Both reference trees retain all 1,287 recorded content/mode/mtime entries. All
three pending owner files and twenty normal saves retain their recorded values.
No extracted scripts, dialogue, art, caches, campaigns or saved proofs are
committed. Native actions/films remain limited to combinations observed in each
baseline program, with specialized class/training anchors preserved. Original
records cannot be deleted; redirect around them. Calls/recursion and arbitrary
authored-event execution remain unsupported. C4.2 service content is next;
C4.3–C4.5 and C5 remain open. See [authoring usage](BLD_AUTHORING.md).

## C4.2 — Native service content and context registry

**C4.2 gate passed, 2026-10-24.** The native service catalogue exposes 156 typed
parameters and 47 named F5 operations, including all 76 observed action/building
pairs. Entries describe requirements, outputs, mutations, yields, errors and
implementation owners. Recruitment's separate E9 instruction retains its
existing context/skill checks. These are retained port contracts, not new DOS
execution evidence for every possible edited combination.

Service content covers personal equipment prices/stock/weapon IDs, repairs,
refits and ammunition costs; hospital fees/programs/messages/cooldown; classes,
apprenticeships, recruitment and spy rules; theft timers/attempts/rewards,
garage/crew policies; broker stock/resale; Comstar market/allowance parameters;
and other building costs/gifts/effects. Existing menus, partial repairs, recipient
swaps, spy replacement and once-only transactions stay in their native routines.
Market parameters reach both cadet and later-world clock callers.

Unmodified original price text and BLD funds/payment operands gain explicit
service references when enabling support. Existing custom dialogue is preserved.
All 52 unedited encrypted BLDs remain byte-identical. Sources, effective compiled
payloads and service contract participate in strict save identity. Class/prison
validators use current prices/limits without changing the serialized game state.

**VERIFIED:** five replay fixtures per edition match the prior C4.1 imports for
214,544 gameplay/RNG ticks on Linux and Windows/Wine. The unchanged built-in
comparison passes again for 108,156 combined ticks, rendered checkpoints, state,
RNG, original presentation and twelve isolated save slots on each platform.
Edited class routes cover 6,176 combined ticks. Separate real-doorway fixtures
prove a changed armour price with recipient selection, a changed hospital fee/
cooldown and prison theft with a longer timer, first-attempt success and changed
reward. A prison save at tick 85 reloads with a configured 100-tick guard timer,
where the old 80-tick validator rejects it. Healing and purchase acknowledgements
do not repeat charges/effects. All eighteen Linux/Windows held-save pairs match
byte-for-byte. Controlled mechanics checks also exercise partial repair costs,
recruitment limits/ranks, broker filtering and the later-world market caller.

**418 Python tests and all 93 Linux native tests pass.** The full 93-case Windows
suite passes under isolated Wine; ten focused cases pass after final bounds and
world-market caller adjustments. Sequential two-job builds have no warnings.
The Linux service GUI journey passes typed costs and stock, action browsing,
Undo/Redo, invalid-draft rollback/recovery and navigation, Save of pending fields,
reopen and native Play without external originals. The existing BLD GUI journey
passes again. Native Windows Python/Tk remains UNKNOWN.

Private evidence is `work/chi-import/c42-evidence-final5/evidence.json`,
`windows-evidence.json`, `paired-saves.json` and `parity.json`. Regression/build
logs use `work/chi-import/c42-*`; the full Windows log is
`c42-native-windows.log` and final focused log `c42-native-windows-followup.log`.
GUI report/capture: `work/chi-services-gui.json`, `work/chi-service-editor.png`.
The evidence generator requires a new ignored destination and a retained prior
import pair. Foundation commit: `34e8d0e`; the following commit records editor
and command integration with the completed verification ledger.

Both reference trees retain all 1,287 content/mode/mtime entries, the three
pending owner files keep their hashes and twenty observed normal saves keep
their hashes/mtimes. Registered projects are not automatically upgraded. No
decoded text, source programs, art, caches, campaigns or saved proofs are
committed. Old imported saves require their previous content revision.

Native menu sizes, refit recipes, identity and party/bay limits remain explicit.
Mission opponents/spawns, yard combat layouts and broader campaign settings are
C4.3; general event bridging is C4.4 and complete campaign coverage is C4.5/C5.
Custom literal prices and remapped equipment descriptions remain the author's
responsibility. See [service usage](CHI_SERVICE_AUTHORING.md).
