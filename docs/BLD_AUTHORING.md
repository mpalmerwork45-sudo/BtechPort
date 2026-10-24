# Edit native CHI building scripts

C4.1 exposes all 26 original BLD programs as labelled, typed source in imported
Original and Updated campaigns. The player compiles these sources through the
same C loader used for validation. Native interpreter behavior is retained.
[Service content](CHI_SERVICE_AUTHORING.md) is exposed by C4.2, including prices,
inventory and native-action descriptions. [Mission definitions](CHI_MISSION_AUTHORING.md)
and the [optional quest bridge](CHI_QUEST_AUTHORING.md) are implemented in
C4.3/C4.4. C4.5 still owns the aggregate campaign-authoring gate.

## Open and edit

Open an imported campaign in the Construction Kit and choose **Project → CHI
scripts**, or **Native building scripts** in the project tree. New imports
already contain source. Opening an older import adds source support as one
Undoable change. **Make a copy first if you need its existing saves**: enabling
source or changing it changes strict content identity.

Select a building and a labelled instruction. The table groups native clear-text
sections into pages and shows dialogue or an operation description. These groups
do not consume authored event IDs. The properties pane exposes:

- Dialogue, with normal line breaks stored as native carriage returns. Existing
  colour controls appear as `{color:6}`, `{color:14}`, `{color:15}`.
- Story-byte conditions and assignments, label destinations, native menu selector
  and ordered choices, cursor/font settings, waits, films and sound references.
- Compatibility action numbers with readable names. They retain their building
  context and may wait for a service, battle or input to finish.
- An author note, original offset, current compiled offset and owning source file.

**Apply instruction** validates the whole candidate and adds an Undo step.
**Save project** and **Play** also collect pending fields. Invalid fields stay
editable and leave the valid document unchanged. Double-clicking a compiler
problem returns to its building/instruction. Draft recovery retains unfinished
fields, including edited destination-list lengths.

**Clone** creates a fresh label after the selected instruction. **Insert** adds
a typed instruction; **Remove inserted** removes new records if references still
resolve. Original records retain their original byte ranges: redirect around
them instead of deleting them. **Restore original** restores that instruction's
baseline operands. Branches use **Go to target**. Add/remove menu destinations
before applying a selector change; their count must match that native selector.

Native menu IDs still select the original layout and number of choices. Edit
their preceding dialogue to match. The compiler checks characters, operands,
targets and budgets; it does not automatically reflow dialogue into the original
screen. Use Play to review text placement. Recruitment, purchase and other
native operations still require their original state/layout preconditions.

## Source and compilation

The optional manifest property `chi_scripts: chi-scripts.json` declares
`btp-chi-scripts-v1`, schema version 1. See the
[schema](../schemas/chi-scripts-v1.schema.json). The file contains the 26 programs
in native building order. Each has a stable ID, resource/building identity,
baseline payload SHA-256, entry label and ordered instruction records.

Each original record retains `origin` and `original_size`; newly inserted records
omit both. Branch words are resolved from stable label references in two passes.
Every original byte range remains represented. Unreachable bytes, including an
unvisited code region in the weapons program, are explicit preserved-data records.
They remain byte-identical and cannot be executed by a branch or fall-through.
They are not interpreted as no-ops or silently removed.

Unchanged source compiles to the exact original payload and encrypted BLD file,
including its size word and padding. The immutable `chi/*.BLD` baseline files
are not overwritten. Gameplay uses the compiled source directly; there is no
separate generated file that can become stale. Sources, compiler contract and
compiled payload hashes all participate in strict saved-game identity.

Native guards for classes, banking and training resolve original semantic
anchors to compiled positions. Instruction starts and resume boundaries have
separate maps: inserting an instruction after a native call must not skip it
when that call returns. The invasion retains the training program while the
visible Citadel changes to its ruined map. Held saves store normal native state
against the exact compiled project; they reload without new save-state fields.

Current bounds are 26 programs, 1–9,000 compiled bytes each, 1–2,048 records per
program and a 1 MiB/60,000-node source JSON budget. Dialogue spans are at most
4,096 bytes; the native eight-active-span limit still applies during execution.
Story operands address bytes 0–99. Add wraps modulo 256 (`255` adds minus one).
Money addition uses the original signed 16-bit operand. Dispatch retains the
original signed-byte/CBW behavior; keep its state value within the supplied
table's range. Invalid dynamic indices fault visibly in the interpreter.

Unknown operations, missing/duplicate labels, operand/data targets, altered or
removed original ranges, unsupported context/action combinations, invalid menu
counts and exhausted budgets are errors. Deterministic cycles without a yield
are rejected. Conditional loops retain the interpreter's 256-instruction budget.
Calls/recursion and crossing into authored events are not introduced here.
Native action/film combinations are restricted to those verified in that
program's immutable baseline; specialized training/class calls also keep their
existing anchors. C4.2's registry names these operations and documents their
contexts; it does not make arbitrary cross-building calls safe. `action` also
accepts the stable `native.*` name reported by that registry. Text and money
operands accept [service references](CHI_SERVICE_AUTHORING.md#linked-prices-and-messages)
when the project enables service content.

## Headless authoring

From the repository root:

```sh
python3 tools/chi_bld.py --project MY_PROJECT enable
python3 tools/chi_bld.py --project MY_PROJECT list
python3 tools/chi_bld.py --project MY_PROJECT show chi:bld-training
python3 tools/chi_bld.py --project MY_PROJECT compile chi:bld-training
python3 tools/chi_bld.py --project MY_PROJECT compile chi:bld-training \
  --output work/training-verification.bld

python3 tools/author.py inspect MY_PROJECT --query objects \
  --collection native-scripts --limit 26
python3 tools/author.py inspect MY_PROJECT --query object \
  --collection native-instructions --id chi:training-0005
```

`compile` emits the native compiler's bytes and original/source/compiled location
map. `--output` requires a new file outside project/reference directories.
Compiled BLDs remain original-derived private content.

The shared command interface supports `bld.enable`, `bld.update`, `bld.insert`
and `bld.remove`. Use the usual project ID, expected revision, request ID and
transaction envelope. For example, an operation inside that envelope is:

```json
{
  "op": "bld.update",
  "program": "chi:bld-training",
  "id": "chi:training-0005",
  "changes": {"text": "Welcome to this training ground."}
}
```

Changes and protection use `chi.programs/<program-id>` scopes. Command receipts
remain recorded after Undo to prevent delayed retries from repeating an edit.
**Campaign sources and build** splits the program collection into owned modules;
compiler errors resolve back to those modules and instruction labels. Original
and source projects use the same validator, snapshots, save journal and Play.

All extracted dialogue, source records, preserved bytes and compiled output
retain original provenance. Generated campaigns stay private; public export
continues to reject them. [Evidence](CHI_IMPORT_PROGRESS.md#c41--labelled-bld-sources-and-compiler)
and [remaining campaign milestones](CHI_EDITABLE_CAMPAIGNS_PLAN.md#9-c4--editable-story-services-and-campaign-progression).
