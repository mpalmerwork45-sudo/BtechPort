# Project status — bounded M3d–M3h complete, 2026-10-12

All five authorized follow-on milestones have playable implementations and
bounded original comparisons. The seventh-assignment invasion leads through
the destroyed Citadel into the outer world. Starport's garage, civilian clothing,
inauguration, Rex/Commando grant and technician recruitment follow ordinary
inputs. Owned-mech repairs, ammunition and Speed Shop refits are integrated.
The original title music, building portraits and recruitment crest now play.
See [M3d–M3h evidence](M3D_H_PROGRESS.md) for confidence and remaining differences.

Earlier training, Rick/device, diagonal movement, route arrows, physical
attacks, force-field electricity and original borders remain covered. The third
assignment's shell stays stationary as requested. The wider campaign is unfinished.

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
| M3a | Third-assignment manual weapons combat, stationary shell, route arrows and victory/report |
| M3b | Kick; fourth/fifth assignments and Mechit-Lube apprenticeship |
| M3c | Live turns, twelve waypoints, flames/effects, map electricity, Rick/device, sixth assignment and generated Citadel view |
| M3d | Seventh/eighth invasion branches, Jenner setup, surviving-mech ownership, loss presentation and destroyed Citadel escape |
| M3e | Independent C world generation, travel/town overlays, encounter gates and Starport garage |
| M3f | Rex/Commando, party inspection/equipment recipient, saved following and mixed encounters with independent friendly orders |
| M3g | Owned-mech repair/ammo/refits, technician recruitment and selected-member apprenticeship |
| M3h | Original PC speaker title sequence, building portraits and recruitment/invasion-loss animation contexts |
| Remaining M4 | Broader encounter aftermath, original formation/crew behavior, later story/towns, original saves and ending |
| M5 | Optional enhancements after original-mode completion |

## Play and verify

```sh
./scripts/build.sh
./build/btech-port --data "Original DOS"
./build/btech-port --replay tests/fixtures/ordinary-starport.actions
./build/btech-port --replay tests/fixtures/ordinary-rex.actions
./build/btech-port --replay tests/fixtures/ordinary-services.actions
./scripts/test.sh
python3 tools/native_smoke.py --campaign-only
./scripts/test-sanitize.sh
```

The later replays execute ordinary input histories quickly in the headless core,
then open an interactive window. They preserve the real campaign prerequisites
without editing saves or jumping story flags. New native games show the original
title and music; Enter begins play. `--mute` disables the audio device.

Arrows/keypad move and select; Enter/Space confirms; Backspace declines or
recovers. Bank and ammo quantities use digits, Backspace erasure, Escape clear
and Enter submission; Space does not submit. F3 toggles diagnostics, F4 the area
map, F5/F9 save/load, R restarts, and Esc exits outside an amount editor.
F5/F9 use `work/player-save.btp`; `--save-file FILE` chooses another slot.
Failed loads preserve the session.

Space outdoors after the attack opens party actions. Inspect/Equipment selects
a member for display and subsequent shop purchases. Garage parking preserves
all owned mech records; checkout has the original 150-credit fee. Mechit-Lube
selects a mech, repair category, ammo bin/quantity or its scripted refit offer.
In combat, the friendly-unit selector retains independent movement/weapon/Kick
orders. General computer control remains an explicit unsupported command.

## Evidence and verification

**PASS:** all 34 CTest suites, five Python tool tests, the complete historical
headless regression and headless ASan/UBSan/LeakSanitizer. The final amount-editor
fix is covered by core, campaign continuation, native keys and the updated
sanitizer CTests. The SDL backend is checked natively but is not instrumented.

New primary comparisons cover 16 invasion setups; 30 complete 64×64 world
sectors across three seeds, including opposite world corners; 65 Rex/agent
recruitment cases; 18 mixed encounter candidate cases; 47 repair/reload/refit
cases; 128 speaker pitches; and the complete 17,409-interrupt title trace.
Portrait dispatch uses the original 26-byte building table. Original SIF note
bytes, images, executable spans and RAM remain outside Git.

Campaign integration restores before every ordinary input through invasion,
loss, Starport, Rex and services. The longest route has 48,159 actions and
96,694 assertions. Native SDL checks compare recorded inputs, final canonical
state and every final RGB pixel with headless playback. Focused tails cover
498 invasion, 560 loss, 991 Starport, 1,193 Rex and 226 service inputs, taking
roughly 0.5–2.5 seconds each. Prefixes are real input histories saved before the
tail. Real F5/F9 checks cover the recruitment crest, partial ammo entry and music.

Earlier M3c comparisons retain 126 full live turns, 108 waypoint cases, 128 flame
cases, 161 pose/gait programs, 60 terrain-animation crops, 144 training setups
and 225 result cases. The full historical checks retain ordinary training,
Kick-only and Rick/sixth routes. Focused verification avoids repeatedly spending
real time traversing the campaign; normal play keeps 32ms logical ticks.

**APPROXIMATE:** the invasion handoff at the bounded combat window edge;
encounter cadence, terrain placement, engagement/flee and mixed-party AI;
party following and crew-allocation UI; service layout/batching; DOS busy-loop
timing after recruitment; animation cadence and host audio filtering.
Complete original pilot ejection/character loss, encounter loot, field
technician repairs, other sound dispatch, GAME import/export and the later
campaign remain unverified or unimplemented. Old long-route NPC/RNG gaps and
later-quiz prerequisites remain documented. A 24-unit logical encounter does
not establish complete original party-combat parity.

## Persistence and provenance

Current saves are **BTPI/v18**, a 16,384-byte payload in the 16-byte BTS1
length/CRC envelope: 16,400 bytes total. Party, extended combat, service input,
animation and speaker timing survive reload; older v1–v17 layouts migrate.
These are internal saves, with no original GAME compatibility claim.

The runtime is independent C11/SDL2. Owner-derived BTT6, BTC6 and BTW2 caches
retain provenance. BTW2 contains static numeric generation inputs; the native
core generates arbitrary sectors independently. Build preparation and play no
longer need an emulator. Optional research fixtures execute bounded unmodified
original instruction spans. No original art, music stream, executable, RAM or
GPL reference runtime code enters Git.

The final immutable-tree guard checks all 1,287 reference entries, including
content, modes, timestamps and Git metadata. Local commits remain on `main`;
no push was made. README acknowledgements explicitly credit UnBattletech's
Edoardo Barolo/velteyn, Maximilien Noal and the other research/tool contributors.

## Next five proposed tasks

1. **M4a — Encounter results:** original engagement/flee decisions, rewards,
   salvage and aftermath, including pilot ejection and character-loss paths.
2. **M4b — Party and crews:** recover original formation, collision, crew
   allocation and equipment-transfer behavior; verify technician field effects.
3. **M4c — Next story and town services:** the next reachable companion/story
   branch, spy outcomes, hospital healing and timed NPC events.
4. **M4d — Original cache sequence:** recover the original Star League cache
   path and puzzle with bounded input routes and saved intermediate states.
5. **M4e — Original saves and remaining presentation:** GAME import/export
   round trips, original sound-effect dispatch and remaining status/portrait UI.

Each proposal needs a bounded original audit before its implementation; these
five tasks are not a claim that all remaining campaign work fits those increments.
