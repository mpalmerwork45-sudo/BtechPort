# Project status — bounded M4 acceptance, 2026-10-13

The independent C11/SDL2 port has playable implementations of the authorized
M4a–M4e increments and the subsequent building, theft, encounter, recruitment and
presentation requests. A recorded 66,119-input route now starts with a new cadet
and reaches the cache ending through the actual training, companion, disk and
password prerequisites. It uses the authorized money shortcut. M4 as a complete
reproduction of every original campaign branch remains unfinished.

See [M4 evidence](M4_PROGRESS.md) and [follow-up evidence](M4_FOLLOWUPS_EVIDENCE.md)
for original routines, explicit prerequisites and confidence limits. README
credits the reverse-engineering contributors.
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
| Owner follow-ups | Four Jenners/ruins escape, purchase recipients, armour repair, original crew/inspection/engagement/Speed Shop selectors, world seed/city alignment, all-party collision and gait, replacement recruits and spy confrontation |
| Fresh campaign | New-cadet input route through training, companions, paid apprenticeships, holodisk, password and cache ending; original checks at selected prerequisites |
| Remaining original campaign | Additional branches and broader DOS combat/presentation parity |
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

The current build has 45 CTest suites. New comparisons include 360 armour-repair,
160 purchase-recipient, 32 prison/arena return, 432 water-boundary, 512 device
direction and 314 recruitment/spy cases. Two controlled larger encounters cover
11 original waves and 171 complete record/position/facing/heat/RNG comparisons.
These extend the earlier campaign, medical, save and cache evidence.

The fresh ending and 50,575-input spy/replacement routes restore and continue
before every input. Nine SDL tails cover the house, cinema, hut, laser shop,
both thefts and spy replacement, comparing recorded keys, complete continued
state and final RGB pixels. Collision tests exercise three mechs and five people,
each footprint at every intermediate step, all moving gaits and saved positions.

**PASS:** all 45 regular and ASan/UBSan/LeakSanitizer suites, the complete
historical regression and full sanitizer script, native M4 acceptance and all
nine native follow-up tails. Both reference trees pass all 1,287
content/mode/mtime checks. Work is committed locally in successive increments.

**VERIFIED in these bounds:** numeric rules, resource interpretation, original
BLD branches and saved/native continuations. **APPROXIMATE:** DOS busy-loop
cadence, encounter placement and broader AI/initiative, follower detours, several UI
layouts and physical speaker response. Audio uses original effect programs and
a nominal 8 MHz 8088 timing model; no exact recording from physical XT hardware
is claimed. Enemy Jenner/UrbanMech sprite bases follow the original enemy table,
while owned mechs use the original garage selection rule.

Internal saves are **BTPV/v31**, with a 20,480-byte payload inside the BTS1
length/CRC envelope. The discovery marker and held spy confrontation are saved.
Current local caches are BTTA/v16, BTCB/v11 and BTW3; the world seed is the
original startup value `0x020304`, rather than the former research seed.
Older saves migrate their represented fields; absent direction/exploration
history cannot be reconstructed. Build and play need no emulator. Optional
oracle tools execute bounded original instructions and commit numeric results
and source hashes only.

## Next five proposed tasks

1. Reproduce the original eight-entry on-foot combat menu, active-unit header
   and remaining infantry/crew inspection layouts.
2. Trace larger DOS fights through their full live caller contexts, including
   spy crews, multiple ejections, manual friendly targeting and aftermath.
3. Audit all city doorways, roof corners and walking formations; compare the
   collision correction with additional original movement frames.
4. Compare isolated recorded combat effects and calibrate speaker filtering
   and cadence against suitable XT recordings.
5. Add fresh-game alternate theft/arena/loss routes and legacy-save migration
   cases, especially active invasion saves from v29.
