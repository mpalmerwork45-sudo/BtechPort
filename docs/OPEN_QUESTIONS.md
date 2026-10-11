# Open questions after bounded M3b — 2026-10-12

Earlier Citadel, NPC, shop, banking, Class, save, sprite and first-mission
findings remain in their evidence reports. Five training assignments, Kick and
early Mechit-Lube now reach their results; see [M3a evidence](M3_COMBAT_EVIDENCE.md)
and [M3b evidence](M3B_TRAINING_EVIDENCE.md).

1. **Proposed M3c:** verify full multi-actor turns and general initiative, then
   the waypoint queue, exact attack/jump animations and persistent terrain fire.
   Kick rules, bounded enemy decisions/paths, original robot setup and the live
   Locust duel are implemented. The user's
   stationary shell and original movement arrows are implemented and verified
   in the native route; original DOS moving-target observations remain intact.
   Missions after the fifth are unsupported. Fifth success now naturally sends
   Rick to the lounge; subsequent party recruitment remains unfinished.
   Mechit-Lube covers Jason's apprenticeship and no-owned-mech services, not
   repairs/refitting/ammunition purchases for owned mechs or party-member courses.
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
   original save/load round trips before import/export. Native saves use BTPF/v15
   (2048-byte payload, 2064-byte BTS1 file), preserving seven-unit combat, Kick,
   defeat, firing indication and technician/apprenticeship. v13/v14 migrate from
   their original 1024-byte payloads.
   Historical migrations initialize only state the old format could represent.
7. Exact DOS keyboard repeat/flush/CPU timing and wider day progression. O0/O8
   timing uses observed VGA retrace units mapped to 32ms ticks; decode cost and
   wall-clock pacing remain approximate. Later combat timers, campaign gates
   and general C61B/C61C skill semantics remain open.
8. Tactical combat now has bounded instruction comparisons for dice, targeting,
   hit location, damage/criticals, ammunition, heat, walking/LOS and complete
   controlled turns. M3b adds 600 physical/personal attacks, 128 enemy decisions
   and paths, and 105 encounter/apprenticeship comparisons. Retaliating opponents
   are playable; full multi-actor turn traces, general initiative, salvage and
   wider aftermath remain open. EXE salvage strings contradict
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
