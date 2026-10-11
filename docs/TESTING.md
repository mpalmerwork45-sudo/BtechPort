# Build, verification and original oracle — M2a, 2026-10-11

## Native commands

Run from `/home/mpalmer/BtechPort`:

```sh
./scripts/build.sh
./build/btech-port --data "Original DOS"
./build/btech-port --data "Original DOS" --replay tests/fixtures/citadel-hall.actions
./scripts/test.sh
./scripts/test-sanitize.sh
```

The build script selects the installed host GCC 15.2/CMake and clears inherited Conda compiler/linker flags for its child commands. A direct build with the current shell's Conda `ld` fails on the host libc's `.relr.dyn`; no shell or Git configuration is altered to fix this. It produces `build/btech-port`, `build/btech-headless`, `build/btp-tests` and `build/btp-script-tests`. No network access is needed for the current build.

SDL2 2.32.4 runtime is installed, and development headers are extracted under `local-deps/sdl2/`. CMake also supports a conventional SDL2 development installation; SDL2 must provide `SDL_GetTicks64` (2.0.18 or later). On a machine with normal compiler environment:

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build
```

The same core/data/pixel tests build without SDL using `-DBTP_FRONTEND=OFF`. Windows portability is a design goal, **UNKNOWN** until an actual Windows build is tested. C11 code, explicit little-endian serializers and CMake avoid a Linux dependency in the core.

Arrows move/select; Enter or Space confirms/continues; Backspace declines entry or recovers unsupported choices; F3 toggles collision outlines and mode/script diagnostics; R restarts; Esc quits. The native tick is fixed at 32ms; key repeat, original delays and input flushing are **APPROXIMATE**. Deterministic replay accepts lowercase logical actions `up`, `down`, `left`, `right`, `idle`, `accept`, `cancel`, one per line:

```sh
./build/btech-port --data "Original DOS" --record work/my-walk.actions
./build/btech-headless --data "Original DOS" --replay work/my-walk.actions --trace --frame work/my-walk.ppm
```

Recording includes idle ticks. Restart is visibly refused during recording because reset is not a supported replay action. Unknown actions fail with a diagnostic. The bounded BLD interpreter supports the Citadel menu, Hall of Legends and exit; other choices stop with the unsupported opcode and payload address. Headless replay returns a failing exit code on script errors and can still write their requested diagnostic frame. Backspace/`cancel` explicitly returns to the menu without invented quest effects.

`BTP2` is a tested 64-byte **internal core encoding**, preserving mode, pending entrance, VM position, text range, pause request, menu choice and 16 state bytes. Legacy 24-byte BTP1 states still decode. Tests restore during entry, every Hall wait, menu, fault and exit and compare subsequent encoded state. This is not an original GAME save feature or a native save/load UI.

## Passed checks and scope

| Check | Actual result | What it establishes |
|---|---|---|
| CTest `core-formats-state-pixels` | PASS, 65 assertions | Literal/signed/long RLE, malformed/truncated/overflow rejection, block boundaries, movement, collision offset, edges, deterministic state restoration, serialization validation, rendering/palette regression. |
| CTest `script-bounds-dispatch` | PASS, 24 synthetic assertions | BLD size/decrypt, truncated operands/text, unsupported operations/font/scene/menu, invalid targets, bounded loops and input wait/selection. |
| `build/btp-tests "Original DOS"` | PASS, 231 assertions including synthetic checks | All 14 MTPs and 12 graphics decode; raw MAP15 rejected; integrated Citadel entry/decline/dialogue/exit and error recovery; exact entrance halves; validated BTP2 restoration and BTP1 migration. |
| `build/btp-script-tests "Original DOS"` | PASS, 47 assertions including synthetic checks | Authentic Citadel menu, all six Hall text ranges/waits, jump-back selection retention, `FF` exit and three explicit unsupported branches. |
| Python unpacker tests | PASS, 3 tests | Synthetic backward repeat/prefix, malformed EXEPACK header/run rejection, actual original unrelocated-image length/hash/anchor. |
| Canonical original replay | PASS, 31 states / 30 actions, all four directions | Native positions/gate match original cursor **and party member 0**, including repeated wall/hedge blocks and west-wall offset. Not a claim about all parties/scenes. |
| Citadel differential projection | PASS, 16 original checkpoints / 20 native states | Cursor/party[0], gate, 16 state bytes, pending step and exit; seven text digests, six waits and retained selection. Original credits stay 35; economy itself is absent from the native core. Modes and text order were checked visually; PC is bytecode-derived. |
| Repeat and unknown input | PASS | Identical replay output is byte-identical; unsupported logical actions fail. |
| Native SDL dummy + private X11 smoke | PASS, movement and Citadel scenarios | Window, queued SDL arrow/confirm events, texture presentation and bounded exit. Recorded movement (8 ticks) and Citadel (24 ticks) inputs replay to the same canonical state. |
| ASan / UBSan / LeakSanitizer | PASS, core/data/pixels/VM + corpus + both canonical replays | No detected address, undefined-behavior or leak errors in those paths. SDL frontend is not sanitizer-tested. LeakSanitizer requires execution outside the ptrace sandbox. |
| Reference guard | PASS, 1287 entries | Both supplied trees match baseline hashes, modes, modification times, directory entries and symlinks; includes reference `.git/`. Access times are intentionally excluded. |

`./scripts/test.sh --x11` adds both private-display native scenarios and closes automatically. Under Codex, GUI processes require approval for the whole script; there is no interactive terminal or per-input approval. Plain `test.sh` uses SDL's dummy driver and needs no display or audio device. Sanitizers cover headless paths, including software rendering through C tests; they do not claim SDL/backend instrumentation.

## Citadel original comparison

[Citadel evidence](M2_CITADEL_EVIDENCE.md) records exact trigger/decrypt/opcode findings and confidence. Run the original and compare the printed run directory:

```sh
python3 tools/reference_session.py --script tools/reference-citadel.json
python3 tools/verify_m2.py --reference-run work/reference-runs/1791682077232453392
```

The input script waits through arrival/text rendering, selects Hall of Legends, advances six screens, selects Leave from the retained Hall highlight, and takes one south step. The verifier compares fresh original cursor **and party[0]**, 16 state bytes, unchanged credits and all 4328 decrypted bytes with the fixture/core. Seven native text digests are checked against the original resource. Snapshot mode labels come from captured screen observations; the verifier does not read an assumed DOS mode enum or claim that VM PC was captured from the live interpreter.

Without DOSBox:

```sh
python3 tools/verify_m2.py
./build/btech-headless --replay tests/fixtures/citadel-hall.actions --trace --frame work/citadel-hall.ppm
```

`--smoke-citadel` feeds a bounded set of logical controls through the native SDL event queue. Its records and screenshots remain in ignored `work/`. Error-branch checks require a failing process exit with `unsupported opcode`; they also verify explicit recovery. This does not establish the other Citadel choices, complete story flags, economy, pixel equality or original timing.

## Original-game reference sequence

Spice86 cannot run with this checkout alone: no dotnet executable, no matching external Spice86 tree, and no prebuilt reference executable. DOSBox 0.74-3 is the practical oracle. It executes an unpatched copy of `BTECH.EXE`, not UnBattletech's runtime.

One-time working copy, if absent:

```sh
mkdir -p work/dos
cp -a "Original DOS/." work/dos/
```

Reference command:

```sh
python3 tools/reference_session.py --script tools/reference-movement.json
```

The script selects `3` for VGA, `3` for hard disk, waits through startup, uses the recorded title/menu keys, then walks the road, the south wall, the hedge and the west wall. Intro/menu inputs remain part of the recorded sequence. Coordinates already exist during the initial question screen; the native slice begins directly at those initialized MAP1 coordinates and omits the original startup menus. This is a scenario fixture, not a claim to reproduce every new-game variable.

Every invocation creates `work/reference-runs/<unique-id>/`: `inputs.jsonl`, DOSBox/Xvfb logs/config, raw 320×200 PNGs, read-only guest-RAM exports, and JSON snapshots. `work/reference-latest.txt` gives the newest directory. The harness owns a private Xvfb display, focuses only its own DOSBox window, does not receive interactive stdin, and terminates both child processes. Files read/mounted by DOSBox are only under `work/dos/`; originals are never mounted writable. Failures stop the script rather than silently accepting absent captures.

To compare a fresh run with the native core and compute the frame report, substitute its printed directory:

```sh
python3 tools/verify_m1.py --reference-run work/reference-runs/1791680299506554032
```

`tools/verify_m1.py` uses Python's standard library for state comparison; Pillow is required only for the optional PNG/pixel report. All 88 original hashes are checked first. Regression fixtures contain only factual coordinates/actions and provenance; proprietary PNGs/RAM/resource bytes are kept out of the fixtures. Before launch, the reference harness also checks working-copy resources against the manifest, excluding mutable GAME saves.

**VERIFIED observations:** initial raw X/Y `0C45:C019` → half coordinates `(69,25)`, nominal cursor tile `(34,12)`; party[0] coordinates agree. Gate `85`; runtime UI selector `2`, narrow-panel value `1`, world-active byte `0`, scene bytes recorded as zero. `w014A` is `1` while movement works; interpreting the harness's historical `suspend` field as a global pause flag is unproven. Credits are `20` at the initial question snapshot and `35` in the later walk snapshot; allowance/timing parity is excluded from M1.

The game image is located using its known unpacked string offset `37A88`, then validated against BIOS data and entry bytes; the load segment in these runs is `01A2`. Common DS is load + `36DB`; the map-buffer DS is load + `1C6C`. Runtime selector pointers resolve state, UI and cursor storage. Reko's load base `0800` and old Spice86 aliases are not used as raw file offsets or native-core addresses. Original MAP1 payload bytes are present at guest offset `1F0FD`. The 24×24 working grid at map DS + `07AD` matches all 576 corresponding MAP1 tile IDs at map region origin `(24,0)` in the recorded start. It is not a tile-property LUT or proof of a static global world.

Cursor tile projection floors both half coordinates. Player collision in the recorded trace instead samples `ceil(x_half/2), floor(y_half/2)`: west moves `68→67` succeed although the nominal cursor enters tile 33, then `67→66` blocks on its wall. Tile ID threshold 85 and this offset rule reproduce the tested route. Generalization to additional scenes, multi-unit footprints and world edges remains **INFERRED/UNKNOWN**; native map edges currently block deliberately.

## Graphics comparison and exact deviations

All 64,000 independently decoded C BTTLTECH pixels match the secondary reference tilesheet under the standard EGA palette. MAP1 uses 16×16 tiles, block-normalized map data, and an observed terrain remap 5→9, 9→1. At the tested start, the original right panel begins at X=104; its map crop origin is `(464,104)` after the first east step, matching camera `x_half*8−96, y_half*8−96`. Native resolution is 320×200, scaled without filtering.

**VERIFIED for that frame:** 42,625 / 43,200 right-panel pixels equal, **98.669%**. The remaining 575 pixels include omitted NPC/sprite overlays and the approximate player marker; their complete causes are not assigned without further tests. The independently drawn left diagnostic panel replaces original status/animation/menu graphics. Whole-screen equality is not claimed. Palette/camera parity for other graphics modes remains **UNKNOWN**.

Remaining differences: no NPCs/followers, campaign quest progression, allowance, shops, encounters, combat, original GAME saves, ANM playback or audio. M2a executes only the verified Citadel subset and reproduces its recorded 16-byte state projection; this is not a complete story-state model. Font/layout, Citadel imagery, tick/repeat/flushing cadence, edge blocking and player marker remain approximate. There is no original Citadel whole-screen pixel-parity claim.

## Dependency provenance

Packages were downloaded through the configured Ubuntu archive with `apt-get download` and extracted with `dpkg-deb -x`; no privileged system package installation or arbitrary remote script was used. Original-game graphics are loaded directly, not copied from the GPL project. Existing GPL tooling was exercised only on copies to audit decoding/round trips.

| Local package | Destination | SHA-256 |
|---|---|---|
| dosbox 0.74-3-5build2 amd64 | `local-deps/dosbox/` | `f7fabe8e4923ec503349f8c7466ab132395e83ba03aa1e382955c09f434c4433` |
| libsdl-net1.2 1.2.8-6build1 amd64 | `local-deps/dosbox/` | `3a060ffbfb07f8046ee78c7211fe67932717bc6a4f52daca9860cd60c3396dd2` |
| libsdl-sound1.2 1.0.3-9build4 amd64 | `local-deps/dosbox/` | `c02bfb7fe9e20189b4c5556f73acab4c1b53594db6ff10dde58d11be0be97d10` |
| libmikmod3 3.3.13-1 amd64 | `local-deps/dosbox/` | `f2b562ffcd8bf90947487ce3ded3363f2afeef0cce07e6732d1b691bb8d297ab` |
| libsdl2-dev 2.32.4+dfsg-1 amd64 | `local-deps/sdl2/` | `90a21699bdb8f6f491b92dba345a85b1ab865c54cd59c527b91603a2d1a13b17` |
| xvfb 2:21.1.18-1ubuntu1.1 amd64 | `local-deps/xvfb/` | `a980a874e0b5663ada7ff1f145ce91b87ba03a40bd5d4fde335bf6d0f1a4ed06` |

The harness supplies a process-local library path for DOSBox's extracted libraries and dummy audio. X11/XTest libraries and fonts were already present. There is no audio device dependency in the slice. These packages are local ignored dependencies, not new implementation source. No new dependencies were needed for M2a.
