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
