# Building and pixel tools

**Maps → Buildings → Save selection as stamp** captures the selected tile
rectangle and its entrances/NPCs. **Place building stamp** creates a new overlay
and fresh entrance IDs, retaining their event references. Stamps use symbolic
tile IDs and survive upgrading a project to the wider tile format. They are
stored in `EDITOR.json` and exported with the game. **Layer actions → Move
building and markers** moves a selected overlay and its contained entrances,
NPCs and spawn markers as one undo step.

**Starting formation** shows the collision cells of all starting people and
units under the pointer: green usable, red blocked. Independent games use their
declared formation; CHI-dependent games read the real cached formation through
the shared loader. This preview shows the configured starting party.

**World / jigsaws → Generate** accepts a seed and a weight for each jigsaw
(zero excludes it). Optional edge matching compares the terrain along adjoining
edges. An incompatible selection reports failure without publishing a partial
world. The generated pieces are saved explicitly; the game does not regenerate
them on loading. Cities and local patches retain their placements. The seed and
weights are retained for subsequent editing.

Pixel and sprite editors now provide:

- **Select**, copy/cut and **Paste selection** for rectangular pixel regions.
- **Layers**: up to eight named layers, visibility, ordering and deletion.
  Paint, erase, frame copy/paste and flips act on the selected layer.
- **Selection / canvas → Crop / Resize** crops or pads every animation frame
  and layer consistently. No smoothing is introduced. Map tiles stay 16×16.
- **Export PNG sheet** writes RGBA cells in order, suitable for importing again
  with the same frame dimensions.

Apply stores flattened runtime artwork and editable layers in one shared undo
entry. Library blueprints carry these layers with their owned sprite images.
Layer history is capped by an estimated 32 MiB pixel budget as well as stroke
count. Original assets remain read-only; editing them makes a package copy.

**VERIFIED:** model tests cover alpha composition, selection/paste, crop/pad,
PNG export/reimport, stamps with grouped entrance movement, saved metadata,
deterministic generation and formation cells. Linux Tk checks drawing, layers,
selection, crop/undo, Apply/reopen and the existing direction/frame editor.
Screenshot: `work/construction-kit-pixels.png`.
