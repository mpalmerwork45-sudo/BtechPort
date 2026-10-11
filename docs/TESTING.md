# Build, verification and original oracle — M2h, 2026-10-11

## Native commands

Run from `/home/mpalmer/BtechPort`:

```sh
./scripts/build.sh
./build/btech-port --data "Original DOS"
./build/btech-port --replay tests/fixtures/citadel-hall.actions
./build/btech-port --replay tests/fixtures/citadel-katrina.actions
./build/btech-port --replay tests/fixtures/citadel-arrival.actions
./build/btech-port --smoke-shops --replay tests/fixtures/reference-shops.actions
./build/btech-port --smoke-replay --replay tests/fixtures/reference-bank.actions
./build/btech-port --replay tests/fixtures/reference-bank-rates.actions
./build/btech-port --shop-talk-checkpoint armor
./build/btech-port --shop-talk-checkpoint weapon
./build/btech-port --conversation-checkpoint --replay tests/fixtures/citadel-talk.actions
./scripts/test.sh
./scripts/test.sh --x11
./scripts/test-sanitize.sh
```

The build script uses our proven EXEPACK reader through `tools/prepare_talk.py` to generate ignored `work/talk-data.bin` and its provenance sidecar from the audited original executable. BTT3 has 55 strings in 1889 bytes (292-byte header, 1597-byte blob). It then selects installed host GCC 15.2/CMake and clears inherited Conda compiler/linker flags for its child commands. Direct builds with this shell's older Conda linker fail on host libc's `.relr.dyn`. No shell or Git configuration changes or network calls are needed. Outputs are `build/btech-port`, `build/btech-headless`, `build/btp-tests`, `build/btp-script-tests`, `build/btp-npc-tests`, `build/btp-shop-tests` `build/btp-bank-tests`, `build/btp-save-tests` and `build/btp-school-tests`. Python is required for conversion/testing, not by the running C game.

The runtime reads MAP1, BTTLTECH, CITADEL, COMSTAR, ARMOR and WEAPON directly, plus the local EXE text cache. For another resource/cache location, run `python3 tools/prepare_talk.py --data DIRECTORY --output CACHE` and pass `--data DIRECTORY --dialogue-data CACHE` to the executable. Wrong source/image hashes, malformed caches and missing files fail visibly. See [Talk provenance](M2_TALK_EVIDENCE.md) and [banking evidence](M2_BANKING_EVIDENCE.md).

SDL2 2.32.4 runtime is installed; development headers are under ignored `local-deps/sdl2/`. Conventional SDL2 installations also work; `SDL_GetTicks64` requires 2.0.18 or later. With a normal compiler environment:

```sh
python3 tools/prepare_talk.py
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build
```

Core/data/pixel tests build without SDL using `-DBTP_FRONTEND=OFF`. Synthetic CTest suites can build without original assets/cache; corpus/native checks require them. Windows portability remains **UNKNOWN** until tested.

Arrows move/select; Enter/Space confirms/continues; Backspace declines entry or recovers unsupported choices; F3 toggles diagnostics; F5 saves; F9 loads; R restarts; Esc quits. In bank amounts, digits type (maximum seven), Backspace erases, Escape clears to 0 without quitting/submitting, and Enter submits; Space is ignored. The 32ms step, key repetition, delays and flushing are **APPROXIMATE**. Replays accept lowercase `up`, `down`, `left`, `right`, `idle`, `accept`, `cancel`, `0`–`9` and `clear`, one per line:

```sh
./build/btech-port --record work/my-walk.actions
./build/btech-headless --replay work/my-walk.actions --trace --frame work/my-walk.ppm
```

Records include idle ticks. Restart is visibly refused while recording because reset is not a replay action. Unknown actions fail. The VM supports the bounded Citadel, bank and two-shop menus, Hall, Katrina/repeat, `F5 0C` local Talk, F6 Yes/No, positioned cash/account text and exit/re-entry. Bank native actions `06/07/08` handle accounts/buy/sell with serializable company selection and amount entry. Combat class stops at `F5 04` after its introduction. Other native actions and nonlocal Talk contexts remain explicit faults. Failed choices roll back story/result/cash/investment/equipment writes across restored pauses; Backspace recovers to the menu. This recovery is a prototype control, not original behavior. Headless faults return failure and can still write diagnostic frames.

## ComStar and both shops' Talk oracle

