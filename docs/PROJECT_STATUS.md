# Project status — M2b review, 2026-10-11

**M0, M1, M2a and bounded M2b complete. Stop here for milestone review.** The native slice now supports Citadel entry → first Katrina conversation → menu → repeat denial → exit/re-entry, alongside Hall of Legends. Original resource text preserves upper and lower case. M2 campaign foundations and the whole campaign remain unfinished. Use [README.md](../README.md) and [TESTING.md](TESTING.md) to run and reproduce it.

## Actual working result

```sh
./scripts/build.sh
./build/btech-port --data "Original DOS"
./build/btech-port --data "Original DOS" --replay tests/fixtures/citadel-hall.actions
./build/btech-port --data "Original DOS" --replay tests/fixtures/citadel-katrina.actions
./scripts/test.sh
```

C11/SDL2 was chosen by the [weighted comparison](LANGUAGE_DECISION.md). The engine is independent of Godot/.NET/UnBattletech; core, resource parsing and software rendering run without SDL. Controls: arrows move/select, Enter/Space confirm/continue, Backspace declines entry or recovers from an unsupported choice, F3 diagnostics, R restart, Esc exit. From the outdoor start, five Up presses reach the Citadel prompt. Confirm entry, confirm Request to see Katrina, advance the sentry and conversation screens, then return to the menu. A repeat request gets the original denial. Four Down presses reach Leave. The Hall route still has six screens.

**VERIFIED in scope:** original resource loading, signed RLE, 14 supported local maps, block normalization, MAP1 working-grid identity, start position, four arrow directions and collision on the original 30-action trace. M1 tile/frame comparisons remain recorded in [TESTING.md](TESTING.md). M2a verifies the Citadel entrance/deferred step, all 4328 decoded bytes matching RAM, Hall texts/waits, retained menu choice, `FF` exit and byte 10 becoming 1. M2b verifies the first Katrina conversation's three-block text assembly, byte setters/addition and required branches, byte 6 changing 0→1 and persisting, byte 22 being set to 255 in the building, repeat denial and selection retention on re-entry. Native records replay deterministically. Tests restore either conversation pause and migrate BTP1/BTP2 state.

**INFERRED:** generalized movement/entrances, later script branches, broader state meanings and presentation semantics. **APPROXIMATE:** player marker, Citadel imagery, independent left panel, mixed-case glyph shapes/layout, 32ms step, key repeat/input flushing and edge blocking. `F2` records a delay request without reproducing its timing. The original byte-22 countdown decreases outdoors; the native slice retains its last script-set value, so post-exit countdown equality is excluded. **UNKNOWN/unavailable:** full party footprints, outer-world generation, original animations/NPCs, complete flag meanings, campaign-wide native actions, shops, economy, combat, original GAME compatibility and audio. Combat class reaches its introductory pause then fails visibly at `F5 04`; talk fails at `F5 0C`. Failed choices roll back partial state changes, and Backspace recovers to the menu. This recovery is a prototype control, not an original rule. Other interiors remain unavailable; no opcode is silently skipped.

## Audit and evidence

88 original files, 641,365 bytes; correct game is unpatched `BTECH.EXE` v1.03, EXEPACK-compressed. Six saves and three backups are 3913 bytes. No manual/config is supplied. Full sizes, SHA-256 and apparent formats are in [ORIGINAL_FILES.md](ORIGINAL_FILES.md) and [original-manifest.json](original-manifest.json).

Reference checkout `86e1b637c39a713547cfa2aa2149d744b995acfc` (2026-09-29). The [audit matrix](RESEARCH_AUDIT.md), [Citadel evidence](M2_CITADEL_EVIDENCE.md) and [Katrina evidence](M2_KATRINA_EVIDENCE.md) record original traces and corrections. Decrypt before interpreting; `F2` requests delay/flush rather than room description; `0800:2A2B` drains keys. Independent original-image disassembly confirms `F1`/`F4` write bytes, despite misleading generated C widths. State 22 is a countdown, not a permanent quest flag. Original evidence takes precedence. The outer-world static-template claim remains open.

Original oracle: locally extracted DOSBox 0.74-3 and Xvfb; Spice86's source/.NET dependencies are missing. DOSBox runs only ignored working copies. Bounded JSON scripts own a private display and close automatically, removing per-key interactive terminal approvals. Whole-script GUI and sanitizer execution still follow the environment's permission rules.

## Verification

PASS: two CTest suites; **319 core/corpus/state checks**, **88 script checks**, three Python EXEPACK tests; 31 M1 movement states; **16 Hall checkpoints / 20 native states** and **20 Katrina checkpoints / 20 native states**; original text hashes, deterministic replay, decline, class/talk faults with rollback/recovery, pause restoration and BTP1/BTP2 migration; native dummy/private-X11 movement, Hall and Katrina scenarios with recorded replay; headless ASan/UBSan/LeakSanitizer. The Katrina fixture also matches the live original snapshots and full decoded RAM payload. All 88 original hashes match. Reference guard: **1287 entries unchanged**, including modes, modification times and reference Git metadata. Commands and scope are in [TESTING.md](TESTING.md).

No known failing milestone checks remain. This validation does not establish complete behavioral, pixel, RNG, Windows or timing parity.

## Work and provenance

Added independently written state-byte BLD operations, consecutive text spans, case-preserving lowercase glyphs, safe failed-choice recovery, original Katrina script/fixture/verifier and bounded native smoke scenario. Internal state is now **128-byte BTP3**, preserving VM position, waits, menu choice, 23 modeled bytes, up to eight text spans and a recovery checkpoint. Legacy 24-byte BTP1 and 64-byte BTP2 decode; a real Hall pause migrates and continues identically. This is a tested core encoding, not an original GAME save feature or a save/load UI. Dependencies and proprietary captures remain ignored in `local-deps/` and `work/`. Both supplied trees are unchanged. No substantial GPL implementation is copied/translated; original evidence informs independently written C.

The local repository remains on `main`. M2b has incremental commits for the case correction, original Katrina evidence and playable integration; this report completes the review. Existing author identity was used; no Git configuration changes or pushes occurred. `.gitignore` excludes both supplied directories, generated assets, builds and dependencies.

## Smallest next milestone

Proposed M2c: trace **Talk to others → one original conversation → return to menu**, recover the required `F5 0C` native action and verify its state changes with a canonical regression. Resolve any required random selection from original evidence; do not invent outcomes. Combat class, countdown/day calibration and player/scene imagery remain separate unfinished work. Do not start tactical combat, expanded mechs or campaign-wide implementation in that step.
