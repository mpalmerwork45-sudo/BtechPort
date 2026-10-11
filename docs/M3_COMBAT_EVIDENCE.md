# M3a — bounded third-assignment weapons combat, 2026-10-12

Status: **complete within the manual weapons-training scope**. The native
encounter reaches destruction, instructor reporting and the 500 allowance
cap. The shell is stationary by the user's explicit request. Original DOS
observations below show a moving disabled target; the controlled comparison
retains that behavior instead of changing the original expectations.
The broader combat system remains unfinished. The [overnight checkpoint](M3_CHECKPOINT.md)
is retained as history; [current status](PROJECT_STATUS.md) records the review.

## Sources and address conventions

The audited BTECH.EXE and unpacked-image identities remain those in
[the original inventory](ORIGINAL_FILES.md). Addresses below are **unrelocated
load-image segment:offset**, with DS at image 36DB0 and the state block at 28920.
The secondary combat notes use an older runtime load base: their `1000:458C`
is image `12E8:000C`, and `19EF:0BC0` is image `187F:0BC0`. Subtracting 1700
from their linear addresses resolves these aliases. Secondary names do not
establish behaviour; instructions and live snapshots do.

Read-only secondary guides: `UnBattletech/docs/combat-system.md` and
`UnBattletech/docs/engine/segments-19ef-1000.md`. No reference implementation
or generated GPL source is copied into the port.

## Verified primary findings

* `07DC:06F8`: assignment index 2 creates one enemy mech and no infantry through
  `07DC:0D49`. It clears actuator bytes 0x24/0x25, ammunition 0x27..0x30,
  movement 0x31 and jump 0x32, then enters `103B:000A` with training argument 1.
* The enemy is the original Locust template at image 28170. Setup consumes two
  RNG draws; this assignment forces x=114 and retains y=89+(second draw & 7).
  The party's first mech starts two half-rows above the launch cursor: (64,77).
* `103B:22BC` gives a mech **one movement point** when neither actuator byte
  retains bit 08. Zeroed training actuators therefore do not immobilise it.
  Ordinary DOS turns confirmed one enemy step per turn, with no RNG draws
  during the recorded movement-only turns.
* Combat asks about computer control, message verbosity and graphics, then
  exposes the ten original commands. Choosing a weapon and a target records
  an order; **Begin Fight** resolves the turn. Weapon orders persist.
* `0000:19F3` implements a die by drawing `RNG & 7`, rejecting 6/7, then adding
  one. `0000:19DD` calls it twice. This is not `RNG % 6`.
* `0E31:0BB5` distance is floor(max(abs(dx),abs(dy))/2)+min(abs(dx),abs(dy)).
  `0E31:0F24` adjusts distant mech targets for their footprint and uses strict
  range thresholds from the original weapon table.
* `12E8:0971` rolls **two dice** for an ordinary weapon's hit location, using
  the facing table at DS:2D0A and location table at DS:2E40. The later `RNG & 8`
  branch at 09D9 applies to **kicking**, not ordinary gunfire. Location and
  cluster draws precede the to-hit roll, including on misses.
* `12E8:0B43..0CD3` applies armour/internal damage and overflow. Internal hits
  call `0E31:11AB`; those critical effects cannot be omitted from a faithful
  weapons-training encounter. `0E31:1122` supplies overflow transitions.
* `0E31:0C63` dissipates heat using the mech's base cooling and working heat
  sinks before clearing the accumulated heat pool. The secondary statement
  that heat never dissipates is contradicted by these instructions.
* The training target is unit 12 / mech record 4, not special tutorial dummy
  unit 13. Its E48E flag is zero, so the tutorial line-of-sight bypass does
  not apply. Live blocked shots consume no ammunition or RNG.
* `07DC:0C80`: the surviving player mech and a clear flee flag produce the
  third assignment's success result. This case skips the later rank increase.
* `103B:188E..191F`: each planned movement step draws an original font glyph,
  indexed by `(dx+1)+4*(dy+1)` in DS:3B06. The eight direction IDs are N=1,
  NE=2, E=3, SE=4, S=5, SW=6, W=7, NW=8. The port uses these glyphs in planning
  and along the remaining saved path during execution.

## Repeatable observation and faster testing

The ordinary DOS run `work/reference-runs/1791709609448346900` starts from a new
game, completes both earlier assignments and sleep, and launches the third in
a Locust. There are no game-state or RNG writes. Snapshots include the two
125-byte mech records, orders, positions and RNG; captures remain ignored.
The live sequence records blocked shots, successful armour hits, internal
damage, target destruction and the return/result dialogue. The assignment
counter advances from 2 to 3. `tools/reference-third-combat.json` retains the
flattened ordinary input sequence; its complete replay has not yet been rerun.

The reference harness now accepts a final `next-script` directive under `work/`:
its arrival timeout is at most 300 seconds and the whole session is bounded to
500 commands. Continuations use the same ordinary keyboard driver and audit
log. They require no interactive terminal input or repeated prefix replay.

