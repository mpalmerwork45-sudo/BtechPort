# Edit native CHI services

C4.2 exposes native service content in imported Original and Updated projects.
The existing service state machines still own transactions, rendering, RNG and
continuations. There are **156 typed parameters** and **47 named native actions**
covering all **76 action/building pairs** found in the original BLD programs.
The separate BLD recruitment instruction retains its existing repair/hospital/
prison contexts. Mission definitions and the authored-event bridge remain C4.3
and C4.4.

## Open and edit

Choose **Project → CHI services**, or **Native service content** in the project
tree. New imports already include this support. Opening an older import enables
it as one Undoable change. Make a copy first if you need that import's existing
saves: enabling or changing service content changes strict content identity.
The built-in Original/Updated games and their saves are separate.

The **Service content** tab groups searchable settings by purpose. Select a row,
edit its value and choose **Apply**. Bounds and the original default appear below
the field. **Restore default** restores that value. Save and Play collect pending
fields; invalid values leave the valid document unchanged and remain editable.
Problems navigate back to the affected parameter, and draft recovery retains
unfinished fields. Undo/Redo, source projects and ordinary Save/reopen work here.

The **Native actions** tab documents the allowed building slots, implementation,
requirements, returned values, mutations, yields and errors. Action IDs remain
compatibility operations; they do not bypass building/state preconditions.
Use **Edit building scripts** for selection menus and control flow, or **Edit
native messages** for service text fragments.

The **Broker inventory** tab selects Updated's stock by stable unit ID. Use
**All roster units** for the existing Updated behavior, or select an explicit
list. An empty explicit list offers nothing. The roster editor still owns unit
definitions and purchase prices. Mech/vehicle categories and native garage/
crew allocation continue to work as before. Stock never enables Original's
broker capability.

## What the settings control

| Area | Editable content | Preserved native behavior |
| --- | --- | --- |
| Weapons and armour | Prices, availability, weapon menu-slot equipment IDs, personal armour repair costs | Payment before recipient/swap selection; dropping equipment does not refund payment |
| Mechit-Lube | Armour/structure/heat-sink/weapon/actuator repair prices, refit prices and ammunition costs | Partial repairs, per-mech damaged-weapon lists, eligibility and held estimates |
| Hospital | Facility/doctor/kit prices, healing programs, cooldown and apprenticeship cost | Native patient messages, RNG, once-only treatment and cooldown behavior |
| Training/recruitment | Class and apprenticeship prices, recruitment limit/specialty rank/seed/autoseating, spy chance/delay | Native identities, class transcript and saved return anchors, spy replacement protocol |
| Theft/garage | Boarding attempt, guard timer, native reward-template selection, garage fee and crew policies | Prison/arena temporary-party restoration and native allocation screens |
| Broker | Stable stock IDs and resale parameters | Four native bays, parked purchases, crew references and damage-based offers |
| Comstar | Native text and BLD menus, market masks/rates/split parameters and cadet allowance | Existing account input, receipts, unsigned arithmetic and RNG draws |
| Other buildings | Clothes/inventor prices, cinema funds requirement, arena fees/prize, laser gifts and meal effect | Existing BLD flow, theatre exit, kit/device grants and native side effects |

Training selection lives in the labelled `TRAINING.BLD` menu destinations.
Menus and other building dialogue use the [BLD editor](BLD_AUTHORING.md).
Mission opponents/spawns, yard combat layouts, initial campaign state and new
authored-event calls remain later milestones. Native refit recipes, character
identity limits and eight-person/four-mech capacities remain engine contracts.
The shared catalogue reports exact bounds rather than implying unlimited data.

Stock `0` uses the native purchase-refused branch. Update that branch's wording
if it should distinguish unavailable goods from insufficient funds. Remapping
a weapon changes the item granted; edit its description/menu name to match.
A zero refit price retains the native disabled-recipe meaning. Spy chance is
restricted to 0/50/100 percent, preserving the original one-bit RNG draw and
the existing rule that later replacements are legitimate after a spy is dealt
with. The cinema's funds requirement retains the original check-only behavior.

## Linked prices and messages

Enabling service content binds unmodified original price text and fee operands
to parameters. For example:

```json
{"op":"text","text":"The price is {service:armour.price.1} C-bills."}
```

Use `{service:armour.price.4:comma}` to retain comma-separated formatting.
The three money instructions also accept a single reference:

```json
{"op":"spend_money","amount":"{service:medical.facility_fee}"}
```

The C loader expands references before compilation/rendering. The displayed
price, funds check and payment therefore use the same value. Native repair
fragments use the existing campaign dialogue overrides, with the same tokens.
Unchanged values still reproduce the original BLD bytes and native text.
Money instructions retain their original word semantics; the configurable arena
prize is bounded to the nonnegative signed-word range.

Existing custom dialogue is preserved when enabling this feature. It is not
automatically rewritten: add price tokens manually where appropriate. Editing
text or restoring a literal original fragment can remove a binding. Unknown
references, oversized source/expanded text and invalid money values fail with
source locations. Text is not automatically reflowed into native windows; use
Play to review long descriptions and menu alignment.

## Headless and AI authoring

From the repository root:

```sh
python3 tools/chi_services.py --project MY_PROJECT enable
python3 tools/chi_services.py --project MY_PROJECT list
python3 tools/chi_services.py --project MY_PROJECT set repair.armour 6
python3 tools/chi_services.py --project MY_PROJECT stock --all
python3 tools/chi_services.py --project MY_PROJECT stock chi:your-unit-id
./build/btp-project chi-services MY_PROJECT

python3 tools/author.py inspect MY_PROJECT --query objects \
  --collection native-service-parameters --limit 200
python3 tools/author.py inspect MY_PROJECT --query objects \
  --collection native-actions --limit 47
```

The native catalogue supplies the valid IDs, bounds, defaults and current
values; do not guess unit IDs. The shared batch commands are `services.enable`,
`services.update` and `services.stock`. For example:

```json
{"op":"services.update","parameter":"repair.armour","value":6}
```

Use the normal project/revision/request envelope. Parameter write/protection
scopes are `chi.service_parameters/<parameter>`; broker stock uses
`chi.broker_stock`. Enable on an older project first with a scope covering the
manifest, generated script bindings, service content and campaign text. Receipts
survive Undo. Source conversion/build and diagnostics use the same documents.

`chi_services: chi-services.json` declares `btp-chi-services-v1`, schema 1. Its
`parameters` object allows only catalogue keys and bounded integers; omitted
keys use effective native defaults. Optional `broker_stock` is an explicit
unique list of existing roster IDs; omitting it means all roster units.
The [schema](../schemas/chi-services-v1.schema.json) and C loader reject unknown
fields and incompatible values. Source and the service contract participate in
strict save identity. Class and prison continuation validators use the current
content's prices/limits; no new serialized game-state fields are needed.

Extracted text/source, private imports and saved proofs remain original-derived
content. They are not committed or included in redistributable exports. See
[the plan](CHI_EDITABLE_CAMPAIGNS_PLAN.md), [progress](CHI_IMPORT_PROGRESS.md)
and [verification](TESTING.md).
