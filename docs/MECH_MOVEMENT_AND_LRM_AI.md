# Mech movement and LRM AI audit — 2026-10-17

The current mech movement allowances match the original calculations in the
tested cases. The combat AI can fire LRMs, but its original range heuristic
does not provide good fire-support tactics for the expanded roster. An optional
Updated-mode planner is justified; the original attack rules do not require an
LRM-specific fix on the evidence below.

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

## Recommended Updated-mode increment

Keep the existing planner as the Original compatibility policy. Add an optional
weapon-aware policy for Updated games, selecting tactics from the actual usable
loadout, with an optional external `fire_support`/`skirmisher`/`brawler` hint.

- Score reachable positions using expected weapon damage, range bands, line
  of sight, cover and enemy return-fire reach. Choose a useful distance band.
- Retreat or reposition when pressed; keep a small tolerance band so a mech
  does not shuttle between two positions every round.
- Ignore empty/destroyed launchers when planning. Switch toward backup guns
  when missiles run out and toward support behavior when they are available.
- Choose a heat-safe volley using movement heat and expected cooling. A
  Catapult/Archer should not automatically spend every available laser and
  missile shot whenever a cooler sustained volley is preferable.
- Test pure missile, mixed, empty-ammo, damaged, hot, blocked-LOS and rushing
  opponents, plus mixed parties. Measure survival, damage, ammunition and
  movement, while keeping Original policy/RNG regressions intact.

This is analysis and a proposed next increment. AI policy and LRM rules were
not changed in this presentation update.

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
