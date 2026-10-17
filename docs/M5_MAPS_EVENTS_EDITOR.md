# Authored maps, events and the small roster editor

Implemented 2026-10-17: roadmap task 3 and the roster portion of task 5.
This document records that CHI-dependent increment. The subsequent
[independent game/editor](M5_INDEPENDENT_GAME_EDITOR.md) implements task 4 and
extends the same GUI with map painting, placement, event forms and export.
These are **CHI-dependent projects** using the existing C player and validator.
Original and Updated still use their existing campaign, original BLD adapter
and save formats. This increment introduces no original-game behavior claims.

## Try the playable example

Build and prepare the three caches using the main README, then run:

```sh
./build/btp-project validate examples/adventure-demo
./build/btech-port --project examples/adventure-demo \
  --data "Original DOS" \
  --dialogue-data work/talk-data.bin \
  --combat-data work/combat-data.bin \
  --world-data work/world-data.bin
```

Frontier Depot starts with a Rook and 12,000 C-bills. Approach the western
doorway to buy a Kite, the eastern doorway to recruit Rex, and the eastern
end of the road to travel to the proving ground. Assign the purchased mech
through the Space menu. At the proving ground, approach the patrol marker to
fight. Winning grants 2,500 C-bills once; withdrawing leaves the contract open.
The scenario intentionally uses invented statistics and dialogue, not a new
BattleTech canon scenario. Original resources are supplied by the player.

Use arrows/numpad to move, Space or Enter to select, Escape to decline a door
or back out of choices, F5/F9 to save/restore and Ctrl+Shift+Escape to exit.
The Space menu retains inspection, crew allocation, settings, healing, the
overhead map and six save slots. Authored projects start at their declared
event rather than showing CHI's logo and new-cadet questions.

## Roster editor

Run with **Python 3.10 or newer and Tk**; there are no pip dependencies.

This small tool uses Tk to ship useful forms without introducing a Qt build
dependency. The full map/event editor's toolkit remains an architectural choice;
the C player and shared validation do not depend on either GUI toolkit.

```sh
python3 tools/roster_editor.py work/editor-ready
# Or open an example, then use New project to create your own copy:
python3 tools/roster_editor.py examples/adventure-demo
```

