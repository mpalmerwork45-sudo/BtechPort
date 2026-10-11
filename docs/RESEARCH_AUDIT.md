# Research audit — M0/M1 with M2a–M2f findings, 2026-10-11

Local reference revision: `86e1b637c39a713547cfa2aa2149d744b995acfc` (2026-09-29). Its README explicitly separates reverse engineering from an unvalidated Godot reconstruction. Both supplied directories are immutable for this assignment, including reference git metadata. Local agent instructions to update/push the reference wiki are superseded by the user's instruction to leave it unchanged and never push.

Confidence is scoped: **VERIFIED** means the stated fact was checked against bytes, machine code, or a recorded original observation; **INFERRED** means a supported interpretation still awaiting a direct check; **APPROXIMATE** means knowingly simplified behavior; **UNKNOWN** means unestablished. Passing an extraction round trip does not verify script semantics.

| Subsystem | Source of evidence | Confidence | Reusable tools/data | Important gaps | Proposed verification |
|---|---|---|---|---|---|
| World generation | [world-map.md](../UnBattletech/docs/world-map.md); [135D decompilation](../UnBattletech/reko/segments/UNBTECH_135D.c) `01E9`, `0AB6`; [0800](../UnBattletech/reko/segments/UNBTECH_0800.c) `32B3` | **VERIFIED** local maps are stored; **INFERRED/UNKNOWN** complete outer-terrain generation | MTP files; `MAP15.MTP` star map; original executable | The alleged 64×64 global map may conflate a local/working buffer with world geography. A buffer differing from an EXE image does not prove procedural terrain or a static template. | Trace outer-map entry and regeneration at multiple coordinates/seeds; compare loaded MTP blocks and generated areas. Do not invent a global map file. |
| Local maps | Actual MTP headers/payloads; [map triggers](../UnBattletech/docs/formats/map-bld-triggers.md); [NPC evidence](M2_NPC_EVIDENCE.md) | **VERIFIED** 541-byte header, dimensions, block order, MAP1 position/translation bytes, names, first eight waypoints and route table at 533–540; **INFERRED** broader header semantics | `InceptionTools/FileTypes/MAP.cs` as format evidence; converted PNGs for independent comparisons | 8×8, 32×32, 64×64 local maps; headerless MAP15 is a different format. | Compare additional runtime map bytes, entrances and rendered tiles with DOSBox. |
| Graphics | Actual ICN/CMP signed-RLE runs; [file formats](../UnBattletech/docs/formats/file-formats.md); original frames | **VERIFIED** all 12 decode to 32,000 packed bytes; C BTTLTECH equals all secondary PNG pixels; recorded MAP1 viewport/remap | Authentic original resources; reference PNGs as checks only | Python extractor handles negative runs incorrectly. Disk pixels are packed nibbles, separate from planar hardware. Player/NPC overlays and other-mode palettes remain unverified. | Passed parser/corpus tests; original MAP1 panel 98.669% equal in the compared frame. Extend mode/sprite validation. |
| Animations | [ANM notes](../UnBattletech/docs/formats/anm-format.md), 22 actual ANMs | **INFERRED** XOR-delta RLE; **UNKNOWN** dispatch/timing parity | Existing converted animation sheets and C# tooling | Notes disagree about flag 0x32 and O21 corruption. O21 here is binary, not textual hex. Building mappings vary by docs; avoid guessing them. | Validate frame lengths, accumulator behavior, and original animation dispatch. |
| BLD/story | [Bank/Talk evidence](M2_BANKING_EVIDENCE.md); [shop evidence](M2_SHOPS_EVIDENCE.md); [Citadel evidence](M2_CITADEL_EVIDENCE.md); [Katrina evidence](M2_KATRINA_EVIDENCE.md); [BLD specification](../UnBattletech/docs/formats/bld-bytecode.md); original-image disassembly | **VERIFIED** 26 raw round trips; bounded Citadel/shops/ComStar paths, native suspension, accounts/numeric input, F6 confirmations, positioned text and shop Talk; **INFERRED/UNKNOWN** broader actions/flags | Whole-input DOS traces, independent C VM and milestone verifiers; converter for byte preservation only | F2 is delay/flush, not description; F1/F4 writes are byte-sized; byte 22 is a countdown. F5 0C is a real NPC handler; bank receipt uses bytecode wait without an extra pause. Class faults visibly. | Prior and M2f text/state/return/persistence projections pass. Broader training/day/campaign remains open. |
| Input/movement/collision | [input notes](../UnBattletech/docs/engine/input-navigation.md); [1631](../UnBattletech/reko/segments/UNBTECH_1631.c) `0006`; [0800](../UnBattletech/reko/segments/UNBTECH_0800.c) `1C12`; own movement/Citadel fixtures | **VERIFIED** 31 movement states, collision offset, Citadel and two-shop pending-step/exit; Citadel re-entry; **INFERRED** broader model | Bounded DOSBox harness; native deterministic actions | +0x7AD is a 24×24 working grid, not a property LUT. Other gates, party footprints, entrances/rearming and edges remain unproven. | Passed cursor AND party[0] projections for movement, Hall and Katrina routes. Next: multi-unit footprint and other entrances. |
| Local NPC travel/RNG | [NPC evidence](M2_NPC_EVIDENCE.md); [bank corpus](M2_BANKING_EVIDENCE.md); primary image 024C2–02866, 0E316–0E5F3, 0F9FE–0FB59 and 193B0–193EA | **VERIFIED** 570 earlier + 459 bank complete steps, two arrivals and naturally reachable Citadel reply; **INFERRED** unobserved steps | Independent C routine, two numeric corpora, 56 natural-route checkpoints, read-only observer/verifiers | Human footprint is exact equality; wider branch applies to other unit slots. Original M2d skips 68 player-movement gaps; bank corpus skips none. Complete startup, world/edge/party/global RNG remain open. | All positions/destinations/directions/timers/phase/RNG/search and persistence pass, including investments/allowance draws through bank wraps. |
| Inventory/economy | [Bank/Talk evidence](M2_BANKING_EVIDENCE.md); [shop evidence](M2_SHOPS_EVIDENCE.md); original COMSTAR/ARMOR/WEAPON; primary image 150AA–15817, 919E–9578, 02EE–0449 and math helpers | **VERIFIED** two purchases, No/insufficient funds, three stock accounts, buy/sell clipping/zero/unfunded/unowned, local allowances/returns; **UNKNOWN** wider economy/shop parity | 121 purchase + 62 bank/rates checkpoints, 459 full economy/NPC frames, authentic BLDs, native/persistence/sanitizer checks | D374/D378/D37C are investments; supposed D390 stocks alias NPCs. Native math writes balances; it is not display-only. Remaining goods, repair, party assignment, cap/day gates deferred. | Passed original RAM/text/state, all accounts/NPC/RNG through two wraps, every-tick persistence. Wider cap/day progression needs its own audit. |
| Combat | [combat-system.md](../UnBattletech/docs/combat-system.md); [segment recovery](../UnBattletech/docs/engine/segments-19ef-1000.md); `reko/gencode{,-current}/` | **VERIFIED** recovered code is present; **INFERRED** formula reconstructions; **UNKNOWN** differential parity | Generated code, formula notes, older traces | README's missing-segment statement is stale. WIP reports deeper formula recovery, but no end-to-end differential harness. Its “no salvage wording in BLD” does not imply no salvage: BTECH.EXE contains salvage messages. | Original RNG/attack/heat/AI/aftermath traces; avoid the Godot combat loop as specification. |
| Save/load | Six GAME files + three backups; [SaveFile](../UnBattletech/InceptionTools/FileTypes/SaveFile.cs); independent BTP7 tests | **VERIFIED** local originals are 3913 bytes; 384-byte internal state restores all new/earlier replay paths; **UNKNOWN** GAME round-trip semantics | Original structure notes/saves, independent versioned encoder | Reference claims 4096 bytes. BTP7 is internal state without a player-facing UI; it does not establish original import/export. | Proposed M2g: expose internal save/load and verify restart continuation. Separate original load→save→reload audit before compatibility. |
| Timing | [viewport/main loop](../UnBattletech/docs/engine/viewport.md); [NPC evidence](M2_NPC_EVIDENCE.md); primary 0800 main loop | **VERIFIED** observed player-before-NPC order, three-phase NPC update, loop-timer/RNG schedule and building freeze; **UNKNOWN** exact cadence | Original normal-core DOSBox run; timer/address notes | `w014A` has different processing levels; animation/key repeats and other timers not calibrated. One original frame per four 32ms native ticks is approximate. | Controlled input intervals plus logical snapshots; preserve fixed-step replay while calibrating. |
| Audio | WWOODBT.SIF and executable; reference's stated gap | **UNKNOWN** sound-driver/music roles | DOSBox (muted for repeatability) | No decoded audio/music model. | Trace file accesses/interrupts; locate and decode sequences before implementation. |

