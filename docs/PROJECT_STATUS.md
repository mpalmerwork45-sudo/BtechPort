# Project status — bounded M4 acceptance, 2026-10-14

The independent C11/SDL2 port has playable implementations of the authorized
M4a–M4e increments and the subsequent building, theft, encounter, recruitment and
presentation requests. A recorded 65,975-input route now starts with a new cadet
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

The current build has 51 CTest suites. New comparisons include 360 armour-repair,
160 purchase-recipient, 32 prison/arena return, 432 water-boundary, 512 device
direction and 314 recruitment/spy cases. Two controlled larger encounters cover
11 original waves and 171 complete record/position/facing/heat/RNG comparisons.
Five additional live-caller contexts cover 25 complete original waves and
7,252 assertions, including spy pilots/passengers and finite ammunition.
These extend the earlier campaign, medical, save and cache evidence.

The fresh ending and 50,423-input spy/replacement routes restore and continue
before every input. Nine SDL tails cover the house, cinema, hut, laser shop,
both thefts and spy replacement, comparing recorded keys, complete continued
state and final RGB pixels. Collision tests exercise three mechs and five people,
each footprint at every intermediate step, all moving gaits and saved positions.

**Current batch PASS:** all 51 regular and ASan/UBSan/LeakSanitizer core suites,
the historical sanitizer checks, six native arena/prison/theft tails and the
ordinary hospital-Talk SDL continuation. The preceding 48-suite increment
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
cadence, encounter placement and broader AI/initiative, follower detours, several UI
layouts and physical speaker response. Audio uses original effect programs and
a nominal 8 MHz 8088 timing model; no exact recording from physical XT hardware
is claimed. Enemy Jenner/UrbanMech sprite bases follow the original enemy table,
while owned mechs use the original garage selection rule.

Internal saves are **BTPY/v34**, with a 20,480-byte payload inside the BTS1
length/CRC envelope. The discovery marker and held spy confrontation are saved.
Current local caches are BTTA/v19, BTCB/v11 and BTW3; the world seed is the
original startup value `0x020304`, rather than the former research seed.
Older saves migrate their represented fields; absent direction/exploration
history cannot be reconstructed. Old ambiguous decorative wreck/fire marks
are cleared on migration; v34 stores their actual world sectors. Build and play need no emulator. Optional
oracle tools execute bounded original instructions and commit numeric results
and source hashes only.

## Remaining authorized work

The original five follow-ups are underway; this list records the actual
unfinished portions, including subsequent owner observations.

1. Finish original combat/result UI coverage: manual friendly targeting,
   additional live caller contexts, arena outcomes, withdrawal and salvage
   prompts. Five victory/scavenging/scrap/pocket/loot panels now match exactly;
   rewards, healing and held-page restoration are tested.
2. Expand live original doorway, roof-corner and formation comparisons across
   towns. All-party collision, city joins, ruined-Citadel sheet continuity and
   five visible cache companions have focused regression coverage.
3. All eighteen isolated tone/noise sequences agree with executed original
   code. Physical 8 MHz XT calibration remains UNKNOWN; the existing clock
   model and speaker response remain APPROXIMATE. Further tuning needs evidence.
4. Phoenix Hawk LAM colours now match the original decoder and palette writes,
   with native save/load checks. Field/hospital treatment and injured-cooldown/
   healthy notices match complete original crops. Healthy with active cooldown
   still needs a measured comparison.
5. Alternate owned-arena/win/loss and prison-loss journeys now pass, including
   arena completion, old stuck-menu recovery, reward and ownership checks.
   Town/Starport NPCs and room arrivals are restored, with 95 executed original
   cases and a normal hospital-Talk route. Regular Starport encounters are
   infantry-only; arena setup remains separate.
   Existing prison theft, rental escape, invasion loss and fresh ending routes pass.
   Active v29 invasion positions, current/per-actor goals and waypoints now
   have migration and continued-input checks; stale cache formations recover
   before the first loaded frame.
