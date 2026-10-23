# Editable CHI import progress

Authorization: C1 and C2 first pass, 2026-10-23. See the
[milestone plan](CHI_EDITABLE_CAMPAIGNS_PLAN.md) and [contracts](CHI_IMPORT_CONTRACT.md).

## C1 — Audit and contracts

**Implemented structural audit.** `tools/chi_audit.py` generates the committed
numeric/fingerprint inventory: 77 supported source files, 76 resource copies,
26 BLDs, 1,816 reachable instructions, all native actions 1–47 with their script
contexts, maximum script 8,499 bytes and maximum 12 populated entrances. Native
capability sizes and dependency/editability dispositions are recorded in the
contracts. Existing Original/Updated save and resource paths are retained.

**Preservation baseline:** private `work/chi-import/baseline.json` records HEAD
and hashes of the three pending Last Beacon files. Reference guard verifies
1,287 entries unchanged in content/mode/mtime against
`work/reference-before-map-construction.json`.

**Provenance:** 20 original-derived Last Beacon tile images already exist in
tracked HEAD. Cleanup will retain local dirty files and replace only the public
baseline payloads with recipe-reconstructible placeholders. No history rewrite.
Generated CHI projects remain local; typed assets, caches and native dialogue
remain original-derived through edits. Detection limits are explicit.

**C1 gate:** contracts resolve C2 loading/profile/identity, resource budgets,
state preservation, initial edit surface and transaction behavior. Full map and
BLD/native authoring remains C3/C4 with concrete owners/verification. Static audit
is VERIFIED; re-verifying every original branch is not claimed.

## C2 — Importer and first slice

**Resource/import foundations implemented.** The opt-in project extension owns
79 runtime files; the validator hashes and decodes the same bounded snapshots.
Original/Updated features are explicit. Original retains an empty additions
container and exact cache templates; Updated exports its current definitions/art.
The shared headless importer checks all 77 fingerprints, stages both projects
and publishes their new parent without replacement. Completed projects run with
every external resource path absent. Native text overrides participate in the
ordinary document history, strict fingerprint, source conversion and build.

**Verified:** the two imports match their built-in editions for 108,156 total
gameplay ticks across ordinary training/combat and mission pass/fail fixtures,
including rendered checkpoints and held-script save/reload. Twelve slot
round-trips pass with cross-profile/normal-save rejection. Four affected native
regression tests pass. Private evidence: `work/chi-import/parity-linux.log`,
`native-focused.log`, `first-import.json`; Linux build uses `/usr/bin` tools to
avoid the development host's older Conda linker.

In progress: GUI import/text views, failure/recovery/isolation tests, provenance
guards, public baseline cleanup and Windows comparison. No full editable-campaign
claim until C3–C5 gates pass.
