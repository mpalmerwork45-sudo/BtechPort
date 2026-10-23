# BtechPort and the BattleTech Construction Kit

The editor and desktop launcher are named **BattleTech Construction Kit**. They
create and edit game packages for the BtechPort player, including maps, events,
artwork and shared Unit and Construction Libraries.

An independent **C11 / SDL2** recreation of **BattleTech: The Crescent Hawk's
Inception** (1988), targeting the DOS **1.03** release.

This project uses **AI-assisted reverse engineering and development**, including
**OpenAI Sol 6.1 and Astra**, with human direction, gameplay reports and review.
AI helps investigate the original executable, interpret observations, implement
the port and build verification tools. AI-generated explanations are checked
against original data and executable behavior; they are not themselves evidence
of fidelity. See [research methods and AI use](docs/AI_AND_PROVENANCE.md).

**The implementation does not use the original game's source code.** It is
independently written from reverse-engineering research, original game data and
observations of the DOS executable. The substantial contributions of other
researchers are credited below.

**Original game assets are not included.** Everyone running the port must supply
the original DOS game files, including `BTECH.EXE`. Local extraction creates
ignored caches from those files; it does not download the game.

## Start the application

**Linux:** double-click `BtechPort.desktop` if present, or run `./BtechPort` once
and choose **Create launch shortcut**. **Windows:** double-click `BtechPort.cmd`
or `BtechPort.pyw` with Python/Tk installed.

The launch window provides **New game**, **Continue quicksave**, **Open editor**,
**Unit Library** and **New project**. Select Original, Updated, a demo or your own
project. **Build application** builds the local executables; **Player setup**
sets the original files if needed. The independent demos run without them.
See the [launcher and Unit Library guide](docs/UNIT_LIBRARY_AND_LAUNCHER.md).

The Construction Kit now includes service-building templates, a connected event
graph and quest journal, saved playtest checkpoints, building stamps, layered
pixel editing, generated jigsaw worlds, named animation actions and individual
infantry sprites. **Project** provides asset reports and explicit save migration.
**Play options → Checkpoints and trace** can verify later missions from a saved
point, with exact-content checks and saved RNG; see [saved journeys](docs/SAVED_JOURNEYS.md).
See the [five milestones](docs/EDITOR_COMPLETION_MILESTONES.md) and
[distribution guide](docs/CONSTRUCTION_KIT_DELIVERY.md). A packaged Linux kit
starts with `ConstructionKit` and includes Python/Tk/Pillow/SDL; a Windows kit
starts with `ConstructionKit.cmd` and can use an installed or supplied Python runtime.
Both packages include a console authoring launcher: `Author` on Linux and
`Author.cmd` on Windows. It exposes the same JSON interface used by external
AI authors, without requiring a model or network connection.

