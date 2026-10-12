# M4a–M4e working evidence — 2026-10-12

Authorized: encounter results/ejection, original party/crew/field effects,
further story and medical services, original cache sequence, original saves and
remaining sound/presentation. Additional request: restore the Space menu,
walking step amount and six load/save slots. Reference trees remain immutable;
owner assets and primary executable/screenshot data stay in ignored work/.

## Acceptance and working order

Additional presentation requirements: original combat opening popups; working
combat sound and graphic outtakes; clean building entry Yes/No; and the original
return-to-base message after completed training combat. These are part of M4e's
presentation checks and must not be silently omitted.

Every increment requires primary comparisons, saved continuation, appropriate
core/native checks and a local commit. Begin with menu/persistence controls,
then use verified late-game save contexts to shorten bounded research. A
late-game original save is an explicit starting prerequisite, not proof of a
whole native campaign route. Final acceptance includes the historical suite,
headless sanitizers, focused SDL checks and reference guard.

| Increment | Current status |
|---|---|
| Space menu and splash correction | Implemented; numeric, pixel, six-slot and native input checks pass |
| M4a: encounter aftermath/ejection | Implemented and committed; 114 executed-primary cases and saved continuations |
| M4b: party/crew/field effects | Implemented and committed; formation, allocation, transfer, medical and technician vectors |
| M4c: next story/town services | Hospital and jail-visitor companion routes implemented; primary effects and every-input saved continuations pass |
| M4d: original cache sequence | Implemented from original GAME1 prerequisite; 530 primary cases and complete input-only ending route pass |
| M4e: original saves/sound/presentation | Original saves, menus, map, inspection and sequential combat presentation pass; further owner fidelity requests remain active |

## Space menu and step amount

**VERIFIED:** original `0000:2C50..2DA7` builds Return, Settings, optional
Allocate, Inspect, Heal, Load, Save and Overhead entries. Allocate is included
when an active owned-mech record exists. `0000:3BD0..3D3F` supplies movement,
combat speed, sound, outtake frequency, quit and cancel settings. Executed
`3C86..3C93` yields movement rates 1, 2 and 4 for selections 0, 1 and 2.
`32B3/35D3` use six slots plus Cancel. The menu is available before the invasion.

Native Space is a distinct logical `menu` action during exploration; it
retains dialogue confirmation elsewhere. One movement input traverses the
chosen number of half-steps and stops at collision or an entrance. Cadet/world
clocks advance once per logical input. Existing one-step routes remain covered.
Inspection works before and after recruitment, with the selected shop recipient
retained. The overhead view pans without moving the party. Sound, speed and
outtake choices persist; wider speed/outtake presentation dispatch is being
connected during M4e. Field healing and complete crew allocation are M4b work.

Six native save files are written through the existing atomic length/CRC save
system. Slot One retains `work/player-save.btp`; Two–Six use
`work/player-save-2.btp` through `work/player-save-6.btp`. A custom `--save-file`
base follows the same suffix rule. F5/F9 use the selected slot. Menu load/save
operations are recorded as logical actions and replay against the same initial
slot context; quick F9 remains unavailable while recording.

Internal **BTPJ/v19** adds menu settings/request/map-view state inside the
existing 16,384-byte payload. v1–v18 saves migrate with one-step, sound-on,
normal-speed defaults. Six original GAME files are still read-only and are
not yet claimed compatible with this internal envelope.

**PASS:** 74 new C checks cover saved menu pages/requests, early Space access,
frozen NPC state, four-step movement stopping at the Citadel entrance, all six
independent save/load files, failed-load preservation and map view. Native SDL
records/replays all 157 inputs through settings, six saves/loads, inspection
and overhead with exact canonical state and final RGB equality. The six files
retain distinct 1/2/4-step settings. Remaining menu layout/cadence is approximate.

## Splash palette correction