```sh
python3 tools/reference_session.py --script tools/reference-bank.json
python3 tools/reference_session.py --script tools/reference-bank-rates.json
python3 tools/reference_session.py --script tools/reference-armor-talk.json
python3 tools/reference_session.py --script tools/reference-weapon-talk.json
python3 tools/verify_m2f.py
python3 tools/verify_m2f.py --live
build/btp-bank-tests "Original DOS"
python3 tools/native_smoke.py --m2f-only
python3 tools/native_smoke.py --bank-input-only
```

The committed bank/rates fixtures use ordinary inputs and an unpatched working
copy. They compare 33 + 29 checkpoints, all three balances and exact original
text hashes. `bank-frames.csv` records 460 stable samples during the fixed-player
outdoor wait; every one of its 459 complete steps matches cash/accounts, cap,
all eight NPCs, phase/timer/RNG/search/bias. Both wraps match: `[30,1,1]` plus
cash 3 becomes `[31,0,2]` plus cash 18, then assets 51 suppress the next updates.
Original adjacent-human collision establishes a single half-coordinate footprint.

Shop Talk has 28 Armor and 48 Weapons ordinary-route/empty checkpoints, then 11
controlled occupied-handler checkpoints per shop. Each explicit precondition
places slots 1 and 4 in the room with timers 5/7 and result 91; a before/after
audit records exactly the occupancy/result writes in the child emulator. No
resource, executable or save is patched. Default gameplay uses ordinary NPC
travel. Controlled snapshots establish name ordering, Done, remembered selection,
both replies/result clearing and return; they do not prove natural occupied-shop
arrival. Outdoor post-exit timers are excluded from that disabled-travel demo.

`--live` rechecks all 160 checkpoints against the ignored original RAM exports,
full BLD/native text bytes and cursor/party. To export a new run, use
`--export bank|bank-rates|armor-talk|weapon-talk --reference-run DIRECTORY`;
do not overwrite factual fixtures until its observation/projection is reviewed.
The original numeric editor buffer after a receipt may contain formatted cash,
not the earlier typed amount. Recorded keys/frames establish the latter.

The bank C suite restores/re-encodes/continues all 7297 ticks of six replays and
checks synthetic arithmetic/input/atomic-validation/migration/rollback cases.
Native X11 runs bank (419 ticks), rates (2247), Armor Talk (19), Weapons Talk
(19) and synthetic editing (349); each full action record and final JSON equals
headless replay. The synthetic editor check appends leading zero, digits,
Backspace, Escape clear and Enter to the verified bank-entry prefix, and ends
with cash 5/investments `[30,0,0]`. It is not an additional DOS observation.
Whole scripts use private displays and close automatically; no terminal input
is sent one key at a time.

## Two-shop oracle and replay

```sh
python3 tools/reference_session.py --script tools/reference-shops.json
python3 tools/reference_session.py --script tools/reference-shop-boundaries.json
python3 tools/verify_m2e.py
python3 tools/verify_m2e.py --reference-run work/reference-runs/1791690976267363973
python3 tools/verify_m2e.py --boundaries --reference-run work/reference-runs/1791691394449093827
python3 tools/native_smoke.py --shops-only
```

Both DOS runs use ordinary inputs, private displays, read-only snapshots and
unpatched work copies. The first records 50→0 for the flak vest and 15→13 for
the knife; final equipment is weapon 1, armor 1/protection 25. The second checks
No for both goods and insufficient funds for another vest, preserving equipment.
Its longer final wait receives another allowance (13→28). Modes/highlights are
checked against original frames; expected PCs/text ranges come from original
BLD paths, not a captured guest IP. [Shop evidence](M2_SHOPS_EVIDENCE.md) records
primary executable addresses and discrepancies in provisional native labels.

Committed fixtures are numeric fields, actions, resource offsets and hashes;
proprietary text and memory stay ignored. To re-export a run, use
`verify_m2e.py --export DIRECTORY` (add `--boundaries` for the second script).
Idle ticks derive from consecutive D323 observations, and that counter matches
at every checkpoint. The placement of original NPC frames between road keys
and wall-clock timing are excluded from route parity. Existing complete-frame
NPC verification remains separate.

## Save/load and paid Class verification

```sh
build/btp-save-tests "Original DOS"
build/btp-school-tests "Original DOS"
python3 tools/verify_m2g.py
python3 tools/verify_m2h.py
python3 tools/native_smoke.py --school-only
./build/btech-port --smoke-replay --replay tests/fixtures/reference-class-funded.actions
```

