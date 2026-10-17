# Updated CHI roster — 0.3.0

This optional data pack adds **23 mech models/variants** to the original campaign. Select
**Updated BTECH CHI** before the Westwood/Infocom logo, then enter the central
doorway of Starport's unused three-door building, northeast of Mech-It Lube.
Approach local position **54,50** from the south (**54,51**). Its new **'Mech
Broker** counter has Buy, Sell and Leave options, a descriptive introduction,
compact menu rows and a [newly generated broker portrait](art/README.md).
Delivery uses the existing parked
mech roster; assign a pilot when leaving through the garage (the original
150 C-bill checkout fee still applies). Four owned bays
remain the limit. A free bay and sufficient money are required; rejected
purchases take no money. The Space menu has its original entries.

Updated also supplies new static 1980s anime-style portraits for the Training
Center, lounge, prison, inventor's hut, cinema, hospital, ComStar, clothes shop,
Video Hut and mayor's house. Their
[artwork guide](art/README.md) includes masters, exact prompts, native ANM files
and conversion instructions. Original mode retains the original presentation;
the new art does not change scripts, roster identity or save compatibility.

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
| Phoenix Hawk PXH-1 | 45 | 6/9/6 | Large laser, two medium lasers, two machine guns | 25,000 |
| Dragon DRG-1N | 60 | 5/8/0 | AC/5, LRM-10, two medium lasers | 31,000 |
| Grasshopper GHR-5H | 70 | 4/6/4 | Large laser, four medium lasers, LRM-5 | 45,000 |
| Highlander HGN-733 | 90 | 3/5/3 | AC/10, LRM-20, SRM-6, two medium lasers | 62,000 |
| Stalker STK-3F | 85 | 3/5/0 | Two large and four medium lasers, two LRM-10s, two SRM-6s | 57,000 |
| Jenner JR7-D | 35 | 7/11/5 | Four medium lasers, SRM-4 | 15,000 |

The LRM Crusader is the standard mixed-range CRD-3R, not an LRM-only refit.
Charles Bear's documented variant replaces the arm LRMs with SRM-6s and has
18 heat sinks instead of ten. This optional campaign roster does not enforce
historical introduction dates or faction availability.

The six models at the bottom are new in 0.3.0; Shadow Hawk and Rifleman were
already available in 0.2.0. PXH-1 is the conventional Phoenix Hawk, separate
from the original story's Phoenix Hawk LAM. The broker's Jenner also has its
own definition; scripted training Jenners retain their original records.
HGN-733 supplies an AC/10 Highlander compatible with CHI's weapon set; Gauss
rifles are not implemented. The Grasshopper has 22 heat sinks and the Stalker
uses all ten available weapon mounts.

Catapult, Marauder, Stalker and Jenner use the **Locust** sprite;
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

New campaigns now start with **Enhanced combat**. Existing saves and imported
Original games retain **Legacy**. To switch outside combat, use **Space →
Change game settings → Combat rules → Enhanced / Legacy**. Progress and owned
mechs are retained. Both manual and automatic LRM shots use the selected
rules; the target panel shows any close-range accuracy penalty.

The optional adjacent [`combat.json`](combat.json) selects the versioned
`chi-updated-lrm-v1` / `weapon-aware-v1` profile. Its range units are the
original effective shot distance divided by three, rounded down and clamped
to one. Minimum range is six; the close modifier is `max(0, 7 - range)`.
Short/medium/long limits are 7/14/21. This is an authored CHI adaptation.
Other weapon ranges retain the original rules. See the
[implementation and evidence](../../docs/MECH_MOVEMENT_AND_LRM_AI.md).

The bounded loader rejects malformed, duplicate or unknown rule fields. A
pack with no `combat.json` remains Legacy. Enhanced saves bind a semantic
rules fingerprint as well as the roster; loading with missing or changed
required rules fails without replacing the current game. Enhanced states
use BTPj/v45 in a BTU2 envelope. Legacy states keep BTU1/v44, except while
held on one of the new settings pages. These choices share the existing
six Updated slots; no extra save directory is needed.

