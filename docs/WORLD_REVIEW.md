# World review and protected terrain

The Construction Kit can review a proposal across whole planets before applying
it. The **Worlds** page shows the composed terrain, including jigsaws, painted
patches and town maps. Named world regions preserve hand-painted terrain through
generated command batches. Ordinary manual editing, gameplay and saves keep
their existing behavior.

## Editor workflow

1. In **Worlds / planets**, choose **Select**, drag a rectangle, then click
   **Protect selection…**. Name the rule and apply it. Alternatively, open
   **Project → Changes and protection → Protected content**, add a
   `world_region` rule and select a planet and rectangle. Use normal Save to
   persist the policy; Undo can reverse policy edits.
2. Load a proposal with **Load commands…**, or select a proposal submitted
   through the local authoring session. Open **Review changes → Worlds**.
3. Select a planet. Orange outlines indicate changed bounds, yellow outlines
   indicate towns, and cyan outlines indicate protected regions. Terrain counts
   include shared tile properties/art and ground underneath towns.
4. Select a changed town or terrain area, then click **Detail**. You can also
   double-click a location in an overview. Matching before/after crops show
   full tile pixels at that location. **Overview** returns to the whole planet.
   Scrollbars, Ctrl + wheel and editable zoom percentages work on both pictures.
5. **Edit… → Open location in planet editor** opens that location in the current
   editable project. **Open selected town map** opens the source town. These
   actions never apply the proposal. A town or planet that exists only in a
   retained snapshot must be created in the live project before it can be edited.
6. Choose accepted groups in **Summary**, then **Recheck groups**. A protected
   conflict requires a narrower proposal or an explicitly selected named
   exception. **Apply changes** uses the existing validated application path,
   one Undo step and normal Save.

At short window heights, changed locations use a dropdown to leave room for the
paired pictures. Taller views show a table. Detail rendering runs in a worker;
switching proposals or planets cancels the old request, and an old completion
cannot replace the newly selected view.

## What a world-region rule protects

```json
{
  "id": "hand-painted-pond",
  "label": "Keep the pond beside the shuttle port",
  "kind": "world_region",
  "world": "survey:aster",
  "rect": [44, 12, 2, 2]
}
```

Coordinates are **world tiles**, with `[x, y, width, height]` measured from that
planet's origin. A movement coordinate is half a tile; a jigsaw contains 8×8
tiles. The named planet must exist and the rectangle must initially fit inside
it. Removing that planet produces a conflict; lookup never substitutes another
planet.

The rule compares:

- Composed ground: jigsaw tiles followed by painted patches, including ground
  under towns. Changing a shared jigsaw can therefore conflict with a rule even
  when no world object was directly edited.
- Towns that intersect the rectangle: their identity, origin and clipped tile
  layers. Moving a town into or away from protected ground is a conflict.
- Referenced tile properties, owned image frames and timing, and used pixels in
  an independent game's presentation palette. Shared artwork cannot bypass
  protection by keeping the tile ID unchanged.

This protects composed terrain and town layers, not every underlying authoring
choice: a jigsaw change completely hidden by a patch need not conflict. Use
object/field rules to preserve a jigsaw definition itself, a world's name,
entrances, events or other non-terrain data. Manual editing remains available.
Rules constrain supported authoring commands, not arbitrary filesystem writes.

Policies live in `EDITOR.json.authoring_protection`. Generated batches cannot
change them. A named exception permits that application while leaving its rule
in place. Native shape/reference/capacity validation runs before region
composition, so malformed content receives the loader's field diagnostic.

## CLI and retained evidence

```sh
python3 tools/author.py protection work/my-game --file work/pond-rule.json --expected-revision HASH
python3 tools/author.py review prepare work/my-game --request work/revision.json --output work/review-1
python3 tools/author.py review show work/review-1
python3 tools/author.py review world work/review-1 --world survey:aster --rect 40 8 32 32
```

For CHI artwork, pass `--data 'Original DOS'` to preparation/detail rendering.
Missing artwork produces an explicit preview warning; it does not erase the
structural change report or waive protection. The original files remain external
dependencies.

`review.json.world_changes` lists each changed planet's before/after dimensions,
changed tile count, bounded terrain areas and placed/removed/moved/edited towns.
Artifact entries with `kind: "world"` contain the side, world ID, rectangle,
pixels per tile, towns, changed bounds, protected rectangles and image hash.
Standalone SVGs have the same colored annotations as the editor.

The before/after snapshots remain normal inspectable projects, including source
module ownership. Detail crops verify both snapshot revisions and cached image
hashes before reuse. Cancellation and invalid coordinates do not publish a
completed crop index. A stale live project must get a fresh proposal before
application; reviewing old pictures never authorizes overwriting newer edits.

## Bounds and verification

- Whole-planet overviews sample actual **first-frame** tile pixels at 1–4 pixels
  per tile, at most 1024×1024 pixels per side. They are orientation views;
  details show full 16×16 tile pixels. Neither view plays tile animations.
- Changed areas are bounding rectangles grouped by 64×64 sectors; an outline
  can contain unchanged cells. Town movements have explicit before/after bounds.
- The editor requests 32×32 detail crops. The CLI supports up to 64×64, clipped
  against each snapshot's dimensions. At most 64 distinct crops are retained
  per review; existing crops can still be reopened after reaching that limit.
- There are at most 256 protection rules and an aggregate budget of 4,194,304
  world tiles across their rectangles, counting overlaps. Use whole-object
  protection for broader policies. Runtime world/discovery capacities remain
  unchanged; source format size does not increase them.
- A maximum-size planet is composed row by row, rather than expanded into a
  full-resolution planet image. Unchanged planets are skipped when their world,
  town and tile dependencies have not changed.

Reproduce the independent two-planet acceptance journey:

```sh
python3 tools/world_review_demo.py --output work/world-review-example
python3 tools/native_smoke.py --editor-world-review-only
python3 tools/world_review_demo.py --large --output work/world-review-large-example
```

Use new output directories. The first demonstration rejects replacement of a
protected pond, accepts a narrower town/terrain revision, checks Undo/Redo and
Save/reopen, and verifies ordinary party travel before and after editing. Add
`--windows` to compare the Windows runner under isolated Wine with Linux state
and exact save bytes. The large fixture measures review and preservation only;
it does not establish traversal of every tile. See [recorded results](TESTING.md#world-review-and-regional-protection--2026-10-23).
