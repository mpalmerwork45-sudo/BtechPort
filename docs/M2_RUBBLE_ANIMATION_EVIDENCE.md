# M2k–M2m: rubble, cadet gates and original animation audit

This extends [M2j](M2_MISSION_EVIDENCE.md). The authority is the supplied
v1.03 executable and original data, with the same EXE/image hashes recorded
there. `Original DOS/` and `UnBattletech/` remain reference inputs.

## Findings before implementation

| Finding | Primary evidence | Confidence |
|---|---|---|
| Second assignment has no elapsed-time result test | `TRAINING.BLD:040E`; original `0FDC:0629`, cases `0678`, `0A0A`, `0C45` | VERIFIED in original bytes and live Wasp success |
| Rubble is tile 80 at one of eight locations, chosen by RNG & 7 | `DS:1632` X = 29,55,53,60,59,48,32,31; `DS:163A` Y = 15,17,24,33,44,46,48,27 | VERIFIED in original bytes |
| Standing beneath the rubble triggers pickup automatically | `0FDC:0A0A`: floor(x/2) in [rubbleX−1,rubbleX], floor(y/2)=rubbleY+1 | VERIFIED in original bytes |
| Locust has an initial snickering pause and cannot pick up the rubble | `DS:1434`, `DS:14EF`; `0FDC:06D5`, `0A69` | VERIFIED in original bytes |
| Other two loan mechs remove the rubble; return restores the underlying map byte | `0FDC:0A84`, `0C45`; success uses original unit-name byte != 'L' | VERIFIED in original bytes |
| Return advances original C61C rank by one, capped at 3, including a Locust failure | `0FDC:0C66–0C79` | VERIFIED in original bytes; broader skill semantics still under audit |
| Second success raises allowance cap to 250 | `TRAINING.BLD:113C`, low-byte alias D33F | VERIFIED in original bytes |
| Third assignment checks whether the player has slept; it then requires weapons combat | `TRAINING.BLD:04F3–05B6`; third case of `0FDC:0629` | VERIFIED in original bytes; launch remains beyond this milestone |
| Rick's invitation is after fifth-assignment success | `TRAINING.BLD:13E8–1674`, recruitment flag 45 | VERIFIED in original bytes; natural reachability requires M3 combat |

No separate carried-object inventory write appears in the noncombat mission
routine. A logical carrying indication represents its local completion flag
and removed map tile; broader mech hand/inventory mechanics remain UNKNOWN.

## ANM audit

The existing reverse engineering located these routines. Our interpretation
and decoder were independently derived from the original image's instructions,
using targeted `objdump -mi8086` slices under ignored `work/m2klm-audit/`.
No GPL implementation was translated or copied.

Original `187F:23EC–245B` expands exactly **3872 XOR bytes** over the previous
frame, initially zero. Positive controls are literal counts; negative controls
repeat one byte; zero introduces a big-endian 16-bit repeat count. A packet
stops at the frame boundary as the original does. Frames contain packed
4-bit pixels, 88×88. The checked independent reader decodes all 22 files,
including binary O21; descriptions of O21 as corrupt text are incorrect.

The 51-byte header contains a NUL-terminated sequence in bytes 0–31, durations
indexed by its letters in bytes 32–49, and a timing scale at byte 50.
Original `0800:1AFD–1C12` consumes one delta per sequence step and waits
`duration[letter] × scale × 3 / 4` units. `173D:0006` and `187F:0B40` show
these units wait for **vertical retrace**, rather than BIOS timer ticks.
VGA playback writes the image at (8,8), via `187F:1E37`; other adapter paths
are outside the current frontend.

`0800:48B7–4CAC` repeats O8's ABC sequence seven times. Mission launch calls
O0 with parameter zero (`1CD3:00AC`), adding a 50-unit first-frame hold and
60-unit final hold. Its dispatcher draws one random number even for forced
playback. Barracks `EA 08 01` must finish before the following wake-up text;
the previous interpreter merely recorded that request.

`tools/anm_audit.py` is the independent bounded reader. The read-only observer
in `tools/reference_session.py` compares stable original RAM frame hashes and
consumed offsets while ordinary keyboard input drives the game. All RAM,
screenshots and decoded pixels stay in ignored `work/`; committed fixtures
contain only numeric observations and hashes.

## Completed verification

The unpatched original run at `work/reference-runs/1791705480602565515`
uses ordinary keyboard inputs: first Locust success, outdoor cooldown, second
Wasp mission at rubble (55,17), pickup, return/250-cap reward, tired refusal,
barracks sleep/O8 dream and rested third briefing/mech menu. It contains
181 checkpoints. Later stationary-target combat is outside this milestone.
No separate live Locust rubble run was performed; its no-hands branch is
established from the instructions above and independent C tests across every
objective/mech combination, not claimed as a live observation.

`tools/verify_m2kl.py` compares positions, flags, cash/cap, equipment, skills,
mech ranks, menu memory, quiz state, objective/tile, gait/terrain and exact
original text hashes. **Three explicit original RNG prerequisites** at later
quiz introductions condition this comparison. The compressed native schedule
packs outdoor idle intervals before movement, changing some NPC arrivals and
one subsequent random draw. Full unseeded original/native NPC/RNG parity
across these long waits remains UNKNOWN. No position, money, story, skill,
mission or NPC field is overwritten to satisfy the comparison. The fixture
records these seeds and the verification output names its conditioned scope.

