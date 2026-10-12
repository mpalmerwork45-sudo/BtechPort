# M3d–M3h working evidence

Authorized 2026-10-12: seventh assignment/invasion, native world travel,
party recruitment/inventory, owned-mech services, original audio/presentation.
This document records bounded primary observations and completed checks;
unchecked features are not fidelity claims.

## Primary findings

- **VERIFIED by original instructions:** `07DC:0765..07E9` draws one random
  bit on assignment index 6; index 7 forces the invasion. An ordinary index-6
  encounter has three Locusts. The invasion substitutes four Jenner records
  (`27E8:0561`) and clears the final sixteen MAP1 payload tiles to tile 64.
  `103B:0610..0651` permits escape outside the packed Citadel sector bounds.
- `07DC:0C80..0D1D` applies independent gunnery/Kick practice after index 4,
  enables `D310`, and sets `D311` if the training mech survives the invasion.
  Authentic TRAINING.BLD branches on those bytes and plays O9 only when the
  mech was lost. Secondary notes conflate several unrelated story fields.
- **Existing primary evidence:** world generation uses a 16×16 coarse table,
  256 saved noise bytes, midpoint subdivision, neighbour connections and
  mirrored 8×8 tile templates (`187F:0BFB/104E/11BB/13D9`). No original static
  whole-world map is being invented.

## Verification to complete

Each working increment needs original comparison cases, save continuation,
appropriate headless checks and a local commit. Final acceptance includes
native accelerated checks, sanitizer coverage and the immutable-tree guard.
The complete wider campaign, original GAME import/export and exact host-time
presentation remain outside these five bounded increments.

## Native generator increment

**VERIFIED:** independent C generation matches 30 complete original 64×64
sectors across three seeds, including `(0,0)` and `(15,15)`, and the previous
nine Citadel-area fingerprints. Static input extraction is 1,520 bytes in an
ignored, provenance-tagged/checksummed BTW2 cache. Build preparation no longer
runs an emulator to produce world tiles. Focused world tests pass, including
malformed-cache atomicity, the complete MAP1 overlay and saved-clock rendering.
Travel, town switching and random encounters are still being connected.

## Invasion increment

**VERIFIED:** sixteen primary seventh/eighth branch/setup cases match the
invasion bit, all opponent records/positions and RNG. The cleared payload
bytes normalize to the southeast 8×2 tile opening, not a whole border row.
Ordinary input routes reach both mech retention and loss; the latter plays
authentic O9. Save/restore before every input passes on both routes.
Internal BTPH/v17 adds invasion, owned-mech record, transition coordinates
and the post-attack encounter mask while retaining v1–v16 migration.

**APPROXIMATE / limits:** the current bounded combat window hands off at its
last half-row; the original crosses the packed sector boundary. Global travel
is the next increment. The invasion loss presentation and flags are covered;
the complete original pilot-evacuation/body damage RNG span remains outside
the combat comparisons. General campaign encounters are not yet implemented.

## World travel and town increment

All original local maps and the original 26-entry BLD dispatch table are loaded.
Stored maps overlay their original packed-coordinate sectors; the destroyed
Citadel replaces MAP1 after the invasion. World movement crosses sectors and
stored-map boundaries, and retains an owned mech's wider collision footprint.
The Starport (MAP2, sector 10,8) is reachable through its west garage entrance.
The original GARAGE.BLD parks the mech and uses E6 to place Jason inside town;
EE/EF implement its credit deduction and affordability branch. The 150-credit
checkout fee remains the original script's requirement.

**VERIFIED:** primary `0000:201D..20CF` checks building entrances after a
blocked terrain sample, using unit feet. The native mounted cursor therefore
checks entrance Y+2. Ordinary inputs from new game through the invasion and
garage parking survive save/restore after every input. The additional ComStar
branch has also been exercised on foot. Full random-encounter setup is still
being connected; walking animation, host-time cadence and allocation UI remain
**APPROXIMATE** until their wider primary comparisons are complete.

## Party and encounter increment

**VERIFIED:** 65 original `09B8:104E..136D` Rex/alley and
`09B8:E4F..FB7` agent-generation cases match character records, the Commando
grant, opponent coordinates/records and random-state results. Eighteen
`05AB:D68..FBF` random-encounter candidate cases match every original infantry
and mech record, the relative spawn origin and RNG. These are independent
native implementations compared with unmodified instruction spans.

The ordinary input route now buys civilian clothing, attends the inauguration
after its D329 timer, plays O6, recruits Rex, receives his stored Commando and
enters/exits the alley encounter. Saves restored after every input preserve the
route. Combat supports mixed groups up to the original 24 unit IDs; friendly
selection retains independent orders and resolves attacks by ascending ID.
Party inspection and shop recipient selection expose each member's equipped
weapon/armour and skills. Internal BTPI/v18 expands to 16,384 bytes with bounded
party and extended-combat sections; old save layouts still migrate.

**APPROXIMATE:** following uses a saved position trail; the full original
formation/crew-allocation UI is not yet reconstructed. Random candidate
generation is compared, while wider terrain placement, encounter cadence,
engagement/flee UI and mixed-party AI/aftermath need further whole-encounter
comparisons. Current encounter loot is not yet awarded. Inventory exposes
equipped items; no speculative backpack system is introduced.
