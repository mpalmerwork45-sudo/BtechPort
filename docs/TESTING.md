# Build, verification and original oracle — 2026-10-17

## Sprite workflow and BattleTech-demo vehicles

The [dedicated sprite editor](SPRITE_EDITOR.md) adds direction/pose labels,
thumbnails, next/previous navigation, independent animation preview, frame
copy/paste and preview-only onion skin. The original shared mech/character gaits
and new 32-image per-unit layouts are distinguished explicitly.

Fresh checks for this follow-up:

- **109/109 Python tests**, 4.20 s, including six new sprite cases.
- **3/3 focused native suites**: vehicle/planet rules, authored formation and
  the BattleTech demo. The expanded demo test also passes after adding stock
  checks for all ten vehicles, an ordinary grouped-menu Skulker purchase,
  assignment to Cole, field movement and entry into mixed mech/vehicle combat.
- **Linux Tk world/art workflow passes**: both sprite entry points, direction
  and thumbnail navigation, copies/pastes/undo/redo, separate playback, timer
  cleanup, character aliases, scrolling, staging, Apply/discard and save/reopen.
- **15/15 Linux SDL demo screens** pass F5/F9 with identical resumed headless
  state/full-frame pixels. These include vehicle purchase, field and combat.
  The complete original two-contract demo route still reaches its final payment.
- New-project/export/reimport preserve all 19 definitions, vehicle artwork and
  `VEHICLE-SOURCE-README.md`. Existing hand-edited demo maps, tile choices and
  entrance coordinates were compared with the pre-change copy and preserved.

Screenshots inspected: `work/sprite-editor.png` and
`work/adventure-vehicle-{purchase,field,combat}.png`. The demo is version 1.1.0;
its changed package fingerprint requires a new demo game. Both reference trees
match the 1,287-entry snapshot taken before the demo update; the older historical
guard's pre-existing Git metadata qualification below still applies.

No C runtime or save format changed in this follow-up. Native Windows Tk remains
unverified, and Windows/Wine was not rerun for this Python UI/data change. The
preceding broad native/Wine/sanitizer results below are historical checks.

## World, art, vehicles and planets

The [world/art guide](M5_WORLD_ART_EDITOR.md) and
[vehicle/planet guide](M5_VEHICLES_AND_PLANETS.md) describe this new authoring
increment and its approximation boundaries.

| Check | Result |
| --- | --- |
| Native CTest regression suite | **70/70**, 44.03 s |
| Python tool/editor regression suite | **103/103**, 4.20 s |
| Focused Windows/Wine CTest | **9/9**, 28.29 s |
| Focused ASan/UBSan/LeakSanitizer | **9/9**, 0.69 s |
| Python world/art/unit tests with sanitized C tools | **15/15**, 2.01 s |
| Linux Tk | Roster, map/events, original tile/marker and world/art workflows pass |
| Vehicle SDL held screens | **7/7 Linux and 7/7 Windows/Wine**, F5/F9 and full state/pixel comparisons |

The later vehicle checkpoint expansion and Vedette bow-machine-gun correction
were checked again through the vehicle sanitizer suite and both SDL platforms.
The full C suite was not repeatedly rerun for these data/test-only refinements.
Builds used two jobs, with only one platform build running at a time.

The vehicle C scenario follows ordinary movement/entrance actions through two
planets at identical city coordinates, runs an actual three-versus-two battle
with computer orders, returns and buys a vehicle. Saves are round-tripped during
travel, combat, results and trading. Rules tests exercise all ten vehicle models,
drive terrain, movement, no jump/kick/heat and damage facings. New Python checks
cover catalogue import/re-import/export, independent unit sprite assignments,
equipment validation, separate local/planet discovery, legacy single-world fog
migration, a door contacted across a sector boundary, and atomic map/art saves.

Pixel tests check alpha-preserving transforms, rectangular animation constraints,
copying indexed tiles without modifying sources, local/shared undo and independent
clones. Real GUI checks paint pixels, flip/undo, clone frames/tiles, invoke the
palette and sprite context menus, import vehicles, animate previews, paint under
the blinking map cursor, drag cities, switch planets and save/reopen. Minimum-size
windows retain their toolbars, tile palette and marker controls. Screenshots in
ignored `work/`: `pixel-editor.png`, `roster-vehicle-editor.png`,
`editor-graphics-minimum.png`, `world-art-editor.png` and `vehicle-lab-*.ppm`.

```sh
ctest --test-dir build --output-on-failure
python3 -m unittest discover -s tests -p 'test_*.py'
python3 tools/native_smoke.py --world-art-editor-only
python3 tools/native_smoke.py --editor-visual-only
python3 tools/native_smoke.py --map-editor-only
python3 tools/native_smoke.py --editor-only
python3 tools/native_smoke.py --vehicles-only
python3 tools/native_smoke.py --windows --vehicles-only
```

The nine focused C suites match
`vehicles-multiple-planets|independent-game-complete|authored-|combat-primary-rules|combat-primary-cooling|combat-primary-physical|save-file-integrity`.
Run them with `ctest --test-dir build/sanitize --output-on-failure -R '...'`
or `python3 tools/windows_check.py --ctest -R '...'` after the appropriate build.
For the 15 sanitized Python cases, set `BTP_PROJECT_TOOL` and `BTP_HEADLESS` to
absolute paths in `build/sanitize`, then discover `test_*editor.py`.

**Reference check qualification:** 1,285/1,287 entries match the historical
content/mode/mtime baseline exactly. The two differences are `UnBattletech/.git`
and its `config`: a single `vscode-merge-base = origin/main` line was added, with
timestamps 2026-10-17 12:02:30 UTC. Removing only that line in memory reproduces
the original config SHA-256. All supplied game assets, reference source and
research files match. The reference files and guard baseline were left as found;
the strict guard's nonzero result is not presented as a pass.

These tests verify authored features and regressions. They do not establish
tabletop vehicle fidelity, DOS equivalence for new features, native Windows Tk
behavior or physical audio/driver behavior.

