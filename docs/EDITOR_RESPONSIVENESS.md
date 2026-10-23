# Large-project responsiveness, batch 2 — 2026-10-23

Measured against the same independent source campaign: 40 maps, 403 events,
two planets, 574 source files and 20 accumulated Undo states. The benchmark
takes three GUI-thread samples per operation, with a separate cProfile pass
excluded from those timings. Later samples include the same four additional
metadata edits in both versions. These are local operation measurements, not
an overall game/editor speed multiplier.

| Operation | Before, median | After, median |
| --- | ---: | ---: |
| Snapshot for validation/test/build, no pending fields | 282.05 ms | 24.94 ms |
| Undo followed by Redo, source view open | 1,087.53 ms | 18.47 ms |
| Refresh unchanged source ownership table | 372.24 ms | 0.07 ms |
| Snapshot including an unfinished field | 355.04 ms | 212.11 ms |
| Metadata edit | 10.67 ms | 10.43 ms |
| Full rollback-capable preview transaction | 145.41 ms | 144.85 ms |

The profile identified repeated deep copies of discarded Undo history and
repeated source compilation/table reconstruction. The fixes are deliberately
limited to those measured paths:

- Worker snapshots copy current data and all mutable disk/source baselines,
  excluding editor history before traversing it. With no pending fields, no
  rollback transaction is needed to take that isolated copy.
- Undo and validated Save skip an empty field-flush transaction. Pending fields
  still use the complete transaction, preserving rollback of invalid text,
  current data, baselines and even direct mutations to history during a failed
  operation. Save's validation/stale-result checks and durable journal remain.
- The source table caches ownership while IDs, collection order, source index
  and runtime file mappings stay the same. Structural edits, deletion and Undo
  invalidate it. Selection and scroll position survive a rebuild. This cache
  never supplies the content used by Save, Build or native validation.
- The shared sorting helper updates appended rows without rescanning every row
  after every cell/insert. Numeric and three-state sorting, original order,
  child rows, selection and detach/reparent behavior remain covered.

The separate large-campaign GUI journey still paints map 40, edits event 383,
navigates a source diagnostic, repairs it with Undo, saves/reopens, builds and
starts/stops the actual SDL game. Its latest maximum heartbeat gap was **219.3
ms**, with **56.3 ms** to open the project/map and **129.9 MiB** peak RSS. The
earlier documented capacity journey had a 594 ms gap; that older observation is
context, not a controlled whole-editor before/after comparison. The dedicated
operation benchmark above is the controlled comparison.

Full transactions with pending fields, first-time source reconstruction,
large visual redraws and serialization can still pause the GUI. This batch
does not claim every supported maximum stays below 100 ms. Further work should
measure those paths before changing isolation or moving more work off-thread.

## Reproduce and verify

```sh
env BTP_RESPONSE_LABEL=after python3 tools/native_smoke.py --editor-responsiveness-only
python3 tools/native_smoke.py --editor-capacity-only
python3 tools/native_smoke.py --editor-style-only
python3 tools/native_smoke.py --editor-collaboration-only
python3 tools/native_smoke.py --editor-suites-only
python3 -m unittest discover -s tests -p 'test_*.py'
```

The first command writes `work/responsiveness-after.json`, `.prof` and
`-profile.txt`. The recorded baseline is `work/responsiveness-before.json` and
its matching profile, taken before production code changed. Tests also exercise
edits and Undo during a cancelled worker, stale validation, pending-field
snapshot/recovery, source Save/reopen, source ownership invalidation and a
1,000-row table. Native gameplay code and runtime budgets are unchanged.
