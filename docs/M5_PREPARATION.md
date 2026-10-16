# M5 preparation — preserving the playable original

**2026-10-16: P1–P5 implemented and verified within the bounds below.**
These are the five bounded increments in the
[engine/editor plan](ENGINE_AND_EDITOR_PLAN.md). P1 was previously completed;
the four subsequent increments were authorized together. Existing rules,
controls, resources, cache versions and BTPe/v40 saves remain the compatibility
case. Runtime custom units, Lua and an editor are later work.

## P1 — Shared content ownership

[content.h](../port/data/content.h) defines the owned `BtpContent` context and
explicit original resource/cache paths. [content.c](../port/data/content.c)
loads in the established order and publishes only a complete result. Failed
loads free their partial allocation and preserve existing loaded content.
Closing releases the resources and clears identity; closing again is safe.

The context identifies the original DOS 1.03 profile outside `BtpState`, so no
pointer/profile field enters saves. Large resources stay on the heap. Contexts
must not be copied; borrowed pointers expire on replacement/close. Replacement
is a session-boundary operation, not live battle hot reload.

Both players use [cli.c](../port/frontend/cli.c) for this loading/cleanup path.
No new runtime dependency or manifest is required. `BtpResources` still models
original formats; the boundary itself does not load arbitrary packages.

## P2 — Unit lookups

[unit_data.h](../port/data/unit_data.h) centralizes original template selection,
weapon fields, base movement values, sprite selection and refit recipes.
Combat, campaign/training/yard setup, services and inspection use these named
lookups. The [content inventory](CONTENT_INVENTORY.md) records ownership,
original identity mapping and raw record assumptions that remain.

Original templates and live records remain authoritative. The eight refit
recipes preserve their exact writes/copy sources; sprite selection preserves
the different original owned/enemy tag mappings. Catalogue definition identity
is distinct from a party slot, while live custom definition IDs still need M5a.
Capacities, gameplay and saved bytes have not been widened.

## P3 — Original story dispatch and reusable operations

[original_actions.c](../port/core/original_actions.c) owns original native
service dispatch, held native input and transaction checkpoints. It preserves
BLD bytes, action numbers, the sixteen-call service budget, blocking E4 sound,
PCs, resume order and fault behavior. The game loop still owns tick advancement,
animation dispatch, position publication and completion/recovery. Complex
original services retain their existing continuations.

[commands.h](../port/core/commands.h) supplies three synchronous operations:
active-party identity and skill queries, plus checked credit spending. BLD
conditions and school/refit payment use them. Queries return a boolean;
spending returns false without changing insufficient credits, or debits and
returns true. Callers own subsequent UI and waits. Other original money/overflow
semantics remain in the interpreter/adapter. This is a small real command
boundary, not a Lua binding or a new campaign-script ABI.

## P4 — Persistence boundary

[state_codec.c](../port/core/state_codec.c) owns the payload encoder, decoder,
historic migrations and validation. The moved function bodies are byte-for-byte
identical to their prior source in `game.c`. Public functions, BTPe/v40, the
20,480-byte payload and BTS1 envelope are unchanged.

[save.c](../port/data/save.c) retains file integrity, transactional loading and
slot I/O. [original_save.c](../port/data/original_save.c) retains original GAME
import/export and otherwise uninterpreted bytes. The decoder publishes a
candidate only after validation. The inventory distinguishes simulation,
content, presentation and pending-action state, and describes the future
package-identity boundary without reserving new fields in existing saves.

## P5 — Inventory and validated authoring prototype

The [inventory](CONTENT_INVENTORY.md) ties remaining compiled content and
original assumptions to current code owners. It includes maps/terrain,
characters, factions, encounters, stock/services, story/native actions, fonts,
text, UI, animations, sound and persistence, then lists the concrete missing
inputs for an independent game.

The provisional [schema](../schemas/content-v1.schema.json),
[three-model example](../examples/content-demo/README.md) and
[offline validator](../tools/validate_content.py) exercise namespaced IDs,
weapon references, explicit mount slots, units/bounds, capabilities, sprite
geometry and animation blocks. The validator also rejects malformed JSON,
duplicate IDs/keys, incompatible loadouts and nonportable/escaping asset paths.
Its structure checks read the schema; unsupported schema keywords fail.

