# Distributing and updating a Construction Kit game

The visible editor and launcher name is **BattleTech Construction Kit**. Source
checkout commands `./BtechPort` and `BtechPort.cmd` remain usable.

## Export a game

**File > Export game** creates a validated new project directory. **Project >
Assets and dependencies** lists declared files, SHA-256 hashes, owned pixel images,
external original-game requirements and source documents. The report can be
saved as JSON. Library imports retain source attribution and editable art layers.
An inventory does not establish permission to redistribute imported artwork.
Copies made from original sprites remain original-game artwork.

## Build an application distribution

After building both executables, run:

```sh
python3 tools/delivery.py --output work/releases/ConstructionKit-linux
python3 tools/delivery.py --platform windows --output work/releases/ConstructionKit-windows
```

Output must be a new directory. Add `--archive` to also create a `.tar.gz`
(Linux) or `.zip` (Windows) containing only inventoried files. The Linux packager copies the locally installed
distribution Python, Tk, Pillow, SDL and non-glibc dependencies, copyright
notices, project source/build files, examples and catalogues. It uses no network.
Run **ConstructionKit** inside the resulting folder; it sets its own runtime
paths and works from another working directory. It requires Linux x86_64, a
compatible glibc (at least this build host's version), X11 and system fonts.
This is a portable folder for compatible systems, not an all-distributions
AppImage. It does not include original DOS assets, extracted caches or saves.

Windows output includes the player and SDL DLLs. Run **ConstructionKit.cmd**.
Without an explicit runtime it requires Python 3.10+ with Tk and Pillow installed
on Windows. To bundle a full existing Windows Python installation, add
`--python-runtime PATH`; it must include `pythonw.exe`, `Lib/tkinter`, Pillow
and their licenses. The embeddable Python ZIP alone does not include Tk.
The packager does not download or install prerequisites.

`DISTRIBUTION.json` inventories all output hashes and dependency origins;
`ASSETS.json` inventories example packages; `START-HERE.txt` records runtime
requirements. Engine, tools and vendored Lua source are included with licenses.
Building the included source still requires the compiler/CMake/SDL development
dependencies described in README; ordinary launching uses the bundled binaries.

**Author** (Linux) and **Author.cmd** (Windows) start the console authoring CLI.
They preserve relative paths, JSON stdout and failure exit codes; use them from
any working directory, including installations with spaces in their paths.
Try `Author capabilities` or `Author recipe list`. Schemas, recipes, source
tools, catalogues and native analysis/playtest programs ship in the same kit.
See [recorded campaigns and external authoring](CAMPAIGN_RECIPES.md). There is
no required provider SDK, model configuration or network service.

Linux validation runs the bundled launcher, roster/map editor, PNG round trip,
validator and actual SDL player from outside the checkout. It also exercises
CLI discovery, generation, source build, gameplay/checkpoints, missing-asset
diagnostics and an independent exported game with only its native player:

```sh
python3 tools/native_smoke.py --delivery-only work/releases/ConstructionKit-linux
```

On a real Windows desktop, run `py -3 tools/runtime_probe.py` from the unpacked
kit, or use its bundled Python executable. Cross-build and Wine engine/SDL
checks pass; **native Windows Tk interaction remains unverified** until this
probe and ordinary editing are run on a Windows host.

## Migrate a saved game deliberately

Use **Project > Migrate an old save**. Select the exact old project snapshot,
its save, and a new output filename. The currently open, saved project is the
destination. A playtest checkpoint's `game` folder is a suitable old snapshot.
The equivalent command is:

```sh
python3 tools/save_migration.py --old-project path/to/old-game \
  --new-project path/to/new-game --save old-save.btp --output migrated-save.btp
```

The first migration policy accepts cosmetic changes and appended definitions
while preserving all old unit, weapon, person, flag and event ordinals. Existing
rules, map topology, encounters, formations and script source must match.
Deleted/reordered definitions or gameplay changes are rejected with a reason.
This is deliberately narrower than a general content remapper.

Both saves are checked by the real player against their exact content. The
payload—including damage, ammunition, position, flags and progress—remains
byte-for-byte identical; only the validated package envelope changes. Output
creation is exclusive. The original save is preserved. Ordinary loading remains
strict and does not silently migrate edited projects. The CLI prints an audit
report with checks and before/after hashes; configure original resources in
Player setup when migrating a CHI-dependent game.
