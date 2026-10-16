# M5a CHI roster and broker — 2026-10-16

An ordinary interactive launch now asks **Original BTECH CHI** or **Updated
BTECH CHI**, before either original intro screen or audio playback. Original is
the default. Arrows choose, Enter/Space confirms, and 1/2 choose directly.
Numeric keypad navigation and Enter work too. Escape selects Original without
quitting; Ctrl+Shift+Escape exits. The Shift K/Y/R credit shortcut also works on
the selector and carries into the selected game.

Updated loads [the 17-model roster](../content/updated/README.md), exposes a
Starport broker in an unused building, and adds eligible random outdoor mech
opponents. Owned models use the existing crew, movement, firing, inspection,
repair, reload and salvage operations. Purchases are parked outside Starport;
the existing garage allocation assigns crew before departure. Four owned bays
remain the capacity, and the usual 150 C-bill garage checkout fee applies.
Unsupported custom refits take the original no-upgrade
branch without charging money or modifying the mech.

## Expanded stock and scrolling

Pack **0.2.0** adds Centurion CN9-A, Trebuchet TBT-5N, Griffin GRF-1N,
Shadow Hawk SHD-2H, Wolverine WVR-6R, Rifleman RFL-3N, Thunderbolt TDR-5S,
Archer ARC-2R, Warhammer WHM-6R, Marauder MAD-3R, Zeus ZEU-6S, Atlas AS7-D,
Crusader CRD-3R and Crusader CRD-3R (Bear). The initial Panther, Hunchback and
Catapult definitions remain byte-identical. The new stock uses existing CHI
weapon and movement operations; no model-specific combat branches were added.

The standard Crusader has two LRM-15s and two SRM-6s; Bear's has four SRM-6s
and 18 heat sinks. MegaMek's pinned source records and the CHI adaptations are
documented in the [pack README](../content/updated/README.md).

The broker has an eight-row scrolling window. Up/Down traverses every model
and the final Back item, wrapping at either end. Left/Right jumps eight
entries, with bounds clamping. Enter/Space selects and Backspace returns to
the counter. The footer shows the visible stock range. Confirmations retain
default No; cancelling or completing one returns to the same model and scroll
position. Leaving stock clears the scroll offset before entering other menus.

## Broker and inspection follow-up

The broker now occupies the central doorway of the existing three-door building
northeast of Starport's Mech-It Lube: local half-step **54,50**, approached from
**54,51** (world **1334,1075**). Only Updated adds the entrance trigger; the
original MTP, BLD and graphic files are unchanged. Entry uses the regular Yes/No
popup. The counter uses the original mechanic portrait and offers Buy, Sell and
Leave. Space no longer has a broker shortcut.

The four-bay ownership limit is explicit on every counter page. A full-fleet
purchase cannot charge money or replace a record. Sales accept both original
and custom mechs, include installed equipment, keep characters, and clear the
chosen bay and crew references without shifting any other bay. An intact custom
mech offers half its catalogue price; an original offers 100 C-bills per ton.
The condition fraction weights armor/structure points, equipment, actuators and
engine/gyro/sensor damage. It is an **APPROXIMATE authored expansion economy**,
not a recovered original price table. The quoted confirmation defaults to No;
cancel and account overflow leave ownership and money unchanged. Selling the
last mech also permits leaving the garage on foot.

Inspection preserves one pixel per armor/structure point where that fits. A
larger intact capacity scales into its original well (24 pixels, or 16 for the
head); the same fixed capacity scales damaged records, so damage shortens the
bar. Heat retains its existing 30-point display. This is a presentation change,
not a change to protection or damage calculations.

The same follow-up includes the owner's **temporary formation workaround in
both editions**. `btp_party_recover` regroups active followers on returning from
buildings/battles/menus and when a unit is over 12 half-steps (six tiles) from
its target formation offset on either axis. Placement uses terrain-checked
footprints, preferring the original formation and otherwise nearby legal tiles.
Parked vehicles and wrecks are skipped; ownership, damage and crew persist.
It does not move combatants during a battle. The comment marked **TEMPORARY
WORKAROUND** and **TODO** in [party.c](../port/core/party.c) explains the local
route-search dead end and the intended removal. It is not original DOS
behavior and is not a complete pathfinding fix. The recovery search is bounded;
if no legal spot is available nearby it retains the prior position.

