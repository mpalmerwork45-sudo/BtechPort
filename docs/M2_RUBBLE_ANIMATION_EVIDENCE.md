# M2k–M2m: rubble, cadet gates and original animation audit

This extends [M2j](M2_MISSION_EVIDENCE.md). The authority is the supplied
v1.03 executable and original data, with the same EXE/image hashes recorded
there. `Original DOS/` and `UnBattletech/` remain reference inputs.

## Findings before implementation

| Finding | Primary evidence | Confidence |
|---|---|---|
| Second assignment has no elapsed-time result test | `TRAINING.BLD:040E`; original `0FDC:0629`, cases `0678`, `0A0A`, `0C45` | VERIFIED in original bytes; live comparison pending |
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

## Verification plan

Run one ordinary first-success → second-success → tired refusal → barracks
dream → rested third-briefing chain, and a bounded alternative Locust case.
Compare positions, flags, reward, C61C rank, pickup tile and text hashes.
Verify native save/restart at the new phases and retain all earlier regression
fixtures. Compare original ANM packed-frame hashes before claiming playback
fidelity. Timing on the fixed 32ms native clock is explicitly APPROXIMATE.