**VERIFIED:** fresh original VGA run
`work/reference-runs/1791776933604596833/captures/after-title.png` associates
every BTTITLE.CMP pixel index with its actual displayed RGB value. Index 1 is
black; the terrain mapping incorrectly drew it blue. The title now uses the
observed sprite/title palette and omits the added footer. All **64,000 RGB
pixels** equal the original screenshot, SHA-256
`44b20dc58bce673f4d395ce2256a7eeed985af413f757dcc5ffce2750a5dc02d`.
Only palette values, source identity and fingerprints enter the fixture;
the screenshot and original title artwork remain ignored.

## Located original save layout

Primary `0000:368B..3703` writes byte 12, `0F44` bytes starting at
`STATE:C614`, then packed cursor words from `BUFFER:A44B/A44D`: **3,913 bytes**.
The six supplied originals have that header and length. The subsequent
compatibility increment below verifies their exact codec and bounded native
projection while preserving unmodeled bytes.

### Original save compatibility increment

**VERIFIED:** independently implemented original format-12 reader/writer.
`--load` accepts all six supplied GAME files; `--export-original` writes an
imported original after returning outdoors. All **3,913 bytes** of each
unchanged import/export match exactly. Executed original reader
`0000:334F..33D8` and writer `368B..3710` accept and reproduce all six through
private, memory-backed DOS file services. Instructions and reference files are
unmodified. Only source hashes and numeric read/write sizes are committed.

Native original imports preserve character records, active/stored mech
records, story flags, cash/accounts, cursor and NPC building occupancy.
Unmodeled bytes are preserved in an opaque original envelope. Stored mech
types come from original `D452..D455`, distinct from active record tags.
The supplied first two saves equip Jason with weapon 13; the old native
validator's limit 11 incorrectly rejected them. Supplied late saves also
contain skill 5. These values are now retained, including partial armour.
Jason's existing mounted slot is preserved when syncing the party.

**PASS:** 23,766 C assertions cover six byte-exact roundtrips, native save/reopen,
saved next-input continuation, exact changes to the modeled cash field,
atomic private exports and malformed-load destination preservation. All
36 regular and sanitizer CTest suites pass. All six native SDL import,
inspection, save/reopen and export checks pass with exact input/state/pixels.
Original GAME contains no RNG or sound playback state;
imports use a documented deterministic RNG prerequisite and reconstruct NPC
positions. These aspects are **APPROXIMATE**, and full DOS gameplay/load UI
parity is not claimed. Fresh native games continue to use native BTS1 saves;
original export requires an imported envelope so unknown fields are preserved.

Internal **BTPL/v21** keeps the 16,384-byte payload and v1–v20 migrations.
The original initialized 100-byte story window is retained: extra flag/checkpoint
bytes 64..99 at 11424..11495; original bytes at 11500..15412; presence at 15413.
BLD support remains explicit; retaining later flags alone does not implement
the cache or remaining story handlers.

## Combat presentation increment

**VERIFIED:** the original Control, Messages and Graphics lower-left panels,
plus the training building entrance crop, match native RGB pixels exactly.
`tests/fixtures/popup-pixels.json` records the four crops and fingerprints.
The entry prompt contains only the original question, building name and Yes/No.
The added help footer has been removed. Mixed-case font and original borders
are retained. These crop comparisons do not claim whole-screen combat parity.

**VERIFIED:** `103B:0D6D..0DA5` prints original `DS:398B` after training
combat and waits for a key. The native mission enters a saved Return phase,
 shows “You should return to base now” in original window 7, then
accepts Enter/Space before driving back for the instructor's report. Victory,
withdrawal and defeat paths retain their distinct instructor results. The
invasion follows its separate original branch.

Primary `12E8:12C7..1B1C` and `0D39` call original combat impact/fire/topple
outtakes. The reference note claiming no combat ANM calls is contradicted by
these executable instructions. Original `0000:4900..494D` draws RNG even
when an outtake is skipped. All **990 executed cases** match the native
frequency masks 3/15/63 and forced-kind rules, including the *non-forced*
kind-16 and kind-7 cases. Frame artwork comes from the existing independently
verified 22-file/198-frame ANM decoder. Native combat freezes during the saved
cutscene and restores the battle view afterwards. Injury/ejection outtakes
remain part of M4a's further outcome work.

