# Recorded campaigns and offline authoring

**Greybank Dispatch** is the AI8 demonstration: five local maps, a service
depot, two alternative opening contracts, a timed relay defence and a convoy
escort. Select **Greybank Dispatch (campaign)** in the launcher to play or edit
the shipped example. It requires separately supplied original CHI resources.
Last Beacon is a separate, user-authored project and is never regenerated.

The [recorded brief](../examples/authoring/greybank/BRIEF.md) and
[recipe](../examples/authoring/greybank/recipe.json) define the example.
The generator reuses the tested Relay Contract, Argent Recovery and Cairn
Passage layouts and mechanics. It expands them into normal maps/events,
unit dependencies and a bounded Lua extraction check. No recipe interpreter
or AI provider is involved in gameplay.

## Generate, check and play

From a built source checkout, after configuring the original resources:

```sh
python3 tools/author.py recipe list
python3 tools/author.py recipe build \
  --file examples/authoring/greybank/recipe.json \
  --output "work/My Greybank campaign" --check --play
```

Remove `--play` to generate and check headlessly. Remove both switches to create
validated editable content without requiring original resources. Output must
be a **new directory**. Existing projects, libraries and saves are preserved.
Generation/checking works without a model, account or network connection.

In a packaged kit use `./Author` on Linux or `Author.cmd` on Windows instead
of `python3 tools/author.py`. These launchers preserve caller-relative paths,
JSON stdout and exit codes; their installed location may contain spaces.
CLI discovery (`capabilities`, `schema`, `recipe list`) does not open a window.
The Windows kit needs the installed or explicitly bundled Python described in
the [delivery guide](CONSTRUCTION_KIT_DELIVERY.md).

`--check` and `--play` accept the normal resource switches:

```sh
python3 tools/author.py recipe build \
  --file examples/authoring/greybank/recipe.json --output "work/My checked game" \
  --check --data "Original DOS" --dialogue-data work/talk-data.bin \
  --combat-data work/combat-data.bin --world-data work/world-data.bin
```

The launcher prepares these caches from your files in **Player setup**. They
can also be prepared with `tools/prepare_talk.py`, `prepare_combat.py` and
`prepare_world.py`, each accepting `--data` and `--output`. The recipe command
does not download resources. Missing files produce `dependency.missing`
diagnostics naming the relevant switch, a nonzero exit code and a retained
editable campaign. Corrupt/incompatible resources still need native checks.

## What is produced

| Path | Purpose |
| --- | --- |
| `game/` | Validated playable package; open in the launcher or native player |
| `source/` | Modular source project; open this for ongoing GUI/AI editing |
| `expanded/` | Initial ordinary-package expansion, retained for inspection/replay |
| `inputs/` | Exact seed package, unit bundles, Lua source and creation batch |
| `recipe.json` | Explicit parameters used for generation |
| `build-report.json` | Input/tool hashes, content fingerprint, counts and dependency declaration |
| `scenarios/` | Editable route scenarios and seeded suite |
| `checks/` | Deliberate failure, repair, gameplay reports, checkpoints and replayed build |
| `visuals/` | Depot/recovery/escort map previews, contract graph and roster contact sheet |
| `demo-report.json` | Overall result and artifact locations |
| `play/` | Isolated save location and player log when using `--play` |

Edit **one** source of truth. For ongoing work use `source/`, then
**Project → Campaign sources and build → Build** or `author.py source build`.
`game/` and `expanded/` are initial outputs, not automatically synchronized
copies. Gameplay edits change strict save identity; retain the old game for
its existing saves. The example uses current v2 mission mechanics/save v51;
the larger v3 budgets are available by explicit upgrade when needed.

`--check` first validates/analyzes the campaign, deliberately overlaps a raider
with the player formation, records `deployment.overlap` and a failing route,
then repairs the enemy with a scoped `marker.move`. The final source is restored
even if the diagnostic check fails. It completes both branches at the recipe
seeds and separately checks defer, retreat, abandonment and defence failure.
Checkpoints include active combat and the finale. A tiny independent Beacon
fixture runs without original resources. Visual previews and actual captured
game frames accompany the reports.

