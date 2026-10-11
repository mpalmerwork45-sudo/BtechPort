# BtechPort

Independent C11/SDL2 recreation research for **BattleTech: The Crescent Hawk's Inception**, supplied DOS version 1.03. **M0, M1 and bounded M2a–M2j are complete.** Explore MAP1 with moving NPCs, visit the Citadel, buy all eleven weapons and five armour types, trade investments at ComStar and talk to occupants in both shops and the lounge. The first MechWarrior quiz, loaned-mech mission, result and barracks sleep loop are playable. Paid Citadel classes improve personal weapon skills and obey the original cooldown. Native save/load preserves progress. Jason and the outdoor cadets now use original walking sprites. Text preserves upper/lower case; the campaign remains unfinished.

## Acknowledgements

BtechPort builds on substantial reverse-engineering work by others. Their
research made this recreation possible and deserves explicit credit:

- **[UnBattletech](https://github.com/velteyn/UnBattletech), by Edoardo Barolo
  (`velteyn`) and its contributors, including Maximilien Noal.** Its file-format
  specifications, memory maps, story and engine research, annotated disassembly
  and decompiler output, and extraction tools supplied the main starting point
  for this port's research. We used its BLD round-trip converter for the initial
  audit and its documentation and assembly to locate original routines for
  further verification. UnBattletech is licensed under GPL-3.0.
- **The [Reko](https://github.com/uxmal/reko) and Spice86 contributors.** Their
  decompilation and emulator tooling underpins much of UnBattletech's research
  material consulted here. BtechPort's own live comparisons currently use DOSBox.
- **[w4kfu's unEXEPACK research](https://github.com/w4kfu/unEXEPACK#exepack-header).**
  Its published EXEPACK header description informed this project's independently
  written unpacker and executable-format audit.

This port's independent C implementation and original-game validation extend
that research foundation. Detailed sources and verification limits are recorded
in the [research audit](docs/RESEARCH_AUDIT.md) and milestone evidence reports.
The original game, artwork and story are the work of **Westwood Associates**,
published by **Infocom**.

## Build and play

From this directory on the current Kubuntu machine:

```sh
./scripts/build.sh
./build/btech-port --data "Original DOS"
./scripts/test.sh
```

Arrows move/select; hold two perpendicular arrows for diagonal movement. Keypad 1/3/7/9 or End/PgDn/Home/PgUp move diagonally, and keypad 2/4/6/8 moves in cardinal directions. These movement keys work while walking and driving a mech; Enter or Space confirms and advances dialogue; Backspace declines entry or recovers from an unsupported choice. F3 toggles diagnostics, R restarts and Esc closes. From the start, move Up five times, confirm entry, then confirm **Request to see Katrina**. Advance the sentry and Katrina screens to return to the menu. A repeat request gets the original denial. Four Down presses select Leave; after exiting and re-entering, the menu retains that selection. Hall of Legends still has its six original screens.

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

The runtime reads `MAP1.MTP`, `BTTLTECH.ICN`, `MECHSHAP.CMP`, `CITADEL.BLD`, `COMSTAR.BLD`, `ARMOR.BLD`, `WEAPON.BLD`, `TRAINING.BLD`, `BARRACKS.BLD`, `LOUNGE.BLD`, `BTSTATS.CMP` and ignored `work/talk-data.bin`, which the build prepares reproducibly from `BTECH.EXE`. No Godot/.NET/reference runtime is required. Later missions, armour repair and unsupported interiors stop visibly or remain unavailable. Failed choices roll back partial story/result/equipment/cash/investment/skill changes, and Backspace returns to the menu. Use `citadel-hall.actions` for the first Hall screen.

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
than a clamp. All eleven weapons and five armour types are now purchasable through the original menus, prices and confirmations. Purchases replace the equipped item; full party equipment remains future work.

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

Citadel **Class** offers three personal weapon-skill courses. Tuition starts at
75 and rises by 125 per rank; insufficient funds and mastery use the original
responses. Successful completion starts the outdoor cooldown. Indoors the
countdown stops; leaving and waiting allows re-enrolment. The first MechWarrior mission and barracks sleep are now implemented separately from these personal classes.

To watch the ordinary funded course and cooldown route (about 99 seconds):

```sh
./build/btech-port --smoke-replay --replay tests/fixtures/reference-class-funded.actions
```

Omit `--smoke-replay` to continue interactively after that route. See
[training verification](docs/M2_TRAINING_EVIDENCE.md).

Both shops' and the lounge's **Talk to others** handle empty rooms or present NPCs. Normal
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

The replay walks south, steps off the narrow road, follows an NPC north/east and returns to the Citadel before it departs. NPC movement and stay timers make the conversation reachable; the replay supplies ordinary actions and idle ticks. Enter/Space returns to the Citadel menu. Player and cadet sprites come from the original atlas, with directional walking frames. This starts at the recorded initialized MAP1 baseline and omits the DOS startup menus.

The earlier isolated handler checkpoint remains available:

```sh
./build/btech-port --conversation-checkpoint --replay tests/fixtures/citadel-talk.actions
```

Omit `--replay` to start outdoors with the visibly labeled checkpoint; five Up, Enter, three Down, Enter opens the NPC menu. Done returns immediately; selecting the NPC shows the authentic reply. Both menus remember selection independently. This checkpoint supplies controlled occupancy with travel disabled. A quick Citadel visit from the normal start still gets the original empty-room response. Custom resource/cache paths use `--data` and `--dialogue-data`; preparation is documented in [TESTING.md](docs/TESTING.md).

**VERIFIED in scope:** authentic resource decoding and bounded BLD interpretation; earlier movement/Citadel, NPC, two-shop and ComStar routes. M2g adds file integrity and native save/load. M2h adds 64 original Class/funding/cooldown checkpoints and 460 complete outdoor frame comparisons. All 3271 Class replay ticks restore and continue identically in the current state format; 137 disk snapshots and 31 fresh-process restart/continuation states pass. Occupied-shop checks retain their explicit controlled preconditions. **INFERRED:** unobserved movement and broader campaign contexts. **APPROXIMATE:** remaining UI imagery, independent mixed-case font/layout, input cadence and map edges. **UNKNOWN/unimplemented:** later MechWarrior missions and day progression, world/party rules, repair, combat, original GAME compatibility, terrain/scene animation, audio and the full campaign. Unknown operations fail visibly. The older NPC capture's 68 missing movement intervals remain reported and skipped.

**M2i sprites:** all 376 original sprite crops match the EXE's RAM, and walking tests
cover 30 player checkpoints, four exact player pixel crops and 63 NPC frame steps.
Save/load retains walking frames; older saves start a new gait at their stored
facing. Mechs are available in a separate animated preview and in the first training mission; ownership, later missions and combat remain incomplete. See [sprite evidence](docs/M2_SPRITE_EVIDENCE.md).

```sh
./build/btech-port --sprite-preview
python3 tools/verify_sprites.py
python3 tools/native_smoke.py --sprites-only
```


The Training Center is at half-coordinate (46,114), Barracks at (17,13), and
the lounge at (17,89). The written quiz asks for three parts on the original
mech diagram. Select the correct names, accept the first assignment, then choose
Locust, Wasp or Chameleon. Drive to the southeast corner (x>=120,y>=124),
acknowledge its message and return to x<=60,y=73..79. Terrain adds to the timer;
success raises the allowance cap to 150. A successful first assignment unlocks
the barracks dream/sleep sequence, which clears the training cooldown. Later
assignments display an explicit diagnostic. Dream animation and audio remain
unimplemented. The lounge supports ordinary Talk and the verified Rick/device
branch; that branch's later campaign prerequisite is not yet naturally unlocked.

To start inside the loaned Locust after ordinary entry and quiz inputs, or watch
the successful mission/return/sleep route through SDL:

```sh
./build/btech-port --replay tests/fixtures/reference-diagonal-mech.actions
./build/btech-port --smoke-replay --replay tests/fixtures/reference-mission-pass.actions
python3 tools/verify_m2j.py
python3 tools/native_smoke.py --diagonal-only
```

**M2j verification:** 325 original checkpoints cover the mission and sleep loop,
all goods, lounge and four diagonal directions for people and mechs, including
blocked attempts. Save/restart checks continue every observed new phase. The
full-goods trace uses an explicit 20000-credit test budget; the Rick branch uses
an explicit occupancy/story prerequisite. The mission/sleep and diagonal routes
use ordinary inputs. Native SDL, F5/F9, keypad bank entry and sanitizer checks
pass. See [mission and diagonal evidence](docs/M2_MISSION_EVIDENCE.md).

The bounded DOSBox harness runs whole JSON input sequences on a private virtual display, captures frames/state and closes automatically. It uses no interactive terminal input, so the former per-key approval loop is removed. Original binaries, screenshots and memory dumps remain in ignored directories.

Read [the milestone review](docs/PROJECT_STATUS.md), [testing](docs/TESTING.md), [banking and shop Talk evidence](docs/M2_BANKING_EVIDENCE.md), [shop purchase evidence](docs/M2_SHOPS_EVIDENCE.md), [NPC travel evidence](docs/M2_NPC_EVIDENCE.md), [Talk evidence](docs/M2_TALK_EVIDENCE.md), [Katrina evidence](docs/M2_KATRINA_EVIDENCE.md), [Hall evidence](docs/M2_CITADEL_EVIDENCE.md), [inventory](docs/ORIGINAL_FILES.md), [audit](docs/RESEARCH_AUDIT.md), [language decision](docs/LANGUAGE_DECISION.md) and [open questions](docs/OPEN_QUESTIONS.md). New code is under `port/`, automation under `tools/`/`scripts/`, regressions under `tests/`.

Both supplied reference directories remain unchanged. A local Git repository on `main` records incremental milestones; originals, reference checkout, generated assets and dependencies are ignored. No pushes or Git configuration changes were made. No substantial GPL source was copied or translated into the runtime; this does not establish legal clean-room status or permission to redistribute proprietary assets.
