# Project status — M2j complete, 2026-10-11

**M0, M1 and bounded M2a–M2j are complete.** The first MechWarrior quiz,
loaned-mech mission, result, reward and barracks sleep loop are playable.
All eleven weapons and five armour types are purchasable. The lounge supports
Talk and its verified Rick/device branch under the documented prerequisite.
People and loaned mechs move in all eight directions using original sprites.
The full campaign remains unfinished.

## Milestones

| Gate | Result |
|---|---|
| M0 | Research/inventory/runtime audit; C11/SDL2 decision |
| M1 | Native MAP1 exploration and terrain collision |
| M2a | Citadel entry, six Hall screens and exit |
| M2b | First Katrina conversation and repeat denial |
| M2c | Native Talk/Done/reply; explicit controlled checkpoint |
| M2d | MAP1 NPC travel; conversation reachable through exploration |
| M2e | Two shop purchases, confirmations, local allowance and persistence |
| M2f | ComStar investments/returns, banking boundaries and Talk in both shops |
| M2g | Internal save slot, integrity, native controls and restart continuation |
| M2h | Paid personal-skill classes, tuition/refusals, cooldown and re-enrolment |
| M2i | Original player/NPC walking sprites, persistent gait and mech preview |
| M2j | First MechWarrior quiz/mission/return/sleep; all goods; lounge; diagonal movement |
| Proposed M2k | Audit and implement the second assignment's rubble pickup/carrying/return loop |
| Remaining M2 | Further training/day progression, party/repair, maps/world and campaign foundations |
| M3–M5 | Verified tactical combat; original campaign; optional separate enhancements |

## Play and verify

```sh
./scripts/build.sh
./build/btech-port --data "Original DOS"
./build/btech-port --replay tests/fixtures/reference-diagonal-mech.actions
./build/btech-port --smoke-replay --replay tests/fixtures/reference-mission-pass.actions
./scripts/test.sh
python3 tools/native_smoke.py --training-only
python3 tools/native_smoke.py --diagonal-only
./scripts/test-sanitize.sh
```

The first replay opens an interactive window in the loaned Locust after ordinary
walking, quiz and launch inputs and twelve diagonal attempts. The second watches
the complete successful mission/return/sleep route through native SDL and closes
in about 57 seconds. It uses ordinary gameplay; no money or progress is injected.
The Training Center is at (46,114), Barracks at (17,13), Lounge at (17,89), all
in half-coordinate units. The written quiz asks for three parts on the original
diagram. Accept the first assignment and choose Locust, Wasp or Chameleon.
Visit x>=120,y>=124, acknowledge the corner, then return to x<=60,y=73..79.
Terrain costs time; success raises the allowance cap to 150. A successful first
mission permits the dream/sleep sequence and clears training cooldown. Later
assignments stop visibly before launch pending their verification.

Arrows move/select. Hold two perpendicular arrows for a diagonal. Keypad
1/3/7/9 or End/PgDn/Home/PgUp select diagonals; keypad 2/4/6/8 selects cardinal
movement. Enter/Space confirms/continues; Backspace declines entry or recovers
an unsupported choice. F3 toggles diagnostics, R restarts, Esc exits. Bank
amounts retain keypad/top-row digits, Backspace erasure, Escape-clear and Enter.
**F5 saves and F9 loads** `work/player-save.btp`; `--save-file FILE` chooses a
slot. Quiz answers, loaned mech, mission progress, sleep and lounge story flags
persist. Failed loads preserve the session; loading during recording is refused.

## Evidence and verification

**M2j VERIFIED in scope:** 325 original checkpoints: 100 mission-success/sleep,
69 mission-failure, 77 full-goods/ordinary lounge, 8 controlled Rick lounge,
19 diagonal human and 52 diagonal mission/entry checkpoints. Positions, story,
cash/cap, equipment, selectors, skills/accounts, outdoor clock and original text
hashes match. Quiz point/selection/RNG and human/mech gait/terrain also match.
Every observed new phase restarts in a fresh process and continues identically.
Diagonal free/blocked moves match the original's single destination check;
saved diagonal facing, entrances and both mission-return deltas are tested.
See [mission and diagonal evidence](M2_MISSION_EVIDENCE.md).

