# Mech movement audit and Updated LRM combat plan — 2026-10-17

The current mech movement allowances match the original calculations in the
tested cases. The combat AI can fire LRMs, but its original range heuristic
does not provide good fire-support tactics for the expanded roster. An optional
Updated-mode planner is justified; the original attack rules do not require an
LRM-specific fix on the evidence below. The owner has requested a plan for that
planner **including LRM minimum range**. The implementation plan below is
now being implemented at the owner's request. The dated audit above remains
the pre-change baseline; the delivery record below distinguishes completed work.

## Implementation record

- **LRM1 implemented:** bounded external combat profile, explicit saved policy,
  Enhanced/Legacy settings and pure range/attack queries. Enhanced payloads
  use BTPj/v45 inside BTU2; ordinary Original/Legacy states retain v44 bytes.
  Old saves select Legacy; rule fingerprint mismatches reject transactionally.
  Eight focused native suites pass, including original attacks/AI, roster,
  original saves and the new profile/query tests (`work/lrm-stage1.log`).
- **LRM2 implemented:** manual, friendly and enemy resolution share the Updated
  range query; the target panel displays the close-range modifier within its
  existing border. Independent boundaries, footprint cases, actual manual
  shots and held saves pass; four focused suites pass (`work/lrm-stage2.log`).
  The target panel has been visually reviewed.
- **LRM3 implemented:** deterministic candidate paths, usable-weapon scoring,
  incoming-fire/heat estimates and stable position preferences. Controlled
  Catapult, Trebuchet and Archer cases retreat when supplied and approach with
  empty launchers; Atlas accepts its useful close fight. Blocked maps hold
  safely. Six focused native suites pass (`work/lrm-stage3.log`).
- **LRM4 implemented:** exact cooling-aware volleys for eight shortlisted
  positions, live shot valuation and bounded LRM deferral. Remaining useful
  mounts reserve firing opportunities. A synthetic two-launcher retreat fires
  each launcher once and resumes identically through every tick, including
  held effects; per-unit Computer/Next/Space controls and the stationary shell
  pass. The focused policy suite has 20,167 checks. Original combat/UI/pacing
  regressions also pass (`work/lrm-stage4.log`).
  LRM5 remains in progress; new-game defaults are not enabled yet.

## Movement calculations

**VERIFIED:** `make_extended_movement_vectors.py` runs original `103B:22BC`
instructions with the walk/jump dimensions of all 23 external models and three
original loans. All **1,872 cases** match the native movement allowance: three
modes, six heat levels and four actuator states per model. This supplements
the existing original navigation, terrain, waypoint and complete-wave cases.

| Model | Walk | Run | Jump |
|---|---:|---:|---:|
| Atlas AS7-D | 3 | 5 | 0 |
| Highlander HGN-733 | 3 | 5 | 3 |
| Catapult CPLT-C1 | 4 | 6 | 4 |
| Shadow Hawk SHD-2H | 5 | 8 | 3 |
| Phoenix Hawk PXH-1 | 6 | 9 | 6 |
| Jenner JR7-D | 7 | 11 | 5 |

The adapter puts declared walk/jump values in record bytes 49/50. Healthy,
cool running is the familiar rounded 1.5× allowance. Leg/actuator damage and
heat reduce walking/running; jumping uses its jump allowance, with heat 30
disabling movement. The original running calculation applies its rounding bit
from the **base** walking value after damage/heat reductions. Replacing that
with a blanket modern rounding formula would change original behavior.

These are movement budgets, rather than per-sprite animation delays. A round
has twelve microsteps: a faster mech can advance during more of them. Terrain
can consume two or three points for an advance. Jump uses its own terrain/
landing rules. All current models fit the twelve-step ceiling; future custom
walk values above eight can produce running allowances above twelve, requiring
an explicit engine/content decision before claiming they are fully usable.

**Exploration distinction:** ordinary party travel uses the selected one/two/
four-step input amount and group formation. It does not independently pace
every mech by its combat walk statistic. The new audit verifies combat budgets;
it does not claim different model speeds on the world map or exact tabletop
movement rules. No movement-rule change was needed for the current roster.

## What the current AI does

**VERIFIED native behavior:** `btp-mech-tactics-audit` runs the real automatic
player planner in **644 controlled open-ground scenarios**: every external
model, seven separations, cool/hot, and stock/empty missile ammunition.
These are planner probes, rather than campaign outcome comparisons.

The current shared planner:

1. Chooses a nearby target, generally preferring its own unit class.
2. Scans installed weapon components for a preferred range. The original scan
   intentionally uses the raw component value as the table index, although a
   weapon's real index is one less. The port preserves this observed original
   quirk. It takes the smallest threshold rather than weighting a loadout.
3. Approaches when outside that threshold or lacking line of sight. It has no
   corresponding retreat rule when the enemy comes closer.
4. Assigns available weapons to the target. Actual range, ammunition, firing
   eligibility and numeric attacks are checked during the wave. Empty guns
   are not fired, but still influence the preferred-range scan.
5. Uses the existing broad heat decisions. It does not optimize a sustained
   missile volley against future cooling or reserve heat for movement.

Measured examples (the thresholds below are CHI distance-heuristic values,
not half-step coordinates or minimum ranges):

| Model | Current threshold | Behavior observed |
|---|---:|---|
| Catapult C1 | 24 | Holds inside 24; approaches from farther away; never backs off |
| Trebuchet 5N | 24 | Same range behavior despite its different movement budget |
| Archer 2R | 16 | Closes farther in because its raw LRM20 component indexes the next weapon row |
| Crusader 3R | 4 | Mixed short-range equipment drives a close approach |

An empty Catapult retains threshold 24 while its gun orders fall from six to
four. It can therefore hold too far away to use its remaining weapons well.
At point-blank separation it stays in place; there is no fire-support retreat.
These are concrete reasons to improve the Updated planner. A separate hardcoded
controller for every mech name would make loadout changes harder to support.

## Original LRM attack rules

**VERIFIED bounded observation:** `audit_lrm_rules.py` executes the original
attack span for all four LRM sizes at six target positions. With stationary,
cool, unskilled, uncovered actors and no target movement, the required roll is
4 at X=66, 68, 76, 86 and 106 from an attacker at 64,64; it becomes 6 at X=120.
There is no additional close-range LRM penalty in those original calculations.
Existing original-shot regressions cover the native attack routine separately.

Consequently, a tabletop-style minimum range should be a deliberate Updated
rules option if desired. It should not be introduced as an Original-mode
correction. Stand-off tactics still have value without it: an LRM carrier can
use range to avoid shorter-range return fire and protect its missile supply.

## Updated combat plan

**Authorized implementation plan; see the delivery record above for status.**
Introduce one versioned Updated combat profile that combines weapon-aware
tactics with an LRM close-range accuracy penalty. Derive tactics from working
weapons, ammunition and movement, so a Catapult, Archer, Crusader or future
custom model uses the same planner. An Atlas with one launcher should still
use its other weapons effectively.

### Edition and save behavior

- New Updated campaigns default to the enhanced profile once all five gates
  below pass. The profile applies to every LRM, including weapons on original
  models, for both player and enemy attacks. Manual and automatic firing use
  identical rules. Enemy mechs and individually automated player mechs use the
  new planner; infantry retains its current planning policy initially.
- Updated's existing settings gain one `Combat rules: Enhanced / Legacy`
  choice, available outside an encounter. It selects the rules and planner
  together. The early Original/Updated selector remains sufficient to start
  a new campaign; another startup question is unnecessary.
- Original campaigns always use the compatibility policy. Legacy within
  Updated keeps its expanded roster but uses the current CHI combat rules and
  AI. The selector must never interpret a mech's name, sprite or roster index
  as the rules profile.
- Existing Updated saves, including v44 saves held during combat, load into
  Legacy. Original saves explicitly imported into Updated do likewise. The
  player can enable Enhanced outside combat without restarting or losing
  owned mechs, equipment, money or story progress. A short settings description
  makes this migration discoverable.
- Save the active profile ID/version and semantic rules fingerprint, along
  with any persistent planner state, in a versioned codec. An old BTU1 save
  means Legacy. Add an explicitly versioned Updated envelope when needed;
  update edition detection and all six slots together. Retain original GAME
  import/export restrictions and transactional failure. Loading a held battle
  restores its saved policy, pending orders and effects. Unknown profiles or
  changed required rules produce a clear error and preserve the current game.

Keep policy selection in explicit core/session state and immutable rule data
in the content context. A roster fingerprint cannot identify combat behavior:
the current save header binds models and prices but has no AI/rules identity.
Headless state encoding must retain policy too, rather than relying on an SDL
preference or a process-global flag. Original payload compatibility is a gate;
do not relabel all existing saves merely to add an Updated option.

### Minimum range and CHI distance

