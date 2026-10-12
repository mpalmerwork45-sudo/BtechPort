# Five-task combat and campaign continuation

Authorized together on 2026-10-12. Work is bounded to MAP1 and its next original
training/story step; both supplied reference trees remain immutable.

| Task | Status |
|---|---|
| Complete robot/live-Locust turn comparisons | Implemented and verified against original instructions |
| Original multi-waypoint orders | Implemented; 108 original planning/turn cases pass |
| Persistent fire/smoke behavior | Original flame-marker ring implemented; 128 dice/offset/wrap/terrain cases pass |
| Original combat/jump/impact/destruction effects | Original poses/gaits, impact stars, flame cycle and corpse/wreck artwork integrated |
| Natural Rick/device route and sixth original assignment | Implemented; original five-page dialogue, two Locusts, skill practice and 3,000-cap result |
| Force-field electricity (added by user) | Original ANIMATE.ICN three-frame map cycle integrated; 60 executed decoder/swap comparisons |
| Citadel within the generated surrounding world (added by user) | Nine original generated sectors and exact MAP1 overlay available in the F4 area map; early campaign barriers retained |

## Turn research and corrections

The original `12E8:000C` performs up to twelve microsteps, moving active units
in ascending original ID order, then attempting one eligible attack per active
unit. It does not draw a separate randomized initiative roll in these cases.
The existing 35-turn disabled-target comparison is retained; new controlled
**126** complete turns cover all loan choices, movement/heat, 3–6 armed robots,
one live Locust and two live Locusts, with positions, facing, heat, complete record fingerprints
and final RNG compared. Test prerequisites and the death-UI argument are explicit
in `tools/make_combat_live_turns.py`; no executable instruction is patched.
These comparisons exclude destruction of the player's mech: the original's
pilot evacuation/character-loss branch requires separate campaign state. Native
training defeat/withdrawal and non-advancement remain covered by integration tests.

New original comparisons correct three earlier bounded assumptions:

* `0E31:046F` normalizes robot IDs before `103B:2474`. Robots 16–19 receive
  three points; IDs 20/21 cross its threshold and receive six.
* `32AE` cover flags are 2/4 for people and robots, and 8/16 for mechs.
* `12E8:0F03` removes an arrived waypoint before heat cleanup. If no waypoint
  remains, its movement mode is already 255 during cleanup. This supersedes
  M3b's assumption that movement heat must be retained on arrival.

The live Locust's Kick has a further original call-path quirk: `12E8:02C3`
passes raw unit ID 12 to `0E31:1B44`, although the hip gate uses normalized
record 4. The penalty reads the inactive early-training record 12 and adds six.
The port retains this observed behavior; wider party contexts are not claimed.

## Fire research

An energy/Inferno miss at a covered wooded target invokes `12E8:1E46`.
It rolls 2d6 and, outside 5..9, stores sprite 124 in the original 64-entry
`D457/D497/D4D7/D517` ring through `103B:27C9`. Mech marks use `(x,y-1)`;
person/robot marks use `(x-1,y)`. The ring wraps and survives an encounter.
Refreshing the original viewport after insertion leaves all 576 terrain bytes
unchanged. No terrain-spread, smoke-blocking or extra terrain-damage rule is
invented from this visual marker. Flame artwork and its two-frame cycle are now verified below.

Current internal saves use BTPG/v16, 4096-byte payload / 4112-byte BTS1 file.
The existing combat prefix and legacy migrations are retained; v15 saves have
no fire markers and migrate their old robot cover flags explicitly. Numeric
combat remains independent of graphics. Original artwork is verified by the
earlier 376 RAM crop comparisons; placement/cadence remain approximate.

## Queued movement

The original `32C6` buffer holds twelve `(mode,map,x,y)` waypoints. Planning
spends one turn's point budget across consecutive destinations; `12E8:0F03`
removes arrived entries during resolution. **108 original cases** compare the
complete planned path, final position/heat, movement mode and remaining queue.
Selecting the same mode appends a destination; duplicate destinations do not
add entries. Changing mode offers confirmation and clears the previous route
on Yes. No/Backspace retains it. Queue capacity, the Yes/No popup, cancellation
and saved continuation are tested through the real game core. The route-arrow
preview uses the same complete queue planner as resolution. Popup wording and
destination-box presentation remain approximate; original font/borders are used.

## Combat effects

**161 original comparisons** execute `0000:1732`: 144 finite mech/personal
firing/Kick programs, the three-frame impact program and sixteen directional
gait programs (twelve steps each). BTC2 extracts these programs into the ignored
owner-derived combat cache; no artwork or executable data enters Git. The
original impact frames are **374,375,374**, distinct from flame sprites 124/125.
`0000:2A93` alternates the two visible flame sprites. `12E8:1B7F/1C6E` records
corpse 126 and wreck 128/129 in the persistent mark ring.

