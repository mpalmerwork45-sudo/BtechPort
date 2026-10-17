# Editor completion milestones

Requested 2026-10-18. These extend authored game packages; the original CHI
campaign remains available. Each stage is implemented, checked and committed
separately. Existing user edits to `examples/battletech-demo/adventure.json`
are preserved. Neither reference directory is writable input to this work.

1. **Services and buildings:** repair, rearm, healing and salvage event commands,
   explicit prices and success/failure branches, and reusable building templates.
2. **Events and quests:** connected event view, dialogue branching, objectives
   and journal, runtime flags/trace inspection and reusable testing checkpoints.
3. **Maps and artwork:** building stamps with entrances, grouped movement,
   collision/formation overlays, pixel selections/layers, crop/resize and sheet
   export. Add author-controlled generation of explicit jigsaw arrangements.
4. **Animation and units:** named action sequences, frame timing and cues,
   construction guidance, additional equipment behavior and individual infantry
   graphics. Library sprite editing must save and travel with the design.
5. **Delivery and compatibility:** package player/editor dependencies, asset and
   provenance reports, explicit save migration, and platform smoke tooling.
   Native Windows interaction can only be marked verified on a Windows host;
   cross-compilation and Wine are reported separately.

Additional steering: broker navigation separates **Mechs** (four weight classes)
from **Vehicles** (one scrolling list). Selling accepts either type.

## Verification gates

- Engine commands: deterministic success/failure/no-op tests, no partial payment,
  save/reload and invalid-data rejection where applicable.
- Editor: meaningful model tests plus real Tk/SDL workflow smoke checks for the
  new controls, shared undo history, save/reopen and library import/export.
- Build Linux and Windows in separate runs, at most two compiler jobs.
- Update status, testing and remaining limitations honestly. Custom authoring
  semantics are authored extensions, not claims about original DOS behavior.
- Compare the 1,287-entry reference snapshot in
  `work/reference-before-editor-five.json` after implementation.

## Progress

- **VERIFIED:** separate Mechs/Vehicles broker navigation; vehicle list scrolls,
  saves and returns to the hub. Linux headless broker/vehicle checks pass.
- **VERIFIED:** Unit Library preview has an Edit sprite button and right-click
  Edit/Select sprite actions. Real Tk editing, library save and game import pass
  (`python3 tools/native_smoke.py --library-editor-only`).
- **VERIFIED (engine/model):** [service buildings](AUTHORED_SERVICES.md), including
  atomic payment/result branches, templates, saved one-time salvage and target
  validation. The GUI workflow will receive the combined editor smoke check.
- Event/quest, map/art, animation/unit and delivery stages remain in progress.
