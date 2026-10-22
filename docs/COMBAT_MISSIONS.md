# Authored combat missions (AI6b / AI6c)

Optional authored-game extensions add timed defence, reserve waves and protected
actors. They do not change the original CHI campaign. The playable example is
[Cairn Passage](../examples/cairn-passage/README.md); its recorded batch and
[nine-run suite](../examples/authoring/cairn/suite.json) exercise the native player.

## Groups and actors

`combat_groups` names groups belonging to one encounter. Each has `id`, `name`,
`encounter`, `affiliation` (`hostile`, `friendly`, `neutral`), `reserve` (0/1) and
`units`. A unit uses `kind` (`mech` or `person`), `definition`, and `at` in **half
tile coordinates**, like encounter placement. Vehicle definitions use `mech`.
Optional `movement` is `walk` or `run`; optional `waypoints` is an ordered list
of half-tile positions for friendly or neutral actors.

Initial groups deploy with the encounter. Reserve actors occupy stable IDs but
no terrain until a `reinforce` event deploys them. This event has `group`,
`radius` (0..8 half tiles), `next`, and `failure`. Placement searches each unit's
anchor outward by distance, row and column, checking terrain and every living
unit's footprint. The whole wave deploys or nothing changes. Repeated deployment
fails. Authors explicitly retry through a later hook; there is no hidden queue.

Friendly actors target hostiles. Hostiles can target the party, friendly guards
and neutral transports. Neutral actors never fire. Friendly actors without
waypoints use ordinary guard AI; stationary neutral actors can represent a
protected crew/vehicle. Routed actors use the existing combat path planner and
movement budget, aiming at one waypoint per round. Blocked movement waits and
replans; actors never teleport. Tracked, wheeled and hover terrain rules apply.
Arrival does not despawn an actor or make it invulnerable.

Actors are encounter units, not owned vehicles or selectable party members.
Retreat ends the attempt. Starting the encounter again resets groups, routes and
timers. Ordinary persistent variables/objectives remain campaign state.

## Hooks, timers and outcomes

`combat_hooks` entries name `id`, `encounter`, `when`, `event` and `repeat`
(`once` or `always`). Supported triggers:

| Trigger | Additional fields | Boundary |
| --- | --- | --- |
| `start` | none | After deployment, before round one |
| `round_start` | `round`, `every` | Before movement/attack planning |
| `round_end` | `round`, `every` | After combat resolution and cooling |
| `destroyed` | optional `group` | After destruction text, effects and audio |
| `arrival` | required `group` | An actor reaches its final waypoint |

Rounds start at one and measure simulation progress, not real time. `every:0`
fires only on the specified round; positive values repeat at that interval.
Simultaneous notifications queue in declaration order. Repeating destruction
hooks can run once per casualty; use counters/conditions if aggregating them.

Hooks suspend the battle using a saved event continuation. Dialogue, choices,
conditions, flags, rewards, variables, objectives, bounded Lua, reinforcements
and explicit outcomes are supported. `end` resumes combat. Nested battles,
transfers, shops, recruits, services and campaign endings are rejected in hook
routes. Cancel from a script fault takes the battle's loss route.

An encounter defaults to `completion:"eliminate"`. Use `"scripted"` to keep it
running between waves or until a transport arrives. `battle_end` takes
`result:"win"|"loss"|"flee"`, `next`, and `failure`. Effects and pending hooks
drain before resolution; a loss overrides a requested win/flee at the same
boundary. Normal party destruction still loses. A scripted battle without a
reachable outcome can continue indefinitely until the 65,535-round bound, so
authors should supply success, casualty and retreat routes.

Conditions `group_alive`, `group_destroyed`, `group_deployed`, `group_arrived`
take a group `id`, comparison and numeric `value`; deployed is 0/1, the others
are counts. `combat_round` takes comparison/value without an ID. Arrived living
actors count as alive; destruction removes their current arrived count. Results
remain queryable until another encounter starts. Read-only Lua APIs are
`game.combat_round()` and `game.group_count(id, measure)` where measure is
`alive` (default), `destroyed`, `deployed` or `arrived`.

## Editor, automation and persistence

**Regions / mission state → Combat groups / escorts** edits actors and their
routes. **Combat hooks / timers** edits lifecycle hooks; encounter properties
choose scripted/elimination completion. These forms share Save, Undo, recovery,
validation and problem navigation. Waypoints currently use coordinate fields;
there is no drag-to-route actor editor in this milestone.

AI authors use normal `object.put`/`object.patch` on `combat_groups` and
`combat_hooks`, and `reinforce`/`battle_end` event records. Scenarios can assert
group measures and combat rounds, save/reload held hooks, and capture frames.
Hook choices require explicit scenario choices. Static graph analysis includes
hook roots; it does not prove all conditions or waypoint paths are reachable.

Bounds: 16 groups, 32 hooks, 16 waypoints per actor, 12 nonparty units per
encounter **including reserves and ordinary enemies**, and 24 combat slots
including the party and ejected pilots. Event-chain and Lua budgets remain as
documented in [mission state](MISSION_STATE.md).

V1/v2 packages using combat missions write optional state version 51 (`BTPp`).
Its 512-byte versioned continuation occupies previously reserved combat bytes
5600..6111 (absolute offset 9696). State size remains 20,480 bytes; older and
original-game encodings keep their layouts. Saves preserve pending hooks,
one-shot bits, deployment, stable unit identities, actor progress and outcomes.
The project envelope still requires the exact saved content. Revised example
artwork therefore needs a new campaign/save namespace.

Adventure v3 uses state v52 with an explicit presence flag for this same combat
continuation. It supports 64 encounters and 1,024 events while retaining the
group/hook/actor limits above. [Campaign capacity](CAMPAIGN_CAPACITY.md) documents
the format upgrade, save refusal policy and high-encounter verification.

Verification covers declared routes and seeds, not general tactical balance or
unbounded campaign scale. Native Windows Tk remains unverified; Windows runtime
checks use isolated Wine. See [test evidence](TESTING.md).
