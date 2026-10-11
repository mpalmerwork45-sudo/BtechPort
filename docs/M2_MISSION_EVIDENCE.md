# M2j — first MechWarrior mission, shops and lounge (in progress)

The authorized scope is the first MechWarrior assignment and return/sleep loop,
plus all goods in both existing shops and the MAP1 lounge. Later missions,
combat, armour repair and party recruitment remain separate work.

## Primary audit

The executable and unpacked-image SHA-256 identities are unchanged from
[M2i](M2_SPRITE_EVIDENCE.md). Independent bounded `objdump -mi8086` output is
under ignored `work/training-audit/`; reference assembly only locates routines.

| Finding | Evidence | Rating |
|---|---|---|
| MAP1 Training Center / Barracks / Lounge | MTP header slots 0 / 6 / 7, half-coordinates (46,114) / (17,13) / (17,89) | **VERIFIED** resource bytes |
| Training entrance gate | Original `0FDC:0058..0080` calls `1467:08A8` when D320 is zero | **VERIFIED** primary and ordinary original play |
| Written quiz | BTSTATS.CMP diagram; three distinct RNG-selected points out of ten, twenty answer labels; DS 28C4/28D8/28EC coordinates/answers, 4DE2 label pointers | **VERIFIED** primary and original run 1791700769071891803, points 7,5,2 and RNG states |
| Quiz failure | Any wrong answer sets D320=255 after the three questions; entry is refused | **VERIFIED** primary; live failure trace still to export |
| First briefing / mech selection | TRAINING.BLD 0229, 0A42, menu 7; Locust/Wasp/Chameleon, F5 01 | **VERIFIED** decrypted bytes and original screen |
| Mission launch | `1CD3:0027..0181`, copies selected original unit, mounts Jason, entry animation ends at (64,79) | **VERIFIED** primary and original run 1791700897500835555 |
| Southeast and return gates | `0FDC:09C4..0A02`: x>=120,y>=124; `08A7..08F9`: x<=60,73<=y<=79, requires corner visit; early return warns | **VERIFIED** primary; corner/return ordinary live trace |
| Pass/fail | `09A9..09C4`, `0C18..0C37`: update counter plus terrain penalty; Locust subtracts 50, signed result must be <215 | **VERIFIED** primary; timed live boundary not yet claimed |
| Terrain / mech footprint | `0800:1FC7..2186`, `0A42..0B40`; one loaned unit, offset (0,-2), two horizontal tile columns; terrain flag 0/8/16 feeds penalty | **VERIFIED** primary arithmetic; wider unit formations deferred |
| Mission exit position | `1CD3:01C2` sets (46,118), then original caller commits pending entrance movement | **VERIFIED** observed final (47,118) after eastward entry; other approaches require tests |
| Failure and reward | Failure increments flag 3; success clears it, increments mission flag 0 and writes cap low byte 150 (script index 51) | **VERIFIED** BLD; success live run pending |
| Sleep gate | BARRACKS.BLD requires completed mission and success; flag 19 guards repeat sleep; dream ends by clearing cooldown 20 | **VERIFIED** bytes; no-mission refusal observed; successful sleep pending |
| Dream EA 08 01 | VM `0FDC:0494` requests original animation 8 with parameter 1 via `0800:48B7` | **VERIFIED** primary; this is an animation request, not an audio opcode |
| Shop roster | DS 4F44 prices: 11 weapons; DS 4F26/4DDB: five armour types, protection 25/40/30/50/50 | **VERIFIED** primary. Existing two-item live regressions remain; full roster capture pending |
| Lounge | LOUNGE.BLD menu 24; room 7 Talk; Rick handler `0FDC:18C6..18F3`, flags 45/46/47 | **VERIFIED** script/primary. Ordinary and explicitly controlled event captures pending |

`reference_session.py` runs bounded whole scripts on private displays. Its
`quiz-answer` helper reads the original white diagram box and sends normal
menu keys; it never writes memory. Shop coverage uses an explicitly recorded
20000-C-bill budget precondition in the child emulator to exercise every price;
it is not a claim of ordinary campaign funding. The lounge Rick event uses a
separate, explicit occupancy/recruitment precondition; natural conversations
and the mission route do not inject progress. Assets, screenshots, guest RAM,
working DOS files and generated text caches stay ignored.

The first successful quiz and a real failed mission demonstrate feasibility.
The native implementation must preserve the quiz, typed success/failure state,
loaned mech, reward cap, return movement, and dream/sleep gates. Unknown native
services must continue to fail visibly. UI font, pacing and unrecovered animation
presentation remain **APPROXIMATE**; subsequent training/combat is **UNKNOWN**.
