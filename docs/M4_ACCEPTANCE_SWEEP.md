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
original combat snapshot. It intercepts text/panel, delay and keyboard boundaries
only. Three qualified pilots, three wrecks, four technician ranks, eight damage
masks, four answer masks and three seeds produce **384 complete loops and 552
held pages**. `tests/fixtures/salvage-primary.{txt,json}` records prompt/attempt
order, text hashes, full party/garage record hashes, remaining wrecks and RNG.
Templates are the original Locust, Chameleon and Wasp records.

The port now follows that sequence. Internal saves advance to **BTPb/v37** to
retain inspection history; older held failure pages continue the same pilot's
search without repeating consumed random draws. Every new held result is saved
and restored during the test. **PASS:** all 384 loops/552 text pages and the ten
focused aftermath, campaign-save, save-integrity and core suites. This is exact
text/behavior evidence; additional live result pixels are a separate comparison.
