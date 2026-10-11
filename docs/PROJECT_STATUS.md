# Project status — M2f review, 2026-10-11

**M0, M1 and bounded M2a–M2f are complete. Stop here for milestone review.**
ComStar now supports its original three investment accounts, account inspection,
buying/selling, numeric entry, boundary responses and return to MAP1. Outdoor
allowances and investment changes follow the audited local rules. Talk works in
both shops, including empty rooms, multiple occupants, Done and original replies.
Earlier Citadel, NPC and two-shop purchase routes continue to pass. The campaign
and remaining M2 systems are unfinished.

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
| M2f | ComStar investments/returns, banking boundaries and Talk in both shops |
| Proposed M2g | Player-facing save/load for the verified internal state |
| Remaining M2 | Wider inventory/shops, day/training, maps/world and campaign foundations |
| M3–M5 | Verified tactical combat; original campaign; optional separate enhancements |

## Actual working result

```sh
./scripts/build.sh
./build/btech-port --data "Original DOS"
./build/btech-port --smoke-replay --replay tests/fixtures/reference-bank.actions
./build/btech-port --replay tests/fixtures/reference-bank-rates.actions
./build/btech-port --shop-talk-checkpoint armor
./build/btech-port --shop-talk-checkpoint weapon
./scripts/test.sh
python3 tools/native_smoke.py --m2f-only
./scripts/test-sanitize.sh
```

The first banking replay runs ordinary movement, buys 30 DefHes from the initial
35 cash, sells 7, checks excessive/zero/unfunded requests, sells the remainder
and returns outdoors with 35 cash and empty investments. `--smoke-replay` sends
the entire input sequence through SDL and closes after about 13 seconds. Omit it
to continue interactively. The rates replay opens on accounts showing cash 18
and investments `[31,0,2]`, after the verified two-wrap outdoor wait.

The two `--shop-talk-checkpoint` commands are explicitly labeled handler demos:
each starts inside that shop with two controlled occupants and travel disabled.
Choose **Talk to others**, select a name or Done, and continue the reply. In
ordinary gameplay, occupancy comes from NPC travel; the demo is never injected.
The existing `--smoke-shops --replay tests/fixtures/reference-shops.actions`
route still buys the flak vest and knife and returns with 13 cash.

Arrows move/select; Enter/Space confirms/continues; F3 diagnostics, R restart,
Esc exit. **Bank amounts use digits, Backspace to erase, Escape to reset to 0,
and Enter to submit.** Space does not submit an amount. Elsewhere Backspace
declines entry or recovers unsupported choices. Other goods, repair and Class
still fault visibly; recovery rolls back the failed choice before restoring the
building menu. No save/load UI or original GAME compatibility is claimed yet.

Runtime resources are authentic MAP1/BTTLTECH/CITADEL/COMSTAR/ARMOR/WEAPON and an
ignored, reproducible EXE dialogue cache. Python supports conversion/tests; the
C game has no Godot/.NET/reference runtime dependency. [README](../README.md)
and [TESTING](TESTING.md) provide controls, paths and commands.

## Evidence, verification and limits

**VERIFIED in scope:** 160 new original checkpoints: 33 banking, 29 outdoor-return
economy, 28 empty Armor and 48 empty Weapons route checkpoints, plus 11 occupied
Talk checkpoints per shop. Ordinary bank/empty-shop paths use unpatched DOS
gameplay. Occupied-shop checks explicitly control two NPC occupancy pairs and
the result byte in a working emulator, with before/after audits. They establish
the handler under those preconditions, not a naturally reached occupied-shop
state. Text hashes, complete decrypted BLD bytes in RAM, original native string
bytes, party/cursor, cash/accounts, result flags and menu memory all pass.
See [banking and Talk evidence](M2_BANKING_EVIDENCE.md).

The economy trace compares **459 complete outdoor frame steps / 460 samples**,
including all eight NPCs, loop counter, RNG, search/bias, cash and three balances.
It observes `[30,1,1]` with cash 3 becoming `[31,0,2]` with cash 18; total assets
51 then suppress the next allowance/returns. Primary instructions establish
unsigned transfers, clipped requests, seven-digit editing and arithmetic rules.
The trace also exposed an NPC collision error: the human cadet occupies one
half-coordinate, while the wider footprint branch applies to other unit slots.
The corrected helper passes both this full trace and the earlier NPC corpus.

PASS: five CTest suites; 420 core, 94 script, 1741 NPC, 30928 shop and 78178
bank/Talk assertions; four Python tests; all prior differential routes and all
new bank/shop-Talk routes. **All 7297 new replay ticks restore, re-encode and
continue identically**, including transaction input and replies. Five new private
X11 checks cover bank, rates, both occupied-shop Talk routes and amount editing
through actual SDL events. Complete final JSON equals each headless recorded
replay; Escape clears an amount without closing the window. Headless
ASan/UBSan/LeakSanitizer pass. SDL/backend is not sanitizer-instrumented.
Mixed-case account, amount, receipt, clipped/zero transaction and shop Talk
frames were inspected. All 88 original hashes match; **1287 reference entries
remain unchanged**, including reference Git metadata, modes and mtimes.

Earlier M2d still covers 570 complete NPC frame steps, two arrivals and 56 natural
conversation checkpoints; its 68 gaps with missing player movement are reported
and skipped. Earlier M2e still covers 121 original shop checkpoints and 6137
restored purchase-route ticks. Road replay idles reproduce observed outdoor
counter intervals, without recovering every intermediate original NPC position.
**INFERRED:** unobserved local paths and broader campaign contexts.
**APPROXIMATE:** font/layout, sprites/markers, native cadence and edges.
**UNKNOWN/deferred:** cap progression, full day/countdowns/training, other goods,
repair/party assignment, world, combat, animation/audio, original saves and
Windows. The economy is verified in the MAP1 cadet context with local cap 50;
it is not a claim about the full campaign economy.

## Work, provenance and next gate

Independent bank/economy services extend the bounded BLD interpreter rather than
replace it with scripted screens. Native F5 06/07/08 implement account display,
buy and sell; both shops use their authentic F5 0C Talk paths. The BTT2 cache
contains 43 original strings in 1448 bytes with source/address provenance.

**BTP7 is a 384-byte internal encoding**, preserving earlier field offsets and
adding three balances, their rollback copies, suspended bank input/result and
account-display state. BTP6 migrates with empty accounts and no pending bank
service while preserving cash/equipment. Earlier migrations retain their
documented limits. This format is tested internal persistence, not GAME import
or an implemented player-facing save feature.

The supplied v1.03 BTECH.EXE collection remains 88 files/641365 bytes, including
six 3913-byte saves and three backups. [Inventory](ORIGINAL_FILES.md) and the
[manifest](original-manifest.json) remain authoritative. Proprietary resources,
text, RAM, screenshots, caches and dependencies stay ignored. No substantial
GPL implementation was copied/translated; distribution or clean-room status is
not claimed. Local commits record M2f research (`562fed8`) and implementation/
tests (`578efab`), followed by this review. No pushes or Git configuration changes.

Smallest proposed next gate: **M2g, player-facing internal save/load**. Preserve
exploration, NPC/RNG/economy and paused dialogue or transaction input across a
restart; check file failure handling and identical continuation. Original GAME
compatibility needs a separate DOS load/save audit. Day/training remains the
next larger campaign foundation after that convenience.
