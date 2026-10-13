# M4 follow-ups — 2026-10-13

The original executable remains the authority. Both reference trees stay read-only; all source strings, RAM, graphics and WAVs are generated into ignored `work/`. Numeric fixtures record hashes and caller prerequisites.

## Implemented and compared

- **VERIFIED numeric:** 360 dispatcher cases for actions 31/32, personal armour selection/repair, including partial funding, refusal and undamaged armour. This repairs armour in ARMOR.BLD, rather than a mech garage.
- **VERIFIED numeric:** 160 original weapons/armour purchase-recipient cases. Multiple characters pay first, select a recipient or drop the purchase, and may redistribute displaced equipment. Solo purchases always go to Jason.
- **VERIFIED numeric:** 32 prison/arena return outcomes, including full garages, owned/rental vehicles, theft, destruction and the original failed-result flag.
- **VERIFIED numeric:** 40 original walk/run/jump obstacle paths and invasion escape bounds. Jump ignores terrain movement penalties, but the primary planner still checks solid obstacles. The invasion now includes generated terrain around MAP1/MAP11, with normal town collision gate 85; arena gate 139 stays local to arena combat. Four invasion opponents use the original Jenner records.
- **VERIFIED numeric:** two larger controlled encounters, 11 original waves and 171 full record/position/facing/heat/RNG comparisons. They exercise two friendly mechs, people, two enemy mechs, eight enemy people and three ejections, through victory and the original continue-flag loss boundary. Original sprite-sequence pointers are caller prerequisites; omitted pointers produce spurious facing differences. The original turn executes all movement after the final enemy dies, and the first two character slots are essential. This is bounded executable evidence, not a claim of full DOS UI combat parity.
- **VERIFIED numeric:** 432 water-boundary decisions from `0000:1C24..1CC1`. The original checks crossings of 16 half-step blocks and rejects descriptor 0F, displaying DS:0410. The port blocks the step and shows “The water is too deep that way.” The popup and its dismissal survive saving.
- Original `0000:0BC9..0D30` supplies compact walking formations: independent vehicles around the cursor, people only when on foot. Every visible member advances one animation frame per key even in two/four-step mode. Each intermediate step checks collision.
- Inspection now follows `0000:378D`: ask whether to inspect a mech, show the available vehicles on Yes, or select a character on No. Allocation uses its original right-hand pilot/rider table and left-hand vehicle selector, with compact living characters and actual vehicle bays.
- The prison yard has an explicit draw pass for the four parked vehicles at `0000:0D7D..0E43` positions. These are scenery independent of the party's temporarily hidden mechs.
- Speed Shop vehicle selection and its offer preserve the BLD model description, followed by original price/confirmation/result fragments from `09B8:080A/0925`.

## Integration verification in progress

The fresh-game input route covers the six training assignments, invasion escape, party and garage checkout, paid rank-four technician/medical apprenticeships, Jeremiah's holodisk in BARRACK2, Tellhim's password, cache doors/MAP15 and ending. It uses the owner's authorized credit shortcut, with no edited coordinates, skills, quest flags or RNG. Training/campaign recordings are being regenerated after combat corrections; full regression, sanitizer and SDL acceptance results will be recorded after those inputs stabilize.

Original captures use a private DOSBox display with a fixed cycle setting, not a physical 8 MHz XT. Audio pitch/event programs have executable evidence; speaker/filter response and host timing remain approximate. Source reference runs and controlled prerequisites are documented in ignored capture metadata. City/MTP placement and building-interior presentation are under additional review following the owner's reports.