The full-goods run uses one audited 20000-credit test budget to buy every item.
The Rick event uses an explicit occupancy/recruitment prerequisite; its natural
later-campaign unlock is not implemented by the first mission. It removes Rick
from the room and sets the device flag, without party joining. Ordinary Talk
and all first-mission/sleep/diagonal routes use normal inputs.

Mission timing uses deterministic input updates and bounded native idle delays.
The live failed route's corner wait is normalized to four timer updates in its
fixture; exact DOS CPU elapsed parity is excluded. Original instructions and
boundary tests establish the raw Locust 264/265 pass/fail boundary and 214/215
for Wasp/Chameleon. The terrain field is obscuration, not combat heat. All three
loan choices have primary/test coverage; live completed mission parity is Locust.

PASS: nine CTest suites; 654 core, 95 script, 848 sprite, 1741 NPC, 33253 shop,
78178 bank/Talk, 12520 save-file, 59197 school and 2219 training assertions;
four Python tests; all historical and new differential routes. Headless
ASan/UBSan/LeakSanitizer pass. Native SDL covers success/failure/all goods/lounge
and restores changed quiz, active mission and dream states through F5/F9.
Real-key checks cover all diagonal mappings, simultaneous arrow chords/releases
and preserved keypad banking, with complete recorded replay equality.
SDL/backend itself is not sanitizer-instrumented. Native diagram, loaned-mech,
menu and dream frames were inspected for readable mixed case and clipping.

Earlier verified evidence remains: 376 sprite crops/45472 indexed pixels,
30 player and 63 complete NPC gait steps; 64 Class/funding/cooldown checkpoints
and 460 complete outdoor frame comparisons; 137 disk snapshots and 31 fresh
process states with 1024-tick continuation; 570 NPC frames, 56 natural conversation
checkpoints, 121 historical shop checkpoints, 160 bank/shop-Talk checkpoints
and 459 bank economy frames. The old NPC trace's 68 gaps remain explicitly skipped.

## Persistence, provenance and limits

Current saves use **BTPA/version 10**, a 448-byte payload in the 16-byte BTS1
length/CRC envelope (464-byte file). The extension retains quiz/mission/gait,
entry direction, story/checkpoint indices 45/46/47/51, reward-cap rollback and
dream animation request. BTP1–BTP9 migration remains covered; missing historic
state is initialized according to its documented limits. Original 3913-byte
GAME compatibility, power-loss durability and Windows remain unverified.
The **BTT4** cache contains 84 strings in 2712 locally generated bytes with
source hashes/address provenance; it stays ignored.

Both reference directories match all **1287** guarded content/mode/mtime entries,
including reference Git metadata. All 88 original file hashes match. Proprietary
assets, RAM, screenshots, caches and dependencies remain outside commits.
No substantial GPL source was copied/translated into the independent C runtime.
Local incremental commits: `3029374` audit, `1f73aeb` implementation, `67da964`
verification and diagonal controls. No pushes or Git configuration changes.

**INFERRED:** unobserved wider unit/world contexts. **APPROXIMATE:** independent
mixed-case font/layout, remaining original UI, native timing and map edges.
The diagram pointer/connector differs from the original despite authentic diagram
pixels. **UNKNOWN/deferred:** later assignments/day progression, natural Rick
unlock, party/repair/world, combat, original GAME saves, Windows, terrain/scene
animation and audio. Sleep preserves the original animation request and text;
its timed imagery and sound are absent. The next proposed gate is the second
MechWarrior assignment, beginning with original rubble pickup/carrying evidence.
