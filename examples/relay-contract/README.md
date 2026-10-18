# BattleTech — Relay Contract

A separate short demonstration created through the Construction Kit authoring
commands. Your Phoenix Hawk and Trebuchet must clear a Jenner from Greybank's
relay approach and return to the depot for 4,000 credits. A workshop offers
machines and repairs. The contract can be declined or combat abandoned.

Select **Relay Contract (command-created)** in the launcher, or run from the
repository root:

```sh
./build/btech-port --project examples/relay-contract
python3 tools/game_editor.py examples/relay-contract
```

Requires the original CHI resources and prepared caches supplied by the player.
Construction artwork is generated editable art. CHI terrain and actor sprites
are runtime references; unit statistics are existing CHI adaptations, with
source documents retained in `LIBRARY-SOURCES.json`. No new tabletop accuracy
or original-game fidelity claim is made for this custom mission.

The [recorded commands](../authoring/relay-contract.commands.json) recreate the
package, including its editable building footprints and pattern library.
The [scenario](../authoring/relay-contract.scenario.json) checks the full normal
route and saved progression. Follow the [author guide](../../docs/AI_AUTHORING_GUIDE.md)
to reproduce it into a new directory, inspect it, generate a map preview and
run that scenario. Keep your edited copy rather than regenerating over it.

This project is independent of the user's improved Last Beacon maps. Its
`AUTHORING.json` records the creation request for retry detection; it is not a
gameplay asset or part of save compatibility.
