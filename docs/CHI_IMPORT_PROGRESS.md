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

In progress. Next: implement the versioned compatibility resource loader and
explicit profile capabilities, then extraction/generation, editor/import wizard,
provenance enforcement and differential slice tests. No full editable-campaign
claim until C3–C5 gates pass.
