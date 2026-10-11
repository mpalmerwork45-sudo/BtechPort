# BtechPort

Independent C11/SDL2 recreation research for **BattleTech: The Crescent Hawk's Inception**, supplied DOS version 1.03. **M0, M1, M2a, M2b and the bounded M2c Talk handler are complete.** Explore MAP1, visit the Citadel's Hall, have the first Katrina conversation, or play an original NPC conversation in a labeled checkpoint. NPC travel is still unimplemented; the normal fresh-game Citadel is empty. Text preserves upper/lower case. Development stops here for milestone review; the campaign remains unfinished.

From this directory on the current Kubuntu machine:

```sh
./scripts/build.sh
./build/btech-port --data "Original DOS"
./scripts/test.sh
```

Arrows move/select; Enter or Space confirms and advances dialogue; Backspace declines entry or recovers from an unsupported choice. F3 toggles diagnostics, R restarts and Esc closes. From the start, move Up five times, confirm entry, then confirm **Request to see Katrina**. Advance the sentry and Katrina screens to return to the menu. A repeat request gets the original denial. Four Down presses select Leave; after exiting and re-entering, the menu retains that selection. Hall of Legends still has its six original screens.

To open directly on Katrina's first conversation:

```sh
./build/btech-port --data "Original DOS" --replay tests/fixtures/citadel-katrina.actions
```

The runtime reads `MAP1.MTP`, `BTTLTECH.ICN`, `CITADEL.BLD` and ignored `work/talk-data.bin`, which the build prepares reproducibly from `BTECH.EXE`. No Godot/.NET/reference runtime is required. Combat class stops at an unsupported action after its introduction; other building interiors remain unavailable. Failed choices roll back partial state/result changes, and Backspace returns to the menu. Use `citadel-hall.actions` for the first Hall screen.

To open the verified NPC conversation:

```sh
./build/btech-port --conversation-checkpoint --replay tests/fixtures/citadel-talk.actions
```

Enter/Space returns to the Citadel menu. Omit `--replay` to start outdoors with the visibly labeled checkpoint; five Up, Enter, three Down, Enter opens the NPC menu. Done returns immediately; selecting the NPC shows the authentic reply. Both menus remember selection independently. The checkpoint supplies a controlled NPC precondition; it does not simulate arrival. The normal Talk choice now shows the original empty-room response and returns. Custom resource/cache paths use `--data` and `--dialogue-data`; preparation is documented in [TESTING.md](docs/TESTING.md).

**VERIFIED in scope:** authentic resource decoding; 31 movement states; Citadel entry/Hall/Katrina, repeat denial and persistence; `F5 0C` empty response and NPC handler under an explicit controlled precondition, exact original text, result changes, selection retention and return. **INFERRED:** broader movement, multiple NPCs/changing counts, later paths and flag meanings. **APPROXIMATE:** imagery, panel, independent mixed-case font/layout, input, 32ms cadence and map edges. **UNKNOWN/unimplemented:** NPC travel/RNG parity, countdown/day timing, shops, economy, combat, GAME saves, animation/audio and later campaign progression. The original resumes NPC/countdown updates outdoors; native context holds its last values, so those post-exit fields are excluded from parity.

The bounded DOSBox harness runs whole JSON input sequences on a private virtual display, captures frames/state and closes automatically. It uses no interactive terminal input, so the former per-key approval loop is removed. Original binaries, screenshots and memory dumps remain in ignored directories.

Read [the milestone review](docs/PROJECT_STATUS.md), [testing](docs/TESTING.md), [Talk evidence](docs/M2_TALK_EVIDENCE.md), [Katrina evidence](docs/M2_KATRINA_EVIDENCE.md), [Hall evidence](docs/M2_CITADEL_EVIDENCE.md), [inventory](docs/ORIGINAL_FILES.md), [audit](docs/RESEARCH_AUDIT.md), [language decision](docs/LANGUAGE_DECISION.md) and [open questions](docs/OPEN_QUESTIONS.md). New code is under `port/`, automation under `tools/`/`scripts/`, regressions under `tests/`.

Both supplied reference directories remain unchanged. A local Git repository on `main` records incremental milestones; originals, reference checkout, generated assets and dependencies are ignored. No pushes or Git configuration changes were made. No substantial GPL source was copied or translated into the runtime; this does not establish legal clean-room status or permission to redistribute proprietary assets.
