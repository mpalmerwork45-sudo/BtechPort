# Project status — M2d review, 2026-10-11

**M0, M1 and bounded M2a–M2d are complete. Stop here for milestone review.** MAP1 NPCs now move, arrive, stay and depart. One original Citadel conversation is reachable through normal exploration from the recorded initialized baseline. The earlier controlled Talk checkpoint remains a separate regression. Hall, Katrina/repeat and exit/re-entry still work, with original mixed-case text. The rest of M2 and the campaign remain unfinished.

## Actual working result

```sh
./scripts/build.sh
./build/btech-port --data "Original DOS"
./build/btech-port --replay tests/fixtures/citadel-arrival.actions
./build/btech-port --conversation-checkpoint --replay tests/fixtures/citadel-talk.actions
./scripts/test.sh
./scripts/test.sh --x11
./scripts/test-sanitize.sh
```

The build prepares ignored `work/talk-data.bin` from the audited executable using our proven EXEPACK reader. The C runtime reads that cache and authentic MAP1/BTTLTECH/CITADEL resources; Python is for conversion/testing only. Custom paths use `--data` and `--dialogue-data`. No Godot/.NET/reference runtime is required. [C11/SDL2 was chosen deliberately](LANGUAGE_DECISION.md); core/data/state/software rendering remain headless-testable.

Arrows move/select, Enter/Space confirms/continues, Backspace declines entry or recovers a failed choice, F3 diagnostics, R restart, Esc exit. The arrival replay walks south, gets off the narrow road, follows slot 1 north/east and returns to the Citadel before its stay expires; it opens on the authentic NPC reply. Enter returns to the Citadel menu. No controlled-presence option is used. Green NPC markers show logical positions; original sprites remain deferred. A quick fresh-game Citadel visit is still empty. The separate checkpoint is visibly labeled, supplies occupancy and disables travel. [README](../README.md) and [TESTING](TESTING.md) give full commands.

## Evidence and confidence

**VERIFIED in scope:** prior resource/movement/Citadel/Talk routes; natural NPC arrival and reply in the unpatched original; **570 complete original frame steps**, including two arrivals, matching positions, destinations, directions, packed state, timers, phase, loop timer, RNG and search state; **56 original player/story checkpoints** for the natural route. Timer expiry, zero-delay arrival, proximity gating, building suspension and persistence are covered. The 68 capture gaps with missing player movement are explicitly skipped and resumed from observations. No uninterrupted equality is claimed across those gaps.

MAP1 supplies waypoint coordinates and the eight-byte route table, plus NPC/destination names. The original outdoor loop and direction/collision routines establish region gating, gradual turns, candidate order and occupancy. Primary code/live state correct the reference's packed-nibble, position-alias and arrival-RNG labels. EXE text and the decrypted BLD still supply the conversation. See [NPC evidence](M2_NPC_EVIDENCE.md), [Talk evidence](M2_TALK_EVIDENCE.md), [Katrina evidence](M2_KATRINA_EVIDENCE.md), [Hall evidence](M2_CITADEL_EVIDENCE.md) and [audit](RESEARCH_AUDIT.md).

The final natural original run is `1791689346416199589`: whole-script ordinary keys, a read-only observer, 639 stable numeric samples and a genuine arrival/menu/reply. The earlier unmodified arrival run is `1791688646507325853`. Native arrival occurs at tick 2588; entry/reply completes by tick 2612 and return/exit by tick 2621. Native and original route snapshots use different elapsed time, so NPC/RNG equality is established by complete frame steps rather than by their dialogue snapshots. M2c's controlled run remains documented separately and never substitutes for this evidence.

**INFERRED:** unobserved local NPC steps, multiple occupants/changing counts, generalized entrances and later flags/paths. **APPROXIMATE:** NPC/player markers, panel, mixed-case font/layout, 32ms cadence, repeat/flushing/delays and edges. **UNKNOWN/deferred:** complete startup, world/recruitment dialogue, full party collision and player movement against NPCs, outer terrain, general economy/day timing, shops, combat, GAME compatibility, animation/audio and later progression. The RNG schedule models the recorded unspent baseline: credits 35, zero investments, cap 50, one pending allowance event. It is not an economy implementation. Other countdowns remain unimplemented. Class still faults at F5 04; rollback/Backspace recovery remains a prototype control. Unknown opcodes/actions are never silently skipped.

## Verification

PASS: **three CTest suites**, **420 core/corpus assertions**, **94 script assertions**, **1741 NPC assertions** and **four Python tests**; all prior projections plus the 570-frame/56-checkpoint arrival comparison. Native SDL runs close automatically: four short dummy/X11 regressions plus the entire 2621-tick arrival/reply/exit route through private-X11 SDL events. The actual native final JSON equals the headless record replay, including all NPC/RNG fields. Headless ASan/UBSan/LeakSanitizer cover core/data/pixels/VM/NPCs/corpus and all five canonical routes; SDL/backend is not sanitizer-instrumented. Original/native reply frames were inspected for mixed case and readable layout.

Each complete NPC frame also tests identical continuation after core encode/decode. Tests reject corrupt travel phases, direction, bias, context, pending-event marker and reserved bytes; legacy migration preserves only fields those formats stored. Live comparisons verify unmodified inputs, cursor/party, story/result, runtime text/full BLD bytes and the allowance precondition. All 88 original hashes match; the guard confirms **1287 reference entries unchanged**, including Git metadata, modes and mtimes. No failing milestone checks remain. This does not establish full pixels, timing, global RNG, Windows or campaign parity.

## Work and provenance

Added independent eight-slot local movement/RNG logic, MAP route loading, green NPC markers, factual numeric frame/route fixtures, a differential verifier and a full native-input smoke. State is now **224-byte BTP5**, preserving positions/directions, RNG/search/phase/tick remainder, loop timer and pending allowance-RNG event alongside prior VM/Talk context. BTP1–BTP4 decode with travel disabled because those versions never stored a travel clock; BTP4 retains its occupancy/Talk fields. This is core persistence, not GAME compatibility or a save/load UI.

The supplied game remains unpatched BTECH.EXE v1.03: 88 files, 641,365 bytes; six saves/three backups are 3913 bytes. [Inventory](ORIGINAL_FILES.md) and [manifest](original-manifest.json) remain authoritative. Both supplied directories are unchanged. Proprietary caches/captures/RAM/dependencies stay ignored in `work/`/`local-deps/`; no substantial GPL implementation was copied/translated. Distribution rights or legal clean-room status are not claimed.

Local M2d commits record research (`2de92d6`), implementation/tests (`f608c38`) and this review. Repository remains on `main` using the existing author identity; no Git configuration changes or pushes occurred.

## Smallest next milestone

Proposed **M2e:** recover **one local shop entry/purchase/return loop**, with its actual BLD/native dispatch, item change and credit delta verified against DOS. Choose one shop and one transaction after a bounded audit. This continues M2's inventory/shop foundations; full economy/day calibration, combat class, sprites and tactical combat remain separate milestones.
