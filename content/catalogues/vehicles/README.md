# Editable combat vehicle catalogue

In an authored game project, choose **Import vehicles** in the roster toolbar.
Select the vehicles to import; their weapons, ammunition and original sprite
images come with them. Re-importing preserves existing definitions and artwork.
**Vehicles** in the roster selector shows their movement, five armour facings,
structure and loadout. Right-click the animated preview to edit/select a sprite.

These are playable authoring presets for BtechPort's vehicle adapter. They do
not replace the Original or Updated campaign rosters. Try the
[two-planet proving ground](../../../examples/vehicle-lab/README.md).

## Sources and adaptation

Sarna's contributors provided the reference information below, consulted
2026-10-17. Mass, drive type and principal armament follow the linked standard
design descriptions. Cruise/flank movement points are inferred from their
reported speeds using BattleTech movement conventions. No Sarna prose, artwork,
record-sheet scans or source code was copied into the package.

| Design / source | Tons | Drive | Cruise / flank | Fitted weapons |
| --- | ---: | --- | ---: | --- |
| [Patton](https://www.sarna.net/wiki/Patton) | 65 | Tracked | 4 / 6 | AC/10, LRM-5, small laser, flamer |
| [Rommel](https://www.sarna.net/wiki/Rommel) | 65 | Tracked | 4 / 6 | AC/20, LRM-5, small laser |
| [Pegasus](https://www.sarna.net/wiki/Pegasus_Scout_Hover_Tank) | 35 | Hover | 8 / 12 | Two SRM-6s, medium laser |
| [Skulker](https://www.sarna.net/wiki/Skulker_(Combat_Vehicle)) | 20 | Wheeled | 7 / 11 | Medium laser |
| [Drillson](https://www.sarna.net/wiki/Drillson) | 50 | Hover | 9 / 14 | Large laser, LRM-10, two SRM-2s, two machine guns |
| [Galleon](https://www.sarna.net/wiki/galleon) | 30 | Tracked | 6 / 9 | Medium laser, two small lasers |
| [Scorpion](https://www.sarna.net/wiki/Scorpion_(Combat_Vehicle)) | 25 | Tracked | 4 / 6 | AC/5, machine gun |
| [Vedette](https://www.sarna.net/wiki/Vedette) | 50 | Tracked | 5 / 8 | AC/5, bow machine gun |
| [LRM Carrier](https://www.sarna.net/wiki/LRM_Carrier) | 60 | Tracked | 3 / 5 | Three LRM-20s |
| [SRM Carrier](https://www.sarna.net/wiki/SRM_Carrier) | 60 | Tracked | 3 / 5 | Ten SRM-6s |

**APPROXIMATE:** armour totals are 232/176/104/72/116/56/64/96/48/48 in
table order. The Drillson value is inferred from its ferro-fibrous armour mass;
the last four totals are provisional presets. Facing splits use a front bias;
structure, per-mount ammunition allocation, prices and remaining construction
details are editable adaptation choices, not audited record-sheet reproductions.
No chassis mass/critical-slot construction calculator is provided yet.

The vehicle rules distinguish tracked/wheeled/hover movement, five damage
facings and motive damage. They forbid jumping/kicking, suppress mech heat and
avoid mech limb/gyro destruction. This is an explicitly approximate ruleset:
turret rotation/firing arcs, detailed crew/engine criticals, skid/flip rules and
full tabletop vehicle construction are not implemented. Weapon locations affect
damage/critical handling but do not constrain firing arcs. The existing CHI
planner accepts at most 12 steps per movement order, including the Drillson's
nominal 14-point flank allowance. See the
[implementation limits](../../../docs/M5_VEHICLES_AND_PLANETS.md).

## Artwork and reproducibility

`graphics.json` contains independently drawn 32x32 RGBA sprites. Each has eight
directions (N, NE, E, SE, S, SW, W, NW) with four driving frames per direction.
Tracks, wheels or hover skirts distinguish the drive types; the art is a
starting point for editing, not a claim to match official vehicle illustrations.

The generator and this original artwork were created with AI assistance and
are distributed under this repository's GPL-3.0-only licence. BattleTech design
names remain attributed to their respective owners. Original CHI assets are
not included here.

To regenerate the shipped presets and demonstration (overwrites those files):

```sh
python3 tools/make_vehicle_catalogue.py
python3 tools/make_vehicle_demo.py
```

The graphics generator requires Pillow. Work on a project copy when editing
art or stats you want to keep; regeneration is unnecessary for normal editing.