This delivers the first playable CHI adapter in M5a. It does not complete the
general package/weapon schema, Lua, map authoring or editor milestones. The
[earlier authoring sample](../examples/content-demo/README.md) remains a separate
offline prototype and is not the runtime roster format.

## Starting, switching and saving

Run from the repository root after the usual build:

```sh
./build/btech-port
./build/btech-port --edition original
./build/btech-port --edition updated
./build/btech-port --edition updated --roster content/updated/roster.json
./build/btech-port --load work/player-save-updated.btp
```

Restart and choose Original to restore the original lineup immediately. Edition
switching happens before a session, not during a battle. Headless runs and
explicit diagnostic/replay entry points retain Original by default; specify
`--edition updated` to exercise the expansion there. `--load` detects an updated
save unless an edition is explicitly supplied. Use `--roster` as well if that
save belongs to an alternate roster file.

The usual six slots, including F5/F9, use `work/player-save.btp` for Original
and `work/player-save-updated.btp` for Updated, with the existing slot suffixes
on slots two through six. `--save-file` changes the base filename; Updated
inserts `-updated` before the extension. Explicit `--save PATH` uses that exact
path, but refuses to overwrite a save from the other edition.

An original save can seed a separate Updated campaign:

```sh
./build/btech-port --edition updated --load work/player-save.btp
```

Subsequent menu/F5 saves use Updated slots. Updated saves cannot be loaded in
Original or exported as DOS GAME files. Keep the original save to resume the
original campaign. Existing original assets and both reference directories
remain unchanged.

Released **0.1.0 three-mech Updated saves load directly in 0.2.0**, including
those held inside broker menus. Load normally using F9, the six-slot menu or
`--load`. The migration preserves the selected model or Back item, pending
Yes/No, party, damage, ammunition and money. It does not rewrite the source
save on load. Future saves use the new catalogue and v43 state. Older executables
cannot read that state; retain earlier saves and the
[archived three-mech pack](../content/updated/versions/0.1.0.json) to resume with
the earlier executable/catalogue.

## External definitions and compatibility

`btp-roster-check` uses the same C parser as the player:

```sh
./build/btp-roster-check content/updated/roster.json
```

The `btp-chi-roster-v1` document requires `format`, `package_id`,
`content_version`, and a nonempty `mechs` array. At most 32 definitions and
64 KiB of JSON are accepted. Strings are bounded printable ASCII without escape
sequences; numbers are unsigned integers. Unknown/duplicate fields, duplicate
IDs/codes, bad references, excessive components and malformed/trailing data
fail with a diagnostic. Loading is transactional. Choosing Original does not
require a valid or present expansion file.

Each model has a stable namespaced `id`, a unique `save_code` from 160 to 191,
`name` (15 characters maximum), `mass_tons`, `walk`, `jump`,
`engine_heat_sinks`, `sprite`, `price`, `armor`, `structure`, `actuators`,
`external_heat_sinks`, and `loadout`. Use the included definitions as examples.

- `structure` and `external_heat_sinks` have eight entries: left arm, left torso,
  left leg, head, center torso, right arm, right torso, right leg.
- `armor` has those eight front locations followed by left, center and right
  rear torso. Torso front/rear totals and per-location limits are validated.
- `actuators` contains CHI's two arm/leg actuator bitfields, retained in this
  adapter. This is one of the original-format assumptions still to replace.
- `sprite` is `locust` or `red_stinger`. Presentation is independent of the
  name, faction and save code.
