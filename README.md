# BtechPort

Independent C11/SDL2 recreation research for **BattleTech: The Crescent Hawk's Inception**, supplied DOS version 1.03. **M0, M1, M2a and bounded M2b are complete.** You can explore MAP1, visit the Citadel's Hall of Legends, have the first Katrina conversation and return outside. Original dialogue now preserves upper and lower case. Development stops here for milestone review; the rest of M2 and the campaign remain unfinished.

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

The runtime reads `MAP1.MTP`, `BTTLTECH.ICN` and `CITADEL.BLD`. It requires no Godot, .NET or reference recreation. Combat class stops at an unsupported native action after its introduction; Talk to others stops immediately. Failed choices roll back partial state changes, and Backspace returns to the menu. Other building interiors are unavailable. Use `citadel-hall.actions` instead for the first Hall screen.

**VERIFIED in the tested routes:** authentic map/tile decoding; 31 original movement states; Citadel trigger and deferred outdoor step; six Hall screens; first Katrina conversation, text concatenation, state-byte writes, repeat denial and persistent visit result; retained menu selection on re-entry. **INFERRED:** generalized movement/trigger rules, later script paths and broader state meanings. **APPROXIMATE:** player/scene imagery, diagnostic panel, independent mixed-case font/layout, input repetition/flushing, 32ms cadence and map edges. The original byte-22 countdown resumes outdoors; the native slice retains its last script-set value and does not model countdown/day timing. Shops, economy, combat, original GAME saves, animations, audio and later campaign progression remain unavailable; complete parity is **UNKNOWN**.

The bounded DOSBox harness runs whole JSON input sequences on a private virtual display, captures frames/state and closes automatically. It uses no interactive terminal input, so the former per-key approval loop is removed. Original binaries, screenshots and memory dumps remain in ignored directories.

Read [the milestone review](docs/PROJECT_STATUS.md), [testing and reproduction](docs/TESTING.md), [Katrina evidence](docs/M2_KATRINA_EVIDENCE.md), [Citadel entry/Hall evidence](docs/M2_CITADEL_EVIDENCE.md), [original inventory](docs/ORIGINAL_FILES.md), [evidence audit](docs/RESEARCH_AUDIT.md), [language decision](docs/LANGUAGE_DECISION.md), and [remaining questions](docs/OPEN_QUESTIONS.md). New implementation is under `port/`, automation under `tools/` and `scripts/`, regression checks under `tests/`.

Both supplied reference directories remain unchanged. A local Git repository on `main` records incremental milestones; originals, reference checkout, generated assets and dependencies are ignored. No pushes or Git configuration changes were made. No substantial GPL source was copied or translated into the runtime; this does not establish legal clean-room status or permission to redistribute proprietary assets.