The editor now uses a single tabbed workspace with an explorer, Inspector,
Problems/output, direct unit-to-sprite and entrance-to-event navigation, shared
Undo/Redo and private recovery drafts. Project and library saves have explicit
separate scopes. Validation, imports, exports and playtest preparation run in the
background; Play/Stop manages an isolated test game. See the
[workspace guide](docs/EDITOR_WORKSPACE.md), [implementation stages](docs/EDITOR_USABILITY_PLAN.md)
and [verification results](docs/TESTING.md#editor-workspace-ui5--2026-10-18).
Native Windows editor interaction remains unverified.

Map authoring now includes **Building, Wall and Road designers**, a reusable
**Pattern Library**, terrain cut/copy/paste and tile editing directly from
construction/jigsaw previews. The tile chooser can clone an entire sheet into
editable project tiles. New worlds default to the original **1024 × 1024** size.
Open **Construction tools** in the explorer or use **Project**; see the
[map construction guide](docs/M5_WORLD_ART_EDITOR.md#buildings-walls-and-roads).

**Project → Construction Library** shares building, wall and road definitions
and saved patterns between games, with their tiles, animation frames, editing
layers and source credits. Designers and the project Pattern Library provide
**Save to library**; **Import and edit** opens a shared copy in another game.
AI authors can search and import the same designs before drawing.
See the [Construction Library guide](docs/CONSTRUCTION_LIBRARY.md).

Construction designers show complete part coverage, including all four road
T-junction orientations and right-angle turns. The Road designer shows **Turn
N/E, E/S, S/W, W/N** and **T North / East / South / West** previews; right-click
one to choose, clone or edit its tile with the
surrounding road tiles visible. Walls default to zero stories (top tiles only).
Event graph boxes show editable descriptions; **Description** changes an author
note without changing game dialogue. Last Beacon includes descriptions for all
54 events. Click table headings for ascending, descending, then original order;
type the start of a dropdown item to select or complete it.

The shared **Unit Library** currently offers **82 blueprints: 66 mechs, ten
vehicles and six infantry templates**, including [25 additional classic
mechs](content/catalogues/mechs/README.md). Mechs use Locust or red Stinger
animations according to leg type; infantry uses the original animations.
Edit designs and sprites inside the library, import selected
designs into games, or export game designs back as updates/variants. Dependencies,
source credits, conflict handling and Undo/Redo accompany imports.

## Status

The game is playable from training through the campaign ending. Exploration,
shops and services, recruitment, mixed infantry/mech combat, the Star League
cache and six save slots are implemented. Original graphics, animations, text
and PC-speaker programs are read from the supplied files.

Fidelity work continues. Original routine comparisons and repeatable gameplay
routes verify specific behavior; they do not establish complete parity. Combat
presentation/timing, wider encounter behavior, some transitions and physical
speaker response still have limits. See [project status](docs/PROJECT_STATUS.md)
and the [weapon/fire presentation audit](docs/WEAPON_PRESENTATION.md) for the
latest evidence. The [mech movement and LRM AI analysis](docs/MECH_MOVEMENT_AND_LRM_AI.md)
records the verified movement calculations and implemented Updated combat rules.

Original/Legacy saves retain v44; Enhanced combat and its settings use v45.
Held broker category menus use v46 in Updated's existing save envelope.
Older saves remain loadable, including held combat effects.
Rebuilding prepares the updated local combat cache from your original files.

The proposed path to more mechs, custom game packages, BLD/Lua scripting and a
Windows/Linux editor is recorded in the
[engine and editor plan](docs/ENGINE_AND_EDITOR_PLAN.md).

The [editable CHI campaign plan](docs/CHI_EDITABLE_CAMPAIGNS_PLAN.md) specifies
five milestones for importing separate Original and Updated campaigns
from a user's original files. It covers editable maps/scripts/services, isolated
saves and keeping original-derived content out of repository and release assets.
C1–C3 and C4.1–C4.2 are implemented: choose **Import CHI** in the launcher to create both local
projects. **Project → CHI maps and world** edits native maps, town placements,
generator inputs, entrances and jigsaws; **CHI resources** edits presentation
art/animation and supported audio settings; **CHI campaign** edits native text.
**Project → CHI scripts** provides C4.1's labelled BLD dialogue/control-flow
editing and lossless compiler. **CHI services** exposes C4.2's prices,
inventories, repair/healing/recruitment settings and named native actions, with
linked price text and saved continuations. See [import instructions](docs/CHI_IMPORT.md),
[BLD authoring](docs/BLD_AUTHORING.md) and [service authoring](docs/CHI_SERVICE_AUTHORING.md).
Mission definitions and new-event continuations remain C4.3–C4.4.

[World-route checks](docs/WORLD_ROUTE_VERIFICATION.md) exercise whole-party
travel between towns and planets, discovery and save/reload, with navigable
editor diagnostics. The independent World Survey fixture needs no original assets.

[AI authoring tools](docs/AI_AUTHORING_GUIDE.md) can inspect projects, search
assets, apply validated command batches, export labelled visual previews, check
mission navigation and run seeded gameplay suites through `python3 tools/author.py`.
The editor's **Project** menu has **Content catalogue**, **Check mission**,
**Changes and protection** and **Local authoring session**, alongside command-file
exchange. Review proposed maps/events, protect human edits, and accept changes
with shared Undo and revision checks. External authors can take snapshots of
the open editor and submit scoped proposals; review is the default.
[World reviews](docs/WORLD_REVIEW.md) add paired planet previews, town navigation
and protected terrain rectangles, including changes to shared jigsaws and art.
[Scenario selection](docs/SCENARIO_SELECTION.md) explains which regression cases
a proposal may affect. In **Changes → Checks**, choose a suite, review the reasons,
and run selected cases or the full suite against the retained candidate.
[Test suite authoring](docs/TEST_SUITE_AUTHORING.md) is available under **Play →
Test suites and coverage**. Create cases and route starters, edit steps and seeds,
import/export CLI suites, and navigate failures and observed event/branch coverage.
Try **Relay Contract (command-created)** in the launcher.
**Cairn Passage (defence / escort)** demonstrates timed defence, reinforcements,
friendly guards and a neutral Skulker convoy, with save/reload and loss routes.
Select it in `./BtechPort` to play or edit it. See the
[demo instructions](examples/cairn-passage/README.md) and
[combat authoring guide](docs/COMBAT_MISSIONS.md).

**Greybank Dispatch (campaign)** combines a depot/service loop, a choice of
Jenner assault or data recovery, timed defence and a vehicle escort. Play or
edit it in the launcher. To generate your own copy, check both branches and
launch it with your configured original resources:

```sh
python3 tools/author.py recipe build \
  --file examples/authoring/greybank/recipe.json \
  --output "work/My Greybank campaign" --check --play
```

The [recipe guide](docs/CAMPAIGN_RECIPES.md) covers parameters, recorded inputs,
diagnostics, source editing and delivery. Generation and gameplay work offline.

**Argent Recovery (regions / objectives)** demonstrates AI6a: named map regions,
typed counters, explicit objective states and compound extraction conditions,
with saved event continuations. The [mission reference](docs/MISSION_STATE.md)
documents the editor controls and lifecycle rules.
For a separate playable discovery/repair demonstration, run
`python3 tools/authoring_demo.py --output work/my-authoring-lab` after preparing
the original resources. It retains previews, exact commands and test reports
beside the new game. The [eight-milestone plan](docs/AI_AUTHORING_PLAN.md) records
the completed boundaries and proposed mission/campaign work. The full manual
editor remains central; generated games run without an AI service.

**Modular campaign sources** are available through **Project → Campaign sources
and build**. Create a separate source copy, edit it normally, and build a playable
package; maps, missions, definitions and dialogue live in separate files.
`python3 tools/author.py source convert PROJECT --output NEW_SOURCE_DIRECTORY`
provides the same workflow for automated authors. See the
[source/build guide](docs/CAMPAIGN_SOURCES.md), including save compatibility and
the reproducible two-planet Cairn example. Existing projects need no conversion.

**Larger campaigns:** the same panel's **Upgrade campaign limits** enables
64 local maps, 64 encounters, 1,024 events and 128 objectives/variables.
This optional v3 format requires runtime 0.2.0 and a new campaign; retain the
old package for its existing saves. AI authors use `campaign.upgrade`.
See [limits and the reproducible 20-contract fixture](docs/CAMPAIGN_CAPACITY.md).

The [shared authoring format and project loader](docs/M5_AUTHORING_PROJECTS.md)
now support editable CHI-dependent projects, up to 256 mech definitions, custom
weapon statistics, explicit portrait assets and separate package-bound saves.
Use `btp-project export` to make an editable copy of Updated, or start with the
[Workshop example](examples/project-demo/README.md). The
[project guide](docs/M5_AUTHORING_PROJECTS.md#create-validate-and-play) gives
export, validation and play commands for both platforms. Original and Updated
remain available as before. [Authored maps and events](docs/M5_MAPS_EVENTS_EDITOR.md)
now support entrances, overlays, shop stock, recruitment, transfers, battles and
saved continuations. Try [Frontier Depot](examples/adventure-demo/README.md).
For a BattleTech adventure, try **[BattleTech: Last Beacon](examples/battletech-demo/README.md)**:
three maps, nine established mech variants and ten vehicles, a Phoenix Hawk/Trebuchet starting
team, two mercenary contracts, a broker, recruitment and two endings. It uses
your supplied CHI graphics/sound and defaults to Enhanced combat:

```sh
sh scripts/play-battletech-demo.sh
python3 tools/game_editor.py examples/battletech-demo
```

See [verification and the next editor milestones](docs/BATTLETECH_DEMO.md).
The [world and graphics editor guide](docs/M5_WORLD_ART_EDITOR.md) covers jigsaws,
multiple planets, city placement, the full tile browser and pixel/animation editing.
Select a tile and **Edit pixels** to draw it; **Clone**, **Flip X/Y**, rotations,
nudging, fill, transparency and undo/redo are available. Roster selections show
animated sprites; right-click to edit or choose one. Mechs, vehicles, weapons
and heat-sink/jump-jet equipment can be created through **New definition**.

Try the new **[Vehicle proving ground](examples/vehicle-lab/README.md)** with
Patton, Rommel, Pegasus, Skulker, Drillson, Galleon, Scorpion, Vedette and the two
missile carriers. It has two planets, a depot and a live battle, with original
editable art and no requirement for CHI files:

```sh
./build/btech-port --project examples/vehicle-lab --save-file work/vehicle-lab.btp
python3 tools/game_editor.py examples/vehicle-lab
```

Use **New project** to work on a copy. **Unit Library → Vehicles → Import into game**
adds selected presets to an authored project. [Vehicle rules and source notes](content/catalogues/vehicles/README.md)
identify approximations; these presets do not replace the original campaign roster.

For clear editor text on Linux, use the distribution's Python with `python3-tk`
and `python3-pil`. The launcher prefers that interpreter when Conda's minimal Tk
is active and the system Tk is available. Windows uses normal Python/Tk.
The [game editor and independent demo](docs/M5_INDEPENDENT_GAME_EDITOR.md)
now add map painting, overlays, entrances/NPCs, encounters, event/choice forms,
roster editing, shared validation, undo/redo, export and Play here:

```sh
./build/btech-port --project examples/beacon-demo --save-file work/beacon-game.btp
python3 tools/game_editor.py examples/beacon-demo
```

[Visual editing](docs/EDITOR_GRAPHICS_AND_DRAGGING.md) now includes real map
graphics, a thumbnail palette, a full tile-sheet picker and marker dragging,
with a cleaner desktop layout. CHI projects use the original game folder from
**Player setup**; **Reload graphics** refreshes the previews.

[Last Beacon](examples/beacon-demo/README.md) is a complete tiny quest with its
own graphics, font, text, sound and a bounded Lua event. It requires **no original
files or caches**. Use New project in the editor to make your own copy. The guide
includes a build without original files and Windows setup. The old roster-editor
launcher remains supported, including `work/editor-ready` for the exported
31-mech CHI roster. Richer script authoring, packaging and construction rules
remain future work; the pixel, frame and world tools described above are usable now.

An ordinary launch first asks **Original BTECH CHI** or **Updated BTECH CHI**,
before the Westwood/Infocom logo. Original is the default. Use arrows and
Enter/Space, or press 1/2. Restart and choose Original whenever you want the
original lineup. `--edition original` or `--edition updated` skips the selector.

Updated adds **31 models**, from the UrbanMech to the 100-ton Atlas, including
Zeus, both Crusader variants, Phoenix Hawk, Shadow Hawk, Dragon, Grasshopper,
Highlander, Rifleman, Stalker, Jenner, Ostsol, Javelin, Cicada, Clint,
Hermes II, Whitworth and Ostroc.
In Starport, enter the central doorway of the unused three-door building
northeast of Mech-It Lube (local position 54,50, approached from the south).
The **'Mech Broker** has a newly generated 1980s anime-style salesman portrait,
a building description and compact **Buy**, **Sell** and **Leave** choices.
Choose **Buy a 'Mech → Light, Medium, Heavy or Assault**. Each class lists
its stock by tonnage, then name. **Up/Down scrolls**; Enter or Space selects.
Back/Backspace returns one menu level. The
[artwork guide](content/updated/art/README.md) includes masters, prompts and
PNG-to-ANM conversion instructions. Updated also adds portraits to the Training
Center, lounge, prison, inventor's hut, cinema, hospital, ComStar, clothes shop,
Video Hut and mayor's house. These
static illustrations preserve the buildings' scripts and original cutscenes.
New models cost 10,000–70,000 C-bills and
are parked outside for crew assignment when you leave through the garage.
The fleet has **four owned bays**. The counter shows occupancy; a fifth purchase
takes no money. Sell an original or added mech to free a bay, retaining its
crew. Offers include installed equipment and fall with damage. Added models
can also appear in eligible outdoor encounters and be salvaged under the
existing rules.
See [roster details and sources](content/updated/README.md).

New Updated games use **Enhanced combat**: mechs choose positions and volleys
from their usable weapons, ammunition and heat. LRM carriers can retreat and
wait for a better shot while moving. LRMs receive an accuracy penalty within
six adapted range units; close shots remain possible, and the targeting panel
shows the penalty. These authored rules apply equally to player and enemy
attacks. The planner runs locally as deterministic C code.

**Existing saves keep Legacy combat**, including Original saves imported into
Updated. Outside a battle, press **Space → Change game settings → Combat rules**
and select **Enhanced** to enable it, or **Legacy** to restore the original rules
and planning. This preserves your party, mechs and progress. Original mode
always retains Legacy combat. See [rules, limits and test results](docs/MECH_MOVEMENT_AND_LRM_AI.md).

Inspection bars scale larger armor/structure totals into the original diagram.
A temporary follower workaround regroups active units after building/battle
exits and closing menus, and recovers units more than six tiles from their
formation position. It applies to both editions and excludes parked/wrecked
mechs. The [implementation and removal TODO](port/core/party.c) distinguish it
from original behavior; the underlying routing still needs improvement.

Updated keeps six separate save slots, starting at
`work/player-save-updated.btp`; Original keeps `work/player-save.btp`.
`--load` recognizes the edition. To continue an existing original save as a
separate Updated campaign, use `--edition updated --load PATH`.
Existing three-, 17- and 23-model Updated saves load automatically with the expanded roster.
The loader verifies that all earlier definitions are unchanged before accepting
appended models. Editing/removing earlier definitions still requires their
matching roster. See [save behavior](docs/M5A_ROSTER_SLICE.md#starting-switching-and-saving).

## Build and run on Linux

You need a C11 compiler (GCC or Clang), CMake 3.16 or newer, Python 3 and SDL2
development files. On Debian, Ubuntu or Kubuntu, these can be installed with:

```sh
sudo apt install build-essential cmake python3 libsdl2-dev
```

1. Place the original DOS 1.03 game files directly in `Original DOS/` in this
   repository. Keep the original uppercase filenames. Use the complete game
   directory, including its executable, maps, scripts, graphics and animations.
   The supported executable is identified in [the file audit](docs/ORIGINAL_FILES.md).
2. From the repository root, build:

   ```sh
   ./scripts/build.sh
   ```

   This prepares the local resource caches in `work/` and builds the SDL2 game
   and headless tools in `build/`. It leaves the original files unchanged.
3. Run from the repository root:

   ```sh
   ./build/btech-port --data "Original DOS"
   ```

No DOS emulator, Godot, .NET or reference checkout is needed to build or play.
Python's standard library suffices for cache preparation. Optional research
and GUI verification tools have separate dependencies described in
[TESTING.md](docs/TESTING.md).

For an incremental rebuild after editing C code:

```sh
cmake --build build -j4
```

If your game files are elsewhere, prepare the three caches with that same path
before configuring and building directly:

```sh
python3 tools/prepare_talk.py --data /path/to/game
python3 tools/prepare_combat.py --data /path/to/game
python3 tools/prepare_world.py --data /path/to/game
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build -j4
./build/btech-port --data /path/to/game
```

The convenience build script and most reference tests expect `Original DOS/`.
The native runtime also supports custom cache paths; see `--help`.

## Windows build and run

A Windows x86-64 executable can be cross-built on Linux with MinGW-w64 and the
[official SDL2 MinGW development archive](https://www.libsdl.org/release/SDL2-devel-2.32.4-mingw.tar.gz).
Install `gcc-mingw-w64-x86-64-posix` using your package manager, then extract the
SDL archive under `local-deps/windows/` and run:

```sh
./scripts/build-windows.sh
```

For SDL2 elsewhere, set `BTP_WINDOWS_SDL2` to its
`x86_64-w64-mingw32/lib/cmake/SDL2` directory. `BTP_WINDOWS_CC` can select a
particular MinGW compiler. The script prepares the same three resource caches
and creates `build-windows/btech-port.exe` with `SDL2.dll` beside it.

On Windows, retain that build directory, the `content` directory for Updated,
your `Original DOS` directory and the
three generated files `work/talk-data.bin`, `work/combat-data.bin` and
`work/world-data.bin` under a common directory. Open a terminal there and run:

```powershell
.\build-windows\btech-port.exe --data "Original DOS"
```

The executable and its input, saves and audio queue are tested under Wine on
Linux. Actual Windows drivers and physical audio hardware remain unverified.
See [Windows verification](docs/M4_PORTABILITY_SWEEP.md#5-windows-build-and-verification).

## Controls

| Key | Action |
| --- | --- |
| Arrow keys | Move or select; hold perpendicular arrows to move diagonally |
| Numeric keypad | Move in eight directions; Num-Lock-off arrows work in menus |
| Enter or Space | Confirm a menu choice or advance dialogue |
| Space during exploration | Open the game menu |
| Escape or Backspace | Back out or decline; Escape does not quit |
| F4 | Toggle the explored overhead map |
| F5 / F9 | Save / load the selected slot |
| F3 | Toggle diagnostics |
| Ctrl + Shift + Escape | Quit |
| Hold Shift, then K, Y, R | Add 10,000 C-bills, including during the intro |

Amount fields accept digits, Backspace and Enter; Space does not submit a number.
Use the Space menu for walking step size, party inspection, equipment, map and
all six save slots. During combat, select a unit, give movement/weapon orders,
and use **Begin Fight** to resolve them. **Computer** assigns the selected unit
without starting a fight; use **Next Mech** to assign others. Space interrupts
automatic play at the end of the current wave and returns to the menu, retaining
the individual assignments. Giving manual movement or weapon orders returns
that unit to manual control.
Space also confirms manual combat commands, movement destinations, weapon and
target choices, and Yes/No prompts.

## Saves and useful options

Native saves default to `work/player-save.btp`; slots two through six add `-2`
through `-6` before `.btp`. They retain held menus and in-progress combat.
Use `--save-file PATH` to change the slot base filename.

```sh
./build/btech-port --load work/player-save.btp
./build/btech-port --mute
./build/btech-port --help
```

Original `GAME*` saves can also be imported:

```sh
./build/btech-port --load "Original DOS/GAME3"
```

All six supplied original saves have byte-for-byte import/export comparisons.
Export requires a previously imported original save and a supported outdoor
state; see [save compatibility](docs/M4_PROGRESS.md). Keep exported files outside
the original reference directory, for example `--export-original work/GAME3`.

## Verification and development

Run the fast headless suite after building:

```sh
ctest --test-dir build --output-on-failure
```

For the broader historical verification workflow, use `./scripts/test.sh`.
GUI tests, sanitizer checks, deterministic replays and optional original-executable
oracles are documented in [TESTING.md](docs/TESTING.md). Tests require your local
game files and generated caches. Native builds and tests do not need DOSBox;
original-game capture tools do.

| Directory | Contents |
| --- | --- |
| `port/core/` | Deterministic game rules and serializable state |
| `port/data/` | Resource and save readers |
| `port/frontend/` | Rendering, SDL2 input/audio and headless entry points |
| `tools/`, `tests/` | Extraction, original comparisons and regression tests |
| `docs/` | Research, evidence, milestones and known gaps |
| `work/`, `build/` | Ignored local caches, captures, saves and build output |

`Original DOS/` and `UnBattletech/` are read-only reference directories, excluded
from this repository. Do not commit proprietary assets, extracted text, original
RAM dumps or screenshots. Findings use **VERIFIED**, **INFERRED**,
**APPROXIMATE** and **UNKNOWN** to make their limits explicit.

## License

BtechPort's independently authored code and documentation are licensed under the
**GNU General Public License, version 3 (GPL-3.0-only)**. See [LICENSE](LICENSE)
for the full terms. Third-party dependencies retain their own licenses.
The optional [Updated roster data](content/updated/README.md) adapts MegaMek
unit records and has a separate **CC BY-NC-SA 4.0** data license. It is not
covered by the engine's GPL license.
The [newly generated building artwork](content/updated/art/README.md) is a separate
contribution under GPL-3.0-only to the extent copyright applies; its AI provenance
and generation prompts are recorded with the assets.

This license does not cover or grant rights to the original game executable,
artwork, music, text or other game assets. The original DOS installation and
extracted runtime caches must be supplied by the person running the port.
The public [Last Beacon baseline](examples/battletech-demo/README.md) uses
placeholders and a local reconstruction recipe for 20 CHI-derived tiles.
Original-derived working copies remain private; 17 historical edited variants
cannot be reproduced by the base-tile recipe. See
[asset handling](docs/CHI_IMPORT.md#original-derived-art-and-sharing).

## Acknowledgements

BtechPort builds on substantial reverse-engineering work by others. Their
research made this recreation possible and deserves explicit credit:

- **[UnBattletech](https://github.com/velteyn/UnBattletech), by Edoardo Barolo
  (`velteyn`) and its contributors, including Maximilien Noal.** Its file-format
  specifications, memory maps, story and engine research, annotated disassembly
  and decompiler output, and extraction tools supplied the main starting point
  for this port's research. We used its BLD round-trip converter for the initial
  audit and its documentation and assembly to locate original routines for
  further verification. UnBattletech is licensed under GPL-3.0.
- **The [Reko](https://github.com/uxmal/reko) and Spice86 contributors.** Their
  decompilation and emulator tooling underpins much of UnBattletech's research
  material consulted here. BtechPort's comparisons use DOSBox and bounded
  execution of original instructions with Unicorn.
- **[w4kfu's unEXEPACK research](https://github.com/w4kfu/unEXEPACK#exepack-header).**
  Its published EXEPACK header description informed this project's independently
  written unpacker and executable-format audit.

This port's independent C implementation and original-game validation extend
that research foundation. Detailed sources and verification limits are recorded
in the [research audit](docs/RESEARCH_AUDIT.md) and milestone evidence reports.
The original game, artwork and story are the work of **Westwood Associates**,
published by **Infocom**.
