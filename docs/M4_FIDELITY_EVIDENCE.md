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
24 now holds its medical page before returning to its BLD. Subsequent hospital,
cooldown and healthy comparisons are recorded below. BTTA/v19 extracts 317
original fragments.

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

## Arena completion and world debris

**VERIFIED:** original `0D43:0A35..0B1A` silently retires the rental-arena
spectator when opponent 12 dies. `103B:0F13..0F31` ends a normal arena match
when the player's mech is destroyed, even when Jason survives the ejection.
The port now applies both rules, waits for pending destruction presentation,
and also recovers an older save held at the resulting stuck combat menu.
`103B:13AD..13DA` sets the win flag and shows the original result text;
`14D3:10EA` clears arena fire marks before returning to the cashier. The
cashier's BLD applies the 500-credit win award once. Owned-mech liability
waivers and every held result/cashier page now restore correctly.

`arena-finish-primary.*` contains 28 executed original retirement/terminal
cases. Five new ordinary-input routes cover owned and rented arena wins and
losses, plus a prison-loss route. The arena routes return to town with the
expected cash, vehicle ownership and surviving Jason; the prison loss reaches
game over. Every input is checked against restored continuation. All six SDL
tails (these five and rental theft) pass recorded-input, full-state and final
pixel comparisons via `native_smoke.py --arena-only`. Arena popup geometry is
still **INFERRED** from its shared original caller, pending a direct DOS crop.

**VERIFIED:** `103B:27C9..2834` records debris with a packed world sector,
not a local map identifier. The previous representation placed unrelated
world wrecks and human remains in each new encounter window. All marks now
retain world coordinates and render only at their actual location. The 126
executed original cases cover all six mark sprites, ring wrap and world seams;
the integration check fills all 64 slots in other sectors and compares the
encounter-offer image with an empty ring. A local wreck remains visible.
Original GAME1–GAME6 imports and exports retain the original ring byte for byte.

Internal saves are **BTPY/v34**, retaining the 20,480-byte payload. Saves older
than v34 discard their ambiguous decorative debris ring because its missing
world origin cannot be recovered. Character, vehicle and mission state is
preserved. Original empty ring slots retain their otherwise-unused coordinates
for exact round trips.

**PASS:** all 50 regular and ASan/UBSan/LeakSanitizer core suites, with focused
reruns of two synthetic legacy-save fixtures after removing modern debris from
their old-format prerequisites. The preceding 48-suite increment's historical
sanitizer checks and broader native acceptance remain recorded above; this
increment additionally ran the six arena/prison/theft native tails.

## Remaining authorized work

1. Complete weapon override/empty/destroyed notices, selection persistence,
   infantry/Kick selectors and direct arena/salvage comparisons. Original
   withdrawal and weapon/target regions now have comparisons below.
2. Expand live original doorway/corner/formation observations across towns.
3. Physical speaker calibration still needs suitable hardware evidence. All
   eighteen ordered tone/noise traces now agree with executed original code;
   exact physical 8 MHz XT sound remains UNKNOWN.
4. Phoenix LAM decoding/palette registers are verified below. The healthy-with-
   cooldown medical branch still needs a measured visual comparison.
5. Alternate owned-arena/win/loss and prison-loss routes and the subsequent
   town-NPC/hospital-Talk request now have saved and SDL continuations.

This batch does not mark the original five follow-ups or M4 complete.

## Weapon/target panels and withdrawal — 2026-10-14

**VERIFIED for eight complete, unmasked regions:** original run
`1791924339149371505` selects a mech weapon, cycles from a LOCUST to a human,
assigns the gun, closes the weapon list and withdraws. The private GAME4
prerequisite activates GAME3's parked vehicles, puts character four on foot,
and enables encounters; the EXE/assets and both reference directories are
unchanged. The port now draws `0D43:0004`'s weapon window from x72 to x319,
sized by installed weapon count, with its 80-pixel name selection, original
ammunition labels, actual target model and range. `0D43:07CB`'s target facts
and three choices occupy the left boxes, leaving the battlefield visible.

Successful withdrawal displays its notice in the lower left box. Its next
page restores the party status panel and shows the original 216x56 return
popup, without the former extra footer. These pages now match the original
captured regions. The input test restores before every transition and checks
that withdrawal awards no money. The original manual selector initializes
enemy ID12 and cycles through IDs12..23; no ordinary friendly-target gesture
was found, so the earlier plan to add one was not justified.

The assigned-row pixel comparison explicitly sets the original selected row.
The port still advances to the next gun after assignment, whereas the captured
original retains the selection and clears the left text. Selection persistence,
override/empty/destroyed notices and the infantry/Kick selectors remain work
for a subsequent behavior increment. Battlefield equality is not claimed.

