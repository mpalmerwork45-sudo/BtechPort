# Five-task combat and campaign continuation

Authorized together on 2026-10-12. Work is bounded to MAP1 and its next original
training/story step; both supplied reference trees remain immutable.

| Task | Status |
|---|---|
| Complete robot/live-Locust turn comparisons | Implemented and verified against original instructions |
| Original multi-waypoint orders | Implemented; 108 original planning/turn cases pass |
| Persistent fire/smoke behavior | Original flame-marker ring implemented; 128 dice/offset/wrap/terrain cases pass |
| Original combat/jump/impact/destruction effects | Pending |
| Natural Rick/device route and next original assignment/event | Pending |

## Turn research and corrections

The original `12E8:000C` performs up to twelve microsteps, moving active units
in ascending original ID order, then attempting one eligible attack per active
unit. It does not draw a separate randomized initiative roll in these cases.
The existing 35-turn disabled-target comparison is retained; new controlled
**84** complete turns cover all loan choices, movement/heat, 3–6 armed robots and
the live Locust, with positions, facing, heat, complete record fingerprints
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
invented from this visual marker. Further effect-frame verification is pending.

Current internal saves use BTPG/v16, 4096-byte payload / 4112-byte BTS1 file.
The existing combat prefix and legacy migrations are retained; v15 saves have
no fire markers and migrate their old robot cover flags explicitly. Numeric
combat remains independent of graphics. The marker artwork/placement is still
APPROXIMATE until the effects task compares original rendering.

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

## Verification commands

```sh
python3 tools/make_combat_live_turns.py
./scripts/build.sh
ctest --test-dir build --output-on-failure
python3 tools/make_training_combat_replay.py
```

Routine tests use committed numeric fixtures and owner-supplied resources;
fixture regeneration uses the existing ignored RAM capture and optional pinned
Unicorn wheel. Full campaign/timing/pixel parity remains outside these claims.
