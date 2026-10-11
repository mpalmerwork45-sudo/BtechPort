# M3b — physical combat, Mechit-Lube, fourth and fifth assignments

Work in progress. Primary evidence is the audited owner's BTECH.EXE and BLD
resources; the ignored instruction oracle executes those bytes in private RAM.
No reference runtime or GPL game implementation is part of the port.

* **VERIFIED:** `07DC:074D` draws `3 + (RNG & 3)` labor robots for assignment
  index 3. `07DC:0D49` creates their original 17-byte C614 records, six binary
  skill ranks, 2d6 constitution, HP = constitution × 10, and weapon = RNG % 14.
  They occupy combat IDs 16 onward; C614 records start at slot 8. The fifth
  assignment, index 4, creates one live Locust through `07DC:07C3`.
* **VERIFIED:** Kick is weapon 32 / order slot 11. `12E8:0059..00AA` requires
  both hip actuator bits (record bytes 36/37, bit 8); `12E8:0297..02DD` starts
  its to-hit number at 3 and adds missing lower leg actuator bits.
  `12E8:0990..09EE` computes damage as mech weight / 5 and chooses between two
  leg locations with RNG bit 3. Ordinary location dice are still consumed.
* **VERIFIED:** `12E8:0758..091A` handles infantry armor and HP. Mech weapons
  use a 127 HP hit against these robots. Packed personal-weapon damage rolls
  are different from mech damage; small arms cannot penetrate mech armor.
  `12E8:0B5A..0B72` applies Inferno burning for three heat cleanups.
* **VERIFIED:** `REPAIR.BLD` supplies the six-option Mechit-Lube menu and all
  apprenticeship, no-mech speed-shop, repair and ammunition dialogue. A course
  costs 500 C-bills, once per character; `14D3:0BFC..0C9B` deducts the price,
  increments C61D and sets C624 bit 0. The insufficient-funds path changes
  neither skill nor credits. Loan mechs are training equipment, not ownership.
* **VERIFIED:** fourth success raises the allowance cap to 1000, fifth success
  to 2000; these are the low/high byte writes in TRAINING.BLD. Fifth success
  sets flag 45 and native action 43 places Rick at the lounge. No new mech
  gunnery/kicking rank is granted by these two assignment result routines.

Physical attack fixtures currently contain 600 controlled original spans,
including all three loan weights, leg damage, heat, cover, robot targets, all
14 randomly assigned robot weapons and Inferno burning. These are numeric
rule comparisons, not ordinary-input campaign or pixel comparisons.
