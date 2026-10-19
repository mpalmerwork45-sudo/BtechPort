# Open questions after bounded M4 work and authoring increments — 2026-10-19

The authorized M4 increments have playable, tested paths. Confidence belongs
to the individual original comparisons and recorded continuations in
[M4 evidence](M4_PROGRESS.md) and [follow-up evidence](M4_FOLLOWUPS_EVIDENCE.md),
rather than to every branch of the original game.
The latest results and remaining bounds are in [project status](PROJECT_STATUS.md)
and the [latest five-area sweep](M4_PORTABILITY_SWEEP.md).

The [AI authoring tools](AI_AUTHORING_GUIDE.md) deliver AI1/AI2, shared asset
search/visual feedback and bounded mission analysis/scenario suites while
retaining the full editor. The eight-case suite measures ten ordinary-input
runs, including a declared validated low-funds fixture. Local navigation uses
the actual initial party and collision rules; it does not establish all later
party compositions, world routes, arbitrary conditions/Lua or general combat
balance. Those remain extensions of AI4. The next proposed increment is AI5:
a Changes review view, protected objects/regions and live sessions. Richer
mission mechanics and measured campaign capacity follow separately. CLI work
cannot inspect another editor process's unsaved forms: use the GUI command-file
exchange or close/save before CLI publication. Native Windows Tk remains
unverified. Model/provider selection is optional and does not block these tools.

The Unit Library now includes 25 additional classic chassis and corrected
original animation defaults. These remain CHI adaptations: rear firing arcs,
shared ammunition bins, split weapon criticals and full construction legality
remain outside the adapter. Individual infantry sprites are now supported. Its
[source and adaptation notes](../content/catalogues/mechs/README.md) distinguish
checked numeric specifications from runtime simplifications.

Editor follow-ups after the [five milestones](EDITOR_COMPLETION_MILESTONES.md):
Windows Tk needs native verification; Windows dependency bundling requires a
supplied full Python installation; Linux bundles require compatible glibc/X11.
Canvas zoom is verified with Linux Tk wheel/button events, editable percentages
and drawing coordinates. Native Windows/macOS wheel handling and physical
high-resolution devices still need desktop checks; synthetic Windows-style
events on Linux do not establish those results.
Map painting now defaults to the visible surface; building detail overrides
survive rebuilding where the projected shape remains. External layer moves or
untracked replacements still require resolving the stale-layer warning. The
world view edits terrain outside city overlays; city tiles are edited locally.
Play now rechecks edits made during preparation and exposes startup diagnostics;
the saved user project validates, but the exact previously reported interactive
failure has no captured error/trace. Controlled blocked-entrance, stale-result
and failed-player retry paths pass. Tile editing shows actual map/construction/
jigsaw neighbours; empty preview cells do not invent surrounding map terrain.
Authored original terrain animation and live editor previews now share the
verified source frames. Timing uses the existing native clock (128 ms/frame
for original loops), not a new DOS hardware measurement. Existing single-frame
owned copies remain static until their animated source is copied again; direct
CHI references need no migration. Native Windows/macOS animation UI still needs
desktop verification.
Save migration preserves existing rule/topology/ordinal structure and rejects
arbitrary remaps. Sprite anchors, imported audio, full construction tonnage and
vehicle turret/arcs/critical rules remain future extensions. Scripted salvage
awards an authored chassis; selecting arbitrary combat wrecks is not implemented.

1. **Fresh-game campaign — playable route VERIFIED; broader parity UNKNOWN.**
   A 83,339-input new-cadet route now earns companions, apprenticeships, the
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
   248 further complete inventor/house/theatre branches now execute, with cash,
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
   Another 768 continuous original inputs compare every member after each
   one/two/four-step key in both rooms. Exact DOS recovery from malformed
   legacy formations remains outside those path claims.
   A new 440-case placement regression prevents disconnected enemy spawns and
   ordinary enemy mechs inside Starport, including from outside its boundary.
   This owner-requested reachability protection extends the original's
   terrain-only test, documented by 25 bounded placement observations. Initial
   native infantry sampling and cursor-relative offsets are corrected; the
   original mech spacing and column wraps are now implemented, with initial
   positions matching two MAP4 contexts. Four more original encounters compare
   133 waves: two MAP4 victories and two Starport traces bounded at 64 waves
   each. Four additional completed fights at different positions now compare
   20 waves: two Starport infantry victories and two mixed MAP4 victories.
   These exposed the original enemy-kick reads overlapping explored-map bytes;
   the port now reproduces those reads. These bounds do not establish every
   encounter outcome or wall-clock timing. Existing saved fights keep their already placed units.
