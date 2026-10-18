# BattleTech Construction Kit usability plan

Recorded 2026-10-18 against implementation commit `cf4d5e4`.

**Status: approved and in progress.** The five stages bring the
existing editors into one project workspace and make errors, saving, navigation
and recovery predictable.

The [previous five editor milestones](EDITOR_COMPLETION_MILESTONES.md) delivered
authoring capabilities. This plan makes those capabilities easier to use. Each
stage below has a usable stopping point, verification requirements and its own
commits. The original game and existing authored projects remain playable during
the transition.

## 1. Problems to solve

The audit found these concrete issues. `VERIFIED` here means verified by source
inspection, not a completed interactive reproduction on every operating system.

| Finding | Evidence | Effect on the user |
| --- | --- | --- |
| **VERIFIED:** errors from graphics and world tools delegate to the map editor; forms delegate to their owner | `guard()` in [graphics_editor.py](../tools/graphics_editor.py) and [world_editor.py](../tools/world_editor.py); `Form.submit()` in [adventure_editor.py](../tools/adventure_editor.py) | Messages belong to an ancestor instead of the active tool. This can explain obscured warnings; exact stacking depends on the window manager |
| **VERIFIED:** editing a library sprite creates several dependent editor windows | `edit_sprite()` in [library_browser.py](../tools/library_browser.py) and `edit_unit_sprite()` in [roster_editor.py](../tools/roster_editor.py) | A single task requires managing a unit editor, map editor, graphics browser and sprite editor |
| **VERIFIED:** closing a parent destroys child windows without collecting every local draft | `AdventureEditor.close()`, `RosterEditor.set_document()` and `PixelEditor.close()` | A parent's close path can bypass a pixel editor's discard check; jigsaw drafts also need explicit protection |
| **VERIFIED:** controls and navigation are spread across large toolbars and separate forms | Current roster, sprite and event editors; saved GUI captures | Less room for artwork, repeated navigation and inconsistent Apply/Save behaviour |
| **VERIFIED:** validation uses a synchronous subprocess; some playtest preparation is also synchronous | `run_validator()` in [editor_model.py](../tools/editor_model.py), `PlaytestWindow.run()` in [playtest_workbench.py](../tools/playtest_workbench.py) | Long operations can stall interaction. Their impact on larger projects is **UNKNOWN** until measured |

The existing shared `ProjectDocument`, validation, undo snapshots, save journal,
asset provenance and library dependency handling are foundations to retain.

## 2. Intended workspace

Use one main editor window per session, with one open game project and any
explicitly opened shared-library designs. Starting another editor process may
open another project; existing external-edit protections still apply.

```text
BattleTech Construction Kit - My Campaign *

File  Edit  View  Project  Play  Help
Save   Undo   Redo                       Search...   Play v

+------------------+--------------------------+------------------+
| Project          | Open editor tabs         | Inspector        |
|                  | [World] [Atlas] [Sprite] |                  |
| Worlds / planets |                          | Properties of    |
| Local maps       |                          | the selected     |
| Units            | Main editing area        | object           |
| Weapons/equipment|                          |                  |
| Events/objectives|                          | Preview          |
| Artwork          |                          |                  |
| Shared library   |                          |                  |
+------------------+--------------------------+------------------+
| Assets / tile palette | Problems | Playtest / output           |
+--------------------------------------------------------------+
```

Panels resize and collapse. Remember the layout, open tabs and view positions;
provide Reset layout and restore windows within the available monitor bounds.
Keep a compact default layout usable at 1280 by 800. Higher display scaling must
keep controls reachable through sensible reflow or scrolling.

The project explorer uses names and previews, with search and filters. It groups
mechs, vehicles and infantry under Units and makes planets, city overlays,
entrances, events and their relationships discoverable. Technical IDs remain
available in advanced properties and details.

File contains project opening, saving and export. Edit contains common editing
commands. View controls panels and layout. Project contains validation,
dependencies, package settings and delivery tools. Play contains Start, From
here, Checkpoint and Stop test. Help provides contextual guidance and shortcuts.
The toolbar exposes frequent actions rather than every available command.

The initial welcome view offers recent projects, New project, Open project and
the Unit Library. A single New project flow gathers the name, template, directory
and resource requirements. Existing desktop and command-line launchers continue
to reach the editor directly. The SDL game retains its separate play window.

## 3. Common interaction rules

### Errors and dialogs

- Show field errors beside the relevant field, keep the entered value and move
  focus to the first invalid field when the user submits. Explain the correction
  in ordinary language, such as "Ammunition must be a whole number".
