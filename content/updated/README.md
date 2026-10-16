# Updated CHI roster — 0.2.0

This optional data pack adds **17 mech models/variants** to the original campaign. Select
**Updated BTECH CHI** before the Westwood/Infocom logo, then enter the central
doorway of Starport's unused three-door building, northeast of Mech-It Lube.
Approach local position **54,50** from the south (**54,51**). Its new **'Mech
Broker** counter has Buy, Sell and Leave options and the original mechanic
portrait. Delivery uses the existing parked
mech roster; assign a pilot when leaving through the garage (the original
150 C-bill checkout fee still applies). Four owned bays
remain the limit. A free bay and sufficient money are required; rejected
purchases take no money. The Space menu has its original entries.

**Up/Down scrolls** the catalogue one row at a time. Left/Right jumps eight
entries; Enter or Space selects. Back is the last item, and Backspace returns
to the counter. The footer shows the visible range. Save/load preserves the
highlight and scroll position, including a pending purchase confirmation.

The broker buys both original and added models. An intact added mech fetches
half its catalogue price; an intact original mech fetches 100 C-bills per ton.
Armor, structure, component, actuator, engine, gyro and sensor damage reduce
the offer. Installed equipment goes with the mech; its crew stays with you.
The confirmation shows the actual offer and defaults to No. Selling frees
that bay without renumbering the other mechs. These are authored expansion
prices, not an original-game mechanic.

| Model | Tons | Walk/run/jump | Armament | Price |
| --- | ---: | --- | --- | ---: |
| Panther PNT-9R | 35 | 4/6/4 | PPC, SRM-4 | 12,000 |
| Hunchback HBK-4G | 50 | 4/6/0 | AC/20, two medium lasers, small laser | 22,000 |
| Catapult CPLT-C1 | 65 | 4/6/4 | Two LRM-15s, four medium lasers | 36,000 |
| Centurion CN9-A | 50 | 4/6/0 | AC/10, LRM-10, two medium lasers | 23,000 |
| Trebuchet TBT-5N | 50 | 5/8/0 | Two LRM-15s, three medium lasers | 24,000 |
| Griffin GRF-1N | 55 | 5/8/5 | PPC, LRM-10 | 28,000 |
| Shadow Hawk SHD-2H | 55 | 5/8/3 | AC/5, LRM-5, SRM-2, medium laser | 27,000 |
| Wolverine WVR-6R | 55 | 5/8/5 | AC/5, SRM-6, medium laser | 29,000 |
| Rifleman RFL-3N | 60 | 4/6/0 | Two AC/5s, two large and two medium lasers | 32,000 |
| Thunderbolt TDR-5S | 65 | 4/6/0 | Large laser, three medium lasers, LRM-15, SRM-2, two machine guns | 38,000 |
| Archer ARC-2R | 70 | 4/6/0 | Two LRM-20s, four medium lasers | 42,000 |
| Warhammer WHM-6R | 70 | 4/6/0 | Two PPCs, two medium and two small lasers, SRM-6, two machine guns | 43,000 |
| Marauder MAD-3R | 75 | 4/6/0 | Two PPCs, AC/5, two medium lasers | 46,000 |
| Zeus ZEU-6S | 80 | 4/6/0 | AC/5, LRM-15, large laser, two medium lasers | 50,000 |
| Atlas AS7-D | 100 | 3/5/0 | AC/20, LRM-20, SRM-6, four medium lasers | 70,000 |
| Crusader CRD-3R (“CRUSADER 3R LRM”) | 65 | 4/6/0 | Two LRM-15s, two SRM-6s, two medium lasers, two machine guns | 37,000 |
| Crusader CRD-3R (Bear) (“CRUSADER BEAR”) | 65 | 4/6/0 | Four SRM-6s, two medium lasers, two machine guns | 39,000 |

The LRM Crusader is the standard mixed-range CRD-3R, not an LRM-only refit.
Charles Bear's documented variant replaces the arm LRMs with SRM-6s and has
18 heat sinks instead of ten. This optional campaign roster does not enforce
historical introduction dates or faction availability.

