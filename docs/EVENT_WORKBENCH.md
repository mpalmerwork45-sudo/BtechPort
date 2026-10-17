# Events, objectives and testing

In **BattleTech Construction Kit → Maps / events → Events**, open **Event graph /
quests**. Drag nodes to arrange them, double-click to edit their ordinary fields,
or use **Connect branch** to select a named output and destination. **Add dialogue
branch** adds a choice and a new reply that returns to that conversation. Graph
positions live in `EDITOR.json`, share Undo/Redo, and travel with exported projects.

**Objectives** defines a title, description, Active flag and Complete flag. Set
those flags with normal event nodes or Lua. Discovered objectives appear under
**Space menu → Objective journal**; arrows browse, Space/Enter/Escape return.
Completion and discovery survive ordinary save/load. Up to 32 objectives use the
existing 64 saved flags. Journal text is validated against its display area.

**Playtest / checkpoints** runs the actual player from the beginning or from a
selected saved checkpoint. Enter logical actions, one per line (`accept`, `menu`,
`up`, `down`, `left`, `right`, `cancel`, `idle`), and choose a new checkpoint name.
The result includes the exact project, saved state, frame, input log and command
trace. Flags and command entries are shown in the window; double-click an event
to edit it in the current project. **Play selected** resumes that saved snapshot
interactively. Checkpoints live in `work/roster-editor/checkpoints/<package>/`.
Editing the working project never silently changes an existing checkpoint.

The headless player also accepts `--event-trace FILE` for JSONL command-entry
snapshots containing symbolic event/flag names, tick and credits. Subsequent
entries expose changes made by preceding commands, including synchronous flag
and service nodes. A resumed run omits discarded startup initialization.

**VERIFIED:** Python integration checks connected branches, layout undo/save,
objective activation, a saved journal, trace flags, checkpoint continuation and
snapshot isolation. The Linux Tk smoke checks graph dragging, event editing,
checkpoint creation and trace inspection. Screenshots:
`work/construction-kit-events.png`, `work/construction-kit-checkpoint.png`.
Native Windows GUI interaction remains unverified.