- Put project-wide errors in a persistent Problems panel, with severity, asset
  name and a short explanation. Activating a row opens the relevant tab, object
  and field. Preserve technical details for copying and diagnosis.
- Use modal dialogs for decisions that require an answer: file selection,
  destructive replacement and unsaved changes. Parent each dialog to the active
  visible view, centre it appropriately, and restore focus and any local grab
  when it closes. Avoid blanket always-on-top or forced-focus workarounds.
- Catch unexpected Tk callback failures centrally, report them visibly and keep
  diagnostic details. An error must not appear only in a terminal.
- Show successful routine operations in the status area. Do not interrupt work
  with a confirmation popup after every save or validation.

### Saving, drafts and undo

- **Save Project** includes valid pending edits across every project tab,
  including artwork, jigsaws, forms and events. Collect and validate drafts as
  one candidate before changing the saved files. A failed save preserves all
  drafts and makes the first problem visible; it cannot partly save the project.
- **Save Library Design** writes only the identified library design and its
  dependencies. Library and project tabs clearly show their scope. `Ctrl+S`
  saves the active scope; explicit menu commands let the user choose either.
- **Save All** processes each dirty scope explicitly. Cross-scope saving is not
  one filesystem transaction: report successful and failed scopes separately,
  retain failed drafts, and never claim that everything saved when it did not.
- Mark unsaved tabs and the project title. Closing the application presents one
  review of unsaved scopes with Save, Discard and Cancel. A failed save or Cancel
  keeps the affected views open. Switching tabs never silently discards work.
- Closing a tab with an uncommitted form draft offers Apply, Discard or Cancel.
  Applied in-memory edits remain in the project when their tab closes; closing
  a tab does not implicitly write package files.
- Undo acts first on an actively edited text field or unfinished gesture, then
  on the active project's or library design's shared history. Label the pending
  action, such as "Undo paint tiles". One stroke, drag, import or multi-field
  change is one meaningful operation. Escape cancels the current gesture.
- Separate crash-recovery drafts from validated package files and ordinary game
  saves. Recovery includes invalid field text and local art drafts; it must not
  silently publish these into a playable package.

### Navigation and selection

Open an existing asset tab when it is already present. Keep one editing owner
per asset within a scope, identified by scope, kind and stable ID; two assets
with the same ID in different scopes must never share a draft accidentally.
Inspector and preview changes propagate to other views after an edit.

Back and Forward restore selection, zoom and scroll position. Breadcrumbs show
routes such as Planet / City / Entrance / Event. Search covers names and IDs;
commands can also be searched from the common action registry. Asset pickers use
searchable thumbnails, filters and friendly names with IDs available in details.

Use consistent shortcuts: Ctrl+S saves the active scope, Ctrl+Z undoes,
Ctrl+Y/Ctrl+Shift+Z redo, Ctrl+Tab changes tabs, Ctrl+W closes the active tab,
Ctrl+Shift+P searches commands and F5 starts the selected playtest mode. Text
editing and modal dialogs retain their appropriate local key handling. Buttons
remain accessible through keyboard focus, Enter and Space.

Before deleting an asset, show its usages. Provide a compatible replacement
where references can be updated safely, as one undoable operation. Block unsafe
deletion with navigable references. Opaque Lua references require manual review;
do not promise that arbitrary script dependencies can be discovered automatically.

## 4. Implementation structure

Retain Python/Tk for this refactor. The present notebook, tree, paned-window and
canvas controls provide the required building blocks. Extract the existing
tools into reusable views instead of changing GUI toolkit and document format
at the same time.

The following are proposed responsibilities, not existing module APIs:

| Component | Responsibility |
| --- | --- |
| Workspace | Main window, menus, explorer, tabs, inspector, panels and layout |
| Editor session | Open project/library scopes, registered drafts, selection, document revisions, save and close coordination |
| View registry | Reuse asset tabs and preserve navigation state without hidden owner editors |
| Action registry | Shared menu, toolbar, shortcut and context-menu actions, with enabled state and undo labels |
| Dialog and diagnostic service | Visible ownership, focus restoration, inline errors, Problems entries and callback failures |
| Task runner | Bounded background jobs, progress, cancellation, immutable input snapshots and revision-tagged results |

Retain [editor_model.py](../tools/editor_model.py) as the document and atomic-save
foundation. Reuse the pure editing helpers, library import/export and runtime
launcher. Views should receive a session and document reference directly rather
than reach through chains such as `owner.owner.parent`.

