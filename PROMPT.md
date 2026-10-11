# BtechPort — BattleTech: The Crescent Hawk's Inception
## Independent, portable recreation — Codex project brief

### Your role

You are the lead reverse-engineering and implementation agent for **BtechPort**, an independent recreation of **BattleTech: The Crescent Hawk's Inception** (1988, MS-DOS). Work from the actual original game files and existing reverse-engineering evidence, not guesses about how the game *ought* to work.

**Start in the current working directory (`BtechPort/`). Inspect the filesystem before assuming any paths, file names, executables, versions, or installed tools.** You are running on **Kubuntu/Linux**. The user has already placed these two directories in the project root:

```text
BtechPort/
├── PROMPT.md                    # This brief
├── Original DOS/                # Original MS-DOS game files — READ ONLY
└── UnBattletech/                # Existing third-party research/recreation — REFERENCE ONLY
```

The directory names contain spaces and mixed case; handle them correctly. The exact contents are unknown until you inspect them.

**The immediate goal is an evidence-based feasibility audit followed, if viable, by the smallest honest playable vertical slice of an independent implementation.** The longer-term goal is a faithful, end-to-end playable game, with a separate, optional enhanced mode later. Do not attempt the entire campaign in one uncontrolled pass.

---

## 1. Non-negotiable principles

1. **Protect source material.** Treat `Original DOS/` as immutable. Hash and inventory the originals; never modify, patch, overwrite or delete them. Use separate working copies for experiments. Do not change tracked files in `UnBattletech/` or push to its upstream repository. When using its tooling, prefer out-of-tree builds/copies so reference material remains unchanged.
2. **Independent codebase.** Do not make Godot, the existing C# project or UnBattletech's runtime a dependency of the new game. Use them as historical evidence and comparative references, not as architecture to be mechanically translated.
3. **Binary/emulator is the behavioural authority.** Reverse-engineering notes are valuable but can be provisional. The original executable, data and repeatable emulator observations take precedence when they disagree with a secondary reconstruction.
4. **Never equate implemented with verified.** Mark findings and features as `VERIFIED`, `INFERRED`, `APPROXIMATE` or `UNKNOWN`; include the evidence behind every substantial claim. Preserve uncertainty explicitly.
5. **Faithful first, enhancements later.** Do not redesign combat, replace story events, simplify shops, add mechs or fix frustrating encounters in the baseline. Original-mode fidelity should remain independently testable. The Star League cache sequence and expanded mech roster are desirable future *enhanced-mode* options, not initial tasks.
6. **Prefer a small, portable, headless-testable engine.** Game rules and state must not depend on a renderer, operating system or frame rate. A light 2D frontend is preferred over a full scene-graph engine.
7. **Keep work bounded and measurable.** Reuse proven existing extraction/research tools instead of redoing archaeology unnecessarily. Make incremental working commits if this is a local git repository and commits are appropriate; **never push** without user instruction. Never alter git configuration unexpectedly.
8. **Respect provenance and licences.** `UnBattletech` is a GPL-3.0 project; its original source, tooling, docs, and any reused code have relevant licensing implications. This project is **not automatically a legal clean-room implementation** merely because it has a new language or design. Start with factual format specifications, documented observations and independent new code. **Do not copy or translate substantial GPL source into the new implementation without first recording that choice and its distribution implications and seeking user approval.** Keep proprietary game binaries and assets out of public commits. If distribution becomes a goal, flag copyright and licensing questions for review rather than making legal guarantees.
9. **No fabricated completeness.** A map drawn from original assets is not a reconstructed campaign; an approximate combat algorithm is not verified combat; an interpreter with silently skipped opcodes is not complete.
10. **Make sensible progress autonomously.** Do not ask permission for every small step. Stop and report only for genuine blockers, major licensing decisions, destructive operations, or the specified milestone review.

---

## 2. Existing evidence — investigate before reinventing

Start with the local `UnBattletech/` checkout and read its actual README, contributor/agent instructions, documentation index, status/roadmap and licensing files. The public repository is https://github.com/velteyn/UnBattletech, but **the local checkout takes priority**; filenames and progress may have changed.

Relevant areas to locate and inspect, where present:

