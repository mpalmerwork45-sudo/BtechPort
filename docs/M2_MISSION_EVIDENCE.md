# M2j — first mission, all shop goods, lounge and diagonal movement

Completed 2026-10-11. Scope: first MechWarrior quiz/assignment/return/sleep,
all eleven weapons and five armour types, MAP1 lounge Talk, and eight-direction
walking and loaned-mech control. Later missions, combat, repair and party
recruitment remain separate work.

## Primary audit

Original EXE SHA-256:
`15a1712682cf1fe50ca9e6a68a4b31d3bef7912401915edf7bb6242be193562a`.
Unpacked-image SHA-256:
`100f0df244e4b0c8693d1b5013fb073f486b35d6f5c538ecd53d03f85ed54bfa`.
Independent bounded `objdump -mi8086` output is under ignored
`work/training-audit/`; reference assembly only locates routines. Addresses below
use the historical segment notation; image offsets subtract load base 0800.

| Finding | Evidence | Rating |
|---|---|---|
| Training / Barracks / Lounge | MAP1 slots 0 / 6 / 7, half-coordinates (46,114) / (17,13) / (17,89) | **VERIFIED** resource bytes and ordinary entry |
| Training entrance gate | `0FDC:0058..0080` calls `1467:08A8` while D320 is zero | **VERIFIED** primary and ordinary original play |
| Written quiz | BTSTATS.CMP; three distinct RNG points out of ten, twenty labels; DS 28C4/28D8/28EC coordinates/answers, 4DE2 label pointers | **VERIFIED** primary and live points 7,5,2 with RNG parity |
| Quiz failure | Any wrong answer sets D320=255 after three questions, then refuses entry | **VERIFIED** primary and native boundary/continuation tests; no complete live failure parity claimed |
| First briefing / mech selection | TRAINING.BLD 0229 / 0A42, menu 7, Locust/Wasp/Chameleon, F5 01 | **VERIFIED** bytes and live Locust route; other selections primary/test coverage |
| Mission launch | `1CD3:0027..0181`, copies original unit, mounts Jason, entry ends at (64,79), east gait 6 | **VERIFIED** primary and live launch |
| Southeast / return gates | `0FDC:09C4..0A02`: x>=120,y>=124; `08A7..08F9`: x<=60,73<=y<=79 after corner visit | **VERIFIED** primary and live route; early-warning boundary tests |
| Pass/fail arithmetic | `09A9..09C4`, `0C18..0C37`: counter plus terrain flag>>3; Locust subtracts 50 wrapping at 16 bits; signed result <215 | **VERIFIED** primary and boundary tests; exact DOS timing excluded |
| Terrain / mech footprint | `0800:1FC7..2186`, `0A42..0B40`; foot offset (0,-2), two horizontal columns, gate 85; terrain 0/8/16 | **VERIFIED** primary and live gait/terrain/blocked moves; broader formations deferred |
| Mission exit | `1CD3:01C2` sets (46,118), then caller commits both pending entrance deltas | **VERIFIED** live east exit (47,118); other deltas primary and saved-state tests |
| Failure / reward | Failure increments flag 3; success sets 0/1, clears 3, writes cap low byte 150 through script index 51 | **VERIFIED** BLD and live success/failure |
| Sleep | BARRACKS.BLD requires completed successful mission; flag 19 guards repeat sleep; seven pauses finish by clearing 20 | **VERIFIED** bytes and live refusal/success/repeat |
| Dream EA 08 01 | VM `0FDC:0494` requests animation 8, parameter 1 via `0800:48B7` | **VERIFIED** primary/request persistence; playback absent |
| Full shop roster | DS 4F44 weapon prices, DS 4F26/4DDB armour prices/protection; selectors 12,16,17,18 | **VERIFIED** primary and all sixteen live purchases |
| Lounge | LOUNGE.BLD menu 24, room 7 Talk; Rick `0FDC:18C6..18F3`, story indices 45/46/47 | **VERIFIED** ordinary empty Talk and controlled Rick scene |
| Eight directions | DS 0160 BIOS scan table; `0800:218F..2212` passes X/Y deltas to one destination check; 231D..240B human gait | **VERIFIED** primary and live human/mech diagonals |

The scan table orders N,NE,E,SE,S,SW,W,NW as signed words
`[-72,-73,-77,-81,-80,-79,-75,-71]`. Home/PgUp/End/PgDn supply the diagonal
BIOS codes. Both axes commit together; the original does not add separate
orthogonal wall checks. Gait advances even on a blocked attempt and resets
when direction changes. Human and mech programs retain their different starts
and cycles. Native combined arrows are a frontend convenience projecting to
these same logical actions; keypad digits retain priority in bank amounts.

## Original runs and regression projection

