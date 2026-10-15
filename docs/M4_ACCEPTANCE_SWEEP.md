# Five-area fidelity sweep — 2026-10-15

This continues the five priorities authorized from PROJECT_STATUS. References
remain immutable; the executable runs only in private RAM or `work/dos`.
Original screenshots, decoded text and RAM remain ignored. Numeric fixtures
record the exact comparison bounds, not a claim of complete game parity.

## Salvage sequence

**VERIFIED:** the complete original `05AB:04F9` loop retries failed wrecks for
the same pilot, without another question or key wait. Its result box accumulates
those failures until recovery succeeds or no wreck remains. A separate held
no-more-wrecks page follows the last result, including a successful last recovery.
The failure branch retains the model name's padding and omits the success
branch's period; the native text previously trimmed both.

`tools/make_salvage_vectors.py` executes the unmodified routine in the existing
original combat snapshot. The real text engine runs; the harness supplies
keyboard/delay boundaries and rasterizes observed glyph calls with the original
font. Three qualified pilots, three wrecks, four technician ranks, eight damage
masks, four answer masks and three seeds produce **384 complete loops and 552
held pages**. `tests/fixtures/salvage-primary.{txt,json}` records prompt/attempt
order, text and interior RGB hashes, full party/garage record hashes, remaining
wrecks and RNG.
Templates are the original Locust, Chameleon and Wasp records.

The port now follows that sequence. Internal saves advanced to **BTPb/v37** to
retain inspection history; older held failure pages continue the same pilot's
search without repeating consumed random draws. Every new held result is saved
and restored during the test. **PASS:** all 384 loops and all 552 text and
200-by-72 interior pixel comparisons. The renderer preserves text committed by
each original string call: a separate full stop after a model that fills the
line wraps by itself, while an overflowing new word moves intact. This shared
fix also passes the existing combat, medical and Mechit-Lube layout checks.
The six earlier live aftermath crops cover borders separately; these additional
interiors are reconstructed from original glyph calls, not live screenshots.


## Combat controls and reports

**VERIFIED within the declared original routine boundaries:**
`make_computer_control_vectors.py` executes `103B:14C3` with four friendly units.
Computer assigns only the selected unit, is idempotent, and leaves the command
menu open. Next Mech changes the selected actor. Only Begin Fight starts the
manual sequence. `103B:100D..102E` establishes that Space clears the continuous
run flag while retaining individual assignments. Movement/weapon editing
returns only that actor to manual control. The initial Yes answer still enables
continuous computer play. Native Space completes the current wave before the
menu opens; DOS busy-loop/key-poll latency remains approximate.

The owner-reported Space-selection bug is corrected across held combat pages.
Previously the main command menu and movement/replace-order pages treated Space
as a request to reopen the menu. Space now has the same result as Enter on held
choices, and interrupts a running wave or its outtake without clearing unit
assignments. The command test compares both keys before and after restoration
for mech/infantry commands, destinations, weapon/target selectors and notices.
Native shop/story tails, settings/six-slot menus and Mechit-Lube choices also
exercise physical Space. Numeric amount fields still submit with Enter.

`make_battle_text_vectors.py` executes 256 brief/verbose shot contexts. The
original text engine and glyph calls establish the report in the upper-left
11-by-11-cell panel, interior `(8,8)..(95,95)`. Text, line wrapping, scrolling,
colours, weapon/location names and critical messages match all 88-by-88 pixels
reconstructed from those original calls. These are not live screenshot captures
or death-cleanup comparisons. The former generic battlefield hit/miss overlay
has been removed. A numeric subset also checks the critical-message count
against real structural damage. Replacement names Rusty and Hunter remain
saveable even though party capacity is eight.

Queued reports retain the actor/target identity and result before later attacks
change the records. **BTPc/v38** saves those reports in the existing 20,480-byte
payload and retains old-format migrations. **BTTA/v23** extracts 370 strings;
no original text or generated cache is committed.

## Encounters and town boundaries

**VERIFIED:** four additional original encounter contexts compare **133 complete
waves**: two MAP4 fights end in victory after three and two waves; two Starport
infantry cases reach the declared 64-wave observation limit each. The latter
are bounded traces, not completed fights. Every observed wave checks RNG,
records, living positions, facing, heat and outcome. This found and corrected
mechs planning around trampleable enemy infantry and skipped heat accounting
on the winning wave.

Initial native enemy records, RNG and positions also match the two MAP4
contexts. Enemy mechs now have the original extra gap, three-half-step spacing
and column wrap. The owner-requested reachability guard remains: the Starport
original positions include inaccessible areas that the native game deliberately
rejects. Exact placement parity is therefore not asserted for those contexts.

`make_town_boundary_vectors.py` executes **10,512** original collision/first-door
cases across **all 13 towns and 84 doorways**, including eight seam locations,
eight directions and three compact party configurations. They extend the
existing live formation observations and whole-party intermediate-step checks.

The cache oracle now includes entry/exit with and without the solved password,
for **534 original cases**. Native input/restore tests exercise those transitions
with parties of one through eight, check legal follower positions, and repair
old saves whose leader is correct but a follower remains outside the room.
Legal saved formations are preserved. This recovery is a compatibility repair;
no exact original follower-path claim is made for constrained cache corridors.

## Alternate services and campaign continuations

**VERIFIED:** `make_alternate_service_vectors.py` runs the original
`07DC:01C0` BLD interpreter through **928 complete CLOTHES/FROB visits**.
It compares money, purchase/spy/viewer/mapper/viewed flags, ordered menu choices
and held-page PC sequences for low/exact/surplus funds, Yes/No, repeated
purchases, one/two/five-person parties and the viewer's party restriction.
Native tests restore before every choice. All 26 original BLD control graphs
also pass a static audit; that is not execution coverage of all their branches.

A new **769-input** route imports GAME3 normally, parks the mechs through the
garage, visits both electronics product branches and the clothing shop, and
leaves with unchanged cash and ownership. The longer dependent routes were
regenerated after the Computer behavior change. The fresh campaign now has
**66,257 inputs**, and spy removal/replacement **50,672**. Both restore and
continue before every input; the fresh route still uses only the authorized
money shortcut and actual campaign prerequisites.

## Phoenix, audio and timing

**VERIFIED:** all **64,000 Phoenix LAM RGB pixels** match the live original
DOSBox capture `1792046692272345269/phoenix-open-1`, as well as the original
ENDMECH decoder and palette writes. The original cache save and controlled
approach coordinates are explicit prerequisites; ordinary Left/Return opens
the display. Raw captures remain ignored.

The original eighteen speaker programs, ordered tone/noise events and
sequential battle effects remain covered by the existing tests. **UNKNOWN:**
physical 8 MHz XT speaker filtering and exact timing without a suitable
hardware recording. **APPROXIMATE:** DOS busy-loop pacing, animation/NPC
wall-clock cadence and wider encounter behavior outside the compared contexts.
These limits are retained rather than claiming that the entire M4 milestone
is now verified.

## Verification handoff

All 54 regular suites and all 54 sanitizer suites pass, with address,
undefined-behavior and leak checks enabled; all five Python tool tests pass. Native checks cover the
intro and keypad, Space selections in six-slot/settings/inspection/map menus,
individual Computer assignments and interruption, 19 combat F5/F9 pages,
Mechit-Lube repair/ammunition/refit/recruitment, ten shop/story tails and cache
terminals/doors/Phoenix/map room/ending. See [TESTING.md](TESTING.md) for the
two corrected Space-test routes and the sandbox-only LeakSanitizer limitation.
