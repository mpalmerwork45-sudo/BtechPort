# BtechPort

Independent C11/SDL2 recreation of **BattleTech: The Crescent Hawk's Inception**,
supplied DOS version 1.03. **M0, M1, bounded M2a–M2m and M3a–M3h are complete.**
M4a–M4e are underway; [current evidence and limits](docs/M4_PROGRESS.md)
cover the Space menu, six save slots, splash palette, combat opening prompts,
PC-speaker effects, combat outtakes and training return-to-base message.
All six supplied original GAME files now import and roundtrip exactly. To use
one, run `./build/btech-port --load 'Original DOS/GAME3'`. Export an imported
save outdoors with `--export-original work/GAME3`; unmodeled bytes are retained.
The compatibility limits are recorded in the M4 evidence above.
Explore MAP1, visit the Citadel, buy all weapons/armour, use ComStar and talk
in both shops, Mechit-Lube and the lounge. Six MechWarrior assignments now reach
their results: movement, rubble, a stationary shell, armed labor robots and a
live Locust duel, then two live Locusts. Rick's device scene follows the natural
lounge invitation. Weapons and Kick physical attacks are playable, with separate
walk, run and jump orders. Mechit-Lube offers its 500-C-bill apprenticeship and
the original early-game service responses.
Original walking/firing/Kick/impact artwork, persistent flames and wrecks,
force-field electricity, launch/dream animations, mixed-case font and borders
are integrated. The seventh-assignment invasion opens the destroyed Citadel and
outer world. Travel to Starport, park an owned mech, recruit Rex and a technician,
inspect party equipment, and use mech repairs, ammunition and Speed Shop refits.
The original title music, building portraits and recruitment crest now play.
F4 follows travel across independently generated original terrain. Native
save/load preserves party, service prompts, music, animation and combat.
The wider campaign remains unfinished; encounter timing, following and parts of
the service interface remain approximate.

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
  material consulted here. BtechPort's comparisons use DOSBox and bounded
  execution of original instructions with Unicorn.
