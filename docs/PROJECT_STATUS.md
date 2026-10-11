# Project status — M2k–M2m complete, 2026-10-11

**M0, M1 and bounded M2a–M2m are complete.** Both noncombat MechWarrior
assignments, rubble pickup/return, barracks sleep and the third assignment's
rest gate/briefing are playable. Original launch/dream animations, font and
border graphics are integrated. Shops, lounge Talk, banking, personal classes,
eight-direction movement and native saves remain available. The campaign and
combat remain unfinished.

## Milestones

| Gate | Result |
|---|---|
| M0 | Research/inventory/runtime audit; C11/SDL2 decision |
| M1 | Native MAP1 exploration and terrain collision |
| M2a | Citadel entry, six Hall screens and exit |
| M2b | First Katrina conversation and repeat denial |
| M2c | Native Talk/Done/reply; explicit controlled checkpoint |
| M2d | MAP1 NPC travel; conversation reachable through exploration |
| M2e | Two shop purchases, confirmations, allowance and persistence |
| M2f | ComStar investments/returns, boundaries and both shops' Talk |
| M2g | Internal save slot, integrity, native controls and continuation |
| M2h | Paid classes, tuition/refusals, cooldown and re-enrolment |
| M2i | Original walking sprites, persistent gait and mech preview |
| M2j | First MechWarrior mission/sleep; all goods; lounge; diagonals |
| M2k | Rubble pickup/carrying/return; all loan choices and objectives |
| M2l | Ordinary two-mission/rest loop through the third briefing |
| M2m | O0/O8 playback, original font/borders and animation persistence |
| Proposed M3a | Recover and verify the third assignment's stationary-target weapons combat |
| Remaining M2/M4 | Party/repair, world/maps and wider campaign progression |
| M3–M5 | Verified tactical combat; original campaign; optional enhancements |

M2l stops at the third mech menu: its combat launch fails visibly. Rick's
natural invitation requires fifth-assignment success and remains deferred;
the existing controlled lounge branch retains its explicit prerequisite.

## Play and verify

```sh
./scripts/build.sh
./build/btech-port --data "Original DOS"
./build/btech-port --smoke-replay --replay tests/fixtures/ordinary-rubble-story.actions
./scripts/test.sh
python3 tools/native_smoke.py
./scripts/test-sanitize.sh
```

The ordinary replay watches both missions, sleep and the third briefing, then
closes in about 126 seconds. Omit `--smoke-replay` to continue at the third
mech menu. Automated window checks accelerate replays while retaining every
logical input, render and 32ms simulation step. The 3945-tick window route
measured **3.63 seconds versus 126.24 seconds** at normal tick pacing, about
35× faster for this replay. Normal play and short real-key/animation/save
checks retain real-time pacing. See [testing commands](TESTING.md).

Training Center (46,114), Barracks (17,13) and Lounge (17,89) use half-coordinate
units. Pass the written quiz and first mission, wait outdoors for cooldown or
sleep, then accept assignment two. Choose Wasp or Chameleon, stand beneath
rubble and acknowledge pickup, then return to x<=60,y=73..79. A Locust has no
hands and fails this assignment. Success raises the allowance cap to 250.
Sleep allows the third assignment's original briefing.

Arrows/keypad move/select; perpendicular arrows form diagonals. Enter/Space
confirms; Backspace declines/recovers; F3 toggles diagnostics, R restarts and
Esc exits. Bank digits, Backspace, Escape-clear and Enter keep their editor
meanings. **F5/F9** save/load `work/player-save.btp`; `--save-file FILE` selects
another slot. Failed loads preserve the session.

## Evidence and verification

**VERIFIED in scope:** primary instructions establish all eight rubble targets,
automatic pickup geometry, Locust no-hands behavior, tile removal/restoration,
absence of a second-mission time limit and C61C rank increment. Live Wasp
success establishes the 250-cap reward, tired refusal, sleep and rested third
briefing. Tests cover all eight objectives with each loan mech, restoring and
continuing at every tick. See [milestone evidence](M2_RUBBLE_ANIMATION_EVIDENCE.md).

**181 original state/text checkpoints** and **100 phase/animation restarts**
pass under **three explicit original RNG prerequisites** at later quiz entries.
Long outdoor waits and NPC arrival timing diverge in the compressed native
input schedule: unseeded full-route NPC/RNG equality is not established.
A separate **3940-tick ordinary native replay** uses no state/RNG edits and
reaches both results, sleep and the third briefing. These are distinct claims.

All **198 decoded frames across 22 ANMs** match the independent reader;
**18 launch and 21 dream packed-frame hashes/offsets** match stable original
RAM. All **2048 font bytes**, **183 border cells** and **7744 final dream RGB
pixels** match original observations. Popup glyph checks cover all eight
entrances and both selections. Earlier **325 M2j checkpoints** and all other
movement, sprite, NPC, shop, banking, save and Class comparisons still pass.

PASS: **10 CTest suites**, four Python tests and all historical/new headless
comparisons. Corpus checks include 5776 core, 95 script, 33253 shop, 78178
bank/Talk, 17413 save-file, 59197 school, 17269 training and 4570 ANM assertions
(the frame export adds checks to its 4370-assertion corpus run).
Disk saves cover **175 replay snapshots** and every action's continuation.
Headless **ASan/UBSan/LeakSanitizer** pass; SDL/backend is not instrumented.
Native window routes match complete inputs, final state and pixels. Real-key
checks retain diagonals/chords/keypad banking; F5/F9 restores quiz, driving,
rubble pickup/carrying and dream/launch animation states.

## Persistence, provenance and limits

Current saves use **BTPC/version 12**, a **512-byte payload** inside the 16-byte
BTS1 length/CRC envelope (**528-byte file**). BTP1–BTPB migrations remain
covered. New fields retain assignment/objective/underlying tile, two mech ranks
and rollback, animation frame/cycle/hold and retrace fraction. Missing historical
state follows documented migration limits. The ignored **BTT6** cache contains
87 strings and the original 2048-byte font in 4937 bytes, generated from the
audited EXE with address/hash provenance.

Both supplied trees match **1287** guarded content/mode/mtime entries; all
88 original hashes match. The guard detected an external editor adding
`vscode-merge-base` to reference Git metadata; only that addition and its
modified timestamps were restored to the baseline. Research files and assets
were not changed. Proprietary captures, RAM, caches and dependencies stay
ignored. No substantial GPL source was copied/translated into the independent
C runtime; see README acknowledgements. Local audit/implementation commits
include `599b782` (audit), `9bfb67b` (mission/gates), `4430a23` (animation/UI)
and `a765830` (verification/fixes/accelerated tests). The review documentation
is committed separately. No pushes.

**INFERRED:** broader mech-rank semantics and unobserved unit/world contexts.
**APPROXIMATE:** remaining UI layout/status information, diagram pointer,
native input/animation timing and map edges. Movement history and original
rank bars remain absent. **UNKNOWN/deferred:** full-route long-wait NPC/RNG
parity, combat/later assignments, natural Rick unlock, world/party/repair,
original GAME compatibility, Windows, terrain animation and audio. O0/O8 are
the supported playback contexts; decoding other files does not implement their
campaign events. Whole-screen and complete timing parity are not claimed.
