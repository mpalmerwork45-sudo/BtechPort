# Project status — M2e review, 2026-10-11

**M0, M1 and bounded M2a–M2e are complete. Stop here for milestone review.**
The Armor Shop and Weapons Shop now support one verified purchase each from
normal MAP1 exploration: a 50 C-bill flak vest and a 2 C-bill knife. Original
BLD text, Yes/No, separate remembered menus, cash/equipment changes, insufficient
funds and outdoor return are implemented. Earlier NPC/Citadel routes still pass.
The campaign and remaining M2 systems are unfinished.

## Milestones

| Gate | Result |
|---|---|
| M0 | Research/inventory/runtime audit; C11/SDL2 decision |
| M1 | Native MAP1 exploration and terrain collision |
| M2a | Citadel entry, six Hall screens and exit |
| M2b | First Katrina conversation and repeat denial |
| M2c | Verified native Talk/Done/reply; explicit controlled checkpoint |
| M2d | MAP1 NPC travel; conversation reachable through exploration |
| M2e | Two shop purchases, confirmations, local allowance and persistence |
| Proposed M2f | One ComStar banking deposit/withdrawal loop, following a bounded audit |
| Remaining M2 | Wider inventory/shops, day/training, maps/world and campaign foundations |
| M3–M5 | Verified tactical combat; original campaign; optional separate enhancements |

## Actual working result

```sh
./scripts/build.sh
./build/btech-port --data "Original DOS"
./build/btech-port --smoke-shops --replay tests/fixtures/reference-shops.actions
./build/btech-port --replay tests/fixtures/citadel-arrival.actions
./scripts/test.sh
python3 tools/native_smoke.py --shops-only
./scripts/test-sanitize.sh
```

The native shop replay takes about 98 seconds and closes automatically; omit
`--smoke-shops` for an interactive window after both purchases. It walks to
Armor first, waits for the ordinary 35→50 allowance, buys the vest, walks to
Weapons, receives a fresh 15-credit allowance, buys the knife and returns to
(32,44) with 13 credits, weapon type 1, armor type 1 and protection 25.

Arrows move/select; Enter/Space confirms/continues; Backspace declines entry or
recovers unsupported choices; F3 diagnostics, R restart, Esc exit. Other goods,
repair and shop Talk stop visibly. Backspace restores the original building's
main menu after rollback; this recovery is a prototype convenience. Class still
faults at F5 04. No save/load UI or original GAME compatibility is claimed.

Runtime resources are authentic MAP1/BTTLTECH/CITADEL/ARMOR/WEAPON plus an ignored,
reproducible EXE dialogue cache prepared by the build. Python supports conversion
and tests; the C game has no Godot/.NET/reference runtime dependency. The core
and renderer run headlessly. [README](../README.md) and [TESTING](TESTING.md)
provide controls, paths and commands.

## Evidence, verification and limits

**VERIFIED in scope:** 121 original shop checkpoints across two unmodified DOS
runs, covering cursor/party, cash, equipment, result byte, menu memory, exact
BLD text ranges/hashes and complete decrypted scripts in RAM. The second run
also declines both purchases and attempts a second vest at zero cash: the
original response clears the result flag, leaves equipment/cash intact and exits.
The longer boundary run ends with 28 credits after another outdoor allowance.

Original EXE instructions establish unsigned 32-bit purchase comparison and
one-member equipment assignment. D374/D378/D37C are investment balances, not
inventory. F5 09 buys armor, F5 0B buys weapons and F5 0A displays cash. D316
becomes one in the Armor Shop too; it is not exclusively a Citadel visit flag.
See [shop evidence](M2_SHOPS_EVIDENCE.md) and the updated [audit](RESEARCH_AUDIT.md).

PASS: four CTest suites, 420 core/corpus, 94 script, 1741 NPC and 30928 shop
assertions; four Python tests; all prior differential routes and both shop
routes. Core persistence restores identical continuation at every one of the
6137 shop replay ticks. Private-X11 SDL completes the 3064-tick shop/tail route;
its entire final canonical state equals the headless input replay. Headless
ASan/UBSan/LeakSanitizer pass both shops and earlier milestones. SDL/backend
is not sanitizer-instrumented. Mixed-case menu/confirmation frames were inspected.
All 88 original file hashes match and **1287 reference entries remain unchanged**,
including reference Git metadata, modes and mtimes. No failing gate checks remain.

Earlier M2d comparisons still cover 570 complete original NPC frame steps,
two arrivals and 56 natural conversation checkpoints; 68 capture gaps with
missing player movement are explicitly skipped. The shop route's idle ticks
reproduce captured outdoor loop-counter decrements. They do not reconstruct
exactly when NPC frames occurred between individual road keys. **INFERRED:**
unobserved local behavior and broader flags/contexts. **APPROXIMATE:** native
cadence, font/layout, sprites/markers and edges. **UNKNOWN/deferred:** investments,
cap progression, day/countdowns, remaining goods/repair/party assignment, world,
combat, animation/audio, original saves and later campaign. The local allowance
uses zero investments and cap 50, tests pre-update cash, adds 15 without clamping,
and preserves the three-account RNG draw schedule. It is not a general economy.

## Work, provenance and next gate

Added independent shop services, variable menus/confirmation/positioned cash
text, two authentic resource loads, factual fixtures, whole-script DOS automation,
headless/native differential verification and persistence/boundary tests.
**BTP6 is a 320-byte internal encoding**, preserving prior fields and adding
credits/cap/equipment, sparse shop refusal byte, remembered menus, confirmation,
text positions/cash and transaction rollback. BTP1–BTP4 migration disables travel;
BTP5 retains travel and migrates its known unspent allowance marker to 35 or 50
credits. Legacy files never stored equipment; migration supplies the baseline.

The supplied v1.03 BTECH.EXE collection remains 88 files/641365 bytes, including
six 3913-byte saves and three backups. [Inventory](ORIGINAL_FILES.md) and the
[manifest](original-manifest.json) remain authoritative. Proprietary resources,
text, RAM, screenshots, caches and dependencies stay ignored. No substantial GPL
implementation was copied/translated; distribution or clean-room status is not
claimed. Local commits record M2e research (`0386b7a`) and implementation/tests
(`37ef639`), followed by this review. No pushes or Git configuration changes.

Smallest proposed next gate: **M2f, one ComStar banking deposit/withdrawal loop**.
Audit its original BLD/native handlers, then verify cash and one actual investment
balance plus return/persistence. This would connect the two shops to the next
bounded economic action; full day/training and combat remain separate gates.
