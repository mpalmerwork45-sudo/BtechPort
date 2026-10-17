# Five follow-up areas — 2026-10-16

This is the next authorized, bounded fidelity sweep. Original executable/data
remain the authority. Controlled caller prerequisites are distinguished from
ordinary played journeys; proprietary RAM, captures and decoded text stay in
ignored `work/`.

## 1. Complete encounters

**VERIFIED within the new corpus:** eight complete encounters, 24 tactical
waves: owned and rented arena wins/losses at ranks 0/6, two prison guard defeats,
and two outdoor victories with three mechs and Rick on foot. Every wave compares
the RNG, complete unit-record hashes, living world positions, facing, heat,
ejection and the final outcome. The native test saves/restores and continues
before every input. Existing mixed-party, spy and town corpora remain separate.

`tools/make_complete_encounter_vectors.py` executes original `07DC:0D49` or
`05AB:0D68..1462` setup, `103B:00A1..01B8` command/heat initialization,
`103B:1774` camera, `0E31:03AB` AI and `12E8:000C` waves. It supplies the original
MAP2/MAP3 file payloads or generated sector D9 at world 1263,1675. Exact seeds,
party/loan/rank prerequisites and executable hashes are in
`tests/fixtures/complete-encounters-primary.json`. No executable instructions
are patched. These are numeric encounters, not DOSBox journeys to each arena.

**Fixed:** arena defeat now performs the final cooling pass before returning
to the cashier. Original `12E8` cools before `103B:0F13..0F31` checks mech loss.
The former early return left the surviving opponent too hot. Pilot facing and
prison movement discrepancies during development were incomplete oracle
prerequisites (inactive state and the wrong town payload), not port defects;
the corrected, explicit prerequisites now agree.

Reproduce with `python3 tools/make_complete_encounter_vectors.py`, then
`ctest --test-dir build --output-on-failure -R 'combat-primary-(complete-encounters|live-campaign|town-encounters)|arena'`.

## 2. Death reports and live salvage panels

**VERIFIED within the corpus:** 384 additional original shot/retirement cases
compare casualty/ejection text; 256 brief/verbose cases also compare every
88-by-88 interior pixel. Quiet-mode ejection text is compared, but its retained
cursor/header layout remains approximate. The missing destruction, ejection and
infantry death notices are now rendered at their corresponding events, with
original green mech-retirement ink. Held/queued death flags survive BTPd/v39
saves; v38 reports migrate without inventing a casualty. BTTA/v24 extracts 373
strings locally; no original strings are distributed.

Three live DOSBox result captures now compare all 216-by-88 panel pixels,
including borders: Rick salvaging a Wasp, rejecting its wreck, and the final
no-more-wrecks page. `make_salvage_live_vectors.py` records the controlled
presentation prerequisites and run IDs. Ordinary movement and complete combat
precede salvage; Rick's ranks/seat and encounter RNG are explicit data
prerequisites. For the failure capture only, the existing hostile wreck's
engine is damaged before accepting the offer. No original code is patched.
Incomplete capture attempts are excluded. The live success case exposed and
fixed the extra carriage return after an exactly full text row. Existing
salvage, combat, medical and Mechit-Lube panel tests still pass.

## 3. Cache formations and saved paths

**VERIFIED:** 5,760 original `0000:1C12` whole-formation collision/first-contact
cases across MAP14/MAP15, 120 cursor positions per room, parties of 1/5/8 and
eight directions. The original viewport runs; cache interaction calls are
intercepted after observing contact (their effects have the separate 534-case
corpus). MAP15's four-column jigsaw mapping is explicitly initialized by the
harness. Some starts deliberately place larger formations across obstacles.

**Fixed:** cache movement now checks every compact foot position at every
half-step. A follower touching a terminal or door supplies the interaction
position. An out-of-room sentinel cannot accidentally open the Phoenix scene.
The route generator uses the same complete formation test. The late-save and
fresh-game ending journeys were regenerated using ordinary inputs; both pass
save/restore before every input. Another 2,400 native saved steps exercise
scattered legal formations, diagonal movement and one/two/four-step inputs with
five/eight people in both rooms. These compatibility checks establish legal
positions and deterministic continuation, not exact DOS follower recovery from
malformed native saves.

## 4. Executed story branches