F5/F9 uses `work/player-save.btp` by default; `--save-file FILE` selects a slot.
`--load FILE` restores before a replay and `--save FILE` writes on successful
exit. Failed loads leave the current session intact; loading while recording is
refused. Native notices appear in the window title. Original GAME files are not
supported. See [save evidence](M2_SAVE_EVIDENCE.md) for failure and durability scope.

PASS: 11972 save-file assertions across 137 replay snapshots; 31 fresh-process
states with exact full-JSON restore and 1024-tick continuation. Native F5/F9
restores a partially entered bank amount, including after a missing-file error.
M2g BTP7/BTS1 migration and independently recomputed valid-CRC/invalid-state
rejection are checked.

PASS: 59197 school assertions; all subjects/ranks, price boundaries, mastery,
32-bit cash borrow, Withdraw, rollback, saturated countdowns and migration.
The 15 audit and 49 funded original checkpoints match exact text hashes,
cash/skills/story/menu state and frame counter. All 3271 route ticks restore
and continue identically. The two new frame captures match 460 complete outdoor
steps / 462 samples over all 70 observed NPC/RNG/economy fields; ranks and
countdowns use separate RAM checkpoints. Native SDL sends all 3093 funded-route
ticks and its complete final state equals the recorded headless replay.

The ordinary route funds a 75-credit course from 87 cash, raises the first skill
to rank 1, enforces cooldown 255→0 outdoors, then offers tuition 200 and refuses
with cash 27 unchanged. Higher ranks and the other subjects are supported by
primary instructions and boundary tests, not additional live paid-course traces.
Personal Class leaves mission counter 0 unchanged. MechWarrior missions and
barracks sleep remain future work. See [training evidence](M2_TRAINING_EVIDENCE.md).

## Internal state encoding

`BTP8` is a tested **416-byte internal core encoding**, stored by the native F5/F9 interface inside a 16-byte BTS1 length/CRC envelope. Original GAME compatibility remains unimplemented. It adds personal-skill ranks, their rollback copies and the paused course context; BTP7 (384 bytes) migrates with zero ranks and no active course. It preserves prior state plus cash/accounts, cap, equipment, sparse shop refusal byte, remembered menu selectors, confirmation, text positions/dynamic balances, bank selection/amount/results and transaction rollback. BTP6 (320 bytes) migrates with empty investments/no bank service, preserving its cash/equipment. Legacy BTP1 (24), BTP2 (64), BTP3 (128) and BTP4 (160 bytes) disable travel because they never stored its clock. BTP4 retains Talk/occupancy; earlier versions carry none. BTP5 (224 bytes) retains travel and migrates the recorded unspent baseline to cash 35 if its pending allowance marker is set, otherwise 50 when travel is enabled. Legacy equipment defaults to zero because those formats never stored it. Migration is not reconstruction of arbitrary old economy state.

The first 384 bytes retain previous field positions, with magic/version BTP8/8. Words/ticks are little-endian; reserved bytes are zero. Fields added since BTP2:

| Byte offsets | BTP8 field |
|---|---|
| 59–65 | Story bytes 16–22; bytes 0–15 remain at 24–39 |
| 66 | BLD text span count, bounded to eight |
| 68–99 | Eight 16-bit `(offset,length)` pairs; unused pairs zero |
| 100–122 | Story rollback checkpoint |
| 123 | Checkpoint-valid byte |
| 124–127 | Talk phase, remembered NPC selection, occupant count/mask |
| 128–143 | Eight packed-state/occupancy pairs |
| 144–147 | Room, reply actor, D33A result, D339 recruitment context |
| 148–149 | Result rollback checkpoint, visible scenario marker |
| 150–152 | NPC system disabled/lazy/ready, original phase, native tick remainder |
| 153–159 | Three RNG bytes, 16-bit search counter, candidate bias, explicit fault |
| 160–199 | Eight `(packed X word, packed Y word, direction byte)` records |
| 200–201 | Outdoor loop timer, assets-below-cap marker (validated against cash + investments) |
| 67, 202–223 | Reserved zero |
| 224–232 | 32-bit credits, 16-bit cap, weapon/armor/protection bytes |
| 233–237 | Story byte 39, its rollback, Yes/No selection, native service, cash insertion index |
| 238–241 | 32-bit displayed cash snapshot |
| 242–272 | Independent remembered selectors for menu IDs 0–30; unsupported IDs zero |
| 273–277 | Confirmation target, current text column/row, cash-present marker |
| 278–293 | Eight column/row bytes for original text spans |
| 294–300 | Credit/weapon/armor/protection rollback checkpoint |
| 301–319 | Reserved zero |
| 320–331 | Three unsigned 32-bit investment balances |
| 332–343 | Three investment rollback balances |
| 344–347 | Bank phase, company, outcome, clipped-request flag |
| 348–355 | Unsigned 32-bit available balance and transferred amount |
| 356–363 | Seven-digit editor buffer with zero terminator/tail |
| 364 | Account-display flag |
| 365–383 | Reserved zero |
| 384–386 | Three personal weapon-skill ranks, each 0–4 |
| 387–389 | Skill rollback ranks |
| 390–393 | Course phase, selected subject, prior rank and outcome |
| 394–415 | Reserved zero |

