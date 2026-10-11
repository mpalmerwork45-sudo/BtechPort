# Project status — bounded M3a complete, 2026-10-12

**M0, M1, M2a–M2m and bounded M3a are complete.** Three MechWarrior assignments
are playable through reporting and their rewards. The third supports manual
movement, weapon orders, targeting, damage/criticals, heat/ammunition, victory
and withdrawal. Its training shell stays stationary as requested. Original
movement arrows show the planned steps before confirmation and during execution.
The wider tactical combat system and original campaign remain unfinished.

## Milestones

| Gate | Result |
|---|---|
| M0 | Research/inventory/runtime audit; C11/SDL2 decision |
| M1 | Native MAP1 exploration and terrain collision |
| M2a | Citadel entry, six Hall screens and exit |
| M2b | First Katrina conversation and repeat denial |
| M2c | Native Talk/Done/reply; explicit controlled checkpoint |
| M2d | MAP1 NPC travel; conversation reachable through exploration |
| M2e | Two shop purchases, confirmations, allowance and persistence |
| M2f | ComStar investments/returns, boundaries and both shops' Talk |
| M2g | Internal save slot, integrity, native controls and continuation |
| M2h | Paid classes, tuition/refusals, cooldown and re-enrolment |
| M2i | Original walking sprites, persistent gait and mech preview |
| M2j | First MechWarrior mission/sleep; all goods; lounge; diagonals |
| M2k | Rubble pickup/carrying/return; all loan choices and objectives |
| M2l | Ordinary two-mission/rest loop through the third briefing |
| M2m | O0/O8 playback, original font/borders and animation persistence |
| M3a | Manual third-assignment weapons combat, stationary shell, route arrows, victory/report and 500-cap reward |
| Proposed M3b | Recover and verify kicking/physical attacks in this encounter |
| Proposed M3c | Audit and implement the fourth assignment's combat |
| Remaining M2/M4 | Party/repair, world/maps and wider campaign progression |
| M3–M5 | Wider verified tactical combat; original campaign; optional enhancements |

Later assignments still stop visibly. Rick's natural invitation requires
fifth-assignment success; the earlier controlled lounge branch retains its
explicit prerequisite. No earlier campaign unlock is invented.

## Play and verify

```sh
./scripts/build.sh
./build/btech-port --data "Original DOS"
# Open at the third loan-mech menu after ordinary earlier gameplay inputs:
./build/btech-port --replay tests/fixtures/ordinary-rubble-story.actions
# Watch the complete route quickly, then close automatically:
./build/btech-port --smoke-replay --smoke-fast --replay tests/fixtures/ordinary-combat.actions
./scripts/test.sh
python3 tools/native_smoke.py --combat-only
./scripts/test-sanitize.sh
```

In combat, choose No for computer control, select the message/graphics options,
then Walk/Run/Jump to plot a destination with arrows/keypad and confirm with
Enter. White arrows show the next turn's steps; the yellow box marks the
confirmed destination. Use Weapons assigns a weapon to the Locust shell;
Done returns to orders and Begin Fight executes a turn. Weapon orders persist.
After destruction, walk back to x<=60,y=73..79 and report to the instructor.
Success advances the assignment counter to 3 and raises the allowance cap to
500; Flee retains the prior progress/cap. Kick and computer control currently
show an explicit unsupported-command notice.

Normal play uses 32ms ticks. The accelerated **5219-tick SDL route measured
4.95 seconds versus 167.01 seconds** at normal pacing, about 34 times faster.
Every input, logical tick and render is retained. Short real-key/save checks
keep normal pacing. Reference research uses a bounded original-instruction
oracle, avoiding repeated long DOS sessions. See [testing commands](TESTING.md).

