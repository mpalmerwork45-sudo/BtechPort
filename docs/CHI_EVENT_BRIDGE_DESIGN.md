# C4.4 continuation contract

**Status: C4.4b and C4.4c implemented.** The acceptance requirements below are
retained as the design contract. [Quest authoring](CHI_QUEST_AUTHORING.md)
documents the shipped API, editor and native adapter limits;
[progress](CHI_IMPORT_PROGRESS.md) records verification. Native C-handler
internals remain unknown where only their BLD boundaries are measured.

## Current boundaries that must be preserved

The project loader rejects an ordinary authored `adventure` in a CHI import.
`btp_state_bld()` returns no program when `event.enabled` is set. The game loop
routes that flag directly to the authored event interpreter. Authored startup
also replaces map, party and exploration state. The opt-in `chi_events` and
`chi_bridge` documents therefore use explicit continuation ownership rather
than lifting that restriction or running authored startup.

Native BLD programs suspend in `BtpScriptState`; menus, services, films, effects,
training, prison, arena and cache have additional serializable owners. The
native service adapter retains a sixteen-operation budget; the BLD interpreter
has a 256-instruction budget. The authored interpreter uses 64 commands per
synchronous run. Each existing budget must remain in force across bridge calls.

The native 100-byte story window and the authored boolean flags are different
namespaces. A bridge must explicitly expose typed campaign-state access rather
than treating matching indices as the same variable. Allowance, party aliases,
recruitment and other native mirrored values must remain coherent.

Original and Updated saves use stable encoded payloads. Authored v52 already
uses much of the formerly unused save area for increased capacities. Do not
reuse those bytes opportunistically or serialize native C struct padding.
Bridge v53 uses an explicit 8,192-byte tail; ordinary saves retain their bytes.

The initial borrowed native service owners are ComStar buy/sell shares. Other
native actions require their existing campaign entry contexts and are rejected
as adapters. This is an explicit capability boundary, not a claim that all 47
registered native actions can be called from arbitrary quest scenes.

## C4.4b — Runtime and persistence

1. Introduce an explicit opt-in bridge document/capability. Load and resolve its
   references before allowing BLD event calls or authored compatibility calls.
   Ordinary imports with no bridge keep their existing startup and state bytes.
2. Define a bounded continuation stack, with four frames as the initial limit.
   A frame identifies its caller, return label, failure/cancellation labels,
   native building context and suspended owner. It must contain no C pointer,
   live Lua coroutine or process-local stack address.
3. Reuse existing event and native service implementations. Resolve an authored
   compatibility call through the native-action registry and a verified source
   anchor. A service that requires a specific building, mission, yard or cache
   context must either receive a validated context or be rejected explicitly.
   Arbitrary invocation of every native action is not implied by registration.
4. Specify shared and suspended state before coding each adapter. Credits,
   party damage/inventory and explicitly declared story effects are shared;
   caller UI/cursor and return ownership are suspended. Do not restore a whole
   stale game snapshot on return, which would erase purchases or battle damage.
5. On successful effects, advance the serialized continuation before yielding.
   A later native rollback checkpoint must not roll back credits while keeping
   an authored one-time reward flag committed. Establish a fresh checkpoint at
   the boundary or preserve both sides of the transaction together.
6. Give normal return, declined choice, cancellation, missing precondition,
   runtime fault, defeat and retreat explicit destinations. Returning to a BLD
   menu must not restart its entry instructions. Re-entry starts only a new
   invocation and retains persistent completion state.
7. Version bridge persistence explicitly. Preserve existing ordinary/native
   save bytes; add a documented bounded encoding for bridge state and validate
   the entire mixed continuation against the pinned content revision. Reject
   invalid depths, owner combinations, source labels and suspended phases.
   Include bridge state in canonical comparisons and checksums.
8. Keep presentation owned by the active continuation. A sound finishes before
   the next film/dialogue; held film frames and partially entered amounts must
   resume accurately after loading. Borrowed map contexts must restore correct
   world coordinates, discovery, native tile bank and party formation.

Acceptance cases: BLD → event → native service → event → BLD menu; nested event
return at the depth limit; rejected excess nesting/cycles; cancel and re-entry;
save/load at text, choice, partial payment, animation, sound and battle outcome;
exactly-once rewards/purchases; retained original/Updated gameplay and RNG.
Include a Windows/Wine comparison of all held saves, not just a successful load.

## C4.4c — Shared authoring and a real new quest

Add the same operations to the GUI and headless command/schema layer. Keep
Undo/Redo, pending forms, recovery, source projects, scope/protection and
problem navigation consistent. The existing native map projection still has
placeholder BLD entrance events; do not quietly serialize it as an authored
adventure or mistake those placeholders for measured campaign coverage.

Provide an asset-free recipe which adds an entrance to an unused native door
slot. The example reads an original campaign condition, offers a new dialogue
choice, invokes a supported native service, runs an authored encounter, applies
a one-time reward and returns to ordinary exploration. Test acceptance,
decline, defeat/retreat, repeat visits and checkpoint resumption in both
imported profiles. It must be constructible through the editor and CLI.

Extend observations across bridge boundaries, and record explicit native
outcomes where adapters supply them. Keep unobserved C-handler internals marked
unknown. Then feed these results into C4.5's aggregate campaign gate.
