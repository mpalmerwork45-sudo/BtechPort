# BtechPort

Independent C11/SDL2 recreation research for **BattleTech: The Crescent Hawk's Inception**, supplied DOS version 1.03. **M0, M1 and bounded M2a–M2g are complete; M2h is in progress.** Explore MAP1 with moving NPCs, visit the Citadel, buy a flak vest and knife, trade investments at ComStar and talk to occupants in both shops. Native save/load preserves progress. Text preserves upper/lower case; the campaign remains unfinished.

From this directory on the current Kubuntu machine:

```sh
./scripts/build.sh
./build/btech-port --data "Original DOS"
./scripts/test.sh
```

Arrows move/select; Enter or Space confirms and advances dialogue; Backspace declines entry or recovers from an unsupported choice. F3 toggles diagnostics, R restarts and Esc closes. From the start, move Up five times, confirm entry, then confirm **Request to see Katrina**. Advance the sentry and Katrina screens to return to the menu. A repeat request gets the original denial. Four Down presses select Leave; after exiting and re-entering, the menu retains that selection. Hall of Legends still has its six original screens.

Bank amounts use digits (including keypad), Backspace erasure, Escape to clear
to 0, and Enter to submit; Space does not submit. Escape closes elsewhere.

**F5 saves; F9 loads** the single slot `work/player-save.btp`. Failed loads keep
the current session intact. `--save-file FILE` chooses a slot; `--load FILE`
starts from a save, and `--save FILE` writes on successful exit. Paused dialogue
and partial bank amounts restore too. These internal saves use the tested state
format; original DOS GAME compatibility remains unimplemented. Loading during
input recording is refused; start the next log after loading. See
[save/load verification](docs/M2_SAVE_EVIDENCE.md).

To open directly on Katrina's first conversation:

```sh
./build/btech-port --data "Original DOS" --replay tests/fixtures/citadel-katrina.actions
```

The runtime reads `MAP1.MTP`, `BTTLTECH.ICN`, `CITADEL.BLD`, `COMSTAR.BLD`, `ARMOR.BLD`, `WEAPON.BLD` and ignored `work/talk-data.bin`, which the build prepares reproducibly from `BTECH.EXE`. No Godot/.NET/reference runtime is required. Combat class stops at an unsupported action after its introduction. Other shop purchases and repair stop visibly; other building interiors remain unavailable. Failed choices roll back partial story/result/equipment/cash/investment changes, and Backspace returns to the menu. Use `citadel-hall.actions` for the first Hall screen.

To watch the complete two-shop route through native SDL inputs (about 98 seconds, closes automatically):

```sh
./build/btech-port --smoke-shops --replay tests/fixtures/reference-shops.actions
```

For an interactive window after both purchases, omit `--smoke-shops`. The route
buys the 50 C-bill flak vest in the Armor Shop at tile (25,62), then the 2 C-bill
knife in the Weapons Shop at (16,22), and returns outdoors with 13 credits.
Arrows select items and Yes/No; Enter confirms. The ordinary 35-credit start
receives 15-credit outdoor allowances while cash plus investments are below the
local 50-credit cap, so wait
outside if a vest is unaffordable. Declining a purchase costs nothing; insufficient
funds produce the original response and exit. The cap is a pre-update test rather
than a clamp. Only these two item purchases are implemented in this gate.

To open ComStar on the verified account screen, or watch its whole transaction
replay through SDL (about 13 seconds, closes automatically):

```sh
./build/btech-port --replay tests/fixtures/reference-bank-rates.actions
./build/btech-port --smoke-replay --replay tests/fixtures/reference-bank.actions
```

ComStar handles cash and three stock balances: DefHes, NasDiv and BakPhar.
Inspect accounts, change investments or review the original prospectus text.
Buy/Sell and company selection share the original remembered selector. Requests
beyond available cash or holdings are clipped; zero/unfunded/unowned requests
use their original responses. The bounded MAP1 allowance/return rules include
all three balances and preserve the observed RNG schedule. Full day/cap
progression remains deferred.

