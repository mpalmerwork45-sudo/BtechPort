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
and the post-attack countdown while retaining v1–v16 migration.

**APPROXIMATE / limits:** the current bounded combat window hands off at its
last half-row; the original crosses the packed sector boundary. Global travel
is the next increment. The invasion loss presentation and flags are covered;
the complete original pilot-evacuation/body damage RNG span remains outside
the combat comparisons. General campaign encounters are not yet implemented.
