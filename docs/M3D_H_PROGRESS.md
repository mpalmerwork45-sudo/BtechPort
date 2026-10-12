# Bounded M3d–M3h evidence — complete, 2026-10-12

Authorized 2026-10-12: seventh assignment/invasion, native world travel,
party recruitment/inventory, owned-mech services, original audio/presentation.
This document records bounded primary observations and completed checks;
unchecked features are not fidelity claims.

## Primary findings

- **VERIFIED by original instructions:** `07DC:0765..07E9` draws one random
  bit on assignment index 6; index 7 forces the invasion. An ordinary index-6
  encounter has three Locusts. The invasion substitutes four Jenner records
  (`27E8:0561`) and clears the final sixteen MAP1 payload tiles to tile 64.
  `103B:0610..0651` permits escape outside the packed Citadel sector bounds.
- `07DC:0C80..0D1D` applies independent gunnery/Kick practice after index 4,
  enables `D310`, and sets `D311` if the training mech survives the invasion.
  Authentic TRAINING.BLD branches on those bytes and plays O9 only when the
  mech was lost. Secondary notes conflate several unrelated story fields.
- **Existing primary evidence:** world generation uses a 16×16 coarse table,
  256 saved noise bytes, midpoint subdivision, neighbour connections and
  mirrored 8×8 tile templates (`187F:0BFB/104E/11BB/13D9`). No original static
  whole-world map is being invented.

## Acceptance scope

Each working increment has original comparison cases, save continuation,
appropriate headless checks and a local commit. Final acceptance includes
native accelerated checks, sanitizer coverage and the immutable-tree guard.
The complete wider campaign, original GAME import/export and exact host-time
presentation remain outside these five bounded increments.

## Native generator increment

**VERIFIED:** independent C generation matches 30 complete original 64×64
sectors across three seeds, including `(0,0)` and `(15,15)`, and the previous
nine Citadel-area fingerprints. Static input extraction is 1,520 bytes in an
ignored, provenance-tagged/checksummed BTW2 cache. Build preparation no longer
runs an emulator to produce world tiles. Focused world tests pass, including
malformed-cache atomicity, the complete MAP1 overlay and saved-clock rendering.
Travel, town switching and random encounters are described in the later increments below.

## Invasion increment

**VERIFIED:** sixteen primary seventh/eighth branch/setup cases match the
invasion bit, all opponent records/positions and RNG. The cleared payload
bytes normalize to the southeast 8×2 tile opening, not a whole border row.
Ordinary input routes reach both mech retention and loss; the latter plays
authentic O9. Save/restore before every input passes on both routes.
Internal BTPH/v17 adds invasion, owned-mech record, transition coordinates
and the post-attack encounter mask while retaining v1–v16 migration.

**APPROXIMATE / limits:** the current bounded combat window hands off at its
last half-row; the original crosses the packed sector boundary. Global travel
is connected in the next increment below. The invasion loss presentation and flags are covered;
the complete original pilot-evacuation/body damage RNG span remains outside
the combat comparisons. General campaign encounters are described below.

## World travel and town increment

All original local maps and the original 26-entry BLD dispatch table are loaded.
Stored maps overlay their original packed-coordinate sectors; the destroyed
Citadel replaces MAP1 after the invasion. World movement crosses sectors and
stored-map boundaries, and retains an owned mech's wider collision footprint.
The Starport (MAP2, sector 10,8) is reachable through its west garage entrance.
The original GARAGE.BLD parks the mech and uses E6 to place Jason inside town;
EE/EF implement its credit deduction and affordability branch. The 150-credit
checkout fee remains the original script's requirement.

**VERIFIED:** primary `0000:201D..20CF` checks building entrances after a
blocked terrain sample, using unit feet. The native mounted cursor therefore
checks entrance Y+2. Ordinary inputs from new game through the invasion and
garage parking survive save/restore after every input. The additional ComStar
branch has also been exercised on foot. Random-encounter setup is compared in
the next increment; walking animation, host-time cadence and allocation UI remain
**APPROXIMATE** until their wider primary comparisons are complete.

## Party and encounter increment

**VERIFIED:** 65 original `09B8:104E..136D` Rex/alley and
`09B8:E4F..FB7` agent-generation cases match character records, the Commando
grant, opponent coordinates/records and random-state results. Eighteen
`05AB:D68..FBF` random-encounter candidate cases match every original infantry
and mech record, the relative spawn origin and RNG. These are independent
native implementations compared with unmodified instruction spans.

The ordinary input route now buys civilian clothing, attends the inauguration
after its D329 timer, plays O6, recruits Rex, receives his stored Commando and
enters/exits the alley encounter. Saves restored after every input preserve the
route. Combat supports mixed groups up to the original 24 unit IDs; friendly
selection retains independent orders and resolves attacks by ascending ID.
Party inspection and shop recipient selection expose each member's equipped
weapon/armour and skills. Internal BTPI/v18 expands to 16,384 bytes with bounded
party and extended-combat sections; old save layouts still migrate.

**APPROXIMATE:** following uses a saved position trail; the full original
formation/crew-allocation UI is not yet reconstructed. Random candidate
generation is compared, while wider terrain placement, encounter cadence,
engagement/flee UI and mixed-party AI/aftermath need further whole-encounter
comparisons. Current encounter loot is not yet awarded. Inventory exposes
equipped items; no speculative backpack system is introduced.

