# Native CHI script coverage

Implemented as the first C4.4 increment. This observes the existing interpreter;
the cross-interpreter bridge and added-quest demonstration are still pending.

## Use it in the editor

Play an imported campaign, then stop the test. Open **Project → CHI script
coverage → Last Play trace**. **Open traces** also accepts one or more retained
`bld.jsonl` files. Expand a building to see its instructions, branch destinations
and native-operation enter/return counts. Double-click a row, or use **Open
source**, to open that BLD label.

Coverage requires the exact content revision recorded by Play. If the project
has since changed, open the retained `play-snapshots/run-…/game` project, or record
the new version. A mismatching trace is rejected. Reading a trace from an older
import resolves its original byte offsets without upgrading or saving it.
Opening its source editor can separately enable labelled sources as a draft.

## Headless use

```sh
./build/btech-headless --project PATH_TO_IMPORTED_PROJECT \
  --replay tests/fixtures/reference-bank.actions \
  --bld-trace work/bank-bld.jsonl --save work/bank-held.btp

python3 tools/chi_coverage.py PATH_TO_IMPORTED_PROJECT work/bank-bld.jsonl \
  --output work/bank-coverage.json
```

`--bld-trace` also works in the interactive SDL player. It is separate from
`--event-trace`, which records authored adventure nodes. Native editor Play now
records `bld.jsonl` automatically. These diagnostics do not alter content or
save identity, and require no save-format migration.

Each trace starts with a content fingerprint and an explicit fresh/continuation
marker. Observations identify the building/resource, compiled source and target
offsets, available source labels, kind and detail. Branch details distinguish
Yes/No, conditional outcomes and individual menu/dispatch choices even when
multiple choices have the same target. Existing C2 imports have no compiled
source map; the report resolves their original offsets from local BLD data.

The report includes all 26 programs and keeps declared and observed counts
separate. Source paths such as `$.programs[chi:bld-comstar].nodes[chi:comstar-…]`
use the same navigation mechanism as editor Problems.

## What this does and does not establish

- **VERIFIED:** instructions and resolved BLD branches were executed; native
  operations entered/returned at the recorded bytecode boundaries.
- **UNKNOWN:** branches inside native C handlers. A service return is not proof
  that every purchase, repair, failure or recruitment outcome was tested.
- Unvisited instructions/branches remain untested. Observation does not prove
  behavioral correctness. Faults and unresolved return boundaries are retained.
  A branch outside the declared source destinations is retained separately as
  unresolved evidence, including its choice and byte offsets; it is not silently
  dropped or counted as coverage of a declared edge.
- A continued trace records only execution after the loaded checkpoint. A
  return may legitimately occur without an entry in that same trace.
- Source labels are accepted only when they agree with the current compiled
  offsets. Truncated or malformed traces fail visibly; they are not silently
  counted as passing coverage.
- Original-derived generated reports and traces belong in private `work/`,
  alongside their exact imported project revisions.

See [the remaining bridge work](CHI_EVENT_BRIDGE_DESIGN.md) and
[verification](TESTING.md#native-import-usability-and-script-observation--2026-10-24).