**VERIFIED:** all 18 original PC-speaker programs at `DS:5008`, dispatched
by `0000:19BF` / physical `17C5:0002`, match native pitch-write fingerprints
and speaker noise-toggle counts. The original noise helper receives the same
explicit seed each time; it must not be treated as an evolving game RNG.
Every effect has tested PCM continuation across save/reload. **APPROXIMATE:**
busy-loop duration, host filtering/volume and ordering of simultaneously
queued presentations. The original animation files contain no sound stream;
the relevant firing/impact sounds occur before their outtake calls. The native
SDL audio report confirms an opened dummy device and 4,096 nonzero queued
samples for a real ordinary-input combat checkpoint.

New **BTPK/v20** stores the sound queue/playback and combat outtake queue at
11326..11387, leaving the payload/file sizes unchanged. BTT7 contains 91
original strings (5,084 bytes); BTC7 adds the original numeric speaker programs.
Fresh games use the original observed outtake default 0. v19 retains its saved
choice; older saves receive original defaults. Ordinary-input combat routes
are regenerated because the newly restored original RNG draws legitimately
change subsequent combat. The graphics-independent full-state assertion from
M3 is superseded by these primary comparisons.

Focused native presentation checks seed checkpoints with ordinary inputs and
compare recorded SDL input, complete final state and final pixels against
headless replay. Entry, combat Control, firing sound, combat outtake and
Return all pass. `--audio-report` is a diagnostic file option, not popup text.
**PASS:** all 35 CTest suites, the complete historical original-data/replay
suite and full headless ASan/UBSan/LeakSanitizer suite. The regular CTest pass
takes 4.83s; the sanitizer CTest pass takes 13.92s on this host. Historical
NPC/bank/school oracle setups now explicitly include the restored default
menu settings. Their original numeric projections are unchanged. The native
Space event is resolved when consumed, so batched keys correctly confirm
dialogue after entering a building. Both reference trees pass the 1,287-entry
content/mode/mtime guard. No public asset files or pushes are involved.

## Encounter aftermath increment

**VERIFIED numeric rules:** 114 executions of original cash span
`05AB:09EC..0A11`, salvage qualification `05AD..05E1`, recovery copy
`06E2..07AD`, and complete ejection `0D43:0A35`. Pocket cash is the sum of
one `(RNG & 15)+3` draw per marked enemy soldier, with a minimum of 2.
Critical head, reactor or gyro damage requires technician rank 4 for recovery.
Recovery copies bytes 1..124, restores the original type, assigns the selected
pilot and repairs the original minimum critical/structure bytes. Ejection
puts both surviving crew on foot at the wreck and the adjacent half-step,
without a random draw. The original classifier's overlapping owned-mech
byte read is retained, not silently corrected.

General combat now preserves wreck identities and inserts surviving crew
with stable original unit IDs after presentation finishes. Losing a friendly
mech no longer ends a battle when crew survive. Jason's death enters a saved
terminal loss state; other character losses remain in the party result.
`103B:0BFC..0C51` gates salvage on a marked mech loss, a qualified pilot on
foot, an empty owned record and no populated neighboring terrain. Salvage,
recovered cash and weapon recipient choices are saved continuations. Loot is
applied once, including after withdrawal. The original corpse-slot behavior
when a salvage scan encounters a human marker is not established; the native
flow rejects that candidate visibly. Loss/aftermath panel geometry, timing,
and character injury inside a surviving mech remain **APPROXIMATE/UNKNOWN**.
These are not claims of a complete original campaign.

Internal **BTPM/v22** uses the existing reserved payload for aftermath,
17 additional effect records and 24 additional queued speaker effects.
All v1–v21 migrations remain supported. Full party combat can present up to
24 shots per microstep and 48 firing/impact sounds. Campaign tests now use
separate scratch save filenames: concurrent CTest runs previously collided on
`work/campaign-test.btp`.

