# BtechPort

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
The [shared authoring format and project loader](docs/M5_AUTHORING_PROJECTS.md)
now support editable CHI-dependent projects, up to 256 mech definitions, custom
weapon statistics, explicit portrait assets and separate package-bound saves.
Use `btp-project export` to make an editable copy of Updated, or start with the
[Workshop example](examples/project-demo/README.md). The
[project guide](docs/M5_AUTHORING_PROJECTS.md#create-validate-and-play) gives
export, validation and play commands for both platforms. Original and Updated
remain available as before. Authored maps/events, Lua, independent games and the
desktop editor are the next stages.

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
artwork, music, text or other game assets. Those are not distributed here and
must be supplied by the person running the port.

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