**VERIFIED within the stated prerequisites:** 124 more complete original BLD
executions cover HUT technician/medic threshold combinations and repeat visits,
MAYOR's three activities, solo/group wording, repeats and health boundaries, and
THEATER refusal and insufficient/exact/surplus funds. Final cash, story flags,
all party records, ordered menu choices, held-page PCs and animation/sound
requests match. Native continuations save before every input, film frame and
sound step. These branches required no game-rule changes. Executed bytecode
nodes are recorded separately from the earlier 26-file static graph audit.

**Theatre overflow fixed:** 17 additional film/held-page checkpoints execute
the original BLD and `1656:03F5/07CB` text engine. Every 200-by-184 interior
pixel matches, including the three-row scroll near the end and the final
clear/closing page. The former generic wrapper stopped at the panel bottom
and displayed an overflow diagnostic. Theatre text now uses the bounded
scrolling renderer, retaining the individual FC string boundaries. Native
save/restore precedes every input and animation/audio step in this comparison.
`make_theater_text_vectors.py` records numeric hashes only; reconstructed
original/native panels and two late-film saved checkpoints remain in `work/`.

## 5. Timing and sound audit

**VERIFIED request timing:** 66 original animation executions (all 22 ANMs,
flags 0/1/2) compare every packed frame hash, ordered retrace delay and startup
sound request. Original `0000:48B7/1AFD` and `187F:23EC` execute unchanged;
file reads, drawing, waits and speaker playback are explicit boundaries. All
six `0E31:1DCC` combat speed selections are recorded too. The native test checks
51 supported playback contexts against their requested durations within one
32 ms tick, plus both non-cinema repair/invasion contexts.

**Fixed:** repair, invasion and cache-ending films now include the original
50-retrace pause after their opening frame. Dream playback still repeats seven
times without that pause; normal startup keeps its sound and final hold. Combat
speeds 1–4 now convert 12/24/36/48 VGA retraces into 6/11/17/22 logical ticks per
advance, instead of 2/3/4/5. Speed five retains key stepping. Existing saved
in-progress delays finish normally; new advances use the corrected conversion.
Frame decoding cost and host scheduling are outside these duration claims.

**Correction, 2026-10-17:** the duration conversion above was correct, but its
application to every movement advance was not. Complete original-wave traces
show that this wait belongs after each attack; speed five also holds attacks
only. [The pacing correction](COMBAT_PACING.md) supersedes that part of this
earlier sweep and removes hidden pose waits when graphics are disabled.

**Measured, still APPROXIMATE:** a fresh 25-second, read-only DOSBox MAP1 idle
capture produced 160 stable samples and 159 consecutive frame transitions.
All NPC coordinates, timers, RNG, phase and saved continuations match the native
frame rules. The observed mean period is **156.825 ms** (median 151.952 ms,
15 ms polling resolution), consistent with the original eleven idle retraces.
The port currently advances an idle NPC frame every four 32 ms ticks (**128 ms**).
This difference remains open: changing the exploration scheduler also affects
recruitment/allowance RNG history and needs its own input-timing migration and
regression pass. DOSBox ran its normal core at fixed 10000 cycles; this is not a
physical XT measurement. Timestamps are stored separately from projected frames
so they cannot defeat the two-identical-polls stability filter.

**Sound:** all eighteen original tone/noise program comparisons and the
sequential attack/impact/destruction/startup continuation tests pass. Physical
speaker filtering, prefetch/interrupt effects and exact 8 MHz XT calibration
remain **UNKNOWN** without suitable hardware recordings. No hardware sound
parity is claimed from the emulator timing observations.

The ordinary training, invasion, town, theft, arena, spy and ending routes were
regenerated after the deliberate presentation delay changes. The fresh ending
has **73,026 inputs**, and spy removal/replacement has **56,936**. Both restore
before every input. The two fresh apprenticeship checkpoints were re-executed
against the original routines with the new route's actual records and cash.

## Verification

All **55 regular suites** pass, including the focused cache rerun after updating
its original checkpoint prerequisites. All five Python tool tests pass. Native
`--completion-only` checks both late theatre pages and all three live-compared
salvage result pages with actual Space/F5/F9 keys, comparing complete restored
state and pixels. The ordinary cinema SDL tail also matches its Enter-key
headless continuation. All **55 ASan/UBSan/LeakSanitizer suites** pass in
121.32 seconds outside the sandbox restriction on LeakSanitizer process
inspection; no leak checks were disabled. The reference guard is run after
the final commit against the 1,287-entry immutable-tree baseline.
