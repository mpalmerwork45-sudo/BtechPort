# M4 fidelity follow-ups — 2026-10-13

The owner authorized the five tasks in PROJECT_STATUS after the previous M4
batch. Original instructions and live DOS captures remain the authority; both
reference trees are immutable. Original assets, screenshots, RAM and WAVs stay
in ignored work files. This report records each verified increment separately.

## 1. Original combat commands and scanning

**VERIFIED:** `103B:14C3` chooses ten mech commands from DS:3A6F and eight on-foot
commands from DS:3ABC. On-foot Move/Clear Moves replace Walk/Run/Jump/Kick.
Clear Moves clears that actor's path and computer flag while retaining weapons
and other actors' orders. The port retains stable internal command IDs so
existing mech orders remain compatible; replay helpers now use the actual menu.

`05AB:18E8` supplies the pilot/model header for mechs and the character name on
foot. The invented Heat/Turn/Route text is removed from this original layout.
`103B:2591` asks Friends/Enemies/Cancel before `05AB:1467` presents summaries.
Next Unit, optional Detail Scan for mechs and Done retain the map. Humans show
their original condition text and personal weapon, plus friendly armour or an
enemy direction. On-foot observers and mechs with destroyed sensors describe
enemy humans only, with the original warning. Detail Scan opens the existing
original mech diagram and returns to the summary.

Nine live original 104×200 left regions match every RGB pixel, including all
borders and selectors. Numeric hashes/provenance are in
`tests/fixtures/combat-ui-primary.*`. The private source prerequisite activates
GAME3's three parked vehicles, places its fourth member on foot and enables an
encounter. It does not alter original instructions or reference saves. These
regions establish interface parity, not full battlefield/encounter parity.

**PASS:** all 46 core suites after this increment, including every-input
restoration through the new menus. Native SDL input/state/pixel checks and real
F5/F9 on scan-choice, scan-summary and scan-detail also pass. BTPW/v32 retains
older saves, migrating an old direct Scan to the detail page and normalizing
obsolete on-foot command selections. BTTA/v17 extracts 223 original fragments.

Dependent ordinary routes were regenerated because the on-foot menu uses
different key counts: the fresh ending is now 66,115 inputs and the spy/
replacement route 50,569. Their prerequisites remain ordinary inputs, with
only the owner's money shortcut used for the ending route.

## Remaining authorized work

The owner additionally requested a thorough Mechit-Lube comparison. That
increment is implemented and verified in [its audit](MECHIT_LUBE_AUDIT.md):
591 complete original service cases, 21 pixel-matching screen pairs, native
visits and seven real save/load pauses. It is a separate local commit.

2. Trace larger fights from captured live caller state, including sector-edge
   geometry, spy crews, ejection, targeting restrictions and aftermath.
3. Audit city doorways, corners and formations against original movement.
4. Compare isolated speaker events and refine filtering/cadence with explicit
   limits on physical-XT evidence.
5. Add alternate fresh theft/arena/loss routes and legacy-save migration cases.

These four tasks are in progress; this report does not mark them complete.

Additional owner observations to resolve within those tasks: black combat
edges, wrecks appearing before their destruction notification/sound, distinct
human/mech death sounds, the uneasy spy text on the inspected character sheet,
replacement specialists in other hospitals/Mechit-Lubes after the spy is killed,
and the original city/forest transition tiles. None is silently treated as
superseded by the Mechit-Lube work.
