# M2i — authentic sprites, 2026-10-11

The user requested original player, NPC and mech sprites. The bounded addition
uses `MECHSHAP.CMP` directly, through the existing independent C decoder. No
reference PNG, C# implementation or proprietary asset is committed. `ANIMATE.ICN`
contains terrain animation; the previous assumption that it supplied walking
characters was wrong.

## Primary evidence

Executable: audited DOS v1.03 `BTECH.EXE`, SHA-256
`15a1712682cf1fe50ca9e6a68a4b31d3bef7912401915edf7bb6242be193562a`.
Unpacked image SHA-256
`100f0df244e4b0c8693d1b5013fb073f486b35d6f5c538ecd53d03f85ed54bfa`.
`MECHSHAP.CMP` is 16918 bytes, format 2 (320×200), SHA-256
`861545376ecff306fecf960cfb61f931dda61a640ec1c9f417a4a5108e5edc05`.
Addresses below refer to that unpacked image; Reko addresses subtract loaded
segment base `0800` before conversion. Primary `objdump -mi8086` output is kept
locally under `work/sprite-audit/`.

| Finding | Evidence | Confidence / limit |
|---|---|---|
| 376 atlas rectangles | Primary `567B..5AA1` (`0D27:040B..0831`), extraction `17ADA` (`1F3D:070A`); original allocated sprite headers/pixels | **VERIFIED**: every crop matches RAM, 45472 indexed pixels total |
| Sprite format | Far pointer table at state `39FA+4*id`; header byte 1 is height−1, byte 2 width/8, then four bitplanes per group of eight pixels | **VERIFIED** by original RAM and independent CMP decoding |
| Transparency | VGA blitter `18B67`, mask from OR of all four planes at `18C81..18C86`; zero is transparent | **VERIFIED** primary instructions; opaque index 1 maps to black on screen |
| Palette | Sprite 1→black, 5→light blue, 9→dark blue; other tested colors use standard EGA | **VERIFIED** for four live Jason crops; full sprite palette across other modes is not claimed |
| Actor selection | `068F..06D4` and `0946..098A`: frame byte at `409A+actor`, unsigned base at `D55E+actor`; player uses actor 4 | **VERIFIED** primary and RAM: Jason base 150, outdoor cadets base 254 |
| Human walking | Eight programs at image `28130..2816F`; dispatcher `1732..17BA`; player update `231D..240B`, NPC update `272F..2781` | **VERIFIED**: four frames per direction, reset on direction change; 30 player checkpoints, including blocked attempts, and 63 uninterrupted NPC frames |
| Placement/order | Original `051B` draws humans before outdoor NPCs. Jason anchor `(208,96)`; NPC anchor adds eight times its displacement from the cursor | **VERIFIED** primary, plus four exact player pixel crops. This also corrects the old markers' horizontal offset |
| Water occlusion | `0665..068F`, `091C..0946`, DS quadrant tables `032E/0332`; remove bottom 2/4 rows on matching shallow/deep water quadrants | **INFERRED implementation** from primary arithmetic and synthetic coverage; no live water-wading trace yet |
| Mech groups | Frames 0–15 and 146–161, all 24×24; primary `34D8..3506` chooses base 0 for the `L` unit record, otherwise 146. Original unit records contain LOCUST at `28170`, COMMANDO at `282E7` | **VERIFIED** crops/base selection; preview labels Locust/Commando. No campaign mech ownership, tactical movement, combat cadence or firing is claimed |

Original directory `work/reference-runs/1791699158003067611/` provides all 30
walking checkpoints and screenshots. Its subsequent requested 12-second wait
exceeded the driver's 10-second per-command bound and was rejected; no frames
from that failed tail are used. The corrected complete script is
`tools/reference-sprites.json`. The separate successful motion run
`1791699253251047269` used `tools/reference-sprite-motion.json` and provides
64 consecutive stable outdoor samples plus the original sprite allocations.
The player remained still; only nearby cadet slot 4 actively walked in this
trace. All eight direction programs are recorded separately. Do not generalize
this capture into live verification of every NPC direction or campaign actor.

The independent verifier reads original dimensions and planar pixels from RAM,
without using the port's atlas rectangle formulas, and commits only their
SHA-256 values and numeric states. Four original screenshots supply hashes for
8×8 Jason crops. The native crops match all 64 pixels in each crop, including
underlying terrain where transparent. This is not whole-screen parity.

## Implementation and persistence

`port/data/sprites.c` defines bounded atlas rectangles. The renderer composites
authentic transparent 8×8 people and 24×24 mechs, clips to the viewport and
retains the original party-before-NPC order. Character walking is simulation
state: directional movement attempts advance Jason; NPC path updates advance
nearby cadets; idle/indoor time does not advance their walking frames. No
wall-clock renderer state affects replay or saving.

`--sprite-preview` opens a diagnostic sheet of all 16 walking frames for each
of the two mech and two human groups, with cycling mech examples. It changes
no campaign ownership. It cannot be combined with gameplay replays, saves,
recording, controlled checkpoints or smoke modes. Escape closes it.

**BTP9** retains the 416-byte payload and BTS1 envelope (432 bytes total).
Bytes 0–393 retain the preceding field layout; byte 394 stores Jason's walking
index (original frame minus 16), bytes 395–402 the eight NPC indices. Values
must be 0–15; bytes 403–415 remain reserved zero. The state JSON adds
`player_sprite` and `npc_sprites` without changing existing fields.

BTP1–BTP8 still load with their existing logical migration rules. They lack
animation history, so migration selects the first frame for the stored facing;
an uninitialized travel baseline initializes NPC animation on first use. This
is an explicit approximation for old saves. BTP9 resumes the exact saved gait.

## Reproduce

```sh
./scripts/build.sh
./build/btech-port --data "Original DOS"
./build/btech-port --sprite-preview
./build/btech-headless --sprite-preview --frame work/sprites.ppm
python3 tools/verify_sprites.py
python3 tools/native_smoke.py --sprites-only
./scripts/test.sh
./scripts/test-sanitize.sh
python3 tools/reference_session.py --script tools/reference-sprites.json
python3 tools/reference_session.py --script tools/reference-sprite-motion.json
```

To regenerate the fixture, use `verify_sprites.py --export-atlas-run DIRECTORY
--export-walk-run DIRECTORY`. These must contain the corresponding motion and
walking snapshots. Normal verification needs neither a DOS emulator nor Pillow;
Pillow is used only to export screenshot hashes. `--export-sprites FILE` writes
a local verification stream, `BTSP` followed by 376 width/height/pixel records.
That export contains original pixels and belongs only under ignored `work/`.

Current sprite-specific checks pass: all RAM crops; all walking checkpoints;
four player screenshot crops; 63 NPC frame steps; fresh-process animation
continuation; synthetic bounds, masking, water clipping and legacy migration;
native window rendering matches the recorded headless frame byte for byte;
preview grid/presentation/animation/Escape; and native F5/F9 persistence.
Full regression, eight CTest suites and ASan/UBSan/LeakSanitizer pass. The added
BTP8 migration check also retains earned ranks and the active refusal receipt.
See `TESTING.md`; the native frame and preview were visually inspected.

Remaining visual gaps: original status panel/font/menu geometry, terrain
animation, portraits/ANMs, combat frames and actual mech gameplay. SDL key repeat
and wall-clock pacing remain approximate. Both reference directories stay
immutable.
