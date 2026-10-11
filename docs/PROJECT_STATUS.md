# Project status — M2g/M2h complete; sprite follow-up in progress, 2026-10-11

**M0, M1 and bounded M2a–M2h are complete.** M2g adds native internal save/load.
M2h adds the first verified paid Class → skill increase → outdoor cooldown →
re-enrolment loop. The user has now also requested authentic player, NPC and
mech sprites; that rendering audit is the active follow-up.

## Milestones

| Gate | Result |
|---|---|
| M0 | Research/inventory/runtime audit; C11/SDL2 decision |
| M1 | Native MAP1 exploration and terrain collision |
| M2a | Citadel entry, six Hall screens and exit |
| M2b | First Katrina conversation and repeat denial |
| M2c | Native Talk/Done/reply; explicit controlled checkpoint |
| M2d | MAP1 NPC travel; conversation reachable through exploration |
| M2e | Two shop purchases, confirmations, local allowance and persistence |
| M2f | ComStar investments/returns, banking boundaries and Talk in both shops |
| M2g | One internal save slot, native controls, integrity and restart continuation |
| M2h | Paid personal-skill classes, tuition/refusals, outdoor cooldown and re-enrolment |
| Active follow-up | Original player/NPC/mech sprite data, selection and masking audit |
| Remaining M2 | MechWarrior training/day progression, wider inventory/shops, maps/world and campaign foundations |
| M3–M5 | Verified tactical combat; original campaign; optional separate enhancements |

## Play and verify

```sh
./scripts/build.sh
./build/btech-port --data "Original DOS"
./build/btech-port --smoke-replay --replay tests/fixtures/reference-class-funded.actions
./build/btech-port --replay tests/fixtures/reference-class-funded.actions
./scripts/test.sh
python3 tools/native_smoke.py --school-only
./scripts/test-sanitize.sh
```

The course demonstration follows ordinary inputs: invest the initial 35 at
ComStar, wait, sell 72, return to Citadel with 87, pay tuition 75, improve the
first skill, observe the immediate enrolment refusal, wait outdoors and return
to the next offer. The SDL replay takes about 99 seconds and closes. Omitting
`--smoke-replay` opens an interactive window after this route, with rank 1 and
27 cash. The next tuition is 200. No money or mission progress is injected.

Arrows move/select; Enter/Space confirms/continues; F3 toggles diagnostics,
R restarts and Esc exits. Bank amounts use digits, Backspace erasure, Escape
to clear to zero and Enter to submit. Elsewhere Backspace declines entry or
recovers an unsupported choice.

**F5 saves and F9 loads** `work/player-save.btp`. `--save-file FILE` selects a
slot; `--load FILE` restores before a replay; `--save FILE` writes on successful
exit. Partial amounts, dialogue, skill progress and course pauses survive.
Failed loads preserve the session. Loading while recording is visibly refused
because the logical action log cannot represent a rewind.

The earlier bank, shop, Hall/Katrina and NPC routes remain playable. Other goods,
repair, additional interiors and campaign progression remain incomplete.
Unsupported operations fail visibly and recover the failed choice's state.
Resources are loaded from the original files plus a reproducible local EXE text
cache; the C runtime has no Godot/.NET/reference runtime dependency.

## Evidence and verification

**M2g VERIFIED implementation:** 137 disk round-trip snapshots from authentic
replay phases and input states, with identical continuation under every logical
action; 31 fresh-process save/restart states, each compared through another
1024 ticks. These current totals include the M2h extension. Malformed, truncated,
wrong-CRC, semantically invalid and missing files are rejected. Failed writes
preserve the earlier slot. Native F5/F9 restores a partially typed amount and
continues the same transaction. See [save evidence](M2_SAVE_EVIDENCE.md).

**M2h VERIFIED in scope:** 64 original checkpoints (15 first-visit/refusal and
49 ordinary funding/course/cooldown checkpoints), exact BLD/native text hashes,
cash, skills, flags, selectors and outdoor timer. The original pays 75 from 87,
raises skill `[0,0,0]` to `[1,0,0]`, sets cooldown 255 and refuses another class
until it reaches zero. The next offer costs 200. All 3271 replay ticks restore,
re-encode and continue identically. Two additional read-only captures compare
460 complete outdoor frames / 462 samples across all 70 recorded NPC, RNG,
search, cash and account fields. Countdown/rank parity is established by the
separate RAM checkpoints, not added retroactively to that observer.
See [training evidence](M2_TRAINING_EVIDENCE.md).

Primary instructions establish all three subjects, tuition `75 + 125 * rank`,
exact debit, insufficient-funds and mastery refusals. Boundary tests cover all
subjects/ranks, high-word cash subtraction, Withdraw, rollback and invalid
states. Only the first subject's first paid course is claimed as live original
paid-course parity. Personal Class leaves the MechWarrior mission counter at
zero; it does not establish mission completion or barracks sleeping.

PASS: seven CTest suites; 421 core, 95 script, 1741 NPC, 30928 shop, 78178
bank/Talk, 11972 save-file and 59197 school assertions; four Python tests;
all prior/new differential routes. Headless ASan/UBSan/LeakSanitizer pass.
The native 3093-tick course demonstration produces exactly the recorded inputs
and complete final headless JSON; native F5/F9 also passes. SDL/backend is not
sanitizer-instrumented. Course menus/completion/refusal frames were inspected
for readable mixed case. Original font/layout/cadence remain approximate.

Earlier evidence remains: 570 complete NPC frames/two arrivals, 56 natural
conversation checkpoints, 121 shop purchase checkpoints, 160 bank/shop-Talk
checkpoints and 459 bank economy frames. The older NPC trace's 68 movement gaps
remain explicitly skipped. Occupied-shop handler tests use controlled
preconditions, while the new funded Class route uses ordinary gameplay only.

## Persistence, provenance and limits

The current **BTP8 payload is 416 bytes**, wrapped in a 16-byte BTS1 file header
with length and CRC32. It adds ranks, their rollback copies and the paused course
transcript context. Existing M2g BTP7 saves migrate to zero skill ranks, retaining
their stored gameplay state. Older migrations keep their documented limitations.
This is internal persistence; original 3913-byte GAME compatibility, power-loss
durability and Windows behavior remain unverified.

The **BTT3 dialogue cache** has 55 original strings in 1889 bytes, including
source hashes and address provenance. It is generated locally and stays ignored.
Both supplied reference trees match all **1287 guarded entries**, including
content, modes, mtimes and reference Git metadata. All 88 original file hashes
match. Proprietary assets, RAM, screenshots, caches and dependencies stay out of
commits; no substantial GPL source was copied/translated into the runtime.

Local commits: `d77e9c7` (M2g save/load), `175ec98` (M2h original audit),
`1189da2` (M2h implementation/tests). No pushes or Git configuration changes.

**INFERRED:** unobserved movement and broader campaign contexts.
**APPROXIMATE:** current markers/imagery, independent mixed-case font/layout,
native cadence and map edges. **UNKNOWN/deferred:** MechWarrior missions,
barracks sleep, later day/cap progression, remaining goods/repair/party/world,
combat, animation/audio, original saves and Windows. After the requested sprite
work, the next campaign gate should audit the first MechWarrior assignment and
its return/sleep conditions before implementing a bounded mission loop.
