# Content boundaries and remaining original assumptions

This inventory accompanies [M5 preparation](M5_PREPARATION.md). It distinguishes
the reusable interface from the original adapter behind it. Moving an operation
behind an interface does not make every original format authorable.

**2026-10-16: inspected against the completed P1–P5 source.** Current owners below
are verified by code and the reported compatibility tests. Future owners and
formats are design decisions, not claims of an implemented custom runtime.

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

## Remaining content and original assumptions (P5)

| Area and code location | Current data or compiled assumption | Intended ownership and next work |
| --- | --- | --- |
| [content.c](../port/data/content.c), [resources.c](../port/data/resources.c), [cli.c](../port/frontend/cli.c) | Original resource names, required MAP1 geometry/entrances, 26 building IDs, 22 animations and three cache paths | Retain the original loader as a profile adapter; a package loader must resolve its own manifest, dependencies and startup resources |
| [resources.h](../port/data/resources.h), [prepare_talk.py](../tools/prepare_talk.py), [prepare_combat.py](../tools/prepare_combat.py), [prepare_world.py](../tools/prepare_world.py) | Fixed arrays, executable offsets, 373 text slots, font data, unit tables, world tables and sound programs | Extractors remain original-only tools. Authored definitions need stable IDs and independently supplied text/font/art/audio, not another executable extraction |
| [unit_data.c](../port/data/unit_data.c), [combat_rules.c](../port/core/combat_rules.c) | Template families and presentation/refit lookup now centralized; live records still use original armor/component/weapon bytes and fixed critical-slot layouts | Original adapter preserves bytes. M5a adds explicit definition IDs and richer live instances, mapping supported weapons/locations to reusable combat operations |
| [combat.c](../port/core/combat.c), [party.c](../port/core/party.c) | Four owned mechs, eight people, 24 combat actors, original pilot/party indexing, initiative/AI/attack semantics | These are rule/profile and instance limits, not catalogue limits. A larger catalogue must not silently widen them or change original rules |
| [world.c](../port/data/world.c), [generate.c](../port/data/generate.c), [world.c](../port/core/world.c) | Generated jigsaw terrain, original seed/coordinates, town overlays/joins, tile-property bitfields, discovery masks and tinyland mapping | Original adapter owns original tags and placement. Authored maps need explicit terrain, collision, depth, overlay, entry and minimap definitions; reuse movement/query algorithms only after their inputs are separated |
| [game.c](../port/core/game.c), [campaign.c](../port/core/campaign.c), [training.c](../port/core/training.c) | Jason's initial coordinates/credits, Citadel/training progression, destruction, Starport contexts and fixed story flags | Move authored startup/quest/transition configuration into package events. Preserve original branches behind the original profile |
| [script.c](../port/core/script.c), [original_actions.c](../port/core/original_actions.c), [story.c](../port/core/story.c), [cache.c](../port/core/cache.c), [yard.c](../port/core/yard.c) | BLD operands, numbered native actions, context-dependent waits, cache passwords/doors, theft and ending continuations | Original BLD stays supported. Future events/Lua call explicit commands and save serializable pending operations; they do not poke original flags or raw records |
| [npc.c](../port/core/npc.c), [talk.c](../port/core/talk.c), [spy.c](../port/core/spy.c) | Town routes, original names/replies, recruitment categories, spy identification/replacement and original RNG ordering | Original story adapter retains these; packages need character/faction/dialogue/route/recruitment definitions and explicit conditions |
| [campaign.c](../port/core/campaign.c), [combat_rules.h](../port/core/combat_rules.h), [yard.c](../port/core/yard.c) | Encounter pools, arena levels, guards, original hostile/friendly relations, spawn and reward rules | Future encounter/reward definitions select unit IDs and faction relations. Terrain reachability and bounded placement remain reusable rules |
| [shop.c](../port/core/shop.c), [bank.c](../port/core/bank.c), [school.c](../port/core/school.c), [service.c](../port/core/service.c) | Stock/item indices, investment/tuition behavior, medical/refit/ammo prices, original service menus, 125-byte damage repairs | Authored service definitions supply stock, prices and eligibility; commands perform checked state changes. Original quote and payment continuations remain intact |
| [menu.c](../port/core/menu.c), [pixels.c](../port/frontend/pixels.c), [sprites.c](../port/data/sprites.c) | 320×200 composition, fixed panel coordinates, original labels/ranks, palette substitutions, border/font/sprite atlas conventions | Original presentation adapter retains exact pixels. Custom presentation needs text IDs, font metrics, portraits, atlas/animation metadata and chosen UI layouts |
| [animation.c](../port/core/animation.c), [effects.c](../port/core/effects.c), [anm.c](../port/data/anm.c) | Original animation IDs, directional poses, frame programs, electric terrain and ordered attack/destruction outtakes | Generic renderer/effect sequencing can consume authored frame/timing/event metadata; original ANM decoding and frame programs stay profile-specific |
| [audio.c](../port/core/audio.c), [sounds.c](../port/data/sounds.c), [sdl.c](../port/frontend/sdl.c) | SIF title music, 18 sound programs, PC-speaker calibration and action-bound event order | Original sound adapter preserves XT behavior. Packages need sound/music IDs and timing; output device buffering stays in the frontend |
| [state_codec.c](../port/core/state_codec.c), [save.c](../port/data/save.c), [original_save.c](../port/data/original_save.c) | Original-profile migrations, raw GAME preservation and held state | Keep current contract. Custom packages need separate definition references, identity/version checks and migration policy before any custom state is persisted |

