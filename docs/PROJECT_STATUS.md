# Project status — bounded M4 acceptance, 2026-10-15

The independent C11/SDL2 port has playable implementations of the authorized
M4a–M4e increments and the subsequent building, theft, encounter, recruitment and
presentation requests. A recorded 66,257-input route now starts with a new cadet
and reaches the cache ending through the actual training, companion, disk and
password prerequisites. It uses the authorized money shortcut. M4 as a complete
reproduction of every original campaign branch remains unfinished.

See [M4 evidence](M4_PROGRESS.md), [follow-up evidence](M4_FOLLOWUPS_EVIDENCE.md)
and [current fidelity work](M4_FIDELITY_EVIDENCE.md)
and the [five-area acceptance sweep](M4_ACCEPTANCE_SWEEP.md)
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

The current build has **54 CTest suites**. The five-area sweep adds:

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

Computer assigns only the selected unit and leaves the menu open. Next Mech
allows separate assignments; Begin Fight starts the wave. Space stops continuous
play after the current wave while retaining assignments. Manual movement or
weapon editing returns the selected actor to manual control. Original command
loop comparisons and saved/native input checks cover this distinction.
Space selects on all held combat menus, including movement destinations and
replace-order prompts; during a running wave or outtake it interrupts instead.

The fresh ending and **50,672-input** spy/replacement routes restore and continue
before every input. The new native service tail joins the existing house,
cinema, hut, laser shop, theft and replacement checks. Nineteen held combat pages
exercise F5/F9; the cache check includes the Phoenix display, map room and ending.
**PASS:** all 54 regular and sanitizer suites, five Python tool tests, and the
native checks listed above. See [testing](TESTING.md) for exact commands and
the corrected Space-test routes.

**VERIFIED in these bounds:** numeric rules, resource interpretation, original
BLD branches, compared text/pixels and saved/native continuations.
**APPROXIMATE:** DOS busy-loop cadence, broader encounter AI/initiative, some
layouts and constrained-cache follower paths. Audio uses original effect
programs and a nominal 8 MHz 8088 timing model; physical speaker response and
exact hardware calibration remain **UNKNOWN** without a reference recording.

New random encounters cannot place enemies in disconnected areas behind town
walls. Infantry uses the correct ground sample, and enemy mechs cannot spawn
inside Starport even when the party is outside. **Owner-requested correction:**
the reachability guard extends the original terrain-only scan; it is not claimed
as original behavior. Twenty-five bounded original placement observations record
that distinction. If no candidate can be placed, exploration continues. Existing
saved fights retain their already placed units; arena/story fights are separate.

Internal saves are **BTPc/v38**, with a 20,480-byte payload inside the BTS1
length/CRC envelope. The discovery marker and held spy confrontation are saved.
Salvage inspection history and queued/held battle reports persist too, retaining
actor names and results before later attacks change their records.
Current local caches are **BTTA/v23** (370 strings), BTCB/v11 and BTW3; the world seed is the
original startup value `0x020304`, rather than the former research seed.
Older saves migrate their represented fields; absent direction/exploration
history cannot be reconstructed. Old ambiguous decorative wreck/fire marks
are cleared on migration; v34 stores their actual world sectors. Build and play need no emulator. Optional
oracle tools execute bounded original instructions and commit numeric results
and source hashes only.

## Remaining fidelity work

The authorized five-area sweep has the bounded results above. Remaining gaps
must not be represented as complete original-game parity:

1. Complete additional outdoor, arena and prison DOS fights; the two 64-wave
   Starport observations are not victories, and elapsed combat timing remains
   approximate.
2. Capture live salvage success/failure/no-wreck screens and further death
   reports; current salvage interiors and shot reports use original glyph calls.
3. Compare long follower paths through constrained cache corridors and more
   irregular saved formations beyond the invalid-position repair cases.
4. Execute additional branches identified by the 26-BLD static audit and extend
   ordinary save/load journeys. Original export remains limited to supported
   outdoor contexts.
5. Measure animation/NPC cadence and audio against a suitable timing reference;
   physical 8 MHz XT sound needs hardware recordings. Windows remains untested.
