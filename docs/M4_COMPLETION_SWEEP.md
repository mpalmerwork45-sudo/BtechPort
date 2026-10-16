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

## Remaining work in this sweep

2. Live salvage result captures and death/ejection text.
3. Constrained cache follower paths and irregular saved formations.
4. Additional executed BLD branches and saved continuations.
5. Animation/NPC/audio timing measurements; physical XT recordings remain an
   external evidence requirement.
