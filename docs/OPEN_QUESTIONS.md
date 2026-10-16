# Open questions after bounded M4 work — 2026-10-16

The authorized M4 increments have playable, tested paths. Confidence belongs
to the individual original comparisons and recorded continuations in
[M4 evidence](M4_PROGRESS.md) and [follow-up evidence](M4_FOLLOWUPS_EVIDENCE.md),
rather than to every branch of the original game.
The latest results and remaining bounds are in [project status](PROJECT_STATUS.md)
and the [latest five-area sweep](M4_COMPLETION_SWEEP.md).

1. **Fresh-game campaign — playable route VERIFIED; broader parity UNKNOWN.**
   A 73,026-input new-cadet route now earns companions, apprenticeships, the
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
   reaches its result. Owned/rented arena wins and losses and prison loss now
   have full ordinary-input and SDL continuations; 28 original arena terminal
   cases explain and correct the stuck fight. Eight additional complete original encounters now compare 24 waves: four
   owned/rental arena results, two prison defeats and two outdoor victories.
   Broader fights and elapsed timing remain outside those bounds.
3. **Later native actions — partial VERIFIED coverage.** Actions 31/32 are
   personal armour selection/repair, now supported with 360 original cases;
   they are not mech garage repair. Hospital/Mechit-Lube replacement recruiting
   and the spy have another 314 executed cases and an ordinary combat route.
   Another 928 original clothing/electronics visits and an ordinary 769-input
   saved continuation now pass. All 26 BLD control graphs have a static audit;
   124 further complete inventor/house/theatre branches now execute, with cash,
   flags, records and event-order comparisons. More branches still need
   execution before claiming all town services.
   Unknown actions produce diagnostics.
4. **Whole encounters — APPROXIMATE beyond bounded comparisons.** Candidate
   generation, formations, attacks, cooling, ejection and aftermath have primary
   cases. Placement/cadence, broader initiative and mixed-party AI still need
   complete DOS encounter traces. Two larger controlled encounters now compare
   11 waves/171 complete records, positions, facing, heat and RNG projections;
   caller prerequisites remain explicit. Five additional live-caller cases cover
   25 complete waves and 7,252 checks, including spy crews and finite ammunition. Arena threshold 139 stays local;
   ordinary town/world exploration uses threshold 85. Whole-party movement
   matches 40 live town observations and 1,920 executed collision decisions;
   480 doorway decisions include outer members. Another 10,512 decisions now
   cover all 13 towns and 84 doorways. The 534-case cache corpus includes entry/
   exit; native tests restore parties of one through eight and repair old saves
   with invalid follower positions. Another 5,760 original cache formation/first-contact cases check every member;
   2,400 saved native steps check split legal formations and all step sizes.
   Exact DOS follower recovery paths remain outside those legality claims.
   A new 440-case placement regression prevents disconnected enemy spawns and
   ordinary enemy mechs inside Starport, including from outside its boundary.
   This owner-requested reachability protection extends the original's
   terrain-only test, documented by 25 bounded placement observations. Initial
   native infantry sampling and cursor-relative offsets are corrected; the
   original mech spacing and column wraps are now implemented, with initial
   positions matching two MAP4 contexts. Four more original encounters compare
   133 waves: two MAP4 victories and two Starport traces bounded at 64 waves
   each. Those bounds do not establish every encounter outcome or wall-clock
   timing. Existing saved fights keep their already placed units.
5. **Timing and NPC arrival — APPROXIMATE.** Native logical ticks replace DOS
   busy loops. Long original waits and recruitment coins can consume a
   different RNG history. Earlier explicit later-quiz prerequisites remain
   documented. All ten populated towns now restore roaming actors; 50 original
   initialization/expiry and 45 Talk lookup cases pass. An ordinary arrival and
   hospital conversation has a complete saved/SDL route. Recorded input-only
   playability does not establish timer parity. A fresh 159-step MAP1 idle
   trace matches NPC state/RNG and saved continuations; its mean period is
   156.825 ms, versus 128 ms in the port. Original idle loops request eleven
   VGA retraces. This scheduler difference remains open because changing it
   affects recruitment/allowance RNG history. Animation and tactical speed
   requests now have 66/6 original cases and native 32 ms conversion checks.