**PASS:** 416 assertions, all 114 primary vectors, saved ejection/salvage/loss
and exact resumed continuation. All 37 CTest suites pass; headless sanitizer
suites pass. The SDL saved-result test uses an explicit controlled prerequisite,
not an asserted ordinary-input campaign route.

## Crew, formation and field effects increment

**VERIFIED:** another 146 primary numeric cases cover all 24 medical
skill/equipment programs with three RNG prerequisites, 32 crew replacement
cases, all 12 encounter formation positions and 30 technician recovery cases.
`0C31:01BC..0207` adds the original die-program result to each injured living
character and caps it at body × 10. `0C67:067F..0873` removes previous seating,
evicts a passenger or moves the replaced pilot to the passenger seat, and
writes the new mount/seat consistently. These spans require the original
small-model DS=SS relationship for indexed stack-local arrays; the oracle
sets that caller prerequisite without modifying instructions.

Space allocation handles all four active owned records and eight people,
qualified pilots, passengers, foot travel, pilot replacement and the original
unpiloted-mech completion/abandonment conditions. Encounter positions use
`DS:3A16..3A2D`, rather than guessed offsets. The camera follows the selected
friendly unit and outdoor rendering uses Jason's actual mounted record and
omits duplicate passenger mech sprites. Existing primary movement/collision
fixtures remain covered. Outdoor party following remains the documented
**APPROXIMATE** trail; complete outdoor formation/cadence is not asserted.

Field healing uses the best living medic, original `DS:2602` programs, Field
Medical Kit `D450`, and advanced kit `D451`. Earlier secondary notes call
those bytes training flags; executed `14D3:0DC2/0DCF` and their medical
callers contradict that label. `D335` stores the original 63-count cooldown.
Native world-clock cadence remains approximate. Kit bytes and owned-mech
positions occupy reserved bytes in each 1,024-byte party block; original
imports/exports retain both medical flags. Internal **BTPN/v23** retains all
older versions and payload size. Up/Down on a party inspection opens the
bounded equipment-giving menu; weapon and partial-armour records move to the
chosen member. This convenience's layout is **APPROXIMATE**, while the modeled
record changes are explicit and saved.

`05AB:00C7..042A` recovers armour, internal structure (technician rank 4),
working heat sinks (rank 2) and weapon components (rank 3) from enemy wrecks.
Original `103B:273D` checks the associated surviving structure. Recovery
restores surviving owned records before mech salvage. Its cash formula uses
the selected technician's **party slot**, not rank: the native implementation
preserves this unusual executed rule. All 30 record fingerprints and RNG
results match. No guessed repair chance is added.

**PASS:** 4,329 party/field checks; 89 menu assertions, saved multi-mech
allocation, equipment transfer, medical treatment/cooldown and all six exact
original-save roundtrips. All 37 regular CTest suites pass. The focused SDL
original-save prerequisite, equipment and field-treatment flow matches full
headless state and pixels. Historical bounds tests now reject index 100;
the verified 100-byte initialized story window supports later script flags.

## Additional owner acceptance requirements (active, not yet verified)

- Space menu must match the original presentation.
- Character inspection must match its formatting and UNSKILLED–EXCELLENT labels.
- Party selectors list only present characters, with no empty-slot rows.
- Infocom/Westwood intro precedes BattleTech title and dismisses with Space.
- Two/four-step travel advances character animation by one frame per input.
- Mech test highlights the selected part as the original did.
- Mech-start animation plays its original startup sound.
- Overhead map reveals explored terrain and uses original TINYLAND graphics.

These supplement the five authorized increments; none is implied complete by
existing core checks or the corrected BattleTech title palette.

Further owner requirements during the active work:
- Generated landscape must render beyond local city edges, with authentic city overlays.
- Shift-held K, Y, R credits 10,000 even in intro; plain Escape never quits; Ctrl+Shift+Escape quits.
- Combat speaker effects must match original playback at an 8 MHz XT, replacing approximate busy-loop durations.
- Return-to-base message must match the original popup presentation.

