# Independent demonstration game and map/event editor

Implemented 2026-10-17. Scope: roadmap task 4 and the map/event portion of
task 5. Original/Updated, CHI-dependent authored projects and their saves remain
supported. Both reference directories remain protected.

## Play and edit

With the existing build:

```sh
./build/btp-project validate examples/beacon-demo
./build/btech-port --project examples/beacon-demo --save-file work/beacon-game.btp
python3 tools/game_editor.py examples/beacon-demo
```

[Last Beacon](../examples/beacon-demo/README.md) contains a town, wilderness,
Walker Exchange, Relay Office, Mira's recruitment, a guardian battle, payment
and an ending. Talk to Mira or visit the office, travel east, clear the relay,
then return to the office. Buying another walker is optional. Space/Enter
selects, arrows travel, Escape cancels, F4 shows the map, F5/F9 save/restore,
Ctrl+Shift+Escape exits. The ending accepts any key.

For a separate build with **no original files or caches**, install the normal
C11/CMake/SDL2 build dependencies and use:

```sh
cmake -S . -B build-demo -DBUILD_TESTING=OFF
cmake --build build-demo -j2
./build-demo/btech-port --project examples/beacon-demo --save-file beacon-game.btp
```

The headless player can be built with `-DBTP_FRONTEND=OFF` and needs no SDL.
Lua is built from the vendored source; no Lua system installation or DLL is
required. The full original-game CTest suite still requires the user's original
files/caches, so it is disabled in the independent-only build above.

The editor requires Python 3.10+ with Tk. `tools/roster_editor.py` remains an
equivalent launcher. Set the player executable in Player setup if using
`build-demo/` or a Windows build. Independent projects require only the player
path; CHI projects continue requiring their four explicit dependency paths.
On Windows use `py tools/game_editor.py ... --validator PATH/btp-project.exe`.

Use **New project** before modifying the shipped example. With no project open,
New uses Last Beacon as the independent template; with one open, it makes a new
copy of that project. New identity/version and original declared inputs are
validated before publishing the new directory. It retains package licensing
and attribution and excludes saves/caches/unrelated files.

## Editor workflow

The existing roster forms and the Maps / events window share one document and
one undo/redo history. The latter has three tabs:

- **Maps:** create/resize maps and edit names/world origins; paint base tiles or
  rectangular overlays; transparent erase applies only to overlays. A whole
  mouse stroke is one undo step. Zoom/scroll, a terrain view and selected-layer
  bounds help distinguish artwork from collision. Independent games show actual
  package tile pixels; CHI projects show terrain/key swatches.
- **Placement:** choose Entrance, NPC, Encounter or Start, then click the map.
  Entrances/NPCs select an event; NPCs select a character template. Encounter
  forms declare map, party spawn and individual enemies, with Add/Edit/Remove.
  The marker list supports editing and removal. Coordinates are half tiles;
  the cursor/status also shows tile coordinates. World origins/overlays use
  whole tiles. Place doors far enough in front of roofs for a full mech party.
- **Events:** New/Duplicate/Delete, opcode selection, dialogue, portraits,
  continuations, up to five choices and typed forms for conditions, flags,
  credits, recruitment, transfer, shop, battle, Lua routes and finish. Apply
  adds an undo step. Changing selection or saving applies pending text; Undo can
  discard a half-typed form. Long forms scroll rather than overflow.
- **People, shops and start:** character templates/names/stats, shop stock,
  flags, start map/event/credits and initial party/mech assignment.

Save/Validate uses the **same C loader as the player**. Invalid intermediate
work can remain in memory; it cannot overwrite a valid disk project. Deleting
something referenced elsewhere causes a validation error until its references
are fixed. Existing event IDs remain stable; Duplicate creates a new identity.
Map and character IDs should likewise be treated as stable references.

Definition and adventure changes save together after full-package validation.
Each replacement is atomic; a flushed rollback journal records the prior files
before a multi-file save. Reopening after an interrupted save restores those
prior snapshots. If another program also edited a pending file, recovery stops
and preserves the files for review. It is not a replacement for version control.

**Play** starts a fresh campaign. **Play here** starts the declared initial party
at the selected map/half tile and skips the start event, with all flags initially
clear. The whole formation must fit. It does not resume a current campaign or
mark a quest complete. Preview saves are isolated by exact project revision
under the editor's state directory. A command-line equivalent is:

```sh
./build/btech-port --project examples/beacon-demo --play-here beacon:wild 12 28
```

**Export** validates and copies declared package files plus licenses/credits to
a new directory, preserving package identity and snapshot compatibility. It
does not bundle the player, SDL, Python, original dependencies or private saves.
The exported independent directory is directly playable with `--project`.

## Independent package contract

`btp-project-v1` now accepts `"requires": "none"`, requiring
`"startup": "authored-adventure-v1"`, an adventure and a `presentation` file.
The independent branch allocates fresh resources and does not enter the DOS
resource/cache loader. CHI-dependent manifests retain their previous contract.