| Scenario / original run | Checkpoints | Actions | Preconditions |
|---|---:|---:|---|
| `mission-pass` / 1791702526057748887 | 100 | 1767 | Ordinary start, quiz, Locust, optimized route, return and sleep |
| `mission-fail` / 1791700897500835555 | 69 | 1236 | Ordinary route; explicit native timer normalization below |
| `full-goods` / 1791701039890663749 | 77 | 1227 | One audited 20000-credit test budget; all goods and ordinary lounge Talk |
| `lounge` / 1791702226982563634 | 8 | 44 | Explicit Rick occupancy/recruitment prerequisite |
| `diagonal-human` / 1791703432794053744 | 19 | 216 | Ordinary start; free and blocked diagonals in all four directions |
| `diagonal-mech` / 1791703495815619813 | 52 | 935 | Ordinary quiz/launch; free and blocked diagonals in all four directions |

`tools/verify_m2j.py` exports actual `inputs.jsonl` commands and original guest
snapshots, rather than assuming a later edited research script was executed.
Committed fixtures contain actions, numeric fields, provenance and text hashes.
They compare position, mode, 23 baseline flags, device/recruitment/result, cash,
cap, equipment, skills, investments, remembered selectors and outdoor loop
counter. Quiz point/selection/RNG, mission gait/terrain and diagonal human gait
also match. Bounded dialogue hashes reconstruct original BLD/native strings.
All 325 checkpoints pass; every observed new phase saves, restarts in a fresh
process and continues to the same complete JSON state through a bounded tail.
Outdoor diagonal checkpoints also undergo restart/continuation checks.

Mission elapsed time is a stack-local original counter, not the observed field
historically called heat. DS:32AE is terrain obscuration here. Native 32ms ticks
normalize pacing: a movement key gives one update; ten idle delay loops precede
the next idle update. The live failed L-shaped route waits at the corner; its
native replay adds 44 idle ticks (four updates) to reproduce failure. It would
otherwise pass at 262 updates. The optimized successful route matches without
that adjustment. Boundary tests establish raw Locust 264 pass / 265 fail and
Wasp/Chameleon 214 pass / 215 fail; live CPU-timed boundary parity is not claimed.

All weapon prices in order are 2,10,100,10,20,35,40,80,250,1500,1500;
armour prices are 50,150,200,10000,1000, with protection 25,40,30,50,50.
The live budget ends at cash 5053, weapon 11, armour 5/protection 50.
Exact funds, one credit short, No, 32-bit high-word cash, replacement equipment,
invalid context, rollback and saved continuation are tested. This remains solo
MAP1 equipment, not full party assignment or armour repair.

The Rick precondition is documented in `lounge-rick-context.json` and audited
before/after in the child emulator. The event clears recruitment/result, removes
Rick's occupancy, shows five original pauses and sets device flag 47. It does
not join a party. Its later campaign unlock is not reachable through the first
mission alone; ordinary lounge Talk does not inject that prerequisite.

## Native verification, persistence and limits

PASS: nine CTest suites; 654 core, 95 script, 848 sprite, 1741 NPC, 33253 shop,
78178 bank/Talk, 12520 save-file, 59197 school and 2219 training assertions;
four Python tests; all preceding and new differential checks. The full headless
ASan/UBSan/LeakSanitizer suite passes. Native SDL replays pass mission success
(1772 ticks), failure (1241), all goods (1232) and Rick lounge (49), comparing
complete inputs and final JSON. Real F5/F9 restores a changed quiz, active loaned
mech and dream pause. Real XTest input checks Home/PgUp/End/PgDn, keypad diagonals,
simultaneous arrow chords and releases for people/mechs, plus keypad bank digits,
Backspace, Escape-clear and Enter; each full record matches headless replay.
The original mission-start 24×24 Locust anchor crop (200,64) also matches all
576 RGB pixels in the inspected native frame. SDL/backend itself is not
sanitizer-instrumented.

BTPA/version 10 has a 448-byte payload (464-byte BTS1 file). It retains quiz,
mission timer/phase/mech gait, pending entrance direction, extra story/checkpoint
bytes 45/46/47/51, cap rollback and dream animation request. BTP1–BTP9 migrations
remain covered; old formats retain their documented missing-state limitations.
BTT4 has 84 original strings in 2712 locally generated bytes. Proprietary files,
cache, RAM and screenshots remain ignored. Both reference trees match all 1287
content/mode/mtime guards; all 88 original hashes match. No GPL runtime source
was copied or translated, and no repository was pushed.

**APPROXIMATE:** native cadence and map edges; independent mixed-case font,
layout and missing original panel imagery. Original diagram pixels are loaded,
but the native quiz pointer/connector differs: the inspected right crop matches
37845/38400 pixels, with differences at its left border and pointer line.
**UNKNOWN/deferred:** later assignments, natural Rick unlock, party/repair/world,
combat, original GAME compatibility, Windows, terrain/scene animation and audio.
The dream request and its text are retained; the original animation's timed
screen changes and sound are not reproduced. Unknown later mission launches
fail before changing campaign progress, the loan or player location.

Next proposed bounded gate: second MechWarrior mission, beginning with primary
and live verification of rubble pickup, hand/load state, carrying, return and
result. This milestone does not authorize implementing all subsequent missions.

During the final guard, an externally added `vscode-merge-base = origin/main`
line changed the reference Git config and directory timestamp. Removing only
that line reproduced its baseline SHA-256 byte for byte; those two recorded
mtimes were restored. The final guard again passes all 1287 entries. The new
project's remote configuration was left as found; no push was performed.
