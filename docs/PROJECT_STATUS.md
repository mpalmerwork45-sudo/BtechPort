# Project status — M0/M1 review, 2026-10-11

**M0 complete. M1 is a working, bounded native MAP1 exploration slice. Stop here for the requested milestone review.** The whole campaign remains unimplemented. Use [README.md](../README.md) and [TESTING.md](TESTING.md) to run and reproduce it.

## Actual working result

```sh
./scripts/build.sh
./build/btech-port --data "Original DOS"
./scripts/test.sh
```

C11/SDL2 was chosen by the [weighted comparison](LANGUAGE_DECISION.md): accessible C maintenance and available host tooling narrowly outweigh Rust's safety advantage for this small slice. The engine is independent of Godot/.NET/UnBattletech. Core, resource parsing and software rendering also run without SDL. Native controls: arrows, F3 diagnostics, R restart, Esc exit.

**VERIFIED in scope:** original resource loading, checked signed RLE, all 14 supported local maps, 8×8 block normalization, MAP1 working-grid identity, recorded position, all four arrow directions and wall/hedge collision on a 30-action original trace. Runtime tile decode matches all 64,000 secondary PNG pixels. Observed MAP1 palette/camera gives 98.669% agreement for its original 216×200 panel at the compared frame. Native input records replay deterministically.

**INFERRED:** generalized single-player movement/collision beyond that route. **APPROXIMATE:** player marker, independent left diagnostic panel, 32ms native step/OS key-repeat cadence, and edge blocking. **UNKNOWN/unavailable:** full party footprints, outer-world generation/transitions, original animations, NPC behavior, story/BLD control flow parity, shops, cadet economy, combat, original GAME compatibility and audio. Building entrance metadata is exposed but no real interior transition is implemented, as required until those rules are understood. A full BLD engine with skipped actions is not supplied.

## Audit and evidence

88 original files, 641,365 bytes; correct game is unpatched `BTECH.EXE` v1.03, EXEPACK-compressed. Six saves and three backups are 3913 bytes. No manual/config is supplied. Full sizes, SHA-256 and apparent formats are in [ORIGINAL_FILES.md](ORIGINAL_FILES.md) and [original-manifest.json](original-manifest.json).

Reference checkout `86e1b637c39a713547cfa2aa2149d744b995acfc` (2026-09-29). MTP/graphics structure and newer trigger/code recovery are useful; complete story/combat/timing parity remains unproven. The [audit matrix](RESEARCH_AUDIT.md) records stale README/progress statements about missing segments, assets and save sizes, the faulty Python signed-RLE extractor, and stale BLD annotations despite successful byte round trips. The outer-world static-template claim remains an open question, not an implemented assumption.

Original oracle: locally extracted DOSBox 0.74-3 and Xvfb; Spice86's source/.NET dependencies are missing. DOSBox runs only ignored working copies. Bounded JSON scripts own a private display and close automatically, removing per-key interactive terminal approvals. Whole-script GUI and sanitizer execution still follow the environment's permission rules.

## Verification

PASS: 65 C synthetic core/format/pixel assertions; authentic corpus adds checks to 131; three Python EXEPACK tests; 31 canonical original states including cursor and party[0]; deterministic replay and unknown-input rejection; native dummy/X11 window events/presentation and recorded replay; ASan/UBSan/LeakSanitizer for headless paths. All 88 original hashes match. Final reference guard: **1287 entries unchanged**, including content, modes, modification times and reference git metadata. Exact limits, commands, sandbox sanitizer issue and frame deviations are in [TESTING.md](TESTING.md).

No known failing milestone checks remain. This validation does not establish complete behavioral, pixel, RNG, Windows or timing parity.

## Work and provenance

Created `port/core`, `port/data`, `port/frontend`, CMake/build/test scripts, fixtures/tests, inventory/guard/unpacker/reference automation, and the requested reports. Dependencies and proprietary captures remain in ignored `local-deps/` and `work/`. Both supplied trees are unchanged. No substantial GPL implementation source is copied/translated; format facts, original bytes and live observations inform independently written code. No public distribution or clean-room guarantee is asserted.

The project root has an empty, read-only `.git/` placeholder; `git status` reports no repository. `.gitignore` protects both references, generated assets, build artifacts and local dependencies. Recommend a normal local repository once the placeholder is resolved. No repository was initialized over it, no git configuration changed, and no commits or pushes were made.

## Smallest next milestone

M2a: trace one **Citadel entry → one dialogue choice → exit** in the original, recording trigger packed coordinates, BLD decrypt/dispatch path, mode/flag changes and output. Implement only the verified opcode subset with explicit unsupported-opcode diagnostics and a canonical entry/exit test. Add original player sprite/masking where its dispatch is proven. Resolve multi-unit footprint and map-edge behavior before claiming broader faithful exploration. Do not start combat, expanded mechs, or campaign-wide scripts in this next step.
