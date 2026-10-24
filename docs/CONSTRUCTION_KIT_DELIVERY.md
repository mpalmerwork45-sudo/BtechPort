# Distributing and updating a Construction Kit game

The visible editor and launcher name is **BattleTech Construction Kit**. Source
checkout commands `./BtechPort` and `BtechPort.cmd` remain usable.

The [2026-10-24 package refresh](DELIVERY_REFRESH_20261024.md) records current
archive paths, hashes, requirements and packaged Linux/Wine verification.
Native Windows Tk remains an external acceptance check.

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

For the complete CHI import/editor/reconstruction and Saved games journey,
provide the original files explicitly and a new evidence directory outside the
kit. Every child uses the kit's bundled interpreter and tools, with no copied
original installation inside the distribution:

```sh
python3 tools/native_smoke.py --delivery-only work/releases/ConstructionKit-linux \
  --delivery-data "Original DOS" --delivery-output work/packaged-linux-proof
```

This also verifies current endgame dialogue extraction, edited original-text
references, six save slots and continuation after moving the editable project.
The evidence records the distribution inventory hash and each child report.

On a real Windows desktop, run `py -3 tools/runtime_probe.py` from the unpacked
kit, or use its bundled Python executable. Cross-build and Wine engine/SDL
checks pass; **native Windows Tk interaction remains unverified** until this
probe and ordinary editing are run on a Windows host.

### Native Windows acceptance sequence

**UNKNOWN until run on a Windows desktop.** Linux Tk with a Windows player
under Wine, and Windows Python/Tk running under Wine, are separate evidence;
neither closes this check. The development host has no configured Windows VM
or remote Windows desktop. The following sequence is prepared for a real
Windows 10/11 x64 machine or Windows VM with an interactive desktop.

Unpack the Windows kit into a **new writable folder**, such as
`C:\BCK Acceptance\Kit é 漢字`. Use this disposable kit's own state and new project
folders; do not point it at existing saves. Check `START-HERE.txt`: when Python
is not bundled, Python 3.10+ with Tk, Pillow and the `py` launcher must already
be installed. The embeddable Python ZIP is insufficient. No compiler, checkout,
Linux installation or extracted CHI cache should be needed for these checks.
Original DOS files are needed only for the explicit CHI import/reconstruction.

In PowerShell, set the two input paths below, then run the probes **from outside
the kit directory**. The new proof folder retains environment details, the kit
inventory fingerprint, both command logs and CHI save/reconstruction evidence.
Each probe must exit successfully; keep failure output if it does not.

```powershell
$kit = (Resolve-Path 'C:\BCK Acceptance\Kit é 漢字').Path
$source = (Resolve-Path 'C:\Games\Original DOS').Path
$proof = Join-Path (Split-Path $kit -Parent) ('Proof-' + [guid]::NewGuid())
New-Item -ItemType Directory -Path $proof | Out-Null
Set-Location $proof

if (Test-Path (Join-Path $kit 'runtime\python.exe')) {
    $python = Join-Path $kit 'runtime\python.exe'
    $pythonArgs = @('-E', '-s', '-B')
} else {
    $python = 'py'
    $pythonArgs = @('-3', '-E', '-s', '-B')
}
[System.Environment]::OSVersion.VersionString | Out-File environment.txt
Get-FileHash (Join-Path $kit 'DISTRIBUTION.json') -Algorithm SHA256 |
    Format-List | Out-File -Append environment.txt
& $python @pythonArgs -c "import sys,platform,tkinter,PIL; assert sys.version_info >= (3,10); print(sys.executable); print(platform.platform()); print(sys.version); print('Tk', tkinter.TkVersion, 'Pillow', PIL.__version__)" 2>&1 |
    Tee-Object -FilePath python-runtime.txt
if ($LASTEXITCODE -ne 0) { throw 'Python/Tk/Pillow prerequisites failed.' }

& $python @pythonArgs (Join-Path $kit 'tools\runtime_probe.py') 2>&1 |
    Tee-Object -FilePath runtime-probe.txt
if ($LASTEXITCODE -ne 0) { throw 'Desktop runtime probe failed; keep the log.' }

& $python @pythonArgs (Join-Path $kit 'tools\chi_delivery_probe.py') `
    --data $source --output (Join-Path $proof 'CHI proof') 2>&1 |
    Tee-Object -FilePath chi-delivery-probe.txt
if ($LASTEXITCODE -ne 0) { throw 'CHI delivery probe failed; keep the log.' }