- `docs/` — documented formats, memory map, combat, world map, story, viewport, known gaps, and validation plans.
- `reko/` and `asm/` — decompiled DOS code, assembly, addresses and annotations.
- `tools/bld/`, `tools/assets/`, `tools/analysis/`, `tools/playtest/` — decoders, asset extraction, emulator driving and analysis utilities.
- Spice86-based emulator/debugger and game-specific introspection tools (discover actual build/run instructions and ports; do not blindly reuse the author's machine-specific paths).
- `BattleTechCHI/` — Godot/C# recreation, useful as a **secondary comparison**, not the specification or implementation to port.

Pay special attention to the README's distinction between reverse-engineered evidence and unverified recreation behaviour. Its documented gaps may include (verify against local files):

- Accurate combat: random-number generation, initiative, hit chance, hit location, damage, heat, ammunition and artificial intelligence.
- Missing or incomplete 8086 code segments, potentially including `19EF` and `1000`.
- Map-to-story-script/BLD trigger mapping and tile collision properties.
- Story-state variables and script dispatcher behaviour.
- Viewport structure, screen transitions and graphical fidelity.
- Save-file round-trip correctness.
- Cadet economy/day progression.
- Sound/music format.

**Do not take the above list as an assertion about the present checkout.** Produce a fresh, concise evidence inventory with links to *local files, routines or data* and a confidence rating.

Supplementary public research, only if it answers a specific missing question:

- https://github.com/Elthial/Reko-Btech
- https://github.com/Elthial/CrescentHawksTools
- https://github.com/waynepiekarski/battletech-maps

The game appears to mix stored maps with procedural world generation. Verify which part of the world is data-driven, procedural, or both. Do not invent a giant static world-map file if the original generates terrain algorithmically.

---

## 3. First investigation: original DOS files and tooling

### 3.1 Inventory `Original DOS/`

- List all files and subdirectories, including readme/manual/config/save files if present.
- Record SHA-256 hashes, sizes and apparent formats.
- Identify the correct DOS executable(s), version and loading requirements; do not assume `BTECH.EXE` versus `UNBTECH.EXE` without inspection.
- Determine which original `.BLD`, `.MTP`, `.ICN`, `.CMP`, `.ANM` and save files actually exist. These extensions are examples from earlier research, not a guarantee of the local contents.
- Check for compression, duplicate versions, patched executables and missing files.
- Document case-sensitivity issues and how original DOS paths are passed to Linux tools.

Write findings to `docs/ORIGINAL_FILES.md` and a compact machine-readable manifest if useful. Exclude proprietary assets themselves from Git.

### 3.2 Verify the reference runtime

Use the most practical installed tools (potentially DOSBox-X, DOSBox, Spice86 or the existing UnBattletech emulator). Prefer the existing game-specific Spice86 introspection if it can be made to work on Kubuntu without changing the reference checkout.

Demonstrate, where feasible:

- The original reaches a reproducible start state.
- At least one screenshot/frame can be captured.
- The initial player/party position, map identifier, game mode and a few relevant state values can be recorded.
- A short reproducible keyboard-input sequence can be driven or documented.

Record exact commands, dependencies, paths and observed output. If a runtime cannot be brought up without disproportionate effort, document the blocker and proceed with independently verifiable data extraction instead. **Do not stall the whole project on emulator automation.**

### 3.3 Audit reusable tools

Try representative read-only extraction/decoding workflows on copies of original files. Before trusting a decoder, test its outputs against the source bytes, round trips or independent known examples where possible.

Produce `docs/RESEARCH_AUDIT.md` containing a table:

| Subsystem | Source of evidence | Confidence | Reusable tools/data | Important gaps | Proposed verification |
|---|---|---|---|---|---|

Include world generation, local maps, graphics, animations, BLD/story, input/movement, inventory/economy, combat, save/load, timing and audio. Distinguish verified facts from the Godot recreation's approximations.

---

## 4. Choose the implementation language deliberately

Evaluate **portable C (C99 or C11)** against **Rust (stable toolchain)** for this specific project. The user already knows C; Rust is interesting but relatively unfamiliar to them.

Consider:

- How directly each language can express verified 8086-era state machines and bit-level behaviour.
- Correctness and deterministic testing of combat, scripts, inventory and saves.
- Memory safety, refactoring and long-term maintainability.
- Simplicity of Linux builds, Windows portability, and debugger support.
- Accessibility to a human maintainer unfamiliar with Rust.
- Potential future DOS/retro builds (a benefit of C, **not** a current requirement).
- Dependency footprint and integration with rendering, audio and input.
- How much code the agent must maintain rather than merely generate.

Create `docs/LANGUAGE_DECISION.md` with a short weighted comparison, a chosen language and justification. Do not let enthusiasm for Rust or familiarity with C decide the issue without analysis. If there is no meaningful advantage to Rust, C is perfectly acceptable; if Rust offers a compelling maintainability/correctness benefit, choose it and explain the basic project layout and commands for someone new to Rust.

Use a modest rendering library such as SDL2/SDL3 or Macroquad when appropriate. **No Godot, Unity or large entity-component-system framework** without a demonstrated need. Prefer one native window, simple 2D rendering, keyboard controls, and an offscreen/headless mode for tests.

Do not spend an extended period building duplicate C and Rust implementations. A tiny compile/run spike is acceptable; then select one.

---

## 5. Proposed new architecture

Create the independent implementation **outside** both supplied reference directories, for example:

```text
BtechPort/
├── PROMPT.md
├── Original DOS/           # immutable, not committed
├── UnBattletech/           # reference checkout, not modified
├── docs/                   # new project's reports, decisions and status
├── port/                   # independent Rust or C project
│   ├── core/               # logical simulation: platform-independent
│   ├── data/               # original-file parsers and data models
│   └── frontend/           # window, pixels, keyboard and audio
├── tools/                  # our own repeatable converters and trace tools
└── tests/                  # corpus, state/replay/format tests
```

Adapt the exact `port/` layout to idiomatic Cargo or CMake conventions, without inventing a complex workspace prematurely.

Architectural requirements:

- **Game core:** explicit, serialisable game state; fixed-step `tick()`; logical player/party, entities, world and story state; no graphics-library dependency; controlled random seed/source where feasible.
- **Data layer:** reads authentic original DOS resources from a configurable path. Check bounds and file lengths; reject malformed input gracefully. Prefer runtime loading or reproducible local conversion over embedding proprietary assets in source.
- **Story scripting:** an explicit interpreter/state machine for verified BLD behaviour. Unknown opcodes/actions must be visible diagnostics, not silent no-ops. Keep evidence mappings from opcode to source/routine.
- **Rendering layer:** reproduces original graphics, UI, palettes, animation and timing as closely as established evidence allows. Build modern-platform conveniences around the faithful model, not into it.
- **Input:** recordable logical actions, decoupled from SDL/platform key events.
- **Persistence:** versioned internal save format if helpful, with eventual fidelity to original save behaviour; verify any original GAME* import/export carefully before claiming support.
- **Diagnostics:** optional debug overlay/logging for map ID, coordinates, flags, last script opcode, random state, and game mode.
- **Testing:** the same core must run with no display or audio device.

No premature plugin framework, network layer, elaborate editor or multithreaded engine. Favor clarity and verifiability.

---

## 6. Differential validation: the essential feature

Treat the original executable as a **test oracle** wherever technically possible.

Implement the simplest repeatable validation mechanism that actually works. Start with stable snapshots and small behavioural steps; add fuller automation incrementally.

Potential reference observations:

1. New game: initial location, credits, party/mech state, game mode, story flags.
2. Movement across several tiles: coordinates, collision and terrain transitions.
3. Entering and leaving a building: map→BLD trigger, screen transition, story state.
4. One shop transaction: item and credit deltas.
5. One cadet/day-cycle action.
6. One combat encounter: initiative, random draws, to-hit, heat, damage, aftermath.
7. Save and reload: persistent state equality.

Do not require exact pixel or RNG equality before useful work begins, but define *what* has been compared and which differences remain. When state layouts differ, compare a **canonical logical projection** rather than unrelated raw memory addresses. Capture reference snapshots and test cases without including copyrighted executable/data files in the repository.

Provide tools that can run deterministic core tests quickly on Kubuntu. Include at least one regression test for each subsystem implemented. A screenshot-only comparison never proves behavioural equivalence.

---

## 7. Development milestones

### M0 — Research and feasibility checkpoint (first priority)

**Do this immediately:**

- Inventory/hashes of `Original DOS/`.
- Inspect and assess actual `UnBattletech/` checkout and its status.
- Build or exercise at least one relevant extraction tool.
- Establish an original-game reference run or record an honest blocker.
- Produce the evidence matrix and language decision.
- Identify the **smallest verified, genuinely playable vertical slice**.
- Write `docs/PROJECT_STATUS.md` with concrete next steps.

Do not mistake this checkpoint for the end of the project. If M0 is viable and tools allow, continue into M1 autonomously in the same session.

### M1 — Minimal independent playable vertical slice

Get a native executable running on Kubuntu using the **new** engine, not the Godot recreation. The target slice should, insofar as verified source data permits:

- Load necessary original resources from `Original DOS/` at runtime (or from a deterministic locally generated cache, with clear provenance).
- Display a recognizable original screen/location using authentic graphics and correct geometry/palette as far as known.
- Accept keyboard input, move the player and reproduce basic collision.
- Support one real map/room transition **only if its rules are understood**.
- Show useful diagnostics in a debug mode.
- Have a repeatable build/run command and at least a few automated tests.
- Report precisely which details are verified versus approximated.

An honest, correct partial slice is better than a larger fictional implementation. If original location or rendering cannot yet be reproduced faithfully, build a diagnostic viewer plus an isolated verified behaviour test as the interim milestone; don't represent it as playable.

**Stop and give the user a milestone review after M1, or after M0 if a material blocker prevents M1.** Include runnable commands, evidence, differences, risks, and the proposed next milestone. Do not silently spend an entire project budget completing the whole game.

### M2 — Exploration and campaign foundations (future)

Faithful procedural terrain, local maps, collisions and entrances; original story state and BLD processing; dialogue, inventory, shops, cadet economy/day cycle. Build end-to-end test scenarios for a short complete gameplay loop.

### M3 — Tactical combat (future)

Recover and verify the original's initiative, attack/defence modifiers, random-number sequence, targeting, line of sight, hit locations, cluster hits, heat, ammunition, critical damage, artificial intelligence, encounter results and transitions. Use original traces, not approximate rules from the Godot version.

### M4 — Complete original campaign (future)

Original progression, mech configuration, save/load, ending, interface polish and remaining visuals/audio. Validate multiple paths and save/reload points. Do not mark the original game complete solely because all screens exist.

### M5 — Optional improvements (future, explicitly separate)

Introduce **Enhanced Mode**, leaving Original Mode stable:

- Additional mechs and equipment.
- Reduced unnecessary repetition and a redesigned Star League cache sequence.
- Better usability, configurable pacing, accessibility and optional combat/interface improvements.
- External, validated game data/mod support where feasible.

Only tackle this once the relevant original behaviour is sufficiently established to preserve it.

---

## 8. Efficiency and operating constraints

The previous **Dragon Slayer** (CoCo/6809) and **Amaze** (DOS/8086) recreations were successful and relatively efficient. This game is more complex, so avoid unnecessary token/compute consumption:

- Read `UnBattletech`'s top-level documentation/index before dumping enormous source files into context.
- Use targeted searches and bounded file sections; record findings once for future sessions.
- Prefer existing proven decoders over writing duplicate ones.
- Debug one representative scenario at a time.
- Avoid polishing visuals while foundational game rules are unverified.
- Do not repeatedly run full builds or enormous analysis suites when small targeted tests suffice.
- Keep your reports concise and evidence-rich rather than narrating every operation.
- Do not fetch or execute arbitrary remote scripts without checking their source and necessity.
- Do not run privileged package installs or broad file deletion without user approval; use available toolchains first.
- Keep network calls and new dependencies minimal and documented.
- Maintain `docs/PROJECT_STATUS.md`, `docs/OPEN_QUESTIONS.md`, and `docs/TESTING.md`, so later Codex sessions can resume without rediscovering the same facts.

If the user has not created a Git repository for `BtechPort`, recommend a local one and create appropriate `.gitignore` protection only when safe. Do not accidentally add original files or nested reference repositories. Do not push anything remotely.

---

## 9. Completion and reporting requirements

At the end of this initial assignment provide a short, candid report containing:

1. **Original files:** what was found, executable identity and obvious missing dependencies.
2. **Evidence audit:** which systems are well understood, inferred or unknown; important discrepancies in UnBattletech.
3. **Language decision:** C or Rust, renderer, toolchain, and reasons.
4. **Actual working result:** commands to build and launch; playable features and what fails.
5. **Verification:** tests passing, any emulator comparison and exact deviations.
6. **Work created:** directory/file summary; ensure both reference directories remain unchanged.
7. **Next steps:** the smallest logical milestone that will make the game more genuinely playable.

When making fidelity claims, use the precise terms `VERIFIED`, `INFERRED`, `APPROXIMATE` and `UNKNOWN`.

### Begin now

Start with the local inventory and evidence audit. Make practical choices based on what is actually on disk, establish a sound independent architecture, and — if viable — carry it through to the first honest, testable playable slice. The long-term objective is a complete, faithful C or Rust recreation of **The Crescent Hawk's Inception**, without depending on Godot, designed so that optional gameplay enhancements can eventually be added without losing the original.