The [visual editor increment](EDITOR_GRAPHICS_AND_DRAGGING.md#verification)
passes **69 native CTests, 88 Python tests**, three focused Wine/sanitizer
suites per platform and all three Linux Tk workflows. Tests exercise original
tile decoding, binary Windows/Linux atlas equality, graphic picking, dragging
every marker kind, one-step history, cancellation, save/reopen and minimum sizes.

## Independent game and map/event editor

Roadmap tasks 4 and 5 now have a self-contained demonstration and a first useful
roster/map/event editor. The [implementation/verification guide](M5_INDEPENDENT_GAME_EDITOR.md)
records commands, schema/API bounds and evidence: **67/67 native CTest**,
**69/69 Python tests**, **8/8 focused Windows/Wine** and **8/8 focused sanitizer
suites**, plus **8 independent Python tests using sanitized binaries**.
Linux and Windows SDL each pass nine held F5/F9 screens with matching resumed
headless state/pixels, and the complete ordinary-input quest with battle,
payment and ending. This runs from an isolated directory containing only the
declared demo package; no original resource/cache arguments are supplied.

The real Linux Tk check creates/paints a map and overlay, uses undo/redo,
authors a branching event, places NPC/encounter records, saves/reopens both
roster and map edits, exports and launches Play here. The existing roster GUI
check remains separate. Native Windows Tk and physical audio/driver testing
remain outside those claims. Lua tests include compile errors, missing OS API,
undeclared command targets, infinite loops and allocation-budget exhaustion.
An interrupted two-file editor save restores both original snapshots on reopen.

```sh
python3 tools/native_smoke.py --independent-only
python3 tools/native_smoke.py --windows --independent-only
python3 tools/native_smoke.py --map-editor-only
```

## Authored maps, events and roster editor

Roadmap tasks 1–3 and the small roster portion of task 5 are implemented.
The [verification record](M5_MAPS_EVENTS_EDITOR.md#verification) gives the
tested behavior and limits: **66/66 native CTest**, **59/59 Python tests**,
**9/9 focused Windows/Wine** and **9/9 focused sanitizer suites**. Another
**26 Python tests** pass using sanitized player/validator binaries.
Linux and Windows/Wine each pass ten authored SDL save/load checkpoints with
matching headless state and pixels. The Linux Tk smoke edits/saves/reopens a
roster, exercises undo/redo and loadout forms, and launches the real player.
The native Windows Tk desktop remains unverified.

Repeat the full CTest/Python commands below, or focus on the authored work:

```sh
ctest --test-dir build -R authored-adventure-continuations --output-on-failure
python3 -m unittest discover -s tests -p 'test_adventure_tools.py'
python3 -m unittest discover -s tests -p 'test_editor_model.py'
python3 tools/native_smoke.py --adventure-only
python3 tools/native_smoke.py --windows --adventure-only
python3 tools/native_smoke.py --editor-only
```

These are independently authored feature tests, not DOS equivalence claims.
Original campaign behavior remains covered by the existing oracle regressions.
See the [guide](M5_MAPS_EVENTS_EDITOR.md) for package requirements, saved
continuations, editor setup and current authoring bounds.

## Broker categories and roster 0.4.0

**VERIFIED within these bounds:** Buy exposes four weight classes, with
tonnage/name ordering, scrolling, Back, Enter/Space selection and saved held
choices. The lifecycle suite covers all **31 models**, including all eight new
definitions, movement, firing every fitted weapon, cooling, repair/reload,
inspection, garage allocation, sale and salvage. Energy-only Ostsol/Cicada
records do not charge for reloads. The first 23 definitions are unchanged.

Save checks cover old flat menus and category menus against the archived
0.1.0/0.2.0/0.3.0 packs: scrolled models, Back, pending Yes/No, completed
purchases, empty classes, and new stock sorting ahead of a held selection.
Both Enhanced and Legacy category states round-trip; Legacy works with no
optional combat rule file. Invalid class/count/definition combinations fail
validation. Six-slot and original-save regression tests remain in the suite.

| Check | Result |
| --- | --- |
| Full native CTest | **64/64**, 42.86 s |
| Python tools/parser tests | **33/33**, 2.71 s |
| Focused ASan/UBSan/LeakSanitizer | **9/9**, 4.24 s |
| Focused Windows/Wine CTest | **9/9**, 30.46 s; default stack reserve |
| Linux SDL | **46/46** window scenarios |
| Windows/Wine SDL | **46/46** window scenarios |

The nine focused suites cover Updated roster/combat, original save round-trips,
Space/six-slot menus, Mech-It visits, combat shots/cooling, core formats and save
file integrity. SDL checks cover all four categories and restored full frames,
21 purchases including all eight additions, scrolling/wrap, Atlas confirmation,
full bays, selling and replacement. The Linux review sheet is
`work/broker-categories-review.png`; logs are `work/broker-categories-*.log`.
Windows category frames also match the native headless renderer after reload.

Repeat with the normal build, CTest and Python commands below, plus
`python3 tools/native_smoke.py --updated-only` and its `--windows` variant.
The authored broker/roster additions have no original-DOS counterpart. Their
campaign balance, unique mech artwork and a physical Windows run remain
outside these checks. The full original-game campaign route was not replayed;
the existing original oracle suites passed in the full native run.

Category menus add **BTPk/v46**, storing the weight class at payload byte 20005
inside Updated's BTU2 envelope. Ordinary states retain v44/v45. No existing
unit definition, original save layout, combat rule or asset was changed.

## Updated combat release

All five [LRM milestones](MECH_MOVEMENT_AND_LRM_AI.md) are implemented. The
full native run passes **64/64 suites** in 41.82 seconds; Python passes
**32/32**. The focused Updated policy test passes **25,136 checks**, covering
profile parsing/identity, six slots, old-save migration, range boundaries,
pure queries, heat/ammo/damage legality, paths through terrain and streets,
escape bounds, the arena spectator, per-unit controls and saved shot effects.
A final UI/layout check passes the Updated and original combat-UI suites.

Nine focused sanitizer suites pass with ASan/UBSan/LeakSanitizer, as do the
same nine Windows/Wine suites. Selection:
`updated-combat-policy|updated-roster-lifecycle|original-game-roundtrips|combat-primary-(shots|rules|enemy-ai|navigation|cooling)|combat-ui-save-progression`.
Build one platform at a time with **two jobs**. The policy tests use synthetic
maps/loadouts where declared; they do not replace original executable fixtures.

Linux and Windows SDL each pass **18 scenarios**: nine startup/edition checks
and nine held rules/combat/import states. The checks use real Space/F5/F9 input,
edition-aware paths and exact resumed headless state/pixels. The settings and
minimum-range panels were also visually reviewed. The held retreat/effect
files contain declared synthetic actors; loading them for UI comparison
uses the normal game's terrain, not the in-memory open-ground audit map.

The seeded audit covers **1,344 cases**, with identical normalized CSV output
on Linux and Windows. It compares Legacy, Legacy order planning with Enhanced
rules/live firing, and the complete Enhanced profile. Conditions, results,
limitations and 24-mech planning timings are in the
[release results](MECH_MOVEMENT_AND_LRM_AI.md#release-results). This measures
authored Updated tactics; original numeric behavior remains covered by the
separate executable-derived fixtures.

```sh
ctest --test-dir build --output-on-failure
python3 -m unittest discover -s tests -p 'test_*.py'
./build/btp-lrm-ai-audit 'Original DOS' > work/lrm/comparison.csv 2> work/lrm/performance.log
python3 tools/windows_check.py build-windows/btp-lrm-ai-audit.exe 'Original DOS' > work/lrm/comparison-windows.csv
python3 tools/native_smoke.py --updated-combat-only
python3 tools/native_smoke.py --windows --updated-combat-only
```

Local logs are `work/lrm-native.log`, `work/lrm-python.log`,
`work/lrm-final-native.log`, `work/lrm-sanitize.log`, `work/lrm-windows.log`,
`work/lrm-sdl-linux.log` and `work/lrm-sdl-windows.log`; scenarios, snapshots,
CSV comparisons and review images are under `work/lrm/`.
Native CTest creates the held prerequisites before the SDL checks.
The normalized comparison CSV has SHA-256
`073ece834488e754ba2c222a6b49e74d8091ddd61165eaaaabd5d3f43a2b6130`.

Current combat data remains **BTCC/v12**. Enhanced saves and the new settings
pages use **BTPj/v45** (20,480 bytes) in **BTU2**, binding rules and roster.
Ordinary Legacy/Original states retain **BTPi/v44** and their old envelopes.
Old Updated and imported Original games select Legacy; fresh Updated games
select Enhanced if their pack supplies a valid `combat.json`.

## Weapon effects, fire and mech audits

The [weapon/fire increment](WEAPON_PRESENTATION.md) passes **63/63 native
CTest suites** (41.84 seconds) and **32/32 Python tests**. Seven focused
ASan/UBSan/LeakSanitizer suites pass (5.88 seconds), as do the same seven
Windows/Wine suites (23.98 seconds). Subsequent focused checks cover the final
queued-report crop and visible-movement versus empty-microstep fire behavior.

Original observations include **2,400 weapon presentations**, **720 fire/debris
redraws**, and **1,872 movement allowances** using the dimensions of the current
roster and original loans. The weapon suite also checks 200 timed/sound
sequences, every older saved presentation stage, saved PCM and held report
pixels. Linux and Windows SDL each pass five F5/F9 animation continuations:
firing pose, missile flight, beam sound, impact and outdoor fire, with exact
headless state/pixel comparison and dummy audio.

The [requested movement/LRM analysis](MECH_MOVEMENT_AND_LRM_AI.md) adds 644
controlled native planner probes and 24 original LRM to-hit observations.
Those planner scenarios establish the recorded behavior; they are not a whole
campaign AI-quality comparison. That audit did not change AI or numeric rules;
the subsequent Updated implementation and its separate verification are above.

That increment used **BTCC/v12** and **BTPi/v44** saves,
with the same 20,480-byte payload and separate Original/Updated envelopes.
Older held presentation states and fire phases migrate explicitly. The fresh
ending uses 75,573 inputs and spy replacement 58,886 after replay regeneration.

```sh
ctest --test-dir build --output-on-failure
python3 -m unittest discover -s tests -p 'test_*.py'
python3 tools/native_smoke.py --weapon-effects-only
python3 tools/native_smoke.py --windows --weapon-effects-only
```

The focused sanitizer/Wine selection is:
`weapon-presentation-primary|world-marks-primary|mech-movement-extended-primary|combat-ui-save-progression|combat-primary-pacing|original-game-roundtrips|updated-roster-lifecycle`.
Local traces, scenario output, GUI frames and logs are in
`work/weapon-presentation/`. Explicit retrace requests and event/geometry order
are verified; physical XT CPU/blit time and speaker calibration remain outside
those claims.

## Combat pacing correction

That increment passed **61/61 native CTest suites** (41.68 seconds), together with **32/32
Python tests**. Five focused combat/roster suites pass with
ASan/UBSan/LeakSanitizer (5.08 seconds) and under Windows/Wine (17.64 seconds).
Linux and Windows SDL each pass four normal-clock pacing scenarios with
exact input/state/pixels: movement, a held attack, Enter and Space. The GUI
checks use isolated displays, generated test saves and a dummy audio sink.

The new original-executable fixture observes 48 complete waves across all six
speed settings, graphics on/off and zero/one/two attacks. The regression checks
the verified post-attack wait boundary, free movement, graphics-off pose skips,
queued reports and save/PCM continuation. Existing numeric combat, sound,
outtake, arena, spy, Updated roster and fresh-ending checks also pass. The
input-only routes were regenerated for the deliberate pacing change; the
original apprenticeship checkpoint comparison was rerun against those inputs.

The same default-speed movement-only checkpoint takes 122 native ticks before
the change and 12 afterwards: 3.904 s versus 0.384 s. This measures removal of
the erroneous native waits; physical XT wall-clock equivalence and detailed
weapon-animation cadence remain approximate. See [the audit](COMBAT_PACING.md)
for original call sites, limits, the unchanged save formats and next work.

```sh
python3 tools/make_combat_pacing_vectors.py
ctest --test-dir build --output-on-failure
python3 -m unittest discover -s tests -p 'test_*.py'
python3 tools/native_smoke.py --combat-pacing-only
python3 tools/native_smoke.py --windows --combat-pacing-only
```

The focused sanitizer/Wine selection is:
`combat-primary-pacing|combat-ui-save-progression|combat-event-primary|combat-primary-complete-encounters|updated-roster-lifecycle`.
Local before/after measurements and platform logs are in `work/combat-pacing/`.

## Updated roster 0.3.0 and building artwork

The preceding roster/art follow-up passed **60/60 native CTest suites**, **32/32
Python tests**, five focused ASan/UBSan/LeakSanitizer suites and the same five
Windows/Wine suites. All 23 models pass the lifecycle checks, including the
Grasshopper's 22 heat sinks and all ten Stalker weapons. Both earlier released
rosters load with their held menus, damaged mechs, ammunition, crew and credits.
The ten ordinary building portraits each pass exact pixel,
held-save and real-script continuation checks. All original cinema animation
IDs and the training quiz retain their rendering priority. Missing art falls
back independently; malformed art rolls back the complete content switch.

Linux and Windows SDL each pass 34 selector/trading scenarios and ten real-window
portrait/F5/F9/full-frame checks. The bounded commands are:

```sh
python3 tools/native_smoke.py --building-art-only
python3 tools/native_smoke.py --windows --building-art-only
python3 tools/native_smoke.py --updated-only
python3 tools/native_smoke.py --windows --updated-only
```

See [the recorded results](M5A_ROSTER_SLICE.md#030-roster-and-three-more-illustrations--2026-10-17)
and [asset provenance](../content/updated/art/README.md). These optional pictures
are new authored content, separate from original-game differential evidence.

## M5-P1–P5 preparation

The current **57 CTest suites** pass on Linux (41.94 seconds), under ASan/UBSan/LeakSanitizer
(133.48 seconds), and under Windows/Wine (222.08 seconds). The content-lifetime
suite now has 100 checks, including lookup boundaries. P2–P4 each passed all
native suites and exact before/after comparisons for fresh-campaign, spy and
ordinary-service routes. The existing BTPe/v40 save/cache formats are unchanged.

All **41 Windows SDL portability checks** pass, including six slots,
character/mech/map views, failed loads, nineteen held combat pages and ordered
sound. **Eleven Linux Mech-It checks** pass: four service/recruitment routes and
seven F5/F9 held continuations. Windows checks use the actual MinGW player with
the default stack reserve, on Wine/private X11; audio is queued to a dummy sink.
These checks do not measure physical Windows devices or XT speakers.

**Nineteen Python tool tests** pass, including fourteen authoring cases. The
regular `scripts/test.sh` now includes all Python `test_*.py` suites. The new
[prototype](../examples/content-demo/README.md) validates without the original
resources or a compiled player; it does not make custom units loadable yet.

```sh
ctest --test-dir build --output-on-failure
./scripts/test-sanitize.sh --core-only
python3 tools/windows_check.py --ctest
python3 -m unittest discover -s tests -p 'test_*.py'
python3 tools/validate_content.py examples/content-demo/content.json
python3 tools/native_smoke.py --windows --portability-only
python3 tools/native_smoke.py --mechit-only
python3 tools/reference_guard.py verify
```

For a local before/after comparison, retain the prior headless executable before
editing and run `python3 tools/verify_preparation.py --before PATH`. It compares
every canonical trace record and final save/frame bytes using private temporary
slots. The local pre-P2 binary remains in `work/m5-preparation/before`; it is not
a distributed fixture. See [scope and evidence](M5_PREPARATION.md) for the
increment-by-increment record and the previously verified P1 loader cases.

## Previous cadence and portability sweep

That sweep had **56 CTest suites**. Saves are **BTPe/v40**, with a
20,480-byte payload and explicit older-version migrations. Local caches are
**BTTA/v24** (373 strings, 15,226 bytes), BTCB/v11 and BTW3. Original assets,
extracted text, screenshots and RAM remain outside Git.

```sh
./scripts/build.sh
ctest --test-dir build --output-on-failure
./scripts/test-sanitize.sh --core-only
python3 -m unittest discover -s tests -p test_tools.py
./scripts/build-windows.sh
python3 tools/windows_check.py --ctest
python3 tools/native_smoke.py --windows --portability-only
```

The sanitizer command rebuilds all current core suites. Process inspection
requires running outside the restricted sandbox; leak detection stays enabled.
Native checks use a private X11 display and bounded scripts, avoiding interactive
terminal-input approvals. The Windows option runs the actual MinGW executable
under an isolated Wine prefix, with Linux headless output as its state/pixel
oracle. `--portability-only` groups keypad/diagonals, intro, menu/inspection/map,
six slots, failed loads, combat controls and sequential sound checks. Its SDL
sound device is a dummy sink; physical Windows output is outside that claim.
Individual groups remain available, for example `--windows --controls-only`.
`--completion-only` retains the earlier theatre/salvage Space/F5/F9 and cinema
checks. No DOS emulator is needed for ordinary build/test runs.

The optional original-executable generators require the local Unicorn package.
Only numeric observations and hashes enter fixtures:

| Tool under `tools/` | Current comparison bounds |
| --- | --- |
| `make_complete_encounter_vectors.py` | Eight complete outdoor/arena/prison encounters, 24 waves |
| `make_complete_encounter_vectors.py --towns` | Four additional complete Starport/MAP4 encounters, 20 waves; full records, RNG, positions, heat, facing and outcomes |
| `make_quiet_ejection_vectors.py` | Twelve original selected-header/ejection combinations, before/after complete 88-by-88 interiors |
| `make_combat_visibility_vectors.py` | 2,582 original unit visibility flags, including cross-sector positions |
| `make_cache_follow_vectors.py` | 768 continuous original inputs in both cache rooms with 1/5/8 people; all positions after each input |
| `make_story_branch_vectors.py` | 248 complete HUT/MAYOR/THEATER branches, including parties of 1/4/5/8 and ordered waits/sound/animation requests |
| `make_battle_text_vectors.py --deaths` | 384 casualty/ejection texts; 256 brief/verbose 88-by-88 interiors |
| `make_salvage_live_vectors.py` | Three complete 216-by-88 live result panels, including borders |
| `make_cache_movement_vectors.py` | 5,760 formation collision/first-contact cases in both cache rooms |
| `make_theater_text_vectors.py` | 17 film/held-page interiors with original wrapping, scrolling and final clear |
| `make_presentation_timing_vectors.py` | All 22 ANMs with three caller flags, ordered retrace/startup sound requests and all six combat speeds |
| `make_npc_timing_observations.py RUN` | 160 live idle samples, 159 consecutive state/RNG transitions; measured mean 156.825 ms |

The existing 384-loop/552-page salvage, 133-wave town combat, 10,512 town
collision, 534 cache-rule and 928 alternate-service corpora remain in use.
The two earlier 64-wave Starport traces are still bounded traces; the newly
completed Starport fights use different declared positions and seeds.

NPC/world idle timing now accumulates eleven nominal 70 Hz retraces; keyboard
input performs an immediate update and resets the countdown. Tests compare
1,100 host ticks to 224 complete outdoor frames with save/load, RNG, recruitment
and economy checks. BTPe/v40 stores two little-endian fractional clocks at
16010–16013 and an 18-byte quiet header/ejection state at 16014–16031. Old byte
clocks migrate elapsed time without RNG draws; absent old headers cannot be
reconstructed. The envelope remains 20,480 payload bytes plus 16 header bytes.

The ordinary fresh campaign now has **83,339 inputs**; spy replacement has
**66,760**. Both restore before every input. Corrected key/idle cadence required
regenerated inputs and waits. Run `make_followup_replays.py --training`,
`make_arena_outcome_replays.py`, `make_spy_replay.py` and
`make_fresh_campaign_replay.py` in that order, then
`make_campaign_checkpoint_vectors.py` for the actual apprenticeship contexts.
The continuous cache comparison complements 2,400 saved native compatibility
steps; it does not claim exact DOS recovery from malformed legacy formations.

**2026-10-16 verification:** all 56 Linux suites pass (42.10 seconds), all 56
ASan/UBSan/LeakSanitizer suites pass (135.56 seconds), and all 56 Windows suites
pass under Wine (220.12 seconds). Five Python tool tests also pass. Windows
checks exposed and fixed exclusive save creation, replacement of existing
slots, path separators in tests and stack overflow in the large combat/audio
decoder. The Windows stack reserve remains its default 2 MB. Decoder rejection
preserves existing output and is checked with leak detection enabled.

All **41 Windows SDL checks** pass: keypad/diagonals, intro/credit shortcut,
Space choices, six saves/loads, held character/mech/map views, failed-load
preservation, combat popups, individual Computer assignments and Space
interruption. Nineteen held combat pages pass F5/F9 with exact state/pixel
continuation. The combat sound case queues 44,468 nonzero samples; the return
to base case queues none, and the device backlog stays within three ticks.
The final report-buffer capacity adjustment also passes focused Linux,
sanitizer and Windows combat-panel checks. This dummy-device result is not a
physical audio recording.

See [the current report](M4_PORTABILITY_SWEEP.md) for exact evidence and limits.
Physical Windows devices and 8 MHz XT speaker calibration remain unverified.
Reference content, mode and mtime are checked against 1,287 baseline entries,
including nested Git metadata. Dependency archive hashes are recorded in
[windows-dependencies.json](windows-dependencies.json).

Historical commands/results below describe their original milestone bounds;
the current route counts and save/cache versions above take precedence.

## Earlier presentation increments (historical)

The earlier build had 53 CTest suites. Internal saves were BTPa/v36, with a
20,480-byte payload; old versions retain explicit migrations. Current caches
are BTTA/v22, BTCB/v11 and BTW3. The world seed is the original `0x020304`.
The older sections below describe earlier increments.
That increment passed all 53 regular and ASan/UBSan/LeakSanitizer core
suites and three native Starport-boundary encounter/menu/F5/F9 checks.
`encounter-placement-reachability` covers 44 legal positions with ten seeds
each, infantry/single-mech/mixed parties, 1,404 reachable enemies, unchanged
candidate records/RNG and saved offers. Its independent terrain components
reproduced the former trapped spawn at party `(1274,1078)`, seed 1: enemy ID20
at `(1298,1092)`. The same test now passes. Original code supplies the footprint
and cursor-offset evidence; the added connectivity guard is explicitly a
requested correction, not an original-parity claim.
`python3 tools/native_smoke.py --encounters-only` creates controlled encounter
prerequisites through the test executable, then compares actual SDL combat-menu
entry and F5/F9 against headless state and complete pixels for all three parties.
The optional `python3 tools/audit_encounter_placement.py` records 25 original
terrain-placement observations from its documented private DOS snapshot.
The preceding batch passed all 52 then-existing suites, five Python tool tests,
16 combat F5/F9 pages, six arena/prison/theft SDL tails, all nine building/theft
follow-up tails and the ordinary hospital conversation. The earlier historical
sanitizer corpus also passed.
The preceding 48-suite increment also passed every native M4
acceptance section and all nine follow-up tails. Campaign/story/cache sections
passed in focused reruns after an outdated ammo-editor checkpoint label was
corrected; see the current evidence for that test-harness correction.
The final reference guard checks all 1,287 entries, including Git metadata.
Only the editor's precisely identified merge-base metadata drift is restored
to its established baseline before this guard runs.
`make_live_campaign_vectors.py` adds 25 complete original waves/7,252 checks;
`make_aftermath_ui_vectors.py` adds six complete original lower-right panels.
`--controls-only` checks physical keypad arrows/Enter, bank digits with Num Lock,
and a letter/function key closing the current/legacy ending. The cache suite
checks five visible companions, stale formation recovery and the final exit
flag. Campaign tests migrate an active v29 invasion and its per-actor waypoints,
then compare continued inputs. See [current evidence](M4_FIDELITY_EVIDENCE.md).
Native focused checks: `--intro-only`, `--menu-only` and `--presentation-only`
on `tools/native_smoke.py`. The menu probe includes saving/loading from the
character, mech and overhead screens. These compare actual recorded SDL keys,
complete canonical state and exact continued pixels.
`--overhead-only` presses real Space keys through settings and the map entry,
then reads the actual X11 window pixels and checks visible terrain and F5/F9.
The four animated player-marker pixels can change between save and screenshot;
this asynchronous comparison excludes only those pixels and checks their 2x2
shape. The separate primary DOS comparison matches all 64,000 pixels with no
masks. Post-F9 comparison replays the measured idle ticks, including marker RNG.
`--m4-acceptance` bundles the native intro, six-slot menu, inspection, overhead,
audio, original-save, aftermath, crew, campaign, hospital/jail and cache checks.
`--story-only` includes paid treatment of an injured original GAME2 party.
`--followups-only` checks native newspaper/chow, cinema, both hut outcomes,
laser distribution, prison search, arena escape and spy removal/replacement
from saved ordinary prefixes.
`--cache-only` verifies terminals, doors, the Phoenix display, map-room puzzle,
ending and real F5/F9 while the map room and Phoenix display are open.

Primary numeric generators: `make_mech_view_vectors.py`,
`make_world_view_vectors.py`, `make_story_vectors.py` and
`make_speaker_timing_vectors.py`, all under tools/. They use the owner EXE in
private emulated RAM and commit only numeric projections/source identities.
`make_world_mark_vectors.py` adds 126 original world-debris ring writes and
`make_arena_finish_vectors.py` adds 28 arena completion cases.
`make_town_npc_vectors.py` adds 50 original town initialization/expiry and
45 Talk-waypoint cases. `make_town_talk_replay.py` records a 772-input ordinary
arrival/hospital conversation; `native_smoke.py --town-only` runs its SDL tail.
The town suite also compares 64 Starport/outside encounter contexts and restores
roaming, menu suspension, the hospital selector, reply and returned BLD menu.
`medical-ui-primary.json` records five complete original treatment/notice crops,
including a fully healed party with the recovery timer still active. The menu
test reaches that branch by actual treatment and a second Heal, saves the held
notice, and compares complete state after restored acknowledgement.
`test-sanitize.sh --historical-only` rebuilds and reruns the older oracle/replay
corpus without repeating the already-passing CTest suites. This batch used it
after updating a legacy assertion which expected an absent Talk category to
fault; original execution establishes the empty-room response instead.
`make_arena_outcome_replays.py` records owned/rented wins/losses and prison
loss. `native_smoke.py --arena-only` runs all five tails plus arena theft;
the headless arena suite restores before every input and tests old stuck-menu
recovery. Pre-v34 decorative marks migrate to an empty ring, because their
world origin was not stored; original GAME saves retain their exact ring.
`make_theft_vectors.py` adds 68 executed prison/arena setup cases;
`make_event_audit_vectors.py` adds 154 weapon-sound and encounter-choice cases.
The follow-up generators `make_armour_repair_vectors.py`,
`make_purchase_recipient_vectors.py`, `make_world_water_vectors.py`,
`make_world_view_vectors.py`, `make_mixed_encounter_vectors.py` and
`make_recruitment_vectors.py` document their original routine/caller boundaries.
The last adds 314 recruitment, inspection and post-wave spy cases.
`make_followup_replays.py --training` regenerates dependent ordinary routes in
order when gameplay/presentation timing changes. Routine native checks replay
short saved tails, so adding a later mission does not require repeatedly playing
every earlier mission in real time.
`make_fresh_campaign_replay.py` records 73,026 fresh-cadet inputs through the
cache ending; `make_spy_replay.py` records 56,936 through inspection, spy removal
and replacement recruitment. C integration restores and continues before
every input. Only the ending route uses the authorized credit shortcut; neither
imports an original save or edits quest flags, coordinates, skills or RNG.
World tests check three mechs and five people at a roof strip: the entire party
stops, then a deliberate turn goes around the obstacle. Each intermediate step
and moving member's gait is checked after restoration. `town-movement-primary`
adds 40 played DOS formation observations, 1,920 bounded collision decisions,
480 doorway decisions, 50 sprite anchors and 121,024 Starport infantry paths.
The corresponding `make_formation_*`, `make_town_formation_vectors.py` and
`make_combat_anchor_vectors.py` tools retain only numeric results/provenance.
Speaker timing is a nominal 8 MHz 8088 model; physical hardware filtering and
interrupt/prefetch costs remain approximate. See [M4 follow-up evidence](M4_FOLLOWUPS_EVIDENCE.md).
`make_speaker_event_vectors.py` now compares the complete ordered tone/noise
stream and nominal active PIT clocks for all eighteen effects; the native WAV
audit is stored locally under `work/m4-audit/isolated-speaker/`. No physical XT
recording or waveform equality is asserted. `make_phoenix_palette_vectors.py`
executes the original ENDMECH decoder and palette writer; the cache suite
checks all 64,000 Phoenix pixels and the native cache acceptance checks F5/F9.
`make_target_ui_vectors.py` records eight unmasked original weapon/target/
withdrawal regions. The combat UI suite checks those in addition to its nine
earlier menu/scan regions and restores before every target/withdrawal input.
`native_smoke.py --combat-ui-only` also checks actual F5/F9 on the weapon list,
target selector and both withdrawal pages. All 51 regular suites and the five
Python tool tests pass; focused sanitizer checks cover these changed paths.
`make_weapon_menu_vectors.py` adds 30 unmasked regions from 20 original held
pages. The input test keeps the original selected row, verifies both override
choices and cancellation, checks empty/destroyed weapons, and exercises Kick
and infantry selection. It restores before every input and migrates v34 foot
weapon lists. Six more held pages pass actual native F5/F9 (13 combat pages
in total). BTPZ/v35 stores presentation bits at payload offset 10233; the
combat annex and total payload lengths are unchanged. BTTA/v21 contains 331
original text ranges (14,473 bytes including the font and provenance header).

`make_weapon_warning_vectors.py` adds 36 original heat/sensor/order gate cases
and nine complete RGB regions across seven live DOS pages. `test_combat_ui`
restores before every input and checks acknowledgement order writes, delayed
weapon-list normalization, cooled-mech reopening and v35 migration. Three more
held warning pages pass native F5/F9 (16 combat pages total). BTPa/v36 adds no
payload bytes; BTTA/v22 has 334 strings and is 14,644 bytes.

The native intro starts at the logos. Use `--intro-preview` for equivalent
headless replay. Escape cancels; Ctrl+Shift+Escape quits. Shift-held K/Y/R adds
10,000 credits in every screen. Space opens settings, inspection, the overhead
map and all six slots while outdoors.

## M4 menu and combat presentation increment

The subsequent original-save increment adds a **36th CTest suite** and
23,766 assertions. All six owner GAME files roundtrip byte-for-byte; the
original reader/writer spans independently reproduce them. `BTPL/v21`
retains the original opaque envelope and flags 64..99. Focused native checks:
`python3 tools/native_smoke.py --original-save-only`. Optional executed codec
audit: `python3 tools/original_save_oracle.py`. No reference files are written.

Current increment: **35 CTest suites**, full historical regression and full
headless ASan/UBSan/LeakSanitizer pass. Four original popup crops and all title
RGB pixels match. All 18 speaker programs and 990 outtake decisions match
executed original instructions. See [M4 working evidence](M4_PROGRESS.md) for
precise scope, internal BTPK/v20 offsets and remaining M4 work.

Focused SDL verification, including actual queued combat PCM:

```sh
python3 tools/native_smoke.py --presentation-only
python3 tools/native_smoke.py --menu-only
python3 tools/native_smoke.py --campaign-only
```

Each uses private ordinary-input checkpoints and compares full recorded input,
state and pixels. Speaker timing/filtering remains approximate; outtakes have
no embedded sound track. Optional primary regeneration:
`python3 tools/make_sound_vectors.py`. The optional oracle is not a build or
runtime dependency. Historic counts below describe their original increments.

## Historical M3d–M3h acceptance

**34 CTest suites, the complete historical headless regression, five Python
tool tests and headless ASan/UBSan/LeakSanitizer pass.** Native SDL checks cover
the invasion/loss, Starport, Rex, technician/services, recruitment crest, ammo
input and title-music save contexts. The SDL backend itself is not instrumented.
Current BTPI/v18 saves have 16,384-byte payloads / 16,400-byte BTS1 files.
Historical sections retain their old format names, counts and prerequisites.

```sh
./scripts/build.sh
./scripts/test.sh
python3 tools/native_smoke.py --campaign-only
./scripts/test-sanitize.sh
```

For a focused follow-up after a core change, `ctest --test-dir build
--output-on-failure` and `./scripts/test-sanitize.sh --core-only` run the 34
current suites, including every-input campaign restoration. The full default
scripts additionally run the historical corpus and Python differential checks.
Run the full suite for milestone acceptance. Leak detection stays enabled;
sanitizer execution uses the previously approved whole script outside the
sandbox's ptrace wrapper.

The five later routes are `ordinary-invasion`, `ordinary-invasion-loss`,
`ordinary-starport`, `ordinary-rex` and `ordinary-services` under
`tests/fixtures/`. Native focused checks build the prefix with ordinary
headless inputs, save normally, then send the bounded tail through SDL.
They compare all recorded inputs, canonical state and final RGB pixels. The
498/560/991/1,193/226-input tails each take roughly 0.5–2.5 seconds on this host.
F5/F9 probes use real X11 keys and bounded continued clocks at O6 recruitment,
partial ammo input and title music. Ammo also checks Backspace erasure, Escape
clear and Space ignored. Window-close events end these probes without changing
the logical state. This avoids replaying 25 minutes of normal pacing for each
later feature, while the full core route checks its actual prerequisites.

To open a later playable state:

```sh
./build/btech-port --replay tests/fixtures/ordinary-starport.actions
./build/btech-port --replay tests/fixtures/ordinary-rex.actions
./build/btech-port --replay tests/fixtures/ordinary-services.actions
```

Regenerate input-only routes when their behavior changes:

```sh
python3 tools/make_campaign_replay.py 4 0
python3 tools/make_campaign_replay.py 4 1 --loss
python3 tools/make_later_campaign_replay.py
```

The last command tries bounded real key delays at the technician's pause to
select the non-hostile recruitment coin. It does not edit RNG, story flags or
save payloads. All earlier quiz, invasion and town requirements are reached by
ordinary inputs. Its full service route has 48,159 actions and 96,694 C assertions.

Original numeric fixture regeneration is optional research, using the pinned
Unicorn tool environment and ignored original snapshots:

```sh
python3 tools/make_world_vectors.py
python3 tools/make_party_vectors.py
python3 tools/make_service_vectors.py
python3 tools/make_audio_vectors.py
```

The comparisons cover 30 whole generated sectors / three seeds, 65 recruitment
records, 18 mixed encounter candidates, 47 service cases, 128 speaker pitches,
the full 17,409-IRQ title fingerprint and original building portraits. Native
world generation reads static numeric inputs from BTW2; `prepare_world.py`
extracts those without running an emulator. Build/runtime need no Unicorn.

Audio can be inspected without a display or audio device:

```sh
./build/btech-headless --title-preview --frame work/title.ppm
./build/btp-audio-render "Original DOS" work/title-music.wav
./build/btech-port --title-preview
./build/btech-port --mute
```

Ordinary new native games include the title; headless defaults and existing
campaign fixtures start at the initialized MAP1 baseline. Use `--title-preview`
when replaying a recording made from a new native title screen. Logs made from
a loaded save need that same `--load` context. Original GAME files are not supported.
Speaker divisor/timing and saved PCM continuation are verified; host filtering,
latency, other sound dispatch and full screen parity are not claimed. See
[M3d–M3h evidence and limits](M3D_H_PROGRESS.md).

## Historical M3c acceptance

**26 CTest suites, complete headless regression and headless
ASan/UBSan/LeakSanitizer pass.** Current saves use BTPG/v16: 4,096-byte payload,
4,112-byte BTS1 file. Historical sections below retain their milestone counts.
The SDL backend is exercised natively but is not sanitizer-instrumented.

Original comparisons add 126 live complete turns, 108 waypoint cases, 128 flame
cases, 161 pose/gait programs, 60 map-animation crops, 144 encounter constructions
and 225 result/rank/RNG cases. The controlled live harness refreshes terrain and
cover even for idle orders, avoiding stale capture prerequisites. Player-mech
destruction's pilot evacuation is outside that comparison. Native loss and
withdrawal are covered separately. No separate smoke/spread rule is invented.

```sh
./scripts/build.sh
./scripts/test.sh
python3 tools/make_training_combat_replay.py --campaign
python3 tools/native_smoke.py --training-combat-only
python3 tools/native_smoke.py --world-only
./scripts/test-sanitize.sh
```

Third combat has 5,378 ordinary inputs / 20 fresh-process save points; the
five-mission/service route has 36,755 / 54; Kick-only has 5,358 / 20;
Rick/device and sixth victory has 43,996 / 55. C integration also restores before
every input. The sixth route uses four real withdrawals and their original
skill-practice results before victory. The final-microstep effect regression
checks that presentation completes before the command menu returns.

Native X11 full input/state/frame equality passes for five-mission playback
(36,760 ticks, 39.16s), Kick-only (5,363, 5.85s) and Rick/sixth (44,001, 46.90s).
Normal durations are 1,176.32s, 171.62s and 1,408.03s: about 30× faster.
Twelve real-time F5/F9 contexts cover queued routes, Yes/No replacement, firing,
course payment, Rick dialogue/device, sixth launch and victory. A separate
real-key F4/F5/F9 check compares the generated area map and exact continued pixels.

At M3c the build prepared `work/world-data.bin` with the existing optional research
wheel, Unicorn 2.1.4 under `local-deps/python`. It executes unmodified original
terrain routines from the hash-checked EXE, with no RAM capture dependency.
The C runtime needs no emulator. BTW1 is an 80-byte provenance/area/seed header
plus 36,864 tiles, default seed 123456. This is a bounded generated cache, not an
original static world file. Nine sector hashes, all 4,096 MAP1 overlay tiles,
malformed-cache rejection, saved-clock rendering and closed border values pass.
F4 is a frontend view toggle; it does not change logical actions or campaign gates.

Regenerate new numeric fixtures only during original research:

```sh
python3 tools/make_combat_live_turns.py
python3 tools/make_combat_waypoints.py
python3 tools/make_fire_vectors.py
python3 tools/make_effect_vectors.py
python3 tools/make_terrain_animation_vectors.py
python3 tools/make_training_combat_vectors.py
python3 tools/prepare_world.py --fixture tests/fixtures/world-sectors.txt
```

See [M3c evidence and limits](M3C_PROGRESS.md). All 1,287 reference content/mode/
mtime entries match the baseline. No assets or RAM enter the committed fixtures.

## M3a manual weapons combat

The historical M3a **16 CTest suites** and the **5214-input** ordinary combat/victory/report
route pass, with **20 fresh-process continuations**. Native X11 combat,
six real-time F5/F9 contexts and headless ASan/UBSan/LeakSanitizer pass.
The shell stays stationary by the user's request; original comparisons retain
the observed moving-target AI through a dedicated comparison entry point.
See [combat evidence](M3_COMBAT_EVIDENCE.md) for prerequisites and limits.

```sh
ctest --test-dir build --output-on-failure
python3 tools/make_combat_replay.py
python3 tools/native_smoke.py --combat-only
./scripts/test-sanitize.sh
```

The 5219-tick accelerated SDL route measured **4.95s**, versus **167.01s** at
normal pacing, with identical complete inputs, final state and pixels. Real-time
save checks cover computer prompt, route preview/confirmation, weapons, target
and turn execution; each saved-state continuation and final frame matches the
headless renderer. Core checks compare original arrow glyphs in all eight
directions before/after route confirmation and after actual movement. Graphics
options cannot change numeric combat state, and the firing indicator resumes
from a save. M3a used BTPE/v14; historical M3b used BTPF/v15 as described below.

## M3b physical attacks, Mechit-Lube and two encounters

**Historical M3b: 19 CTest suites passed.** Primary comparisons add **600** physical/personal
weapon cases, **128** enemy decisions/paths and **105** encounter/apprenticeship
cases. The 35978-input ordinary five-assignment/Mechit-Lube route has 35
fresh-process continuations; the 5202-input Kick-only victory has 13. A C suite
makes 109704 assertions, restoring before each ordinary input and checking
kicks/ammunition, damaged hips, walk/run/jump heat, target cycling, defeat/flee,
course payment/refusal/decline/repeat and atomic invalid-save rejection.

```sh
ctest --test-dir build --output-on-failure
python3 tools/make_training_combat_replay.py
python3 tools/make_training_combat_replay.py --kick
python3 tools/native_smoke.py --training-combat-only
./scripts/test-sanitize.sh
```

Native X11 routes preserve complete inputs, final state and pixels. Nine new
real-time F5/F9 checks restore Kick selection/order, run/jump preview, Mechit
confirmation/completion and turn execution with exact headless continuation
and pixels. The five-mission route took **34.24s / 35983 ticks** versus its
normal **1151.46s** duration; the Kick route took **4.86s / 5207 ticks** versus
166.62s. Headless ASan/UBSan/LeakSanitizer and historical comparisons pass.

Focused tests reuse saved ordinary-play checkpoints. New original rules run
bounded instructions, avoiding repeated DOS sessions; a full input-only route
still checks progression from the start. The native replay bound is 131072
ticks to accommodate the longer funding/progression route. Normal play pacing
is unchanged. Full original multi-actor initiative/turn parity, persistent
terrain fire and owned-mech services remain unverified/unimplemented; see
[M3b evidence](M3B_TRAINING_EVIDENCE.md).

## Native commands

Run from `/home/mpalmer/BtechPort`:

```sh
./scripts/build.sh
./build/btech-port --data "Original DOS"
./build/btech-port --replay tests/fixtures/citadel-hall.actions
./build/btech-port --replay tests/fixtures/citadel-katrina.actions
./build/btech-port --replay tests/fixtures/citadel-arrival.actions
./build/btech-port --smoke-shops --replay tests/fixtures/reference-shops.actions
./build/btech-port --smoke-replay --replay tests/fixtures/reference-bank.actions
./build/btech-port --replay tests/fixtures/reference-bank-rates.actions
./build/btech-port --shop-talk-checkpoint armor
./build/btech-port --shop-talk-checkpoint weapon
./build/btech-port --conversation-checkpoint --replay tests/fixtures/citadel-talk.actions
./scripts/test.sh
./scripts/test.sh --x11
./scripts/test-sanitize.sh
```

The build script uses our proven EXEPACK reader through `tools/prepare_talk.py` to generate ignored `work/talk-data.bin` and its provenance sidecar from the audited original executable. BTT6 has 87 strings and the original 2048-byte font in 4937 bytes (420-byte header, 2469-byte text blob). It then selects installed host GCC 15.2/CMake and clears inherited Conda compiler/linker flags for its child commands. Direct builds with this shell's older Conda linker fail on host libc's `.relr.dyn`. No shell or Git configuration changes or network calls are needed. Outputs are `build/btech-port`, `build/btech-headless`, `build/btp-tests`, `build/btp-script-tests`, `build/btp-npc-tests`, `build/btp-shop-tests` `build/btp-bank-tests`, `build/btp-save-tests` `build/btp-school-tests` `build/btp-training-tests` and `build/btp-anm-tests`. Python is required for conversion/testing, not by the running C game.

The runtime reads MAP1, BTTLTECH, MECHSHAP, BTSTATS, CITADEL, COMSTAR, ARMOR, WEAPON, TRAINING, BARRACKS, LOUNGE, REPAIR, BTBORDER and all 22 ANMs directly, plus the local EXE text cache. For another resource/cache location, run `python3 tools/prepare_talk.py --data DIRECTORY --output CACHE` and pass `--data DIRECTORY --dialogue-data CACHE` to the executable. Wrong source/image hashes, malformed caches and missing files fail visibly. See [Talk provenance](M2_TALK_EVIDENCE.md) and [banking evidence](M2_BANKING_EVIDENCE.md).

SDL2 2.32.4 runtime is installed; development headers are under ignored `local-deps/sdl2/`. Conventional SDL2 installations also work; `SDL_GetTicks64` requires 2.0.18 or later. With a normal compiler environment:

```sh
python3 tools/prepare_talk.py
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build
```

Core/data/pixel tests build without SDL using `-DBTP_FRONTEND=OFF`. Synthetic CTest suites can build without original assets/cache; corpus/native checks require them. The Windows build is now checked under Wine; see the current verification above.
Physical Windows drivers and hardware remain unverified.

Arrows move/select; held perpendicular arrows form a diagonal while walking/driving. Keypad 1/3/7/9 and End/PgDn/Home/PgUp move diagonally; keypad 2/4/6/8 moves cardinally. Enter/Space confirms/continues; Backspace declines entry or recovers unsupported choices; F3 toggles diagnostics; F5 saves; F9 loads; R restarts; Esc quits. In bank amounts, digits type (maximum seven), Backspace erases, Escape clears to 0 without quitting/submitting, and Enter submits; Space is ignored. The 32ms step, key repetition, delays and flushing are **APPROXIMATE**. Replays accept lowercase `up`, `down`, `left`, `right`, `up-left`, `up-right`, `down-left`, `down-right`, `idle`, `accept`, `cancel`, `0`–`9` and `clear`, one per line:

```sh
./build/btech-port --record work/my-walk.actions
./build/btech-headless --replay work/my-walk.actions --trace --frame work/my-walk.ppm
```

Records include idle ticks. Restart is visibly refused while recording because reset is not a replay action. Unknown actions fail. The VM supports the bounded Citadel, bank, two-shop and Mechit-Lube menus, Hall, Katrina/repeat, `F5 0C` local Talk, F6 Yes/No, positioned cash/account text and exit/re-entry. Bank native actions `06/07/08` handle accounts/buy/sell with serializable company selection and amount entry. Class services `04/05` implement the verified personal-skill courses. Training services `01/02/03` implement six MechWarrior launch/result/return loops; action `43` delivers Rick's lounge invitation. Mechit-Lube actions `14/15/16` handle Jason's apprenticeship and `17/20/29/44` support the early no-owned-mech service/menu contexts. Later assignments, owned-mech services and nonlocal Talk contexts remain explicit faults. Failed choices roll back story/result/cash/investment/equipment/technician writes across restored pauses; Backspace recovers to the menu. This recovery is a prototype control, not original behavior. Headless faults return failure and can still write diagnostic frames.

## ComStar and both shops' Talk oracle

```sh
python3 tools/reference_session.py --script tools/reference-bank.json
python3 tools/reference_session.py --script tools/reference-bank-rates.json
python3 tools/reference_session.py --script tools/reference-armor-talk.json
python3 tools/reference_session.py --script tools/reference-weapon-talk.json
python3 tools/verify_m2f.py
python3 tools/verify_m2f.py --live
build/btp-bank-tests "Original DOS"
python3 tools/native_smoke.py --m2f-only
python3 tools/native_smoke.py --bank-input-only
```

The committed bank/rates fixtures use ordinary inputs and an unpatched working
copy. They compare 33 + 29 checkpoints, all three balances and exact original
text hashes. `bank-frames.csv` records 460 stable samples during the fixed-player
outdoor wait; every one of its 459 complete steps matches cash/accounts, cap,
all eight NPCs, phase/timer/RNG/search/bias. Both wraps match: `[30,1,1]` plus
cash 3 becomes `[31,0,2]` plus cash 18, then assets 51 suppress the next updates.
Original adjacent-human collision establishes a single half-coordinate footprint.

Shop Talk has 28 Armor and 48 Weapons ordinary-route/empty checkpoints, then 11
controlled occupied-handler checkpoints per shop. Each explicit precondition
places slots 1 and 4 in the room with timers 5/7 and result 91; a before/after
audit records exactly the occupancy/result writes in the child emulator. No
resource, executable or save is patched. Default gameplay uses ordinary NPC
travel. Controlled snapshots establish name ordering, Done, remembered selection,
both replies/result clearing and return; they do not prove natural occupied-shop
arrival. Outdoor post-exit timers are excluded from that disabled-travel demo.

`--live` rechecks all 160 checkpoints against the ignored original RAM exports,
full BLD/native text bytes and cursor/party. To export a new run, use
`--export bank|bank-rates|armor-talk|weapon-talk --reference-run DIRECTORY`;
do not overwrite factual fixtures until its observation/projection is reviewed.
The original numeric editor buffer after a receipt may contain formatted cash,
not the earlier typed amount. Recorded keys/frames establish the latter.

The bank C suite restores/re-encodes/continues all 7297 ticks of six replays and
checks synthetic arithmetic/input/atomic-validation/migration/rollback cases.
Native X11 runs bank (419 ticks), rates (2247), Armor Talk (19), Weapons Talk
(19) and synthetic editing (349); each full action record and final JSON equals
headless replay. The synthetic editor check appends leading zero, digits,
Backspace, Escape clear and Enter to the verified bank-entry prefix, and ends
with cash 5/investments `[30,0,0]`. It is not an additional DOS observation.
Whole scripts use private displays and close automatically; no terminal input
is sent one key at a time.

## Two-shop oracle and replay

```sh
python3 tools/reference_session.py --script tools/reference-shops.json
python3 tools/reference_session.py --script tools/reference-shop-boundaries.json
python3 tools/verify_m2e.py
python3 tools/verify_m2e.py --reference-run work/reference-runs/1791690976267363973
python3 tools/verify_m2e.py --boundaries --reference-run work/reference-runs/1791691394449093827
python3 tools/native_smoke.py --shops-only
```

Both DOS runs use ordinary inputs, private displays, read-only snapshots and
unpatched work copies. The first records 50→0 for the flak vest and 15→13 for
the knife; final equipment is weapon 1, armor 1/protection 25. The second checks
No for both goods and insufficient funds for another vest, preserving equipment.
Its longer final wait receives another allowance (13→28). Modes/highlights are
checked against original frames; expected PCs/text ranges come from original
BLD paths, not a captured guest IP. [Shop evidence](M2_SHOPS_EVIDENCE.md) records
primary executable addresses and discrepancies in provisional native labels.

Committed fixtures are numeric fields, actions, resource offsets and hashes;
proprietary text and memory stay ignored. To re-export a run, use
`verify_m2e.py --export DIRECTORY` (add `--boundaries` for the second script).
Idle ticks derive from consecutive D323 observations, and that counter matches
at every checkpoint. The placement of original NPC frames between road keys
and wall-clock timing are excluded from route parity. Existing complete-frame
NPC verification remains separate.

## Save/load and paid Class verification

```sh
build/btp-save-tests "Original DOS"
build/btp-school-tests "Original DOS"
python3 tools/verify_m2g.py
python3 tools/verify_m2h.py
python3 tools/native_smoke.py --school-only
./build/btech-port --smoke-replay --replay tests/fixtures/reference-class-funded.actions
```

F5/F9 uses `work/player-save.btp` by default; `--save-file FILE` selects a slot.
`--load FILE` restores before a replay and `--save FILE` writes on successful
exit. Failed loads leave the current session intact; loading while recording is
refused. Native notices appear in the window title. Original GAME files are not
supported. See [save evidence](M2_SAVE_EVIDENCE.md) for failure and durability scope.

PASS: 12520 save-file assertions across 137 replay snapshots; 31 fresh-process
states with exact full-JSON restore and 1024-tick continuation. Native F5/F9
restores a partially entered bank amount, including after a missing-file error.
M2g BTP7/BTS1 migration and independently recomputed valid-CRC/invalid-state
rejection are checked.

PASS: 59197 school assertions; all subjects/ranks, price boundaries, mastery,
32-bit cash borrow, Withdraw, rollback, saturated countdowns and migration.
The 15 audit and 49 funded original checkpoints match exact text hashes,
cash/skills/story/menu state and frame counter. All 3271 route ticks restore
and continue identically. The two new frame captures match 460 complete outdoor
steps / 462 samples over all 70 observed NPC/RNG/economy fields; ranks and
countdowns use separate RAM checkpoints. Native SDL sends all 3093 funded-route
ticks and its complete final state equals the recorded headless replay.

The ordinary route funds a 75-credit course from 87 cash, raises the first skill
to rank 1, enforces cooldown 255→0 outdoors, then offers tuition 200 and refuses
with cash 27 unchanged. Higher ranks and the other subjects are supported by
primary instructions and boundary tests, not additional live paid-course traces.
Personal Class leaves mission counter 0 unchanged. M2j adds the first MechWarrior mission and barracks sleep separately. See [training evidence](M2_TRAINING_EVIDENCE.md).

## First mission, all goods, lounge and diagonals

```sh
build/btp-training-tests "Original DOS"
python3 tools/verify_m2j.py
python3 tools/native_smoke.py --training-only
python3 tools/native_smoke.py --diagonal-only
./build/btech-port --replay tests/fixtures/reference-diagonal-mech.actions
./build/btech-port --smoke-replay --replay tests/fixtures/reference-mission-pass.actions
python3 tools/reference_session.py --script tools/reference-mission-pass-sleep.json
python3 tools/reference_session.py --script tools/reference-full-shops-lounge.json
python3 tools/reference_session.py --script tools/reference-lounge-rick.json
python3 tools/reference_session.py --script tools/reference-diagonal-human.json
python3 tools/reference_session.py --script tools/reference-diagonal-mech.json
```

All 325 original checkpoints pass: mission success/sleep 100, failure 69,
full goods/ordinary lounge 77, controlled Rick lounge 8, diagonal human 19,
diagonal mission/entry 52. Text hashes derive directly from original BLD/EXE;
fixtures contain numeric projections and actions. Every observed new phase
saves, restarts and continues through an identical bounded tail. Quiz RNG/answer
selection, mech/human gait and terrain penalties are compared explicitly.
The 2219 training assertions include quiz failure, all loan choices, timer
boundaries, sleep/repeat gates, Rick/device state, invalid saves and continuation.
Full shop tests exercise exact/short/high-word funding, No and replacement
for all sixteen goods. Disk continuation now includes all 22 logical actions.

`full-goods` uses an audited 20000-credit test budget. `lounge` uses the explicit
Rick prerequisite from `lounge-rick-context.json`; default Talk supplies no
story precondition. Mission/diagonal routes use ordinary gameplay inputs.
The failed mission's corner wait is normalized to four native timer updates;
exact DOS CPU-time parity is excluded. Original dream animation 8/parameter 1 is now played and saved by M2m; sound remains absent.
The native quiz uses original diagram pixels and font with an approximate pointer UI.
M3a adds third-assignment manual weapons combat; later launches still fail
visibly before changing progress or the loan.
See [M2j evidence](M2_MISSION_EVIDENCE.md) for addresses, run identities and limits.

Native mission success/failure/all-goods/lounge runs match complete inputs and
final headless JSON. Real F5/F9 restores changed quiz, active mission and dream
states. The diagonal check sends actual X11 key events for keypad, Home/PgUp/
End/PgDn, simultaneous perpendicular arrow chords, releases and bank keypad
amount editing; complete native records and final JSON match headless replay.
The default full native smoke includes both new groups. Private displays close
automatically and use no interactive terminal input.

## M2k–M2m rubble, cadet gates and animations

```sh
python3 tools/verify_m2kl.py
python3 tools/make_training_replay.py
python3 tools/verify_animations.py --frame work/rubble-result.ppm --dream-frame work/rest-wake.ppm
python3 tools/native_smoke.py --rubble-only
./build/btech-port --smoke-replay --smoke-fast --replay tests/fixtures/ordinary-rubble-story.actions
```

The first verifier compares 181 original state/text checkpoints under three
explicit original RNG prerequisites and tests 100 fresh-process continuations.
The second runs an independent 3940-input native progression with no edits;
it writes `work/rest-wake.ppm`, while the first writes `work/rubble-result.ppm`.
The animation verifier checks all 22 files, original RAM observations, font
identity and both pixel crops. Source images/RAM remain ignored; fixtures store
only numeric observations and hashes. ANM timing normalizes 70Hz VGA retraces
onto the fixed 32ms clock, excluding original decode cost and keyboard buffering.

A fresh ordinary original run can be captured with:

```sh
python3 tools/reference_session.py --script tools/reference-rubble-story.json
```

The audited successful run is `work/reference-runs/1791705480602565515`.
Exporting its facts uses `verify_m2kl.py --export` and
`verify_animations.py --export`; the ordinary native route generator uses
`make_training_replay.py --generate`. Export/generation requires that ignored
original capture; ordinary regression execution uses committed fixtures and
local original assets only. Do not replace factual fixtures without reviewing
their projection. [Evidence and limits](M2_RUBBLE_ANIMATION_EVIDENCE.md) document
the long-wait RNG gap, live Wasp coverage and instruction/test-only Locust branch.

## Historical internal state encoding (M3b)

The table below describes that earlier milestone; current BTPe/v40 additions
are documented above and in `port/core/game.c`.

`BTPF` (version 15) was the then-tested **2048-byte internal core encoding**
(2064-byte BTS1 file), stored by F5/F9 inside a 16-byte length/CRC envelope.
Its annex adds seven-unit combat, enemy orders/paths, target selection, Kick
and defeat; technician/apprenticeship and their rollback values persist too.
BTPD/v13 and BTPE/v14 migrate from their historical 1024-byte payloads.
BTPD introduced combat and the high allowance byte; BTPE added a
three-tick firing-indicator countdown. BTPD migration starts without an active
indicator. Previously planned target paths in old combat saves cannot move the
stationary shell after loading. BTPC/v12 retains its historical 512-byte size
and migrates with no active combat. Original GAME compatibility is unimplemented.

Earlier saves retain quiz/mission/entry direction, story/checkpoint bytes, cap
rollback, animation request/progress and walking indices; older saves start
missing gait at the first frame for the stored facing. BTP7 (384 bytes) migrates
with zero personal-skill ranks and no active course. BTP6 (320 bytes) migrates
with empty investments/no bank service while preserving cash/equipment. BTP1
(24), BTP2 (64), BTP3 (128) and BTP4 (160 bytes) disable travel because they
never stored its clock. BTP4 retains Talk/occupancy; earlier versions carry none.
BTP5 (224 bytes) migrates the recorded unspent baseline to cash 35 when its
pending allowance marker is set, otherwise 50 when travel is enabled. Legacy
equipment defaults to zero where missing. Migration reconstructs only fields
the old format could represent.

Fields through byte 449 keep their historical positions; magic/version is
BTPF/15. BTPA/v10 (448 bytes) and BTPB/v11 (512 bytes) migrate with no active
animation. BTPB introduced rubble/mech-rank fields; BTPC added cutscene progress.
Words/ticks are little-endian; reserved bytes must be zero. Fields added since BTP2:

| Byte offsets | BTPF field |
|---|---|
| 59–65 | Story bytes 16–22; bytes 0–15 remain at 24–39 |
| 66 | BLD text span count, bounded to eight |
| 68–99 | Eight 16-bit `(offset,length)` pairs; unused pairs zero |
| 100–122 | Story rollback checkpoint |
| 123 | Checkpoint-valid byte |
| 124–127 | Talk phase, remembered NPC selection, occupant count/mask |
| 128–143 | Eight packed-state/occupancy pairs |
| 144–147 | Room, reply actor, D33A result, D339 recruitment context |
| 148–149 | Result rollback checkpoint, visible scenario marker |
| 150–152 | NPC system disabled/lazy/ready, original phase, native tick remainder |
| 153–159 | Three RNG bytes, 16-bit search counter, candidate bias, explicit fault |
| 160–199 | Eight `(packed X word, packed Y word, direction byte)` records |
| 200–201 | Outdoor loop timer, assets-below-cap marker (validated against cash + investments) |
| 67, 202–223 | Reserved zero |
| 224–232 | 32-bit credits, 16-bit cap, weapon/armor/protection bytes |
| 233–237 | Story byte 39, its rollback, Yes/No selection, native service, cash insertion index |
| 238–241 | 32-bit displayed cash snapshot |
| 242–272 | Independent remembered selectors for menu IDs 0–30; unsupported IDs zero |
| 273–277 | Confirmation target, current text column/row, cash-present marker |
| 278–293 | Eight column/row bytes for original text spans |
| 294–300 | Credit/weapon/armor/protection rollback checkpoint |
| 301–319 | Reserved zero |
| 320–331 | Three unsigned 32-bit investment balances |
| 332–343 | Three investment rollback balances |
| 344–347 | Bank phase, company, outcome, clipped-request flag |
| 348–355 | Unsigned 32-bit available balance and transferred amount |
| 356–363 | Seven-digit editor buffer with zero terminator/tail |
| 364 | Account-display flag |
| 365–383 | Reserved zero |
| 384–386 | Three personal weapon-skill ranks, each 0–4 |
| 387–389 | Skill rollback ranks |
| 390–393 | Course phase, selected subject, prior rank and outcome |
| 394 | Player walking index, original frame minus 16 (0–15) |
| 395–402 | Eight NPC walking indices (0–15) |
| 403–406 | Story indices 45,46,47,51 |
| 407–410 | Rollback values for indices 45,46,47,51 |
| 411–412 | Allowance-cap rollback word |
| 413–416 | Animation request/parameter, mech-result insertion selector/index |
| 417 | Pending entrance action, including diagonals |
| 418–424 | Quiz phase, selected label, round, point, failure and 16-bit used-point mask |
| 425 | Reserved zero |
| 426–433 | Mission phase, corner/warning/idle, gait/direction and 16-bit elapsed |
| 434–436 | Assignment, rubble objective index and underlying tile |
| 437–440 | Two mech skill ranks and their rollback values |
| 441–445 | Animation active context, kind, step, cycle and hold |
| 446–449 | Remaining retraces and fixed-clock fractional remainder |
| 450–451 | Story/checkpoint index 52: high allowance bytes |
| 452–455 | Technician, apprenticeship flag and rollback values |
| 456–459 | Story/checkpoint indices 24 and 32 |
| 460–511 | Reserved zero |
| 512–877 | Combat units (125-byte records plus position/heat), UI/options/orders, counters, paths and last shot |
| 878 | Firing-indicator countdown, 0–3; reserved zero in BTPD/v13 |
| 879–895 | Reserved zero; legacy combat prefix remains 384 bytes |
| 896–908 | Unit count, current target, Kick, defeat, last attacker/target and seven infantry flags |
| 909–1713 | Five additional combat records, movement/gait state and paths |
| 1714–1802 | Additional enemy modes, six enemy order lists and fired masks |
| 1803–2047 | Reserved zero |

BLD text spans concatenate exact bytes without added separators. Native Talk suspends after its operand, clears BLD spans and assembles text from checked EXE/MAP1 references. Bank text combines original literals, numeric input and positioned account values; the digest represents that documented concatenation, not pixel equality. Original case/spaces and bank color controls survive the cache. Decoding validates native PC, occupant mask/count, actor, result, bank phase/editor and checkpoint consistency. More than eight BLD spans, malformed operands/targets, unsupported indexes and exhausted instruction budgets stop explicitly. The sparse story model covers `D30C[0..22]` plus indices 24,32,39,45,46,47,51,52 and explicit native contexts. Index 23 is the separately modeled outdoor timer; other indexes in 23–38 remain unsupported in the VM. CLI `story_flags` keeps its prior 23-byte projection; Mechit-Lube flags, `shop_refusal`, `recruitment`, `talk_result`, `device` and `allowance_cap` expose the additional fields separately. Restore callers must supply the active slot's BLD via `btp_building_bld`. Immediate purchase/account-display services finish inside one tick; Talk and bank input serialize suspended services. Receipts wait on original bytecode FB, without an extra native pause.

## Passed checks and scope

| Check | Actual result | What it establishes |
|---|---|---|
| CTest sprites | PASS, 848 assertions | Atlas bounds, black outline/transparency, palette, 8×8/24×24 clipping, extreme coordinates, eight gait programs, water rule and BTP8/BTP9 migration. |
| CTest core | PASS, 269 synthetic assertions | RLE/map bounds, movement/collision, edges, state restoration/validation, palette and mixed-case glyph regression. |
| CTest script | PASS, 58 synthetic assertions | BLD size/decrypt/bounds, unsupported operations/index/font/scene/menu, byte wrapping, signed tables, concatenation, span limits and native suspension/return. |
| CTest NPC | PASS, 24 synthetic assertions | RNG vectors, first/later allowance wraps, proximity freeze, positive/zero arrival, expiry, timer guard, BTP9 validation/restoration and BTP4 migration. |
| CTest shops | PASS, 40 synthetic assertions | Variable menus/targets, F6 branches, F0 bounds, sparse state, dynamic cash bounds, native-service budget. |
| `build/btp-shop-tests "Original DOS"` | PASS, 33253 assertions | Restore/continue all 6137 ticks of two full shop replays; 49/50 and 1/2-credit boundaries, No, unsupported-context recovery and all sixteen goods, malformed/atomic state, allowance overshoot, BTP5 migration. |
| Shop differential | PASS, 56 purchase + 65 boundary checkpoints | Original cursor/party, complete RAM BLDs, exact text hashes, menus/confirmation, credit/result/equipment changes and return; ordinary inputs only. |
| Native X11 shops | PASS, 3064 ticks | SDL input/presentation through both purchases and outdoor return; full final JSON matches headless recorded replay. |
| CTest bank | PASS, 16 synthetic assertions | Pre-update cap comparison, account RNG schedule, wrapping arithmetic and Baker growth threshold. |
| `build/btp-bank-tests "Original DOS"` | PASS, 78178 assertions | Restore/re-encode/continue all 7297 new replay ticks; amount editing, unsigned transfers across all three companies, zero/clipping/refusals, BTP6 migration, rollback and malformed atomic state. |
| Bank/shop Talk differential | PASS, 160 original checkpoints | 33 bank + 29 rates + 28 empty Armor + 48 empty Weapons + 11 occupied per shop; original cursor/party, BLD/native text, cash/accounts, flags/results/menu memory and return. Occupied handlers use controlled preconditions. |
| Bank outdoor oracle | PASS, 459 complete frame steps / 460 samples | All 70 numeric fields, two wraps, account returns/allowance, complete NPC/RNG/loop/search equality; no capture gaps skipped. |
| Native X11 bank/Talk/editor | PASS, five checks | Bank 419, rates 2247, occupied Armor/Weapons 19 each, synthetic editor 349 ticks; complete recorded input/final JSON equality with headless replay. |
| `build/btp-tests "Original DOS"` | PASS, 5776 assertions including synthetic checks | 14 MTPs/12 graphics; prior Citadel routes; Talk Done/result/retention, exact lengths, restored pauses, corrupt state/cache, rollback, BTP1/BTP2/BTP3 migration. Multiple occupants/wrap are structural tests, not live parity claims. |
| `build/btp-script-tests "Original DOS"` | PASS, 95 assertions including synthetic checks | Authentic menu/Hall/Katrina texts/effects, repeat denial, retention, exit, native Class/menu suspension and F5 0C continuation. Unknown-action rollback remains covered using a test-owned corrupted BLD copy. |
| Python unpacker/converter | PASS, 4 tests | Synthetic stream/header/run rejection, actual image hash/anchor, deterministic cache/address/string-hash provenance and wrong-version rejection. |
| Movement projection | PASS, 31 original states / 30 actions | Positions/gate match original cursor and party[0], including repeated wall/hedge blocks; all 88 original hashes match. |
| Hall projection | PASS, 16 original checkpoints / 20 native states | Positions, gate, 16 bytes, pending step/exit, seven text digests, six waits and retained selection. |
| Katrina projection | PASS, 20 original checkpoints / 20 native states | Positions, gate, bytes 0–21, first-visit persistence, denial, re-entry highlight and four text hashes. Byte 22 only compared before outdoor countdown resumes. |
| Talk projection | PASS, 10 controlled + 3 unmodified empty-room checkpoints | Positions, bytes 0–22, exact 42-byte menu/162-byte reply/47-byte empty response, Done preserving result, NPC clearing result, both selections and return/exit. NPC arrival and post-exit timers excluded. |
| NPC oracle and natural route | PASS, 1741 NPC assertions; 570 complete frame steps, two arrivals, 56 player/story checkpoints | Exact observed positions/destinations/directions/timers/phase/loop/RNG/search; 68 player-movement gaps skipped. Persistence at every checked frame; ordinary-input arrival/reply/return with original text hashes and building suspension. |
| Native SDL dummy/private X11 | PASS, four short regressions plus X11 natural arrival | Window, SDL input/presentation, bounded exit and records: movement 8 ticks; Hall/Katrina/Talk 24 each; full arrival/reply/exit 2621. Actual native final JSON equals headless replay including NPC/RNG. |
| ASan/UBSan/LeakSanitizer | PASS, headless core/data/pixels/VM/NPC/economy/corpus and all earlier/new bank/shop-Talk replays | No detected address, undefined-behavior or leak errors in these paths. SDL/backend not sanitizer-instrumented. LeakSanitizer requires execution outside the ptrace sandbox. |
| Training/diagonal C suite | PASS, 17269 assertions including synthetic checks | Quiz failure and loan choices, timer thresholds, terrain and blocked diagonal gait, sleep gates, Rick/device branch, invalid saves and continuation. |
| M2j differential | PASS, 325 checkpoints | First mission success/failure/sleep, all goods, lounge and human/mech diagonals; exact text/state/gait/terrain and fresh-process continuation. Controlled funding/Rick prerequisites and timing normalization remain explicit. |
| M2k/l comparison | PASS, 181 original checkpoints and 100 fresh-process restarts | State/text/rubble/gating under three explicit original RNG prerequisites; unseeded long-wait NPC/RNG parity remains open. |
| Ordinary native progression | PASS, 3940 logical inputs | Both results, sleep and rested third briefing with no state/RNG edits. |
| ANM decoding/oracle | PASS, 198 frames across 22 files; 39 original buffers | Independent C/Python byte equality, original packed-frame hashes/offsets, malformed input and sequence/timing checks. |
| Font/border/dream pixels | PASS, 2048 font bytes, 183 border cells, 7744 dream pixels | Original RAM font, frame geometry/colors and final O8 RGB crop; whole-screen parity is not claimed. |
| Save files | PASS, 17413 assertions / 175 replay snapshots | File integrity, atomic rejection, legacy migration and every action's restored continuation. |
| Combat instructions | PASS, 2099 primitive + 896 shot + 779 navigation + 648 cooling cases | Original numeric rules/records/RNG; separate LOS bounds diagnostic is not counted as original parity. |
| Combat turn projection | PASS, 35 original turns | Original moving-target AI enabled explicitly; positions/directions/heat, full record hashes and RNG through destruction, controlled prerequisites. |
| Combat C integration | PASS, 20120 assertions | 5214 restored input continuations, stationary shell, arrow glyphs/actual movement in eight directions, graphics-independent rules, three loan/withdrawal paths and v12/v13/v14 migration. |
| Combat ordinary replay | PASS, 5214 inputs and 20 fresh-process continuations | Three assignments, victory/report/exit and 500 allowance cap; no state/RNG edits. End-to-end combat victory uses Locust. |
| Combat native X11 | PASS, 5219 ticks and six F5/F9 contexts | Exact complete input/state/frame equality; real-time restored continuation and pixels. Accelerated route 4.95s; normal tick duration 167.01s. |
| Reference guard | PASS, 1287 entries | Both supplied trees match content/mode/mtime/entries/symlinks, including reference Git metadata. Access times excluded. |

Repeated canonical outputs are identical and unknown input fails. Original credits stay 35 in the short Citadel traces. M2e added two purchases; M2f adds actual balances and returns in the local 50-cap economy. Wider economy/day progression remains deferred. Screens establish modes/highlights/order; PCs are bytecode-derived. None of these checks establishes full timing, global RNG, pixels, Windows or campaign parity.

`test.sh --x11` adds private-display SDL scenarios and closes automatically.
Long replays use `--smoke-fast`; each logical 32ms tick still polls SDL, consumes
one action and renders a frame. Final records/state/pixels are compared with
headless replay. The 3945-tick rubble/story run measured 3.63 seconds versus
126.24 seconds at normal pacing (about 35× for this replay). Short real-key,
walking/animation and F5/F9 probes retain real-time pacing. Normal gameplay
and smoke runs without this flag keep normal pacing.

Use `python3 tools/native_smoke.py` for the complete native suite. Focused
options are `--shops-only`, `--m2f-only`, `--bank-input-only`, `--save-only`,
`--school-only`, `--sprites-only`, `--training-only`, `--diagonal-only` and
`--rubble-only`. The latter covers an ordinary two-mission/rest route and four
real-time F5/F9 animation/pickup/carrying checkpoints. Test complete scripts;
no interactive terminal input is sent. Plain `test.sh` needs no display/audio
device. Sanitizers cover core/data/software rendering, without instrumenting
SDL/backend. Run focused checks during changes and the full suites at a
milestone boundary; do not repeatedly recapture unchanged DOS observations.

## NPC arrival original comparison

[NPC evidence](M2_NPC_EVIDENCE.md) records primary addresses, the initialized baseline and the limits of the RNG schedule:

```sh
./build/btech-port --replay tests/fixtures/citadel-arrival.actions
python3 tools/verify_m2d.py
build/btp-npc-tests "Original DOS" tests/fixtures/npc-frames.csv
python3 tools/reference_session.py --script tools/reference-npc.json
python3 tools/verify_m2d.py --reference-run work/reference-runs/1791689346416199589
```

Substitute the printed directory for a fresh reference run. The whole JSON script uses ordinary keys, a read-only NPC observer and an adaptive bounded wait for arrival. The observer polls only its child emulator and requires two identical numeric projections before retaining a sample. `wait-npc` observes genuine hidden coordinates/nonzero stay timer; `keys-fast` reaches the entry prompt before expiry. No guest context is injected. Raw screenshots/RAM stay ignored; the committed CSV/JSON contain only numerical facts, actions and hashes.

The final original M2d run yielded 639 stable observations. The verifier matches 570 complete outdoor frame steps and two arrivals, explicitly skipping 68 gaps with missing player movement before resuming from the next captured state. Each verified frame checks identical continuation after current BTPF encode/decode. It compares NPC position, destination, direction, packed/timer pairs, phase, loop timer, RNG and search/bias; it does not claim equality across skipped intervals. The first wrap consumes three account RNG draws, later wraps none, for that unspent 35-credit/50-cap baseline. M2f now extends the model to actual balances/returns and another 459 gap-free full frame comparisons. M2h adds the saturated outdoor countdowns for story bytes 20–22; wider day/cap progression remains deferred.

The default native route has 2612 logical ticks, including idles, and ends on the original 162-byte reply. Fifty-six player/story checkpoints compare by non-idle input ordinal; elapsed-time NPC fields at route checkpoints are excluded from this projection. The frame corpus establishes their step behavior separately. Native entry/building suspension and return/exit pass. `--smoke-arrival --replay tests/fixtures/citadel-arrival.actions` sends the entire route through SDL events, appends nine return/exit/idle actions, and closes at tick 2621. The X11 test compares actual native JSON with its headless replay, including every NPC/RNG field.

Original/native reply frames were visually inspected for mixed case and readable text. M2i now replaces the green markers with verified atlas sprites; the historical M2d trace did not record animation frames. Full startup, exact wall-clock cadence, world/edge/party rules, player movement against NPCs, global RNG/economy and pixels are outside parity. The separate M2c handler checkpoint keeps travel disabled and is never used to establish natural arrival.

## Talk original comparison

A quick Citadel visit from the normal initialized start is empty. Talk shows its original response and returns. The earlier isolated NPC handler is also playable in a visibly labeled controlled scenario:

```sh
./build/btech-port --conversation-checkpoint --replay tests/fixtures/citadel-talk.actions
python3 tools/verify_m2c.py
python3 tools/reference_session.py --script tools/reference-talk.json
python3 tools/verify_m2c.py --reference-run work/reference-runs/1791685774441704966 \
    --empty-reference-run work/reference-runs/1791684527855747449
```

The native replay opens on the NPC reply; Enter/Space returns to the Citadel menu. Without `--replay`, five Up, Enter, three Down, Enter opens the NPC menu. Done returns immediately. The NPC opens the authentic reply. Both menus retain selection independently. Recording/replaying this scenario requires `--conversation-checkpoint` in both commands: action logs do not carry initial-state metadata.

The original script applies an **explicit controlled precondition** at the initial Citadel menu. Only eight NPC pairs and D33A are written in the child emulator, with separate before/after audit and snapshot. No executable/resource/save file is patched. Default reference scripts remain read-only apart from normal gameplay. This verifies the handler under that precondition, not NPC travel or a naturally reached campaign state. The empty-room trace is unmodified. See [M2_TALK_EVIDENCE.md](M2_TALK_EVIDENCE.md).

The verifier reconstructs text directly from original EXE/MAP1 bytes, independently of the cache, and checks live RAM text/name sources and the full BLD payload. Byte 13 persists; Done preserves result 91; the reply clears it to 0. NPC equality is required in the building and excluded on exit, when original travel resumes. `--smoke-talk` exercises the full 19-action path plus five idle ticks. Native mixed-case text was inspected; glyphs/layout and imagery remain approximate. This local reply makes no RNG draw; outer-world dialogue and recruitment are unsupported.

## Katrina original comparison

[Katrina evidence](M2_KATRINA_EVIDENCE.md) records primary bytecode/machine-code findings and the bounded first-visit/repeat/exit/re-entry trace:

```sh
python3 tools/reference_session.py --script tools/reference-katrina.json
python3 tools/verify_m2b.py --reference-run work/reference-runs/1791683236787259649
```

Substitute the printed run directory for a fresh comparison. The successful original run has 20 checkpoints; the verifier matches cursor and party[0], bytes 0–21, recorded credits and full decrypted RAM payloads against the committed factual fixture and native replay. Four text hashes check original case and exact concatenation. Screens were inspected to establish dialogue order, modes and selection; the verifier does not infer them from an assumed DOS mode byte.

**Explicit exclusion:** the original sets byte 22 to 255, freezes it in the building, then counts down outdoors. The recorded exit/re-entry values depend on elapsed original-loop timing. Native state retains 255; no equality is claimed for that field after exit. Byte 6 does persist across exit/re-entry and is compared. Broader timer/day/economy parity is unfinished.

Without DOSBox:

```sh
python3 tools/verify_m2b.py
./build/btech-headless --replay tests/fixtures/citadel-katrina.actions --trace --frame work/katrina.ppm
```

`--smoke-katrina` exercises the 19-action loop through queued SDL events, then five idle ticks, ending on the re-entered menu with Leave selected. Native records are replayed against the same canonical state. Case-sensitive text rendering was also inspected in the generated native frame; original glyph shapes, wrapping and scene imagery remain approximate. These historical Katrina checks do not establish later mission-progress branches or original saves. M2h separately verifies paid personal Class and the outdoor countdown model.

## Citadel original comparison

[Citadel evidence](M2_CITADEL_EVIDENCE.md) records exact trigger/decrypt/opcode findings and confidence. Run the original and compare the printed run directory:

```sh
python3 tools/reference_session.py --script tools/reference-citadel.json
python3 tools/verify_m2.py --reference-run work/reference-runs/1791682077232453392
```

The input script waits through arrival/text rendering, selects Hall of Legends, advances six screens, selects Leave from the retained Hall highlight, and takes one south step. The verifier compares fresh original cursor **and party[0]**, 16 state bytes, unchanged credits and all 4328 decrypted bytes with the fixture/core. Seven native text digests are checked against the original resource. Snapshot mode labels come from captured screen observations; the verifier does not read an assumed DOS mode enum or claim that VM PC was captured from the live interpreter.

Without DOSBox:

```sh
python3 tools/verify_m2.py
./build/btech-headless --replay tests/fixtures/citadel-hall.actions --trace --frame work/citadel-hall.ppm
```

`--smoke-citadel` feeds a bounded set of logical controls through the native SDL event queue. Its records and screenshots remain in ignored `work/`. Error-branch checks require a failing process exit with `unsupported opcode`; they also verify explicit recovery. This does not establish the other Citadel choices, complete story flags, economy, pixel equality or original timing.

## Original-game reference sequence

Spice86 cannot run with this checkout alone: no dotnet executable, no matching external Spice86 tree, and no prebuilt reference executable. DOSBox 0.74-3 is the practical oracle. It executes an unpatched copy of `BTECH.EXE`, not UnBattletech's runtime.

One-time working copy, if absent:

```sh
mkdir -p work/dos
cp -a "Original DOS/." work/dos/
```

Reference command:

```sh
python3 tools/reference_session.py --script tools/reference-movement.json
```

The script selects `3` for VGA, `3` for hard disk, waits through startup, uses the recorded title/menu keys, then walks the road, the south wall, the hedge and the west wall. Intro/menu inputs remain part of the recorded sequence. Coordinates already exist during the initial question screen; the native slice begins directly at those initialized MAP1 coordinates and omits the original startup menus. This is a scenario fixture, not a claim to reproduce every new-game variable.

Every invocation creates `work/reference-runs/<unique-id>/`: `inputs.jsonl`, DOSBox/Xvfb logs/config, raw 320×200 PNGs, read-only guest-RAM exports, and JSON snapshots. `work/reference-latest.txt` gives the newest directory. The harness owns a private Xvfb display, focuses only its own DOSBox window, does not receive interactive stdin, and terminates both child processes. Files read/mounted by DOSBox are only under `work/dos/`; originals are never mounted writable. Failures stop the script rather than silently accepting absent captures.

To compare a fresh run with the native core and compute the frame report, substitute its printed directory:

```sh
python3 tools/verify_m1.py --reference-run work/reference-runs/1791680299506554032
```

`tools/verify_m1.py` uses Python's standard library for state comparison; Pillow is required only for the optional PNG/pixel report. All 88 original hashes are checked first. Regression fixtures contain only factual coordinates/actions and provenance; proprietary PNGs/RAM/resource bytes are kept out of the fixtures. Before launch, the reference harness also checks working-copy resources against the manifest, excluding mutable GAME saves.

**VERIFIED observations:** initial raw X/Y `0C45:C019` → half coordinates `(69,25)`, nominal cursor tile `(34,12)`; party[0] coordinates agree. Gate `85`; runtime UI selector `2`, narrow-panel value `1`, world-active byte `0`, scene bytes recorded as zero. `w014A` is `1` while movement works; interpreting the harness's historical `suspend` field as a global pause flag is unproven. Credits are `20` at the initial question snapshot and `35` in the later walk snapshot; allowance/timing parity is excluded from M1.

The game image is located using its known unpacked string offset `37A88`, then validated against BIOS data and entry bytes; the load segment in these runs is `01A2`. Common DS is load + `36DB`; the map-buffer DS is load + `1C6C`. Runtime selector pointers resolve state, UI and cursor storage. Reko's load base `0800` and old Spice86 aliases are not used as raw file offsets or native-core addresses. Original MAP1 payload bytes are present at guest offset `1F0FD`. The 24×24 working grid at map DS + `07AD` matches all 576 corresponding MAP1 tile IDs at map region origin `(24,0)` in the recorded start. It is not a tile-property LUT or proof of a static global world.

Cursor tile projection floors both half coordinates. Player collision in the recorded trace instead samples `ceil(x_half/2), floor(y_half/2)`: west moves `68→67` succeed although the nominal cursor enters tile 33, then `67→66` blocks on its wall. Tile ID threshold 85 and this offset rule reproduce the tested route. Generalization to additional scenes, multi-unit footprints and world edges remains **INFERRED/UNKNOWN**; native map edges currently block deliberately.

## Graphics comparison and exact deviations

All 64,000 independently decoded C BTTLTECH pixels match the secondary reference tilesheet under the standard EGA palette. MAP1 uses 16×16 tiles, block-normalized map data, and an observed terrain remap 5→9, 9→1. At the tested start, the original right panel begins at X=104; its map crop origin is `(464,104)` after the first east step, matching camera `x_half*8−96, y_half*8−96`. Native resolution is 320×200, scaled without filtering.

**VERIFIED for that frame:** 42,625 / 43,200 right-panel pixels equal, **98.669%**. The remaining 575 pixels include omitted NPC/sprite overlays and the approximate player marker; their complete causes are not assigned without further tests. The independently drawn left diagnostic panel replaces original status/animation/menu graphics. Whole-screen equality is not claimed. Palette/camera parity for other graphics modes remains **UNKNOWN**.

Remaining differences: no full NPC startup/world travel/followers, later campaign/day progression, owned-mech services/party assignment, wider encounters/combat, original GAME compatibility or audio. M3a implements bounded manual weapons training; M3b adds Kick, moving/retaliating opponents in the fourth/fifth assignments and early Mechit-Lube services. General computer control, persistent terrain fire, exact weapon effects and the waypoint queue remain deferred. M2k–M2m adds rubble/rest progression and launch/dream playback. M2j verifies the first mission/cap reward/sleep loop and all shop goods; wider progression remains deferred. M2f adds three local investment balances/returns and both shops' Talk to the earlier purchases/conversation. Unsupported actions still stop visibly. Original font and borders are verified; remaining layout, pauses and status imagery remain approximate. The 98.669% figure above is the historical M1 comparison frame, not current pixel parity. No complete campaign or global map is claimed.

## Dependency provenance

Packages were downloaded through the configured Ubuntu archive with `apt-get download` and extracted with `dpkg-deb -x`; no privileged system package installation or arbitrary remote script was used. Original-game graphics are loaded directly, not copied from the GPL project. Existing GPL tooling was exercised only on copies to audit decoding/round trips.

| Local package | Destination | SHA-256 |
|---|---|---|
| dosbox 0.74-3-5build2 amd64 | `local-deps/dosbox/` | `f7fabe8e4923ec503349f8c7466ab132395e83ba03aa1e382955c09f434c4433` |
| libsdl-net1.2 1.2.8-6build1 amd64 | `local-deps/dosbox/` | `3a060ffbfb07f8046ee78c7211fe67932717bc6a4f52daca9860cd60c3396dd2` |
| libsdl-sound1.2 1.0.3-9build4 amd64 | `local-deps/dosbox/` | `c02bfb7fe9e20189b4c5556f73acab4c1b53594db6ff10dde58d11be0be97d10` |
| libmikmod3 3.3.13-1 amd64 | `local-deps/dosbox/` | `f2b562ffcd8bf90947487ce3ded3363f2afeef0cce07e6732d1b691bb8d297ab` |
| libsdl2-dev 2.32.4+dfsg-1 amd64 | `local-deps/sdl2/` | `90a21699bdb8f6f491b92dba345a85b1ab865c54cd59c527b91603a2d1a13b17` |
| xvfb 2:21.1.18-1ubuntu1.1 amd64 | `local-deps/xvfb/` | `a980a874e0b5663ada7ff1f145ce91b87ba03a40bd5d4fde335bf6d0f1a4ed06` |

The harness supplies a process-local library path for DOSBox's extracted libraries and dummy audio. X11/XTest libraries and fonts were already present. There is no audio device dependency in the slice. These packages are local ignored dependencies, not new implementation source. No new dependencies were needed for M2a–M2m.


## M2i sprite verification

```sh
python3 tools/verify_sprites.py
python3 tools/native_smoke.py --sprites-only
./build/btech-port --sprite-preview
```

PASS: 376 original RAM crops / 45472 indexed pixels, 30 walking checkpoints,
four exact 8×8 player screenshot crops, 63 uninterrupted NPC animation frames
and fresh-process continuation. Native SDL movement emits exactly the replayed
headless pixels/state; the original-mech preview animates, presents the same
static grid and exits normally. F5/F9 also passes with the new walking state.
The complete regression and ASan/UBSan/LeakSanitizer suites include these checks.
A sandboxed sanitizer attempt failed because LeakSanitizer cannot run under
ptrace; the approved whole script runs outside that wrapper, with leak checking
still enabled. No dependencies or reference-directory changes were required.

M2i sources, export commands, exact evidence runs and remaining limits are in
[M2_SPRITE_EVIDENCE.md](M2_SPRITE_EVIDENCE.md). The historical M2i payload is 416
bytes, BTP9; M2j extended it to 448 bytes, BTPA/v10; BTPC/v12 uses 512 bytes;
historical BTPE/v14 uses 1024 bytes; BTPF/v15 uses 2048 bytes; BTPG/v16
used 4096 bytes. Current BTPI/v18 uses 16384 bytes, as described above.
Existing progress and old migrations remain covered.
Mech ownership, party combat and portraits were added in M3d–M3h. Remaining
status UI, whole-screen and complete timing parity are not claimed. The three
loan choices, earlier assignments, original combat/map frames and O0/O8
playback remain covered.
