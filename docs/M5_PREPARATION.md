# M5 preparation — shared original-content loading

**2026-10-16: M5-P1 implemented and verified.** This is the first preparation
increment from the [engine and editor plan](ENGINE_AND_EDITOR_PLAN.md), against
the previously playable revision `901c952`. M5-P2–P5 remain proposed.

## Implemented boundary

[content.h](../port/data/content.h) defines an owned `BtpContent` context and
explicit original resource/cache paths. [content.c](../port/data/content.c)
loads those resources in the previous order and publishes them only after every
stage succeeds. An unsuccessful load frees its partial allocation and leaves
any existing context intact. Closing a context releases its resources and
clears its identity; closing it again is safe.

The context identifies the original DOS 1.03 profile. It lives outside
`BtpState`, so no profile field or pointer enters existing save files. The large
resource allocation remains on the heap. The ownership contract forbids copying
the context; borrowed resource pointers expire when it is replaced or closed.
Replacing content is a session-boundary operation, not live battle hot reload.

[cli.c](../port/frontend/cli.c) maps the existing command-line paths to this
interface. Both [headless.c](../port/frontend/headless.c) and
[sdl.c](../port/frontend/sdl.c) now use that single loading and cleanup path.
Default filenames, original decoders, game startup, gameplay rules, rendering
and save encoding remain as before. No new dependency or manifest is required.

This supplies a real place for a future package loader to create an owned
content context. `BtpResources` still describes original formats and fixed
tables; this increment does not make arbitrary game packages loadable or
externalize mech definitions by itself.

## Verification

**VERIFIED within the following bounds:**

- All **57 Linux CTest suites** pass, including the existing original-save,
  combat, service, world, story and held-continuation comparisons (42.11 seconds).
- The new `original-content-lifetime` test passes **90 checks**: empty-context
  failure, every loading stage, missing/truncated caches, invalid arguments,
  unchanged previously loaded bytes/profile, successful replacement and cleanup.
  It passes under ASan/UBSan with leak detection and under Windows/Wine with the
  default Windows stack reserve.
- Before changing the code, the two existing player executables were retained
  in ignored `work/m5-p1/`. Four cases captured canonical state, full RGB frame
  and save bytes: fresh start, `citadel-katrina.actions`,
  `ordinary-combat.actions` and original `GAME3` import. Both rebuilt entry
  points match all three outputs exactly in all four cases when run headlessly.
- Both players retain the previous output/error behavior for alternate cache
  paths containing spaces and for a missing input at each of the four CLI
  resource options.
- The sanitized headless player loads and resaves all four pre-refactor
  snapshots with identical state, pixels and save bytes. LeakSanitizer needed
  execution outside the process-inspection sandbox; leak checking stayed on.
- Native Linux SDL checks pass for the actual intro, music, credit shortcut,
  played-before choices and exit controls, plus F5/F9, a held amount entry,
  failed-load preservation and continued transaction behavior.
- The Windows SDL player also passes the held-amount F5/F9, failed-load and
  transaction-continuation check under the isolated Wine test environment.

The first eight before/after comparisons are local refactor comparisons, not
new DOS captures. The established original oracle corpus remains in use. The
entire sanitizer/Windows fidelity corpus was not repeated for this isolated
loader change; the new ownership test and affected player paths were checked.
Physical Windows hardware and speaker calibration remain outside these claims.

Repeat the principal checks after building the relevant targets:

```sh
ctest --test-dir build --output-on-failure
ctest --test-dir build/sanitize -R original-content-lifetime --output-on-failure
python3 tools/windows_check.py --ctest -R original-content-lifetime
python3 tools/native_smoke.py --intro-only
python3 tools/native_smoke.py --save-only
python3 tools/native_smoke.py --windows --save-only
python3 tools/reference_guard.py verify
```

## Next preparation increment

**M5-P2:** introduce named mech/weapon/appearance accessors over the existing
records and tables, migrating actual combat, inspection, animation and service
callers in bounded groups. Retain the original records and save bytes as the
authority during that step. These interfaces can later consume external
definitions without teaching every caller about package files or DOS offsets.

Then isolate original BLD/native action dispatch (P3), move the existing save
codec behind its current interface (P4), and validate a first authored content
schema/sample (P5). The original campaign remains the playable compatibility
case throughout those changes.
