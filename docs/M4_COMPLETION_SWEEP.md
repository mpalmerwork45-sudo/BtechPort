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

## 5. Timing audit — in progress

Original animation, combat delay and NPC cadence comparisons are being extended.
Physical XT calibration still requires suitable hardware recordings.