## Intro, inspection, overhead and computer-control increment

**VERIFIED:** fresh DOS captures supply the full logo RGB fingerprint, both
seven/eight-row Space-menu crops, the six-slot list and character-inspection
crop. Original rank labels, health, armour and equipment labels use the owner's
EXE text/font cache. Party selectors are compact and retain physical member
identity. Two/four-step walking advances the gait once per input. The selected
mech quiz component now has the original white horizontal connector.

The intro displays INFOCOM.CMP, then BTTITLE.CMP and music. The owner-requested
question asks whether the player has played before: Yes opens the six slots;
No begins training. This wording reverses the original's first-time question.
Shift-held K/Y/R credits 10,000 in every mode; Escape cancels and
Ctrl+Shift+Escape exits. These are explicit owner variations.

**VERIFIED numeric presentation:** eighteen executions of `05AB:1AFE` and its
bar/component helpers establish the mech inspection's complete left RGB
projection and every filled right-panel pixel. Original BTSTATS.CMP supplies
the diagram, with original damage indicators, armament locations and heat
bar. Combat Scan and mounted-character Left/Right open this display; the latter
navigation and heat blinking cadence are **APPROXIMATE**. These comparisons
intercept graphics boundaries and do not claim full DOS screenshot equality.

**VERIFIED:** 130 executions of `0000:010B..020A` match all 2,048 fog bytes;
144 executions of `187F:1F04` match mini tile selection. Fresh DOS first-time
RAM reveals only the familiar Citadel rows 98..103, byte 12=31. TINYLAND.CMP
supplies the original overhead terrain, and the original colour LUT builds
stored-town overlays. Rick's device displays the original directional glyph
toward Starport and hides it in Starport's sector. Local city edges continue
into the independently generated landscape. Whole-map pixels, cursor flashing
and pan cadence remain **APPROXIMATE**.

Startup queues original effect 12 after its last frame and holds until it
finishes, before asking about computer control. Original return window 7 is
the centred `(104,72,216,56)` popup. Mech impacts retain mech walking frames;
human hit-reaction offsets no longer index into the alternate mech atlas.

Automatic control uses the verified combat planner for friendly units. The
third mission permits its opening question; subsequent training skips it as
original `07DC:0765..07ED` does. The combat menu can override that restriction,
as the owner requested; the original menu itself gates the option. Space pauses
automatic turns safely during effects, and orders/automatic bits survive saves.
A saved-continuation integration test lets the Locust defeat the stationary
shell without manual orders. Combat-speed settings now affect turn delays;
host tick conversion remains **APPROXIMATE**.

**INFERRED nominal 8 MHz 8088 sound profile:** original loop paths execute
unchanged and use Intel's 1979 instruction timings, including taken/exited
branches and word-memory penalties. Twenty boundary cases match the native
busy-loop converter. Calibration 2 replaces the old arbitrary two-PIT-clock
delay estimate. Noise call counts and all eighteen pitch programs retain their
executed comparisons. Prefetch, interrupts, speaker filtering and actual XT
hardware output remain **APPROXIMATE**; no hardware waveform parity is claimed.
The manual source is Intel's *8086 Family User's Manual*, 9800722-03,
tables 2-20/2-21, kept locally under ignored work/ with the primary citation
in `tests/fixtures/speaker-timing.json`.

Title rests use the original divisor 14, an ultrasonic carrier. Its PCM output
is now silent while original PIT/IRQ timing continues, eliminating host-rate
aliasing. Zero output, chunked rendering, no-output advancement and saved PCM
continuation are tested. This fix is committed separately as `9099c31`.

Internal **BTPP/v25** expands to 20,480 bytes; v18..v24 remain 16,384-byte
decoders. Fog occupies 16384..18431, intro-load origin is byte 18432, and
automatic-control fields use previously reserved combat bytes 10234..10239.
Old compact-selection migration preserves member identity. Runtime caches are
BTT9 (119 strings), BTC9 (eight medical ranks) and BTW3 (mini colour LUT).

