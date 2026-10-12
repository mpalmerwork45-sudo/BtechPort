# Open questions after bounded M4 work — 2026-10-13

The authorized M4 increments have playable, tested paths. Confidence belongs
to the individual original comparisons and recorded continuations in
[M4 evidence](M4_PROGRESS.md), rather than to every branch of the original game.
The next five proposed tasks are in [project status](PROJECT_STATUS.md).

1. **Fresh-game campaign completeness — UNKNOWN.** The ending route imports
   original GAME1 with late quest/party prerequisites. Hut success uses GAME5;
   several town routes use GAME3. These explicit prerequisites shorten testing
   but do not prove a complete native campaign from a new cadet.
2. **Theft branches — partial VERIFIED coverage.** Prison search success,
   failed starts, third-mech startup, restoration/allocation, the guard timer,
   eight-guard setup, flee refusal and one combat round are covered. Arena
   rental, spectator damage/alarm, two UrbanMechs, walking escape and retention
   are covered. Full original guard defeat, owned arena combat, normal returns,
   all-bays-full cases and destroyed-mech recovery need further comparisons.
3. **Later native actions — UNKNOWN contexts remain visible.** Garage repair
   actions 31/32 remain unsupported. Additional BLD branches must be audited
   before claiming all town services. Unknown actions produce diagnostics.
4. **Whole encounters — APPROXIMATE beyond bounded comparisons.** Candidate
   generation, formations, attacks, cooling, ejection and aftermath have primary
   cases. Placement/cadence, broader initiative and mixed-party AI still need
   complete DOS encounter traces. The arena movement threshold is recovered;
   general mounted exploration thresholds need a separate broader audit.
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
   combat/map/portrait geometry, viewport-edge visibility margins, animation
   cadence and several service layouts remain approximate.
8. **Persistence — tested represented fields.** All six supplied original saves
   roundtrip unchanged; unmodeled original bytes are preserved. Internal
   BTPT/v29 includes active theft/audio/menu states. Old formats cannot recover
   history that they never stored. Original export remains limited to supported
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
