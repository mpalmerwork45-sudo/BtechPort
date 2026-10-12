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
| M4a: encounter aftermath/ejection | Primary audit in progress |
| M4b: party/crew/field effects | Primary audit in progress; allocation/field healing remain bounded or unavailable |
| M4c: next story/town services | Not complete |
| M4d: original cache sequence | Not complete |
| M4e: original saves/sound/presentation | Combat presentation tested; six original save roundtrips and native continuations implemented |

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
shows “You should return to base now” in the lower-left text panel, then
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
