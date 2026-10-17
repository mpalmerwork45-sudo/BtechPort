# Authored service buildings

**Maps / events → Events → Service building** creates editable event graphs for
a repair depot, clinic, salvage yard or full service depot. Choose prices and an
existing entrance, or attach the generated choice event to an entrance later.
Every menu, description and result message remains editable in the event forms.

Four commands are available in ordinary event forms:

| Op | Effect |
| --- | --- |
| `repair` | Restore armour, structure, components, actuators and engine/gyro damage on surviving owned units. |
| `rearm` | Fill ammunition bins to their design capacity. |
| `heal` | Restore surviving characters to their maximum health. |
| `salvage` | Recover an author-selected chassis into a free bay, with half armour, empty ammunition bins and no crew. |

Each has `cost`, `next`, `failure` and `unchanged`. The price is a flat fee for
the complete operation. Failure or no work consumes no money. Repair/rearm/heal
may specify a zero-based `slot`; omitting it covers the whole party. The editor
displays slot numbers starting at one. Services do not revive dead characters.
Salvage specifies a symbolic `mech` ID (a mech or vehicle) and can succeed only
once per event node, including across save/load. Put it on a battle's victory
branch to award a recoverable chassis. This is a scripted salvage award; it
does not select arbitrary wrecks from a battlefield or retain their exact damage.

These are authored-game rules. Existing CHI hospital and Mech-It-Lube behavior
uses its original service routines.

**VERIFIED:** native transactional tests cover funds, repair fields, ammunition,
healing, missing targets, full bays and save/reload. Python integration runs a
generated building through the actual player and verifies save-resumed salvage
cannot be claimed twice; malformed targets fail validation before disk writes.