The core holds a bounded effect queue and its age, then completes presentation
before the next microstep or victory return. All effects survive F5/F9.
Graphics Yes/No changes visibility while retaining identical numeric simulation;
native timing is approximate and the no-graphics choice does not reproduce the
original's shorter wall-clock animation delay. Pose and hit/star ordering use
original data; beam interpolation/projectile placement and complete frame timing
remain approximate. Jump uses the original directional gait programs: the
verified turn path does not add a separate airborne sprite sequence. Wider
portrait/audio contexts remain deferred. Final-step effects hold the combat
phase until presentation completes; a saved twelfth-step shot has a regression
test, preventing an effect queue from escaping into the command menu.

## Rick and the sixth assignment

`07DC:0D49` adds a second Locust at x+4 for assignment index 5. **144**
construction cases plus nine apprenticeship cases match the original.
**225** bounded executions of `07DC:0C80..0CEE` compare victory, withdrawal and
failure results, both ranks 0..4 and final RNG. Gunnery and kicking receive
independent 0/1 increases even on withdrawal; mastered ranks skip their draw.
The original TRAINING.BLD success raises the cap to 3,000 and advances to index 6.
Later assignments are explicit unsupported contexts.

`ordinary-sixth-story.actions` follows the complete earlier five-mission route,
walks to the lounge after the natural invitation, compares all five Rick text
digests with the original observations, receives the device and continues into
the sixth assignment. It includes four withdrawals with non-advancement,
practice and fresh loans, then defeats both opponents. **43,996** ordinary inputs
and **55** fresh-process continuations pass, without state edits. Every action
also has a C save/restore continuation check. This establishes native playability;
full original campaign timing/RNG and pilot evacuation remain outside the claim.

## Map electricity

The original `0000:320B` loads ANIMATE.ICN and skips its first blank tile.
`0000:240B` cycles three consecutive frames into the ten slots identified by
DS:04B0: 87–91, 105–107, 111 and 113. The renderer now applies those owner-loaded
frames to map tiles, including the force fields. **60** comparisons execute the
original decoder, initialization copy and page swaps in an explicitly supplied
packed-pixel display context. They compare tile IDs and complete crop hashes.
Native cadence uses the saved fixed clock at four ticks per frame; exact DOS
hardware timing and its animation-guard contexts remain approximate. Collision
uses the original tile ID throughout. Rendering, clock continuation and unchanged
collision are covered by the pixel/state tests.

## Verification commands

```sh
python3 tools/make_combat_live_turns.py
./scripts/build.sh
ctest --test-dir build --output-on-failure
python3 tools/make_training_combat_replay.py
python3 tools/make_training_combat_replay.py --campaign
python3 tools/prepare_world.py --fixture tests/fixtures/world-sectors.txt
```

Routine tests use committed numeric fixtures and owner-supplied resources;
fixture regeneration uses the existing ignored RAM capture and optional pinned
Unicorn wheel. Full campaign/timing/pixel parity remains outside these claims.

## Citadel and adjoining generated sectors

The original `187F:104E` expands a coarse 16×16 height grid through `0BFB`;
`187F:1314/13D9` selects and mirrors 8×8 tile patterns. `0000:50D3..50F3`
initializes a 256-byte noise table with the original RNG. This corrects the
secondary claim that a reused 64×64 working buffer establishes a static world.
`tools/prepare_world.py` executes those unmodified routines from the audited EXE,
without a captured RAM dependency, for a stated seed (default 123456).

The ignored BTW1 cache covers sectors 11..13 in both axes: **192×192 tiles**,
origin `(704,704)`, 36,864 generated tiles. Packed MAP1 entrance words place its
64×64 area in sector `(12,12)`; native lookup overlays all **4,096** authentic
local tiles there. Nine complete sector fingerprints are committed, not tiles.
The area map uses original artwork, the saved animation clock, a Citadel outline
and Jason's position. **F4** toggles it; `--world-overview` selects it at launch.
Native F4, movement, F5/F9 and exact continued map pixels pass.

**VERIFIED in scope:** original bounded generation, cache decoding, placement,
complete local overlay and immutable reference assets. **APPROXIMATE:** overview
presentation and the fixed native seed choice. **UNKNOWN/deferred:** independent
C generation of arbitrary sectors, full outer travel/encounters, other town
overlays and later campaign gates. MAP1's entire outer border currently exceeds
the verified early-game gate; tests retain that barrier. No fictional early
escape route is introduced. The C runtime reads generated owner-derived data;
it does not execute the DOS game or depend on the reference recreation.