## Tool validation and reproducible runtime

`PYTHONDONTWRITEBYTECODE=1 python3 UnBattletech/tools/bld/bld_json_converter.py roundtrip work/dos` checked all 26 scripts without writing to the reference tree. `BldParser` + `json_to_bld` preserve bytes, while their annotations remain provisional.

The Python asset extractor was imported with bytecode writes disabled and exercised only under `work/extraction/`. A minimal signed repeat (`F9 FF`, seven FF bytes) is mishandled by `decompress_format_01`; authentic BTBORDER begins with this pattern. Its generated images are excluded as an oracle. An independent signed-RLE audit decoded every ICN/CMP to exactly 32,000 bytes; BTTLTECH RGB pixels and MAP1 block-layout pixels match existing reference PNGs exactly. These checks verify data layout, not Godot behavior.

Spice86 is not practical here: no dotnet executable, no matching ../../Spice86 source tree, no prebuilt UNBATTLETECH binary. Its net10.0/source dependency is recorded, not repaired inside the reference.

DOSBox 0.74-3 and required small libraries were downloaded from the configured Ubuntu archive and extracted under `local-deps/`. Xvfb supplies a private display. `python3 tools/reference_session.py --script tools/reference-movement.json` mounts only `work/dos/` (a byte-identical initial copy); the executable remains unpatched. A bounded JSON sequence controls inputs/captures and closes the emulator, without interactive terminal writes or the user's keyboard focus. Commands, canonical state projections and exact deviations are in [TESTING.md](TESTING.md). Proprietary screenshots/dumps stay in ignored `work/`.