5. **Timing and NPC arrival — APPROXIMATE.** Native logical ticks replace DOS
   busy loops. Long original waits and recruitment coins can consume a
   different RNG history. Earlier explicit later-quiz prerequisites remain
   documented. All ten populated towns now restore roaming actors; 50 original
   initialization/expiry and 45 Talk lookup cases pass. An ordinary arrival and
   hospital conversation has a complete saved/SDL route. Recorded input-only
   playability does not establish timer parity. A fresh 159-step MAP1 idle
   trace matches NPC state/RNG and saved continuations; its mean period is
   156.825 ms. The port now uses eleven nominal 70 Hz retraces, retaining
   fractional phases and updating immediately on a key as the original does.
   NPC, recruitment, allowance and encounter clocks share this rule; ordinary
   routes have been regenerated for the changed RNG cadence. Host scheduling
   and continuous DOS keyboard polling remain approximate. Animation and tactical speed
   requests have 66/6 original cases and native 32 ms conversion checks. The
   [combat pacing follow-up](COMBAT_PACING.md) adds 48 complete original waves:
   speed waits belong after attacks, not movement, and graphics-off skips pose
   waits. The port now follows those boundaries. The subsequent
   [weapon/fire audit](WEAPON_PRESENTATION.md) adds 2,400 original presentation
   and 720 fire-redraw cases, correcting pose waits, sound order, trajectories
   and impacts. CPU-dependent projectile/beam drawing time remains approximate.
   Fire follows actual redraws and persists outdoors with the debris ring.
6. **Sound — programs VERIFIED, physical response APPROXIMATE.** All eighteen
   ordered tone/noise traces, attack effect selections, hit/wreck/arena-alarm dispatch
   and sequential continuation are checked. Busy-loop conversion is a nominal
   Intel 8 MHz 8088 model with midpoint IMUL timing. Prefetch contention,
   interrupts, physical speaker filtering/volume and actual XT calibration
   recordings remain unverified. PCjr audio is not implemented.
   The [movement/LRM audit](MECH_MOVEMENT_AND_LRM_AI.md) confirms current model
   movement budgets and identifies original-planner limitations for missile
   support. The [Updated implementation](MECH_MOVEMENT_AND_LRM_AI.md) now adds
   an optional minimum-range penalty, explicit distance scaling and weapon-aware
   tactics. Bounded seeded comparisons and planning timings are recorded there;
   broad campaign balance, global squad strategy and indirect fire remain open.
   Original mode retains the original planner and attack rules.
7. **Visual parity — mixed coverage.** Title RGB, selected original popup crops,
   font/sprites and menu/inspection facts have primary comparisons. Broader
   combat/portrait geometry, CPU decode cost and several service layouts
   remain approximate. Viewport admission and beam-sound eligibility now match
   2,582 original flag observations, including sector-edge positions. Animation opening holds
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
   interiors. Twelve additional quiet-mode cases match all header/ejection
   interior pixels before/after retirement and retain that cursor across saves.
   Repeated-ejection sequences still need additional original pixel cases.
   Seventeen theatre film/held-page interiors match original wrapping and
   scrolling, including the closing sequence that previously overflowed.
   Nineteen native combat pages now pass F5/F9. Individual Computer assignments
   stay in the menu until Begin Fight; Space preserves them when it stops the
   continuous run. Key-poll latency remains approximate.
   The normal original target selector cycles enemy IDs12..23 only.
