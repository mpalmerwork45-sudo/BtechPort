# Share changes to an editable CHI campaign

**Project → CHI reconstruction recipes** exports an edited Original or Updated
campaign as a small JSON recipe. Another user supplies their DOS 1.03 files and
the matching Construction Kit version to reconstruct the private, playable
project. Keep the complete local project and its backups for editing and saves.

## Editor workflow

1. Open the imported campaign. Apply any draft fields you want included.
2. Open **Project → CHI reconstruction recipes**. Choose the original game folder.
3. Use **New…** beside Recipe JSON file, then **Export current project recipe**.
   This includes the current validated document, including unsaved changes. It
   does not save or reset the working project. Export checks reconstruction
   before publishing the recipe. Existing files are never replaced.
4. Give the recipient the recipe and the matching kit version/commit. Include
   credits and licenses for any independently supplied additions.
5. The recipient uses **Open…** to choose the recipe, selects their DOS folder
   and a new project folder, and presses **Reconstruct recipe**.
6. **Open reconstructed project** opens the result for editing and Play. Ordinary
   launcher **Choose project** can also select that folder.

The workspace task controls can cancel the work before publication. Failed or
cancelled work preserves existing projects and saves. If cancellation arrives
after atomic publication, the completed output is reported normally. Correct
the source/path error and retry with an unused output filename/folder.

## CLI and AI workflow

In a source checkout:

```sh
python3 tools/author.py chi-recipe export \
  --project "work/My CHI campaigns/updated" --data "Original DOS" \
  --output "work/My campaign changes.json"

python3 tools/author.py chi-recipe build \
  --file "work/My campaign changes.json" --data "Original DOS" \
  --output "work/Reconstructed campaign"

./build/btech-port --project "work/Reconstructed campaign"
```

An unpacked kit provides the same commands through **Author** or **Author.cmd**.
Use absolute paths when invoking it from another directory. The standalone
`tools/chi_recipe.py export|build` utility exposes the same service.
`Author capabilities` advertises the interface and
[schema](../schemas/chi-recipe-v1.schema.json).

## What a recipe contains

The `btp-chi-recipe-v1` document records the edition, project identity, matching
baseline/result digests and changes to declarative files. Stable IDs identify
BLD nodes and other records. Copies refer to baseline objects; text and pixel
edits use changed spans. Original screens, sprite frames and other detached
images are regenerated from resource/index references before applying edits.
Unchanged original programs, dialogue, maps, pixel bases and binaries are not
bundled. Applying a recipe never executes Python or shell commands.

Reconstruction validates the native project and proves the exact runtime-file
digest before publishing. Runtime bytes, project ID and content version match
the exported revision; saves for that exact revision retain their strict
identity. Launcher registrations, machine settings, editing history, arbitrary
extra files and personal saves are not exported. Registration is deliberately
separate because the reconstructed project retains the source project ID.

## Limits and recovery

- Both sides need the supported unmodified DOS 1.03 files and matching importer
  revision. Baseline mismatches fail with instructions to use the matching kit
  or export a fresh recipe. There is no guessed cross-version migration.
- Use the ordinary source-aware resource/pixel editors for original art. A
  changed raw binary resource is rejected because it cannot be safely exported
  as an asset-free recipe. Unsupported/missing art provenance must be repaired.
- Edited JSON must use the editor/source builder's canonical serialization.
  Save it through the editor before export if a custom serializer was used.
- Independently authored JSON/Lua content can be included. Other new binary
  formats need a separately licensed asset package and a future explicit import
  contract. This recipe format does not smuggle arbitrary files into a project.
- Inputs are bounded to 16 MiB, 256 files and 32,768 changes. Paths, original
  references, preconditions and the final native package are checked. A failed
  build does not publish a partial project.
- Editing copied art/text does not erase its origin. The exporter avoids known
  original payloads, and the distribution guard checks known hashes/formats and
  declared provenance. Neither can identify every altered asset with stripped
  provenance or establish redistribution rights for arbitrary new content.

**File → Export game** still creates a complete private playable project. It is
different from a sharing recipe. Imported CHI projects must not be shipped as
application examples. Last Beacon's existing `CHI-TILES.json` workflow remains
available; it restores the recorded original tile bases, while this general CHI
recipe service preserves supported edits to whole imported campaigns.