[presentation-v1.schema.json](../schemas/presentation-v1.schema.json) describes
`btp-presentation-v1`: sixteen RGB palette colors, 96 printable-ASCII glyphs
(five by seven), 1–64 sixteen-pixel-square tiles, five four-frame sprite families,
two 64-pixel-square portraits, hit-location schedule, formations, a personal
weapon adapter and eighteen short tone programs. Bitmap rows contain lowercase
hexadecimal palette indices. Index zero is transparent only for sprites.
Each tone gives frequency/duration; sound programs are limited to 1.2 seconds.
The shared audio scheduler preserves event order and saves queued tones.

Independent definitions use `package:walker-a` / `package:walker-b` sprite
sources and `package:tiles` terrain. Visual indices must resolve in the declared
presentation. Portrait selectors `broker` and `training` refer to the two package
pictures; other CHI portrait slots are rejected. Independent character templates
require a display name and use `actor:0` through `actor:9` identities. They are
simulation identities, not raw party positions; the first party member uses
identity zero. Stationary NPC markers disappear once that template is recruited.

The new `finish` event holds paginated ending text and then an any-key exit
screen. Both held states save/reload. Old `end` still returns to exploration.
The v48 authored continuation supports these phases; its package fingerprint
prevents interpreting new content with old definitions. Existing v47/v48
CHI-dependent project saves and Original/Updated envelopes remain supported.

The strict package fingerprint now includes the presentation and each declared
script snapshot after adventure data, before portrait assets. Optional files
are added only when declared; old manifests retain their previous fingerprints.
Whitespace and script/art edits still require a new campaign or restoring the
old snapshot. Arbitrary save migration remains outside this increment.

The demo pixels, font, text, tones and invented definitions are GPL-3.0-only,
with provenance in its CREDITS.md. They are reproducible from
`tools/make_beacon_demo.py`, which reads only this repository's own diagnostic
font and authored examples. It does not read original assets or caches.

## Bounded Lua commands

Lua 5.4.9 is vendored from the [official release](https://www.lua.org/ftp/),
under its MIT license, with the verified archive SHA-256, unmodified source
and notice in [third_party/lua](../third_party/lua/README.md).
No standard libraries are opened. The only exposed functions are:

| Function | Meaning |
| --- | --- |
| `game.flag("id")` | Read a declared Boolean flag |
| `game.credits()` | Read current credits |
| `game.command("event-id")` | Select one of this node's declared command routes |

Declare source files in manifest `scripts: [{id, file}]`. A `lua` event specifies
`script`, 1–5 `routes` and `failure`. Return `game.command(...)`; the selected
event then runs through the ordinary saved command runner. Last Beacon's
`contract.lua` selects a recruitment offer, reminder, once-only reward or
already-completed response using flags.

Each invocation has a fresh VM, 256 KiB allocation limit, 10,000-instruction
budget and at most 8 KiB of text source. Bytecode and syntax errors fail package
validation. Runtime errors/budget exhaustion take `failure` and report the node
in the player log, without partially applying a command. There is no file, OS,
network, module, clock, random-number or raw-state API. No Lua stack/global state
is saved. New mutable capabilities must go through explicit engine commands.

## Bounds and verification

This remains a small editor for the existing tactical rules/party model: four
owned mechs, eight party slots, bounded named body locations/equipment and
finite maps. It reuses the documented compatibility combat algorithms; it does
not implement arbitrary abilities or a new rules designer. The authored
hit/cluster adapter is intentionally small, and existing essential-character
loss rules remain part of the shared tactical profile. There is no procedural
world editor, free-running NPC AI, asset painting, audio timeline, script source
IDE, rich visual event graph, automatic package migration or installer builder.
Lua source and raw presentation edits use external editors; basic quests can
be authored entirely with the provided event forms.

Updated defaults to Enhanced combat on fresh campaigns. A new Original/DOS save
import into Updated now also receives Enhanced when the pack supplies that
profile; it contains no prior Updated preference. Existing Updated saves retain
their explicit saved Enhanced/Legacy choice and old compatibility policy. A
pack without an Enhanced profile retains its supported Legacy behavior.

**VERIFIED so far:** full native CTest 67/67 and Python tools 67/67. The complete
independent quest test saves/restores every held dialogue and ordinary action,
regular combat checkpoints, payment, ending and quit; authored PCM is nonzero.
It checks manual combat cursor movement without an original map loaded. Python
tests exercise absent/malformed assets, strict art/script binding, Lua syntax,
path escapes, infinite loops, memory exhaustion, missing OS APIs, undeclared
commands, atomic-save recovery, export and Play here.

Linux SDL passes nine held F5/F9 checkpoints with identical resumed headless
state/pixels, plus a full ordinary-input quest through combat/ending. The Tk
smoke creates a map, paints a stroke/overlay, uses undo/redo, edits a branching
event, places an NPC/encounter, saves both roster/map changes, reopens, exports
and launches the real player at a chosen map position. Screenshots/logs live
in ignored `work/`. Windows and sanitizer completion results follow below.