- Each of at most ten weapon mounts specifies a named `location`, original
  `weapon`, `ammo` and `ammo_cost`. Energy weapons use zero ammo/cost in JSON;
  the adapter supplies CHI's unlimited-ammo sentinel. Other weapons require
  positive capacities/costs. Mount order is normalized to physical CHI slots.
- Available weapons are small/medium/large lasers, PPC, AC/2/5/10/20, machine
  gun, flamer, LRM-5/10/15/20 and SRM-2/4/6, using the snake_case identifiers
  in [roster.c](../port/data/roster.c). Their rules still come from CHI data.

Adding compatible definitions needs a JSON edit, not a C rebuild. All appear
automatically in the scrolling broker. To preserve existing saves, append new
definitions using higher unused save codes while leaving earlier definitions
unchanged. Loading verifies their entire earlier fingerprint, including IDs,
record bytes, ammunition costs and prices, using the version stored in the save.
The compatible old prefix must be shorter than the new roster. Merely editing
the version, altering/removing earlier definitions, or changing packages does
not bypass matching. There is no general migration or hot reload for edited packs.

Original retains the exact **BTS1 / BTPe v40 / 20,480-byte payload**. Updated uses
a **BTU1 envelope** with package/version and a deterministic 32-bit definition
fingerprint, plus **BTPh v43** for its scrolling-menu state. Existing
**BTPf v41 / BTPg v42** saves with a matching or unchanged extended roster load.
Their seven-model page index becomes the first visible row; old Back choices
remain Back even when new stock has been appended. Their old Space root
becomes the ordinary root, and held purchase screens migrate to the building
counter while retaining the outdoor return position, choice and purchases.
The released 0.1.0 fingerprint is **4022610150**; 0.2.0 is **751321522**. Live custom
records carry their explicit save code and a separate high-bit marker in byte
124; byte 123 alone is insufficient, because original UrbanMech records also
use values in that range. The fingerprint binds the code-to-ID mapping and
definitions, independent of JSON whitespace/object order. It is a compatibility
check, not a security signature. Missing/mismatched packs and cross-edition
overwrites fail without replacing state or files. Held broker and service
states resume through the same validation path.

## Evidence and limits

**VERIFIED:** the lifecycle suite buys each definition through the actual doorway/menu,
checks insufficient funds/full bays, sells damaged and original mechs, reuses
freed bays, leaves the garage after selling its first/last bay, assigns a pilot, fires weapons, checks
movement/heat, repairs/reloads, inspects, salvages and round-trips all six slots.
It also enters the real REPAIR.BLD and saves during repair, ammo and declined
refit continuations, and enters GARAGE.BLD to pay, allocate the new mech's pilot
through the real menus and leave mounted. Parser tests accept another JSON-only model and reject
malformed definitions. SDL checks exercise pre-logo timing, key controls,
separate save names, bad-pack fallback, the initial three purchases and
Zeus/Atlas/both Crusaders with held F5/F9 confirmations. Follow-up cases cover default-No sales, cancellation,
credit overflow, middle-bay identity, v41 held-menu migration and confinement of
intact/damaged/extreme inspection bars. The 18 executed original inspection
screens remain unchanged. The recovery suite covers real menu and BLD exits,
completed/withdrawn battles, the distance threshold, terrain and inactive units.

**APPROXIMATE:** broker/reload prices, temporary sprites and shared inspection
art, CHI component packing, per-weapon splitting of shared ammunition,
ordinary CHI targeting for tabletop rear-mounted lasers, and encounter balance.
**UNKNOWN:** long campaign balance with the expanded
roster, physical Windows audio/drivers and exhaustive combinations of authored
definitions. Source statistics and adaptation credits are in the
[pack README](../content/updated/README.md).

Repeat the checks:

```sh
ctest --test-dir build --output-on-failure
python3 -m unittest discover -s tests -p 'test_*.py'
python3 tools/native_smoke.py --updated-only
./scripts/test-sanitize.sh --core-only
./scripts/build-windows.sh
python3 tools/windows_check.py --ctest
python3 tools/native_smoke.py --windows --updated-only
python3 tools/reference_guard.py verify
```

