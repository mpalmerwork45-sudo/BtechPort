# Saved-journey scenarios

Scenarios can start from a real saved checkpoint, so a later mission or planet
can be checked without replaying the opening campaign. The selected save is
pinned by SHA-256 and loaded by the native player against the **exact game
content**. It keeps the saved party, orders, objectives, discovery and RNG.
The current milestone changes authoring tools, not gameplay or save formats.

## In the Construction Kit

Open **Play options → Checkpoints and trace**.

1. Enter a new run name and **Choose scenario…** to select a scenario JSON file.
2. **Run scenario file** uses the file's declared start: a new game by default,
   or its pinned checkpoint if specified.
3. Select a named checkpoint in the left list, choose a continuation scenario,
   and click **From selected checkpoint**. This explicitly uses the selected
   save and saved RNG in place of the file's checkpoint/new-game seed. It does
   not modify the scenario file.
4. Inspect state and events, or **Show last report** for setup, assertions,
   coverage and artifact paths. **Cancel scenario** stops the background player.

Scenario verification uses the current project, including valid pending forms.
If its playable content differs from the save, the run fails visibly in Problems.
If you edit while a run is active, its result is labelled as an earlier snapshot.
A successful check does not save or discard your edits.

**Play selected** launches the selected save with its historical project snapshot.
**Continue actions** also uses that historical snapshot and the ordinary actions
in the text box. **Run actions from start** creates a fresh manual checkpoint.
Both manual checkpoints and named/final scenario saves appear in the same list.
These runs never occupy the normal game's save slots.

## Scenario files and CLI

Give checkpoint steps unique names when you need to retain several points:

```json
{"op": "checkpoint", "name": "before-escort"}
```

This produces `checkpoint-before-escort.btp`. Names are 1–48 ASCII letters,
digits, underscores or dashes, beginning with a letter or digit. Duplicate names
and existing named output files are refused. An unnamed `checkpoint` retains
its previous save/reload behavior and reuses a content-keyed filename.

To resume, add a top-level checkpoint descriptor to the continuation scenario:

```json
{
  "format": "btp-author-scenario-v1",
  "checkpoint": {
    "file": "../first-run/checkpoint-before-escort.btp",
    "sha256": "REPLACE_WITH_THE_64_LOWERCASE_HEX_CHARACTERS_FROM_SHA256SUM"
  },
  "steps": [
    {"op": "choose", "label": "Begin escort"},
    {"op": "battle", "control": "computer"},
    {"op": "assert", "objective": "cairn:escort", "status": "complete"}
  ]
}
```

Use `sha256sum first-run/checkpoint-before-escort.btp`, or copy the `sha256`
record from that checkpoint's step in `report.json`. Replace the placeholder
above before running. The `file` path is relative to the **scenario file**;
absolute paths work too. A checkpoint scenario cannot also declare `seed`.
It skips new-game initialization entirely, including start events.

Run it with the existing `author.py scenario PROJECT --file SCENARIO --output
NEW_DIRECTORY` command and the project's required asset options. A suite case
can reference the same file: it runs once from that saved RNG and rejects
`seeds` sweeps. Existing new-game scenario and suite behavior remains available.
Python callers pass `base_dir=scenario_path.parent` to `run`; without it,
relative input paths resolve against the current working directory.

The run stages `game/`, a local `initial.btp` copy and a rewritten `scenario.json`.
The report records the original input path, input hash, initial state/RNG/tick,
content revision and runner hash. When a matching earlier scenario report is
available beside the save, it is retained as `initial-report.json` with its hash.
The native loader independently checks the pin, checksum, project identity,
content digest and supported saved state. Missing, corrupt, oversized or
changed-content input fails before any opening game events execute.

Reproduce using the staged `game/` and `scenario.json` in a **new output
directory**. The copied `initial.btp` makes this independent of the source save's
later deletion. For ordinary-input reproduction, load that file with
`btech-headless --project ... --load ... --replay .../replay.actions`.
The input replay alone is insufficient: it needs the saved starting state.

## What the report proves

Coverage covers the continuation only. Earlier events/branches do not become
covered merely because their effects are present in the input save. A past
battle outcome that was only recorded in the earlier runner's report is not a
new observation; assert persistent objectives/flags or run a new battle instead.

A midbattle continuation keeps existing orders. `battle: computer` requires
all friendly units already under active computer control, or the ordinary
initial control prompt. Mixed/manual-paused orders require explicit menu inputs.
A conflicting policy fails without changing the save. A hold/retreat helper
requires saved manual control. Hook text/choices retain the normal scenario rules.

Midbattle resource reductions and casualties have `metric_basis: since_checkpoint`
and `start_round`; subsequent whole battles use `whole_battle`. `rounds` is the
final battle round, while suite `mean_rounds_observed` excludes earlier rounds.
These are declared-route observations, not general balance or Lua path coverage.

Changed game content requires a fresh checkpoint. No save migration, reward
granting, teleportation or state patching is performed by this workflow. Existing
explicit save-migration tools remain a separate operation. Source comments and
module formatting can preserve compiled content; converting an old package to
canonical sources may change its save identity.

## Reproducible demonstration

```sh
python3 tools/checkpoint_demo.py --output work/saved-journey-demo
python3 tools/checkpoint_demo.py --output work/saved-journey-cairn --cairn
```

The first command creates an independent World Survey game using included art.
The second also uses locally supplied original assets/caches for Cairn Passage.
Add `--windows` to compare the continued runs with the Windows executable under
the isolated test Wine prefix. Build both platforms first.

| Recorded journey | Full input ticks | Continuation ticks | Skipped ticks |
| --- | ---: | ---: | ---: |
| Two planets, six party members, return shuttle | 346 | 224 | 122 |
| Cairn contract, starting before the escort | 4,458 | 1,949 | 2,509 |
| Cairn defence, starting during round 2 | 2,508 | 1,933 | 575 |

Each comparison requires exact final save bytes and an identical ordinary-input
suffix. Tick savings describe simulation work; process startup and loading still
take time. See [verification results](TESTING.md#saved-journey-scenarios--2026-10-23)
for platform and regression evidence.