Catapult and Marauder use the **Locust** sprite for their reverse-jointed legs;
all other additions use the **red Stinger**. These are the owner's temporary
art choices. Inspection also retains the existing shared CHI diagram, with
armor bars scaled to fit even the Atlas's larger capacities.

Eligible random mech opponents outside Starport can also use these definitions,
so the existing salvage rules provide another acquisition path. Eligibility is
capped at the heaviest owned mech plus 15 tons; an eligible spawn has a one-in-four
chance of using the added roster. Training, scripted fights and arena opponents
keep their existing definitions. This is an optional balance experiment, not an
original-game feature. Prices and ammunition costs are authored for this port.

## Existing Updated saves

The first three definitions and their save codes are unchanged. Saves from the
released three-model **0.1.0** pack load automatically in **0.2.0**, including
held broker menus, damage, ammunition, crew and money. No manual conversion is
needed. A subsequent save records the new pack and the v43 scrolling-menu state.

Compatibility is checked by recomputing the saved fingerprint against the
unchanged prefix of the new roster. Editing or removing an existing definition,
changing its ID/code or price, or switching packages still fails explicitly.
This supports appended stock; it is not a general migration for edited mods.
The [archived 0.1.0 pack](versions/0.1.0.json) remains available via `--roster`
for sessions using the exact earlier catalogue. Keep earlier save copies if
you also intend to run the older executable; it cannot read new v43 saves.

## Sources and adaptation

Thanks to **MegaMek's mm-data contributors** for the structured unit records:

- [Panther PNT-9R](https://github.com/MegaMek/mm-data/blob/main/data/mekfiles/meks/3039u/Panther%20PNT-9R.mtf)
- [Hunchback HBK-4G](https://github.com/MegaMek/mm-data/blob/main/data/mekfiles/meks/3039u/Hunchback%20HBK-4G.mtf)
- [Catapult CPLT-C1](https://github.com/MegaMek/mm-data/blob/main/data/mekfiles/meks/3039u/Catapult%20CPLT-C1.mtf)

The fourteen additions use mm-data commit
[`e6f20e1fc2f9d6c74a6e2cdc74778b029ca14811`](https://github.com/MegaMek/mm-data/tree/e6f20e1fc2f9d6c74a6e2cdc74778b029ca14811).
[sources.json](sources.json) records each pinned source URL, SHA-256 and number
of rear-mounted lasers. In particular, the SRM variant comes from
[Crusader CRD-3R (Bear)](https://github.com/MegaMek/mm-data/blob/e6f20e1fc2f9d6c74a6e2cdc74778b029ca14811/data/mekfiles/meks/Force%20Manuals/Mercs/Crusader%20CRD-3R%20%28Bear%29.mtf).
[Sarna's Crusader variants](https://www.sarna.net/wiki/Crusader#Custom_Variants)
provided the initial variant identification; the actual imported statistics
come from the linked unit records.

Consulted 2026-10-16. Variant mass, movement, armor distribution, weapon
locations, ammunition capacities, actuator presence and heat sinks inform this
adaptation. Display names are shortened to fit CHI's 15-character field.
CHI represents weapons with one component descriptor, rather than tabletop
critical-slot footprints; heat sinks are placed in the remaining available
component slots. The new fourteen models retain their source heat-sink
locations. Shared ammo bins are divided among matching weapons while preserving
the total number of salvos: the standard Crusader's 15 SRM salvos become 8+7,
and Bear's 45 become 12+11+11+11. CHI reloads each weapon's bin separately.
Rear-mounted lasers use ordinary CHI targeting; rear-only firing arcs are not
represented by this adapter. Original CHI firing, damage, heat and movement
rules apply. Quirks and tabletop construction rules are not implemented.

The adapted [roster.json](roster.json), archived pack and source manifest are separately licensed under
**CC BY-NC-SA 4.0**; see [LICENSE.md](LICENSE.md) and the
[upstream license](https://github.com/MegaMek/mm-data/blob/main/LICENSE).
This data pack is separate from the GPL engine. No upstream engine code, unit
art, original CHI art, music or executable is included in it. The original
assets must still be supplied by the person running the game. No endorsement
by MegaMek or the BattleTech rights holders is implied.

See [the roster milestone](../../docs/M5A_ROSTER_SLICE.md) for the runtime
format, save compatibility and verification limits.
