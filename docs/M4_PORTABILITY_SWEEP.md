# Cadence, encounters and Windows verification — 2026-10-16

This completes the next five authorized areas within the bounds below. The
original DOS 1.03 executable and data remain the behavioral authority. Original
assets, text, RAM, decoded records and images stay in ignored local files.

## 1. Outdoor cadence

**VERIFIED original requests:** `0000:01F4` waits for one VGA retrace and tests
the countdown initialized to ten at `044A`; eleven idle retraces precede the
next outdoor update. The keyboard path at `002D..003E` performs an update
immediately and restarts the countdown. This agrees with the earlier live
159-transition capture's mean of 156.825 ms.

The port now accumulates 224 hundredths of a retrace per 32 ms tick, with a
threshold of 1,100, using nominal 70 Hz. This avoids repeatedly rounding each
interval to five ticks. NPC movement, recruitment coins, allowances and world
encounters share the corrected rule. A two/four-step movement key still causes
one outdoor update. Tests compare 1,100 ticks against 224 complete frame updates,
including RNG/economy state, input resets and restoration at every tick.

**APPROXIMATE:** wall-clock scheduling and actual VGA/CPU timing. Logical input
replays are not continuous recordings of the DOS keyboard polling loop. The
changed RNG cadence required regenerating ordinary routes and waits, including
quiz answers read from the original question table. No game-state/RNG edits are
used to advance those routes. The fresh-cadet ending route now has 83,339 inputs;
spy removal/replacement has 66,760. Both restore before every input.

## 2. Complete town encounters

**VERIFIED within four added fights:** two Starport infantry victories at
world 1320,1110 (seeds 4/5, seven waves each), and two MAP4 victories at
1180,1434 with three mechs and Rick on foot (seeds 1/42, three waves each).
All 20 waves compare RNG, full record hashes, living positions, facing, heat,
ejection and final results. Original placement, command initialization, AI and
resolution routines execute without instruction patches. GAME3 equipment,
town payloads and each caller prerequisite are recorded in
[the fixture metadata](../tests/fixtures/complete-town-encounters-primary.json).

This found a real damage discrepancy: `12E8:02C3` passes the raw enemy ID into
`0E31:1B44`, whose leg reads for IDs 12–15 overlap explored-map bytes at
`CB0C`. The port now uses those actual bytes rather than a fixed penalty for
two enemy IDs. The new fights and earlier complete encounter cases agree.

Run `python3 tools/make_complete_encounter_vectors.py --towns` to reproduce
the new corpus. Earlier Starport traces at a different, obstructed location
remain bounded at 64 waves; these new completed fights do not turn those
earlier traces into completed outcomes. Wider initiative/AI contexts remain
**APPROXIMATE** beyond the compared cases.

## 3. Quiet reports and viewport edges

**VERIFIED:** twelve selected-unit/victim combinations execute original
`05AB:18E8` headers and `0D43:0A35` quiet retirement, with `1656:03F5` wrapping
and `173D:00D5` glyph placement. All 88-by-88 interior pixels agree before and
after ejection. Mech headers retain their two rows and blank separator;
infantry headers retain one row. The renderer preserves the header and cursor
when the original selected mech record has already been retired. Saved quiet
reports retain that presentation. These pixel cases cover one ejection each;
they do not establish every possible sequence of repeated ejections.

Another 2,582 executions of `0000:0E4B` establish the original visibility
flags, including cursor/actor positions across sector edges. Infantry admits
horizontal offsets -13..13 and vertical -12..12; mechs admit -15..13 and
-12..14. Sprites, combat flashes and beam-sound eligibility use these bounds.
This corrects the previous symmetric approximation. It is **not** a claim of
complete battlefield pixel parity: beam/projectile interpolation and some
portrait/viewport compositing still need full-frame comparisons.

Generators: `make_quiet_ejection_vectors.py` and
`make_combat_visibility_vectors.py`; the existing combat UI/event suites consume
their numeric fixtures. Raw text and reconstructed panels remain in `work/`.

