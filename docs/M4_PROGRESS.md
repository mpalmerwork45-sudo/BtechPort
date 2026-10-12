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
| M4e: original saves/sound/presentation | Save layout located; original compatibility and further audio not complete |

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
The six supplied originals have that header and length. Full executed
load/save/reload comparisons, preservation of unmodeled bytes and runtime
projection validation remain required before M4e compatibility is claimed.
