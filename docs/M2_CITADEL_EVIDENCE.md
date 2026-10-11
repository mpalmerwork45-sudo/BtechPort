# M2a Citadel evidence — 2026-10-11

Scope: MAP1 north entrance → Hall of Legends → six text screens → menu → leave → one south step. The original executable remains the authority. This is a bounded M2a step, not completed M2 campaign foundations.

## Original observations

**VERIFIED:** the supplied `CITADEL.BLD` is 4330 bytes; its little-endian size word is 4328. Decode the payload after that word with `((byte + 41) & 255) ^ 233`. Its SHA-256 is `7e64ec068d521347b52cf819344c9d5acf6ad0b10b84b9ebaca91cbf88673fd7`. All 4328 decoded bytes match guest RAM at `0x2A3E0` (runtime segment `0x2A34`, offset `0xA0`). `0FDC:1D30` supplies corroborating loader/decryption evidence. Disk offsets, script-relative addresses and runtime addresses must remain distinct.

**VERIFIED:** MAP1 slot 1 contains packed entrance words `0x0C45:0xC014`, low seven-bit half coordinates `(69,20)`. A northward step from `(69,21)` opens the Yes/No entry prompt while both cursor and party[0] retain `(69,21)`. Accepting runs building index 1. Leaving finishes the pending north step at `(69,20)`; a south step reaches `(69,21)`. Gate remains 85; the MAP1 payload remains resident.

The menu has five original choices. Selecting index 1 enters Hall of Legends at payload offset `0x6A4`; six `FC` text blocks appear in order. One Space per screen advances the dialogue; the menu returns with index 1 still selected. Three Down presses select index 4, whose target is `0x10E5` (`FF`). Credits remain 35 throughout this recorded path. The first 16 state bytes at state-relative `0xD30C` remain zero except index 10, set to 1 on entry and still 1 after exit. **UNKNOWN:** a complete semantic name for that flag. The original wrapper writes `D316`; it must not be treated as a mode bit that clears on leaving.

The final successful run is `work/reference-runs/1791682077232453392`. Captures and full RAM dumps are ignored artifacts; factual positions, flag values, resource/text hashes and offsets are committed in [the canonical fixture](../tests/fixtures/reference-citadel.json). Modes in that fixture are identified from captured screens, not from an assumed memory enum. Script PCs are established from original bytecode and corroborating interpreter evidence, not a captured instruction pointer.

Replay the bounded sequence:

```sh
python3 tools/reference_session.py --script tools/reference-citadel.json
```

The harness uses a private Xvfb display and copied resources, reads only its own emulator child and terminates automatically. Explicit waits are necessary: the original arrival animation and text printing can swallow early menu inputs. No interactive terminal input is used.

## Minimum opcode facts

Interpreter evidence is `UnBattletech/reko/segments/UNBTECH_0FDC.c`, routine `0FDC:01C0`. That code was read for factual dispatch/operand relationships; it is not copied or translated into the independent runtime.

| Opcode | Required behavior | Evidence and confidence |
|---|---|---|
| `FE n` | Presentation/font configuration | Operand 6 in Citadel prefix; **INFERRED** broader font semantics (`1E56:0281`) |
| `FD` | Clear text panel | **VERIFIED** at menu and each Hall text; `1E56:0388` |
| `FA n` | Request original scene/animation | Scene 0 in prefix; **VERIFIED** request, **UNKNOWN** complete animation dispatch/rendering |
| `FC text\0` | Display original text | **VERIFIED** all seven text blocks, runtime bytes and screen order |
| `F2` | Software delay(50), then flush pending input | **INFERRED** from `1F3D:086A` → `1F3D:0006` and `0800:2A2B`; exact timing **UNKNOWN** |
| `FB` | Wait for key | **VERIFIED** six pauses; `1F3D:0259` |
| `F8 word` | Jump relative to payload start | **VERIFIED** `F8 0000` returns to the menu; `0FDC:05F7` |
| `F9 n` | Indexed menu jump table | **VERIFIED** menu ID 8, five little-endian targets, retained highlight |
| `FF` | End script | **VERIFIED** leave target and resumed outdoor movement |

Substantial corrections to secondary notes: encrypted disk `C0` bytes are not executable no-ops; decrypt before interpretation. `F2` is not a room-description operation. `0800:2A2B` drains pending keys, despite a misleading “wait-for-key” label. The other three Citadel branches need additional opcodes/native actions; they must produce visible unsupported diagnostics in this milestone.

## Implementation limits

Only menu ID 8, font request 6 and scene request 0 are supported. Unknown opcodes, other menus/fonts/scenes, truncated operands/text, invalid targets and execution loops stop with explicit errors. Native glyphs, scene imagery, pacing and input flushing remain **APPROXIMATE**; whole-screen/pixel or timing parity is not claimed. `F2`'s delay request is stored explicitly without reproducing its original timing/flush. Quest progression, combat class, conversations, shops, economy and other building interiors remain unavailable.

**M2a validation passed:** 231 core/corpus/state checks, 47 script checks, both canonical replays, native dummy/private-X11 scenarios with recorded replay, and headless ASan/UBSan/LeakSanitizer. `tools/verify_m2.py --reference-run work/reference-runs/1791682077232453392` checks the factual fixture against the original snapshots and full decrypted RAM payload. See [TESTING.md](TESTING.md) for limits and commands.

Code provenance: independent C written from original data, live observations and factual format/dispatch evidence. No substantial GPL implementation source is reused. This is not a legal clean-room claim.