If `work/editor-ready` does not exist, first export Updated as described in
[the project guide](M5_AUTHORING_PROJECTS.md#create-validate-and-play), or omit
the editor's project argument and use Open/New project. New project copies
the current project; with no project open it uses the Workshop CHI template.
The source's declared maps/assets and attribution are retained. Saves, caches
and unrelated files are excluded. Existing destination directories are refused.

On Windows, install Python with Tcl/Tk enabled and use:

```powershell
py tools/roster_editor.py work/my-game --validator build-windows/btp-project.exe
```

Select your `btech-port.exe` and original resource/cache paths in **Player
setup**. A native Windows build may use `build/` instead of `build-windows/`.
On Debian/Ubuntu, a Python installation without Tk usually needs the matching
`python3-tk` system package. The C player itself has no Python/Tk requirement.

The editor provides:

- Searchable mech/weapon lists and property forms; mech names, labels, movement,
  mass, price, presentation, armor, structure, actuators, heat sinks and loadout.
- Weapon behavior, damage, projectiles, heat, range and ammunition selection.
- Duplicate/add and delete, with bounded undo/redo. Existing IDs remain stable;
  duplicated definitions receive new IDs automatically.
- Shared C validation of the **whole package**, including references from maps,
  shops and events. Deleting a referenced mech cannot silently break the map.
- Save/reopen and Play using the actual SDL player. Player setup passes all
  four CHI dependency paths explicitly.

Changes are held in memory. Save validates a temporary package before replacing
the definitions file; failed validation preserves the disk file. If any declared
input changed outside the editor, Save asks you to reopen rather than overwriting
that change. A no-change save preserves the original bytes and fingerprint.
Closing an unsaved project offers save/discard/cancel. Undo history is in memory,
not a replacement for version control or backups.

Play saves valid edits and starts a **fresh campaign**, using separate save
slots for each exact edit under `work/roster-editor/play/`. It never loads your
normal campaign automatically. Player launch diagnostics go to
`work/roster-editor/player.log`. `--state-dir DIRECTORY` moves these local editor
files. Existing saves remain bound to the original project snapshot.

For a CHI-campaign project the Starport broker offers the project roster. For
an authored adventure, each shop lists its own stock IDs: adding a mech to the
roster does not automatically add it to every shop. The subsequent game editor
now edits stock, maps and events through forms. Ammo types, rule profiles,
custom art/audio editing and stable-ID migrations remain outside the GUI.

## Map and event authoring contract

Add `"adventure": "adventure.json"` and change the manifest startup to
`"authored-adventure-v1"`. A manifest without an adventure retains
`"chi-training-v1"`. This optional v1 extension preserves existing project
files. The adventure is an explicit package-relative reference subject to the
same path/case/symlink rules as other inputs.

[adventure-v1.schema.json](../schemas/adventure-v1.schema.json) describes the
structure; the C loader is authoritative for semantics. The complete example
is [adventure.json](../examples/adventure-demo/adventure.json).

| Collection | Meaning and bounds |
| --- | --- |
| `tiles` | Up to 64 stable IDs, each with a one-character row key, original tile index 0–249, `chi:land` or `chi:destroyed` sheet, explicit terrain and overhead-map color |
| `maps` | Up to 16 finite rectangular maps, each 16–64 tiles wide/high; display name, world origin, rows, overlays and entrances |
| `overlays` | Up to 32 rectangular patches per map; applied in declaration order, spaces preserve underlying cells; both appearance and terrain come from the chosen tile definition |
| `entrances` | Up to 16 per map; ID, displayed name, approach coordinate and event ID; doorway confirmation is saved explicitly |
| `people` | Up to 16 CHI character templates: existing named identity, three attributes, seven skills, personal weapon and armor |
| `shops` | Up to 16 brokers; explicit ordered set of mech definition IDs; the shared broker still groups and sorts by weight class |
| `encounters` | Up to 16 fixed encounters; map, party spawn and explicit enemies; at most four enemy mechs plus eight enemy people |
| `flags` | Up to 64 named Boolean flags, distinct from original story bytes |
| `events` | Up to 256 named command nodes, with explicit continuation IDs |
| `start` | Map, party position, initial event, credits and up to eight people/four assigned mechs |

Coordinates are deliberately explicit. Map origins and overlay offsets are
**tiles**. Entrance positions, party positions, transfers and combat spawns are
**half tiles**; each tile contains two movement steps per axis. Mech enemy Y is
its ground anchor; a party position is its formation cursor. Map origins need
not align to old CHI sector boundaries. Different map extents must not overlap;
use local overlays for layered scenery. Travel between maps uses transfer
events. There is no implicit procedural wilderness between authored maps.

Terrain can be `clear`, `rough`, `water`, `woods` or `wall`. Shallow water is
traversable with CHI's combat cover/cooling costs. Set terrain to `wall` for an
impassable visual tile, including deep water. Graphics and collision are
independent. The adapter builds a separate CHI rule grid for shared combat
movement, cover and line of sight. Jump follows the existing CHI rule profile.
The renderer uses the visual grid, never the rule tile numbers.

Every formation member is collision checked at each individual half step,
including two/four-step exploration. Map transfers and combat setup check the
whole current formation at the destination; a formation which cannot fit takes
the declared failure branch. Leave generous room around starts and transfers.
The shared follower recovery remains available after scene returns. No random
CHI encounters or town NPC scripts are injected into authored maps.

The initial profile keeps CHI's character identities (`chi:jason`, `chi:rex`,
etc.), named body locations, equipment behavior and four mech bays. Jason is the
first party member. New character naming, arbitrary inventories/skills,
procedural world authoring and freely scripted unit abilities need further
definition boundaries. Declaring them in JSON is not an implementation.

## Event commands and persistence

