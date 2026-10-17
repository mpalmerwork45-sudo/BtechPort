# Vehicles, planet authoring and editor controls — 2026-10-17

This increment adds vehicle/unit authoring to the
[world and graphics editor](M5_WORLD_ART_EDITOR.md). The original and Updated
CHI campaigns keep their existing catalogues and rules. Authored projects opt
into these definitions and maps. Both reference directories remain immutable.

## Editor workflow

Open an authored project with `python3 tools/game_editor.py PATH`.
The roster selector contains **Mechs**, **Vehicles**, **Weapons** and
**Equipment**. **New definition** supplies an editable template, **Duplicate**
copies one, and **Import vehicles** imports selected presets with dependencies.
The current unit has an animated sprite preview; its context menu edits or
selects its sprite. **Choose sprite** is also available in the properties.
Editing an original sprite makes a project-owned copy and changes that unit's
presentation, preserving other units' choices and the source files.

Weapon templates cover the 17 existing CHI weapon behaviors; damage, heat,
projectile count, ranges, ammunition and per-mount loadouts are editable.
Equipment currently supports **heat_sink** and **jump_jet**. Create an equipment
definition, then use the mech's **Installed equipment** dialog to place it.
Heat sinks add cooling and damageable component slots. Jump jets contribute to
the chassis jump rating; set its base jump value to zero when fitting jets.
Individual jet destruction is not yet modelled. Unsupported behaviors fail
validation instead of silently pretending to work.

The map palette supports **Edit pixels**, **Properties** and **Clone**, including
a context menu and double-click editing. Indexed tiles are copied to RGBA and
their logical definition is retargeted atomically, so existing placements update.
Cloned owned tiles get separate images. Palette artwork changes share document
Undo/Redo; the pixel editor also has local stroke/transform history before Apply.
Flip X/Y, clockwise/counterclockwise rotation, one-pixel nudges, optional wrap,
clear and a grid toggle complement pencil, line, rectangle, fill and eyedropper.
Transforms affect one frame or all frames and preserve alpha without resampling.
Rectangular animations require all frames for a 90-degree rotation because
their dimensions are shared. The map hover square blinks without editing;
clicking/dragging paints with the selected tool.

Linux text now uses consistent named Tk fonts and point sizes, with ASCII
toolbar punctuation. On this machine Conda's Tk lacks Xft font rendering, so the
launcher selects the distribution's Python/Tk when available. Install
`python3-tk` and `python3-pil` through the distribution for that setup; no downloads
or installations happen at launch. The local ignored dependency directory also
supports the extracted distribution Tk module. Windows uses its normal Python
Tk and Segoe UI where available. Windows Tk interaction remains unverified.

## Multiple planets and persistence

`btp-adventure-v2` accepts either the earlier singular `world` or a `worlds`
array, never both. Up to 16 worlds share 256 compiled 64x64 sectors (1,048,576
terrain tiles total). Each world is 64–1,024 tiles per dimension in 64-tile
increments, using shared 8x8 jigsaw and tile libraries. All worlds share up to
16 authored local city maps. City origins may repeat on different planets;
overlaps on the same planet and a city assigned to two planets are rejected.

Unplaced local maps remain finite standalone scenes. They consume their own
8x8-tile discovery cells, reducing the shared discovery capacity accordingly.
Jigsaws, explicit tile patches, city maps and city overlays compose in that
order. Collision, rendering, entrances and map reveal read the composed result.
Formation members can touch entrances across a sector boundary before the
cursor crosses it; the saved entry prompt retains the entrance's owning scene.

Travel uses existing `transfer` events referencing a local map. The engine
resolves its planet/sector and validates the destination formation. Transferring
planets clears transient outdoor debris, retains separate discovery regions and
changes the overhead-map name/bounds. The old single-world save discovery layout
is migrated when loading the same package. Package fingerprints remain strict:
editing maps/definitions/graphics requires a fresh test, not automatic save
migration across changed game content. The event save extension is version 2
inside the existing BTPn/v49 payload; original campaign saves remain separate.

## Vehicle representation and limits

Vehicles use `kind: "vehicle"` in the content `mechs` collection for compatibility
with existing shops, party allocation and unit-instance saves. Their movement
declares `tracked`, `wheeled` or `hover`; armour/structure use `front`, `left`,
`right`, `rear`, `turret`. A turretless unit has zero turret armour/structure.
Weapon mounts refer to these facings. Per-unit presentations can use
`source: "package:art"` plus an image ID. The shared catalogue limit is 256 units,
with ten mounts per vehicle. Four owned unit bays remain a runtime limit.

**VERIFIED implementation:** cruise/flank movement, drive-specific terrain
checks over both footprint columns, motive penalties/immobilisation, no jump or
kick, no mech heat, facing damage, destruction and weapon damage, editable
directional sprites, independent inspection, combat, purchases and package saves.
Hovercraft cross water but cannot enter woods; tracked vehicles enter woods;
wheeled vehicles cannot cross woods, rough ground or water. Walls stop all drives.

**APPROXIMATE rules:** facing selection and motive/weapon criticals are a compact
adaptation. Firing arcs, independent turret facing, full crew/engine critical
tables, skidding, flipping and construction legality are future work. Destruction
of any facing's structure destroys the vehicle. Vehicles use the existing
one-pilot/optional-passenger interface. The planner's 12-step path buffer limits
each movement order even when a design has a larger nominal flank allowance.
Some CHI combat presentation text still uses mech terminology; the independent
renderer provides the vehicle's five-facing inspection screen. This is not a
claim that original CHI contained these vehicle rules.

The [catalogue source record](../content/catalogues/vehicles/README.md) separates
Sarna reference facts from provisional armour splits, ammo and authored prices.
The ten original driving sprites and their generator are editable and included.
The [vehicle proving ground](../examples/vehicle-lab/README.md) is an asset-free
two-planet example with a depot, three-unit starting patrol and a live battle.

## Verification

The shared validator and player are the authority for saved projects; JSON
schemas also describe the authoring contract. Tests cover malformed definitions,
terrain, save integrity, catalogue imports, per-unit sprites, equipment, separate
planet discovery, same-coordinate cities, old single-world discovery migration,
large tile/jigsaw libraries and >255 scene handles. GUI tests exercise actual
Tk controls and private-display SDL checks compare saved state and full frames
with the headless player. These are new-feature acceptance checks, not DOS
behavioral equivalence claims. Final results are recorded in [TESTING](TESTING.md).