BLD text spans concatenate exact bytes without added separators. Native Talk suspends after its operand, clears BLD spans and assembles text from checked EXE/MAP1 references. Bank text combines original literals, numeric input and positioned account values; the digest represents that documented concatenation, not pixel equality. Original case/spaces and bank color controls survive the cache. Decoding validates native PC, occupant mask/count, actor, result, bank phase/editor and checkpoint consistency. More than eight BLD spans, malformed operands/targets, unsupported indexes and exhausted instruction budgets stop explicitly. The sparse story model covers `D30C[0..22]` plus shop refusal index 39 and explicit native contexts. Index 23 is the separately modeled outdoor timer; indexes 23–38 remain unsupported in the VM. CLI `story_flags` keeps its prior 23-byte projection; `shop_refusal` exposes index 39 separately. Restore callers must supply the active slot's BLD via `btp_building_bld`. Immediate purchase/account-display services finish inside one tick; Talk and bank input serialize suspended services. Receipts wait on original bytecode FB, without an extra native pause.

## Passed checks and scope

| Check | Actual result | What it establishes |
|---|---|---|
| CTest core | PASS, 68 synthetic assertions | RLE/map bounds, movement/collision, edges, state restoration/validation, palette and mixed-case glyph regression. |
| CTest script | PASS, 58 synthetic assertions | BLD size/decrypt/bounds, unsupported operations/index/font/scene/menu, byte wrapping, signed tables, concatenation, span limits and native suspension/return. |
| CTest NPC | PASS, 24 synthetic assertions | RNG vectors, first/later allowance wraps, proximity freeze, positive/zero arrival, expiry, timer guard, BTP8 validation/restoration and BTP4 migration. |
| CTest shops | PASS, 40 synthetic assertions | Variable menus/targets, F6 branches, F0 bounds, sparse state, dynamic cash bounds, native-service budget. |
| `build/btp-shop-tests "Original DOS"` | PASS, 30928 assertions | Restore/continue all 6137 ticks of two full shop replays; 49/50 and 1/2-credit boundaries, No, unsupported goods/recovery, malformed/atomic state, allowance overshoot, BTP5 migration. |
| Shop differential | PASS, 56 purchase + 65 boundary checkpoints | Original cursor/party, complete RAM BLDs, exact text hashes, menus/confirmation, credit/result/equipment changes and return; ordinary inputs only. |
| Native X11 shops | PASS, 3064 ticks | SDL input/presentation through both purchases and outdoor return; full final JSON matches headless recorded replay. |
| CTest bank | PASS, 16 synthetic assertions | Pre-update cap comparison, account RNG schedule, wrapping arithmetic and Baker growth threshold. |
| `build/btp-bank-tests "Original DOS"` | PASS, 78178 assertions | Restore/re-encode/continue all 7297 new replay ticks; amount editing, unsigned transfers across all three companies, zero/clipping/refusals, BTP6 migration, rollback and malformed atomic state. |
| Bank/shop Talk differential | PASS, 160 original checkpoints | 33 bank + 29 rates + 28 empty Armor + 48 empty Weapons + 11 occupied per shop; original cursor/party, BLD/native text, cash/accounts, flags/results/menu memory and return. Occupied handlers use controlled preconditions. |
| Bank outdoor oracle | PASS, 459 complete frame steps / 460 samples | All 70 numeric fields, two wraps, account returns/allowance, complete NPC/RNG/loop/search equality; no capture gaps skipped. |
| Native X11 bank/Talk/editor | PASS, five checks | Bank 419, rates 2247, occupied Armor/Weapons 19 each, synthetic editor 349 ticks; complete recorded input/final JSON equality with headless replay. |
| `build/btp-tests "Original DOS"` | PASS, 421 assertions including synthetic checks | 14 MTPs/12 graphics; prior Citadel routes; Talk Done/result/retention, exact lengths, restored pauses, corrupt state/cache, rollback, BTP1/BTP2/BTP3 migration. Multiple occupants/wrap are structural tests, not live parity claims. |
| `build/btp-script-tests "Original DOS"` | PASS, 95 assertions including synthetic checks | Authentic menu/Hall/Katrina texts/effects, repeat denial, retention, exit, native Class/menu suspension and F5 0C continuation. Unknown-action rollback remains covered using a test-owned corrupted BLD copy. |
| Python unpacker/converter | PASS, 4 tests | Synthetic stream/header/run rejection, actual image hash/anchor, deterministic cache/address/string-hash provenance and wrong-version rejection. |
| Movement projection | PASS, 31 original states / 30 actions | Positions/gate match original cursor and party[0], including repeated wall/hedge blocks; all 88 original hashes match. |
| Hall projection | PASS, 16 original checkpoints / 20 native states | Positions, gate, 16 bytes, pending step/exit, seven text digests, six waits and retained selection. |
| Katrina projection | PASS, 20 original checkpoints / 20 native states | Positions, gate, bytes 0–21, first-visit persistence, denial, re-entry highlight and four text hashes. Byte 22 only compared before outdoor countdown resumes. |
| Talk projection | PASS, 10 controlled + 3 unmodified empty-room checkpoints | Positions, bytes 0–22, exact 42-byte menu/162-byte reply/47-byte empty response, Done preserving result, NPC clearing result, both selections and return/exit. NPC arrival and post-exit timers excluded. |
| NPC oracle and natural route | PASS, 1741 NPC assertions; 570 complete frame steps, two arrivals, 56 player/story checkpoints | Exact observed positions/destinations/directions/timers/phase/loop/RNG/search; 68 player-movement gaps skipped. Persistence at every checked frame; ordinary-input arrival/reply/return with original text hashes and building suspension. |
| Native SDL dummy/private X11 | PASS, four short regressions plus X11 natural arrival | Window, SDL input/presentation, bounded exit and records: movement 8 ticks; Hall/Katrina/Talk 24 each; full arrival/reply/exit 2621. Actual native final JSON equals headless replay including NPC/RNG. |
| ASan/UBSan/LeakSanitizer | PASS, headless core/data/pixels/VM/NPC/economy/corpus and all earlier/new bank/shop-Talk replays | No detected address, undefined-behavior or leak errors in these paths. SDL/backend not sanitizer-instrumented. LeakSanitizer requires execution outside the ptrace sandbox. |
| Reference guard | PASS, 1287 entries | Both supplied trees match content/mode/mtime/entries/symlinks, including reference Git metadata. Access times excluded. |

