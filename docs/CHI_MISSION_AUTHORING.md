# Edit native CHI missions and campaign settings

C4.3 adds **Project → CHI missions and campaign** to imported Original and
Updated projects. It exposes 837 validated numeric settings and 65 mech roles.
They feed the existing native game loop, combat, renderer and saved
continuations. Default imports retain the corresponding built-in edition's
behavior. These are compatibility campaigns; new unrestricted authored quests
and calls between the two scripting systems belong to C4.4.

## Editing in the Construction Kit

Open your imported project and choose **Project → CHI missions and campaign**,
or **Native missions and campaign** in the project explorer. On an older import,
opening this view enables the document as one Undoable change. New imports
already include it. Existing registered projects are not silently upgraded.

Choose a system in the group dropdown, or search by setting ID/description.
Select a row, enter its value and press **Apply**. **Restore default** restores
the native setting or clears a unit override. **Save** and **Play** collect
pending edits. Invalid edits retain your draft, leave the document unchanged
and give a problem location that returns to the offending field. Undo/Redo,
recovery, source-project builds and headless editing use the same document.

**Keep a copy/revision for existing saves.** Enabling or editing mission content
changes the imported project's strict content identity. Saves require the exact
project revision that created them. Ordinary Original/Updated games and their
save slots are separate and are not modified.

For a simple duel change:

1. Choose **Training 4: duel** and set `training.4.enemy_count` to `2`.
2. Set `training.4.control_prompt` to `1` to offer computer control after the
   startup film/sound. This does not force computer control on.
3. Choose **Unit roles** and set `training.4.enemy.0` and `.1` to the desired
   native templates or project mech IDs.
4. Edit **Building scripts** to change the selection dialogue and success/failure
   branches. Use **Native messages** to edit popup wording, or change the
   mission's `return_message` index.
5. Save, then play the training route. Native combat yields return to the BLD
   instruction after the call, so subsequent story assignments/rewards remain
   editable script content.

Changing a mission does not put a running save into that mission. Use a new game
or a compatible declared test checkpoint. Never label a checkpoint test as a
complete playthrough from the beginning.

## Settings and coordinates

| Group | Editable content | Conventions |
| --- | --- | --- |
| New campaign | Credits, allowance cap, three gameplay RNG bytes, attributes and seven skills | Attributes 2–12; skill order follows the native person record: personal skills 0–2, mech skills 3–4, technician 5, medical 6. These initialize new games only. |
| Training 0–7 | Start, return rectangle, control prompt, enemy AI, skill awards, invasion choice, return text and win/retreat/loss pass policy | Slots remain driving, recovery and six combat assignments. Invasion values: 0 off, 1 random bit, 2 forced. A triggered invasion uses its own enemy count/roles. |
| Combat training | Enemy count/mask, spawn/mask, six formation offsets, shell/infantry switches, infantry weapon range and skill mask | Count + mask cannot exceed six enemies. A shell has its movement/weapons disabled on its copied instance. Infantry roles use native person generation, not mech role records. |
| Unit roles | Three training loans, 36 training opponents, six invasion attackers, three encounter mechs, Rex's stored mech, prison reward, arena loan/11 opponents/spectator/two guards | Empty retains the original template. A role may use an existing mech ID from this project's roster. Vehicles are rejected for these native mech roles. |
| Recognition test | 1–10 rounds, ten answers/marker positions and three message references | Marker coordinates are 320×200 screen pixels; answers index the native 20-part menu. |
| Driving/recovery | Time limit, first-loan allowance, corner/cleared cell, eight recovery locations, rubble tile, rank cap and messages | Recovery locations and cleared cell use map tiles. Pickup text uses the selected index and its following entry for the two loan states. |
| Invasion | Attacker count/roles, six message references, ruin threshold, physical escape band, retained loan and skill awards | Default four Jenners; five successive round messages plus the initial warning. Ruin changes collision and graphics together. Physical escape uses the padded battlefield coordinates, whose town starts at 64. Menu withdrawal remains the native refusal. |
| Encounters | Enable/offer/refusal mask, infantry/mech candidate slots, distance, starport restriction, Updated roster selection, weapon roll table, cash, field/mech salvage, town salvage, expert skill and aftercare | Candidate slots are independent native chance checks, not a guaranteed force size. Setting both counts to zero prevents random forces. Default starport encounters remain infantry-only. |
| Rex/ambush | Rex attributes, skills, weapon and stored mech; player/spawn positions, enemy count/mask, formation, enemy weapons/skill mask | The native person identity/party slot and joining script remain intact. |
| Prison | Entry/exit, four parked mechs' row, guard count/position/weapon range/skill mask and stolen-mech role | Search timing and successful boarding attempt are in CHI services. The reward role, if empty, follows that document's prison reward choice. |
| Arena | Player/opponent/spectator/guard positions and roles, return/escape, rental rolls, armour reductions, damage thresholds and rolls, field layouts | `field_variant`: 0 no fields, 1–3 specific layouts, 4 native random selection. The choice consumes its native RNG draw even when fixed. |
| Cache | Access flag, entry/map-room/return and interaction positions, secret overlay origin/tiles, 33 terminals, 12 doors and requirements, password cells, door art, ending prerequisites/exit | Secret overlay stays 3×6 tiles; door art stays three four-tile frames. Door coordinates must be even half-steps. `quit_at_end=0` holds the completed screen until another key; 1 exits when the final script returns. |