Both shops' **Talk to others** now handles empty rooms or present NPCs. Normal
occupancy comes from travel. These explicitly labeled demos put two occupants
inside each shop with travel disabled, matching controlled original-handler
preconditions:

```sh
./build/btech-port --shop-talk-checkpoint armor
./build/btech-port --shop-talk-checkpoint weapon
```

Select Talk, then a name or Done. Replies use original mixed-case text and the
NPC's actual destination; both shop and NPC menus retain their selections.

To open the NPC reply after a verified normal-start exploration replay:

```sh
./build/btech-port --replay tests/fixtures/citadel-arrival.actions
```

The replay walks south, steps off the narrow road, follows an NPC north/east and returns to the Citadel before it departs. NPC movement and stay timers make the conversation reachable; the replay supplies ordinary actions and idle ticks. Enter/Space returns to the Citadel menu. Green NPC markers are approximate; original sprites remain deferred. This starts at the recorded initialized MAP1 baseline and omits the DOS startup menus.

The earlier isolated handler checkpoint remains available:

```sh
./build/btech-port --conversation-checkpoint --replay tests/fixtures/citadel-talk.actions
```

Omit `--replay` to start outdoors with the visibly labeled checkpoint; five Up, Enter, three Down, Enter opens the NPC menu. Done returns immediately; selecting the NPC shows the authentic reply. Both menus remember selection independently. This checkpoint supplies controlled occupancy with travel disabled. A quick Citadel visit from the normal start still gets the original empty-room response. Custom resource/cache paths use `--data` and `--dialogue-data`; preparation is documented in [TESTING.md](docs/TESTING.md).

**VERIFIED in scope:** authentic resource decoding and bounded BLD interpretation; earlier movement/Citadel routes; 570 complete NPC frame steps, two arrivals and 56 natural conversation checkpoints; 121 two-shop purchase checkpoints. M2f adds 160 banking/shop-Talk checkpoints and another 459 gap-free outdoor frame steps with exact NPC/RNG/cash/investment projection. Occupied-shop checks use explicit controlled two-NPC preconditions, not natural arrival traces. All 7297 new replay ticks restore and continue identically in BTP7. **INFERRED:** unobserved movement, later paths and broader flag meanings. **APPROXIMATE:** imagery/markers, panel, independent mixed-case font/layout, input, 32ms cadence and map edges. **UNKNOWN/unimplemented:** complete startup, world/party rules, global RNG/day/cap timing, remaining purchases/repair/assignment, combat, save/load UI or GAME compatibility, animation/audio and later campaign progression. Unknown BLD opcodes/native actions fail visibly. The earlier NPC capture's 68 missed player-movement gaps remain reported and skipped.

The bounded DOSBox harness runs whole JSON input sequences on a private virtual display, captures frames/state and closes automatically. It uses no interactive terminal input, so the former per-key approval loop is removed. Original binaries, screenshots and memory dumps remain in ignored directories.

Read [the milestone review](docs/PROJECT_STATUS.md), [testing](docs/TESTING.md), [banking and shop Talk evidence](docs/M2_BANKING_EVIDENCE.md), [shop purchase evidence](docs/M2_SHOPS_EVIDENCE.md), [NPC travel evidence](docs/M2_NPC_EVIDENCE.md), [Talk evidence](docs/M2_TALK_EVIDENCE.md), [Katrina evidence](docs/M2_KATRINA_EVIDENCE.md), [Hall evidence](docs/M2_CITADEL_EVIDENCE.md), [inventory](docs/ORIGINAL_FILES.md), [audit](docs/RESEARCH_AUDIT.md), [language decision](docs/LANGUAGE_DECISION.md) and [open questions](docs/OPEN_QUESTIONS.md). New code is under `port/`, automation under `tools/`/`scripts/`, regressions under `tests/`.

Both supplied reference directories remain unchanged. A local Git repository on `main` records incremental milestones; originals, reference checkout, generated assets and dependencies are ignored. No pushes or Git configuration changes were made. No substantial GPL source was copied or translated into the runtime; this does not establish legal clean-room status or permission to redistribute proprietary assets.
