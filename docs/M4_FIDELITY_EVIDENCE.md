# M4 fidelity follow-ups — 2026-10-13

The owner authorized the five tasks in PROJECT_STATUS after the previous M4
batch. Original instructions and live DOS captures remain the authority; both
reference trees are immutable. Original assets, screenshots, RAM and WAVs stay
in ignored work files. This report records each verified increment separately.

## 1. Original combat commands and scanning

**VERIFIED:** `103B:14C3` chooses ten mech commands from DS:3A6F and eight on-foot
commands from DS:3ABC. On-foot Move/Clear Moves replace Walk/Run/Jump/Kick.
Clear Moves clears that actor's path and computer flag while retaining weapons
and other actors' orders. The port retains stable internal command IDs so
existing mech orders remain compatible; replay helpers now use the actual menu.

`05AB:18E8` supplies the pilot/model header for mechs and the character name on
foot. The invented Heat/Turn/Route text is removed from this original layout.
`103B:2591` asks Friends/Enemies/Cancel before `05AB:1467` presents summaries.
Next Unit, optional Detail Scan for mechs and Done retain the map. Humans show
their original condition text and personal weapon, plus friendly armour or an
enemy direction. On-foot observers and mechs with destroyed sensors describe
enemy humans only, with the original warning. Detail Scan opens the existing
original mech diagram and returns to the summary.

Nine live original 104×200 left regions match every RGB pixel, including all
borders and selectors. Numeric hashes/provenance are in
`tests/fixtures/combat-ui-primary.*`. The private source prerequisite activates
GAME3's three parked vehicles, places its fourth member on foot and enables an
encounter. It does not alter original instructions or reference saves. These
regions establish interface parity, not full battlefield/encounter parity.

**PASS:** all 46 core suites after this increment, including every-input
restoration through the new menus. Native SDL input/state/pixel checks and real
F5/F9 on scan-choice, scan-summary and scan-detail also pass. BTPW/v32 retains
older saves, migrating an old direct Scan to the detail page and normalizing
obsolete on-foot command selections. BTTA/v17 extracts 223 original fragments.

Dependent ordinary routes were regenerated because the on-foot menu uses
different key counts: the fresh ending is now 66,115 inputs and the spy/
replacement route 50,569. Their prerequisites remain ordinary inputs, with
only the owner's money shortcut used for the ending route.

## Owner observations: town joins, combat presentation and spy sheet

**VERIFIED:** `0000:3050..30BB` paints consecutive town descriptors into the
height grid before `187F:1886` chooses landscape joining masks. The port's old
MTP overlay left the neighbours unchanged, joining forest pieces through town
edges and then clipping them. Town descriptors now participate in terrain and
TINYLAND joins. `187F:1584` also returns raw height/mask descriptors, distinct
from texture or TINYLAND indices; the port now keeps that distinction.

`city-edges-primary.*` contains 39 complete grids: three seeds, all thirteen
MTPs, their entire tile rectangles and an eight-tile landscape margin on every
side, including destroyed MAP11. Every tile and block descriptor matches the
unmodified original routines. Original file reads supply declared dimensions
and chunks before the bounded city-writing span; no instructions are patched.
The original noise/texture tables and MTP bytes remain in ignored local data.

**VERIFIED:** combat camera edges render surrounding generated pieces using the
saved battle origin. Eight corner/side views match every exploration terrain
pixel at the same world coordinates. This fixes the black rectangles caused
by clipping rendering to the finite local combat rules grid; it does not yet
establish full sector-crossing combat placement/AI parity.

**VERIFIED:** numerical microsteps still resolve before presentation, but their
captured effect records retain a dying unit's sprite and position. Corpses and
wrecks stay hidden until their own queued death event; later deaths cannot leak
into earlier attacks. The focused unit's camera remains at its captured position
through the death sound. Living/queued viewport equality and save/reload checks
cover both a mech and infantry. Sprite-16 vehicles retain their static sprite.

`12E8:1B0C..1E28` traverses the human corpse branch without selecting a sound;
`1C76` selects sound 8 for a wreck and the arena target uses sound 7. The port
now skips sound 8 for people. The event corpus grows from 154 to 155 executed
cases. Fire/hit/death clips and outtakes remain sequential.