- **[w4kfu's unEXEPACK research](https://github.com/w4kfu/unEXEPACK#exepack-header).**
  Its published EXEPACK header description informed this project's independently
  written unpacker and executable-format audit.

This port's independent C implementation and original-game validation extend
that research foundation. Detailed sources and verification limits are recorded
in the [research audit](docs/RESEARCH_AUDIT.md) and milestone evidence reports.
The original game, artwork and story are the work of **Westwood Associates**,
published by **Infocom**.

## Build and play

**M3d–M3h:** invasion, world travel, Starport recruitment, owned-mech services,
title music and building portraits work through ordinary inputs. The training
shell stays still as requested. See [current evidence and limits](docs/M3D_H_PROGRESS.md).

From this directory on the current Kubuntu machine:

```sh
./scripts/build.sh
./build/btech-port --data "Original DOS"
./scripts/test.sh
```

Arrows move/select; hold two perpendicular arrows for diagonal movement. Keypad 1/3/7/9 or End/PgDn/Home/PgUp move diagonally, and keypad 2/4/6/8 moves in cardinal directions. These movement keys work while walking and driving a mech; Enter or Space confirms and advances dialogue; Backspace declines entry or recovers from an unsupported choice. F3 toggles diagnostics, R restarts and Esc closes. From the start, move Up five times, confirm entry, then confirm **Request to see Katrina**. Advance the sentry and Katrina screens to return to the menu. A repeat request gets the original denial. Four Down presses select Leave; after exiting and re-entering, the menu retains that selection. Hall of Legends still has its six original screens.

Bank and ammo amounts use digits (including keypad), Backspace erasure, Escape to clear
to 0, and Enter to submit; Space does not submit. Escape closes elsewhere.
The title screen plays the original PC speaker music; Enter starts play.
Use `--mute` to disable the native audio device.

**F4 toggles the area map.** It places the authentic 64×64 Citadel map within
192×192 tiles generated independently in C. Launch directly
into that view with `./build/btech-port --world-overview`. This bounded area uses
owner-derived numeric inputs and a stated seed; the view follows the party after
the invasion. Thirty complete sectors across three seeds match the original
generator. Stored town maps overlay the generated world; Starport is the first
additional town with an input-only campaign route. The early campaign's closed
borders remain until the attack. Builds and play need no emulator; see
[setup and verification](docs/TESTING.md).

**F5 saves; F9 loads** the single slot `work/player-save.btp`. Failed loads keep
the current session intact. `--save-file FILE` chooses a slot; `--load FILE`
starts from a save, and `--save FILE` writes on successful exit. Paused dialogue
and partial bank amounts restore too. These internal saves use the tested state
format; original DOS GAME compatibility remains unimplemented. Loading during
input recording is refused; start the next log after loading. See
[save/load verification](docs/M2_SAVE_EVIDENCE.md).

To reach the later milestones quickly, these replays execute ordinary inputs
through the headless core before opening an interactive native window:

```sh
./build/btech-port --replay tests/fixtures/ordinary-starport.actions
./build/btech-port --replay tests/fixtures/ordinary-rex.actions
./build/btech-port --replay tests/fixtures/ordinary-services.actions
python3 tools/native_smoke.py --campaign-only
```

Space outdoors after the invasion opens party actions. Inspect or Equipment
selects the person whose equipped weapon, armour and skills are displayed;
subsequent shop purchases equip that selected member. The garage parks the
party's mechs, and checkout retains its original 150-credit fee. Mechit-Lube
selects an owned mech for repairs, an ammo bin and quantity, or its original
Speed Shop offer. Unaffordable work follows the original numeric limits.

To open directly on Katrina's first conversation:

```sh
./build/btech-port --data "Original DOS" --replay tests/fixtures/citadel-katrina.actions
```

The runtime reads MAP1–14, all 26 BLDs, the original ICN/CMP artwork and ANMs,
`BTTITLE.CMP`, `WWOODBT.SIF`, and ignored `work/talk-data.bin`,
`work/combat-data.bin` and `work/world-data.bin`. The build prepares the caches
reproducibly from `BTECH.EXE`. No Godot/.NET/reference runtime is required.
Unsupported later script actions stop visibly. Failed choices roll back partial
story, party, equipment, cash, investment and skill changes; Backspace returns to
the menu. Use `citadel-hall.actions` for the first Hall screen.

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
than a clamp. All eleven weapons and five armour types are purchasable through
the original menus, prices and confirmations. Purchases replace the selected
party member's equipped item. Cash is shared; a backpack/transfer interface is
not implemented.

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
countdown stops; leaving and waiting allows re-enrolment. The MechWarrior assignments and barracks sleep are implemented separately from these personal classes.

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

Omit `--replay` to start outdoors with the visibly labeled checkpoint; five Up, Enter, three Down, Enter opens the NPC menu. Done returns immediately; selecting the NPC shows the authentic reply. Both menus remember selection independently. This checkpoint supplies controlled occupancy with travel disabled. A quick Citadel visit from the normal start still gets the original empty-room response. Custom resource/cache paths use `--data`, `--dialogue-data` and `--combat-data`; preparation is documented in [TESTING.md](docs/TESTING.md).

**VERIFIED in scope:** authentic resources and bounded original BLD, movement,
NPC, shop, banking, training and combat comparisons. M3d–M3h adds 16 invasion
setups, 30 whole generated sectors, 65 recruitment cases, 18 mixed encounter
setups, 47 service cases, 128 speaker pitches and the complete 17,409-step title
interrupt trace. All 34 CTest suites, the historical headless regression,
headless ASan/UBSan/LeakSanitizer and focused native campaign/save checks pass.
**APPROXIMATE:** invasion escape boundary, encounter placement/timing/AI/flee,
party following/allocation, service layout, animation cadence, beam placement,
world bootstrap and host audio filtering. **INFERRED/UNKNOWN:** pilot ejection,
character loss and encounter loot, field technician effects, original GAME
saves, other sound contexts and the full campaign. Earlier long-route NPC/RNG
gaps and explicit later-quiz prerequisites remain documented.

**M2i sprites:** all 376 original sprite crops match the EXE's RAM, and walking tests
cover 30 player checkpoints, four exact player pixel crops and 63 NPC frame steps.
Save/load retains walking frames; older saves start a new gait at their stored
facing. Mechs appear in the animated preview, training, owned-party travel and
mixed encounters. See [sprite evidence](docs/M2_SPRITE_EVIDENCE.md).

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
the barracks dream/sleep sequence, which clears the training cooldown. The second
assignment chooses one of eight rubble locations: stand beneath it to pick it up
automatically in a Wasp or Chameleon, then return to the same reporting area.
The Locust cannot carry rubble. Second success raises the allowance cap to 250.
The third assignment requires sleep, then offers weapons training. Choose No
for computer control and select message/graphics options. Walk/Run/Jump plots
a destination: arrows show the next turn's steps and a yellow box marks the
goal. Selecting the same mode adds a waypoint, up to twelve; changing mode asks
whether to replace the route. Use Weapons assigns attacks to the shell; Done returns to orders and
Begin Fight resolves a turn. Destroy it and walk back to the instructor for
the 500-cap reward. Kick selects an enemy for a physical attack; use Next target
to cycle among opponents. Kick and weapon orders persist. General computer
control remains unsupported.
The graphics option presents original firing/Kick poses, hit reactions and
impact stars. Frame cadence and beam/projectile placement remain approximate.
Launch and dream animations
play with the original artwork; combat sound effects remain unimplemented. The fourth
assignment contains 3–6 armed labor robots and raises the cap to 1000. The fifth
is a live Locust duel, raises it to 2000 and sends Rick to the lounge. The existing
Rick/device branch is now reachable through ordinary play. The sixth assignment
fields two live Locusts and raises the cap to 3000 on success. Its original
result routine grants gunnery/Kick practice on withdrawal too. The seventh can
trigger the Jenner invasion; the eighth forces it. Escape leads to the destroyed
Citadel, retaining the surviving training mech or continuing on foot after its
loss. Pilot ejection and character-loss behavior still need original comparisons.

Mechit-Lube is at half-coordinate (15,109). Its course costs 500 C-bills and raises
the selected member's technician skill once. Talk, early no-owned-mech responses,
technician recruitment and owned-mech services use the original REPAIR.BLD.
Training loans become owned only through the original invasion-survival branch.

Watch the five-assignment/Mechit-Lube route, or the separate Kick-only victory:

```sh
./build/btech-port --smoke-replay --smoke-fast --replay tests/fixtures/ordinary-training-combat.actions
./build/btech-port --smoke-replay --smoke-fast --replay tests/fixtures/ordinary-kick.actions
python3 tools/make_training_combat_replay.py
python3 tools/make_training_combat_replay.py --kick
python3 tools/make_training_combat_replay.py --campaign
python3 tools/native_smoke.py --training-combat-only
```

Open at the third loan-mech menu, or watch the complete three-assignment route
with accelerated SDL playback:

```sh
./build/btech-port --replay tests/fixtures/ordinary-rubble-story.actions
./build/btech-port --smoke-replay --smoke-fast --replay tests/fixtures/ordinary-combat.actions
python3 tools/make_combat_replay.py
python3 tools/native_smoke.py --combat-only
```

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

**M2k–M2m:** second-assignment pickup, carrying, return/reward and third-assignment
rest gating are playable. All 22 ANMs decode independently; O0 launch and O8 dream
play in their verified contexts. The original 8×8 font and BTBORDER graphics replace
the provisional UI assets; Yes/No entrance text is aligned inside its frame.
See [rubble, story and animation evidence](docs/M2_RUBBLE_ANIMATION_EVIDENCE.md).

```sh
./build/btech-port --smoke-replay --replay tests/fixtures/ordinary-rubble-story.actions
python3 tools/verify_m2kl.py
python3 tools/native_smoke.py --rubble-only
```

The first command watches both missions, sleep and the third briefing at normal
speed (about 126 seconds), then closes. Omit `--smoke-replay` to continue from
the third mech menu. Automated window tests use `--smoke-fast`: the same route
measured 3.63 seconds instead of its normal 126.24-second tick duration, about
35× faster for this replay. Inputs, state and final image remain identical;
short keyboard, animation and F5/F9 tests retain real-time pacing. This is a
measured test improvement, not a whole-project speed estimate.

The bounded DOSBox harness runs whole JSON input sequences on a private virtual display, captures frames/state and closes automatically. It uses no interactive terminal input, so the former per-key approval loop is removed. Original binaries, screenshots and memory dumps remain in ignored directories.

Read [the milestone review](docs/PROJECT_STATUS.md), [testing](docs/TESTING.md), [banking and shop Talk evidence](docs/M2_BANKING_EVIDENCE.md), [shop purchase evidence](docs/M2_SHOPS_EVIDENCE.md), [NPC travel evidence](docs/M2_NPC_EVIDENCE.md), [Talk evidence](docs/M2_TALK_EVIDENCE.md), [Katrina evidence](docs/M2_KATRINA_EVIDENCE.md), [Hall evidence](docs/M2_CITADEL_EVIDENCE.md), [inventory](docs/ORIGINAL_FILES.md), [audit](docs/RESEARCH_AUDIT.md), [language decision](docs/LANGUAGE_DECISION.md) and [open questions](docs/OPEN_QUESTIONS.md). New code is under `port/`, automation under `tools/`/`scripts/`, regressions under `tests/`.

Both supplied reference directories remain unchanged. A local Git repository on `main` records incremental milestones; originals, reference checkout, generated assets and dependencies are ignored. No pushes were made. The final reference guard also checks the reference repository’s Git metadata. No substantial GPL source was copied or translated into the runtime; this does not establish legal clean-room status or permission to redistribute proprietary assets.
