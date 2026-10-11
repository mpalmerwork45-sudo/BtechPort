# M2g — player-facing internal save/load, 2026-10-11

**VERIFIED implementation:** F5 saves one slot; F9 loads it. The default is
`work/player-save.btp`; `--save-file FILE` chooses another slot. Failed loads
leave the running state unchanged and show a visible failure notice. A successful
load clears queued input and resets the frontend's timing accumulator. Saving
does not change game rules. Restart remains R; loading during input recording is
visibly refused because the logical recording does not represent a rewind.

This is a modern convenience over the independently tested state encoding,
not a recreation of the DOS save interface or GAME file compatibility. The
original six saves/three backups remain untouched and their semantics UNKNOWN.
No proprietary resource, cached text or native object/pointer is stored in the
new save file.

**Current M3b extension:** BTPF/version 15 stores a 2048-byte payload in the
same BTS1 envelope (2064 bytes total). Seven-unit combat, enemy orders/paths,
targets, Kick, defeat and technician/apprenticeship with rollback survive
reload. The ordinary new-mission/service and Kick-only routes add 48 process
restarts and nine real-time native F5/F9 checks. BTPD/v13 and BTPE/v14 preserve
their historical 1024-byte migrations. See [M3b evidence](M3B_TRAINING_EVIDENCE.md).

**Historical M2k–M2m extension:** BTPC/version 12 stores a 512-byte payload in
the same BTS1 envelope (528 bytes total), adding rubble objective/underlying
tile, mech ranks/rollback and resumable cutscene state. BTPA/v10 and BTPB/v11
first-mission migration is checked explicitly; older migrations retain their
documented limits. Those disk tests cover 175 replay snapshots and 17413
assertions. Four real-time native F5/F9 checks restore launch, pickup, carrying
and dream animation with exact subsequent continuation. See
[rubble/animation evidence](M2_RUBBLE_ANIMATION_EVIDENCE.md).

## File and failure behavior

M2g initially wrote a 400-byte file: a 16-byte BTS1 envelope and the 384-byte
BTP7 payload. M2h writes 432 bytes with the 416-byte BTP8 payload and accepts
M2g saves, adding zero skill ranks and no active course when migrating.
The envelope contains magic, little-endian payload length and CRC32, followed by
four reserved zero bytes. The active building script is selected from the
serialized entrance slot; the existing versioned decoder validates the complete
state against the loaded resource context before committing a load. CRC and
semantic validation are separate checks.

Saving validates the state, exclusively creates `FILE.tmp`, closes a complete
write, then renames it over the slot. An existing pending file is preserved and
causes a visible failure. Write/rename errors clean up only the temporary file
created by this call and preserve the earlier slot. The tested local Linux
rename provides atomic replacement; power-loss durability and Windows behavior
remain unverified. No disk flush/durability guarantee is claimed.

The file stores location, facing, NPC records/occupancy/RNG/clock, cash/accounts,
equipment, story, remembered menus, text/script pauses, transaction input/results
and rollback. Its game payload retains the existing migration/validation rules.
Original GAME saves are rejected instead of being padded or misinterpreted.

## Completed verification

```sh
./scripts/build.sh
build/btp-save-tests "Original DOS"
python3 tools/verify_m2g.py
python3 tools/native_smoke.py --save-only
./scripts/test.sh
./scripts/test-sanitize.sh
```

**VERIFIED at M2g:** 7687 file-suite assertions, including 89 authentic replay phase/
amount snapshots. Each disk-restored state re-encodes identically and continues
identically under every logical action. The suite covers empty/partial files,
bad magic/length/CRC/reserved bytes, missing parents, invalid states, pending-file
collision, prior-slot preservation and repeated replacement. The source routes
include bank receipts/input, Hall/Katrina, both purchases and occupied-shop Talk.

The M2g CLI verifier starts fresh processes for 22 states, compares full
canonical JSON after loading, then compares 1024-tick continuation with the
uninterrupted route. It independently recomputes CRC32 on a semantically invalid
payload to establish that the game-state decoder still rejects it. Failed
rename, pending collision, corrupted/missing files and conflicting checkpoint
options pass.

A private-X11 test loads the verified bank amount screen, attempts a missing
F9 load, types 1 and presses F5, edits to 12, presses F9 and submits. Native
results are cash 34/investment 1 and equal a fresh headless process loading the
saved partial amount and accepting it. Only the indoor elapsed tick counter is
excluded from this wall-clock test; every other canonical field matches. The
separate process-restart test compares the tick exactly. The mixed-case receipt
and visible F5/F9 hints were inspected in the generated native frame.

All six CTest suites, earlier differential routes and the new disk/restart
checks pass. Headless ASan/UBSan/LeakSanitizer pass; SDL/backend remains outside
sanitizer instrumentation. Both reference trees match all 1287 guarded entries.

**M2h extension:** 11972 file assertions / 137 replay snapshots and 31 fresh-
process states now include course menus/transcripts, skill increases, completion
and cooldown. Every restored state continues identically; BTP7/BTS1 migration
is checked with an independently computed CRC. Invalid rank and bank states
with otherwise valid CRCs are rejected. All seven current CTest suites and
headless sanitizers pass; native F5/F9 was rechecked after the format extension.

## Commands

```sh
./build/btech-port
# Press F5 to save, F9 to load.
./build/btech-port --load work/player-save.btp
./build/btech-headless --replay tests/fixtures/reference-bank-rates.actions --save work/accounts.btp
./build/btech-headless --load work/accounts.btp
```

`--load FILE` restores before any requested replay. `--save FILE` writes only
after a successful headless run/native exit. Native notices use the window title;
errors also retain a diagnostic message. Save/load controls and layout are
conveniences, with no claim of original pixel/key/menu fidelity.


**M2i continuation:** current saves use BTP9 (still 416-byte payload / 432-byte
file), adding player/NPC walking frames. BTP8 remains readable; its missing gait
history restarts at the first frame for the stored facing. Logical Class/bank
progress retains the earlier migration rules. All preceding save/course checks
also pass on BTP9; see [sprite evidence](M2_SPRITE_EVIDENCE.md).

**M2j continuation:** current saves use BTPA/version 10, 448-byte payload and
464-byte BTS1 file. New fields retain quiz/mission/gait/timer, pending diagonal
entrance movement, story/checkpoint indices 45/46/47/51, cap rollback and the
dream animation request. BTP1–BTP9 migration stays covered. The original mission,
shop and lounge fixtures restart every observed new phase and continue to the
same complete state; outdoor diagonal checkpoints also restart. Real F5/F9
restores changed quiz, loaned-mech and dream states. The disk suite now includes
all 22 actions and passes 12520 assertions across its existing 137 snapshots.
See [M2j evidence](M2_MISSION_EVIDENCE.md); original GAME compatibility and prior
durability/platform exclusions remain unchanged.