**VERIFIED:** the spy warning uses yellow text at row eight on the existing
character sheet, as `0000:39B3..39FC` does. Name, weapon, armour, health and the
preprinted skill/equipment labels remain visible. The original pauses before
writing the skill ranks/equipment values on this warning; those remain blank
in the held page. All 43,200 right-panel pixels match a live DOS capture,
recorded in `spy-inspect-primary.json`; ordinary sheets retain their ranks.

**PASS:** all 47 CTest suites after these corrections (6.69 seconds in this
run), including the expanded world, event, combat presentation and menu checks.
Broader live fights, additional doorway/formation observations, isolated audio
and alternate fresh/legacy routes remain the authorized follow-ups below.

### Cache-island depth correction

**VERIFIED:** the owner observed a deep-water warning on visible land near the
cache cave. The warning used the raw generated heights even after MAP13's
island block had replaced them in the displayed terrain. The depth check now
uses the same town-aware height and neighbour descriptors as `187F:1314`.
This applies consistently to the leader, followers and ordinary route finder;
genuine all-water descriptor `0F` still blocks deeper crossings.

`world-island-water-primary.txt` adds 392 original decisions around the real
MAP13 island at startup seed `0x020304`, in eight directions on interior,
block and sector boundaries. The original paints the cave block into the
current/neighbouring sector, recomputes joining masks, builds the viewport
descriptors and then executes `0000:1C24..1CC1`. Every decision matches.
The existing 432 water-depth cases remain passing. An actual move from the
island's west edge onto visibly stored land succeeds, saves and returns to the
island with an identical restored next-input state. All 47 suites pass,
including the 66,093-input fresh ending route; no new save fields are needed.
Native SDL also passes walking/diagonal movement across this island edge and
real F5/F9 restoration, with identical recorded input, full state and pixels.

### Replacements in other towns

**VERIFIED:** thirty visits through actual other-town hospital and Mechit-Lube
entrances/BLDs cover the owner's replacement request. After the discovered spy
is removed, another technician/medic joins in their vacant slot. The original
lifetime spy marker prevents another spy. An equally skilled surviving party
member still suppresses another specialist. Every input is restored and
compared. These visits supply their stated post-betrayal travel prerequisites;
they do not claim complete original DOS journeys between the towns. The
existing 314 original recruitment/betrayal cases and ordinary spy-combat route
remain passing. No recruitment-rule change was needed.

## Live caller combat and current presentation corrections

**VERIFIED in the captured caller contexts:** five cases execute 25 complete
original waves from `1791861341506357450/mech-command`. The normal party has
three owned mechs and Rick on foot, opposed by one mech and six humans across
a Y-sector boundary. Variants cover spy passengers/pilots, an armed Rex rider
and finite ammunition. All 7,252 assertions agree: complete record hashes,
positions, facing, heat, RNG, victory/loss, saved continuation and betrayal.
`live-campaign-primary.*` records source identities and declared boundaries;
`make_live_campaign_vectors.py` executes unchanged original instructions.

Corrections include the original LOS reader's negative-index height buffers,
retaining computer pilots' movement modes until their goals are reached,
remembered AI goals, the mech-versus-infantry trample branch and sound 18,
infantry salvo damage after armour, and keeping consumed ammunition when a
spy changes seats. Random encounters now use the original surrounding
16-aligned world window. Enemy cycling follows original IDs and wraps 23 to
12; broader manual friendly selection remains an unfinished UI comparison.

**VERIFIED:** five complete 216x88 result/loot panels match captured original
RGB pixels, including border, retained lines, scrolling, colours and recipient
highlight. Source `1791877416552610064` follows a real computer-controlled
fight to victory, technician scavenging, scrap proceeds and personal loot.
`aftermath-ui-primary.*` records its numerical prerequisites and region hashes.
The held phases apply repairs/cash once, then loot and wound recovery in
original order. Replacing a recovered weapon offers the displaced weapon
again; Drop it ends that exchange. Every result boundary restores and
continues, including delayed cash and healing. Existing 114 primary numeric
salvage/cash/ejection cases remain passing. Withdrawal, salvage-result and arena
result layouts still need full measured original comparisons.

