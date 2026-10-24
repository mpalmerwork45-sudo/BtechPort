# Drawing worlds and editing jigsaws

Open an imported CHI campaign, choose **Worlds / planets** in the project tree,
or use **World, towns and jigsaws** in its map editor. Older imports offer an
**enable editing** action first. The world is 1,024 by 1,024 terrain tiles;
each jigsaw covers an 8 by 8 block. Edits are ordinary project content and affect
the native game, including movement and water depth.

## Choose the layer you want to draw

| Tool | What it changes |
| --- | --- |
| Terrain / TINYLAND | Paints the world's terrain levels in 8 by 8 blocks. The original generator supplies joining edges and the corresponding miniature graphics. |
| Jigsaw | Places the selected 8 by 8 piece with its chosen level/orientation. Painting a piece replaces previous individual tile patches in that block. |
| Tile | Paints an exact tile above generated terrain and jigsaw placements. Choose from project tiles or all available artwork. |
| Restore generated | Removes terrain, piece and individual tile overrides in the selected blocks, revealing the original generated world again. |
| Pick | Reads the tile, terrain level and explicit jigsaw placement beneath the pointer. |
| Move town | Drags a town on the native 64-tile placement grid. The Citadel and its ruined version move together. |

Use **Brush**, **Line** or **Rectangle**, plus brush size, for broad edits. Tile
brush size is measured in individual tiles; the other painting tools use jigsaw
blocks. Release the mouse to commit one Undoable stroke. Escape cancels an
unfinished stroke. Save writes the changes with the rest of the project.

The **TINYLAND** view displays the actual miniature graphics and palette used
by the game, including joins and towns. **Detailed tiles** shows the resolved
terrain artwork. Switching between these views does not change the world.
Click the small overview to navigate, middle-drag to pan, and use Ctrl + wheel
or the editable zoom dropdown to zoom. The highlighted footprint shows the
brush's size and alignment.

Town maps remain above world terrain. Painting with **Town overlays** enabled
skips town cells; double-click the town to edit its visible map. Hiding the
overlays allows editing the ground beneath them. The **Ruined Citadel** checkbox
changes the inspected story state; it does not advance the campaign.

Right-click a detailed world tile to choose, create, clone or edit its artwork.
Pixel editing shows the eight surrounding resolved tiles, so seams can be
aligned. Editing shared tile artwork changes every use of that definition;
cloning and assigning a new tile makes a local variation.

## Why the old jigsaw display looked wrong

Original CHI jigsaws store terrain-relative selectors. The game combines those
values with a terrain level and orientation before choosing the final tile.
Previously, the editor displayed the selectors directly as ordinary tile IDs.
The overview also used flat colours instead of rendering TINYLAND's glyphs.

The jigsaw editor now previews the actual resolved tiles at the chosen level
and orientation. Original pieces keep their adaptive behaviour until changed.
**Clone** preserves an original piece while making a new variant. **New** creates
an exact-tile piece. Painting an original relative piece converts the visible
result to exact tiles first; **Convert to exact tiles** does that explicitly.
This lets the artwork selected in the tile picker appear as selected in play.
The editor identifies the current mode above the canvas.

Exact pieces can be stamped anywhere using **Jigsaw**. Cloning alone does not
replace the generator's existing joins. **Join bindings** assigns a piece to one
of the original sixteen transition masks or the separate level-16 texture.
Changing a binding affects all generated terrain using that join. **Advanced
generator** retains the original seed/coarse-height/flip-table controls for
users who need them; normal drawing does not require editing those arrays.

Terrain levels 0, 16, 32, 48 and 64 correspond to water/shore, open ground, light
woods, denser woods and rocks/mountains. These are the normal drawing brushes.
The original level-16 texture has special orientation behaviour; the preview
follows the native rules. **TINYLAND art** opens the miniature sheet for pixel
editing with its correct palette; that changes appearance, while the terrain
brush changes geography.

## Independent games and shared designs

Independent projects retain their explicit jigsaw worlds and multiple planets.
Their world editor now also has a navigation overview, jigsaw thumbnails, brush
footprints, middle-button panning and right-click tile editing with neighbours.
Stamping a jigsaw replaces covered fine tile patches rather than leaving them
to conceal the new terrain. Town overlays and per-planet selection remain.

The [shared Construction Library](CONSTRUCTION_LIBRARY.md) now supports direct
editing in an isolated workshop with a persistent test canvas. Use it for tiles,
building/wall/road definitions and saved map patterns. Editing a library entry
does not silently change projects that previously imported it.

## Storage and verification boundaries

Native spatial data adds optional `world.terrain`, `world.placements` and
`world.patches` arrays. Coordinates in the first two are jigsaw blocks; patch
coordinates are tiles. New exact pieces use `mode: "absolute"`; omitted mode
retains original relative semantics. Empty override arrays are omitted again
after restoration. Existing unedited imports retain their content identity.

The limits are 16,384 block positions, 32,768 individual tile patches, 1,024
jigsaw definitions and 4,096 tile definitions. Use reusable pieces for broad
areas. Native CHI still has one planet and fifteen fixed local-map slots;
independent games use their existing multiple-world model. Saves continue to
require their exact project revision; retained revisions remain available in
Saved games.

The advanced data model retains levels 80, 96 and 112 for native compatibility.
The original TINYLAND sheet does not contain a complete glyph family for those
levels, so they are excluded from the ordinary terrain-brush choices. The game
still follows the original miniature indexing rules for advanced raw edits.

All original-derived preview pixels and imported campaign data stay local.
The native preview uses one bounded snapshot for both miniature and detail
views. Per-tile collision, water depth and the game's overhead map read the
same authored overrides. See [testing](TESTING.md) for measured coverage and
platform limits; editor previews are not evidence of every possible gameplay
route through an edited campaign.
