# Project status — bounded M4 acceptance, 2026-10-13

The independent C11/SDL2 port has playable implementations of the authorized
M4a–M4e increments and the subsequent building, theft, encounter and presentation
requests. M4 as a complete original campaign remains unfinished. The original
cache and ending route starts from the owner's late GAME1 prerequisite; it does
not establish a fresh-game route through every earlier quest.

See [M4 evidence](M4_PROGRESS.md) for original routines, explicit prerequisites
and confidence limits. README credits the reverse-engineering contributors.
Reference directories are immutable; original assets and emulator RAM stay in
ignored work files. Local commits remain on `main`, with no push.

## Milestones

| Gate | Bounded result |
|---|---|
| M0 | Original inventory/runtime/research audit and C11/SDL2 decision |
| M1 | Independent native MAP1 exploration and collision |
| M2a–M2d | Citadel/Hall/Katrina, NPC travel and original dialogue |
| M2e–M2h | Weapons/armour, ComStar, saved continuations and paid classes |
| M2i–M2m | Original sprites, lounge, diagonals, first two missions/rest and animations |
| M3a–M3c | Weapons/Kick, walk/run/jump, six training assignments, Rick/device, paths/electricity and live combat |
| M3d–M3h | Invasion, destroyed Citadel, generated world, Starport, Rex, party/technician services and original music |
| M4a | Encounter aftermath, cash/salvage, ejection and character-loss comparisons |
| M4b | Formations, allocation, transfers, field healing and technician effects |
| M4c | Hospital/jail companions and treatment; hut, cinema, laser shop, house and two theft routes |
| M4d | Original cache puzzle/ending from GAME1, including eleven doors and MAP15 |
| M4e | Six original-save imports/exports, six internal slots, original intro/menu/inspection/map, sequential sound and outtakes |
| Owner follow-ups | Garage checkout allocation, invasion messages/DESTRUCT switch, walking escape, direction log, encounter Yes/No and source-based sprite selection |
| Remaining original campaign | Fresh-game integration through all prerequisites, additional branches and broader DOS combat/presentation parity |
| M5 | Optional enhancements after relevant original behavior is established |

## Play and verify

```sh
./scripts/build.sh
./build/btech-port --data "Original DOS"
./build/btech-port --load "Original DOS/GAME3"
./scripts/test.sh
./scripts/test-sanitize.sh
python3 tools/native_smoke.py --m4-acceptance
python3 tools/native_smoke.py --followups-only
```

Arrows/keypad move and select; two perpendicular arrows move diagonally.
Enter or Space confirms. Space outdoors opens party/settings/save/map actions;
Space also selects highlighted menu entries. F4 opens the explored overhead
map, F5/F9 save/load the selected slot, and F3 toggles diagnostics. Escape
declines or clears an amount; Ctrl+Shift+Escape closes. Holding Shift while
pressing K, Y, R adds 10,000 credits, including in the intro.

The Infocom/Westwood screen precedes the title/music and played-before question.
Yes opens saves; No starts training. Original GAME saves can be imported, and
an imported save can be exported outdoors with `--export-original work/GAME3`.
Six internal slots preserve active menus, animation/audio, combat and theft
state. `--save-file FILE` changes their base name. Failed loads preserve play.

The garage opens the original crew allocator during checkout. Jason can occupy
any assigned mech bay. Random encounters describe the attacking force and ask
whether to engage. No consumes the original RNG draw: three of four low-bit
outcomes evade; failure shows the original notice before combat settings.
Successful pre-combat evasion produces no loot or cash.

## Verification and limits

The current build has 43 CTest suites. Newly executed original comparisons
cover 68 prison/arena setups and 154 attack-sound/encounter decisions, alongside
46 house/laser/cinema cases and the earlier campaign, medical, save and cache
evidence. Prison and arena routes restore and continue before every input;
the prison guard timer, flee refusal and first fight round are exercised too.
Eight new SDL tails cover the house, cinema, hut, laser shop and both thefts,
comparing recorded keys, complete continued state and final RGB pixels.

**PASS:** all 43 regular and ASan/UBSan/LeakSanitizer suites, the complete
historical regression and full sanitizer script, native M4 acceptance and all
eight new native building/theft tails. Both reference trees pass all 1,287
content/mode/mtime checks. Code and fixtures are committed as `fbda805`.

**VERIFIED in these bounds:** numeric rules, resource interpretation, original
BLD branches and saved/native continuations. **APPROXIMATE:** DOS busy-loop
cadence, encounter placement and broader AI/initiative, following, several UI
layouts and physical speaker response. Audio uses original effect programs and
a nominal 8 MHz 8088 timing model; no exact recording from physical XT hardware
is claimed. Enemy Jenner/UrbanMech sprite bases follow the original enemy table,
while owned mechs use the original garage selection rule.

Internal saves are **BTPT/v29**, with a 20,480-byte payload inside the BTS1
length/CRC envelope. Current local caches are BTTA/v13, BTCB/v11 and BTW3.
Older saves migrate their represented fields; absent direction/exploration
history cannot be reconstructed. Build and play need no emulator. Optional
oracle tools execute bounded original instructions and commit numeric results
and source hashes only.

## Next five proposed tasks

1. Record a fresh-game campaign route through all disk/password/party
   prerequisites into the cache, with matching original checkpoints.
2. Extend prison/arena comparisons to guard defeat, owned-mech arena fights,
   normal rental return, full garages and recovery after losing a mech.
3. Recover the remaining later garage repair native actions 31/32 and verify
   the corresponding original building branches.
4. Compare complete larger encounters against DOS, including initiative,
   multiple ejections, mixed-party AI and aftermath.
5. Compare additional original combat/menu/map frames and recorded speaker
   waveforms; refine remaining UI margins, cadence and XT playback.
