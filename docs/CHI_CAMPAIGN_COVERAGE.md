# Native CHI campaign authoring coverage

This is C4.3's disposition ledger for every system in the
[C1 inventory](CHI_IMPORT_CONTRACT.md#resource-and-campaign-dependency-dispositions).
It covers both imported editions. **VERIFIED** below means the stated current
port comparison/fixture passed; it does not establish every original DOS branch.
Raw imported text, art, maps and evidence remain private.

GUI names below are under **Project → CHI …**. `missions.*`, `services.*`,
`bld.*` and spatial/presentation operations are the shared document commands;
the [command catalogue](AUTHORING_COMMANDS.md) specifies their full envelopes.

| Inventoried system / implementation | Editable content and GUI/CLI surface | Preserved behavior and verification |
| --- | --- | --- |
| MAP1–14; `data/chi_spatial.c`, `core/world.c`, `core/npc.c` | C3 maps/world: cells, collision mapping, entrances, placements, NPC routes; spatial/source operations | VERIFIED C3 all map bytes/cells and edited movement/placement. Native world/location and BLD context retained. |
| MAP15; `data/chi_spatial.c`, `core/cache.c` | C3 map-room cells; C4.3 `cache.password.*`, room entry/return, prerequisites | VERIFIED full fresh campaign, native cache suite, edited terminal/prerequisite/ending journey with saves. Fixed raw index conversion documented. |
| Tile banks/ruin graphics; `frontend/pixels.c`, `core/combat.c` | C3 resources/maps and C4.3 `invasion.ruin_after`, `arena.field.*`, `cache.secret.*`, `cache.door_tile.*` | VERIFIED matching map/collision switch, physical invasion escape and rendering at held saves. Original tile-class semantics remain the native format. |
| CMP screens/sprites/fonts/tinyland; `data/chi_presentation.c`, `frontend/pixels.c` | C3 resources and art/sprite tools | VERIFIED C3 decoded crops/override playback. Original palette/slot identities retained. |
| O0–O21 movies; `core/animation.c` | C3 film frames/timing/sound references; C4.1 BLD `animation` | VERIFIED native startup, invasion and ending sequences with held saves. Native cutscene purposes remain bounded engine continuations. |
| Music/sounds; `core/audio.c` | C3 supported sound references and C4.1 BLD `sound` | VERIFIED existing audio regression; sequential playback and native instruction interpreter retained. This pass adds no new synthesis mechanism. |
| All 26 BLDs; `data/chi_scripts.c`, `core/script.c`, `core/original_actions.c` | C4.1 scripts: text, conditions, flags, menus, rewards, native calls and animation/sound operations | VERIFIED 52 byte-identical compiled files across both defaults; baseline gameplay/RNG and edited return continuations. All 47 actions/76 observed building contexts retain the C4.2 registry. |
| Native dialogue/font; `data/chi_services.c`, `frontend/pixels.c` | Campaign messages, resources/font, script text; `{service:…}` and `{mission:…}` references | VERIFIED reference expansion, invalid references, edited return popup, original native menu placement. Arbitrary reflow remains unsupported. |
| Loan/enemy/arena/combat tables; `data/chi_missions.c`, `core/combat.c`, `core/yard.c` | Missions unit roles; project roster for new records, `training.*`, `arena.*`, infantry weapon/skill settings | VERIFIED native templates preserved and edited two-enemy force/roster role, rental/spectator/guard instance. Generic combat rules and damage machinery stay in C. |
| World generator; `data/world.c`, `core/world.c` | C3 world seed, tables, jigsaws/joins and town placements | VERIFIED C3 whole-world comparisons at three seeds, both ruin states/profiles; sampled water-depth crossings. No claim of all-seed DOS parity. |
| Initial player/state/RNG; `core/game.c`, `core/state_codec.c` | Missions `start.*`; maps/world initial position | VERIFIED edited credits, nonstandard allowance, constitution and medical skill survive saves; defaults preserve gameplay/RNG comparisons. Native story/party initialization conventions retained. |
| Shop purchases/recipients; `core/shop.c`, `core/service.c` | C4.2 services stock/prices, C4.1 shop scripts | VERIFIED C4.2 edited armour purchase and ordinary service/alternate-service routes; native recipient and swap handling retained. |
| Economy/classes/Comstar; `core/economy.c`, `core/school.c`, `core/bank.c` | Services prices/market, scripts costs/caps/conditions, missions starting funds/cap | VERIFIED funded class/bank/default comparisons and C4.2 altered tuition continuation. Native bank/input and market arithmetic/RNG retained. |
| Repair/ammo/crew/garage; `core/service.c`, `core/party.c`, `core/menu.c` | C4.2 services settings, roster equipment and scripts | VERIFIED C4.2 healing/payment and native repair/garage tests; per-instance weapon/damage lists, crew and saves retained. |
| Training/recognition/driving/recovery; `core/training.c`, `core/combat.c` | Missions `quiz.*`, `driving.*`, `recovery.*`, `training.*` and roles; scripts choices/results/story effects | VERIFIED four-question recognition, changed duel/start/force/prompt/retreat-as-pass/return text and script resume with saves. Native assignments, skill/result and timer tests also pass. |
| Invasion/ruined Citadel; `core/combat.c`, `core/training.c`, `core/npc.c`, `frontend/pixels.c` | Missions `invasion.*`, assignment invasion choice, roles; C3 ruin map/film; training result script | VERIFIED four Jenners, earlier ruined-map switch with live cadet NPCs, physical escape and draining story/film before exploration; saves at held transitions. Five-message continuation remains native. |
| Encounters/choices/rewards; `core/campaign.c`, `core/world.c` | Missions `encounter.*`, three unit roles and 22-entry weapon table | VERIFIED offer/refusal, larger cash through reward/weapon/victory pages and single-payment reload. Reachability/starport restrictions and native victory regression pass. Encounter placement remains native plus the previously requested reachability correction. |
| Salvage/aftercare; `core/campaign.c`, `core/party.c` | Missions field/mech/town salvage switches, expert threshold and heal policy; C4.2 repair/heal settings | VERIFIED edited reward fixture disables salvage/aftercare; native salvage/repair/medical corpora preserve original ordering and damaged-instance rules. No replacement salvage algorithm is introduced. |
| Recruitment/NPC/spy; `core/party.c`, `core/talk.c`, `core/spy.c` | C3 routes, C4.2 recruitment attributes/skills/odds, scripts skill/party conditions, C4.3 Rex actor/ambush/role | VERIFIED native recruitment/spy replacement suite and ordinary Rex/services route. Native IDs, trait ownership and spy pilot/passenger resolution remain engine contracts. |
| Prison/starport theft; `core/yard.c`, `core/story.c` | Services attempt/timer/crew policies; missions prison positions/guards/reward and arena escape/roles; scripts branches/rewards | VERIFIED C4.2 altered prison boarding; C4.3 guard/arena theft return and exact held saves. Native four bays/crew menu and theft outcomes retained. |
| Arena; `core/yard.c`, `core/campaign.c` | Missions arena positions, roles, force fields, opponent rolls/reduction/damage and retreat; services rental/prize; scripts waiver/results | VERIFIED real doorway, changed loan, fixed field layout, spectator alarm/one guard, physical escape and retained loan. Native arena win/loss/outcomes suite retained. Alarm proof declares the spectator-hit boundary. |
| Inventor/cinema/houses/ending; BLDs, `core/story.c`, `core/cache.c` | C4.1 scripts, C4.2 costs/effects, C3 art/films, C4.3 cache access/contents/conditions/ending | VERIFIED ordinary services/alternate-services and fresh-game route through ending. Edited final prerequisites execute original ending text/films and quit with saves. Tile-trigger vocabulary and special map slots stay native. |
| Updated roster/rules; `data/definitions.c`, `content/updated` | Existing units/weapons/equipment/rules editors; missions roles reference project mech IDs | VERIFIED imported Updated defaults, enhanced edited mission journeys and C4.2 broker stock. Original edition features are not silently enabled. |
| Updated portraits; `data/portraits.c`, C3 presentation adapter | Resources/portrait edits | VERIFIED existing C3 override/playback. AI provenance/asset licenses remain attached to imported copies. |
| Persistence; `data/save.c`, `core/state_codec.c` | Same pinned project content; effective settings participate in identity and resource-aware validators | VERIFIED edited held saves and continued effects without repeated payments, plus isolated normal/imported slots. C4.4 adds opt-in v53 mixed continuations; ordinary saves retain their layout. |
| Added quests; `core/chi_bridge.c`, `core/events.c` | Quest GUI/CLI, native doorway and BLD calls, explicit return labels, verified ComStar adapters | VERIFIED both editions' optional relay contract, live battle outcomes, payment/reward once, four frames, cancellation/depth/cycle/budget paths, 58 Linux/Wine held-save/frame/next-input comparisons. Other native adapters reject explicitly. |
| Editor/sources/automation; shared Python document/workspace | Mission GUI/CLI, typed batch scopes, inspect/protection, source conversion/build, Undo/Save/recovery/Problems | VERIFIED Python contract tests and Linux GUI edit/invalid-draft/navigation/reopen/native Play journey, including controls in a 1000×730 workspace. Native Windows Python/Tk remains UNKNOWN. |

## Remaining milestones and boundaries

C4.3 externalizes the listed content for the existing native systems. It does
not remove their native record layouts or replace their mechanics with a new
scripting engine. The bounded capacities and coordinate/tile conventions are
listed in [mission authoring](CHI_MISSION_AUTHORING.md#coverage-and-limits).
No known required native opcode is silently skipped.

**C4.4 implemented:** BLD/native ↔ authored-event calls, bounded nested returns,
mixed saved continuations, native boundary observations and an optional new-quest
recipe. See [quest authoring and limits](CHI_QUEST_AUTHORING.md).
**C4.5 passed:** fresh full ending routes, explicit execution counts, multiple
units and the combined service/mission/spatial/quest checks are recorded in
[acceptance](CHI_ACCEPTANCE.md). The Updated full route explicitly selects
Legacy through Settings; replaying Original inputs under default Enhanced does
not prove Updated completion. Earlier broader wording is corrected there.
**C5 implemented:** setup/retry/recovery, general reconstruction recipes and
actual package/archive payload checks. Linux/Wine verification and external
native Windows Tk/Astra audit limits remain explicit in the acceptance report.

Private retained evidence and reproducible commands are recorded in
[TESTING.md](TESTING.md#native-mission-authoring--2026-10-24). Read the declared
checkpoints there before treating a focused mechanism proof as a normal route.
