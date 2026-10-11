# Project status — M2c review, 2026-10-11

**M0, M1, M2a, M2b and the bounded M2c Talk handler are complete. Stop here for milestone review.** The port supports the original empty-room response and one NPC conversation/Done/return path in an explicitly labeled controlled checkpoint. NPC arrival/travel is unimplemented; a naturally reached conversation remains the next gap. Hall, Katrina/repeat and exit/re-entry still work. Text preserves upper/lower case. The rest of M2 and the campaign remain unfinished.

## Actual working result

```sh
./scripts/build.sh
./build/btech-port --data "Original DOS"
./build/btech-port --conversation-checkpoint --replay tests/fixtures/citadel-talk.actions
./scripts/test.sh
./scripts/test.sh --x11
./scripts/test-sanitize.sh
```

The build prepares ignored `work/talk-data.bin` from the audited executable using our proven EXEPACK reader. The C runtime reads that cache and authentic MAP1/BTTLTECH/CITADEL resources; Python is for conversion/testing only. Custom paths use `--data` and `--dialogue-data`. No Godot/.NET/reference runtime is required. [C11/SDL2 was chosen deliberately](LANGUAGE_DECISION.md); core/data/state/software rendering remain headless-testable.

Arrows move/select, Enter/Space confirms/continues, Backspace declines entry or recovers a failed choice, F3 diagnostics, R restart, Esc exit. The Talk replay opens on the NPC reply; Enter returns to the Citadel menu. Without the replay, five Up, Enter, three Down, Enter opens the NPC menu. Done returns immediately; both menus retain selection independently. The normal fresh-game Talk choice shows the original empty-room response and returns. The checkpoint is visibly labeled and supplies NPC context, not simulated arrival. [README](../README.md) and [TESTING](TESTING.md) give full commands.

## Evidence and confidence

**VERIFIED in scope:** prior resource/movement/Citadel routes; F5 0C dispatch to original 0FDC:17B9; three unmodified empty-room checkpoints and ten controlled conversation checkpoints; exact 47-byte empty response, 42-byte NPC menu and 162-byte reply; Done preserving result 91, NPC reply clearing it to 0, byte 13 becoming 1 and persisting, separate selection retention and return/exit. The exercised local handler makes no RNG draw. Screens establish highlights/order; bytes establish the state/text projection. PCs are bytecode-derived.

The reference close/no-op label for F5 0C disagrees with primary code and live execution. MAP1 supplies NPC/destination names; executable literals and a far-pointer table supply dialogue. The converter requires audited source/image hashes and records addresses/string hashes. See [Talk evidence](M2_TALK_EVIDENCE.md), [Katrina evidence](M2_KATRINA_EVIDENCE.md), [Hall evidence](M2_CITADEL_EVIDENCE.md) and the updated [audit](RESEARCH_AUDIT.md).

The original conversation trace applies an explicit precondition at the ordinary Citadel menu: eight NPC occupancy pairs and D33A in the running working copy, with before/after audit and snapshot. Executable/resource/save files stay unpatched. The final-harness run `1791685774441704966` matches the fixture; the initial controlled run is `1791685190039219738`, and the unmodified empty route is `1791684527855747449`. This validates the handler under controlled presence, not natural arrival or save loading.

**INFERRED:** multiple occupants/changing counts, generalized movement/entrances and later flags/paths. Structural tests cover nine choices/order/wrap without claiming a multi-occupant live trace. **APPROXIMATE:** imagery/marker, panel, independent mixed-case font/layout, 32ms cadence, repeat/flushing/delays and edges. **UNKNOWN/unavailable:** NPC travel/init/RNG parity, world/recruitment dialogue, full party footprints, procedural outer terrain, shops/economy/day timing, combat, GAME compatibility, animation/audio and later progression. Native NPC/countdown context holds its last values; original updates resume outdoors, so those post-exit fields are excluded. Class still faults at F5 04 after its introduction. Rollback/Backspace recovery is a prototype control, not an original rule. No unknown opcode/action is silently skipped.

## Verification

PASS: two CTest suites; **420 core/corpus/state assertions**, **94 script assertions**, **four Python unpacker/converter tests**; 31 movement states, 16 Hall checkpoints, 20 Katrina checkpoints and 13 Talk checkpoints. Native SDL dummy/private-X11 scenarios close automatically and recorded inputs replay to canonical states. Headless ASan/UBSan/LeakSanitizer cover core/data/pixels/VM/corpus and all four routes; SDL/backend is not sanitizer-instrumented. The native reply was visually checked for mixed case and readable layout.

Tests restore native menu/empty/reply waits, reject inconsistent NPC/result/PC states and malformed caches, preserve result rollback after a reply, and migrate prior Hall/Katrina states. Live comparisons check RAM text/name sources, full BLD payload, positions/flags/result and unchanged original credits. Native economy remains absent. All 88 original hashes match; the guard confirms **1287 reference entries unchanged**, including Git metadata, modes and mtimes. No failing milestone checks remain. This does not establish complete pixel, timing, RNG, Windows or campaign parity.

## Work and provenance

Added independent native continuation/Talk logic, checked executable-text cache loading, bounded NPC-menu rendering, explicit checkpoint, factual fixtures/verifier and native smoke scenario. State is now **160-byte BTP4**, preserving NPC context, phase/selections/result and rollback. BTP1/BTP2/BTP3 decode with empty legacy NPC occupancy. This is core persistence, not GAME support or a save/load UI.

The supplied game remains unpatched BTECH.EXE v1.03: 88 files, 641,365 bytes; six saves/three backups are 3913 bytes. [Inventory](ORIGINAL_FILES.md) and [manifest](original-manifest.json) remain authoritative. Both supplied directories are unchanged. Proprietary caches/captures/RAM/dependencies stay ignored in `work/`/`local-deps/`; no substantial GPL implementation was copied/translated. Distribution rights or legal clean-room status are not claimed.

Three local commits record evidence, implementation/tests and this review. Repository remains on `main` using the existing author identity; no Git configuration changes or pushes occurred.

## Smallest next milestone

Proposed **M2d:** recover and verify **one MAP1 NPC travel/arrival path**, including required RNG/timing, so this conversation can be reached through exploration. Keep the controlled checkpoint separate from that natural route. Class, shops, day calibration and imagery remain separate work; do not begin tactical combat or a broad campaign pass in that step.