The original RNG and rules are useful reusable algorithms but still implement a
specific rule profile. Externalizing constants alone does not make them support
arbitrary combat systems. Conversely, purely authored names, startup positions,
stock, model statistics and art references should not require C edits once M5a/
M5b implement the corresponding package inputs.

## Stable identity and the prototype

The [sample](../examples/content-demo/README.md) and
[schema](../schemas/content-v1.schema.json) distinguish these identities:

| Identity | Current mapping | Future authored representation |
| --- | --- | --- |
| Immutable original starting template | `BtpMechTemplate` family plus checked table index | Namespaced chassis ID, e.g. `workshop:trail-kite` |
| Original weapon definition | Checked 0–32 lookup into extracted records | Namespaced weapon ID, referenced by an explicit mount slot |
| Original live unit | Party/combat slot plus raw record, retaining original tag semantics | Stable definition ID plus mutable instance identity/state |
| Original appearance | `btp_mech_sprite_base(tag, enemy_context)` | Separate asset ID, frame geometry, direction and animation metadata |
| Original refit | Model byte 123, stage byte 124 and one of eight recipes | Explicit refit/service definition referencing input and output models/equipment |

No original definition export was needed or added. All prototype names and
statistics are independently authored. The sample demonstrates validation of
three models, two weapons and a placeholder presentation; it is not a runnable
miniature game, a new source of original data or an approved final package ABI.
The validator's normalized digest covers definitions only. Asset decoding,
critical-slot allocation, portraits, animation cadence, shops/refits, encounters
and save compatibility remain integration work for M5a.

## Concrete prerequisites for an independent M5b game

1. **Complete M5a first:** one shared runtime definition validator/loader,
   namespaced IDs in instances and custom saves, authored sprites and the full
   obtain/inspect/fight/damage/repair/refit/salvage/save lifecycle. Keep the
   original profile using the compatibility path above.
2. **Package/bootstrap inputs:** manifest, content and rules versions, start
   map/coordinates, initial party/resources, asset roots and optional title/
   ending. Loading must succeed with original files and caches unavailable.
3. **Maps and terrain:** authored map dimensions/layers, tile graphics and
   semantic properties, doors/entries, town placement, discovery/minimap and NPC
   routes. A small static map can precede a general terrain generator/editor.
4. **Characters, text and UI:** authored font/glyph metrics, dialogue/text IDs,
   portraits, menus and inspect/combat layouts, plus world actors and faction
   definitions. No fallback to the original 373 strings or fixed Jason setup.
5. **A minimal quest with persistence:** an event dispatcher, dialogue choice,
   reward/inventory/encounter commands, one Lua handler and serializable waits
   through combat and an ending. Demonstrate reload during dialogue and combat
   before building the GUI editor around those contracts.

These are the concrete package blockers. The P1–P5 work makes their ownership
visible and testable; it does not silently solve them or require an editor/Lua
dependency to keep the existing game playable.
