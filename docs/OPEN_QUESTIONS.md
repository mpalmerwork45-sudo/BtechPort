# Open questions after bounded M3a — 2026-10-12

Earlier Citadel, NPC, shop, banking, Class, save, sprite and first-mission
findings remain in their evidence reports. Three training assignments now reach
their results; see [M3a evidence](M3_COMBAT_EVIDENCE.md).

1. **Proposed M3b:** recover and verify kicking/physical attacks in the existing
   training encounter. **Proposed M3c:** audit and implement fourth-assignment
   combat. General AI/retaliation, the waypoint queue, exact weapon animation,
   terrain ignition and broader Run/Jump turn parity remain open. The user's
   stationary shell and original movement arrows are implemented and verified
   in the native route; original DOS moving-target observations remain intact.
   Later missions are unsupported. Rick's natural invitation requires
   fifth-assignment success; do not invent an earlier unlock.
2. **Long-route NPC/RNG gap:** first quiz/mission RNG matches, but original
   outdoor idle intervals packed before movement keys alter NPC arrival timing.
   Later native quiz draws diverge. The 181-checkpoint comparison uses three
   explicit original RNG prerequisites; full ordinary original/native NPC/RNG
   parity is open. The separate native two-mission/rest route uses ordinary
   inputs with no edits and proves playability, not original RNG equivalence.
3. Full party/unit footprints, collision with NPCs and local/world edge wrapping.
   Recorded eight-direction person/mech moves use one destination check.
   MAP1 human/NPC collisions have bounded coverage; wider unit branches and
   map-edge blocking remain inferred/approximate.
4. Outer-world stored/procedural boundaries and generation/RNG. The local
   64×64 template and 24×24 working grid do not establish a static global world.
5. Original movement history, status/rank bars, portraits, remaining menu layout
   and ANIMATE.ICN terrain animation. Original font bytes, frame borders and
   final dream pixels now match observations. Wider animation contexts, live
   water occlusion and complete screen equality remain unverified.
6. Original 3913-byte GAME saves versus the secondary 4096-byte claim. Prove
   original save/load round trips before import/export. Native saves use BTPE/v14
   (1024-byte payload, 1040-byte BTS1 file), preserving combat and firing indication.
   Historical migrations initialize only state the old format could represent.
7. Exact DOS keyboard repeat/flush/CPU timing and wider day progression. O0/O8
   timing uses observed VGA retrace units mapped to 32ms ticks; decode cost and
   wall-clock pacing remain approximate. Later combat timers, campaign gates
   and general C61B/C61C skill semantics remain open.
8. Tactical combat now has bounded instruction comparisons for dice, targeting,
   hit location, damage/criticals, ammunition, heat, walking/LOS and complete
   controlled turns. Extend actual traces to general initiative/AI, retaliating
   opponents, salvage and wider aftermath. EXE salvage strings contradict
   conclusions based only on missing BLD wording. The controlled original
   moving-target comparison is distinct from the requested stationary shell.
9. All 22 ANMs decode, including valid binary O21; only launch/dream dispatch is
   supported. Recover remaining campaign playback contexts, WWOODBT.SIF and
   audio/music roles. Audio remains absent.
10. Test Windows. Review licensing/distribution if requested; independent C
    implementation does not establish legal clean-room status or asset rights.

Local Git on `main` records incremental work without pushes. Both reference
trees are checked against their original content/mode/mtime baseline, including
Git metadata. The guard caught an external editor's `vscode-merge-base` addition;
that isolated addition and timestamps were restored without changing research.