| `op` | Fields and behavior |
| --- | --- |
| `end` | Return to exploration; if the leader is dead, show game over |
| `say` | `text`, `next`; paginated text with a saved page index |
| `choice` | `text`, 1–5 `{label,next}` options, `cancel`; saved selection; validation rejects text/options that will not fit |
| `if` | `flag`, `value` (0/1), `then`, `else` |
| `flag` | `flag`, `value`, `next` |
| `reward` | `credits`, `next`, `failure`; credit overflow takes failure; a successful payment is recorded once per node |
| `recruit` | `person`, `next`, `failure`; full party/duplicate living identity takes failure; success is recorded once per node |
| `transfer` | `map`, `at`, `next`, `failure`; atomically place the party or leave its existing position intact |
| `shop` | `shop`, `next`; use the shared broker for buying/selling; leaving resumes the node's continuation |
| `battle` | `encounter`, `win`, `loss`, `flee`, `failure`; use shared combat and resume the corresponding branch |

An optional `portrait` names an existing project portrait slot for dialogue.
It is shown when that asset is declared; `none` is the default. Text is printable
ASCII. Dialogue can contain 1,023 characters and is paginated; choices use shorter
text and 24-character labels. Long introductions belong in a preceding `say`.

Events yield only at explicit UI/combat pauses. Immediate commands run with a
64-command budget per input; a non-yielding loop produces a visible fault rather
than hanging the player. Escape returns from the fault to exploration.

Saving captures the current node, phase, selection, page, flags, once-only
receipts, party membership and the existing complete combat state. Effects and
their continuation advance in one logical tick. Loading at a reward message
does not replay the payment, and revisiting a reward/recruit node does not repeat
the effect. Battle damage/ammo/crew changes survive the return. Authored battle
rewards come from event commands; CHI's random looting/salvage/healing epilogue is
not implicitly run. The shared CHI essential-character loss rules still apply.

The strict fingerprint now hashes manifest, definitions, **adventure if present**,
then each declared asset, using the SHA-256 digest of each exact byte snapshot.
Authored continuations use `BTPm` payload v48 inside the existing `BTG1` package
envelope. v47 projects and existing Original/Updated saves remain supported.
Changing maps/events requires restoring their saved snapshot or a new campaign.

The original BLD interpreter remains behind its compatibility adapter. These
new commands are an explicit saved state machine, not an extension of the BLD
bytecode. Lua is not installed or required. A future bounded Lua binding can
issue these commands and save their continuations; it must not expose writable
raw state or serialize a live Lua stack. The independent-assets demonstration
and that binding remain task 4.

## Verification

Completed 2026-10-17, with two-job builds run one platform at a time:

| Check | Result |
| --- | --- |
| Full native CTest | **66/66**, 21.77 s |
| Full Python tools tests | **59/59**, 2.87 s |
| Focused Windows/Wine CTest | **9/9**, 36.25 s |
| Focused ASan/UBSan/LeakSanitizer CTest | **9/9**, 16.39 s |
| Python adventure/editor/project tests using sanitized binaries | **26/26** |
| Linux SDL authored checkpoints | **10/10** |
| Windows/Wine SDL authored checkpoints | **10/10**, same restored state/pixels as Linux |
| Linux Tk editor smoke | **PASS**, including loadout editing and real-player launch |

The nine focused CTest suites cover authored continuations, Updated roster and
combat policy, original content lifetime, combat menus, weapon presentation,
save integrity and original save round trips. The authored continuation suite
also passed on the final Windows and sanitizer builds. Native Windows Tk,
physical Windows audio/drivers and a complete new original-campaign playthrough
were not tested in this increment.

**VERIFIED by project-specific tests:** `authored-adventure-continuations`
plays the depot route, restricted stock, recruitment and repeat visits,
multi-step entrances, allocation, travel, real automated combat, victory,
withdrawal and exactly-once payment. It saves/restores all held pages and
regular combat checkpoints. Python tests cover malformed maps/references,
blocking spawns, overlapped extents, pagination, bounded event loops, corrupt
continuations and exact snapshot binding. Editor document tests exercise real
C validation, undo/redo, atomic saves, external-edit preservation, new projects
and player launch commands.

`python3 tools/native_smoke.py --adventure-only` exercises F5/F9 and identical
headless/SDL states and pixels at ten authored checkpoints. `--editor-only`
exercises real Tk forms, save/reopen, undo/redo, duplication and the Play launch
on a private display. Screenshots are retained in ignored `work/`.

Windows uses the same C loaders/codecs and Python/Tk GUI source. Cross-compiled
player validation is separate from native Windows desktop GUI verification;
do not infer the latter from running Tk on Linux.
