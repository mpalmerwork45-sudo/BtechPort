# Argent Recovery scenarios

Run `ctest --test-dir build -R '^extraction-' --output-on-failure`.
All cases play `examples/argent-recovery` through ordinary game inputs, with
explicit state assertions and save/reload checkpoints.

| Case | Route |
| --- | --- |
| success | Both caches, northern survey, western extraction and once-only payment |
| abandon | Southern pad fails the extraction objective and ends the contract |
| repeat | Leave/re-enter landing pad, count visits/departures, revisit a once-only cache |
| retreat | Optional raider encounter, real retreat, return to exploration |
| combat-win | Computer-controlled victory and return to the still-active contract |
| combat-loss | Declared hold policy, natural defeat and failed contract |

The focused `authored-mission-state` CTest additionally covers overlapping
regions saved between hooks, multi-step crossings, initial entry, Play here,
transfers, world coordinates, tactical return anchors, arithmetic bounds,
terminal objective transitions, journal and Lua queries.

These routes establish the named cases, not arbitrary mission reachability or
general combat balance.
