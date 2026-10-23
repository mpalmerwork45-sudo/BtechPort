# Import and edit a CHI campaign

The C1–C2 first pass imports separate Original and Updated campaigns from the
supported DOS 1.03 files. Each project owns its resources, edition settings and
six save slots. It can run without the original installation after import.
Existing launcher Original/Updated games and their saves remain separate.

**Current editing scope:** native dialogue overrides, plus Updated's existing
external unit/weapon definitions. Original maps, BLD programs, missions and
services execute through the compatibility runtime. Their complete editable
representations are C3–C4 work. The Citadel/training slice is verified against
the built-in editions; importing the full resource set is not evidence that
every campaign branch has been re-tested. See [progress](CHI_IMPORT_PROGRESS.md).
Original's added-unit list starts empty; its campaign mechs still use exact
compatibility templates rather than normalized library adaptations.

## Import through the launcher or editor

1. Build the application normally and launch `./ConstructionKit` or `./BtechPort`.
2. Choose **Import CHI** in the launcher, or **File → Import CHI campaign** in
   the Construction Kit.
3. Select the original game directory and choose **both**, **original** or
   **updated**. Select a new output folder inside an existing parent directory.
4. Press **Import**. Verification/extraction runs in the background; **Cancel
   import** discards unfinished staging and preserves existing projects.
5. Use **Edit** or **Play** beside a completed project. Both are registered in
   the launcher's game list. **My project → Choose project** also opens either
   `original` or `updated` subfolder, including projects created by the CLI.

The importer verifies all 77 required source files by SHA-256. A different,
incomplete or modified installation produces a specific file/version error.
It copies neither the DOS executable nor personal GAME saves. A failed import
publishes neither profile when Both is selected. Retry into a new destination;
resuming partial extraction is not currently supported.

The generated `IMPORT.json` lists input/output provenance and current editing
limits. It is informational; removing it does not turn the campaign into a
redistributable asset-free project. The manifest's imported dependency remains
an explicit original-derived-content boundary.

## Headless import and play

From the repository root:

```sh
python3 tools/chi_import.py --data "Original DOS" \
  --output "work/My CHI campaigns" --edition both

./build/btech-port --project "work/My CHI campaigns/original"
./build/btech-port --project "work/My CHI campaigns/updated"
```

On Windows, run the Python utility with the installed Python command and use
`build\btech-port.exe`. The importer resolves the platform's `btp-project`
validator automatically. Use `--validator PATH` for an explicit build.

Imported projects do not need the four external resource/cache arguments. Do
not combine `--project` with `--edition`. Updated defaults to Enhanced combat
and retains its supported Legacy selection; Original retains Original rules.

Reimporting creates new project IDs, even for the same edition. Keep the exact
old project for its saves. Normal Original/Updated saves cannot be loaded merely
by selecting an imported project; no automatic save migration is included here.

## Edit native dialogue

Open the project and choose **Project → CHI campaign**. Search/select a native
text ID, edit its text and press **Apply text**. An asterisk marks an override.
**Restore original text** removes the override. Apply/restore use the ordinary
Undo/Redo history; **Save project** persists the result. **Play** builds the
current validated project into its own test snapshot and save namespace.

Line breaks use the original carriage-return format. Text must fit the native
character and length limits; errors leave the previous document intact. This
view edits the 373 native text entries, not text embedded in BLD bytecode. Full
BLD text/control-flow editing is C4.

The same operation is available without the GUI:

```sh
python3 tools/chi_editor.py --project "work/My CHI campaigns/original" \
  --index 87 --text "Computer control for this campaign?"

python3 tools/chi_editor.py --project "work/My CHI campaigns/original" \
  --index 87 --reset
```

`--text-file FILE` accepts multiline text instead. Changing runtime text changes
the strict content fingerprint; preserve the old revision for its existing saves.
Imported projects also support the existing **Campaign sources and build**
conversion, shared validation, Save/reopen and private playable-package export.

## Original-derived art and sharing

Generated CHI campaigns are private local content. Their whole imported resource
set, converted caches and later edited derivatives retain original provenance.
Do not add them to Git or distribute them as though the code's license covered
the original game data. Generated folders include an ignore file.

The application packager validates the indexed project snapshot, excluding
uncommitted/private authoring changes. Last Beacon's public baseline now contains
independently drawn placeholders for 20 original-derived tile images and a
`CHI-TILES.json` reconstruction recipe. The launcher can reconstruct those tiles
into a private cache using the configured original files. It preserves the
distributed project and refuses to overwrite an edited cache.

Of those 20 historical tiles, 17 contained custom pixel edits. Public recipes
restore the recorded original base tiles; they do not reproduce those private
edits. The owner's existing working files were preserved byte-for-byte, with a
backup under ignored `work/chi-import/asset-cleanup/`. Earlier Git history was
not rewritten.

Explicit asset-free export and local reconstruction use:

```sh
python3 tools/asset_provenance.py public-export \
  --project MY_PROJECT --output NEW_PUBLIC_PROJECT

python3 tools/asset_provenance.py reconstruct \
  --project NEW_PUBLIC_PROJECT --output NEW_PRIVATE_PROJECT --data "Original DOS"

python3 tools/asset_provenance.py check-staged
```

Public export rejects imported CHI campaigns, copied caches, declared unknown
origins and original-derived artwork without a supported exclusion/recipe.
For known private variants with an explicit base recipe, public export replaces
the pixels with the placeholder and retains the recipe. This does not grant
rights to other content or detect arbitrary copied art whose provenance was
stripped. Keep origin metadata when cloning/editing/importing assets. Publishing
complete edited campaign recipes will be expanded in later milestones.

## Verification and remaining work

The [contracts](CHI_IMPORT_CONTRACT.md) and [numeric inventory](chi-import-inventory.json)
describe the versioned extension, bounds, profile flags and dependency ownership.
The [progress ledger](CHI_IMPORT_PROGRESS.md) records exact tests, evidence and
platform limits. The [five-milestone plan](CHI_EDITABLE_CAMPAIGNS_PLAN.md) defines
the remaining world/resource, story/service and delivery gates.