6. **Sound — programs VERIFIED, physical response APPROXIMATE.** All eighteen
   ordered tone/noise traces, attack effect selections, hit/wreck/arena-alarm dispatch
   and sequential continuation are checked. Busy-loop conversion is a nominal
   Intel 8 MHz 8088 model with midpoint IMUL timing. Prefetch contention,
   interrupts, physical speaker filtering/volume and actual XT calibration
   recordings remain unverified. PCjr audio is not implemented.
7. **Visual parity — mixed coverage.** Title RGB, selected original popup crops,
   font/sprites and menu/inspection facts have primary comparisons. Broader
   combat/portrait geometry, viewport-edge visibility margins, CPU decode cost
   and several service layouts remain approximate. Animation opening holds
   and battle speed delays have now been corrected against original requests. Engagement,
   allocation, inspection-choice and Speed Shop selectors have complete region
   hashes. Original startup seed `0x020304` and all twelve city sectors agree;
   the overhead frame matches all 64,000 pixels without masks. The former black
   pixels are the original 2x2 flashing player marker; its DOS poll cadence is
   approximate. Nine foot/mech menu and scan regions, 23 Mechit-Lube panels,
   five victory/loot panels and one field-treatment panel match their captures.
   Field/hospital treatment and injured-cooldown/healthy notices now match four
   complete crops. Phoenix LAM colours match the original decoder/palette
   writes and all 64,000 RGB pixels of a live DOS capture. Further battle-result
   screens still need visual comparisons. The
   healthy-with-active-cooldown case now has its fifth complete medical crop,
   original RAM confirmation and a saved treatment/second-Heal continuation.
   Eight more weapon/target/withdrawal regions now match complete original
   captures. Another 30 regions across 20 held weapon/infantry/Kick pages now
   match: retained selection, override Yes/No and empty/destroyed notices have
   input/restoration coverage. Sixteen native combat pages pass F5/F9. Shutdown
   and sensor warnings match nine additional regions and 36 executed gate cases;
   the two arena result crops and qualified-pilot salvage question also match.
   Salvage now matches 384 complete original loops and 552 held text/interior
   pages, including automatic retries and final no-wreck notices. Three additional live success/failure/no-wreck salvage captures now match
   their complete panels and borders. Another 256 brief/verbose combat
   reports match text and every pixel of their upper-left interior. The new
   384-case death/ejection corpus compares all text and 256 brief/verbose
   interiors; quiet-mode ejection cursor/header placement remains approximate.
   Seventeen theatre film/held-page interiors match original wrapping and
   scrolling, including the closing sequence that previously overflowed.
   Nineteen native combat pages now pass F5/F9. Individual Computer assignments
   stay in the menu until Begin Fight; Space preserves them when it stops the
   continuous run. Key-poll latency remains approximate.
   The normal original target selector cycles enemy IDs12..23 only.
8. **Persistence — tested represented fields.** All six supplied original saves
   roundtrip unchanged; unmodeled original bytes are preserved. Internal
   BTPd/v39 includes active theft/audio/menu states, spy discovery and world
   sectors for debris, held weapon-window presentation, weapon-entry warnings,
   salvage inspection history and queued/held combat reports with casualty
   flags. v38 reports migrate with no invented death flag. Pre-v35 infantry
   weapon lists migrate to the original direct selector. Ambiguous pre-v34 decorative marks are cleared. Old
   formats cannot recover history that they never stored. Active-invasion v29
   migration now compares positions, current and per-actor goals/waypoints and
   the next four inputs; stale cache follower coordinates recover on load. Original export remains limited to supported
   outdoor contexts rather than every internal native mode.
9. **Portability — UNKNOWN.** Windows builds and audio/input behavior have not
   been tested. The independent runtime is C11/SDL2; research tools and cached
   assets are separate from its runtime dependencies.
10. **Provenance.** Authored code/docs are GPL-3.0-only. Original
    art/music/text/executable data stay outside Git and must be supplied by each
    runner. No original game source code is used. The README credits prior
    research and discloses AI-assisted work using OpenAI Sol 6.1 and Astra;
    independent C does not itself establish a formal clean-room process or
    rights to original assets.

Both reference trees are guarded by content, mode, timestamp and Git-metadata
checks. Known external editor metadata drift is restored only when its exact
baseline is established. No reference code is copied into the port and no
remote push is authorized.