**PASS:** 39 core suites, 40 original hospital effects, eighteen mech-view
cases, 274 world-view cases, all six original-save roundtrips and the native
intro/popup/audio checks. The 157-input native menu check includes real F5/F9
while character, mech and overhead screens are open, with exact continued
state and RGB equality. M4c/M4d remain active and final batch acceptance is
still pending.

## Sequential combat sound, Space selection and later services

**VERIFIED saved sequencing:** each graphical attack waits for its firing
sound, presents its attack, waits for the impact sound, then shows its impact
and selected outtake. The next attack and battle result wait for this sequence.
Original outtake RNG decisions remain at their numeric calculation points;
changing presentation does not reorder those draws. A controlled three-attack
regression compares every encoded save and subsequent PCM chunk, checks that
only one combat clip is queued and verifies silent Return-to-base completion.
Native firing queues 44,468 nonzero PCM samples; Return queues none. The SDL
buffer is bounded to three logical audio ticks (96 ms), so a window stall cannot
accumulate seconds of delayed sound. Device latency/filtering is approximate;
BLD script effects outside combat still use their existing queue.

**VERIFIED input and visible map:** Space previously closed the actions menu
instead of selecting its item. It now confirms the highlighted item, like Enter.
The shared renderer handles the overhead page directly. Real X11 Space keys
select Settings, Movement rate, Two steps and Show Overhead Map. Screen capture
checks the presented SDL pixels, including 2,302 visible terrain pixels at the
Citadel start and 45,056 in the original GAME3 context. F5/F9 restores the visible
map. A 40-by-48 Citadel terrain crop matches the original overhead capture;
the blinking cursor and full-world pixel parity remain outside that claim.

**VERIFIED bounded M4c integration:** ordinary-services inputs continue to the
MAP4 hospital, locate its records, recruit the medical companion and buy both
kits, then reach the MAP3 jail visitor and recruit its companion. The routes
contain 51,207 and 52,319 actions respectively, including the authorized
10,000-credit shortcut. Every input survives an encoded-save restart and has
an identical next-input result. These are input histories, not edited saves or
RNG payloads. The original generic companion naming order is retained. The
existing 40 primary hospital numeric cases and 170 medical cases cover training,
kit and healing calculations. Empty active mech records now use the original
255 tag, preventing nonexistent mechs after garage checkout.

The optional jail impound-yard action 40 remains an explicit unsupported
handler; the verified visitor route chooses No to that branch. Timed NPC/spy
checks retain their existing bounded cases; complete long-campaign timing is
not claimed. M4d cache work and full batch acceptance remain in progress.

Internal **BTPQ/v26** stores story allocation context at 18433, effect stage at
18434, and per-attack outtake decisions at 18435..18482. v25 and older saves
migrate explicitly; legacy active attacks drain their old audio without
replaying new firing clips. CLI continuation comparisons now include an FNV-64
fingerprint of the entire encoded state, as well as character and mech records.

## Original cache and ending increment

**VERIFIED numeric rules:** 530 executions of unchanged original instructions
at 0B5D:03AA, 0AB6, 01E9, 0913 and 0980 match all terminal code updates,
door flags and final map tiles, consumed terminals, the secret passage,
symbol toggles, every subset of the seven-symbol password and rejection reset.
Only UI, sound and redraw call boundaries are intercepted. Fixtures retain
numeric fingerprints and source identities; original text and artwork remain
owner-loaded resources.

**VERIFIED bounded integration:** the original GAME1 late-game prerequisite
travels normally to the cache entrance, reads ENTRANCE/INSTRUCT, opens all
eleven security doors, discovers the secret hallway, views ENDMECH.CMP,
enters MAP15, submits a rejected then correct password, activates the HPG,
finds the cache and plays the five WINSCENE animations. All 10,936 ordinary
inputs restore and continue identically before every action. The cache test
contains 47,676 assertions. The supplied prerequisite already has the earlier
disk/password and trained-party flags; this is not a proof of a fresh native
campaign through those prerequisites.

