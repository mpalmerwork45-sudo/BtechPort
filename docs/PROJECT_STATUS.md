# Project status — bounded M3c complete, 2026-10-12

The five authorized follow-on tasks are complete in their stated MAP1 scope.
The user's additions—force-field electricity and placing the Citadel within
its generated surroundings—are included. See [M3c evidence](M3C_PROGRESS.md).

Six training assignments reach reporting and rewards. Twelve-waypoint routes,
walk/run/jump, weapon/Kick orders, moving armed opponents, original firing and
impact poses, persistent flame/corpse/wreck markers and saved effects work.
The third assignment's shell stays stationary as requested. The fifth success
invites Rick to the lounge; his five-page device scene and the sixth assignment
against two live Locusts now follow ordinary inputs. Sixth success raises the
allowance cap to 3,000. The wider original campaign remains unfinished.

F4 shows the authentic 64×64 Citadel map embedded within nine original generated
sectors (192×192 tiles). The early campaign's impassable borders are retained.
Opening the exits needs the later attack/event; this map view does not claim
outer travel, arbitrary native C generation or other towns are implemented.

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
| M3a | Manual third-assignment weapons combat, stationary shell, route arrows, victory/report and 500-cap reward |
| M3b | Kick physical attacks; fourth/fifth assignments, moving/retaliating opponents, Mechit-Lube apprenticeship and early services |
| M3c | Original live turns, twelve waypoints, flames/effects, animated force fields, natural Rick/device, sixth assignment and generated Citadel area map |
| Remaining M2/M4 | Party/repair, world/maps and wider campaign progression |
| M3–M5 | Wider verified tactical combat; original campaign; optional enhancements |

## Play and verify

```sh
./scripts/build.sh
./build/btech-port --data "Original DOS"
./build/btech-port --world-overview
./scripts/test.sh
python3 tools/make_training_combat_replay.py --campaign
python3 tools/native_smoke.py --training-combat-only
python3 tools/native_smoke.py --world-only
./scripts/test-sanitize.sh
```

Arrows/keypad move and select; Enter/Space confirms; Backspace declines or
recovers. F3 toggles diagnostics, F4 the area map, F5/F9 save/load, R restarts,
and Esc exits. Bank digits/erasure/Escape-clear keep their editor meanings.
F5/F9 use `work/player-save.btp`; `--save-file FILE` chooses another slot.
Failed loads preserve the session.

In combat, selecting the same movement mode appends a destination, up to twelve.
Changing mode asks whether to replace the route. Arrows preview the shared
planner's next turn. Weapons and Kick orders persist; Next target cycles live
opponents. General computer control remains an explicit unsupported command.
Rick delivers the device without joining the party. Mechit-Lube covers Jason's
apprenticeship and original early no-owned-mech responses; owned services remain
future work.

## Evidence and verification

**PASS:** 26 CTest suites, four Python tests, the complete historical headless
regression and headless ASan/UBSan/LeakSanitizer. The SDL backend itself is not
sanitizer-instrumented. Native X11 checks cover the full five-mission/Mechit-Lube,
Kick-only and Rick/sixth routes, exact complete inputs/state/frames and twelve
real-time save contexts. A separate real-key F4/F5/F9 check matches the area map
and its saved-clock pixels exactly. The Yes/No route popup is visually aligned.

M3c primary comparisons include 126 complete live turns, 108 queued planning/
turn cases, 128 flame/ring/unchanged-terrain cases, 161 pose/gait programs,
60 terrain animation crops, 144 fourth-to-sixth encounter setups and 225 result/
rank/RNG cases. Nine complete generated-sector hashes and every MAP1 overlay
tile are checked. Earlier 4,422 numeric combat, 600 physical/personal attacks,
128 enemy decisions and 35 controlled original turns remain covered.

Native input-only routes now use 5,378 actions / 20 fresh-process restarts for
third combat, 36,755 / 54 for five assignments and Mechit-Lube, 5,358 / 20 for
Kick-only victory, and 43,996 / 55 for Rick/device and sixth victory. The latter
includes four withdrawals with non-advancement and original skill practice,
then succeeds against both opponents. C integration restores before every
input and includes a twelfth-microstep effect/save regression.

Accelerated native five-mission playback measured 39.16s for 36,760 ticks
(normal duration 1,176.32s); Kick playback 5.85s for 5,363 ticks (171.62s);
Rick/sixth playback 46.90s for 44,001 ticks (1,408.03s). These are about thirty
times faster than normal play, preserving inputs, logical ticks and rendering.
Focused probes use checkpoints and bounded original instructions. Normal play
retains 32ms ticks.

**Limits:** original whole-route NPC/RNG timing still has the documented gaps
and later-quiz prerequisites. Original player-mech destruction's pilot
evacuation/character-loss branch is not claimed by the full-turn comparisons.
Native training defeat/withdrawal are covered separately. Exact animation
cadence, beam/projectile placement, full pixel parity, wider initiative,
outer travel/encounters, other towns, owned-mech services, party recruitment,
original GAME compatibility and audio remain unfinished. Original flame
markers do not mutate terrain; no invented spreading fire/smoke damage is added.

## Persistence and provenance

Current saves are **BTPG/v16**, 4,096-byte payload in the 16-byte BTS1 length/CRC
envelope (4,112 bytes total). Routes, mark ring and effects survive reload.
BTPF/v15's 2,048-byte migration and older supported formats remain tested.
The runtime is independent C11/SDL2. Owner-supplied graphics and ignored BTT6,
BTC2 and BTW1 caches retain provenance; no original art, executable, RAM or
reference implementation enters Git. The world converter executes original
instructions only during cache preparation, using the existing pinned Unicorn
wheel. The C game reads generated data without an emulator dependency.

Both supplied reference trees match all **1,287** baseline entries, including
content, modes, timestamps and Git metadata. Local commits remain on `main`;
no push was made. Existing acknowledgements explicitly credit UnBattletech's
Edoardo Barolo/velteyn, Maximilien Noal and other research/tool contributors.

## Next five proposed tasks

1. **M3d — Seventh assignment and Citadel attack:** recover the original event,
   destroyed MAP11 transition and escape gate; verify its normal and failure paths.
2. **M3e — Native outer-world generation and travel:** replace the bounded
   cache with independent C generation; establish movement/encounter gates and
   the first additional town transition.
3. **M3f — Party recruitment:** original recruitment, following, party inventory
   and multi-unit collision/ownership, beginning with the next reachable companion.
4. **M3g — Owned-mech services:** repair, ammunition, refitting and technician
   effects through the original Mechit-Lube script.
5. **M3h — Original audio and remaining presentation:** recover sound/music
   data and dispatch, then remaining portrait/campaign animation contexts.