Repeated canonical outputs are identical and unknown input fails. Original credits stay 35 in the short Citadel traces. M2e added two purchases; M2f adds actual balances and returns in the local 50-cap economy. Wider economy/day progression remains deferred. Screens establish modes/highlights/order; PCs are bytecode-derived. None of these checks establishes full timing, global RNG, pixels, Windows or campaign parity.

`test.sh --x11` adds thirteen private-display scenarios and closes automatically; arrival takes about 84 seconds, shops about 98 and the five M2f checks about 98. `python3 tools/native_smoke.py --shops-only` runs just the purchase route; `--m2f-only` runs the new bank/Talk/editor checks; `--bank-input-only` runs the 11-second editor check; `--save-only` checks native F5/F9; `--school-only` runs the 99-second course replay and the save regression. Whole-script GUI approval rules apply; no interactive terminal input is used. Plain `test.sh` needs no display/audio device and checks all routes headlessly. Sanitizers cover software rendering through C tests, without instrumenting SDL/backend code.

## NPC arrival original comparison

[NPC evidence](M2_NPC_EVIDENCE.md) records primary addresses, the initialized baseline and the limits of the RNG schedule:

```sh
./build/btech-port --replay tests/fixtures/citadel-arrival.actions
python3 tools/verify_m2d.py
build/btp-npc-tests "Original DOS" tests/fixtures/npc-frames.csv
python3 tools/reference_session.py --script tools/reference-npc.json
python3 tools/verify_m2d.py --reference-run work/reference-runs/1791689346416199589
```

Substitute the printed directory for a fresh reference run. The whole JSON script uses ordinary keys, a read-only NPC observer and an adaptive bounded wait for arrival. The observer polls only its child emulator and requires two identical numeric projections before retaining a sample. `wait-npc` observes genuine hidden coordinates/nonzero stay timer; `keys-fast` reaches the entry prompt before expiry. No guest context is injected. Raw screenshots/RAM stay ignored; the committed CSV/JSON contain only numerical facts, actions and hashes.

