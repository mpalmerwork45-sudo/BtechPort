# BtechPort

Independent C11/SDL2 recreation research for **BattleTech: The Crescent Hawk's Inception**, supplied DOS version 1.03. **M0 and the bounded M1 exploration slice are complete; development stops here for milestone review.**

From this directory on the current Kubuntu machine:

```sh
./scripts/build.sh
./build/btech-port --data "Original DOS"
./scripts/test.sh
```

Arrows move through the original training-school map. F3 toggles collision diagnostics; R restarts; Esc closes. The game reads `MAP1.MTP` and `BTTLTECH.ICN` at runtime. It does not require Godot, .NET, or the reference recreation.

**VERIFIED:** authentic map block layout and tile decoding; recorded starting coordinates; 30 arrow actions / 31 states matching the original player and cursor; basic road, wall and hedge collision in that scenario. The original MAP1 working grid and observed display palette have been checked. **INFERRED:** the single-player collision rule outside the tested route. **APPROXIMATE:** player marker, diagnostic panel, keyboard repetition, 32ms native tick cadence, and blocking at unsupported map edges. Building interiors, NPC behavior, combat, economy, original save compatibility, animations and audio are unavailable; their complete parity is **UNKNOWN**. This slice lets you explore one location; it is not a campaign.

The bounded DOSBox harness runs whole JSON input sequences on a private virtual display, captures frames/state and closes automatically. It uses no interactive terminal input, so the former per-key approval loop is removed. Original binaries, screenshots and memory dumps remain in ignored directories.

Read [the milestone review](docs/PROJECT_STATUS.md), [testing and reproduction](docs/TESTING.md), [original inventory](docs/ORIGINAL_FILES.md), [evidence audit](docs/RESEARCH_AUDIT.md), [language decision](docs/LANGUAGE_DECISION.md), and [remaining questions](docs/OPEN_QUESTIONS.md). New implementation is under `port/`, automation under `tools/` and `scripts/`, regression checks under `tests/`.

Both supplied reference directories remain unchanged. No substantial GPL source was copied or translated into the runtime; this does not establish legal clean-room status. No distribution licence or proprietary asset redistribution is offered. The project root's empty read-only `.git/` placeholder is not a functioning repository; a normal local repository is recommended once that placeholder is resolved. No commits, pushes or git configuration changes were made.
