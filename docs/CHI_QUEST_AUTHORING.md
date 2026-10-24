# Add quests to an imported CHI campaign

C4.4 adds optional authored quests to either imported edition. Native BLD
scripts, campaign progression, crew, inventory and starting screens still run.
A quest can begin at a native doorway or from an inserted BLD `event` call,
borrow a supported native service, run a new battle, then return to its caller.

## Try the example in the editor

1. Open your imported Original or Updated project in the Construction Kit.
2. Choose **Project → CHI quests**, or **Quests / native doorway bindings** in the tree.
   Opening this view enables quest support as one Undoable draft change.
3. Click **Add example quest**, then **Save project**.
4. Play the native campaign. From the initial training-ground position, take
   two steps east and accept entry to the added relay contract marker.
5. The operator offers a patrol, a ComStar share purchase or departure. Arm
   your cadet before attempting the patrol. Winning pays 250 C-bills once;
   retreat permits another attempt. Losing can kill the crew as in normal play.

The recipe uses the first vacant reachable Citadel door slot, at half-coordinate
`[71,25]`, with freshly authored dialogue. It reads native story byte 4 to
distinguish cadets from veterans. Its sound finishes before its film, followed
by a separate authored battlefield. It restores the native location, discovery
and terrain marks afterward. Repeating a completed contract does not pay again.
Adding the example twice is rejected.

**Keep the previous project revision for its existing imported saves.** Enabling
quests or changing their definitions changes the strict content fingerprint.
Normal Original/Updated games, their saves and previously registered imports
are not upgraded automatically. The example is optional, never added on import.

## Edit the quest

The **CHI quests** tab contains its maps, events and definitions. **CHI maps and
world** continues to edit the original 15 native map slots. These are two views
of one project with shared Undo/Redo, validation, Save and recovery. Native map
projection placeholders are never executed as authored quests.

- **Doorway bindings:** give a binding an ID, native map, door slot and quest
  event. Place/activate that door in **CHI maps → Door slots** first. Binding
  changes what that doorway runs; other doors retain their existing BLD.
- **Native service calls:** define a named adapter using a BLD program, entry
  label and return label. The editor lists supported ComStar buy/sell entries.
- **Quest events:** edit text and operation fields, or open **Event graph** to
  inspect/connect branches. Calls show their destination and all return paths.
- **CHI scripts → Insert → event:** choose an authored event and three native
  return labels. A return resumes that label with the BLD's text/menu choices;
  it does not restart the building's entry instructions.

The `start` map, party and credits in `chi-events.json` are schema/editor
defaults. Native startup uses **CHI missions and campaign** settings. **Play**
shows the original logo/title. A quest is entered through its doorway or BLD
call; the quest view intentionally does not simulate a disconnected party with
**Play here**. Native map Play here remains available for positioning a test.

Bindings/calls and event fields have recoverable drafts. Double-clicking a
quest validation problem opens its quest event, map or binding. Saving flushes
pending valid fields; invalid input stays available for correction.

## Operations and bounds

| Operation | Fields and behavior |
|---|---|
| BLD `event` | `event`, `next`, `failure`, `cancel`; the latter three are labels in the calling BLD |
| Authored `call` | `event`, `next`, `failure`, `cancel`; call another quest event and resume a specified event |
| `return` | `result`: `success`, `failure` or `cancel` |
| `end` | Successful return from the current quest call; an existing combat hook still ends only that hook |
| `chi_native` | `call`: adapter ID; `next`, `failure`, `cancel` |
| `chi_if` | `story_index` 0–99, `value` 0–255, `then`, `else`; read native story state explicitly |
| `chi_sound` | `program` 1–18, `next`, `failure`; wait for the native effect |
| `chi_film` | `film` 0–21, `next`, `failure`; play the native/overridden film before continuing |

Existing dialogue, choices, rewards, flags, variables, objectives, battles and
authored repair/rearm/heal/salvage events remain available. Native story bytes
and authored flags are separate namespaces. `finish` is rejected in a bridged
quest; return to the campaign instead. The six new operations are unavailable
in ordinary unbridged projects and inside combat hooks.

The initial native adapters are **ComStar buy and sell shares**, actions 7/8.
They include original company selection, amount entry and receipt. Their return
boundary must follow the original receipt wait (`chi:comstar-02cf` in untouched
sources). The loader validates the intervening instructions and rejects an
early exit, another service owner, story writes or a cycle. It uses resolved
labels, so inserting earlier text can relocate compiled offsets safely.

