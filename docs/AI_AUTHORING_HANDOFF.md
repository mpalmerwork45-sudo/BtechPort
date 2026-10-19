# Archived AI authoring discovery/testing checkpoint, 2026-10-18

**Completed 2026-10-19.** The four approved steps were resumed, verified and
committed in `f519114` and `d88ecd3`. The full Python/native/GUI checks and Windows
routes under Wine pass; the separate authoring lab demonstrates diagnosis and
repair. Use current [project status](PROJECT_STATUS.md), [testing](TESTING.md#ai-authoring-discovery-and-mission-testing--2026-10-19)
and the [author guide](AI_AUTHORING_GUIDE.md). The original checkpoint below is
kept for history; its pending tasks are superseded, not a new work queue.

The user approved the next pass (steps 1–4), then requested stopping for the
night. Resume this work without restarting the earlier completed AI1/AI2 pass.
This checkpoint is **work in progress**, not a completed milestone release.

## Scope

1. Shared searchable content catalogue (AI3).
2. Labelled contact sheets, animation strips, map/world overlays and event graphs (AI3).
3. Static event lint and native whole-party navigation/deployment checks (AI4).
4. Broader scenario routes, saves during progression/combat and bounded seed samples (AI4).

Changes review/protected regions/live sessions (AI5) are the following milestone.
Do not start AI5 or richer mission mechanics as part of this pass.

## Implemented and checked so far

- `tools/asset_catalogue.py`: project/library/atlas search, numeric comparisons,
  unit class/movement/weapons, explicitly derived roles, dependency closure,
  editable asset names/descriptions/tags/edge notes in `EDITOR.json`.
- `asset.annotate` is a normal revision-checked batch operation. Cloning tiles
  and importing/exporting library units retain relevant annotations.
- `tools/authoring_visuals.py`: standalone SVGs with embedded PNG pixels,
  stable IDs, frame timing, dependency labels and content hashes. Uses existing
  decoders and sprite/construction layouts, with no new dependencies or Tk imports.
- CLI additions: `catalogue`, `contact-sheet`, `animation`, `graph`,
  `world-preview`; labelled/region `render` outputs use `.svg`.
- Project → **Content catalogue**, with animated preview and annotation forms.
  Unit Library, roster, reference picker, tile chooser and Pattern Library use
  shared search. Catalogue tabs remember their query/source in workspace state.
- `tools/authoring_analysis.py` / `build/btp-author-analyze`: explicit event
  graph reachability, synchronous cycles, objective flags; real C collision and
  door-contact probes from start/transfer arrivals using the initial whole party;
  encounter footprints and deployment separation. Original assets remain local.
- Project → **Check mission** runs checks on a detached snapshot, rejects stale
  results, and puts findings in Problems with event/map navigation. This newest
  GUI action still needs its own end-to-end smoke coverage.

Verification already performed:

- **29/29 focused Python tests PASS**: authoring 14, catalogue 8, mission checks 7.
- **18/18 Unit Library tests PASS**.
- Private-display `python3 tools/native_smoke.py --editor-authoring-only` PASS:
  real paint, command application/Undo/stale checks, shared catalogue search,
  original sprite preview, annotation form, tagged tile picker, and ordinary Play.
  That run preceded the newest Check mission action/tab-restoration changes.
- Native `btp-author-playtest`, `btp-author-analyze`, `btp-project` build with
  the system toolchain and two jobs. Relay Contract lint reports no findings,
  checking two maps and 4,248 reachable compact-formation positions.
- Native/GUI full regressions and Windows verification for this pass remain pending.
- Local SVG evidence: `work/authoring-discovery-constructions.svg` and
  `work/authoring-discovery-animated.svg`. SVGs need visual inspection before
  calling presentation finished; manifests/pixels have automated tests.

## New scenario code staged, verification incomplete

The following is written/compiled but **not yet established by new route tests**:

- Optional 24-bit scenario `seed` enters before the first event through
  `btp_initial_state_seeded` / `btp_events_start_seeded`. Normal games retain
  the existing initial random state. Default-state regression must be checked.
- Battle policies `computer`, `hold` (end turns without attacking), and
  `retreat` (real menu command), plus `until_round` for a mid-battle checkpoint.
- Extra assertions/state projections for battle outcome, party/owned units,
  character health, armour/structure/ammunition bounds and round bounds.
- `combat.jsonl` records per-fight policy/outcome/rounds/losses/reductions.
  Ammunition reduction includes destroyed ammunition, not just firing costs.
- `suite` command / `btp-author-suite-v1`: at most 32 new-game runs, at most
  8 seeds per case, per-run and total wall-clock bounds, cancellation files,
  per-case aggregate reports. It separates different policies/cases.
- Scenario reports now include visited events, uniquely identifiable observed
  branches, failure step/replay, seed and combat results. Ambiguous same-target
  branch labels are not claimed as covered.
- `tools/make_authoring_reference.py` regenerates batch, scenario and suite
  schemas plus the operation reference. Run it again after descriptor changes.

## Next actions, in order

1. Exercise the seeded runner immediately on separate temporary copies:
   normal victory; `until_round: 1` → checkpoint → resume; real retreat;
   natural defeat under hold. Fix any stalled combat prompts, metric errors or
   resume-policy issues. Never force victory/loss or patch flags to pass tests.
2. Add recorded scenario files alongside `examples/authoring/` for decline,
   encounter cancellation, retreat, defeat, repeat reward, unaffordable service
   and save/reload. Use controlled validated fixtures if necessary, explicitly
   distinguished from the complete normal route. Seeded win samples should use
   one declared policy and modest sample counts.
3. Add meaningful tests for new seed/policy/assertion/suite behavior, failed
   assertions, cancellation/time budgets, reports and revision mismatch.
   Confirm a seed is applied before a start-event battle consumes RNG.
4. Finish catalogue/visual coverage: world-city overlay, directional/action
   frame timing, owned tile images, atlas annotation, changed-artifact hashes,
   library selection/dependencies. Ensure non-asset reference searches still work.
   Visually inspect contact sheets and map/graph previews. A short animated
   preview may be useful; current output is a labelled frame strip.
5. Extend GUI smoke coverage for Check mission, opening a finding, metadata
   Undo/save/reopen and catalogue tab restore. Capture a catalogue screenshot.
6. Provide one reproducible demonstration workflow in a **new project/copy**:
   search/select assets, annotate industrial construction/road/animated fence,
   render, lint, deliberately break/fix a route via constrained commands, then
   run only affected scenarios. Existing Relay Contract can be the template.
   Do not regenerate Last Beacon or its assets.
7. Finish documentation/capabilities, package the new executable as appropriate,
   then run relevant native/Python regressions and cross-build/Wine checks.
   Commit completed increments locally; never push.

## Preservation and commands

User edits in these files are **not part of the authoring checkpoint commit**:

- `examples/battletech-demo/EDITOR.json`
- `examples/battletech-demo/adventure.json`
- `examples/battletech-demo/graphics.json`

Their session-start hashes are recorded in
`work/authoring-discovery-baseline.json`. The two reference directories are
read-only. The reference guard still verifies **1,287 unchanged entries**:

```sh
python3 tools/reference_guard.py verify --manifest work/reference-before-map-construction.json
env PATH=/usr/bin:/bin cmake -S . -B build
env PATH=/usr/bin:/bin cmake --build build -j2
python3 -m unittest discover -s tests -p 'test_*.py'
env PATH=/usr/bin:/bin ctest --test-dir build --output-on-failure
python3 tools/native_smoke.py --editor-authoring-only
python3 tools/author.py catalogue examples/relay-contract --query 'kind:mech weapon:lrm'
python3 tools/author.py lint examples/relay-contract --data 'Original DOS' --dialogue-data work/talk-data.bin --combat-data work/combat-data.bin --world-data work/world-data.bin
```

Use at most two compiler jobs. The inherited Conda linker cannot read host
`.relr.dyn` sections; the system PATH above is the known working native build.
There are no delegated agents or model/network services required by these tools.