MAP14 is the original 64x64 facility; headerless MAP15 is the separate 32x24
chunk-map puzzle. STARLEAG.ICN and MAP.ICN supply their art. Original code IDs
59..61, white code 62, Phoenix visit 63, power 64, discovery 65, room 66 and
doors 67..78 are retained. The Phoenix encounter is a display/story event;
it does not grant a fictional owned mech. Main-room movement respects the
step setting; the puzzle remains single step. Cache overhead uses the original
alternate mini-colour LUTs. Whole-cache pixel geometry/palette and door cadence
remain **APPROXIMATE**, despite using original maps, graphics, texts and flags.

**PASS:** native SDL saved continuations for terminal Yes/No, door opening,
Phoenix, map room, white code and ending; real F5/F9 restores both map-room and
Phoenix displays with exact native/headless state, clock and final RGB pixels.
All 40 regular and sanitizer core suites, the full historical regression,
headless ASan/UBSan/LeakSanitizer and focused native acceptance pass. The old
migration checks now explicitly distinguish fields absent from legacy saves:
prior explored-map history cannot be recovered from BTP7/8/10/11, while their
existing gameplay fields and course progress remain checked. Normal current
save/load compares the entire serialized-state fingerprint.

**VERIFIED paid clinic integration:** an explicit injured GAME2 party reaches
the Starport hospital through 77 ordinary inputs, including the authorized
credit shortcut. Choosing doctor level four charges 25 credits at reception
and 400 for the doctor, heals Rex from 108 to 120, and returns outdoors with
9,666 credits. Every action restores identically; its native SDL tail passes.
This complements the earlier original medical-effect/dice comparisons.

Internal **BTPR/v27** preserves the 20,480-byte payload. Cache state occupies
18483..19291: interaction phase, used terminals, hallway and mutable MAP15
cells. Previous save versions migrate explicitly. BTTA/v10 supplies 141
original strings; BTCA/v10 adds cache code/door/password and mini-colour tables.
Build and playback require no emulator. The two reference directories pass
all 1,287 content/mode/mtime checks. No assets or original code enter Git.

Further owner requests after this acceptance add Starport assignment, invasion
messages/map switch, withdrawal and encounter descriptions, direction display,
prison/Starport theft, hut/cinema/laser-shop/house routes and a fresh sound audit.
These are active follow-up work, not covered by the cache acceptance claim.
# Campaign follow-ups — native v28

The garage now opens the original scripted crew allocator during checkout
(14D3:0E2C → 0C67:0002); the hospital route explicitly assigns Rex before
leaving. The final training fight shows the uneasy-feeling popup, the five
DS:3A2E invasion messages and O2, switching to MAP11/DESTRUCT.ICN after the
third message while combat is still active. The original menu Flee refusal
and walking escape remain distinct. Both escape and defeat input routes
continue after a save at every input.

The mayor's house has its three original newspaper/holodisk/chow choices.
THEATER.BLD runs its original films and explicit sounds; WEAPON2.BLD runs
the robbery, laser gifts and recipient/displaced-weapon menu. Original
native 47's meal health loss and native 41's health cap are preserved.
The inventor's hut uses the original party skill gates: recorded routes
cover rejection and password success. The latter imports GAME5 and uses
ordinary allocation to take the crew out of that save's malformed fourth
vehicle before travelling; it does not edit prerequisite flags or ranks.

`late-story-primary.txt` contains 46 executed original comparisons for
weapon distribution, exact RNG/health, meal boundaries and the cinema exit.
Seven additional original-save input routes cover the requested buildings.
The travel direction log is saved independently of movement step size.
BLD E4 sound calls now suspend the script until playback completes.
Popup placement, portrait timing and physical speaker response remain
**APPROXIMATE**. Prison/arena theft and the further sound playback audit are
still in progress; these follow-ups are not a complete-campaign claim.

Verification for this follow-up commit: all 41 regular and sanitizer core
tests pass. The new building routes restore state before every input. Native
window checks for these additional routes will run with the theft follow-up.