GUI checks use private virtual displays; they do not send input to the user's
game. The following results belong to the initial roster slice, before the
owner-requested regrouping changed follower positions on scene returns:
native **58/58** (43.00 s), ASan/UBSan/LeakSanitizer **58/58**
(135.78 s), Windows/Wine **58/58** (249.94 s, default stack reserve), and Python
**23/23**. Linux and Windows SDL checks both passed the selector, intro and all
three held purchase flows. The retained fresh-campaign, spy-replacement and
service routes matched every traced input and exact final save/frame bytes.
All **1,287 reference entries** match the original contents, modes and mtimes.
The later added garage-menu assertions were also rerun in the focused lifecycle
suite on native, sanitizer and Windows builds; no production code changed for
that extension.

The follow-up adds `party-straggler-recovery` and expands
`updated-roster-lifecycle`. Native **59/59** (41.41 s),
ASan/UBSan/LeakSanitizer **59/59** (132.44 s), Python **23/23**, and ten targeted
Windows/Wine suites **10/10** (36.17 s) pass. The Windows selection covers the
new roster/recovery suites, arena returns, event decisions, original mech
inspection, original save round-trips, Space/six-slot menus, Mech-It visits,
town movement and file integrity. It uses the default Windows stack reserve.
Linux and Windows SDL checks pass all 20 window scenarios each, including the
doorway, mechanic counter, all three purchases, full capacity, held sale
confirmation/load and replacement purchase. Reviewed images are in
ignored `work/updated-broker-*.ppm` and `work/updated-inspect-*.ppm`.
Exact pre-preparation party-position traces are historical evidence; this
explicit workaround intentionally changes them after regrouping. Original
collision, crew, combat, economic and UI oracle tests remain in the CTest suite.
The reference guard confirms all **1,287 entries** retain their original
contents, modes and mtimes.

### 0.2.0 expansion verification

The lifecycle suite now covers **all 17 definitions**, including every fitted
weapon, movement allowances, heat dissipation, real broker purchases, garage
allocation, Mech-It repair/reload/refit continuations, inspection and salvage.
Both intact and damaged bars are checked for all models plus an extreme record.
Scrolling tests visit every item in both directions, wrap, use page jumps,
save/load at each row, and migrate every old v42 page/Back choice.

Compatibility tests load archived 0.1.0 records in v41/v42 exploration, stock,
confirmation, purchase-result and root-menu states. They retain all three
models, damage, ammo, crew and credits, and reject modified/removed definitions,
a different package and a record absent from the saved catalogue. Copies of
the owner's existing Updated slot 1 and slot 5 also loaded successfully with
0.2.0; the original save files were not changed by these checks.

| Check | Result |
| --- | --- |
| Native CTest | **59/59**, 42.28 s; roster test rerun after fixture-path correction, 0.67 s |
| ASan/UBSan/LeakSanitizer | **59/59**, 135.32 s |
| Python parser/tool tests | **25/25** |
| Targeted Windows/Wine CTest | **11/11** across initial run and focused rerun; default Windows stack reserve |
| Linux SDL | **28/28** window scenarios |
| Windows/Wine SDL | **28/28** window scenarios |

The initial Windows run exposed a forward-slash-only path assumption in the
new archive fixture loader. It was corrected to accept both separators; its
focused rerun passed in 3.83 s. The other ten Windows tests had passed in the
initial run. These cover original inspection, save round-trips, Space/six-slot
menus, Mech-It services, combat shots/cooling/physical attacks and core formats.
The full Windows suite was not repeated for this expansion.

Reviewed broker/Atlas/Crusader frames are collected in the ignored
`work/roster-expansion-review.png`; logs use `work/roster-expansion-*.log`.
The earlier full-game differential routes were not repeated: this update adds
optional stock and broker/save handling, while the original oracle suites
remain part of the full native and sanitizer runs. Expanded campaign balance
and unique model artwork remain outside this verification claim.
The final reference guard verifies all **1,287 entries** unchanged.