The first 17 definitions and their save codes are unchanged. Saves from the
released three-model **0.1.0** and 17-model **0.2.0** packs load automatically
in **0.3.0**, including
held broker menus, damage, ammunition, crew and money. No manual conversion is
needed. A subsequent Legacy save records the new pack and v44 state, including the
scrolling menu and the current weapon/fire presentation phase.

Compatibility is checked by recomputing the saved fingerprint against the
unchanged prefix of the new roster. Editing or removing an existing definition,
changing its ID/code or price, or switching packages still fails explicitly.
This supports appended stock; it is not a general migration for edited mods.
The archived [0.1.0 pack](versions/0.1.0.json) and [0.2.0 pack](versions/0.2.0.json)
remain available via `--roster` for sessions using an exact earlier catalogue.
Keep earlier save copies if you intend to return to an older pack/executable;
those cannot read saves with the new catalogue identity. The 0.1.0 executable
also cannot read v43 state. Earlier executables cannot read v44/v45 saves; their
existing saves remain loadable in the current executable.

## Sources and adaptation

Thanks to **MegaMek's mm-data contributors** for the structured unit records:

- [Panther PNT-9R](https://github.com/MegaMek/mm-data/blob/main/data/mekfiles/meks/3039u/Panther%20PNT-9R.mtf)
- [Hunchback HBK-4G](https://github.com/MegaMek/mm-data/blob/main/data/mekfiles/meks/3039u/Hunchback%20HBK-4G.mtf)
- [Catapult CPLT-C1](https://github.com/MegaMek/mm-data/blob/main/data/mekfiles/meks/3039u/Catapult%20CPLT-C1.mtf)

The twenty additions after the initial three use mm-data commit
[`e6f20e1fc2f9d6c74a6e2cdc74778b029ca14811`](https://github.com/MegaMek/mm-data/tree/e6f20e1fc2f9d6c74a6e2cdc74778b029ca14811).
[sources.json](sources.json) records each pinned source URL, SHA-256 and number
of rear-mounted lasers. In particular, the SRM variant comes from
[Crusader CRD-3R (Bear)](https://github.com/MegaMek/mm-data/blob/e6f20e1fc2f9d6c74a6e2cdc74778b029ca14811/data/mekfiles/meks/Force%20Manuals/Mercs/Crusader%20CRD-3R%20%28Bear%29.mtf).
[Sarna's Crusader variants](https://www.sarna.net/wiki/Crusader#Custom_Variants)
provided the initial variant identification; the actual imported statistics
come from the linked unit records.

Consulted 2026-10-16 and 2026-10-17, as recorded for each source. Variant mass,
movement, armor distribution, weapon
locations, ammunition capacities, actuator presence and heat sinks inform this
adaptation. Display names are shortened to fit CHI's 15-character field.
CHI represents weapons with one component descriptor, rather than tabletop
critical-slot footprints; heat sinks are placed in the remaining available
component slots. The twenty later models retain their source heat-sink
locations. Shared ammo bins are divided among matching weapons while preserving
the total number of salvos: the standard Crusader's 15 SRM salvos become 8+7,
and Bear's 45 become 12+11+11+11. CHI reloads each weapon's bin separately.
Rear-mounted lasers use ordinary CHI targeting; rear-only firing arcs are not
represented by this adapter. Original CHI firing, damage, heat and movement
rules apply. Quirks and tabletop construction rules are not implemented.

The adapted [roster.json](roster.json), archived packs and source manifest are separately licensed under
**CC BY-NC-SA 4.0**; see [LICENSE.md](LICENSE.md) and the
[upstream license](https://github.com/MegaMek/mm-data/blob/main/LICENSE).
This data pack is separate from the GPL engine. The new building artwork has its
own [provenance and GPL license notice](art/README.md); it is not adapted from
mm-data. No upstream engine code or artwork, original CHI art, music or
executable is included here. The original
assets must still be supplied by the person running the game. No endorsement
by MegaMek or the BattleTech rights holders is implied.

See [the roster milestone](../../docs/M5A_ROSTER_SLICE.md) for the runtime
format, save compatibility and verification limits.