Native training, arena, theft, recruitment and cache actions still execute
through their existing BLD contexts. They are explicitly rejected as borrowed
quest service adapters. Use authored service events for new repair/healing
facilities, and native service/mission settings to edit the original facilities.

There are four continuation frames, including the root doorway/BLD caller;
up to 64 doorway bindings and 64 adapters. Native doorway bindings use outdoor
maps `chi:map-01` through `chi:map-13`, slots 0–11. The cache interiors and the
four header slots outside native doorway detection cannot be bound. Repeated
active call sites and excess nesting take the declared failure destination.
A tight synchronous call/return loop yields a recoverable fault; Escape takes
the failure return. These limits avoid unbounded interpreter or C-stack recursion.

Borrowed service cancellation is explicit: Escape at the company selector
returns `cancel`; amount entry keeps its original Escape/backspace behavior.
Zero amount returns `cancel`; lack of money/shares returns `failure` after its
native message. A successful purchase returns after its receipt is acknowledged.

## CLI and automated authors

Use an existing private imported project:

```sh
python3 tools/chi_bridge.py --project "work/My CHI campaigns/original" enable
python3 tools/chi_bridge.py --project "work/My CHI campaigns/original" example
python3 tools/chi_bridge.py --project "work/My CHI campaigns/original" list
```

`example` enables support if necessary and groups the doorway, definitions,
events and adapter into one transaction. These commands also work on Updated.
The generated project contains the user's extracted resources and stays private.
The committed recipe contains no original dialogue, map payloads or artwork.

The normal revision-checked authoring API exposes `bridge.enable`,
`bridge.example`, `bridge.binding`, `bridge.call`, `quest.put`, `quest.patch`,
`quest.remove` and `quest.connect`. For example, an operation inside a standard
batch can replace the example's greeting:

```json
{
  "op": "quest.patch",
  "collection": "events",
  "id": "bridge:cadet",
  "changes": {"text": "The operator has a new assignment for your crew."}
}
```

Use scope `quest.events/bridge:cadet`; native bindings use
`bridge.entrances/<id>` and adapters `bridge.native_calls/<id>`. Object/field
protection addresses those same paths. `bridge.example` also changes native
`chi.maps`; enabling support changes manifest and source metadata, so inspect
the complete proposed diff before narrowing its scope.

Queries expose `quest-events`, `quest-maps`, `quest-encounters`,
`bridge-entrances` and `bridge-calls`. Summary includes a separate `native_quests`
section, keeping native map capacity distinct. Source conversion/build owns
`chi_bridge` and `chi_events` sections without merging them into native maps.
See [command schemas](AUTHORING_COMMANDS.md) and [AI authoring](AI_AUTHORING_GUIDE.md).

## Saves, observations and acceptance

Mixed saves use payload v53: the existing 20,480-byte base plus an 8,192-byte
explicit little-endian `CB01` continuation tail inside the strict project
envelope. Ordinary non-bridge saves retain their existing encoding. Caller
locations, script/menu state, parked NPCs, discovery and terrain marks are
bounded and validated against the same content revision. Shared money, crew,
damage and RNG are never rolled back by restoring a stale caller snapshot.

`--bld-trace` records event entry/return and explicit native adapter outcomes;
`--event-trace` includes bridge depth and original doorway context. Coverage
reports distinguish success/failure/cancel and keep native C internals unknown.

The acceptance recipe can be regenerated from a private pair:

```sh
python3 tools/chi_bridge_evidence.py --source "work/My CHI campaigns" \
  --output work/chi-quest-check
python3 tools/chi_bridge_evidence.py --output work/chi-quest-check --windows
python3 tools/native_smoke.py --editor-chi-bridge-only
python3 tools/chi_bridge_evidence.py --source "work/My CHI campaigns" \
  --output work/chi-default-check --defaults
python3 tools/chi_bridge_evidence.py --source "work/My CHI campaigns" \
  --output work/chi-default-check --defaults --windows
```

It checks native doorway and BLD calls, partial payments, nested/depth/cycle/
budget paths, cancellation, sequential sound/film, live combat outcomes,
one-time rewards, reentry, rollback after a later native fault and held saves.
Windows verification compares every saved payload, rendered frame and canonical
state after the next input. Full campaign acceptance remains C4.5; final setup,
distribution and reconstruction delivery remain C5. This does not certify every
original DOS screen or undocumented native branch.