The check also replays `inputs/creation.commands.json` against a new copy of
`inputs/template`, converts it to source and builds again. Its runtime
fingerprint must match both the deliverable and repaired source. This proves
reproduction from **recorded commands**, not deterministic free-form AI output.
The reports pin tool hashes and seeds. Scenario samples do not prove general
combat balance or every possible edit. Check output is bounded by the existing
scenario/suite budgets and supports `--cancel-file PATH`.

## Vary or reuse a recipe

Copy `recipe.json`, then change these schema-checked parameters:

| Parameter | Meaning |
| --- | --- |
| `package_id`, `title` | A separate game's identity and display name |
| `starting_credits`, `repair_cost` | Opening funds and depot service price |
| `assault_reward`, `recovery_reward` | Payment for the selected opening contract |
| `defence_reward`, `escort_reward` | Later contract payments |
| `defence_rounds` | Protect the relay for 3–8 rounds |
| `seeds` | One to three explicit 24-bit scenario seeds |

The exact limits are discoverable with `recipe list` and in
[the recipe schema](../schemas/greybank-recipe-v1.schema.json). More difficult
parameters can produce a failed gameplay suite; successful structural
validation alone does not establish a winnable mission. This first recipe
has fixed component IDs, layout and roster. It is not an arbitrary mission
template language. After expansion, normal editor/command operations can
change any of those objects with the usual revision and scope checks.

The component recipes remain separately available as `mission_demo.py`
(Argent Recovery) and `combat_mission_demo.py` (Cairn Passage). Their generated
mission objects are ordinary JSON. Use the [mission state](MISSION_STATE.md)
and [combat mission](COMBAT_MISSIONS.md) guides when adapting their conditions,
groups, hooks and waypoints. For units, tiles and complete structures, use the
[catalogue and visual discovery commands](AI_AUTHORING_GUIDE.md)
and [Construction Library](CONSTRUCTION_LIBRARY.md); imports carry dependencies
and source notes rather than relying on a local library's hidden state.

## External authors and human edits

Any assistant or automation that can run a program and read/write JSON can use
the same CLI. Give it the brief, project path and author guide, then have it:

1. Discover `capabilities`, schemas, current revision and relevant catalogue
   entries; inspect labelled map/sprite previews before changing content.
2. Propose a batch with explicit scope and expected revision. Use `--dry-run`
   for a closed saved project, or the editor's **Local authoring session** for
   live snapshots and proposals that include unsaved human drafts.
3. Review actual changes through **Changes and protection**, preserve named
   objects/fields/map regions, then check affected routes and accept through
   normal Undo/Save. Stale revisions require a fresh snapshot.

The [local-session protocol](AI_AUTHORING_GUIDE.md)
is the existing thin transport over the shared schemas. Provider/model choice,
credentials and prompts belong to the external assistant; none are saved in
the game or required by the editor/player. There is no embedded model/chat
panel. The AI8 GUI verification exercises terrain and dialogue edits followed
by a scoped briefing revision, preservation rules, Undo/Redo, Save/reopen and
native Play. It uses scripted GUI gestures on a disposable campaign.

## Deliver and check the installation

The [distribution workflow](CONSTRUCTION_KIT_DELIVERY.md) includes `Author`,
schemas, recipes, catalogues, examples, docs and native validation/playtest
tools. Check a Linux kit from any working directory:

```sh
"/path/Construction Kit/Author" capabilities
"/path/Construction Kit/ConstructionKit" --check-runtime
```

The runtime check covers both the GUI and console authoring workflow.
The equivalent private-display probe command is
`python3 tools/native_smoke.py --delivery-only "path/to/kit"` from a checkout;
it runs both GUI and CLI checks through the bundled interpreter/environment.
On native Windows use the installed/bundled Python to run
`tools/runtime_probe.py` and `tools/author_delivery_probe.py`.

Distribute the compiled `game/` with a compatible native player and the
declared, separately licensed resources. The player reads only runtime files;
it needs neither `tools/`, Python, an editor session nor a model. Exported
independent fixtures are tested in a native-only folder. Original CHI assets
are excluded from both kit distributions and generated packages.
