# M3b — physical combat, Mechit-Lube, fourth and fifth assignments

Bounded milestone complete, 2026-10-12. Primary evidence is the audited owner's BTECH.EXE and BLD
resources; the ignored instruction oracle executes those bytes in private RAM.
No reference runtime or GPL game implementation is part of the port.

* **VERIFIED:** `07DC:074D` draws `3 + (RNG & 3)` labor robots for assignment
  index 3. `07DC:0D49` creates their original 17-byte C614 records, six binary
  skill ranks, 2d6 constitution, HP = constitution × 10, and weapon = RNG % 14.
  They occupy combat IDs 16 onward; C614 records start at slot 8. The fifth
  assignment, index 4, creates one live Locust through `07DC:07C3`.
* **VERIFIED:** Kick is weapon 32 / order slot 11. `12E8:0059..00AA` requires
  both hip actuator bits (record bytes 36/37, bit 8); `12E8:0297..02DD` starts
  its to-hit number at 3 and adds missing lower leg actuator bits.
  `12E8:0990..09EE` computes damage as mech weight / 5 and chooses between two
  leg locations with RNG bit 3. Ordinary location dice are still consumed.
* **VERIFIED:** `12E8:0758..091A` handles infantry armor and HP. Mech weapons
  use a 127 HP hit against these robots. Packed personal-weapon damage rolls
  are different from mech damage; small arms cannot penetrate mech armor.
  `12E8:0B5A..0B72` applies Inferno burning for three heat cleanups.
* **VERIFIED:** `REPAIR.BLD` supplies the six-option Mechit-Lube menu and all
  apprenticeship, no-mech speed-shop, repair and ammunition dialogue. A course
  costs 500 C-bills, once per character; `14D3:0BFC..0C9B` deducts the price,
  increments C61D and sets C624 bit 0. The insufficient-funds path changes
  neither skill nor credits. Loan mechs are training equipment, not ownership.
* **VERIFIED:** fourth success raises the allowance cap to 1000, fifth success
  to 2000; these are the low/high byte writes in TRAINING.BLD. Fifth success
  sets flag 45 and native action 43 places Rick at the lounge. No new mech
  gunnery/kicking rank is granted by these two assignment result routines.

Physical attack fixtures currently contain 600 controlled original spans,
including all three loan weights, leg damage, heat, cover, robot targets, all
14 randomly assigned robot weapons and Inferno burning. These are numeric
rule comparisons, not ordinary-input campaign or pixel comparisons.

## Original encounter and AI details

`tests/fixtures/training-combat-setup.txt` contains **105 original cases**:
48 fourth-assignment constructions, 48 fifth-assignment constructions, and
nine apprenticeship balances, including 499/500 and 32-bit boundaries. These
compare positions, complete record fingerprints, initial sprite frames and RNG.
The original robot offsets for slots 8–13 are `(1,2), (2,2), (0,3), (1,3),
(0,0), (0,1)`. The last two cross the nominal offset-table boundary; retain
the observed bytes instead of correcting the tables.

The blue humanoid sprite uses original base 254 plus frame 16–31. Initial
robots face west with frame 28; the native equivalent is atlas index
`270 + gait`, initially gait 12. Mech opponents start at frame 12. Infantry
uses the previously verified human gait programs rather than the mech programs.

**VERIFIED, bounded:** `combat-ai.txt` captures **128 decisions/path cases**
from `0E31:03AB` and `103B:193B`, with explicit MAP1 unit/position/heat
prerequisites. Enemy Locusts select walk/run, stop/face at close range and
queue their working weapons plus Kick. Labor robots flee six half-coordinates
along each differing axis and queue their assigned weapon. Crucially,
`0E31:046F` passes a normalized ID to `103B:2474`, which reads an inactive
party record and gives these early robots the minimum **three** points.
Calling `103B:2474` with a direct enemy ID gives six; that isolated result
does not describe the actual AI call path. The port preserves the observed
early-training behavior. Wider party contexts remain unverified.

## Playable behavior and continuation

- Fourth assignment: select among 3–6 moving, armed robots; eliminate the
  complete group, walk back and report. Success raises the cap to 1000.
- Fifth assignment: fight a live Locust that moves and retaliates. Success
  raises the cap to 2000 and the original BLD sets Rick's lounge invitation.
- Kick: select its target, cycle targets or cancel. Orders persist until used
  or cancelled. Both hip actuators are required; damage uses mech weight/5.
  Infantry melee weapons use their original attack rules too. The original
  mech menu provides Kick; no separate Punch/Charge command was observed.
- Walk/run/jump retain separate point/heat rules and route-arrow previews.
  Movement heat is retained when a route completes partway through a turn.
- Mechit-Lube: the original REPAIR.BLD menu, 500-C-bill once-only Jason
  apprenticeship, insufficient-funds and decline paths, no-owned-mech repair,
  speed-shop and ammunition responses, Talk/Done and exit.

The **35978-input** ordinary native route completes all five assignments,
the fourth/fifth reports, Rick's invitation and Mechit-Lube without state/RNG
edits. **35 fresh-process continuations** reach exactly the same final state.
A separate **5202-input Kick-only route** destroys the stationary training
shell and reports successfully with no gun orders; **13 continuations** match.
These prove native playability, not whole-campaign original RNG parity.

The C integration suite makes **109704 assertions**, including save/decode
continuation before every ordinary input, kicks without ammunition use,
damaged-hip refusal, no-jump Locust refusal, all three movement modes and
movement heat, target cycling, defeat/withdrawal without advancement,
apprenticeship payment/decline/repeat handling and atomic malformed-save rejection.

**PASS:** 19 CTest suites, historical headless comparisons and
ASan/UBSan/LeakSanitizer. Native X11 playback compares complete input logs,
final states and pixels. **Nine new real-time F5/F9 checks** restore Kick
selection/order, run/jump previews, apprenticeship confirmation/completion and
turn execution, then match headless continuation and pixels. The five-mission
window route took **34.24 seconds**, against **1151.46 seconds** at normal
tick pacing; the Kick route took 4.86 seconds against 166.62 seconds.

Current internal saves use **BTPF/v15**, 2048-byte payload / 2064-byte BTS1
file. Their combat annex stores all seven possible units, enemy paths/orders,
current target, Kick and defeat state. Technician/apprenticeship and their
rollback values persist. BTPD/v13 and BTPE/v14 1024-byte combat saves migrate
explicitly; earlier formats retain their documented migrations. Loading an
old target path still cannot move the third assignment's shell.

## Boundaries

**VERIFIED:** the stated numeric routines, encounter construction, initial
frames and bounded enemy decisions. **INFERRED:** general initiative and the
full multi-actor turn schedule outside those comparisons. The older 35-turn
original comparison remains limited to its controlled third-encounter context.
**APPROXIMATE:** firing/Kick indication, UI/status layout, native timing,
local-map edges and return presentation after defeat. Jump uses verified point
and heat rules; its full original visual sequence is not reconstructed.

**UNKNOWN/deferred:** owned-mech repairs/refitting/ammunition purchases,
multi-character apprenticeship/recruitment, assignments after the fifth,
general computer control, the original waypoint queue and exact attack effects.
Terrain ignition is visibly reported but its persistent fire/smoke simulation
is absent; live encounters resolve the attack without that terrain mutation.
Whole-route original/native NPC/RNG parity retains the documented long-wait gap.
Original GAME compatibility, world travel, terrain animation and audio remain
unfinished. Both reference trees are protected by the existing unchanged
content/mode/mtime baseline; captures and owner-derived caches remain ignored.
