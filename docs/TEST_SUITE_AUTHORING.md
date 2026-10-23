# Test suites and coverage

Open **Play → Test suites and coverage** in the Construction Kit. Definitions
are saved in the project's `EDITOR.json`, with the same Save, Undo, Redo and
unfinished-form recovery as map edits. This works with packages and modular
source projects. It does not change runtime capacity or the game's save format.

1. Choose **New suite**, then **Add case**. Give each case a stable ID. Optional
   comma-separated seeds run the same inputs with different initial randomness.
2. Pick a starter: start of game, entrance, map destination, world destination,
   or objective. Coordinates are **movement cells**, two per terrain tile.
   World-town destinations are checked at their composed world coordinates.
3. On **Steps**, add, edit, reorder or remove ordinary inputs and assertions.
   The standard forms cover walking, choices, pages, entering, battle control,
   checkpoints and common assertions. Advanced JSON exposes the complete
   existing step schema. An objective starter only asserts its completion:
   insert the route and choices that actually achieve it before that assertion.
4. **Run selected** runs the highlighted cases (Ctrl/Shift selects several).
   **Run full suite** runs every case. **Cancel** stops further work and retains
   artifacts already produced. Run limits remain 16 cases, 32 seed runs,
   8 seeds per case, 256 steps and 120,000 ticks per scenario, 45 seconds per
   scenario and at most 300 seconds for the suite.
5. Save to keep definitions. Run reports live separately under the editor's
   settings directory, in `test-runs/`. Output logs their exact paths.

Cases can use project-owned steps or an external scenario file. Clearing an
external file reference in **Edit case** imports its steps for editing. Setup
is explicit: ordinary new game, retained imported fixture, or a fixture command
file. Fixture batches use `expected_revision: "new"` and run only against a
private validated game copy. Selecting New game removes the fixture. Starting
checkpoints are SHA-256 pinned; they keep their saved RNG and cannot use seed
sweeps. The native loader checks exact saved game compatibility.

**Import** copies a standard CLI suite's scenario and fixture definitions into
the project; referenced saves and fixture imports remain explicit external
resources until export/run. **Export** creates a new portable directory holding
the standard suite at `inputs/suite.json`, copied scenarios, checkpoints,
fixture assets and a hash manifest. It refuses to overwrite an existing folder
or write into the game project. Normal CLI `suite` and review-selected checks
can consume this exported suite. Changing external source files later does not
change retained evidence.

## Read coverage honestly

**Inspect dependencies** produces a retained inventory without running tests.
On **Coverage and failures**:

- **Declared** means a conservative static dependency, following explicit
  branches and reachable-map triggers. It does not mean that gameplay visited it.
- **Observed** means the native player recorded that event or an unambiguous
  branch transition in this run, including any observations before a failure.
- **Unvisited** means no observation in this run. Ambiguous edges to the same
  destination cannot be distinguished and remain unverified.
- **Not run** means the case was omitted or never reached. Previous full-suite
  passes never fill in omitted cases in a newer partial report.
- **Unknown** covers opaque input, Lua, checkpoint state, external original
  resources and fixtures that change more than the start. Passing declared
  routes does not prove those other paths.

Double-click a failure to open its map/world position or referenced object.
Double-click an event or branch row to open that event. Earlier draft and loaded
historical reports are labelled; coverage always belongs to its retained
revision and copied inputs. External source freshness is not claimed.

## External authors and automation

Generate an entrance starter, then edit and run it before claiming verification:

```sh
python3 tools/author.py scenario-scaffold /path/to/game \
  --kind entrance --target game:door --output /tmp/door.json
python3 tools/author.py scenario /path/to/game \
  --file /tmp/door.json --output /tmp/door-run
python3 tools/author.py coverage /path/to/game \
  --suite /path/to/export/inputs/suite.json \
  --report /path/to/run/suite-report.json --output /tmp/coverage.json
```

Omit `--report` for an entirely unrun dependency inventory. Mismatched project
revisions show historical evidence without assigning current coverage. Use
only a report from that exact suite/input snapshot: the general CLI accepts
user-supplied reports; the editor's runs capture and verify their own inputs.
`scenario-scaffold` also accepts `--kind start|map|world|objective`, optional
`--at X Y` and `--checkpoint SAVE`. Generated files are never marked verified.

Reproduce the retained independent demonstration with
`python3 tools/suite_authoring_demo.py --output work/my-suite-demo --windows`.
It imports three cases, saves/reopens a source project, inspects dependencies,
runs all five seed samples, runs two selected samples, and compares a selected
case's exact Linux and Windows/Wine final state and save bytes. The GUI check is
`python3 tools/native_smoke.py --editor-suites-only`.