## 4. Story branches and continuous cache paths

**VERIFIED within the expanded corpus:** 248 complete HUT/MAYOR/THEATER branches
now include parties of 1, 4, 5 and 8, threshold skills in the last member,
repeats, refusals, money and health boundaries. Final flags/cash/records and
ordered waits, choices, animation and sound requests agree. This doubles the
earlier 124-case scope; the static audit of all 26 BLDs is separate from
executed branch coverage.

**VERIFIED continuous paths:** 768 original movement inputs across six contexts
(MAP14/MAP15, parties of 1/5/8), comparing the cursor and every member after
each input. `0000:218F` movement and `0000:051B` formation updates run at every
half-step, including the original viewport. MAP14 uses one/two/four-step keys;
MAP15 uses its original single-step behavior. Routes start from declared legal
entry formations and remain continuous, with no state reset between keys.
Native tests save/restore before each input. Interactions are excluded here
and covered by the existing 5,760 formation/contact and 534 cache-rule cases.
The older 2,400 native compatibility steps remain useful, but exact DOS recovery
from malformed legacy follower positions is still **UNKNOWN**.

## 5. Windows build and verification

The Windows x86-64 build uses MinGW-w64 GCC 13.2, SDL2 2.32.4 and Wine 10 on
this Linux host. Dependencies were extracted under ignored `local-deps/windows`
without a system install; archive hashes are in
[windows-dependencies.json](windows-dependencies.json). `scripts/build-windows.sh`
also accepts an installed MinGW compiler and an external SDL2 CMake directory.
The build copies the matching SDL2.dll beside the executable. The optional
`tools/windows_check.py` uses a project-private Wine prefix and maps absolute
fixture paths through its Z: drive. Headless CTests have no desktop display.

Windows verification found and fixed three portability defects:

- MSVCRT ignored the `x` in `fopen("wbx")`, allowing a pending save to be
  truncated. Windows now uses exclusive descriptor creation. Save replacement
  uses `MoveFileExA` without first deleting the old slot.
- Two decoded combat/audio objects, each over 1 MB, overflowed the default
  2 MB Windows stack. The transactional decoder now allocates on the heap and
  frees on success/failure; the test fixture also lives off the stack. The PE
  stack reserve is unchanged. Corrupt-cache tests check that output survives
  rejection unchanged, with leak checks enabled.
- Campaign tests now recognize both slash styles when deriving save filenames.

Windows input/state/pixel checks compare the actual Windows SDL executable
against the Linux headless build. Audio checks use SDL's dummy device to verify
nonzero PCM and bounded sequential queues. **UNKNOWN:** physical Windows
keyboard/audio drivers, sound hardware and real 8 MHz XT speaker calibration.
Wine verification does not establish those hardware properties.

## Saves and checks

Internal saves are **BTPe/v40**, still a 20,480-byte payload in the BTS1
length/CRC envelope. Little-endian retrace phases occupy 16010–16013;
the 18-byte quiet report occupies 16014–16031. Earlier byte clocks migrate by
preserving elapsed 32 ms ticks, without consuming RNG. Old quiet saves cannot
reconstruct headers they never stored; a subsequent round establishes one.
Cache formats remain BTTA/v24, BTCB/v11 and BTW3.

```sh
./scripts/build.sh
ctest --test-dir build --output-on-failure
./scripts/test-sanitize.sh --core-only
python3 -m unittest discover -s tests -p test_tools.py
./scripts/build-windows.sh
python3 tools/windows_check.py --ctest
python3 tools/native_smoke.py --windows --portability-only
```

**PASS:** all 56 Linux, all 56 sanitizer and all 56 Wine CTest suites; five
Python tool tests; 41 Windows SDL checks, including 19 held combat F5/F9 pages.
The final report-buffer adjustment passes the focused combat-panel checks too.
Exact timings and scope are recorded in [TESTING.md](TESTING.md). Original files,
modes, timestamps and nested Git metadata are checked against the immutable
1,287-entry reference baseline before completion. No remote push is made.