**VERIFIED:** the field-treatment panel matches all 216x80 pixels of
`1791876954390161281/healing`. It retains the medic, original skill/equipment
wording, green injured names and key prompt after the numerical healing has
already happened. Save/load never heals a second time. Hospital native action
24 now holds its medical page before returning to its BLD. Hospital and
cooldown/healthy layouts are implemented but remain **INFERRED** until their
own measured screen comparisons. BTTA/v19 extracts 317 original fragments.

The Mechit-Lube audit now includes 23 screen pairs. The last-mech gyro warning
starts below the final menu row; see [the detailed audit](MECHIT_LUBE_AUDIT.md).

**VERIFIED:** the original overhead marker span `0000:44AA..4574` draws a 2x2
RNG-coloured rectangle at the party coordinate after the device arrow. The
previously masked black pixels are this marker. The complete 64,000-pixel
GAME3 map comparison now passes without masks. Colour/RNG are saved and advance
on logical map polls; correspondence to DOS busy-loop cadence is **APPROXIMATE**.
Native X11 checks compare the static map outside those four asynchronous pixels,
check the solid marker footprint, then replay exact idle ticks after F9.

**VERIFIED native regression coverage:** 24 paired Citadel/world viewports at
four animation phases keep DESTRUCT tiles on the ruined Citadel when crossing
its northwest boundary. Tile-sheet selection now uses each displayed tile's
world location. Five cache companions each contribute visible map pixels and
have legal foot positions. Cache movement/room entry updates their world
coordinates and formation; loading older stale cave coordinates recovers the
formation before drawing. Ordinary Mechit-Lube entry and exit retain three
pilots and a rider, including Jason in bay two. Source crew observation:
`1791874354558657062`. Wider live original formation/collision parity remains
**APPROXIMATE**, beyond existing primary city and footprint cases.

**VERIFIED:** the final WINSCENE key sets the exit request, as the original
`0B5D:0515..0534` does. Actual SDL letter-key and legacy function-key tests close
the process and match headless replay. Num-Lock-off keypad arrows and Enter work
in the Space menu; Num-Lock-on bank entry and all diagonal controls still pass.
An active v29 invasion migration compares positions, current and per-actor
waypoints/remembered goals, then four continued inputs. Previously only the
active actor's destination was translated into the padded frame.

The fresh ending route now contains 65,991 ordinary inputs; spy removal and
replacement takes 50,423. Both restore before every input. The arena rental
escape uses earlier spectator fire at (87,97), because the corrected original
AI disables the rental's legs if the previous route waits until (78,102).
This changes the test's player tactics, not the game rules. Original
apprenticeship/VIEWDISK checkpoints have been re-executed against the new fresh
route. Late GAME1 still reaches the ending in 10,856 ordinary inputs.

**Current validation PASS:** all 48 regular and all 48
ASan/UBSan/LeakSanitizer core suites, the full sanitizer script's historical
checks, every native M4 acceptance section and all nine native follow-up tails.
Physical SDL keypad/ending controls and real F5/F9 checks also pass. Native
checks compare recorded inputs, complete continued state and final pixels.

The initial combined native run stopped at an outdated ammo-editor checkpoint
assumption: the corrected fight leaves that mech fully loaded, so the original
service displays an ammo-status page instead. The generator now labels the
actual page, and the harness types editor digits only for an amount editor.
Campaign, hospital/jail and cache sections then passed in focused reruns;
already passing unrelated sections were not repeated. The separate Mechit-Lube
checks retain their ammunition-purchase and save/restore coverage.

## Remaining authorized work

1. Complete remaining manual targeting and battle-result UI comparisons,
   including arena and withdrawal, and broaden full original fight contexts.
2. Expand live original doorway/corner/formation observations across towns.
3. Compare isolated speaker events and refine timing/filtering only with
   suitable evidence. Exact physical 8 MHz XT sound remains UNKNOWN.
4. Verify Phoenix LAM colours and hospital/cooldown/healthy medical layouts.
   Primary action 45 loads ENDMECH.CMP and selects the palette at 2858:0000
   (`14D3:15DD..16A6`); its measured VGA appearance is still pending.
5. Add fresh alternate owned-arena/win/loss and prison-loss routes. The active
   v29 migration and existing prison/rental/invasion/ending routes are now
   covered, but they do not establish all alternate original campaign branches.

This batch does not mark the original five follow-ups or M4 complete.