& (Join-Path $kit 'ConstructionKit.cmd')
```

`runtime_probe.py` exercises the launcher, roster/map editor, PNG decoding and
encoding, native validation, an actual SDL window and independent authoring
CLI/gameplay. `chi_delivery_probe.py` imports both editions, moves them through
Unicode/spaced paths, round-trips twelve saves, rejects cross-edition loads,
reconstructs an edited quest recipe and restores Last Beacon's twenty original
tile bases locally. Its `windows_native_Tk: UNKNOWN` field describes that
**CLI probe's scope**, even when it runs on Windows; record the desktop probe
and the following manual observations separately.

Complete this small manual acceptance sheet, recording PASS/FAIL/NOT RUN and
screenshots or logs in the proof folder:

1. **Launch/import:** `ConstructionKit.cmd` opens with no terminal error. Import
   both CHI editions using **Import CHI**, a new output folder and the original
   files as read-only input. Check progress, Cancel, a visible error for an
   invalid source folder, and the two resulting launcher entries. Imported
   campaigns start without configuring external cache paths.
2. **Edit/save:** create a disposable independent project; edit a unit/sprite,
   map and event. Undo/Redo must restore the edited content. Save, close and
   reopen the project. Changes persist, dialogs stay above their owner, and
   errors do not discard unfinished fields. Check the imported campaign's map
   and building dialogue editors too, saving changes only in a disposable copy.
3. **Play/stop:** use editor Play, F5, F9 and Ctrl+Shift+Esc. Inspect all six
   in-game save slots; save/load slots 1 and 6, leaving another slot empty for
   recovery. Check editor Stop and restarting Play. The editor keeps its
   document; the game resumes the saved progress. Use Space and Enter in menus.
4. **Saved games/recovery:** open **Saved games...** in the launcher and
   **Play → Saved games** in the editor. Check six slot labels, dates, revisions,
   sorting and visible controls. Back up a save; Recover to an empty slot must
   copy it, and Recover to an occupied slot must refuse without changing either
   save. Continue selected must open its matching revision. Edit the working
   project, then move that disposable project folder; the older retained save
   must remain discoverable and continue with its original content. Confirm
   backups are visible after refresh.
5. **Desktop behavior:** test keyboard navigation, Escape/context-menu dismissal,
   canceled file choosers, unsaved-close cancellation, minimize/restore and
   100/150/200% editor scales. Test moving between monitors only if available;
   otherwise record that item NOT RUN. Check all action buttons remain visible.

Retain the evidence and exact Windows/Python/Tk versions before declaring this
platform verified. A passing automated probe alone does not certify native
file-dialog focus, display scaling, every manual route or hardware audio.

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

Imported native CHI campaigns have one separate, explicit compatibility policy:
the v24-to-v25 append of two endgame presentation strings. All earlier text,
font data and every other runtime file must remain byte-identical. The
[endgame copy updater](GAME_OVER_PRESENTATION.md#cache-compatibility-and-existing-campaigns)
creates a new project and optional validated save without changing the old
files. Native terrain, script, rule and roster changes remain outside this policy.

Both saves are checked by the real player against their exact content. The
payload—including damage, ammunition, position, flags and progress—remains
byte-for-byte identical; only the validated package envelope changes. Output
creation is exclusive. The original save is preserved. Ordinary loading remains
strict and does not silently migrate edited projects. The CLI prints an audit
report with checks and before/after hashes; configure original resources in
Player setup when migrating a CHI-dependent game.

## Editable CHI imports and provenance checks

The kit includes the offline [CHI importer](CHI_IMPORT.md) and
[edited-campaign reconstruction recipes](CHI_RECONSTRUCTION.md). Completed
imports own their resources and work after the source install is unavailable.
The launcher keeps imported project saves separate from its normal games.

After packaging, test the unpacked kit with its own bundled Python/tools from
another working directory. Supply the original files explicitly for extraction;
choose a new private output parent. This probe also reconstructs Last Beacon's
20 original tile bases locally:

```sh
/path/to/kit/runtime/bin/python3 -B /path/to/kit/tools/chi_delivery_probe.py \
  --data "/path/to/Original DOS" --output "/new/private/CHI delivery proof"
```

Use the bundled interpreter environment set by `ConstructionKit`/`Author`
(`PYTHONHOME`, Tcl/Tk and library paths) when invoking the interpreter directly.
`tools/native_smoke.py --delivery-only KIT` remains the full Linux desktop/CLI
probe. Native Windows Tk needs a separate Windows desktop check.

The packager scans the final staged bytes and the generated archive. You can
inspect either again, without extracting an untrusted archive:

```sh
python3 tools/release_guard.py work/releases/ConstructionKit-linux
python3 tools/release_guard.py work/releases/ConstructionKit-linux.tar.gz
python3 tools/asset_provenance.py check-staged
```

The guard enforces inventory hashes and rejects recognized original raw files,
converted cache signatures, private campaign documents, known original tile
pixels and declared original/unknown payloads. This extends the indexed-project
checks to all actual shipped files. Stripped/altered arbitrary assets still need
origin review; a passing guard is not license clearance. Personal work, imported
campaigns, test traces and saves stay outside the distribution.