`tools/combat_oracle.py` is a separate, optional research runner using the
pinned Unicorn 2.1.4 binary wheel in ignored `local-deps/python`. It unpacks and
hash-checks the owner's EXE, executes its original instructions in private RAM,
supplies explicit test prerequisites and enforces an instruction limit. It
does not patch instructions, attach to DOSBox, or become a native-game runtime
dependency. The isolated original dice result was cross-checked against the
same routine executing a relocated DOS memory capture. Broader oracle and
native differential coverage now includes **2,099 original-instruction cases**:
128 dice, 441 range, 378 movement-point and 1,152 critical-effect comparisons.
Critical checks compare the complete 125-byte record fingerprint, fatal flag
and final RNG; they include all eight internal locations, three loan mechs,
destroyed locations and disabled actuators. The committed factual vectors
contain inputs, results and fingerprints, not asset or executable bytes.
All sixteen CTest suites pass, including the additional cooling and native-core
combat progression/graphics/save checks.

Regenerate / check those cases:

```sh
python3 tools/make_combat_vectors.py  # optional Unicorn dependency
./scripts/build.sh
./build/btp-combat-tests work/combat-data.bin tests/fixtures/combat-primitives.txt
```

The native game reads an ignored 1,110-byte BTC1 cache generated from the
audited EXE for the rule tests. It contains three loan records and numeric
weapon/location/cluster/critical tables, with an address/hash sidecar.

## Differential coverage and implementation limits

| Check | Result and scope |
|---|---|
| Primitives | 2099 original cases: dice, range, movement points and critical effects |
| Gunfire | 896 original shot spans; hit threshold, location, damage/overflow, death, arm effect, target record hash, RNG, ammo and accumulated heat |
| Navigation | 779 original LOS/path comparisons; one additional out-of-grid case checks a deliberate native diagnostic |
| Heat cleanup | 648 original `0E31:0C63` cases; three loans, idle/walk/run/jump costs, nonzero heat/pools, cooling/sinks, engine damage, burning and water cover |
| Full turns | 35 controlled original turns through destruction; both units' position/direction/heat, full record hashes and RNG |
| Ordinary playability | 5214 native inputs from new game through three assignments/report/exit; no state/RNG edits |
| Disk continuations | 20 fresh processes, including movement planning, targeting, firing indication, mid-turn, victory and reporting |
| C integration | 20063 assertions; continuation at every input, stationary shell, original arrow glyphs in all eight directions, graphics-independent rules, loan/withdrawal paths and save migration/rejection |
| Native X11 | 5219 SDL ticks in 4.95s, versus 167.01s normal pacing; complete inputs/final JSON/frame match headless |
| Real-time save controls | Six F5/F9 contexts restore exact continuation and pixels: computer prompt, route preview, confirmed route, weapons, target and resolving turn |
| Sanitizers | All headless suites/replays pass ASan/UBSan/LeakSanitizer; SDL/backend not instrumented |

The controlled full-turn fixture uses Locusts at (64,77)/(114,89), seed
70/54/210, rank zero, original target AI, messages None and graphics No.
`btp_combat_tick_reference()` enables that original AI only in the comparison;
ordinary gameplay keeps the shell's position and facing fixed. The original
fixture has not been rewritten to pretend that this requested change matches
DOS. The complete input-only victory route uses the Locust; Wasp/Chameleon
launch, Scan, menus and withdrawal paths are covered separately.

Navigation retains the original asymmetric parity and 24-column working-grid
addressing. A ray beyond that verified 576-byte grid is diagnosed; original
out-of-grid memory semantics are not established. Terrain ignition is also a
visible boundary before attack ammunition/RNG changes.

**VERIFIED in scope:** numeric weapon rules, heat cleanup, tested walking
paths/LOS and controlled turn scheduling; ordinary victory/reporting and
500-cap progression; original direction glyphs and save continuation.
**INFERRED:** broader Run/Jump turn behavior and general unit/AI contexts.
**APPROXIMATE:** combat layout, Scan/messages, cadence and a short firing
indicator gated by the graphics choice. It uses an independently drawn beam
and original atlas flame artwork, without claiming exact original weapon
animation. Only one destination is stored; the original waypoint queue is
deferred. **UNKNOWN / incomplete:** kicking, computer control, terrain
ignition, general AI/retaliation, later assignments, audio and wider combat.

Regeneration and verification use the existing optional local Unicorn wheel:

```sh
python3 tools/make_combat_shots.py
python3 tools/make_combat_cooling.py
python3 tools/make_combat_navigation.py work/reference-runs/1791709609448346900/combat-menu
python3 tools/make_combat_turns.py work/reference-runs/1791709609448346900/combat-menu
python3 tools/make_combat_replay.py
python3 tools/native_smoke.py --combat-only
```

Navigation/turn regeneration needs the private matching RAM/metadata capture.
Routine tests consume the committed numeric fixtures and do not need the
oracle wheel or DOSBox. Whole-game RNG, screen and timing parity are not claimed.
