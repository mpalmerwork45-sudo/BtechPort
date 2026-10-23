# Greybank Dispatch: recorded campaign brief

Create a small, playable BattleTech campaign separate from Last Beacon. The
player commands Rowan's Phoenix Hawk and Mira's Trebuchet from a frontier
communications depot. Use the shipped, attributed CHI-adapted definitions;
original CHI graphics remain an explicit, separately supplied dependency.

The depot needs a contract office, a machine shop with purchases and repairs,
and a road out of town. Offer an exclusive choice: defeat a Jenner blocking
the relay, or recover two data caches and survey a relay before extraction.
Either route pays once and opens a timed defence, then a vehicle escort.
Return to the depot between operations. Leave time for repairs and journal
inspection. The Skulker must reach the landing pad alive; retreat or loss of
the protected vehicle fails its contract. Ordinary skirmish retreat leaves
that contract open. Finish through the dispatcher after the escort.

Reuse the tested Relay Contract, Argent Recovery and Cairn Passage geometry
and mission mechanics. Provide descriptions on the important event nodes.
The default parameters, including payments, defence duration and test seeds,
are in `recipe.json`. These are recipe inputs, not instructions evaluated by
the runtime. Retain editable expanded data and modular campaign sources.

Acceptance journey, defined before verification:

1. Generate from the recipe through public authoring operations. Record exact
   inputs, imports, revisions and file hashes. Replaying those recorded inputs
   must reproduce the playable content without a model or network service.
2. Deliberately overlap one enemy with the initial formation. Obtain an object
   and location diagnostic and a failing gameplay route. Repair it through a
   constrained command batch and retain both reports.
3. Complete both opening routes through the finale, at the recorded seeds,
   including repairs and save/reload checkpoints during active battles.
   Check defer, ordinary retreat, abandonment and defence failure separately.
4. Inspect map/event previews and actual game frames. Use the GUI to revise
   dialogue and terrain, then apply a constrained authoring follow-up without
   losing those changes; demonstrate Undo, Save/reopen and Play.
5. Deliver CLI launchers with the Construction Kit. Run the independent
   fixture and exported native game without authoring/model services. Check
   paths containing spaces and report missing original assets clearly.

This is a short demonstration, not a balance claim, an original CHI mission
or a general-purpose procedural campaign generator. Arbitrary edits require
new checks. Planet-wide navigation verification remains a separate milestone.
