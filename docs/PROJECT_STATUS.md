# Project status — original fidelity and expanded M5a roster, 2026-10-16

The independent C11/SDL2 port has playable implementations of the authorized
M4a–M4e increments and the subsequent building, theft, encounter, recruitment and
presentation requests. A recorded 83,339-input route now starts with a new cadet
and reaches the cache ending through the actual training, companion, disk and
password prerequisites. It uses the authorized money shortcut. M4 as a complete
reproduction of every original campaign branch remains unfinished.

See [M4 evidence](M4_PROGRESS.md), [follow-up evidence](M4_FOLLOWUPS_EVIDENCE.md)
and [current fidelity work](M4_FIDELITY_EVIDENCE.md)
the [earlier acceptance sweep](M4_ACCEPTANCE_SWEEP.md)
the [previous completion sweep](M4_COMPLETION_SWEEP.md)
and the [latest cadence and portability sweep](M4_PORTABILITY_SWEEP.md)
for original routines, explicit prerequisites and confidence limits. README
credits the reverse-engineering contributors and explicitly discloses AI use
with **OpenAI Sol 6.1 and Astra**. The independent code and documentation are
GPL-3.0-only; the original game's source code is not used, and its assets are
not distributed. Runners must supply their own original files.
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
| M5 | P1–P5 preparation and the [first playable M5a roster](M5A_ROSTER_SLICE.md) implemented; general packages, Lua and editor remain in the [plan](ENGINE_AND_EDITOR_PLAN.md) |

The owner-requested [engine and editor plan](ENGINE_AND_EDITOR_PLAN.md) records
the future authoring direction separately from the remaining original fidelity
work. [M5-P1–P5 are implemented](M5_PREPARATION.md): shared content ownership,
named unit/weapon/presentation/refit lookups, original action dispatch, isolated
persistence and an offline schema/sample. The current game and BTPe/v40 saves
remain the compatibility case. All 41 Windows SDL portability checks and eleven
Linux Mech-It service/continuation checks pass.
The [M5a CHI roster slice](M5A_ROSTER_SLICE.md) now supplies the pre-logo
Original/Updated selector and 17 playable external models/variants, with broker,
encounter and save support. The separate general-schema sample remains offline;
the rest of M5a and M5b–M5e packages/Lua/editor remain **proposed**.
The broker follow-up moves trading into an unused Starport building, adds sales
and clear four-bay capacity, migrates held v41 menus, and fits larger inspection
bars inside the diagram. Native and sanitizer verification is 59/59 each,
plus 23 Python tests and 10 targeted Windows/Wine suites.
All 20 Updated SDL window scenarios passed on Linux and Windows/Wine for that
initial broker follow-up. The subsequent 0.2.0 stock adds fourteen models,
including Zeus, Atlas and standard/Bear Crusaders, an eight-row scrolling list,
and verified loading of unchanged earlier catalogues. The first three mech
definitions are unchanged. Updated saves use v43; Original keeps v40.
Current expansion checks pass: native **59/59**, ASan/UBSan/LeakSanitizer
**59/59**, Python **25/25**, eleven targeted Windows/Wine suites, and **28/28**
SDL window scenarios on each platform. Existing Updated slots 1 and 5 load
with the new roster; their files were preserved. Evidence and adaptation limits
are recorded in the [roster milestone](M5A_ROSTER_SLICE.md).
The broker now has [new AI-generated artwork](../content/updated/art/README.md)
and the other buildings' description/compact-choice layout. The selected male
salesman master, final prompt, exact 88×88 preview and ANM are included, along
with a reproducible converter. Seven further static portraits now cover the
Training Center, lounge, prison, inventor's hut, cinema, hospital and ComStar.
Optional pack-local art does not change roster fingerprints or saves; older
packs retain each original presentation. Explicit BLD animations and held
frames take priority. General custom-building manifests and animated new
portraits remain future work.
The seven-building follow-up passes native **60/60**, Python **30/30**, and
five focused sanitizer and Windows suites each. Linux and Windows SDL each
pass **7/7** building visits, exact portrait crops, F5/F9 and full-frame restore.
The earlier broker work passed **28/28** selector/trading window scenarios on
each platform. Actual building screens were visually reviewed; all pixels
outside the new portraits and the original script continuations are compared.
Missing/malformed-art behavior, cinema scene priority and the training quiz
are also covered. See the [recorded evidence](M5A_ROSTER_SLICE.md).
At the owner's request, a commented **temporary** formation recovery now applies
in both editions after scene/menu exits and excessive separation. It keeps
parked/wrecked mechs inactive. Its removal TODO targets the underlying follower
route search; it is explicitly a gameplay workaround, not DOS parity evidence.
The [inventory](CONTENT_INVENTORY.md) records the
remaining compiled assumptions and concrete independent-game prerequisites.

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

The current build has **57 CTest suites**, passing on Linux, under
ASan/UBSan/LeakSanitizer and under Windows/Wine. The content-lifetime suite now
has 100 checks. Nineteen Python tool tests pass, including fourteen new authoring
cases. The P2–P4 fresh-campaign, spy-replacement and service routes match a
retained pre-refactor player at every canonical trace record and in final
save/frame bytes. See [preparation verification](M5_PREPARATION.md) for scope,
commands and interactive checks.
The earlier fidelity sweep established:

- **133 original combat waves** in four town contexts, including two complete
  MAP4 victories and two Starport traces bounded at 64 waves each. Two MAP4
  initial formations also match. This corrected enemy infantry avoidance and
  heat accounting on the winning wave.
- **384 complete salvage loops / 552 held pages**, comparing retry order,
  records, RNG, text and every pixel of each 200-by-72 text interior.
