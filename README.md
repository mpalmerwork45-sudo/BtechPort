# BtechPort

Independent C11/SDL2 recreation research for **BattleTech: The Crescent Hawk's Inception**, supplied DOS version 1.03. **M0, M1 and bounded M2a are complete.** You can explore MAP1, enter the Citadel, read the Hall of Legends and return outside. Development stops here for milestone review; the rest of M2 and the campaign remain unfinished.

From this directory on the current Kubuntu machine:

```sh
./scripts/build.sh
./build/btech-port --data "Original DOS"
./scripts/test.sh
```

Arrows move/select; Enter or Space confirms and advances dialogue; Backspace declines entry or recovers from an unsupported choice. F3 toggles diagnostics, R restarts and Esc closes. From the start, move Up five times, confirm entry, select **Visit Hall of Legends**, read six screens, then select **Leave the citadel**. The menu retains your Hall selection, so three Down presses reach Leave.

To open directly on the first Hall screen:

```sh
./build/btech-port --data "Original DOS" --replay tests/fixtures/citadel-hall.actions
```

The runtime reads `MAP1.MTP`, `BTTLTECH.ICN` and `CITADEL.BLD`. It requires no Godot, .NET or reference recreation. The other three Citadel choices produce an explicit unsupported-opcode diagnostic; Backspace returns to the menu. Other building interiors are unavailable.

**VERIFIED:** authentic map/tile decoding; 31 original movement states; Citadel trigger and deferred outdoor step; seven original text blocks, six pauses, retained menu choice, exit position and 16 recorded state bytes on the tested loop. **INFERRED:** generalized movement/trigger rules and some presentation opcode semantics. **APPROXIMATE:** original player/scene imagery, diagnostic panel, uppercase font/layout, input repetition/flushing, 32ms cadence and unsupported map edges. Quest progression, shops, economy, combat, original GAME saves, animations and audio remain unavailable; complete parity is **UNKNOWN**.

The bounded DOSBox harness runs whole JSON input sequences on a private virtual display, captures frames/state and closes automatically. It uses no interactive terminal input, so the former per-key approval loop is removed. Original binaries, screenshots and memory dumps remain in ignored directories.

Read [the milestone review](docs/PROJECT_STATUS.md), [testing and reproduction](docs/TESTING.md), [Citadel evidence](docs/M2_CITADEL_EVIDENCE.md), [original inventory](docs/ORIGINAL_FILES.md), [evidence audit](docs/RESEARCH_AUDIT.md), [language decision](docs/LANGUAGE_DECISION.md), and [remaining questions](docs/OPEN_QUESTIONS.md). New implementation is under `port/`, automation under `tools/` and `scripts/`, regression checks under `tests/`.

Both supplied reference directories remain unchanged. A local Git repository on `main` records incremental milestones; originals, reference checkout, generated assets and dependencies are ignored. No pushes or Git configuration changes were made. No substantial GPL source was copied or translated into the runtime; this does not establish legal clean-room status or permission to redistribute proprietary assets.