Most movement coordinates are **half tiles**: two movement steps span one tile.
Training starts/returns use the local Citadel; a mech's combat ground point is
two half-steps north of its exploration cursor. Training enemy offsets are added
to the random base spawn. The arena's player/opponent coordinates use its padded
battlefield, whereas `arena.return_x/y` are local Starport coordinates.
`arena.escape_min/max/x` are original-world half-step coordinates, automatically
rebased if Starport moves. Recovery, arena field cells and the cache secret
overlay origin use whole tiles. These coordinate spaces deliberately preserve
native state instead of silently changing units during import.

Cache password entries use the original 0–767 map-room storage order. For raw
index `n`, editor cell coordinates are
`x = (n / 64 % 4) * 8 + n % 8`,
`y = (n / 256) * 8 + n % 64 / 8`, using integer division. Entries must be distinct.
Terminals, interaction tiles and doorway art must be placed consistently in
**CHI maps and world**. A numeric setting alone does not paint the map.

Masks mean **bitwise AND with a native random byte**. For example, mask 3 yields
0–3; mask 2 yields 0 or 2. Default settings preserve RNG consumption. Changing
force counts or generation rules intentionally changes subsequent gameplay.

Native template IDs are `native:loan.0` through `.2`, `native:jenner.0`,
`native:commando.0`, `native:encounter.0` through `.2`, `native:arena.0` through
`.10`, `native:spectator.0` and `native:urbanmech.0`. These resolve the user's
local original templates, including damaged loans. They are not normalized
Unit Library replacements. To use a new model, add it to the project's roster
first, then select its stable ID. Unit definitions determine art/equipment;
mission roles determine where those instances are used.

## CLI and AI authoring

```sh
python3 tools/chi_missions.py --project MY_PROJECT enable
python3 tools/chi_missions.py --project MY_PROJECT list
python3 tools/chi_missions.py --project MY_PROJECT set training.4.enemy_count 2
python3 tools/chi_missions.py --project MY_PROJECT unit training.4.enemy.0 native:jenner.0
python3 tools/chi_missions.py --project MY_PROJECT unit training.4.enemy.0 ""
./build/btp-project chi-missions MY_PROJECT

python3 tools/author.py inspect MY_PROJECT --query objects \
  --collection native-mission-parameters --limit 100
python3 tools/author.py inspect MY_PROJECT --query objects \
  --collection native-mission-units --limit 100
```

The catalogue reports exact IDs, defaults, effective values and bounds. Inspect
returns paged results; use its `next_offset` for the next `--offset`. Shared
batch operations are `missions.enable`, `missions.update` and `missions.unit`:

```json
{"op":"missions.update","parameter":"training.4.enemy_count","value":2}
```

```json
{"op":"missions.unit","role":"training.4.enemy.0","definition":"native:jenner.0"}
```

Scopes/protection paths are `chi.mission_parameters/<parameter>` and
`chi.mission_units/<role>`. Enabling also changes the manifest/document and
requires the corresponding broader scope. Receipts identify changed settings
and roles. The source-project section is `chi_missions`.

BLD/native text accepts `{mission:start.credits}` and optional `:comma` number
formatting. BLD money operands accept a single parameter reference, subject to
their existing unsigned/signed operand limits. This links a fee and its wording
without requiring authors to maintain two different numbers. These references
require mission support to be enabled; unknown names are validation errors.

The manifest field `chi_missions: chi-missions.json` declares
`btp-chi-missions-v1`, schema 1. `parameters` is a flat object of typed integer
keys; optional `units` maps role IDs to native/project IDs or empty strings.
Missing values retain native defaults. Unknown/duplicate keys, booleans, bad
bounds, oversized forces, impossible formation bounds and unresolved roles fail
before play. The [schema](../schemas/chi-missions-v1.schema.json) is generated
from [the catalogue](../tools/make_chi_missions.py). Runtime content, its contract
tag and resolved roster dependencies participate in the strict project digest.

## Coverage and limits

[The coverage ledger](CHI_CAMPAIGN_COVERAGE.md) maps every C1 system to its
source, editing operation, preserved behavior and verification. Native mission,
quiz, combat, NPC, cache and aftermath save checks use the loaded settings.
No serialized state fields or ordinary-game save formats were added.

Compatibility limits remain explicit: eight assignment slots, original native
menu sizes/action contexts, fixed story flag meanings, four active native mech
bays, eight people, 33 cache terminals, 12 doors, seven password cells, three
field layouts and the five-round invasion narrative. Tile classes that dispatch
cache interactions are part of the native map format. Editing artwork does not
change their meaning. New mission kinds, unconstrained state/locations and calls
to authored events are C4.4 work, not hidden fallback behavior.

Validation proves structural bounds, not that an edited map can be won. Check
walking/collision, reachability, source conditions, combat outcomes and saved
continuations for your changes. Native template fidelity and the existing port's
combat mechanics are retained; this milestone is not a new proof of every DOS
branch. See [verification](TESTING.md#native-mission-authoring--2026-10-24).
