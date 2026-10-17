# Archived unit authoring prototype

This offline experiment predates the shared runtime contract. New work should
use the [playable Workshop project](../project-demo/README.md) and
[project guide](../../docs/M5_AUTHORING_PROJECTS.md). Its unimplemented sprite
and construction semantics are not silently treated as CHI content.

This independently authored example defines **Trail Kite**, **Quarry Guard** and
**Ridge Hopper**, two weapons and one placeholder sprite sheet. Its names and
statistics are invented for validation; no original game data or artwork is
included. It is covered by the repository's GPL-3.0-only license.

It is **not yet a playable package**. The current player continues to load the
original DOS resources. This sample exercises the provisional contract for M5a,
before committing to a runtime loader or editor.

From the repository root, using only Python's standard library:

```sh
python3 tools/validate_content_prototype.py examples/content-demo/content.json
python3 tools/validate_content_prototype.py examples/content-demo/content.json --canonical
python3 -m unittest discover -s tests -p test_content_tools.py
```

The first command reports counts and a deterministic definition digest. The
second writes normalized JSON to stdout. Both return nonzero on failure and
identify fields such as `/mechs/0/loadout/0/weapon`. Original assets and compiled
executables are not required. `--no-placeholders` intentionally rejects this
sample until authored files replace its placeholder.

## Contract and limits

[content-v1.schema.json](../../schemas/archive/content-prototype-v1.schema.json) supplies structural
rules, field units, limits and required fields. The offline validator reads that
same schema, then checks references and cross-field consistency. Its small JSON
Schema keyword subset is specific to this file; unsupported schema keywords
fail instead of being silently ignored. JSON must be UTF-8, at most 1 MiB, with
unique object keys and finite integral numeric values. Unknown fields fail.

- IDs use `package:local-name`, are unique across definition kinds, and belong
  to `package_id`. Names, list order, party slots and original DOS tags do not
  identify a model. References must name the right definition kind.
- `content_version` describes the sample content. `schema_version` describes
  these authoring files; `rules_profile` selects the provisional rule contract.
  None changes original BTPe/v40 saves or claims runtime compatibility.
- Walk and jump are base combat movement points; run uses the future rule
  implementation. Walk/run are required. Positive jump points require `jump`.
  The only declared capabilities are walk, run, jump and kick. New rules such
  as flight or electronic warfare need implementation, not just another flag.
- Armor, structure, damage and heat are integer points. Mass is whole tonnes.
  Ranges are inclusive combat grid cells. Damage is per projectile; ammunition
  consumption and heat are per trigger pull. Starting ballistic/missile mounts
  need at least one shot; energy mounts have no ammunition.
- Loadout slots are explicit 0–10 identities with named body locations. The
  authoring limits are bounded experiments, not a promise that every definition
  fits an original 125-byte record. M5a must resolve instance storage, location
  mapping, critical slots, hit rules, services, AI and persistence before play.
- Sprite dimensions are pixels. Frames run row by row across the sheet. Each
  animation entry starts eight consecutive directional frames, ordered north,
  northeast, east, southeast, south, southwest, west, northwest. Entries give
  time order, and each block must fit the declared geometry. Cadence, palettes,
  portraits and audio need further metadata during M5a/M5b.
- `placeholder` has no file. `external_sheet` requires an existing regular file
  below the content directory with exact letter case and a portable relative
  path using `/`. Absolute paths, traversal, Windows device names and symlinks
  fail. At this stage the validator checks file presence and declared geometry;
  it does **not** decode images or verify their actual dimensions/format.

Canonical output sorts definitions by ID, loadouts by slot and capabilities by
name, while retaining animation frame order. Its SHA-256 covers definitions
only, not external file contents. It is useful for repeatability checks, not a
package-integrity signature or a save-compatibility guarantee.

M5a must put semantic validation behind a shared runtime interface before the
player/editor accepts this format. These provisional files can change during
that work; existing game play has no dependency on them.
