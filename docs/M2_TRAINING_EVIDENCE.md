# M2h — paid Class and outdoor cooldown evidence

Research audited on 2026-10-11. Implementation and milestone verification are
in progress. This is the first paid personal-skill training loop; MechWarrior
training missions, mission results and barracks sleeping remain separate work.

## Authority and reproducible original runs

The unmodified local v1.03 `Original DOS/BTECH.EXE` is the authority, SHA-256
`15a1712682cf1fe50ca9e6a68a4b31d3bef7912401915edf7bb6242be193562a`.
Our independently unpacked image hashes to
`100f0df244e4b0c8693d1b5013fb073f486b35d6f5c538ecd53d03f85ed54bfa`.
Reference tooling copies the immutable originals into `work/` and runs a whole
bounded script on its own virtual display. No per-key terminal interaction is
needed; no reference source, asset or executable is patched.

```sh
python3 tools/reference_session.py --virtual --script tools/reference-class-audit.json
python3 tools/reference_session.py --virtual --script tools/reference-class-funded.json
python3 tools/verify_m2h.py --export audit
python3 tools/verify_m2h.py --export funded
python3 tools/verify_m2h.py --reference-run work/reference-runs/1791697254944153773
```

The audit run `1791696349743334353` supplies 15 checkpoints: Katrina visit,
Class introduction/offer, insufficient tuition and return. The ordinary funded
run `1791697254944153773` supplies 49 checkpoints: walk to ComStar, invest all
35 in BakPhar, wait for the original return, sell 72, walk back to Citadel,
pay tuition, complete the course, receive the cooldown denial, leave and wait,
then obtain the more expensive course offer and its insufficient-funds reply.
Fixtures contain only numbers, inputs and text hashes. Proprietary RAM dumps,
screenshots and dialogue bytes stay under ignored `work/`.

Two earlier funded driving attempts (`1791696788067223564` and
`1791697026329554956`) lost keys during the original F2 delay/keyboard flush
and stayed in ComStar. They are exploratory failures, excluded from the
successful fixtures. The final script gives each critical Return time to finish
the original delay before submitting the next key.

## Verified rules and source addresses

| Rule | Primary evidence | Confidence |
|---|---|---|
| Three personal weapon-skill ranks, independent of owned weapons | State segment `C618..C61A`; live rank `[0,0,0]` becomes `[1,0,0]` | VERIFIED |
| Tuition `75 + 125 * rank` | Unpacked image `14F61..14FD3` (F5 04), signed-byte IMUL then add 75; valid ranks 0..4 | VERIFIED by instructions; initial/next prices also live |
| Current-rank transcript, selected subject, unsigned 32-bit cash comparison, one-rank increase and exact debit | `14FD5..150A9` (F5 05), rank/subject far-pointer tables `DS:4EA2..4EC1`, cash `D370..D373` | VERIFIED by instructions; course 0 rank 0 success/refusal also live |
| Rank 4 refuses as mastered without debit; insufficient funds also preserve ranks/cash | `1502B..150A9`; outcome byte `D315` is 0 on either refusal, 1 on success | VERIFIED by instructions; no-funds path also live |
| First Class sets introduction flag 7 and clears cooldown 21 | CITADEL branch `0CFA`, text `0D03`, state writes before pause | VERIFIED by BLD and live RAM |
| Course menu 9 has three subjects and Withdraw | CITADEL `0F05..0F0E`; selection writes flag 8; native calls F5 04/05 | VERIFIED by BLD and live screens/RAM |
| Successful course completion sets cooldown byte 21 to 255 | CITADEL `0F75..0F79`, completion text `0F7A`, resumes `10DA` | VERIFIED by BLD and live RAM |
| Immediate re-enrolment is denied; courses reopen when cooldown expires | CITADEL branch checks flag 21; denial text `0F10`, resumes `0F55` | VERIFIED by BLD and live trace |
| Bytes 20, 21, 22 decrement once per outdoor frame when nonzero and saturate at zero; stop indoors | Unpacked image `002C7..002ED`, before economic timer decrement; live indoor 255, then outdoor 240/189/138/87/36/0 | VERIFIED by instructions and checkpoint trace |
| Personal Class does not complete a MechWarrior mission or unlock barracks sleep | Funded trace leaves flag 0 at 0; BARRACKS checks mission flags 0/1; TRAINING is a separate BLD | VERIFIED bounded distinction |

The good funded course pays 75 from 87, leaving **12 cash and skill `[1,0,0]`**.
The ordinary post-course allowance raises cash to **27** while the cooldown
expires. Re-entry offers tuition **200**, then refuses without changing either
cash or skills. No injected funding, skill ranks or mission progress is used.

Original native strings are extracted from the audited image: `DS:491A`,
`4948`, `4999`, rank table `4EA2`, subject table `4EB6`, and `4F7E` for the
come-back response. BLD text is read from CITADEL at runtime. No substantial
GPL source is copied or translated into the independent C implementation.
Secondary labels in `UnBattletech/reko/` helped locate these routines; generic
shop labels there do not establish their personal-skill semantics.

The two read-only outdoor captures contain 205 funding samples and 257 cooldown
samples. Their projections contain all eight NPCs, RNG/search, loop counter,
player, cash, three balances and allowance cap (70 fields). Skill ranks and
cooldown bytes are established by the separate RAM checkpoints; they were not
fields in this frame observer and are not claimed as per-frame measurements.

## Bounded implementation and verification

To be completed with the final implementation results and native checks.
Higher-rank tuition, all three subjects and mastery can be checked directly
against the primary instructions; only the first subject's first paid course
is claimed as live original paid-course parity in these ordinary traces.