**PASS:** all 51 regular CTest suites, all five Python tool tests, focused
ASan/UBSan/LeakSanitizer combat UI/aftermath/menu/cache-format continuation
checks, the native combat input route, and actual F5/F9 on all seven tested
scan/weapon/target/withdrawal pages. The dialogue cache is now BTTA/v20 with
319 ranges; existing string IDs and internal-save format remain unchanged.

## Phoenix Hawk palette and isolated speaker audit — 2026-10-14

**VERIFIED:** action 45 (`14D3:15DD..16A6`) loads ENDMECH.CMP and selects
`2858:0000`, which differs from the title/sprite palette. The port now retains
dark magenta at source colour 5 and uses bright blue at colour 13. The new
`make_phoenix_palette_vectors.py` executes the original CMP decoder and VGA
palette writer, without instruction patches. Its complete 320x200 RGB result
matches the native Phoenix page. The RGB model also matches the previously
captured original title. This is original decoder/register evidence, not a
claim of a live DOSBox Phoenix screenshot or physical monitor calibration.

**VERIFIED within the nominal clock model:** `make_speaker_event_vectors.py`
executes all eighteen original programs and records every tone divisor and
noise-loop input in order. Native event type, divisor, speaker level and active
PIT-clock totals agree. This includes the swept zero divisor, which represents
65536 rather than a rest. Eighteen isolated native WAVs under ignored
`work/m4-audit/isolated-speaker/` are non-silent and unclipped, with durations
0.032–1.216 seconds. No runtime audio or speculative filter change was needed.
These are native renders, not original physical recordings. Interrupt/prefetch
costs, inter-call silence and XT speaker filtering/volume remain approximate.

**PASS:** focused regular cache/menu/audio checks, ASan/UBSan/LeakSanitizer
cache and audio suites, all six native cache tails and actual F5/F9 restores
on both the map-room and Phoenix screens. The preceding complete 51-suite and
historical sanitizer results remain recorded below.

## Town actors, hospital conversations and Starport encounters

**VERIFIED:** fifty executions of original `0000:30E2..3205` and `0000:24C2`
cover all ten populated MTP maps and five initial RNG seeds. All eight route
pairs, first expired room timers, packed positions and resulting RNG match.
Town transitions now initialize those walkers; older saves with disabled
actors initialize them on their first outdoor update. Cinema exit updates the
live actors as well as their saved room pairs. Arena theft clears Starport
actors when the escape crosses into the wilderness. NPC collision checks all
party members and the original horizontal mech footprint. Timing against DOS
poll loops and broader paths remain **APPROXIMATE**.

**VERIFIED:** forty-five executions of `07DC:17C6..17EC` confirm that Talk
uses the first waypoint matching BLD flag 13. The previous port incorrectly
required that waypoint to equal the current building entrance. The original
HOSPITAL.BLD explicitly writes category 5 before native action 12, so the
extra restriction rejected every hospital conversation. That original category
is preserved, including its use of the category-5 occupants. An absent matching
waypoint produces the original empty-room response. The new 744-input GAME2
visit waits for a real walker to arrive, walks to the clinic, selects Talk,
receives an original post-invasion reply and returns to the hospital menu.
Every input restores successfully; `native_smoke.py --town-only` passes exact
SDL continuation and pixels. No actor, timer, quest flag or RNG is injected
in this route. `town-npcs-primary.*`, `town-talk-primary.txt` and
`ordinary-hospital-talk.*` retain numeric evidence only.

**Owner-requested encounter constraint:** ordinary MAP2 candidates now exclude
enemy mechs even when an imported save retains active owned mech records.
The four per-bay eligibility draws are retained. Sixty-four RNG contexts with
four active vehicles produce infantry-only Starport forces while permitting
enemy mechs elsewhere. Arena and prison/theft setup are separate; all four
owned/rental arena outcomes and both arena-theft/prison-loss SDL tails pass.
This explicit map guard is not claimed as a newly located original instruction.

**VERIFIED:** `medical-ui-primary.json` records complete original RGB crops for
field treatment, injured cooldown, healthy party and trainee hospital treatment.
The short notices end at row 127: their native height is corrected to 56 pixels.
All four crop hashes pass. These are live original screen observations with
controlled injury/equipment prerequisites, not a complete doctor-grade matrix.
The healthy-with-active-cooldown branch still needs its own measured capture.

Restoring town RNG draws changes later ordinary replay outcomes. Dependent
routes have been regenerated through actual inputs. Arena losses leave weapons
unassigned; wins use computer control. No battle state is forced. The current
fresh ending takes 65,975 inputs and the spy replacement route 50,423.

**PASS:** all 51 regular and ASan/UBSan/LeakSanitizer core suites, the full
historical sanitizer corpus, six arena/prison/theft SDL tails and the new town
arrival/hospital-Talk SDL tail. An older synthetic missing-room test expected
the removed context error; its expectation now follows the primary empty-room
branch. The focused historical rerun passed without repeating the core suites.
