# M2d — MAP1 NPC travel and arrival evidence

Research began 2026-10-11. Implementation and differential checks are in progress.
Both supplied trees remain immutable. Original v1.03 binary/live execution is the
authority; the third-party C reconstruction is only an address-finding aid.

## Verified natural route

Unmodified DOSBox run `1791688646507325853` starts at the usual MAP1 slice position
`0C45:C019`. The player approaches slot 1 near `0C0F:C06D`, moves off the narrow
road, follows it north/east and returns to the Citadel. Slot 1 reaches
`0C45:C014`; its position clears, packed state changes `51` to `12`, and its timer
becomes nonzero. Citadel Talk lists that NPC and shows the original local reply.
No controlled guest-RAM write, resource patch or save import occurs in this run.
The raw captures/RAM are ignored under `work/reference-runs/`.

**VERIFIED:** natural arrival and conversation are feasible. This does not yet
prove native step equality, complete NPC initialization or wall-clock parity.

## Primary addresses and corrections

Offsets below address our independently unpacked, unrelocated image. Common DS
starts at `36DB0`; relocation is resolved separately in live snapshots.

* `0044A..00469`: the main outdoor loop updates NPCs every third animation phase.
  It draws RNG once earlier in each active outdoor loop, even on local MAP1.
* `024C2..02866`: NPC routine; eight slots, ascending order, stride 26.
  `D399 + 26*i` is a stay timer. A nonzero timer decrements; when it reaches zero,
  the NPC reappears at the high-nibble waypoint. That call does not move it.
* `D398 + 26*i`: high nibble is the present/previous waypoint, low three bits the
  next waypoint. It is **not facing**. Direction is a separate byte at `3930+i`.
* `4024+2*i` / `4056+2*i`: current packed X/Y (also unit slots 16..23).
  They are **not a second set of destination coordinates**. Destination words
  live at `D394+26*i` / `D396+26*i`.
* `02582..02650`: movement is gated by the player's aligned 16-half-coordinate
  region, expanded 16 on each side; comparisons are strict. An out-of-region
  traveler freezes. Timers decrement regardless of proximity.
* `0E316..0E5F3` (original `1631:0006`): local step selection, gradual turn toward
  the goal, eight candidate directions, tile threshold and occupancy checks.
  Shared search counter `DS:315A` starts at 100, then reloads 30 and toggles
  `DS:315C` between 0 and 8. Original working-grid sampling depends on cursor
  parity; replacing it with general pathfinding would change behavior.
* `19161..19215` (original `207F:0971`): direction classification using doubled
  axis differences. `193B0..193EA` (`207F:0BC0`): three-byte RNG, shifts/rotates,
  borrow and XOR. The caller also draws RNG in the outdoor loop.
* `027BB..02843`: arrival consumes one RNG byte masked with 31, clears current
  X/Y, shifts the previous low nibble into the high nibble, gets the next index
  from the MAP1 route table, and updates destination words. Zero is a possible
  timer; the port must not invent a minimum stay time.

MAP1 header supplies 16-word waypoint arrays at file offsets 389/421 (the bounded
slice uses the first eight), room mappings at 517 and an eight-byte route table
at **533..540**, loaded to `3768`. Original text/names remain runtime-loaded.

The reference's [world-map notes](../UnBattletech/docs/world-map.md) §18 mislabel
packed nibbles, position aliases and arrival randomness. These corrections are
recorded here without modifying the reference checkout. See the unchanged
[0800](../UnBattletech/reko/segments/UNBTECH_0800.c),
[1631](../UnBattletech/reko/segments/UNBTECH_1631.c) and
[207F](../UnBattletech/reko/segments/UNBTECH_207F.c) address aids.

## Remaining verification

Capture stable outdoor frames and compare numeric NPC positions, destinations,
directions, timers, search state and RNG against the independent C routine.
Exercise arrival, timer expiry, player/NPC blocking, proximity freeze and
building suspension. Preserve the M2c controlled checkpoint separately. Native
cadence, complete startup, outer-world movement and wider campaign remain open.
