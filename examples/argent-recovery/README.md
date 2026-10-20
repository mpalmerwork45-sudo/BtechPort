# BattleTech - Argent Recovery

An AI6a mission example: lead a Phoenix Hawk and Trebuchet to two data caches,
survey the northern relay, then return to the western landing pad. Crossing
the southern pad abandons the contract. The raider patrol is optional;
retreating from its skirmish leaves the extraction mission open.

From the repository root:

```sh
./build/btech-port --project examples/argent-recovery
python3 tools/game_editor.py examples/argent-recovery
```

Original CHI resources and prepared caches must be supplied by the player,
as for Relay Contract. Unit adaptations and attribution come from that
example and travel in `LIBRARY-SOURCES.json`. No original assets are embedded.
This custom mission does not claim original CHI story or full tabletop rules.

The editor's **Region** tool draws trigger rectangles; **Mission state** edits
regions and typed variables. **Objectives / journal** edits objective states.
The event inspector edits `variable`, `objective` and `check` commands.
All coordinates in region rectangles are map tiles, not movement half-tiles.

Reproduce in a new directory with:

```sh
python3 tools/mission_demo.py --output work/my-argent-recovery
```

The generator records its batch in `creation.commands.json`; this applies to
the generator's initialized template revision, not an arbitrary existing game.
Its Lua script only queries state and selects a declared engine continuation.
See [mission lifecycle](../../docs/MISSION_STATE.md) and the scenarios in
`examples/authoring/extraction/` for success, failure, retreat, repeated visits
and checkpoint evidence.