## Feasibility and M1 scope

**Built and tested in M1:** independent C11/SDL2 MAP1 terrain/movement, headless core and deterministic replay. Thirty actions match 31 original cursor and party[0] states; collision samples `ceil(X/2), floor(Y/2)`. The 24×24 grid matches 576 MAP1 bytes. Sprite/status UI, cadence and map edges remain approximate.

**M2a extension:** independently decrypted Citadel payload matches all 4328 runtime bytes. Entry → six Hall screens → retained menu choice → exit is playable and covered by 16 original checkpoints.

**M2b extension:** first Katrina conversation → repeat denial → exit/re-entry is playable and covered by 20 checkpoints. Original case/text blocks, byte 6 persistence and re-entry selection are verified; outdoor byte-22 pacing remains deferred.

**M2c extension:** `F5 0C` is the original NPC interaction, despite the reference no-op/close label. The empty response and one explicitly controlled local conversation/Done/return are covered by 13 original checkpoints. Primary code establishes no RNG draw in the exercised reply. Executable literals use a reproducible ignored cache; MAP1 supplies names. See [Talk evidence](M2_TALK_EVIDENCE.md).

**M2d extension:** independent local NPC travel makes that reply reachable through exploration. Complete frame comparisons include direction/collision/proximity, timer/route transitions, search and RNG. Fifty-six original player/story checkpoints and full private-X11 native replay pass. Both reference directories remain unchanged. Exact cadence, complete startup, world/party/edge rules, general economy and original NPC imagery remain deferred. See [NPC evidence](M2_NPC_EVIDENCE.md) and [PROJECT_STATUS.md](PROJECT_STATUS.md).

**M2e extension:** two local shops use their actual BLD menus, confirmation and
native buy services. Ordinary original traces prove 50→0 flak vest and 15→13
knife transactions, No/insufficient funds, equipment fields and return. The local
zero-investment allowance funds both transactions and keeps RNG draws consistent.
Both complete replays restore identically at all 6137 ticks; native SDL and
headless sanitizers pass. [Shop evidence](M2_SHOPS_EVIDENCE.md) records exact
addresses, scope and 121 checkpoints. Remaining transactions and wider economy
are deferred. Stop for this bounded review.

**M2f extension:** ComStar uses its actual investment interface and BLD paths,
with native F5 06/07/08 account display/buy/sell. Primary numeric-editor code
establishes seven digits, Backspace, Escape clear and Enter submit. All three
balances participate in pre-update asset comparison and eligible-wrap returns;
cap 50 is the verified local context. Primary code contradicts provisional
display-only return helpers and eight stock records at D390 (actually NPC data).

Both shop F5 0C paths now support empty/occupied Talk, names, Done and local
replies. Occupied-handler checks explicitly control two NPC pairs/result in
working-copy RAM with before/after audits; ordinary bank/empty-shop runs are
unmodified. All 160 new checkpoints and 459 gap-free full outdoor frame steps
pass. The latter corrects the human collision footprint from primary
`0F9FE..0FA88`: exact coordinate equality; the wider unit-slot branch is absent
in this cadet state. Earlier M2d's 570 complete steps still pass. All 7297 new
replay ticks restore identically in BTP7; five native SDL checks and headless
sanitizers pass. See [banking/Talk evidence](M2_BANKING_EVIDENCE.md). Natural
occupied-shop arrivals, wider party/world/day context and original saves remain
open. Stop for M2f review; proposed M2g exposes internal save/load to the player.

## Provenance

No GPL runtime code is copied or mechanically translated. Reference GPL tools are executed solely for extraction audits. New parsers/core are independently written from factual formats, original bytes, and observations; this is **not** a claim of legal clean-room status. SDL headers/binaries, DOSBox, and other local dependencies remain excluded from commits. No public distribution is attempted. Any future substantial GPL incorporation or distribution decision requires the user's review.

EXEPACK identity and decoding were checked against the original `RB` header and an independently written backward-RLE spike. The only supplementary web question was this executable packaging; the format description used was the [unEXEPACK author's README](https://github.com/w4kfu/unEXEPACK#exepack-header). No remote unpacker source was copied or executed.