Machine-specific window layout belongs in editor user state. Portable authoring
metadata, including pixel layers and deliberate graph arrangements, remains in
`EDITOR.json`. Neither should change the runtime content fingerprint. Preserve
the current separation between authored data, metadata and game saves.

Use a small, explicit document-change notification mechanism to refresh affected
views; avoid a general plugin system. Start with labelled transactions over the
existing snapshots. Change history storage only if measured memory use justifies
it. Cancel animation timers, callbacks and jobs when their views or scopes close.

Diagnostic records carry severity, scope, object ID, field or source location,
message and optional technical details. Editor validation can supply these
directly. Add machine-readable output to the C validator where needed for
precise navigation, while retaining its current text interface. Unmapped loader
failures remain visible project-level errors; do not infer field locations by
fragile matching of English error text.

## 5. Milestones

The user approved all five stages. UI1 establishes the safety foundation; UI2 builds
the shell; UI3 moves workflows into it; UI4 completes consistent editing and
recovery; UI5 completes polish and platform checks. Each stage includes focused
tests and documentation. The sequence is incremental, not a single replacement
of the whole interface.

### UI1 Dialog reliability and unfinished edits

**Implemented with focused Linux verification:** dialog ownership, registered
drafts, inline form errors, cancel-close protection and rollback of failed saves
are in place. Real Tk regression and library/construction workflows pass. Later
stages replace the remaining separate windows and complete shared history/recovery.

1. Introduce explicit error/dialog ownership, with a common callback boundary.
   Update forms, weapon mounts, graphics, sprites, worlds, jigsaws, library tools,
   event tools and delivery/playtest dialogs to use the initiating view.
2. Add inline validation for ordinary field errors and an initial shared
   diagnostic list that can later live in the Problems panel.
3. Register all local drafts with their scope, including pixel layers, animation
   forms and jigsaws. Gather drafts before save, close and project replacement.
4. Fix the existing parent-close paths immediately. Establish save/cancel rules
   before converting windows to tabs. Full recovery and shared art history land
   in UI4; draft protection must already work here.

**Acceptance:** invalid ammunition and invalid sprite/action inputs remain
visible and editable; no dialog attaches to a hidden owner. Closing or replacing
a project with unfinished artwork prompts correctly. Cancel retains every draft
and selection. File-dialog cancellation restores usable keyboard focus. No
invalid operation leaves a partial import or document edit.

### UI2 One project workspace

**Implemented foundation, Linux GUI checked:** default editor and launcher routes
now open one workspace with explorer, tabs, inspector, Problems/output, command
search, scoped Save, navigation and layout state. Main authoring tools embed in
the workspace. UI3 completes direct asset navigation and more specialised layouts.

1. Add the workspace shell, common commands, project explorer, tab registry,
   inspector and collapsible panels. Move roster and map views into it first.
2. Convert tool constructors into embeddable views. Temporary standalone
   adapters may use the same view code during migration; keep the existing
   launch commands working. Remove duplicate default routes as each view moves.
3. Add the welcome/recent-project view, unified New project flow, project title,
   unsaved markers, tab reuse and consistent keyboard navigation.
4. Persist and reset layout, and add Back/Forward with per-view navigation state.
   Show the library's separate scope even when opened without a game project.

**Acceptance:** launch, open a project, edit a unit, paint a map, change tabs,
undo, save and reopen within one editor window. Reopening the same asset selects
its existing tab. Project switching respects UI1 draft checks. Existing command
line arguments and source/distribution entry points still reach the right view.

### UI3 Connected authoring workflows

1. **Worlds and maps:** integrate world, city and jigsaw views; keep a local tile
   palette in the active workspace. Open city overlays and entrance destinations
   directly. Preserve painting, fill/stamps, grouped dragging, collision and
   formation overlays, all-tile browsing, generation and multiple planets.
2. **Units and library:** integrate mechs, vehicles, infantry, weapons and
   equipment. Keep animated previews and construction guidance. Offer direct
   Edit sprite/Choose sprite actions without creating a map editor. Use explicit
   Import into project, Update design and Create variant actions with dependency
   previews and attribution preserved.
3. **Artwork:** use a large canvas, compact tools, layer list and frame timeline.
   Show action, movement direction and frame meaning together. Integrate action
   timing, cues, onion skin, import, clone, transformations and export. Keep
   duration labels consistent with the supported 32 ms tick representation.
4. **Events:** edit node properties beside the graph; connect named ports by
   dragging, with an accessible form alternative. Add zoom, fit, filtering to an
   event chain, readable connection routing and an explicit Auto arrange action.
   Handle branches and cycles; preserve manual layouts unless arrangement is
   requested. Integrate objectives, dialogue and links from map markers.
