# Regions, variables and objectives — AI6a

These optional authored-game features work in adventure schemas 1 and 2.
Existing flag-based games keep their behavior. The original CHI campaign
continues through its existing BLD path.

## Editing and authoring

Use **Maps → Region**, then drag a rectangle. The form names it and selects
enter/leave events. **Mission state** lists regions and typed variables;
**Objectives and journal** edits objective definitions. The event inspector
offers `variable`, `objective` and `check`. These edits share normal
Undo/Redo, draft recovery, Save and Play validation.

The command interface uses `object.put`, `object.patch` and `object.remove`
with collections `regions`, `variables`, `objectives` and `events`. A connected
batch can define the state and its referring events together. Queries list
these collections and remaining runtime capacity.

```json
{
  "variables": [
    {"id":"mission:data","name":"Recovered data","type":"counter","initial":0,"maximum":2},
    {"id":"mission:survey","name":"Relay surveyed","type":"boolean","initial":0}
  ],
  "regions": [
    {"id":"mission:landing","name":"Landing zone","map":"mission:valley",
     "rect":[3,11,3,3],"repeat":"always",
     "enter":"mission:check-extraction","leave":"mission:depart"}
  ],
  "objectives": [
    {"id":"mission:extract","title":"Extract the data",
     "text":"Return both data packets to the landing zone.","initial":"active"}
  ]
}
```

These are fragments: referenced maps and events must also exist.
Names are display text; IDs remain stable.

## Coordinates and region lifecycle

`rect` is **[x, y, width, height] in local map tiles**. Width and height
must be positive and the rectangle must fit its named map. Movement positions
are half-tiles: a rectangle starting at tile `[3,11]` starts at movement
`[6,22]`. Its upper/right boundary is exclusive.

Membership follows the party leader's exploration anchor, not each follower.
Placed town regions retain their local coordinates within their planet.
Crossing sectors on the same planet works; another planet at the same XY is
outside the region. Tactical combat movement uses the saved exploration
return position for region queries and does not trigger exploration crossings.

The runtime checks each committed half-step, including a step accepted after
declining an entrance. A crossing with an event ends the current multi-step
movement action. It cannot skip a narrow trigger in two/four-step mode.
Blocked movement fires nothing.

Leaves dispatch before enters. Within each group, declaration order wins.
Overlapping hooks wait for the current event chain to reach `end`; dialogue,
menus and combat keep their normal waiting behavior. A transfer reconciles
membership at the chain's end: it drops pending entries to regions the party
has already left. Intermediate locations in an uninterrupted transfer chain
are not separate visits.

New-game entry hooks run after the starting event chain reaches `end`.
**Play here** initializes membership without firing starting entries, so a
local preview does not silently collect mission rewards. Leaving/re-entering
still triggers the ordinary hooks.

`repeat: "always"` runs on each crossing, not on every tick spent inside.
`"once"` tracks enter and leave independently. A hook counts as fired when
dispatched, even if its action takes a failure branch. Use a repeatable hook
and explicit conditions when a failed attempt should be retryable. Omitting
`enter` or `leave` means that side has no hook.

## Actions and conditions

```json
{"id":"mission:collect","op":"variable","variable":"mission:data",
 "action":"add","value":1,"once":1,"next":"mission:collected","failure":"mission:full"}
```

Booleans are `0` or `1` and support `set`. Counters are unsigned, bounded by
their declared maximum (1–1,000,000), and support `set`, `add`, `subtract`.
An overflow/underflow changes nothing and follows `failure`. A successful
`once:1` command records its completion; later calls skip mutation and follow
`next`. A failed attempt does not consume the command.

```json
{"id":"mission:complete","op":"objective","objective":"mission:extract",
 "state":"complete","next":"mission:payment","failure":"mission:unavailable"}
```

Explicit objectives start `inactive`, `active`, `complete` or `failed`.
Inactive may become active or terminal; active may become terminal.
Complete/failed are terminal and cannot be restarted or changed to one another.
Repeating the current state succeeds without changing it. Returning a started
objective to inactive fails. Journal text distinguishes completed and failed.

Legacy objectives with `active` and `complete` flag IDs remain supported and
can coexist with explicit objectives. Their state can be queried; change them
through their flags. An `objective` command requires an explicit objective.

```json
{"id":"mission:check-extraction","op":"check","match":"all",
 "conditions":[
   {"kind":"variable","id":"mission:data","compare":"eq","value":2},
   {"kind":"variable","id":"mission:survey","compare":"eq","value":1},
   {"kind":"objective","id":"mission:extract","compare":"eq","value":"active"},
   {"kind":"region","id":"mission:landing","compare":"eq","value":1}
 ],
 "then":"mission:complete","else":"mission:keep-looking"}
```

`match` is `all` or `any`, with 1–8 conditions. Kinds are `flag`, `variable`,
`objective`, `region`. All support `eq`/`ne`; only counters support
`lt`/`le`/`gt`/`ge`. Flags/booleans/regions use 0/1; objectives use a state name.
Unknown IDs, invalid bounds and invalid comparisons are rejected by the
shared C validator.

## Lua, saves and limits

Bounded Lua gains read-only queries:

```lua
local data = game.variable("mission:data")       -- integer counter
local surveyed = game.variable("mission:survey") -- boolean
local state = game.objective("mission:extract")  -- state string
local inside = game.in_region("mission:landing") -- boolean
```

Unknown IDs raise a script error and use the existing failure route.
Mutations remain declared event commands selected through `game.command`.
The existing 256 KiB memory, 10,000-instruction and 64-command synchronous
event-chain bounds remain. Region dispatch shares the event-chain budget;
cyclic transfers or conditions do not bypass it.

Limits are 32 variables, 32 regions, 32 objectives and eight conditions per
check, alongside the existing 256 event nodes. The optional mission payload
uses save version 50 and stores values, objective states, current membership,
fired hooks and pending overlapping hooks. Games without these features keep
their existing encoding. Package identity/fingerprint checks still apply:
this does not migrate saves across changed mission definitions.

## Demonstration and evidence

[Argent Recovery](../examples/argent-recovery/README.md) is a separate,
reproducible extraction mission using two data caches, a relay survey,
repeatable landing-zone visits, abandonment and an optional battle. Its
command batch, bounded Lua query and six ordinary-input scenarios are supplied.
See [verification](TESTING.md#ai6a-mission-state-and-editor-repairs--2026-10-20).

Static analysis includes region hooks as declared roots. It does **not** prove
condition/Lua reachability or world-wide routes. This increment provides no
timers, combat lifecycle hooks, reinforcements or escort actors: AI6b/AI6c remain
separate planned mechanics.
