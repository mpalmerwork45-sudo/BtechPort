# Unit Library and desktop launcher — 2026-10-18

## Start the application and play

On this checkout, double-click **BtechPort.desktop**. The launcher has **New game**,
**Continue quicksave**, **Open editor**, **Unit Library** and **New project**.
Choose Original, Updated, BattleTech demo, Vehicle proving ground, Independent
demo, or a custom project folder. No command arguments are needed.

The portable entry points are **BtechPort** on Linux and **BtechPort.cmd** or
**BtechPort.pyw** on Windows. They locate their own repository directory.
Linux's **Create launch shortcut** writes `BtechPort.desktop` beside the source
launchers; it can be copied to the desktop. Regenerate it after moving the
checkout, because desktop shortcuts contain an absolute target path. The source
launchers themselves remain portable.

Python 3 with Tk is required; Pillow supplies image import and screenshot tests.
The existing Linux system-Tk preference and optional local Tk extraction also
work when launched directly from a desktop. There is no installation/download
at startup. **Build application** configures CMake and builds the player,
headless player and validator with two jobs. Compiler, CMake and SDL2 development
dependencies must already be installed. Original assets are optional for building.

**Player setup** saves the player/original-folder paths. Missing local dialogue,
combat and world caches are prepared from the chosen audited `BTECH.EXE` when
an original-dependent game starts. Independent demos need no original files.
Failures appear in the launcher; process output is in
`work/roster-editor/player.log`. Original/Updated startup retains the logos.

Launcher games use separate save folders under `work/roster-editor/games`.
Custom projects also get a folder per exact declared-content revision. **Continue
quicksave** loads the first/F5 slot for that version. The other five slots remain
available through the game's Space menu. Attribution-only edits do not change
this namespace or the runtime save fingerprint. New game starts fresh. The
editor's Play action retains its own isolated test slots.

## Shared library workflow

Open **Unit Library** from the launcher or game editor. The default shared folder
is `work/unit-library`; **Library folder** chooses another and persists that
choice. A single library serves multiple game projects.

The first population currently supplies **57 entries**: **41 mechs**, **10
vehicles** and **6 individual infantry/character templates**. This includes all
31 Updated designs, seven symbolic CHI template adaptations and the three
independent demonstration walkers. Existing stable IDs are deduplicated. The
Expanded/CHI numeric catalogues require the prepared local combat cache; the
vehicle and authored example entries are available without it. **Add missing
built-ins** adds newly available entries and preserves every existing edit.

- Filter **All / Mechs / Vehicles / Infantry**, search name/ID/drive type, and
  filter weight class. Units have animated previews and source/dependency notes.
- **Edit unit**, or double-click, opens the existing property editor on that
  library entry. Edit armour, structure, movement, fitted weapons/equipment,
  prices and graphics there. Infantry has attributes, skills, personal weapon,
  armour and shared sprite controls. **Save to library** validates and increments
  its revision. **Play** opens a small preview scene containing that unit.
- **Duplicate variant** creates a separate blueprint with a new stable ID.
  **New unit** creates a mech, tracked/wheeled/hover vehicle or infantry template,
  then opens its editor. Root design creation/deletion happens in the library
  browser; fitted weapon/equipment definitions remain editable in the unit editor.
- **Import into game** copies selected blueprints and required weapons,
  ammunition, installed equipment, sprite presentations and owned images into
  the chosen game. Ctrl/Shift selects several. An import is one shared Undo step.
  Then Save and place units in shop stock, encounters or the starting party.
- Select a design in the game editor and **Export from game** to send its current
  blueprint/dependencies back. An existing entry can be updated or saved as a
  separate variant. Owned damage, crew assignments and campaign flags are omitted.
- **Sources** displays source documents, licences and adaptation notes. Imported
  attribution is retained in `LIBRARY-SOURCES.json`, preserved by save/undo,
  New project and Export. It is editor metadata, outside the runtime fingerprint.

Imports offer **Keep existing**, **Replace selected designs** and **Import
variants**. Conflicting shared weapon/equipment/image/presentation definitions
are given fresh destination IDs and their references are remapped. Replacing
one selected design therefore preserves unrelated units' definitions. Game
validation completes before document/history changes. Library edits do not
silently update games that already imported a design.

Infantry currently means an individual character, not a platoon. Imports choose
a free local actor identity; the runtime still has ten actor identities, sixteen
character templates and eight party places. Infantry artwork remains shared
across NPC/enemy roles. **Install shared NPC/enemy infantry artwork** explicitly
opts into replacing those global roles. Per-character sprite assignments remain
future engine work.

## Files, dependencies and bounds

Each entry is a separate `*.unit.json` file using `btp-library-unit-v1`, with a
stable library ID, definition ID, revision, kind, symbolic content, optional
person, RGBA graphics, optional independent presentation and provenance. The
filename is a hash of its library ID. There is no combined compiled-roster cap
on the folder; each game's existing 256 mech/vehicle, weapon and equipment
definition limits still apply. Entry files are bounded at 16 MiB.

Library writes use atomic replacement and detect stale editor revisions. Game
imports and library edits are checked by the same C validator as the player.
Editing uses temporary preview projects, which are discarded on close. Closing
a library or launcher gives open unit editors their normal save/discard/cancel
opportunity.

Independent indexed walker art is converted to owned RGBA when crossing into a
CHI project. CHI sprite references stay external; an independent project rejects
such an import until the entry has a package sprite selected. Editing a decoded
original sprite makes a local copy. A package-graphics badge describes runtime
dependencies and does not grant redistribution rights to copied original art.
The shipped library code and presets add no original proprietary assets to Git.

`btp-project export-original-units NEW_FILE --combat-data FILE` exports seven
cached original chassis as symbolic definitions. Original training Chameleon
structure contains dummy zero/one values; its authored adaptation uses the
minimum structure compatible with its armour. Library prices are 350 credits/ton,
reloads 3 credits/shot, and missing ammo capacity defaults to 20. These are
explicit authoring choices, recorded in each entry's Sources, not new fidelity
claims. Original/Updated campaign rules and records remain unchanged.

## Verification

Fresh verification includes **120 Python tests**, four focused native gameplay
suites, the original-unit exporter built for Windows and validated under Wine,
and the library tests against the sanitized validator. Actual Linux Tk checks
cover built-ins, editing properties/sprites in the library, revisions, multiple
imports, game-to-library export, infantry identities/shared art, Undo/Redo,
save/reopen/export, minimum-window controls and cancelling an unsaved close.
The launcher starts an imported-vehicle game and continues its real F5 save.
The root executable also starts from another directory with a clean system-Python
environment. The existing world/art/sprite workflow remains verified.

Commands and final results are recorded in [TESTING](TESTING.md). Screenshots:
`work/unit-library.png`, `work/btechport-launcher.png`. Native Windows Tk and
Windows file-association/double-click behavior remain unverified; Wine checks
exercise the Windows C validator/exporter, not a Windows Python GUI.