- **10,512 collision/doorway decisions**, covering all 13 towns, 84 doorways,
  eight directions and three party configurations. The cache corpus now has
  **534 original cases**, plus saved entry/exit with one through eight people
  and recovery of demonstrably invalid older follower positions.
- **928 original clothing/electronics visits**, a static audit of all 26 BLD
  control graphs and a 769-input ordinary service route. Static graph coverage
  does not establish execution of every story branch.
- **256 original brief/verbose combat reports**, including all pixels in the
  88-by-88 upper-left text area. A live original Phoenix LAM capture matches
  all **64,000 RGB pixels**.

The previous five-area sweep added eight complete outdoor/arena/prison
encounters (24 waves), 384 death/ejection report cases (256 pixel comparisons),
three complete live salvage result panels, 5,760 cache formation/contact cases,
2,400 saved formation steps and 124 complete inventor/house/theatre branches.
Seventeen theatre film/text panels now match the original scrolling text engine,
fixing overflow near the end. Sixty-six animation executions and all six combat
speed settings expose and correct missing opening holds and overly fast tactical
steps. The latest sweep corrects outdoor cadence to eleven nominal VGA retraces,
with immediate keyboard updates and saved fractional phases. It adds four
complete Starport/MAP4 victories (20 waves), twelve quiet-ejection pixel cases,
2,582 viewport visibility cases, 768 continuous original cache movement inputs,
and expands the HUT/MAYOR/THEATER corpus to 248 branches. A newly observed
original enemy-kick/map-memory interaction is now reproduced.

Computer assigns only the selected unit and leaves the menu open. Next Mech
allows separate assignments; Begin Fight starts the wave. Space stops continuous
play after the current wave while retaining assignments. Manual movement or
weapon editing returns the selected actor to manual control. Original command
loop comparisons and saved/native input checks cover this distinction.
Space selects on all held combat menus, including movement destinations and
replace-order prompts; during a running wave or outtake it interrupts instead.

The fresh ending and **66,760-input** spy/replacement routes restore and continue
before every input. The new native service tail joins the existing house,
cinema, hut, laser shop, theft and replacement checks. Nineteen held combat pages
exercise F5/F9; the cache check includes the Phoenix display, map room and ending.
Current verification and exact timings are recorded in [TESTING.md](TESTING.md).
That sweep passed all 56 Linux, sanitizer and Windows/Wine suites, along with five Python
tests and 41 Windows SDL checks (including 19 held combat F5/F9 pages).
The Windows build is checked under isolated Wine against Linux state/pixels;
physical Windows hardware and an actual XT speaker recording remain untested.

**VERIFIED in these bounds:** numeric rules, resource interpretation, original
BLD branches, compared text/pixels and saved/native continuations.
**APPROXIMATE:** DOS busy-loop cadence, broader encounter AI/initiative, some
layouts and exact DOS recovery of irregular saved follower paths. NPC idle updates now average eleven nominal 70 Hz retraces; host scheduling
and exact hardware clock rates remain approximate. Animation retrace
requests and combat speed delays now match within the 32 ms native tick. Audio
uses original effect programs and a nominal 8 MHz 8088 timing model; physical speaker response and
exact hardware calibration remain **UNKNOWN** without a reference recording.

New random encounters cannot place enemies in disconnected areas behind town
walls. Infantry uses the correct ground sample, and enemy mechs cannot spawn
inside Starport even when the party is outside. **Owner-requested correction:**
the reachability guard extends the original terrain-only scan; it is not claimed
as original behavior. Twenty-five bounded original placement observations record
that distinction. If no candidate can be placed, exploration continues. Existing
saved fights retain their already placed units; arena/story fights are separate.

Internal saves are **BTPe/v40**, with a 20,480-byte payload inside the BTS1
length/CRC envelope. The discovery marker and held spy confrontation are saved.
Salvage inspection history and queued/held battle reports persist too, retaining
actor names and results before later attacks change their records. v39 adds
casualty flags; v38 reports migrate without inventing death notices. v40 adds
fractional outdoor clocks and retained quiet-mode headers/ejection cursors.
Earlier clock phases migrate without changing RNG; missing old headers cannot
be reconstructed.
Current local caches are **BTTA/v24** (373 strings), BTCB/v11 and BTW3; the world seed is the
original startup value `0x020304`, rather than the former research seed.
Older saves migrate their represented fields; absent direction/exploration
history cannot be reconstructed. Old ambiguous decorative wreck/fire marks
are cleared on migration; v34 stores their actual world sectors. Build and play need no emulator. Optional
oracle tools execute bounded original instructions and commit numeric results
and source hashes only.

## Remaining original-fidelity tasks

The authorized cadence/encounter/quiet-text/cache/Windows sweep is complete
within [its documented bounds](M4_PORTABILITY_SWEEP.md). Proposed follow-ups:

1. Check the Windows build on actual Windows hardware, including keyboard
   layouts, physical audio output and a distributable executable-only package.
2. Compare complete combat frames and projectile/beam timing, extending the
   now-verified text interiors and viewport visibility rules.
3. Compare additional complete encounters in other towns and with different
   equipment, including mixed-party defeats and ejections.
4. Execute the remaining service/story branches identified by the 26-BLD audit;
   static graph coverage is not execution coverage.
5. Extend continuous original cache comparisons through terminal and door
   interactions with multiple party members, beyond the floor-only path corpus.

Physical 8 MHz XT speaker calibration also needs an appropriate recording.

The separate authoring direction next proceeds to **M5a external units**, as
defined in the [engine/editor plan](ENGINE_AND_EDITOR_PLAN.md). Preparation
completion does not imply that these original-fidelity tasks are complete.