## Owned-mech service increment

**VERIFIED:** 47 numeric original `09B8` cases match record and cash results
for all eight Speed Shop refits, partial armour/structure repairs, and reload
affordability boundaries. Primary price tables (`DS:1D8C`, `DS:2060`) and the
Commando armour table (`DS:1E24`) are extracted as numeric inputs in BTC5.
Armour costs 4 per point, structure 9, a weapon component 300, a heat sink 800,
and restoring leg mechanisms 200. Component repair retains the original
limits; it does not erase unrelated engine/gyro/sensor critical damage.

The Mechit-Lube script now selects owned/stored mechs and provides repair,
ammo quantity, affordability and refit confirmation flows. Original E8/ED
party/skill conditions and E9 agent initialization recruit the technician.
The agent's post-dialogue coin occurs after a saveable key wait; exact DOS busy
loop RNG timing remains **APPROXIMATE**. The ordinary route uses a key delay
with the non-hostile result, then exercises partial repair, ammo limits and
the unfunded Speed Shop offer. Every input on that route survives save/restore.

After the invasion, the original stock-growth rules continue at the world
loop wrap without the cadet allowance (`0000:358..3C9`). Service UI layout and
batch presentation are **APPROXIMATE**; repair/refit/reload numeric comparisons
do not constitute a complete original town UI or technician-field-repair audit.

## Audio and presentation increment

**VERIFIED:** original `0000:477D..48AE` loads BTTITLE.CMP and WWOODBT.SIF.
The PC speaker driver is in `184B`; `0139..015F` derives PIT divisors from the
original frequency table, and `0298` advances the note stream. IRQ reload 4095
at 1,193,182 Hz with four-interrupt note pacing is independently reproduced.
128 original pitch cases and the complete 17,409-interrupt title fingerprint
match note position, divisor, active state and countdown at every interrupt.
The SIF stream is loaded from the owner's original file, not committed.

The native title plays the original artwork and music before ordinary play.
Any logical start key or the end of the approximately 60-second sequence enters
exploration. The headless core advances the same sound clock; SDL queues
48 kHz mono PCM independently from a copied core state. Three hundred saved
continuations preserve the next PCM block exactly. F9 discards old queued
samples before resuming the loaded clock. `--mute` disables the audio device.
Host volume, waveform integration/filtering and actual device latency remain
**APPROXIMATE**. Combat sound dispatch and PCjr output remain unfinished.

**VERIFIED:** original `DS:141A` maps 26 building kinds to their images;
`07DC:0098..00B1` calls the image routine before running the BLD. The native
left panel uses O17 for the Citadel, O21 for weapons/armour, O18 for repair/garage,
O19 for the inauguration hall and O20 for the arena. O6 supplies the recruitment
crest; O9 supplies the invasion-loss sequence. Primary table bytes and decoded
frames are compared. Original entry quality/RNG guards, exact wall-clock
cadence and complete screen parity remain **APPROXIMATE/UNKNOWN**.

## Final verification

**PASS:** all 34 CTest suites, the five Python tool tests, historical corpus and
input-replay checks, and headless ASan/UBSan/LeakSanitizer. The updated amount
editor is covered by CTest, every-input campaign restoration, focused native
keys and a final sanitizer CTest rerun. No SDL instrumentation is claimed.
The amount editor now shares the bank's seven-digit, Backspace, Escape-clear
and Enter-submit behavior; native Space leaves the quantity open.

Ordinary campaign fixtures restore before every input on invasion-survival,
invasion-loss, Starport, Rex and service paths. The longest route has 48,159
actions and 96,694 assertions. Native replay tails compare exact recorded
SDL inputs, full canonical final state and all final RGB pixels against
headless rendering: 498 invasion, 560 loss, 991 Starport, 1,193 Rex and 226
service inputs, roughly 0.5–2.5 seconds per tail. Each prefix is reached by real
logical inputs and written through the real save system; no save bytes or
story state are patched. Real F5/F9 probes compare continued clocks and pixels
at the recruitment crest, partial ammo amount and title music.

Current internal **BTPI/v18** uses 16,384 payload bytes / 16,400 BTS1 file bytes,
with v1–v17 migration. BTT6, BTC6 and BTW2 are ignored owner-derived caches.
Research fixture regeneration remains optional; builds and play no longer
depend on Unicorn. The final reference guard checks all 1,287 immutable entries,
including modes, mtimes and reference Git metadata. Local working commits are
on main, without pushes. Contributor acknowledgements remain in README.

World-preparation regression explicitly blocks the optional emulator imports
and still reproduces the exact BTW2 cache. This also catches research-only
imports accidentally leaking into the normal build path.

**Remaining limits:** mixed combat is not full original-party parity. A general
encounter currently finishes on destruction of unit zero; original pilot
ejection, surviving-party/wreck handling, character loss and loot are not
complete. The effect queue can omit visuals beyond seven simultaneous events.
Following and the crew-allocation UI remain bounded approximations. Other towns
load their original maps/scripts but do not yet have full story integration
coverage. Field technician effects, further audio contexts, original GAME
compatibility and the later campaign remain future work. The
[next five proposals](PROJECT_STATUS.md) address these remaining areas.