The final original M2d run yielded 639 stable observations. The verifier matches 570 complete outdoor frame steps and two arrivals, explicitly skipping 68 gaps with missing player movement before resuming from the next captured state. Each verified frame checks identical continuation after current BTP8 encode/decode. It compares NPC position, destination, direction, packed/timer pairs, phase, loop timer, RNG and search/bias; it does not claim equality across skipped intervals. The first wrap consumes three account RNG draws, later wraps none, for that unspent 35-credit/50-cap baseline. M2f now extends the model to actual balances/returns and another 459 gap-free full frame comparisons. M2h adds the saturated outdoor countdowns for story bytes 20–22; wider day/cap progression remains deferred.

The default native route has 2612 logical ticks, including idles, and ends on the original 162-byte reply. Fifty-six player/story checkpoints compare by non-idle input ordinal; elapsed-time NPC fields at route checkpoints are excluded from this projection. The frame corpus establishes their step behavior separately. Native entry/building suspension and return/exit pass. `--smoke-arrival --replay tests/fixtures/citadel-arrival.actions` sends the entire route through SDL events, appends nine return/exit/idle actions, and closes at tick 2621. The X11 test compares actual native JSON with its headless replay, including every NPC/RNG field.

Original/native reply frames were visually inspected for mixed case and readable text. NPC sprites remain approximate green markers. Full startup, exact wall-clock cadence, world/edge/party rules, player movement against NPCs, global RNG/economy and pixels are outside parity. The separate M2c handler checkpoint keeps travel disabled and is never used to establish natural arrival.

## Talk original comparison

A quick Citadel visit from the normal initialized start is empty. Talk shows its original response and returns. The earlier isolated NPC handler is also playable in a visibly labeled controlled scenario:

```sh
./build/btech-port --conversation-checkpoint --replay tests/fixtures/citadel-talk.actions
python3 tools/verify_m2c.py
python3 tools/reference_session.py --script tools/reference-talk.json
python3 tools/verify_m2c.py --reference-run work/reference-runs/1791685774441704966 \
    --empty-reference-run work/reference-runs/1791684527855747449
```

The native replay opens on the NPC reply; Enter/Space returns to the Citadel menu. Without `--replay`, five Up, Enter, three Down, Enter opens the NPC menu. Done returns immediately. The NPC opens the authentic reply. Both menus retain selection independently. Recording/replaying this scenario requires `--conversation-checkpoint` in both commands: action logs do not carry initial-state metadata.

The original script applies an **explicit controlled precondition** at the initial Citadel menu. Only eight NPC pairs and D33A are written in the child emulator, with separate before/after audit and snapshot. No executable/resource/save file is patched. Default reference scripts remain read-only apart from normal gameplay. This verifies the handler under that precondition, not NPC travel or a naturally reached campaign state. The empty-room trace is unmodified. See [M2_TALK_EVIDENCE.md](M2_TALK_EVIDENCE.md).

The verifier reconstructs text directly from original EXE/MAP1 bytes, independently of the cache, and checks live RAM text/name sources and the full BLD payload. Byte 13 persists; Done preserves result 91; the reply clears it to 0. NPC equality is required in the building and excluded on exit, when original travel resumes. `--smoke-talk` exercises the full 19-action path plus five idle ticks. Native mixed-case text was inspected; glyphs/layout and imagery remain approximate. This local reply makes no RNG draw; outer-world dialogue and recruitment are unsupported.

## Katrina original comparison

[Katrina evidence](M2_KATRINA_EVIDENCE.md) records primary bytecode/machine-code findings and the bounded first-visit/repeat/exit/re-entry trace:

```sh
python3 tools/reference_session.py --script tools/reference-katrina.json
python3 tools/verify_m2b.py --reference-run work/reference-runs/1791683236787259649
```

Substitute the printed run directory for a fresh comparison. The successful original run has 20 checkpoints; the verifier matches cursor and party[0], bytes 0–21, recorded credits and full decrypted RAM payloads against the committed factual fixture and native replay. Four text hashes check original case and exact concatenation. Screens were inspected to establish dialogue order, modes and selection; the verifier does not infer them from an assumed DOS mode byte.

