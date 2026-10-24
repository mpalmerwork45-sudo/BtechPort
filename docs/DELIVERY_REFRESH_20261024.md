# Application delivery refresh — 2026-10-24

The application packages now contain the save/death fixes and the independent
[Astra audit corrections](CHI_ASTRA_AUDIT.md). Their source revision is
`fa7740e8286226d3630d164121af7e333ab935b9`; `DISTRIBUTION.json` records individual
file hashes. This report was added afterward. No package was published remotely.

## Packages and launch

| Platform | Local archive | Size | Requirements |
| --- | --- | --- | --- |
| Linux x86_64 | `work/releases/ConstructionKit-linux-20261024-final.tar.gz` | 50,022,489 bytes | glibc 2.42+, X11 and system fonts. Python 3.13, Tk 8.6, Pillow, SDL and non-glibc dependencies are bundled. |
| Windows x64 | `work/releases/ConstructionKit-windows-20261024-final.zip` | 12,784,232 bytes | Windows 10/11; Python 3.10+ with Tk, Pillow and the `py` launcher. SDL DLLs are bundled; Python is not bundled. |

Extract into a new writable directory and run `ConstructionKit` on Linux or
`ConstructionKit.cmd` on Windows. The already-unpacked Linux kit is runnable
from the checkout with:

```sh
./work/releases/ConstructionKit-linux-20261024-final/ConstructionKit
```

These are clean distributions with their own settings and saves. The existing
checkout launcher and recovered saves remain where they were; replacing the
checkout with a package is unnecessary. Use **Import CHI** with a locally owned
DOS installation to create the two editable campaigns. Original assets and
personal saves are excluded. The packaged examples use their committed public
payloads; pending owner artwork/map edits are preserved in the checkout.

Archive SHA-256:

```text
Linux   7a67e312f30cf07fb1a348a548a03408b5f7306176cd1bf02e3468e82e3f0bd7
Windows c21822e3c4373660eb478bbfb840b002b9df992cb9b94c20df6ab17437ca14bc
```

## Verification

**VERIFIED: Linux packaged desktop and CLI.** The delivered interpreter,
modules and native binaries run from an external proof directory on a private
X display. All four steps pass:

- Launcher, roster/map editor, PNG round trip, SDL player, independent authoring
  CLI, source build, scenario/checkpoint, missing-asset diagnostic and native-only
  exported game.
- Fresh Original/Updated imports, moved Unicode/spaced paths, twelve native
  save round trips and cross-edition rejection. Both imports contain the current
  375-entry dialogue cache. Retained revisions continue after invalidating and
  moving the working project; backups/recovery preserve exact bytes.
- Real import wizard, error/retry/cancel, text editing, Undo/Redo, Save/reopen,
  unsaved recipe export/reconstruction, native Play/F5/Stop, logo startup and
  default Enhanced rules for Updated. Coverage navigation opens script source.
- Launcher/editor Saved games, six-slot dates, Continue/quicksave/quit, backups,
  occupied-slot rejection, empty-slot recovery, old revisions, moved roots and
  invalid editor drafts. Failed discovery clears stale actionable rows.

The recipe check edits a quest, cloned BLD text and native dialogue, excludes
retained original text spans from the recipe, and rebuilds exact content from
local originals. The clean Last Beacon example reconstructs all twenty original
tile bases locally. No imported campaign or extracted resource enters an archive.

**VERIFIED: actual packaged Windows binaries under Wine.** Both imported
campaign validators match Linux; all twelve loaded/resaved saves match Linux
state and bytes, and all twelve cross-edition loads are rejected. Edited and
reconstructed campaigns validate to identical fingerprints. Both editions'
five-input SDL intro replays match Linux final state and pixels. This exercises
the shipped `.exe` files and DLLs, not native Windows Python/Tk.

Six affected Python tests pass. Production native targets were built with two
jobs on each platform, sequentially. No production gameplay or save format was
changed; the earlier full-suite/campaign evidence remains separate from this
bounded package verification.

Both final directories and archives pass inventory and provenance inspection:
2,444 Linux files and 1,234 Windows files including their manifests, with nine
public projects each. The tested modules match the reviewed checkout bytes.
The guard detects known/declared original payloads; it is not a universal detector
for stripped or altered copyrighted content.

## Reproduction and retained evidence

```sh
python3 tools/native_smoke.py \
  --delivery-only work/releases/ConstructionKit-linux-20261024-final \
  --delivery-data "Original DOS" --delivery-output work/new-packaged-proof
python3 tools/release_guard.py work/releases/ConstructionKit-linux-20261024-final.tar.gz
python3 tools/release_guard.py work/releases/ConstructionKit-windows-20261024-final.zip
python3 -m unittest discover -s tests -p 'test*delivery*.py' -v
```

Private reports are under `work/delivery-refresh-20261024/`: package hashes,
`linux-proof-final/evidence.json`, the three child reports, screenshots and
command logs. `windows-proof-final/evidence.json` and `commands.jsonl` record
the Wine checks; `windows_package_probe.py` records their exact private driver.
Proof output must be new; earlier failures remain intact.

The first packaged GUI run exposed a harness environment error: child processes
did not inherit direct-focus mode for the window-manager-free virtual display.
The wrapper now propagates it. Independent review also found a local variable
shadowing the valid DOS source before the import cancellation check; it is fixed.
Neither issue changed the production game. The first Wine attempt was blocked
by the sandbox's read-only server-lock directory; its failure report is retained.

Preservation checks pass for both reference trees (1,287 content/mode/mtime
entries), the three pending owner edits, twenty normal saves (hashes/mtimes),
the recovered source save and all four recovered progress-payload copies.

## Remaining platform check

**UNKNOWN: native Windows Python/Tk interaction.** No configured Windows desktop
or VM is available on this host. The [Windows acceptance sequence](CONSTRUCTION_KIT_DELIVERY.md#native-windows-acceptance-sequence)
records prerequisites, exact commands and manual import/edit/save/Play/recovery/
scaling checks. It must be run on a Windows desktop; Linux Tk and Wine player
results cannot close it. This Linux archive also has not been tested on an older
distribution and explicitly requires glibc 2.42 or newer.