Use the standard Inner Sphere LRM minimum-range **accuracy penalty**. The
official rulebook lists minimum range 6 for LRM-5/10/15/20 and adds
`minimum range - target range + 1` when within that distance. Firing remains
possible at close range. See the *Minimum Range Modifier* rule on printed
page 18 and *Weapons and Equipment Table* on page 55 of the
[official A Game of Armored Combat rulebook](https://battletech.com/wp-content/uploads/2025/07/BattleTech-A-Game-of-Armored-Combat-Rulebook-1st-SLDF-Print.pdf).

The following conversion is an **authored adaptation**, not evidence of a
minimum-range rule in CHI. CHI uses an integer distance heuristic, square
half-tile positions and vehicle footprint adjustments. Its non-personal range
thresholds generally scale by three; interpreting six as six screen tiles or
six raw coordinate steps would be inconsistent with its other ranges.

Proposed calculation, shared by attack resolution, AI and targeting feedback:

1. Obtain `D`, the effective CHI shot distance, using the existing
   `btp_combat_range_to` target-footprint behavior. Infantry targets retain
   their exact anchor. Factor this into a side-effect-free helper without
   changing the compatibility calculation.
2. For Updated LRMs define `R = max(1, floor(D / 3))`. Call this a **range
   unit**, not a literal hex or screen tile. It also defines the behavior at
   overlapping/adjacent anchors where CHI can return zero.
3. Add `max(0, 7 - R)` to the required hit roll, before rolling any dice.
   A legal attempted shot still consumes its usual ammunition and heat.
   A very poor shot can be impossible to hit under the existing dice rules;
   the manual player may still order it, while the AI avoids wasting it.
4. For these LRMs use short range `R <= 7`, medium `8..14`, long `15..21`;
   reject `R > 21`. Other weapon ranges retain their current rules.

| Effective CHI distance D | Updated range unit R | Minimum-range penalty |
|---|---:|---:|
| 0..5 | 1 | +6 |
| 6..8 | 2 | +5 |
| 9..11 | 3 | +4 |
| 12..14 | 4 | +3 |
| 15..17 | 5 | +2 |
| 18..20 | 6 | +1 |
| 21..23 | 7 | 0 |
| 24..44 | 8..14 | 0; ordinary medium-range modifier applies |
| 45..65 | 15..21 | 0; ordinary long-range modifier applies |
| 66 and above | 22 and above | Out of range |

**Deliberate Updated range adjustment:** the extracted CHI LRM rows currently
end short range at `D < 21`, medium at `D < 45`, and long at `D < 66`.
The proposed short-range boundary becomes `D < 24`; the other two remain.
Without that small adjustment, the proposed six-unit penalty would consume
CHI's entire short-range band. Record this change alongside the penalty,
rather than silently changing the original table or claiming exact hex-map
equivalence. Check the transition visually before finalizing this profile.

Put these values in a small validated Updated combat definition, provisionally
`content/updated/combat.json`: schema/profile versions, named LRM weapon IDs,
distance scale, minimum range, range bands and planner policy. Resolve names
through the existing adapter (original weapon indices 25..28); do not scatter
numeric tests through AI and UI code. Hash semantic gameplay data separately
from roster and cosmetic art. Existing packs without the new definition offer
Legacy; malformed definitions fail explicitly. General weapon authoring and
additional weapon families' minimum ranges can follow separately.

### Movement and target selection

At round planning, evaluate the mech's **usable** loadout: working components,
remaining shots, legal targets, current heat, movement budget and cooling.
The current raw-component off-by-one range scan belongs only to Legacy.

1. Consider standing, walking, running and available jumping. Generate a
   bounded set of candidate destinations around the actor and its targets,
   including retreat and lateral movement. Run them through the existing
   route/movement legality helpers and score the actual resulting path and
   endpoint. Respect turns, terrain costs, full mech footprints, other units,
   town walls, water, jump restrictions and the twelve-microstep round.
2. Score target/position pairs using expected usable damage, line of sight,
   cover, likely return fire and movement/heat cost. Damage estimates use
   CHI's actual hit probabilities and missile cluster data. A launcher is not
   worth its maximum missile count on every shot. Enemy threat estimates use
   visible/scan-available information, never hidden orders or future RNG.
3. Prefer a useful firing band instead of maximum separation. When a nearby
   attacker makes LRMs inefficient, retreat or move sideways while retaining
   a shot. When nothing reachable can clear minimum range this round, reward
   useful progress and use backup weapons. A surrounded or immobile mech
   selects its best legal attack; it does not become stuck requesting retreat.
4. Weight the whole loadout. A missile-focused mech should favor support
   distance; a mixed Crusader or Atlas can accept a close fight when its other
   weapons make that worthwhile. Empty or destroyed launchers contribute
   nothing to preferred distance. Reevaluate at each round as damage and
   ammunition change, without hardcoded model-specific controllers.
5. Favor holding an already useful position unless moving offers a meaningful
   improvement. Use deterministic tie-breaking and a small score tolerance
   to prevent alternating between equivalent squares. Account for allied
   destinations to reduce bunching, then recheck occupancy during movement.
   Tactical retreat cannot intentionally cross an encounter's escape boundary;
   fleeing remains a separate decision under existing controls.

The first implementation can use current position/orders for stability. If
testing requires previous-target or previous-goal memory, serialize it; do not
hide it in static variables. Role hints such as `fire_support` may be added
later as optional defaults, after loadout-derived behavior works on its own.

### Heat, ammunition and firing during movement

Choose a useful weapon subset instead of assigning everything. Estimate hit
probability without consuming RNG, and project the selected volley through
the same cooling calculation as combat, including movement, heat sinks,
engine damage, burning and water. Prefer sustainable volleys and cooldown
when hot; give strong penalties to accuracy/movement heat thresholds and
avoid an avoidable shutdown. Ammo conservation should discourage low-value
shots without making a supplied LRM mech refuse ordinary useful attacks.

Planning must account for the twelve-step wave: the first legal shot may occur
before the planned endpoint. For automated actors, reevaluate shot quality
against live positions before each firing opportunity. Permit a launcher to
wait for a better point on its remaining route instead of firing immediately
from inside minimum range. Use a bounded fallback at the last opportunity so
it does not wait forever; skip an impossible shot, or take the best worthwhile
available one. Manual weapon orders retain normal firing opportunities and
receive the same actual range penalty. Do not keep replanning routes every
animation tick or inspect where a hidden enemy order will finish.

Expose concise Updated-only feedback such as `LRM close range: +3 to hit` in
the selected weapon/target panel. The UI uses the common query and existing
text bounds; it must not generate a popup for each missile. Debug traces may
record reasons such as retreat, blocked LOS, empty launcher and heat limit.

### Code boundaries and deterministic behavior

| Area | Intended change |
|---|---|
| `port/core/combat_rules.c/.h` | Pure range/to-hit/heat queries and explicit rules-aware attack entry; existing compatibility entry points retain their behavior |
| `port/core/combat.c` | Dispatch policy before planning; preserve script eligibility; use the same Updated rule for actual manual/enemy/automatic shots and auto-only firing deferral |
| Proposed `port/core/combat_ai.c/.h` | Bounded candidate/target/volley scoring; share existing route and collision primitives |
| `port/data/unit_data.c/.h`, content/resources | Named weapon properties and immutable validated Updated rule data |
| `port/core/game.h`, state codec, `port/data/save.c` | Versioned selected policy and any planner memory; old-save migration and policy fingerprint checks |
| Frontend targeting/settings | Saved profile choice outside combat and one compact minimum-range indication |
| `tools/mech_tactics_audit.c` and focused tests | Policy-selectable multi-round scenarios, decision traces and performance counters |

Attack previews and candidate evaluation are pure: no ammunition use, heat
changes, damage or RNG draws. Apply the extra modifier within attack resolution
before the hit roll, never by editing a completed `BtpShot`. Keep integer/fixed
point scores and stable unit/candidate tie-breaks across Linux and Windows.
The planner runs as ordinary C code without any online/model dependency.

Preserve scenario restrictions ahead of policy dispatch: the training shell
does not move/fire, protected arena spectators retain their protections, and
spy/story targeting rules remain in force. Assigning Computer affects only the
selected player unit and leaves the menu open; Begin Fight and Space pause
retain their current behavior. Manual orders must not be silently replaced.

### Delivery gates

Each gate should leave the game playable and produce a local commit plus a
short verification record. Enable Enhanced by default for new Updated games
only after LRM5; earlier gates expose it to tests/development selection.

| Gate | Deliverable | Acceptance |
|---|---|---|
| **LRM1 — Profiles and shared queries** | Explicit Legacy/Enhanced selection, validated rule data, save identity/migration, pure attack estimates | Original rule/RNG fixtures and saved continuations match; old Updated saves resume Legacy; profile round trips and invalid loads are transactional; querying never mutates state |
| **LRM2 — Minimum range** | Four LRM types use the documented conversion, short-band adjustment and penalty; manual UI explains it | Boundary/diagonal/footprint tests; identical manual/auto/enemy modifiers; original and non-LRM results match their baseline |
| **LRM3 — Positioning** | Usable-loadout scoring, legal retreat/lateral routes, stable useful firing positions, multiple targets | Supplied Catapult/Archer seek support positions; empty ones use backups; mixed Crusaders retain useful close options; trapped/damaged units and town edges never produce illegal paths or endless alternation |
| **LRM4 — Volleys and live fire decisions** | Cooling-aware weapon subsets, ammo valuation, movement-aware firing deferral | Hot/empty/damaged cases use valid orders; a retreating launcher can wait for a better shot; no indefinite waiting, duplicated shots or extra planning RNG; Computer/Space controls still work |
| **LRM5 — Release verification** | Saved/UI checks, Original regressions, Updated scenario results and performance measurements; new Updated defaults enabled | Native full suite plus focused sanitizer, Windows/Wine and Linux/Windows SDL checks pass; report scenario outcomes and limitations; references unchanged |

### Verification matrix and speed budget

Reuse the 644-scenario audit as a starting point, then run several rounds from
small declared prerequisites. A new campaign playthrough is unnecessary for
each AI case. Cover all 23 models in a quick legality sweep and concentrate
behavior checks on Catapult, Archer, Trebuchet, LRM/SRM Crusaders, Stalker and
Atlas, with a fast Jenner pressing them. Include a synthetic pure-LRM loadout
only as a labeled test fixture, not as an undocumented roster addition.

- **Range rules:** each launcher at every penalty step, `D=20/21/23/24`,
  `44/45` and `65/66`; zero distance; all octants, target infantry/mech and
  odd/even anchor coordinates. Compare independent expected tables, actual
  shot results and displayed modifiers. Check skill, cover, motion and heat
  combinations, ordinary shot consumption, and save validation bounds for
  the larger required hit roll.
- **Tactics:** static and rushing targets; multiple enemies; full, partial
  and empty ammunition; disabled launcher, leg/jump damage, high heat and
  burning; open terrain, blocked LOS, corners, narrow streets, water, escape
  boundaries and mixed allied formations. Verify every executed movement
  step, rather than only the final destination. Record damage dealt/taken,
  heat, ammunition use, turns without useful action and position oscillations.
- **Save and control:** Original, old Updated and Enhanced saves; switching
  profile outdoors; blocked switching during an encounter; F5/F9 during
  target selection, approach/retreat, a deferred shot and effects; reload and
  continue deterministically. Check all six slots, explicit save paths, missing
  or incompatible rule definitions, per-unit Computer selection and Space.
- **Comparison:** compare old/new planners under the **same Enhanced firing
  rules** in a test-only configuration to isolate tactics, then compare the
  complete Legacy/Enhanced profiles for balance. Fixed seeds make runs
  repeatable, but different shot choices necessarily diverge combat RNG;
  report results across a declared seed set without claiming matched rolls or
  universally superior win rates. Original behavior retains its separate
  exact-fixture checks.
- **Performance:** bound candidate/target/volley work by fixed operation
  counts, cache shared geometry and evaluate full volleys only for shortlisted
  candidates. At most ten weapon mounts make subset enumeration feasible
  there. Profile a full 24-actor round with graphics off, reporting median,
  tail and maximum planning time; aim to stay within one 32 ms host tick on
  the development machine. If expensive, reduce deterministic search breadth,
  never make decisions depend on a wall-clock timeout. Animation speed must
  not change tactical decisions.

During implementation, run the focused checks first and the broader suite at
the integration/release gates. Preserve existing original oracle fixtures;
Updated expectations have separate fixtures and clearly labeled authored
rules. Build with the established two-job limit. Review the minimum-range
display and a retreating LRM fight on both SDL platforms before release.

The first release excludes indirect fire/spotters, new missile ammunition,
Clan/advanced launchers, other weapon minimum ranges, a general weapon editor,
global squad strategy and a replacement pathfinding engine. Its concrete goal
is credible direct-fire LRM behavior with measurable compatibility and save
support. Balance and worst-case planning time remain **UNKNOWN** until the
proposed gates run.

## Reproduction

```sh
python3 tools/make_extended_movement_vectors.py
ctest --test-dir build --output-on-failure -R mech-movement-extended-primary
./build/btp-mech-tactics-audit 'Original DOS' work/combat-data.bin content/updated/roster.json > work/mech-audit.csv
python3 tools/audit_lrm_rules.py
```

Original executable hashes and prerequisites accompany the movement fixture.
Local scenario output and the original LRM samples are retained under
`work/weapon-presentation/`. The original binary remains the behavioral
authority; these observations do not claim tabletop or general BattleTech AI
equivalence.