**Explicit exclusion:** the original sets byte 22 to 255, freezes it in the building, then counts down outdoors. The recorded exit/re-entry values depend on elapsed original-loop timing. Native state retains 255; no equality is claimed for that field after exit. Byte 6 does persist across exit/re-entry and is compared. Broader timer/day/economy parity is unfinished.

Without DOSBox:

```sh
python3 tools/verify_m2b.py
./build/btech-headless --replay tests/fixtures/citadel-katrina.actions --trace --frame work/katrina.ppm
```

`--smoke-katrina` exercises the 19-action loop through queued SDL events, then five idle ticks, ending on the re-entered menu with Leave selected. Native records are replayed against the same canonical state. Case-sensitive text rendering was also inspected in the generated native frame; original glyph shapes, wrapping and scene imagery remain approximate. These historical Katrina checks do not establish later mission-progress branches or original saves. M2h separately verifies paid personal Class and the outdoor countdown model.

## Citadel original comparison

[Citadel evidence](M2_CITADEL_EVIDENCE.md) records exact trigger/decrypt/opcode findings and confidence. Run the original and compare the printed run directory:

```sh
python3 tools/reference_session.py --script tools/reference-citadel.json
python3 tools/verify_m2.py --reference-run work/reference-runs/1791682077232453392
```

The input script waits through arrival/text rendering, selects Hall of Legends, advances six screens, selects Leave from the retained Hall highlight, and takes one south step. The verifier compares fresh original cursor **and party[0]**, 16 state bytes, unchanged credits and all 4328 decrypted bytes with the fixture/core. Seven native text digests are checked against the original resource. Snapshot mode labels come from captured screen observations; the verifier does not read an assumed DOS mode enum or claim that VM PC was captured from the live interpreter.

Without DOSBox:

```sh
python3 tools/verify_m2.py
./build/btech-headless --replay tests/fixtures/citadel-hall.actions --trace --frame work/citadel-hall.ppm
```

`--smoke-citadel` feeds a bounded set of logical controls through the native SDL event queue. Its records and screenshots remain in ignored `work/`. Error-branch checks require a failing process exit with `unsupported opcode`; they also verify explicit recovery. This does not establish the other Citadel choices, complete story flags, economy, pixel equality or original timing.

## Original-game reference sequence

Spice86 cannot run with this checkout alone: no dotnet executable, no matching external Spice86 tree, and no prebuilt reference executable. DOSBox 0.74-3 is the practical oracle. It executes an unpatched copy of `BTECH.EXE`, not UnBattletech's runtime.

One-time working copy, if absent:

```sh
mkdir -p work/dos
cp -a "Original DOS/." work/dos/
```

Reference command:

```sh
python3 tools/reference_session.py --script tools/reference-movement.json
```

The script selects `3` for VGA, `3` for hard disk, waits through startup, uses the recorded title/menu keys, then walks the road, the south wall, the hedge and the west wall. Intro/menu inputs remain part of the recorded sequence. Coordinates already exist during the initial question screen; the native slice begins directly at those initialized MAP1 coordinates and omits the original startup menus. This is a scenario fixture, not a claim to reproduce every new-game variable.

Every invocation creates `work/reference-runs/<unique-id>/`: `inputs.jsonl`, DOSBox/Xvfb logs/config, raw 320×200 PNGs, read-only guest-RAM exports, and JSON snapshots. `work/reference-latest.txt` gives the newest directory. The harness owns a private Xvfb display, focuses only its own DOSBox window, does not receive interactive stdin, and terminates both child processes. Files read/mounted by DOSBox are only under `work/dos/`; originals are never mounted writable. Failures stop the script rather than silently accepting absent captures.

To compare a fresh run with the native core and compute the frame report, substitute its printed directory:

```sh
python3 tools/verify_m1.py --reference-run work/reference-runs/1791680299506554032
```

`tools/verify_m1.py` uses Python's standard library for state comparison; Pillow is required only for the optional PNG/pixel report. All 88 original hashes are checked first. Regression fixtures contain only factual coordinates/actions and provenance; proprietary PNGs/RAM/resource bytes are kept out of the fixtures. Before launch, the reference harness also checks working-copy resources against the manifest, excluding mutable GAME saves.

**VERIFIED observations:** initial raw X/Y `0C45:C019` → half coordinates `(69,25)`, nominal cursor tile `(34,12)`; party[0] coordinates agree. Gate `85`; runtime UI selector `2`, narrow-panel value `1`, world-active byte `0`, scene bytes recorded as zero. `w014A` is `1` while movement works; interpreting the harness's historical `suspend` field as a global pause flag is unproven. Credits are `20` at the initial question snapshot and `35` in the later walk snapshot; allowance/timing parity is excluded from M1.