Arrows/keypad move/select; perpendicular arrows form diagonals. Enter/Space
confirms; Backspace declines/recovers; F3 toggles diagnostics, R restarts and
Esc exits. Bank digits, Backspace, Escape-clear and Enter keep their editor
meanings. F5/F9 save/load `work/player-save.btp`; `--save-file FILE` selects
another slot. Failed loads preserve the session.

## Evidence and verification

The original DOS audit reaches target destruction and the success dialogue
without state/RNG writes. **VERIFIED, bounded** instruction comparisons include
2099 dice/range/movement-point/critical cases, 896 shots, 779 navigation cases
and 648 heat-cleanup cases. A separate out-of-grid LOS case checks the port's
visible diagnostic rather than asserting original parity. **35 controlled
original turns** match positions, directions, heat, full mech-record hashes
and RNG through destruction, with original target AI enabled explicitly in
the comparison harness. The playable stationary shell is the user's requested
change from that observed DOS behavior. See [M3a evidence](M3_COMBAT_EVIDENCE.md).

A **5214-input ordinary native replay** completes both earlier assignments,
sleep, third combat, reporting and exit without state/RNG edits. **20
fresh-process save continuations** include route preview/confirmation, target
selection, firing indication, turns, victory and reporting. The C integration
suite checks **20063 assertions**, including continuation at every input,
stationary-target invariants, all eight arrow directions against the original
font, three loan/withdrawal paths and malformed saves. The end-to-end victory
replay uses the Locust; the two other loans have launch/withdrawal coverage.

PASS: **16 CTest suites**, four Python tests, all historical headless
comparisons, and headless **ASan/UBSan/LeakSanitizer**. The SDL/backend itself
is not sanitizer-instrumented. Native X11 combat replay matches complete
inputs, final state and pixels; six real-time F5/F9 checks restore computer
prompt, route preview/confirmation, weapons, target and turn execution with
exact headless continuation/pixels. Earlier M2 comparisons, 175 disk snapshots,
ANM/font/border/dream checks and their documented limits remain covered.

The existing long-wait NPC/RNG gap remains: the 181-checkpoint M2 comparison
uses three explicit later-quiz RNG prerequisites. Whole-route original/native
RNG equality is not established by the ordinary native playability replay.

## Persistence, provenance and limits

Current saves use **BTPE/v14**, a **1024-byte payload** in the 16-byte BTS1
length/CRC envelope (**1040-byte file**). Bytes 512..895 contain combat records,
orders, paths, UI and turn state; byte 878 adds the firing-indicator countdown.
BTPD/v13 migrates with no active indicator. Its previously plotted target
paths cannot move the shell after loading. BTPC/v12 and all earlier supported
migrations remain tested. Original DOS GAME compatibility is unimplemented.

Both supplied trees match **1287** guarded content/mode/mtime entries, and all
88 original hashes match. Only the known external editor's reference Git
metadata addition/timestamps were restored to the baseline. No research files,
assets or baseline were changed. Captures, RAM, owner-derived BTC1/BTT6 caches
and local dependencies stay ignored. No substantial GPL source was copied or
translated into the independent C runtime; README acknowledges the research
contributors. Local commits include `97e82bc` (audit/rules), `99197f9`
(playable checkpoint) and `97b3c17` (stationary shell/arrows/verification).
The milestone review is committed separately. No pushes.

**INFERRED:** broader mech-rank semantics, Run/Jump turn behavior beyond the
point/cost routines, and unobserved unit/world contexts. **APPROXIMATE:** UI
layout/status/Scan/messages, native cadence, map edges and the short firing
indicator; exact original weapon animations remain deferred. Only one movement
destination is stored, rather than the original multi-waypoint queue.
**UNKNOWN/deferred:** kicking, general computer control, terrain ignition,
wider combat/AI and later assignments, world/party/repair, natural Rick unlock,
terrain animation, audio, Windows and complete campaign/timing/pixel parity.
Unsupported terrain fire and LOS beyond the verified working grid produce
visible diagnostics before consuming attack ammunition or RNG.
