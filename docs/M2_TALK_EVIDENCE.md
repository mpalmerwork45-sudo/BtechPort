# M2c — bounded Citadel Talk handler, 2026-10-11

## Scope and authority

**VERIFIED:** the unpatched supplied v1.03 executable implements `F5 0C` as an NPC interaction, not a close/no-op action. [The dispatcher](../UnBattletech/reko/segments/UNBTECH_1CD3.c:937) calls [0FDC:17B9](../UnBattletech/reko/segments/UNBTECH_0FDC.c:1719). Independently unpacked original code at image `09579..097A0` confirms its byte reads, room matching, selection, text sources, result writes and return. The reference recreation's `CLOSE_ACTION` label/no-op disagrees with the binary and live execution. No GPL routine was copied or translated into the new implementation.

**VERIFIED, unmodified new game:** `work/reference-runs/1791684527855747449` follows the M2a entry route, chooses Talk, shows the original empty-room message and returns on a key. Repeated attempts retain Citadel choice 3. Byte `D319` (modeled state 13) changes 0→1 and persists. Credits stay 35, position stays `(69,21)` in the building. All eight occupancy bytes are zero. A separate 25-second outdoor wait (`1791684754758962710`) still produced an empty Citadel. NPCs move only within a region near the player; waiting does not establish a naturally reached conversation.

**VERIFIED, explicitly controlled precondition:** `work/reference-runs/1791685190039219738` runs [reference-talk.json](../tools/reference-talk.json). Once the ordinary Citadel menu is reached, the harness applies [talk-context.json](../tests/fixtures/talk-context.json) to the *running working copy*: eight `D398/D399` pairs (26-byte stride) and result byte `D33A`. Slot 1 has packed byte `12` hex, occupancy 1; the result is seeded to decimal 91. The other occupancies remain zero. `controlled-context.json` records before/after bytes and addresses; precondition snapshots are preserved. Executable/resource/save files are unchanged. Subsequent observations exercise the original handler. This does **not** verify NPC arrival, save loading, or a naturally reached campaign state.

[reference-talk.json](../tests/fixtures/reference-talk.json) commits numeric checkpoints and text hashes only. It records the source/image/payload hashes. Proprietary text, frames, RAM and generated cache stay ignored. Original screenshots were inspected for the menu, highlights, reply, return and exit. Script PC `10E2` hex is bytecode-derived, not a captured interpreter instruction pointer.

## Recovered local handler

1. Citadel bytecode at `10DD` performs `F4 0D 01`, then `F5 0C` at `10E0`. On native return, `F8 0000` rebuilds the menu; its highlight remains 3.
2. Find the first of eight entries in the table addressed by `DS:[5460]:4602` equal to `D319`. In MAP1, header offset 517 contains this table; the Citadel is room slot 1. A nonzero `D399 + 26*i` and `((D398 + 26*i) >> 4) & 7 == room` identify an occupant.
3. No occupants: clear the text panel, print common-DS `16DE`, wait for a key, return. No NPC menu or result write occurs.
4. Occupants: print DS `170E`, names from relative segment `1C6C:A461 + 16*i` in slot order, a carriage return after each, and DS `1728` for Done. NPC names come from MAP1 header `5 + 16*i`. Original menu ID is `14` hex (20), count is occupants + 1. Selection is separate from the Citadel menu and persists across repeated calls.
5. Done: return immediately, preserving `D33A`. The controlled trace verifies 91 remains 91.
6. Select an NPC in the local Citadel: clear `D33A` to 0; print DS `172D`, activity text from the far-pointer table at DS `4E32 + 4*D319`, DS `1761`, destination name selected by the occupant's packed low three bits, then DS `178F`. Destination names come from MAP1 header `133 + 16*destination`. Wait for a key, then return to the Citadel menu.

The observed reply uses activity 1 and destination 2. The full logical text is **162 bytes**, hash recorded in the fixture. The NPC menu is **42 bytes**. The controlled trace verifies the result becomes 0, modeled bytes 0..22 otherwise retain their values, credits remain 35 and NPC pairs stay unchanged until leaving the building. Done and NPC selection both preserve outer-menu choice 3. Leaving commits the deferred step to `(69,20)`.

## Text provenance

The independently written [prepare_talk.py](../tools/prepare_talk.py) reuses our [EXEPACK reader](../tools/exepack.py), requiring the audited executable SHA-256 `15a1712682cf1fe50ca9e6a68a4b31d3bef7912401915edf7bb6242be193562a` and unrelocated image SHA-256 `100f0df244e4b0c8693d1b5013fb073f486b35d6f5c538ecd53d03f85ed54bfa`.

Common DS has image base `36DB0`. Six literal offsets are `16DE`, `170E`, `1728`, `172D`, `1761`, `178F`; eleven activity strings use the original far-pointer table `4E32..4E5D`. Unrelocated segments are relative to the image, without subtracting Reko's `0800` load base. The 718-byte ignored BTT1 cache and JSON sidecar preserve source/image hashes, original addresses, sizes and string hashes. Upper/lower case and spaces are retained. MAP1 names are read at runtime. Cache validity/provenance tags do not establish redistribution rights.

## Limits

**VERIFIED from primary code:** the exercised local reply makes no random draw. The outer-world reply instead uses `207F:0BC0 & 7` and table `4E5E`; special recruitment uses `D339`, room 7 and slot 0. Those branches are unsupported diagnostics in this slice, not substituted outcomes.

**INFERRED:** generalization to multiple occupants and changing counts; C tests cover ordering/bounds but a multi-occupant live oracle is not yet captured. **APPROXIMATE:** mixed-case font, layout, imagery, input and timing. **UNKNOWN/unimplemented:** complete NPC travel/pathfinding, initialization/RNG parity, original GAME round trips, other buildings and later campaign context. The original resumes NPC movement on exit (slot 1 changes to `[39,6]` in this trace); the native slice holds its context, so post-exit NPC equality is excluded. Day/countdown pacing remains deferred. A visible conversation checkpoint makes the native handler playable without pretending that NPC travel has been implemented.