The game image is located using its known unpacked string offset `37A88`, then validated against BIOS data and entry bytes; the load segment in these runs is `01A2`. Common DS is load + `36DB`; the map-buffer DS is load + `1C6C`. Runtime selector pointers resolve state, UI and cursor storage. Reko's load base `0800` and old Spice86 aliases are not used as raw file offsets or native-core addresses. Original MAP1 payload bytes are present at guest offset `1F0FD`. The 24×24 working grid at map DS + `07AD` matches all 576 corresponding MAP1 tile IDs at map region origin `(24,0)` in the recorded start. It is not a tile-property LUT or proof of a static global world.

Cursor tile projection floors both half coordinates. Player collision in the recorded trace instead samples `ceil(x_half/2), floor(y_half/2)`: west moves `68→67` succeed although the nominal cursor enters tile 33, then `67→66` blocks on its wall. Tile ID threshold 85 and this offset rule reproduce the tested route. Generalization to additional scenes, multi-unit footprints and world edges remains **INFERRED/UNKNOWN**; native map edges currently block deliberately.

## Graphics comparison and exact deviations

All 64,000 independently decoded C BTTLTECH pixels match the secondary reference tilesheet under the standard EGA palette. MAP1 uses 16×16 tiles, block-normalized map data, and an observed terrain remap 5→9, 9→1. At the tested start, the original right panel begins at X=104; its map crop origin is `(464,104)` after the first east step, matching camera `x_half*8−96, y_half*8−96`. Native resolution is 320×200, scaled without filtering.

**VERIFIED for that frame:** 42,625 / 43,200 right-panel pixels equal, **98.669%**. The remaining 575 pixels include omitted NPC/sprite overlays and the approximate player marker; their complete causes are not assigned without further tests. The independently drawn left diagnostic panel replaces original status/animation/menu graphics. Whole-screen equality is not claimed. Palette/camera parity for other graphics modes remains **UNKNOWN**.

Remaining differences: no full NPC startup/world travel/followers, later campaign progression, later cap/day/sleep progression, remaining shop goods/repair/assignment, encounters, combat or original GAME compatibility, ANM playback or audio. M2f adds three local investment balances/returns and both shops' Talk to the earlier purchases/conversation. Unsupported actions still stop visibly. Glyph shapes/layout, pauses, markers and imagery remain approximate despite preserving original text bytes and case. The 98.669% figure above is the historical M1 comparison frame, not current pixel parity. No complete campaign or global map is claimed.

## Dependency provenance

Packages were downloaded through the configured Ubuntu archive with `apt-get download` and extracted with `dpkg-deb -x`; no privileged system package installation or arbitrary remote script was used. Original-game graphics are loaded directly, not copied from the GPL project. Existing GPL tooling was exercised only on copies to audit decoding/round trips.

| Local package | Destination | SHA-256 |
|---|---|---|
| dosbox 0.74-3-5build2 amd64 | `local-deps/dosbox/` | `f7fabe8e4923ec503349f8c7466ab132395e83ba03aa1e382955c09f434c4433` |
| libsdl-net1.2 1.2.8-6build1 amd64 | `local-deps/dosbox/` | `3a060ffbfb07f8046ee78c7211fe67932717bc6a4f52daca9860cd60c3396dd2` |
| libsdl-sound1.2 1.0.3-9build4 amd64 | `local-deps/dosbox/` | `c02bfb7fe9e20189b4c5556f73acab4c1b53594db6ff10dde58d11be0be97d10` |
| libmikmod3 3.3.13-1 amd64 | `local-deps/dosbox/` | `f2b562ffcd8bf90947487ce3ded3363f2afeef0cce07e6732d1b691bb8d297ab` |
| libsdl2-dev 2.32.4+dfsg-1 amd64 | `local-deps/sdl2/` | `90a21699bdb8f6f491b92dba345a85b1ab865c54cd59c527b91603a2d1a13b17` |
| xvfb 2:21.1.18-1ubuntu1.1 amd64 | `local-deps/xvfb/` | `a980a874e0b5663ada7ff1f145ce91b87ba03a40bd5d4fde335bf6d0f1a4ed06` |

The harness supplies a process-local library path for DOSBox's extracted libraries and dummy audio. X11/XTest libraries and fonts were already present. There is no audio device dependency in the slice. These packages are local ignored dependencies, not new implementation source. No new dependencies were needed for M2a–M2h.