5. **Assets and operations:** share searchable visual pickers, find-usages and
   reference navigation. Bring service templates, start-party setup, asset
   reports, export, save migration and playtest controls into workspace views.
   Retain current behaviour and limits rather than inventing new game semantics.

**Acceptance:** a unit-to-sprite-to-unit edit and a planet-to-city-to-entrance-to-
event edit finish without additional editor windows. Back restores the original
selection. Library art saves and imports with layers/actions intact. Service,
party, equipment and delivery features remain reachable. Auto arrange is
undoable; the graph supports selecting a branch without a tangle of all-project
connections. Choosing an original graphic still creates an explicit editable
package copy when editing is requested.

### UI4 Consistent history saving and recovery

1. Complete labelled shared transactions for maps, unit properties, pixel edits,
   frame/layer changes, jigsaws, event graphs and imports. Make stale editors
   refresh instead of overwriting newer data; scope history separately for each
   library design and the current project.
2. Implement Save Project, Save Library Design and Save All contracts from
   section 3. Stage valid drafts together, run full validation and retain the
   existing transaction journal and external-file-change checks.
3. Add bounded automatic draft recovery, proposed default after two seconds of
   idle with a maximum interval of 30 seconds during continuous editing. Capture
   only changed state; measure the cost before fixing this interval. Flush after
   a completed edit when closing normally. Do not promise preservation of the
   few seconds between recovery writes during a crash.
4. On reopening, offer Recover, Review or Discard with timestamps and project
   identity. Compare the saved baseline with current files; preserve conflicting
   drafts for explicit resolution or recovery into a copy. Keep successful-save
   transaction recovery distinct from unsaved-draft recovery.
5. Finish deletion/replacement checks and cross-view refresh. Persist recovery
   data outside distributed game files and exclude it from package hashes.

**Acceptance:** editing a unit, map and sprite then pressing Save Project saves
all three; a single invalid draft prevents the project save without losing any
input. Undo/Redo survives tab changes and reflects in previews. Simulated exit
without saving recovers art and field drafts. External edits cannot be silently
overwritten. Failure in one library scope during Save All is reported without
claiming that all scopes saved. Ordinary gameplay saves retain their existing
content checks and migration rules.

### UI5 Presentation responsiveness and release checks

1. Apply consistent system-font sizing, spacing, labels, selection/focus states
   and toolbar styles. Use proper icons with readable labels, not font-dependent
   decorative characters. Keep advanced IDs/settings available without placing
   them ahead of everyday controls. Provide tooltips and a shortcut reference.
2. Run validation, large imports/exports, preview preparation and builds through
   the task runner. Debounce lightweight validation and reuse bounded preview
   caches. Use worker processes where CPU work needs isolation; all Tk updates
   stay on the GUI thread. Ignore stale results using document revision IDs.
3. Show progress and cancellation where safe. Disable only conflicting actions.
   Save serializes the scope being committed; an edit during validation must
   trigger revalidation or a clear retry, never a false "all changes saved".
   Complete a durable filesystem commit before reporting cancellation.
4. Unify Play Start, From here and Checkpoint. Launch a validated snapshot, record
   its revision, show trace/problems in the workspace, and keep test saves
   separate. Stop test affects only the process launched for that session.
5. Update screenshots, help, README, status, testing records and packaged
   entry-point checks. Exercise real Linux and Windows focus/scaling behaviour.

**Acceptance:** normal edits provide immediate feedback; the window continues to
repaint and accept navigation during long jobs. Measure and record input latency,
job duration and peak memory on the demo and a declared larger fixture. Target
visible feedback within 100 ms for normal interactions and progress within
500 ms for longer work on the test machine; these are targets, not current
measurements. Controls remain accessible at 100%, 150% and 200% scaling. Starting
and stopping a test returns focus appropriately and preserves pending editor work.

## 6. Verification and delivery

Use copied projects and an isolated library/recovery directory for destructive
and crash tests. Do not exercise them against the user's working demo or library.
Record a fresh reference snapshot before implementation, and preserve the
existing uncommitted edits to `examples/battletech-demo/adventure.json`.

