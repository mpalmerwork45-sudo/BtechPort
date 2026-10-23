# World-route verification

The AI4 world-route extension checks actual travel across jigsaw boundaries,
town overlays and generated 64-tile sectors. Planet changes use normal transfer
events. The game engine, original campaign rules and save formats are unchanged.

## Run an independent example

Build normally, then run from the repository root:

```sh
python3 tools/world_route_demo.py --output work/my-world-survey
```

Use a new output directory. This generates a normal editable **World Survey**
project and runs its journey without original assets. Open its `game` directory
in the Construction Kit, or play it with:

```sh
./build/btech-port --project work/my-world-survey/game
```

The fixture has two 128 × 64 tile planets, a town spanning a sector boundary,
and three mechs, a tracked vehicle and two infantry in one formation. Its town
overrides lake terrain underneath. The journey leaves town, crosses sectors,
uses a shuttle entrance, explores the other planet and returns. Checkpoints
compare the complete serialized state before/after loading, including discovery.
It is a navigation test map using sample artwork, not a new story campaign.

`journey/report.json` contains results, per-step state and route search counts.
`replay.actions` contains only ordinary inputs. Captures and project-digest-keyed
saves are kept alongside it. `--windows` additionally runs the built Windows
scenario tool under the isolated Wine prefix and compares exact save bytes.

## Declare travel and assertions

Use the existing `author.py scenario` and `suite` commands. Each `walk` has
exactly one destination form:

| Destination | Example | Coordinate units |
|---|---|---|
| Entrance, including another town on this planet | `{"op":"walk","entrance":"survey:shuttle"}` | Entrance's source ID |
| Position in a town or detached local map | `{"op":"walk","map":"survey:port","at":[22,12]}` | Local movement half-tiles |
| Position anywhere on the current planet | `{"op":"walk","world":"survey:aster","at":[142,44]}` | World movement half-tiles |

World movement coordinates equal twice the town's tile origin plus its local
movement coordinates. Town origins and map painting use **tiles**. A `map`
destination in a world uses the composed world terrain, so routes may leave
and re-enter the town. A route to a detached map or another planet requires an
ordinary transfer first; the helper never teleports or invents travel events.

```json
{
  "format": "btp-author-scenario-v1",
  "steps": [
    {"op":"walk","world":"survey:aster","at":[142,44]},
    {"op":"assert","world":"survey:aster","world_at":[142,44],"formation":"compact"},
    {"op":"walk","entrance":"survey:shuttle"},
    {"op":"assert","phase":"entry"},
    {"op":"checkpoint"},
    {"op":"enter"},
    {"op":"assert","world":"survey:boreal","world_at":[32,52]},
    {"op":"assert","discovered":{"world":"survey:boreal","at":[16,24],"seen":1}},
    {"op":"checkpoint"}
  ]
}
```

`formation: "compact"` checks actual saved positions of every active infantry
member and owned deployed mech/vehicle, and tests their full collision footprint.
Each planned movement key also checks that the whole formation arrived. Mounted
pilots' unused infantry positions are reported but are not footprint assertions.

Discovery assertions use **world tiles**, with `seen` equal to 0 or 1. They can
check any planet, including one the party has left. Discovery covers 8 × 8 tile
cells; ordinary walking reveals a 3 × 3 neighbourhood of those cells. Reports
include per-planet discovered-cell counts, current world coordinates and source
city/planet locations. The existing `map` assertion still refers to the active
runtime scene; on a world this is a generated sector ID. Prefer `world` and
`world_at` for stable travel assertions.

The planner respects the selected one/two/four-step setting. Exact destinations
must be reachable with that stride and terrain. Other entrances are not silently
declined. Region events that interrupt a route must be handled with explicit
scenario inputs; a destination that itself triggers an event can be asserted
and continued. Splitting a long route into waypoints makes that intent clear.

## Checks, limits and diagnostics

**Project → Check mission** and CLI `lint` now flood each planet from the real
start and all declared transfer arrivals, using the initial whole-party collision
and entrance-contact rules. Town edges, terrain patches and neighbouring sectors
share the same native composition as gameplay. Local maps retain their checks.

Static checks describe potential one-step geometry. They do not prove that every
transfer event can run, model arbitrary Lua/conditions, or predict later party
changes. A door prompt can stop a potential route. Use declared gameplay
scenarios for travel, choices, recruitment and the current movement setting.

| Diagnostic | Meaning |
|---|---|
| `entrance.unreachable` | Exhaustive initial-party geometry search found no contact without another entrance prompt. |
| `navigation.budget` / `navigation.unknown` | World scan incomplete or no declared arrival; reachability is unknown. |
| `route.unreachable` | Exhaustive route search found no path at this step setting without another entrance prompt. |
| `route.budget` | Search budget exhausted; split into waypoints or increase `max_positions`. |
| `route.transfer_required` | Target is on another planet or detached map. |
| `route.interrupted` | An event or changed runtime movement stopped the planned inputs. |

World geometry checks cap each planet at **262,144 reachable positions**. Route
search defaults to **262,144 allocated positions**, configurable per walk up to
**1,048,576**. A* directs searches toward the target; a maximum-size planet's
position index uses 16 MiB, plus the bounded search nodes. Existing scenario
limits of 256 steps, 120,000 input ticks and 45 seconds still apply. Budget
exhaustion is never reported as proof that terrain is unreachable.

Problems with town locations open their source town and select the entrance.
World locations open the correct planet and show a yellow marker which survives
zoom/scrolling. Double-click or press Enter on the problem row. The marker is
editor feedback and is never saved as terrain.

See [verification evidence](TESTING.md#world-route-verification--2026-10-23).
The next proposed extension is starting scenarios from validated saved
checkpoints, so longer campaign tests can reuse proven journeys without
replaying every earlier mission.