Original pauses also normalize two pickup inputs: an early Return discarded
by DOS maps to idle; the first Down used solely to dismiss pickup maps to
accept. Outdoor-counter intervals and cutscene retrace waits are explicit.
This does not establish DOS CPU/key-buffer timing. The original wake screen
retains `BARRACKS:0A11` and appends `0A85`; playback now preserves both text
spans rather than clearing the preceding text.

A distinct `ordinary-rubble-story.actions` fixture runs **3940 ordinary native
inputs with no state/RNG edits**, selecting the actual native objective (29,15),
completing both missions and reaching the tired/sleep/rested-third gates.
`tools/make_training_replay.py` verifies its quest outcomes. Its original quiz
answers derive from the ten-word EXE table at DS:28EC; route generation follows
actual loaded MAP1 collision bytes. It is a playability test, not a substitute
for the conditioned original comparison.

All **100 fresh-process phase/animation checkpoints** restore and continue
identically. The C training suite has **17269 assertions**, covering all
8×3 rubble/mech cases, early return, no-hands failure, carried tile cleanup,
no second-mission timeout, rank saturation, rest gates, invalid saves and
per-tick state restoration. Disk tests cover 175 replay snapshots/current
file integrity and every input's continuation. Earlier 325 M2j observations
still pass with cutscene waits added; source facts remain unchanged.

## ANM, original font and borders

The C decoder (`port/data/anm.c`) matches the independent Python reader for
**198 packed frames across all 22 original files**. Read-only original RAM
polling captured **18 O0 launch frames and 21 O8 dream frames** with exact
packed hashes and consumed offsets. Polls straddling a buffer/index update are
excluded only when their two observed indexes disagree; raw captures remain
unchanged. Fixtures contain hashes/numbers, not artwork or text.

Original VGA retrace durations map to a 70Hz fractional clock on 32ms logical
ticks: O0's 200 retraces take 90 ticks, and seven O8 ABC passes total 147
retraces/66 ticks. Fixed-clock pacing and omitted decode cost are APPROXIMATE.
Input is blocked during playback and interrupted frames/cycles/holds resume
through saves. Only O0/O8 dispatch contexts are implemented; other files being
parseable does not make their story events supported. Audio remains absent.

The original 256×8 font is at unpacked-image **26D21**; VGA glyph dispatch is
`187F:2251`. All 2048 extracted bytes match live original RAM. Its SHA-256 is
`125fd9b6bdf67fa65233193822f18fba970a0eec3bc8228309098ee6eef75fb2`.
The ignored BTT6 cache stores 87 strings and this font (4937 bytes total), with
source addresses/hashes. Mixed-case text uses 8×8 cells and independent 25-column
wrapping; remaining layout is approximate.

`BTBORDER.CMP` stores nine 8×8 cells across the first eight rows at x=8×index,
with decoded pitch 320. Cells 0/1 are top corners, 2/3 middle junctions, 4 the
horizontal edge, 5 the vertical edge, and 6/7 bottom corners. The left frame
is 13×25 cells with a middle divider at y=96; a building's right frame is
27×25 cells starting at x=104. Outdoor map view is unframed. All **183 frame
cells match original screenshot RGB hashes**, including black margins. Entry
popup text begins at (112,80); Yes/No at (112,96)/(144,96), inside the frame.
Pixel assertions check complete glyphs for all eight entrances/both selections.

The final dream crop at (8,8), 88×88, matches **all 7744 original RGB pixels**.
Its palette maps source index 1 to black, matching original observations;
using the terrain palette incorrectly colored 640 pixels dark blue. This
pixel comparison supplements packed-frame equality; broader ANM palettes,
full screens, movement-history/rank bars and other graphics modes remain open.

## Native checks, speed and persistence

Native SDL tests compare full action records, final JSON and frame bytes with
headless replays for arrival, shops, bank/Talk/editor, classes, all M2j routes
and the new ordinary two-mission/rest route. Replays use `--smoke-fast`:
one logical 32ms tick, input poll and rendered frame per iteration, without
normal wall-clock waiting. The 3945-tick route measured **3.63 seconds versus
126.24 seconds** at normal tick duration, approximately 35× faster for this
test. Later full-suite measurement was 3.68 seconds. Gameplay remains normally
paced; short real-key/animation/F5/F9 probes remain real-time. Real F5/F9
restores launch, rubble pickup/carrying and dream states with exact continuation.

Current BTPC/version 12 saves use 512 payload bytes plus the 16-byte BTS1
envelope. Bytes 434–440 retain rubble and rank/checkpoint state introduced in
BTPB/v11; 441–449 hold cutscene context/frame/cycle/hold/retrace fraction;
450–511 remain zero. BTP1–BTPB migrations are validated; v10/v11 first-mission
saves retain their original post-launch context with no active animation.
Original GAME compatibility is not implemented.

Full headless regression, native window checks and ASan/UBSan/LeakSanitizer
pass. Neither SDL/backend nor full campaign behavior is sanitizer coverage.
Both references retain their guarded baseline; proprietary assets/captures
stay ignored and no substantial GPL code was translated into the C runtime.
