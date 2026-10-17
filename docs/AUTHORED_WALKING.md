# Authored exploration walking correction — 2026-10-17

The BattleTech demo and other authored projects now use the original game's
compact exploration formation and doorway contact rules. The original campaign
keeps its existing movement adapter and primary comparison corpus.

## What was wrong

- Follower movement checked a legal authored tile, then consulted the CHI
  generated world's deep-water boundary at the same arbitrary world coordinate.
  A mech could stop at an invisible boundary while the cursor kept walking.
- Entrances tested only exact party-cursor equality. The visible mech's ground
  anchor is a different coordinate, and a following member could never trigger
  a door itself.
- The asset-free renderer placed mounted pilots using stale infantry positions,
  rather than the saved positions of their machines. Its leader also used the
  infantry animation frame for the mech.
- Declining an authored entry prompt discarded the pending movement even when
  the step was legal.

## Original evidence and resulting behavior

Original `0000:0BC9..0D30` rebuilds the compact formations from the cursor and
separate infantry/mech offset tables. Passengers do not consume an infantry
position. The first mech's ground anchor is two half-steps north of the cursor;
the second is four half-steps south. These are collision/drawing coordinates,
not the top of the mech artwork.

`town-formation-primary.*` records 40 live original observations and 160 exact
member positions. `formation-collision-primary.*` contains 1,920 original
whole-party decisions. `formation-entrance-primary.*` contains 480 original
doorway decisions. Their executable hashes, prerequisites and intercepted
UI boundaries remain recorded with the fixtures. See the earlier
[town formation evidence](M4_FIDELITY_EVIDENCE.md#town-formations-combat-anchors-and-parked-vehicles--2026-10-14).

The authored adapter now calls the shared member entrance routine for every
pending half-step. It scans foot soldiers and then mechs in compact order.
Infantry needs exact contact; a mech can touch an entrance at its ground anchor
or either horizontal neighbour. Each member's door check precedes its own wall
test, and an earlier blocked member stops the scan. Every member's footprint
must fit before the whole formation moves. The original active/parked record
distinction continues to apply.

After an accepted authored step, active positions are assigned directly to the
verified compact offsets. Separate detour searches cannot strand individual
machines. A nearby separated mech from an existing save rejoins on the next
accepted step, without needing to open the menu. Existing fallback recovery
remains for invalid/scattered historical positions and scene returns; exact
DOS recovery from malformed saves is not claimed.

The main original keyboard loop repeats movement/formation for the chosen
1/2/4 half-steps, then advances the gait once (`0000:0070..009A`, `00EC..00FA`,
`231D`). Authored walking retains that cadence, including diagonal and blocked
attempts. Answering No resumes only a legal pending half-step and does not add
another gait frame. A held prompt saves the pending direction through the
already serialized facing field. No new save layout or package edit is needed.

The asset-free frontend now draws infantry and vehicles separately. Each active
mech uses its own saved anchor and pilot gait, including unassigned purchases;
passengers do not duplicate sprites and missing/parked vehicles remain absent.

## Verification

`authored-formation-movement` tests controlled loaded scene copies, never source
assets. It covers four mechs, mixed infantry/mechs, 1/2/4 steps, diagonals,
16-half-step boundary crossings, a detached legal follower, blocked outer mech
footprints, exact foot contact, follower-mech door contact, blocked earlier
members, recruited-NPC suppression, gait and byte-identical saved Yes/No
continuations. It independently checks the original offset values used by its
wall/door placements.

The three quest tests now choose ordinary input routes from the shared collision
and contact API. They continue to save/restore throughout exploration, dialogue,
combat and endings. Their route helper never changes story flags, position,
health or results. Separate movement tests establish the semantics the robot
uses to choose its inputs. The independent renderer also has pixel regressions
for stale pilot positions, moving mech anchors, passengers and absent vehicles.

| Check | Result |
| --- | --- |
| Full native CTest | **69/69**, 44.40 s |
| Full Python tools suite | **69/69**, 3.14 s |
| Focused Windows/Wine CTest | **5/5**, 16.49 s |
| Focused ASan/UBSan/LeakSanitizer | **5/5**, 1.73 s |
| Linux BattleTech SDL | **12/12** held F5/F9 screens, real walking keys with matching headless gait/pixels, complete two-contract route |
| Windows/Wine BattleTech SDL | **12/12** held F5/F9 screens, real walking keys with matching Linux headless gait/pixels, complete two-contract route |
| Linux independent SDL | **9/9** held F5/F9 screens and complete quest |
| Windows/Wine independent SDL | **9/9** held F5/F9 screens and complete quest |

Focused platform tests cover authored walking, both demos, the earlier authored
adventure and original party setup. The full native suite also retains the
original movement/doorway primary comparisons. Native and Windows compilation
are warning-free; the sanitizer build retains the two previously documented
original-renderer sign-conversion warnings. No runtime sanitizer error occurred.

Reproduce:

```sh
ctest --test-dir build -R 'authored-formation-movement|battletech-demo-contracts|authored-adventure-continuations|independent-game-complete' --output-on-failure
python3 tools/native_smoke.py --battletech-demo-only
python3 tools/native_smoke.py --windows --battletech-demo-only
python3 tools/native_smoke.py --independent-only
python3 tools/native_smoke.py --windows --independent-only
```

Logs and inspected screenshots are in ignored `work/authored-movement-*.log`
and `work/authored-walking-*.png`. Verification covers the stated authored and
existing primary cases, not every original game branch or physical Windows
hardware. All package JSON/assets remain unchanged, including the BattleTech
demo's strict content fingerprint, so its existing project saves remain usable.
The reference guard verifies all **1,287** entries unchanged in content, mode
and modification time.
