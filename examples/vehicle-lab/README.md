# BattleTech: Vehicle proving ground

A small playable demonstration of editable vehicles and travel between two
authored planets. It uses its own graphics, font and sounds; original CHI files
are not required. This is a test range, not a complete campaign.

From the repository root, after [building the player](../../README.md):

```sh
./build/btech-port --project examples/vehicle-lab --save-file work/vehicle-lab.btp
python3 tools/game_editor.py examples/vehicle-lab
```

On Windows, use `build-windows\btech-port.exe` and `py tools\game_editor.py`.
Use **New project** in the editor to create your own copy before making a game.
Saving edits changes the package fingerprint; start a new playtest after edits.

Your patrol starts with a Patton, Pegasus and Skulker and 200,000 credits. Walk
to the building doorway northwest of the patrol for the depot, which stocks
all ten [catalogue vehicles](../../content/catalogues/vehicles/README.md).
The marked shuttle entrance east of that building takes you to Dustball.
Enter Dustball's range-control building for a battle against a Scorpion and
Vedette; its shuttle returns to New Avalon. The two planets have cities at the
same coordinates and retain separate explored maps.

Arrows/numpad move the formation; Space opens the menu and also selects choices.
Inspect Character offers unit inspection. Show Overhead Map displays the current
planet. F5/F9 save/load the package's separate quick slot. Ctrl+Shift+Esc exits.
The inherited player still has four owned unit bays and eight party positions.

In the editor:

- **Vehicles** selects the roster; **New definition** adds another design.
  **Choose sprite** assigns graphics. Right-click the animated preview for
  **Edit sprite** or **Select sprite**.
- **Maps / events → World / jigsaws** selects New Avalon or Dustball. Paint
  jigsaws or tile patches and place/drag cities. **Create world** adds a planet.
- Select a palette tile and **Edit pixels** to draw it. **Clone** makes an
  independently editable copy. Pixel tools include Flip X/Y, rotations,
  nudging, fill, RGBA transparency, frames and undo/redo.
- Entrances and `transfer` events connect the planets by stable local-map IDs.
  **Play here** starts a fresh isolated test at the chosen location.

Vehicle stats and rules have explicit approximations; see the catalogue guide
before treating them as tabletop record sheets. The original artwork is editable
and GPL-3.0-only, with AI assistance disclosed in the repository documentation.
