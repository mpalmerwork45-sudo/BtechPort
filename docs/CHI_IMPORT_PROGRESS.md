# Editable CHI import progress

Authorization: C1 and C2 first pass, 2026-10-23. See the
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

## C3 — Spatial and presentation authoring (verification in progress)

The native adapter now reads versioned `chi-spatial.json` and optional
`chi-presentation.json`. It retains the original generator and BLD interpreter.
All 15 maps, their native header bytes, room/door slots, NPC routes, four tile
banks, terrain join pieces, generator tables and seed have a shared editable
model. Map artwork and collision are separate; custom world handles retain
16 bits. Native maps use the regular painting, construction, pattern, pixel and
jigsaw tools through a reversible projection, never an authored-event startup.

Resource copies use the game decoder on the current unsaved project. Sprite,
screen, font and film overrides reach native playback; film timing and verified
sound-program references are editable. Clones and library dependencies retain
original-derived provenance. Modular campaign sources include the new formats.

Initial Linux evidence: all 15 maps and their graphics-bank edge crops match;
all 1,048,576 world cells and depth joins match for seeds `0x020304`, `1` and
`0xabcdef`, before/after invasion. The 108,156-tick C2 parity routes passed
after initial map integration. The real GUI journey passes native map painting,
Undo/Redo, moved town preview, jigsaw editing, native sprite editing, Save/reopen
and Play without an external DOS installation. Final regression, cross-platform
and edited-path checks are still being completed; this is not the C3 gate yet.

Native limits remain explicit: one 1,024-square world, 15 map slots, 16 entrance
slots, eight route slots and 64-tile town origin alignment. Citadel/starport and
cache interior dimensions preserve their native service contracts. A town clone
replaces terrain in a chosen existing slot. New unrestricted story/mission state
and authored event execution remain C4. Native sheet/sprite replacement pixels
use their selected 16-colour palette; owned map artwork retains full RGBA.
