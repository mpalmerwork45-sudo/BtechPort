# Updated CHI roster — 0.1.0

This optional data pack adds three mechs to the original campaign. Select
**Updated BTECH CHI** before the Westwood/Infocom logo, then enter the central
doorway of Starport's unused three-door building, northeast of Mech-It Lube.
Approach local position **54,50** from the south (**54,51**). Its new **'Mech
Broker** counter has Buy, Sell and Leave options and the original mechanic
portrait. Delivery uses the existing parked
mech roster; assign a pilot when leaving through the garage (the original
150 C-bill checkout fee still applies). Four owned bays
remain the limit. A free bay and sufficient money are required; rejected
purchases take no money. The Space menu has its original entries.

The broker buys both original and added models. An intact added mech fetches
half its catalogue price; an intact original mech fetches 100 C-bills per ton.
Armor, structure, component, actuator, engine, gyro and sensor damage reduce
the offer. Installed equipment goes with the mech; its crew stays with you.
The confirmation shows the actual offer and defaults to No. Selling frees
that bay without renumbering the other mechs. These are authored expansion
prices, not an original-game mechanic.

| Model | Tons | Walk/run/jump | Armament | Price | Temporary sprite |
| --- | ---: | --- | --- | ---: | --- |
| Panther PNT-9R | 35 | 4/6/4 | PPC, SRM-4 | 12,000 | Red Stinger |
| Hunchback HBK-4G | 50 | 4/6/0 | AC/20, two medium lasers, small laser | 22,000 | Red Stinger |
| Catapult CPLT-C1 | 65 | 4/6/4 | Two LRM-15s, four medium lasers | 36,000 | Locust |

Eligible random mech opponents outside Starport can also use these definitions,
so the existing salvage rules provide another acquisition path. Eligibility is
capped at the heaviest owned mech plus 15 tons; an eligible spawn has a one-in-four
chance of using the added roster. Training, scripted fights and arena opponents
keep their existing definitions. This is an optional balance experiment, not an
original-game feature. Prices and ammunition costs are authored for this port.

## Sources and adaptation

Thanks to **MegaMek's mm-data contributors** for the structured unit records:

- [Panther PNT-9R](https://github.com/MegaMek/mm-data/blob/main/data/mekfiles/meks/3039u/Panther%20PNT-9R.mtf)
- [Hunchback HBK-4G](https://github.com/MegaMek/mm-data/blob/main/data/mekfiles/meks/3039u/Hunchback%20HBK-4G.mtf)
- [Catapult CPLT-C1](https://github.com/MegaMek/mm-data/blob/main/data/mekfiles/meks/3039u/Catapult%20CPLT-C1.mtf)

Consulted 2026-10-16. The variant mass, movement, armor distribution, weapon
locations, ammunition capacities and total heat sinks inform this adaptation.
The short Hunchback and Catapult display names fit CHI's 15-character field.
CHI represents weapons with one component descriptor, rather than tabletop
critical-slot footprints; heat sinks are placed in the remaining available
component slots. Original CHI firing, damage, heat and movement rules apply.
Quirks and tabletop construction rules are not implemented. The supplied sprite
families are placeholders chosen by the project owner, not new model artwork.

The adapted [roster.json](roster.json) is separately licensed under
**CC BY-NC-SA 4.0**; see [LICENSE.md](LICENSE.md) and the
[upstream license](https://github.com/MegaMek/mm-data/blob/main/LICENSE).
This data pack is separate from the GPL engine. No upstream engine code, unit
art, original CHI art, music or executable is included in it. The original
assets must still be supplied by the person running the game. No endorsement
by MegaMek or the BattleTech rights holders is implied.

See [the roster milestone](../../docs/M5A_ROSTER_SLICE.md) for the runtime
format, save compatibility and verification limits.