8. **Persistence — tested represented fields.** All six supplied original saves
   roundtrip unchanged; unmodeled original bytes are preserved. Internal
   BTPe/v40 includes active theft/audio/menu states, spy discovery and world
   sectors for debris, held weapon-window presentation, weapon-entry warnings,
   salvage inspection history and queued/held combat reports with casualty
   flags. v40 additionally retains fractional outdoor clocks and quiet-mode
   headers/cursors; earlier elapsed clocks migrate without RNG draws. v38
   reports migrate with no invented death flag. Pre-v35 infantry
   weapon lists migrate to the original direct selector. Ambiguous pre-v34 decorative marks are cleared. Old
   formats cannot recover history that they never stored. Active-invasion v29
   migration now compares positions, current and per-actor goals/waypoints and
   the next four inputs; stale cache follower coordinates recover on load. Original export remains limited to supported
   outdoor contexts rather than every internal native mode.
9. **Portability — Windows executable verified under Wine; hardware UNKNOWN.**
   MinGW-w64/SDL2 now builds the Windows game and all tests. Cross-platform
   input/state/pixel and save checks use a private Wine prefix. This found and
   fixed exclusive save creation, save replacement and large stack allocations.
   SDL dummy-device checks cover PCM and queue sequencing, not actual Windows
   drivers or speakers. The independent runtime is C11/SDL2; research tools and
   cached assets remain separate from its runtime dependencies.
10. **Provenance.** Authored code/docs are GPL-3.0-only. Original
    art/music/text/executable data stay outside Git and must be supplied by each
    runner. No original game source code is used. The README credits prior
    research and discloses AI-assisted work using OpenAI Sol 6.1 and Astra;
    independent C does not itself establish a formal clean-room process or
    rights to original assets.

11. **Custom games and authoring — CHI-dependent projects implemented.**
    The [transition plan](ENGINE_AND_EDITOR_PLAN.md) separates preparation from
    external units, independent packages, scripting and the desktop editor.
    [M5-P1–P5](M5_PREPARATION.md) establish content ownership, unit lookups,
    original dispatch and persistence boundaries. The
    [shared project loader](M5_AUTHORING_PROJECTS.md) now loads validated
    mech/weapon definitions and declared portraits, exports the 31-model Updated
    roster and binds saves to exact project snapshots. The
    [maps/events increment](M5_MAPS_EVENTS_EDITOR.md) adds finite maps, overlays,
    entrances, explicit saved event commands and a small Tk roster editor.
    The [independent game/editor](M5_INDEPENDENT_GAME_EDITOR.md) now supplies
    Last Beacon with its own pixels/font/sounds/text, named character templates,
    bounded Lua routing and a visual map/event editor with export and Play here.
    It needs no original resources; CHI-profile projects keep their explicit
    original dependency. Multi-planet jigsaw worlds, city overlays, pixel drawing,
    owned graphics, new definitions and vehicle presets are now implemented.
    Direct map footprint drawing now covers irregular buildings, courtyards,
    mixed heights, joined walls and shaped roads. Saved footprints remain
    editable and compile to ordinary game overlays. Combining later hand-painted
    layer details with automatic footprint rebuilding remains open: changed
    generated layers are protected from replacement. Exterior heights do not
    introduce interior floors or a runtime elevation system. See the
    [construction guide](M5_WORLD_ART_EDITOR.md#buildings-walls-and-roads).
    The [sprite editor](SPRITE_EDITOR.md) adds direction/pose editing, shared-image
    labels and independent previews. Named action animations, frame timing/sound
    cues, richer equipment abilities, arbitrary character/rule models, a script
    IDE/debugger and package migrations remain. Its guide lists the current
    five editor follow-ups, including authored repair/reload/salvage services.
    The [shared Unit Library](UNIT_LIBRARY_AND_LAUNCHER.md) and launcher now add
    reusable editable blueprints and application/game startup controls. Infantry
    squads and per-character sprites remain unsupported; existing infantry uses
    individual character templates and shared NPC/enemy artwork.
    Native Windows Tk verification and the full editor toolkit choice remain
    open. Original raw records and compiled assumptions are catalogued in the
    [content inventory](CONTENT_INVENTORY.md).

Both reference trees are guarded by content, mode, timestamp and Git-metadata
checks. The current external Git-config metadata difference is documented in
[TESTING](TESTING.md); the reference files and baseline are left as found.
No reference code is copied into the port and no
remote push is authorized.
