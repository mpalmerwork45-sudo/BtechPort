# Open questions after bounded M4 work — 2026-10-13

The authorized M4 increments have playable, tested paths. Confidence belongs
to the individual original comparisons and recorded continuations in
[M4 evidence](M4_PROGRESS.md) and [follow-up evidence](M4_FOLLOWUPS_EVIDENCE.md),
rather than to every branch of the original game.
The next five proposed tasks are in [project status](PROJECT_STATUS.md).

1. **Fresh-game campaign — playable route VERIFIED; broader parity UNKNOWN.**
   A 66,119-input new-cadet route now earns companions, apprenticeships, the
   holodisk and password before reaching the ending, using only the authorized
   credit shortcut. It restores before every input and has selected original
   prerequisite comparisons. It is not a complete DOS recording of all those
   inputs, nor coverage of every alternative campaign branch. Original-save
   prerequisites still provide short independent UI/service checks.
2. **Theft branches — partial VERIFIED coverage.** Prison search success,
   failed starts, third-mech startup, restoration/allocation, the guard timer,
   eight-guard setup, flee refusal and one combat round are covered. Arena
   rental, spectator damage/alarm, two UrbanMechs, walking escape and retention
   are covered. Another 32 executed return cases cover full garages, owned and
   rental vehicles, normal return and destruction. A bounded native guard fight
   reaches its result. Complete DOS fights and additional ordinary-input
   ownership/loss paths remain to be compared.
3. **Later native actions — partial VERIFIED coverage.** Actions 31/32 are
   personal armour selection/repair, now supported with 360 original cases;
   they are not mech garage repair. Hospital/Mechit-Lube replacement recruiting
   and the spy have another 314 executed cases and an ordinary combat route.
   Additional BLD branches still need audits before claiming all town services.
   Unknown actions produce diagnostics.
4. **Whole encounters — APPROXIMATE beyond bounded comparisons.** Candidate
   generation, formations, attacks, cooling, ejection and aftermath have primary
   cases. Placement/cadence, broader initiative and mixed-party AI still need
   complete DOS encounter traces. Two larger controlled encounters now compare
   11 waves/171 complete records, positions, facing, heat and RNG projections;
   caller prerequisites remain explicit. Arena threshold 139 stays local;
   ordinary town/world exploration uses threshold 85. Local follower detours
   satisfy the requested collision correction but are not original pathfinding
   evidence. More doorway/corner/formation frames remain to be checked.
5. **Timing and NPC arrival — APPROXIMATE.** Native logical ticks replace DOS
   busy loops. Long original waits and recruitment coins can consume a
   different RNG history. Earlier explicit later-quiz prerequisites remain
   documented. Recorded input-only playability does not establish timer parity.
6. **Sound — programs VERIFIED, physical response APPROXIMATE.** All eighteen
   speaker programs, attack effect selections, hit/wreck/arena-alarm dispatch
   and sequential continuation are checked. Busy-loop conversion is a nominal
   Intel 8 MHz 8088 model with midpoint IMUL timing. Prefetch contention,
   interrupts, physical speaker filtering/volume and actual XT calibration
   recordings remain unverified. PCjr audio is not implemented.
7. **Visual parity — mixed coverage.** Title RGB, selected original popup crops,
   font/sprites and menu/inspection facts have primary comparisons. Broader
   combat/portrait geometry, viewport-edge visibility margins, animation
   cadence and several service layouts remain approximate. Engagement,
   allocation, inspection-choice and Speed Shop selectors have complete region
   hashes. Original startup seed `0x020304` and all twelve city sectors agree;
   the overhead frame matches 63,998/64,000 pixels, with two unexplained source
   black pixels explicitly masked. The original eight-entry on-foot combat
   menu and some unit headers/scan layouts still need reproduction.
8. **Persistence — tested represented fields.** All six supplied original saves
   roundtrip unchanged; unmodeled original bytes are preserved. Internal
   BTPV/v31 includes active theft/audio/menu states and spy discovery. Old
   formats cannot recover history that they never stored. Active-invasion v29
   migration needs a dedicated saved-case comparison. Original export remains limited to supported
   outdoor contexts rather than every internal native mode.
9. **Portability — UNKNOWN.** Windows builds and audio/input behavior have not
   been tested. The independent runtime is C11/SDL2; research tools and cached
   assets are separate from its runtime dependencies.
10. **Distribution.** Original art/music/text/executable data stay outside Git.
    Independent C does not itself establish clean-room or asset rights. Any
    requested distribution needs a separate provenance/licence review.

Both reference trees are guarded by content, mode, timestamp and Git-metadata
checks. Known external editor metadata drift is restored only when its exact
baseline is established. No reference code is copied into the port and no
remote push is authorized.
