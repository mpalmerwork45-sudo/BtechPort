# Content boundaries and remaining original assumptions

This inventory accompanies [M5 preparation](M5_PREPARATION.md). It distinguishes
the reusable interface from the original adapter behind it. Moving an operation
behind an interface does not make every original format authorable.

## Unit definitions and mutable records (P2)

[unit_data.h](../port/data/unit_data.h) provides named original template families,
weapon-definition views, base movement values, sprite selection and refit
lookup/application. Combat, campaign recruitment/encounters, training, the yard,
services and inspection use these boundaries. Invalid template/weapon indices
are rejected. Template identity is separate from a party slot and from the first
letter of its display name; these enums are internal original-template selectors,
not the public IDs of future authored content.

| Original input | Interpretation | Owner after preparation |
| --- | --- | --- |
| Loan, Jenner, Commando, encounter, arena, spectator and UrbanMech tables | Immutable 125-byte starting templates | `btp_mech_template`; original byte storage remains in `BtpCombatData` |
| Weapon bytes 0–10, 11–16 | Name, damage code, projectile count/flags, heat, packed range, far range, skill | `btp_weapon_definition`; damage flags retain original personal-weapon semantics |
| Mech bytes 49, 50 | Base walk/jump allowance | Named accessors; damage/heat movement rules stay in combat |
| Mech first-byte tag and owner/enemy context | Original sprite-atlas selection | `btp_mech_sprite_base`; preserve different original owned/enemy mappings |
| Mech bytes 123, 124 and eight price entries | Model recipe and upgrade stage | Refit index/price lookup; service still owns credits and eligibility |
| Eight refit mutation recipes | Installed components, ammo, armor and movement changes | `btp_mech_apply_refit`, with exact original writes and copy sources |

Other original offsets remain deliberately explicit inside compatibility code:
armor/current maxima (17–35 and 86–104), actuator masks (36–37/105–106), ammo
(39–48/107–116), critical slots (51–85), pilot/technician (121–122), and saved
record bytes. Future richer instances must not discard unknown bytes used by
original GAME round trips. Catalogue growth does not increase four owned mech
slots, eight party members or 24 combat actors.

## Story commands and continuations (P3)

`core/original_actions.c` owns original BLD native dispatch, named F5 numbers,
checkpoint creation and held native input. It delegates to the original service
modules. `core/script.c` retains bytecode decoding, PCs, condition/money returns
and faults. `core/game.c` owns tick ordering and completion/recovery.

`core/commands.c` exposes only operations with existing callers: active-person
and party-skill queries and checked credit spending. They complete immediately;
BLD/service state owns subsequent text, menu, sound and transaction waits. Do not
call an original F5 number as a future generic event command: building context,
flags and continuation state are required. Recruitment, encounters, inventory
and complex services need additional reusable commands when a second caller is
implemented, rather than speculative replacement during this preparation.

## Persistence ownership (P4)

| State or data | Current owner | Future package boundary |
| --- | --- | --- |
| Resources, immutable templates, decoded graphics/text/sound tables | `data/content.c`, outside `BtpState` | Package loader owns definitions; saves reference stable IDs, never pointers |
| Party records, credits, damage/ammo, world exploration, RNG and flags | `BtpState`; payload in `core/state_codec.c` | Retain simulation instance data separately from definitions |
| BLD PC, checkpoint, service quote, combat plan, menu and selection | Existing state structs and codec | Event runner must serialize pending operations and their arguments, not a Lua coroutine stack |
| Cutscene frame, sound queue/progress, delayed destruction and combat messages | Existing presentation/audio state in codec | Preserve exactly-once continuation and ordered notifications when restoring |
| File envelope, CRC, pending-file replacement, six slots | `data/save.c` | Keep file integrity separate from package compatibility decisions |
| Original GAME records and otherwise uninterpreted bytes | `data/original_save.c`, `BtpOriginalState` | Original profile retains lossless original import/export; custom packages need a different contract |

The payload decoder builds a candidate and publishes it only after validation;
file loading also uses a candidate. Extraction preserved all existing migrations
and their validation order. Old saves still use the original profile implicitly.
A future custom save needs package ID, content version, rules/API version and
stable definition IDs; its envelope/schema version is a separate concern from
content updates. Do not insert placeholder package fields into BTPe/v40 or claim
that custom instances can already be written to original GAME files.
