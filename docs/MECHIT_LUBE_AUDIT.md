# Mechit-Lube side-by-side audit — 2026-10-13

The original v1.03 executable and REPAIR.BLD are the authority. Original files
and the third-party reference remain immutable. Captures, private save
prerequisites, emulator RAM and comparison images stay in ignored `work/`;
only independent code, numeric observations and provenance are committed.

## Findings and corrections

**VERIFIED:** the original repair service is a sequence of questions about the
selected mech, rather than a menu of generic repair categories. `09B8:0002`
checks armour, internal structure, heat sinks, damaged weapons and actuators.
It skips undamaged areas, supports refusal and partial funding, and returns
to the building script. A fully repaired mech and an unfunded job have their
own responses. Engine, gyro and sensor damage are reported as unrepairable.

Weapon estimates contain only damaged weapon types on that mech, with their
original counts and a Nothing option. No unrelated or undamaged weapon is
offered. The estimate is separate from the record: the original charges each
estimate entry even though its first repair clears all matching critical
slots. Its final SRM6 completion-index behaviour is preserved. Those counts,
quotes and the original delayed actuator payment now survive save/load.

`09B8:1762` visits actual ammunition-using weapons in order. It skips energy
and broken weapons, reports full bins, clips excessive requests after a held
notice, and buys only the rounds the balance permits. A broken weapon elsewhere
does not prevent reloading a working one. The seven-digit editor, green numeric
fields and original notices replace the invented eleven-bin menu and receipts.

`09B8:080A/0925` clears the previous counter explanation before showing its
compact Speed Shop vehicle selector and model-specific offer. The offer keeps
its price and cash footer; the purchase result scrolls the original text by a
row. All eight previously verified refit transformations remain available.

The apprenticeship character selector, confirmation, refusal and 500-credit
payment use the original wording, spacing and retained Yes/No row. The left
panel now has up to four living party names and the original B/D/C outlines,
body/health shading and cash. No Empty bays or generic instruction footer are
added to these service screens.

**VERIFIED recruitment:** Ask to Apprentice also reaches REPAIR.BLD's agent
branch when its original Rex/parking/specialist conditions hold. The agent's
name-derived attributes, technician skill, free passenger seat and held joining
page are preserved. That page now retains the congratulations, name and actual
seat text; it matches the entire original 320×200 frame. The existing specialist
and lifetime-spy checks permit a replacement after a lost specialist, while
preventing a second spy. Hospitals retain their corresponding doctor branch.
This is not an unconditional hire option added to every visit.

**VERIFIED last-row gyro correction:** the engine/gyro/sensor warning has no
leading carriage returns, unlike healthy/unfunded notices. It now starts below
the last listed vehicle, retaining all three menu rows. Original session
`1791876402969678147` adds selection/result pairs to the pixel corpus. Native
entry/exit also preserves three pilots and a passenger, including Jason in bay
two, with every input restored. Original crew evidence is the mounted
before/entry/inside/after sequence `1791874354558657062`.

## Evidence and verification

`tools/make_mechit_vectors.py` executes the complete original repair and reload
functions with declared graphics/input boundaries. Its 591 cases cover three
real vehicle records, multiple damage patterns, refusal policies, seven funding
levels, repeated critical slots, SRM6, unrelated/selected broken guns, ammo
clipping, healthy mechs and the three unrepairable systems. Complete record
hashes, money, confirmation counts and weapon-estimate visits agree.

Twenty-three live original/port pairs match every RGB pixel in the complete
216×200 right panel and 104×100 party footer. These include the mech selectors,
repair questions, weapon estimate/receipt, actuators, return menu, ammo entry/
limit, apprenticeship, Speed Shop offer/purchase and recruitment. Provenance is
in `tests/fixtures/mechit-ui-primary.*`; numeric cases are in
`tests/fixtures/mechit-primary.*`. The changing repair-shop portrait is outside
those region assertions; the held recruitment frame matches all pixels.

Source sessions are `1791863873862567602`, `1791864147791493161`,
`1791865266664660305`, `1791865285111355132` and `1791876402969678147`. Private prerequisites specify
party membership, damage, funds and location explicitly. They do not establish
a complete ordinary DOS campaign replay.

**PASS:** the new core suite restores and continues before every input. Four
native SDL visits agree on recorded keys, complete state and final pixels.
Real F5/F9 checks pass on the repair question, estimate, receipt, ammo amount,
ammo-limit notice, joining page and refit offer. BTPX/v33 stores the estimate
and quote in existing payload padding; older approximate service saves resume
at the real vehicle selector without changing money or damage. BTTA/v19
extracts 317 original fragments, retaining the service text and adding medical
and battle-result wording.

Remaining limits are the wider original campaign and physical timing, rather
than a claim that every DOS building/animation has been compared. Numeric
funding coverage is broader than the 23 measured screen pairs.
