# M2b Katrina evidence — 2026-10-11

Scope: fresh-game Citadel entry → first Katrina conversation → menu → repeat request → denial → leave → re-enter. This extends the [M2a evidence](M2_CITADEL_EVIDENCE.md). Original files and both reference trees remain immutable.

## Original observations

**VERIFIED:** bounded DOSBox run `work/reference-runs/1791683236787259649` captures 20 checkpoints. [The factual fixture](../tests/fixtures/reference-katrina.json) records coordinates, state bytes, credits, text ranges/hashes and screenshot-observed menu selections without embedding dialogue or graphics. [The input script](../tools/reference-katrina.json) runs on a private display and closes automatically:

```sh
python3 tools/reference_session.py --script tools/reference-katrina.json
```

Selecting menu choice 0 first shows the sentry message, then Katrina's conversation, then returns with choice 0 selected. State byte 6 at `D30C+6` changes from 0 to 1 while her text is displayed. Byte 10 remains 1. Bytes 0–21 otherwise remain unchanged, including after exit and re-entry. Credits remain 35. A second request uses a different sentry message, waits once and returns without changing byte 6. Re-entry retains choice 4 (Leave), rather than resetting the highlight.

**VERIFIED:** `F4 16 FF` sets byte 22 to 255 before the conversation pause. It stays 255 in the building, but decreases after returning outdoors: 238 at the recorded exit, 228 after the south step and 227 at re-entry. Byte 23 also decreases outdoors. These are timed observations, not stable quest-state constants. Secondary main-loop evidence is `UnBattletech/reko/segments/UNBTECH_0800.c` around the `D322`/`D323` decrements. **INFERRED:** byte 22 is an availability countdown because another Katrina branch tests it. Complete countdown pacing, day/economy effects and later trained-player conversations are outside M2b. Compare byte 22 exactly only before outdoor countdown resumes; persistent progression comparison uses bytes 0–21.

**VERIFIED:** screens and resource bytes use upper and lower case. The native diagnostic font previously forced uppercase. Independent lowercase glyphs now preserve case; authentic original glyph shapes and wrapping remain **APPROXIMATE**.

## Required bytecode facts

The same 4328-byte decoded Citadel payload matches original guest RAM. The interpreter is `0FDC:01C0` in the secondary address convention (load base `0800`). Independent disassembly of `work/unpacked-image.bin` confirms byte widths and signed extension; no secondary implementation is copied.

| Opcode | Behavior | Primary evidence |
|---|---|---|
| `F1 index value` | Add to one state byte, wrapping modulo 256 | Original `ADD BYTE PTR` at `0FDC:035F`, image offset `0x811F` |
| `F3 index table…` | Select little-endian payload target using twice the signed state-byte value | Original byte load / `CBW` / shift at `0FDC:0324–032A`, image offsets `0x80E4–80EA` |
| `F4 index value` | Set one state byte | Original `MOV BYTE PTR` at `0FDC:0309`, image offset `0x80C9` |
| `F7 index target` | Jump if that state byte is nonzero; otherwise skip the target word | Original byte comparison at `0FDC:02AB`, image offset `0x806B` |
| consecutive `FC` blocks | Append text without an implicit separator; `FD` clears it | Three blocks form the observed Katrina screen, including a word split across blocks |

**VERIFIED in this route:** `F3 06` at payload `0xEB` has targets `0xF3`, `0x34C`, `0x650`. The apparent `F3 00` at `0xED` is the first table word, not another instruction. State 6 = 0 reaches the first sentry text (offset 244, length 180), then `FB` with resume PC `0x1AA`. Her untrained-player conversation concatenates `(428,80)`, `(514,122)`, `(756,76)` into 278 bytes. It executes `F4 16 FF`, `F1 06 01`, `F2`, `FB` and pauses at resume PC `0x349`. `F8 0000` returns to the menu. State 6 = 1 reaches `F7 00` at `0x34C`; with state 0 still zero it displays `(849,208)`, then pauses at PC `0x424` and returns to the menu. Other state variants are bytecode-supported facts, not live-verified campaign paths.

Reproduce the primary instruction check:

```sh
objdump -D -b binary -m i8086 -M intel --start-address=32856 --stop-address=33060 work/unpacked-image.bin
```

The generated secondary C incorrectly suggests wider writes for `F1`/`F4`; the executable uses bytes. State indexes are sign-extended by the original. This milestone deliberately bounds the modeled state window to indices 0–22; other indexes produce an explicit diagnostic.

## Implementation and verification boundaries

M2b implements original-text concatenation, checked state branches/setters, persistence of the first conversation result, retained selection on re-entry, and restoration during either pause. The internal encoding is 128-byte BTP3, preserving 23 state bytes, up to eight text spans and the failed-choice recovery checkpoint; BTP1/BTP2 migrate. This does not imply original GAME compatibility or a save/load UI. Unknown menus/native actions fail visibly. Failed class/talk choices roll back partial writes, including those before a saved pause; Backspace returns to the menu. That recovery is a prototype control, not original behavior.

Original countdown/day timing, authentic fonts/scene animation, economy, combat and later campaign progression remain unverified or unavailable. No whole-screen, timing or campaign parity is claimed. Code is independently written from original bytes, live observations and factual dispatch evidence; this is not a legal clean-room claim.

**M2b validation passed:** 319 core/corpus/state checks, 88 script checks, all three canonical scenarios, native dummy/private-X11 replay checks and headless ASan/UBSan/LeakSanitizer. `python3 tools/verify_m2b.py --reference-run work/reference-runs/1791683236787259649` compares the fixture/core with all 20 original snapshots and decoded RAM payloads. Text hashes preserve the original case and concatenate exact resource bytes. Byte 22 matches only before outdoor timing resumes; afterward the native slice deliberately retains its last script-set value. Both supplied trees still match the 1287-entry baseline. See [TESTING.md](TESTING.md) for commands and limits.
