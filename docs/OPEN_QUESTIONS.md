# Open questions after bounded M2k–M2m — 2026-10-11

Earlier Citadel, NPC, shop, banking, Class, save, sprite and first-mission
findings remain in their evidence reports. The second assignment and sleep
through the third briefing are now playable; see
[M2k–M2m evidence](M2_RUBBLE_ANIMATION_EVIDENCE.md).

1. **Active gate, M3a:** manual third-assignment combat is playable through
   victory and the 500-cap reward, but the milestone is not complete. The user's
   stationary-shell and movement-arrow requests, native X11 combat route and
   sanitizer checks remain pending; see [resume checklist](M3_CHECKPOINT.md).
   Original DOS observations show the disabled target moving one step per turn;
   preserve that evidence when implementing the user's requested stationary shell.
   Later missions remain unsupported. Rick's natural invitation requires
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
   original save/load round trips before import/export. Native saves use BTPD/v13
   (1024-byte payload, 1040-byte BTS1 file), also preserving combat state.
   Historical migrations initialize only state the old format could represent.
7. Exact DOS keyboard repeat/flush/CPU timing and wider day progression. O0/O8
   timing uses observed VGA retrace units mapped to 32ms ticks; decode cost and
   wall-clock pacing remain approximate. Later combat timers, campaign gates
   and general C61B/C61C skill semantics remain open.
8. Tactical combat requires actual traces for initiative, targeting/hit-location,
   damage, heat/ammunition, criticals, AI, salvage and aftermath. EXE salvage
   strings contradict conclusions based only on missing BLD wording.
9. All 22 ANMs decode, including valid binary O21; only launch/dream dispatch is
   supported. Recover remaining campaign playback contexts, WWOODBT.SIF and
   audio/music roles. Audio remains absent.
10. Test Windows. Review licensing/distribution if requested; independent C
    implementation does not establish legal clean-room status or asset rights.

Local Git on `main` records incremental work without pushes. Both reference
trees are checked against their original content/mode/mtime baseline, including
Git metadata. The guard caught an external editor's `vscode-merge-base` addition;
that isolated addition and timestamps were restored without changing research.