All sample names/statistics are independently authored. The sample has two
weapons and one explicit sprite placeholder. It is not a playable package;
external-sheet checks verify file presence and declared geometry, not image
decoding. The deterministic digest covers definitions, not external file bytes.
No original-data export was needed. Runtime acceptance and shared semantic
validation remain M5a work; no JSON reader was added to the player.

## Verification

**VERIFIED within the following bounds:**

| Check | Result |
| --- | --- |
| P2 complete native CTest | 57/57, 42.08 seconds |
| P3 complete native CTest | 57/57, 42.41 seconds |
| P4 complete native CTest | 57/57, 42.26 seconds |
| P5/final native CTest | 57/57, 41.94 seconds |
| Preparation phase ASan/UBSan/LeakSanitizer | 57/57, 133.48 seconds; leak checking enabled |
| Preparation phase Windows/Wine CTest | 57/57, 222.08 seconds; default Windows stack reserve |
| Python tools | 19/19, including 14 authoring tests and five existing extraction/tool checks |
| P2, P3 and P4 before/after routes | Fresh campaign, spy replacement and services all match the retained pre-P2 player |
| Windows SDL portability | 41/41; controls, intro, six slots, views, failed loads, combat and ordered sound |
| Linux SDL Mech-It | 11/11; repair/ammo/refit/recruitment and seven F5/F9 held continuations |

The content-lifetime test now has **100 checks**, including ten new lookup
boundary checks. Existing suites retain original combat, service, world,
recruitment, story, animation, salvage, GAME round-trip, old-save and held-state
comparisons. No expected original result was regenerated for these refactors. The Windows
SDL checks include nineteen held combat pages; the sound case queues 44,468
nonzero samples and the return-to-base case queues none. The dummy audio device
checks event ordering, not physical speaker response.

The [before/after verifier](../tools/verify_preparation.py) compares every
canonical trace record and exact final save/RGB-frame bytes against the retained
`3b295ab` player in ignored `work/m5-preparation/before`. It uses private temporary
save slots. The fresh route has 83,339 inputs, spy replacement 66,760, and ordinary
services 769. Trace equality is a logical projection, not a claim to compare
every in-memory field after every input. Existing fixture tests complement it
with full records, RNG and continuation comparisons.

P1 had already passed all 57 native suites, focused sanitizer/Wine lifetime
checks, and both entrypoints' state/frame/save comparison in four cases each:
fresh start, Citadel/Katrina, ordinary combat and original GAME3 import. It also
checked alternate cache paths with spaces, each missing resource input,
sanitized snapshot restoration, Linux SDL intro and Linux/Windows F5/F9 held
amount entry, failed-load preservation and transaction continuation.

These are local refactor comparisons plus the established original oracle
corpus, not fresh complete DOS captures. Physical Windows hardware and 8 MHz XT
speaker calibration remain outside these claims. The sanitizer build reports
two existing sign-conversion warnings in health display expressions in
`pixels.c`; the refactors did not change those expressions.

Repeat the principal checks after building the relevant targets:

```sh
ctest --test-dir build --output-on-failure
./scripts/test-sanitize.sh --core-only
python3 tools/windows_check.py --ctest
python3 tools/verify_preparation.py --before work/m5-preparation/before
python3 -m unittest discover -s tests -p 'test_*.py'
python3 tools/validate_content.py examples/content-demo/content.json
python3 tools/native_smoke.py --windows --portability-only
python3 tools/native_smoke.py --mechit-only
python3 tools/reference_guard.py verify
```

The retained binary is a local comparison artifact, not a distributed fixture.
The regular test suites do not depend on it. GUI checks use private displays and
bounded scripts; sanitizer leak detection needs process inspection outside the
restricted sandbox. See [TESTING.md](TESTING.md) for build/tool setup.

## Next milestone

**M5a — External units:** load one authored model through shared runtime
validation, give live instances stable definition identity, connect its
presentation and supported rules, and preserve it in a package-aware save.
Exercise obtain, inspect, fight, damage, repair/refit, salvage and reload before
expanding to three models and proving that a fourth needs only data changes.
The existing original profile stays independently testable throughout.
