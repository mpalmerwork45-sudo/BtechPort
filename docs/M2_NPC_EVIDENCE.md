# M2d — MAP1 NPC travel and arrival evidence

Historical M2d review. [M2e](M2_SHOPS_EVIDENCE.md) extends the pending allowance
schedule below to actual credits and repeated funding in the verified local,
zero-investment context; its BTP6 encoding replaces BTP5. The original frame
fixture and its 570 comparisons remain passing regressions.

[M2f](M2_BANKING_EVIDENCE.md) adds actual investment balances/returns and BTP7.
Its gap-free bank corpus verifies another 459 complete outdoor frame steps,
including all NPC/RNG/economy fields. That trace also corrects the human collision
footprint: primary image `0F9FE..0FA88` compares positions exactly, while the wider
branch at `0FB00..0FB59` applies to other unit slots absent here. The cadet blocks
one half-coordinate rather than its two neighbors. Both corpora pass after the
correction; full party/unit collision remains outside scope. Statements below
describe the historical M2d scope and encoding.

Bounded M2d review, 2026-10-11. Original frame comparisons and the independent
normal-start exploration/conversation replay pass.
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

Final run `1791689346416199589` repeats the natural arrival with a read-only frame
observer. Slot 1 arrives with packed state `12`, timer 27 and position `(0,0)`;
the menu/reply retain timer 26. No supplied NPC-presence flag is used in either
the original run or the native arrival replay. The earlier M2c controlled
checkpoint remains a separate handler regression.

## Primary addresses and corrections

Offsets below address our independently unpacked, unrelocated image. Common DS
starts at `36DB0`; relocation is resolved separately in live snapshots.

* `0044A..00469`: the main outdoor loop updates NPCs every third animation phase.
  It draws RNG once earlier in each active outdoor loop, even on local MAP1.
* `002EE..003D9`: `D323` decrements modulo 256. At old value zero, the allowance/
  account branch can consume three more RNG draws before NPC processing. Its
  comparison uses total assets before the update and the allowance cap from
  `D33F/D340` (`029F5..02A2A`). In this unspent baseline, credits 35, investments
  zero and cap 50 produce one 15-credit allowance and three account draws at
  the first wrap. Later wraps consume no account RNG. Snapshots confirm credits
  50 afterwards; both wrap cases occur in the checked frame corpus.
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
  `DS:315C` between 0 and 8. Working-grid sampling uses candidate parity relative
  to the player, with player parity corrections. Away from edges it samples
  `ceil(candidateX/2), floor(candidateY/2)`. The port preserves the actual 24×24
  grid address arithmetic and candidate order, not a general pathfinder.
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

## Native state and verification

The native slice starts from the recorded initialized MAP1 state: packed NPC
pairs `[99,81,53,99,18,4,4,70]`, all timers zero, RNG `[31,66,171]`, phase 1,
search counter 99, bias zero and loop timer 249. Positions come from each high
waypoint nibble, with slot 4's already completed east step/direction 2. This is
an explicit slice baseline, not a recreation of the whole startup procedure.

`port/core/npc.c` is independently expressed from primary instructions and live
observations. It retains eight-slot update order, strict player-region gating,
gradual direction changes, local tile threshold, blocking by other NPC positions
and the observed player footprint, route transitions and timer expiry. Player
movement precedes NPC movement in the outdoor frame; buildings/entry confirmation
freeze the NPC clock. General player movement against NPCs is still deferred.

The core takes one original outdoor frame per four 32ms logical ticks; NPC steps
occur every third such frame. This **APPROXIMATE** cadence keeps simulation and
replay independent of SDL/wall-clock timing. RNG's single pending allowance event
is serialized for the recorded unspent baseline. It is **not a general economy
implementation**; credits, transactions, investments and other countdowns remain
outside this milestone.

The committed numeric fixture contains **639 original stable observations**.
The C verifier matches **570 complete frame steps**, including two arrivals,
across positions, destinations, directions, packed/timer pairs, phase, loop
timer, RNG and search counter/bias. It explicitly skips **68 gaps** where player
movement occurred between missed observations, then resumes from the next
captured state. It does not invent intermediate player positions. Every checked
frame also verifies identical next-frame behavior after BTP5 encode/decode.
Synthetic regressions cover RNG vectors, both allowance wraps, proximity freeze,
positive/zero-delay arrival, expiry without immediate movement, the recruitment
timer guard, malformed state and BTP4 migration: **1741 total NPC assertions**
including the corpus. This establishes the compared steps, not uninterrupted
global-state equality across gaps.

The default-state native replay reaches slot-1 arrival at tick 2588, enters before
its stay expires and ends at the original 162-byte NPC reply at tick 2612.
**56 original player/story checkpoints** match by non-idle input ordinal. NPC
timers/RNG are compared in the frame corpus rather than equated between route
snapshots with different elapsed time. The verifier reconstructs the menu/reply
directly from original EXE/MAP1 bytes, verifies building suspension and checks
conversation return/exit. The private-X11 smoke feeds the full route through SDL
events and compares its complete final JSON state with headless replay.

```sh
./build/btech-port --replay tests/fixtures/citadel-arrival.actions
python3 tools/verify_m2d.py
python3 tools/reference_session.py --script tools/reference-npc.json
python3 tools/verify_m2d.py --reference-run work/reference-runs/1791689346416199589
```

**VERIFIED in scope:** original initialization snapshot, MAP1 route bytes, the
compared movement/timer/RNG steps and natural conversation/return.
**INFERRED:** extrapolation to unobserved local NPC steps. **APPROXIMATE:** native
cadence, green NPC markers, font/panel and edges. **UNKNOWN/deferred:** full
startup, outer-world travel/wrapping, full party collision, recruitment/world
dialogue, global RNG/economy/day timing, original sprites and wider campaign.
The supplied reference directories remain unchanged; only factual numeric
projections, actions and hashes are committed. Proprietary captures/RAM stay in
ignored `work/`.
