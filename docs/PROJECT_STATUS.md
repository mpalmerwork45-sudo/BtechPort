# Project status — bounded M4 acceptance, 2026-10-14

The independent C11/SDL2 port has playable implementations of the authorized
M4a–M4e increments and the subsequent building, theft, encounter, recruitment and
presentation requests. A recorded 66,149-input route now starts with a new cadet
and reaches the cache ending through the actual training, companion, disk and
password prerequisites. It uses the authorized money shortcut. M4 as a complete
reproduction of every original campaign branch remains unfinished.

See [M4 evidence](M4_PROGRESS.md), [follow-up evidence](M4_FOLLOWUPS_EVIDENCE.md)
and [current fidelity work](M4_FIDELITY_EVIDENCE.md)
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

The current build has 53 CTest suites. New comparisons include 360 armour-repair,
160 purchase-recipient, 32 prison/arena return, 432 water-boundary, 512 device
direction and 314 recruitment/spy cases. Two controlled larger encounters cover
11 original waves and 171 complete record/position/facing/heat/RNG comparisons.
Five additional live-caller contexts cover 25 complete original waves and
7,252 assertions, including spy pilots/passengers and finite ammunition.
These extend the earlier campaign, medical, save and cache evidence.

The fresh ending and 50,564-input spy/replacement routes restore and continue
before every input. Nine SDL tails cover the house, cinema, hut, laser shop,
both thefts and spy replacement, comparing recorded keys, complete continued
state and final RGB pixels. Collision tests exercise three mechs and five people,
each footprint at every intermediate step, all moving gaits and saved positions.

**Current batch PASS:** all 53 regular and ASan/UBSan/LeakSanitizer suites.
The new encounter regression checks 440 cases at 44 legal party positions,
including 1,404 reachable enemies, unchanged candidate RNG/records and saved
offers. Three native boundary encounters pass combat-menu entry and F5/F9.
The preceding batch passed all 52 then-existing suites, five Python tool tests,
16 combat F5/F9 pages, six native arena/prison/theft tails, all nine
building/theft follow-up tails and the ordinary hospital-Talk SDL continuation.
The earlier historical sanitizer corpus also passed.
The preceding 48-suite increment
also passed every native M4
acceptance section and all nine native follow-up tails. Actual SDL checks pass
for Num-Lock-off keypad menus, Num-Lock-on amount entry, and one-key exits from
the final WINSCENE wait and older ending saves. Native checks include hospital
treatment and F5/F9 on the map, character, mech, cache and title screens.
The current fidelity evidence records the focused reruns after correcting an
outdated test checkpoint label. Both reference trees are checked against all
1,287 content/mode/mtime entries before handoff. Work is committed locally in
successive increments.

**VERIFIED in these bounds:** numeric rules, resource interpretation, original
BLD branches and saved/native continuations. **APPROXIMATE:** DOS busy-loop
cadence, encounter placement and broader AI/initiative, recovery of older split formations, several UI
layouts and physical speaker response. Audio uses original effect programs and
a nominal 8 MHz 8088 timing model; no exact recording from physical XT hardware
is claimed. Enemy Jenner/UrbanMech sprite bases follow the original enemy table,
while owned mechs use the original garage selection rule.

New random encounters cannot place enemies in disconnected areas behind town
walls. Infantry uses the correct ground sample, and enemy mechs cannot spawn
inside Starport even when the party is outside. **Owner-requested correction:**
the reachability guard extends the original terrain-only scan; it is not claimed
as original behavior. Twenty-five bounded original placement observations record
that distinction. If no candidate can be placed, exploration continues. Existing
saved fights retain their already placed units; arena/story fights are separate.

Internal saves are **BTPa/v36**, with a 20,480-byte payload inside the BTS1
length/CRC envelope. The discovery marker and held spy confrontation are saved.
Current local caches are BTTA/v22, BTCB/v11 and BTW3; the world seed is the
original startup value `0x020304`, rather than the former research seed.
Older saves migrate their represented fields; absent direction/exploration
history cannot be reconstructed. Old ambiguous decorative wreck/fire marks
are cleared on migration; v34 stores their actual world sectors. Build and play need no emulator. Optional
oracle tools execute bounded original instructions and commit numeric results
and source hashes only.

## Remaining authorized work

These are the next five unfinished areas, in priority order. Completed fixes
and comparisons are recorded above and in the evidence reports.

1. **Complete encounter comparisons.** Record full original outdoor and town
   fights, including initial placement/spacing, mixed-party AI, initiative and
   battle timing. The new reachability regression closes the reported trapped
   spawn bug; it does not establish full original encounter parity.
2. **Finish salvage.** Compare the complete success, failure and no-wreck pages
   and the order of repeated salvage attempts. Rewards, qualified-pilot prompt,
   victory/loot panels and arena results already have bounded comparisons.
3. **Finish town and cache boundary checks.** Extend original doorway/formation
   observations to the other towns, map seams and cache exits, including old
   saves with split formations. Whole-party wall checks and parked-mech recovery
   are implemented and tested; the remaining task is the wider transition matrix.
4. **Cover alternate campaign/service branches.** Audit remaining BLD paths and
   extend ordinary-input/save-load journeys beyond the tested fresh-game route,
   theft alternatives and replacement recruits. Original-save export is still
   restricted to supported outdoor contexts.
5. **Complete presentation comparisons.** Obtain a live original Phoenix LAM
   capture, compare remaining service/portrait/battle layouts and animation/NPC
   cadence, and calibrate sound against suitable reference recordings. Effect
   programs are verified; exact physical 8 MHz XT speaker response remains
   UNKNOWN until recording evidence is available.
