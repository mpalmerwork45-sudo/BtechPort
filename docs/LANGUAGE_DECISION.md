# Language decision — M0, 2026-10-11

**Choose C11 with SDL2.** This is an independent, small engine; UnBattletech/Godot/.NET are not runtime dependencies.

Scores are project judgments (1–5), weighted out of 5, not benchmarks.

| Criterion | Weight | C11 | Rust stable |
|---|---:|---:|---:|
| Human maintenance (user knows C, is learning Rust) | 25% | 5 | 3 |
| Memory safety / refactoring | 25% | 2 | 5 |
| Explicit 8086 widths, wrapping, state machines | 15% | 5 | 5 |
| Deterministic headless testing | 15% | 5 | 5 |
| Available tools, Linux builds, debugger, Windows portability | 15% | 5 | 3 |
| Small dependency footprint / possible retro builds | 5% | 5 | 3 |
| **Weighted score** | **100%** | **4.25** | **4.00** |

Rust offers a real safety advantage, particularly for scripts and malformed resources. For this small first slice, checked byte readers, fixed-size state, sanitizers, and tests can manage C's risks while keeping the implementation accessible to its human maintainer. Reconsider if interpreter/state complexity grows beyond what these measures control. No duplicate Rust implementation is planned.

**VERIFIED environment:** `/usr/bin/gcc` and CMake are available; neither `cargo` nor `rustc` was found in PATH or `/usr/bin`, and no `~/.cargo` exists. SDL2 runtime `libSDL2-2.0.so.0` is installed. Development headers were downloaded as the Ubuntu `libsdl2-dev` 2.32.4 package and extracted under `local-deps/sdl2/`; nothing was installed into system directories. Use a normal SDL2 development installation on other machines. The CMake frontend is optional so core/data tests also build without SDL.

Layout: `port/core/` state and logical actions; `port/data/` bounds-checked original resource parsers; `port/frontend/` software pixels and SDL window/events; `tests/` synthetic format tests and private-resource verification. The core has no SDL, clock, filesystem, or OS dependency. SDL2 supplies only window/input/pixel presentation. No audio implementation in M1.

The Windows route is CMake + a C11 compiler + SDL2 development files; **UNKNOWN** until actually built there. DOS/retro is a future option, not a promised target. Build/run commands and completed M1 validation are in [TESTING.md](TESTING.md).
