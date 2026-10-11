# Project status — M2a review, 2026-10-11

**M0, M1 and bounded M2a complete. Stop here for milestone review.** The native slice now supports Citadel entry → Hall of Legends → exit. M2 campaign foundations and the whole campaign remain unfinished. Use [README.md](../README.md) and [TESTING.md](TESTING.md) to run and reproduce it.

## Actual working result

```sh
./scripts/build.sh
./build/btech-port --data "Original DOS"
./build/btech-port --data "Original DOS" --replay tests/fixtures/citadel-hall.actions
./scripts/test.sh
```

C11/SDL2 was chosen by the [weighted comparison](LANGUAGE_DECISION.md). The engine is independent of Godot/.NET/UnBattletech; core, resource parsing and software rendering run without SDL. Controls: arrows move/select, Enter/Space confirm/continue, Backspace declines entry or recovers from an unsupported choice, F3 diagnostics, R restart, Esc exit. From the outdoor start, five Up presses reach the Citadel prompt. Visit Hall of Legends, read six screens, then choose Leave (three Down presses from the retained Hall selection).

**VERIFIED in scope:** original resource loading, checked signed RLE, 14 supported local maps, block normalization, MAP1 working-grid identity, start position, four arrow directions and collision on the original 30-action trace. The M1 tile/frame comparisons remain recorded in [TESTING.md](TESTING.md). M2a adds exact entrance half coordinates, original deferred step behavior, all 4328 decrypted Citadel payload bytes matching guest RAM, seven original text blocks, six waits, retained menu selection, `FF` exit, unchanged quest bytes on that route and the observed state-byte-10 change. Native input records replay deterministically.

**INFERRED:** generalized single-player movement/entrances beyond the tested routes; font and delay opcode semantics. **APPROXIMATE:** player marker, Citadel scene imagery, independent left panel, uppercase font/layout, 32ms step, key repeat/input flushing and edge blocking. `F2`'s delay request is recorded in state but its original timing is not reproduced. **UNKNOWN/unavailable:** full party footprints, outer-world generation, original animations/NPCs, complete flag meanings, campaign-wide BLD/native actions, shops, economy, combat, original GAME compatibility and audio. The other three Citadel choices fail visibly on their first unsupported opcode; Backspace is an explicit prototype recovery control. Other interiors remain unavailable. No opcode is silently skipped.

## Audit and evidence

88 original files, 641,365 bytes; correct game is unpatched `BTECH.EXE` v1.03, EXEPACK-compressed. Six saves and three backups are 3913 bytes. No manual/config is supplied. Full sizes, SHA-256 and apparent formats are in [ORIGINAL_FILES.md](ORIGINAL_FILES.md) and [original-manifest.json](original-manifest.json).

Reference checkout `86e1b637c39a713547cfa2aa2149d744b995acfc` (2026-09-29). The [audit matrix](RESEARCH_AUDIT.md) records useful recovery and discrepancies. [Citadel evidence](M2_CITADEL_EVIDENCE.md) adds corrections: decrypt before reading opcodes; `F2` requests delay/input flushing, not room description; `0800:2A2B` drains keys rather than waiting for a new one. Original bytes and live observations take precedence. The outer-world static-template claim remains an open question.

Original oracle: locally extracted DOSBox 0.74-3 and Xvfb; Spice86's source/.NET dependencies are missing. DOSBox runs only ignored working copies. Bounded JSON scripts own a private display and close automatically, removing per-key interactive terminal approvals. Whole-script GUI and sanitizer execution still follow the environment's permission rules.

## Verification

PASS: two CTest suites; **231 core/corpus/state checks**, **47 script checks**, three Python EXEPACK tests; 31 M1 movement states; **16 original Citadel checkpoints / 20 native states**, seven text digests, deterministic replay, decline, all three unsupported branches and recovery; mid-dialogue BTP2 restoration; native dummy/X11 movement and Citadel scenarios with recorded replay; ASan/UBSan/LeakSanitizer on headless paths. All 88 original hashes match. Reference guard: **1287 entries unchanged**, including modes, modification times and reference Git metadata. Commands and scope are in [TESTING.md](TESTING.md).

No known failing milestone checks remain. This validation does not establish complete behavioral, pixel, RNG, Windows or timing parity.

## Work and provenance

Added independent BLD decoding/interpreter, explicit building modes and logical accept/cancel actions, native dialogue UI, canonical Citadel fixture/verifier and bounded reference input script. Internal state is now **64-byte BTP2**, preserving VM position, waits, menu selection and 16 state bytes; legacy 24-byte BTP1 states still decode. This is a tested core encoding, not an original GAME save feature. Dependencies and proprietary captures remain ignored in `local-deps/` and `work/`. Both supplied trees are unchanged. No substantial GPL implementation source is copied/translated; format facts, original bytes and live observations inform independently written C.

The user authorized a local Git repository. It is initialized on `main`, with incremental commits for the M1 baseline, original Citadel evidence, checked interpreter and playable integration. Existing author identity was used; no Git configuration changes or pushes occurred. `.gitignore` excludes both supplied directories, generated assets, builds and dependencies.

## Smallest next milestone

M2b: trace **Request to see Katrina → first conversation → return to menu** and verify its persistent quest-byte changes. Implement the necessary state-dependent BLD branches/setters and any specifically required native actions, with another canonical regression. Player/scene sprite dispatch is still unproven and remains deferred. Do not start combat, expanded mechs or campaign-wide scripts in that step.
