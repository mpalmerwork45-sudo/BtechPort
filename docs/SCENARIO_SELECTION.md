# Scenario selection for reviewed changes

**Implemented, 2026-10-23 — bounded AI4/AI5 extension.** The Construction Kit
can explain which declared regression cases have visible dependencies on a
proposal, then run selected cases against its retained candidate. This helps
people and external authors choose checks without changing the live game.

## In the editor

1. Open **Project → Changes and protection**, and select a prepared proposal.
2. Open **Checks → Cases → Choose suite…** and select a normal
   `btp-author-suite-v1` JSON file. The job retains the suite and its inputs,
   compares dependencies on both sides of the review, and suggests cases.
3. Select a row and open **Why this case** (or double-click the row). It shows
   the changed objects, reference chains, seeds and any unknown dependencies.
4. Click a **Run** cell, or select a row and press Space, to include/exclude it.
   **Suggested**, **All** and **None** change the selection. **Run selected**
   runs every declared seed of the selected cases; **Run full suite** runs all
   cases. An empty selection cannot accidentally launch the full suite.
5. **Latest check** shows the result of the latest run for this retained suite.
   Cases omitted from that run say **Not run**, even if an earlier full run
   passed. Complete reports remain under **Reports** and **Open artifacts**.

**Reports → Check mission** still runs the native mission analysis. Scenario
selection does not replace ordinary validation. **Apply changes** revalidates the
proposal and uses the same revision checks, protection rules, Undo and Save.

The suite is retained with the review. Editing or deleting the original input
files does not alter it: use **Choose suite…** again to capture later edits.
Changing proposal groups prepares another candidate and requires a new selection.
Workers for a previously selected proposal cannot repaint the current case list.

## CLI

Given an existing review folder and suite, inspect suggestions without running
tests:

```sh
python3 tools/author.py review suggest work/proposal --suite work/scenarios/suite.json
```

The JSON response includes the retained `report` path, cases, explanations,
revision IDs and `suggested` case IDs. Run that exact retained selection using
the returned path:

```sh
python3 tools/author.py review check work/proposal --selection /absolute/path/to/selection.json --suggested
python3 tools/author.py review check work/proposal --selection /absolute/path/to/selection.json --case yard --case world
python3 tools/author.py review check work/proposal --selection /absolute/path/to/selection.json
```

Without `--case` or `--suggested`, a suite check runs **all** cases. To capture
fresh inputs and check in one command:

```sh
python3 tools/author.py review check work/proposal --suite work/scenarios/suite.json --suggested
```

`--cancel-file` uses the existing cancellation protocol. Original-asset projects
also accept the normal `--data`, `--dialogue-data`, `--combat-data` and
`--world-data` arguments when running. `review check` without a suite/selection
continues to mean mission analysis. Standalone `author.py suite --case ID`
also reports which cases were omitted, and still reads only the requested cases.

## What a suggestion means

| Classification | Meaning |
|---|---|
| Affected | A changed object is in the case's conservative dependency inventory, or shared configuration changed. |
| Unknown | Opaque control or an exhausted analysis budget prevents a complete inventory. |
| No known dependency | The explicit inventory has no intersection with these changes. This is neither proof of independence nor a passed test. |

The inventory starts with the effective starting state, explicit scenario IDs
and global sprite bindings. It follows structured references in maps, entrances,
regions, events, shops, encounters, combat hooks/groups, people, units, loadouts,
tiles, jigsaws, worlds and owned images. Every event branch and every trigger on
a reachable map is included, regardless of the choices the case actually makes.
Town maps include their parent planet; planets include all their placed towns,
jigsaws and terrain patches. This intentionally over-selects some world routes.
Before **and** after dependencies cover removed references and changed transfers.

Shared configuration, collection order and runtime metadata not classified as a
named object select every case. Editor-only metadata does not by itself select
gameplay cases. Changes are recomputed from the exact snapshots, rather than
inferred from a command's declared write scope.

Reachable Lua, unknown event operations, raw input, checkpoint starts, an exact
scenario revision pin, original-game dependencies, and fixtures that do more
than `start.set` are explicitly **unknown**. If **any** case is unknown, the
suggested selection is the **full suite**. Arbitrary fixtures still execute
through the existing validated private-copy workflow. Lua is not interpreted;
saved state is not guessed; the native save loader remains authoritative.

Suggestions do not execute paths, prove conditions, establish coverage for
omitted cases or test general balance. Someone may deliberately select a smaller
set even when a full suite is recommended; its reports show that choice.

## Retained evidence and limits

Each review can retain up to 32 selection reports and 32 check reports. A
selection records both revision hashes and hash-pinned copies of the suite,
scenarios, input checkpoints, fixture commands and fixture imports. Rewritten
paths refer to those copies; original bytes and source paths remain recorded.
Imported filenames are preserved for converters that derive image names from
them. Changes to retained inputs, either snapshot or the selection report are
rejected. Source-format projects use the same workflow.

The graph allows 16,384 objects and 262,144 distinct edges per revision. Exceeding
those bounds produces unknown coverage and a full-suite recommendation. Reports
show up to eight reasons, 128 dependency paths and 16 unknown explanations per
case, with complete counts. Reference chains show up to 24 nodes. Input capture
allows 256 source files, 16 MiB per file and 64 MiB of source bytes; at most 33
rewritten runnable copies have a separate 64 MiB budget. Invalid/unreadable/oversized inputs refuse capture rather than
presenting a misleading selection. Existing suite bounds remain 16 cases,
32 total runs, eight seeds per case and 300 seconds maximum.

Selected checks use the existing native runner and retain seeds, actual event
coverage, combat samples, input replay, screenshots, checkpoints and runner hash.
A linked result records selected/omitted IDs and the selection report. Partial
or cancelled suites retain evidence without claiming success. This does not
change the gameplay or save formats.

## Reproducible demonstration

```sh
python3 tools/review_selection_demo.py --output work/selection-demo
python3 tools/native_smoke.py --editor-review-selection-only
```

The first command creates an independent game with two isolated sites and a
two-planet journey. It needs no original assets. The site cases each use two
seeds, giving five runs in the full suite. Expected suggestions:

| Proposal | Suggested cases |
|---|---|
| Yard briefing | Yard |
| Shared grass tile | Range and world journey |
| Shared Rook unit | All three |
| Port placement | World journey |

The selected yard runs match their full-suite counterparts in native final
state, event coverage, exact save bytes and ordinary-input replay. In the recorded
run, the full suite took **0.1445 s** and selected cases **0.0539 s**, saving
**0.0906 s**. These are suite execution times after input/dependency capture on
this small fixture, not a promised end-to-end or general speedup.

Optional `--windows` compares the first selected native case with the Windows
runner under the isolated Wine test prefix. Linux Tk interaction and that Wine
game route pass; native Windows Python/Tk interaction remains unverified.
See [verification](TESTING.md#review-linked-scenario-selection--2026-10-23).
