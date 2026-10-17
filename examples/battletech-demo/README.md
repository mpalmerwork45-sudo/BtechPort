# BattleTech: Last Beacon

A playable, non-canon BattleTech mercenary contract using BtechPort's original
CHI presentation and Enhanced combat. This is the main BattleTech play demo.
The separate [asset-free Last Beacon](../beacon-demo/) remains an independent
engine/editor template.

## Play

From the repository root, with the normal build and original caches prepared:

```sh
sh scripts/play-battletech-demo.sh
```

The launcher starts a fresh campaign and uses separate project save slots.
F5 saves, F9 loads; the Space menu provides all six slots. To resume the default
first slot immediately:

```sh
sh scripts/play-battletech-demo.sh --load work/battletech-demo-project-battletech-beacon.btp
```

For Windows, or another data location, use explicit paths:

```sh
./build/btech-port --project examples/battletech-demo \
  --data "Original DOS" --dialogue-data work/talk-data.bin \
  --combat-data work/combat-data.bin --world-data work/world-data.bin \
  --save-file work/battletech-demo.btp
```

On Windows substitute your built `btech-port.exe`. See the repository
[README](../../README.md) for building and cache preparation. The project
contains no original DOS assets; these four dependencies must be supplied.
Validation alone needs none of them:

```sh
./build/btp-project validate examples/battletech-demo
```

## Your company and contracts

An invented settlement on the Lyran frontier, 3025. You command Rowan's
**Phoenix Hawk PXH-1** and Mira's **Trebuchet TBT-5N**, with 18,000 C-bills.
The company is ready to fight without buying anything.

1. Accept the opening road contract. You may first read the tactical briefing.
2. Follow the road east from Grayhaven. Challenge the **Javelin JVN-10N** at
   the Quarry Road checkpoint. You can decline the encounter or retreat during
   combat and return later.
3. Return west, then enter the **contract office**, the eastern of the two
   garages north of the main road. Collect 8,000 C-bills.
4. Either finish with the road contract fulfilled, or accept the relay job.
5. For the second job, continue east through Quarry Road to High Ridge. Defeat
   the **Jenner JR7-D** and **UrbanMech UM-R60**, then return to the contract
   office for another 15,000 C-bills and the full ending.

The western garage is the **Mech exchange**, with nine sourced variants grouped
by weight. The stock includes Panther, Javelin, Jenner, UrbanMech, Clint,
Whitworth, Phoenix Hawk, Trebuchet and Griffin. Buy/sell uses the existing
four-bay limit and CHI-scale prices. Cole is recruitable on the road between
the garages. Buy him a machine and use **Space → Allocate People** to assign
him; otherwise he remains infantry until assigned a passenger seat. The
northeastern office is the ComStar liaison, with information about the relay.

Use arrows/numpad or diagonals to move, Space/Enter to select, Escape to cancel,
and Ctrl+Shift+Escape to quit. Space on the map opens the party menu. Inspect
both your people and 'Mechs; F4 shows the overhead map. Enhanced combat is the
default. Computer control is offered before each fight, or issue walk/run/jump,
fire and physical-attack orders manually. LRMs have a minimum-range penalty;
keep the Trebuchet behind the Phoenix Hawk. Space pauses automated execution
for the combat menu.

Damage and ammunition use persist between fights. The demo has no repair,
reload or salvage event yet; save before deploying. Both contracts have been
completed using the supplied two 'Mechs and their initial ammunition. Combat
is the port's adapted CHI/Enhanced rules, not a full tabletop rules simulator.
Original Locust/red-Stinger presentation proxies remain in use for expanded
models; these are not newly drawn model-specific sprites.

## Edit

```sh
python3 tools/game_editor.py examples/battletech-demo
```

Use **New project** to make your own copy. **Maps / events** edits the three
maps, entrances, people, shops, encounters and 54 event nodes. **Player setup**
needs the player and all four original dependency paths. **Play here** starts
with fresh flags; use ordinary Play to test the complete quest. Lua only routes
the contract office to declared commands; rewards and quest flags are saved
by the shared event system.

Project saves bind the exact package snapshot. Editing the shipped package
requires a new campaign; the earlier independent demo and main CHI saves belong
to their own packages. `tools/make_battletech_demo.py` regenerates this example
through the existing Updated exporter and overwrites its scenario files.

See [credits and sources](CREDITS.md), [licensing](LICENSE.md), and the
[verification and next editor milestones](../../docs/BATTLETECH_DEMO.md).