| Workflow | Required evidence |
| --- | --- |
| Invalid input in a form opened from a sprite or library view | Correct visible owner, retained text, reachable correction, restored focus |
| Close project with unapplied pixels, jigsaw and event fields | One coordinated review, working Cancel, no bypassed drafts |
| Project unit and shared-library unit with the same ID | Separate drafts, history, save targets and previews |
| Import unit, edit sprite/action, save library, import into game | Correct dependency closure, attribution, layer/frame data and gameplay preview |
| Planet, city, entrance, event, dialogue and service | Direct navigation, retained view position, valid save/reopen and playable branch |
| Paint, drag, replace referenced artwork, Undo and Redo | One meaningful history entry per action and consistent views |
| Invalid save, write failure, external modification and crash recovery | No partial project save, no lost draft, clear conflict resolution |
| Validate/export while changing selection or closing a view | Responsive UI, bounded jobs, no stale result or callback on destroyed widgets |
| Start/From here/Checkpoint and Stop test | Correct snapshot, separate test save and safe return to editing |
| Layout changes, keyboard-only use, minimize/restore and display scaling | Reachable controls, visible focus, usable dialogs and reset layout |
| Original, Updated, independent demo and existing authored projects | Existing loading, gameplay and save behaviour retained |

Extend the existing model and GUI smoke tools rather than add repeated full
campaign playthroughs. UI1 needs focused regressions for the ownership and draft
loss paths; UI2–UI4 need user-journey checks, not tests that merely count widgets.
Keep captured screenshots as visual evidence, alongside assertions about state,
focus, save contents and behaviour.

Existing commands to retain and adapt as views move:

```sh
python3 -m unittest discover -s tests -p 'test_*.py'
python3 tools/native_smoke.py --editor-only
python3 tools/native_smoke.py --map-editor-only
python3 tools/native_smoke.py --editor-visual-only
python3 tools/native_smoke.py --world-art-editor-only
python3 tools/native_smoke.py --library-editor-only
python3 tools/native_smoke.py --construction-kit-only
ctest --test-dir build --output-on-failure
```

Run focused suites during each stage, then the full relevant suite at integration
gates. Pure UI changes do not require rebuilding the C engine repeatedly. If the
validator gains structured diagnostics, preserve its text interface and run
focused native, sanitizer and Windows/Wine checks for that change. At final
integration, check the Linux and Windows builds separately, with at most two
compiler jobs, and exercise the packaged launcher/editor/player.

Use the existing private-display automation for repeatable Linux workflows and
add a real desktop pass for stacking, focus and monitor behaviour. Xvfb success
alone cannot verify these. Windows cross-build and Wine results remain separate
from native Windows Tk results. If a native Windows desktop is unavailable,
record that gate as **UNKNOWN** and provide the reproduction procedure; do not
mark Windows GUI acceptance complete.

Each stage records its commit IDs, actual checks, screenshots where useful,
remaining limitations and updated launch instructions. Update
[PROJECT_STATUS.md](PROJECT_STATUS.md) and [TESTING.md](TESTING.md) when results
exist. Compare the reference snapshot after implementation. No original assets,
user saves, private recovery data or working library copies enter commits.

## 7. Sequence and scope control

| Order | Commit-sized deliverable | Depends on |
| --- | --- | --- |
| 1 | Dialog service, field errors and focused regressions | Existing editor |
| 2 | Draft registration and coordinated close/save protection | 1 |
| 3 | Workspace/session shell with roster and map tabs | 2 |
| 4 | Explorer, action routing, tab reuse and navigation history | 3 |
| 5 | Embedded library/unit/graphics/sprite workflow | 4 |
| 6 | Embedded worlds/jigsaws, entrances, events and supporting tools | 4 |
| 7 | Labelled shared history, complete save coordination and recovery | 5 and 6 |
| 8 | Background jobs, unified playtesting and visual polish | 7 |
| 9 | Cross-platform journeys, packaging, documentation and final report | 8 |

Split a row into smaller commits when needed, keeping working entry points at
each checkpoint. UI2 and UI3 contain most of the structural work; UI4 carries
the greatest data-integrity risk. Ship the UI1 fixes as an independently useful
checkpoint before moving the rest of the interface.

The refactor retains the C engine, package schemas, Original/Updated behaviour,
existing editor capabilities and resource provenance. Additive diagnostic output
and editor metadata may be introduced where required. A GUI toolkit rewrite,
arbitrary detachable docks, new combat rules, a new scripting language, expanded
format limits and automatic merging of arbitrary conflicting projects are
separate work. None is needed for these five usability stages.

After the user's go-ahead, proceed through UI1–UI5 in order with progress reports
and verification at each stage. Routine implementation choices use the defaults
recorded here. A scope change or unavailable platform check should be reported
explicitly rather than silently changing the completion criteria.
