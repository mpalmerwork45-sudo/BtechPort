# M3a — third-assignment combat investigation

Status: in progress. The proposed "stationary target" description was too
strong: the original target moves. This document records primary observations,
not a claim that native combat is finished.

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
  `07DC:0D49`. It clears the enemy's actuator bytes 24/25, ammunition 27..30,
  movement 31 and jump 32, then enters `103B:000A` with training argument 1.
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
All eleven CTest suites pass after adding these independent C rules.

Regenerate / check those cases:

```sh
python3 tools/make_combat_vectors.py  # optional Unicorn dependency
./scripts/build.sh
./build/btp-combat-tests work/combat-data.bin tests/fixtures/combat-primitives.txt
```

The native game reads an ignored 1,110-byte BTC1 cache generated from the
audited EXE for the rule tests. It contains three loan records and numeric
weapon/location/cluster/critical tables, with an address/hash sidecar.

**UNKNOWN / not yet verified in the port:** complete turn scheduling, path
planning, line of sight, critical effects, firing visuals and native encounter
aftermath. Recovery of tables or individual routines is not full combat.
