# Open questions after bounded M3d–M3h — 2026-10-12

The invasion, destroyed Citadel, native world generation/travel, Starport,
Rex/Commando and technician recruitment, owned-mech services, title music and
building portraits are implemented. See [evidence](M3D_H_PROGRESS.md) and
[next five tasks](PROJECT_STATUS.md). Confidence applies to each compared span,
not to the complete campaign.

1. **Invasion and character loss:** the native combat-window escape approximates
   the original packed-sector crossing. Mech retention and loss presentation
   are tested, but full original pilot ejection, body damage and character-loss
   RNG remain open. General encounters still finish on destruction of unit zero;
   the original broader surviving-party/wreck paths need recovery.
2. **World encounters:** generation matches 30 whole sectors across three seeds,
   and 18 original candidate rosters match. Terrain placement, engagement/flee,
   cadence, mixed-party AI, loot/salvage and aftermath need whole-encounter
   comparisons. Global RNG/bootstrap and world-seed initialization remain
   approximate. Town maps and BLD dispatch are loaded, but only the bounded
   Starport route has later-town integration coverage.
3. **Party and technicians:** Rex and generic agent records are compared; saved
   following, inspection and selected-person shop equipment work. Original
   formation, multi-unit collision, complete crew allocation, equipment transfer,
   technician field repairs and understudy effects remain open. Recruitment's
   post-dialogue RNG coin uses native logical ticks instead of the DOS busy loop.
4. **Services:** 47 original numeric cases cover refits and partial repair/reload
   boundaries. The native service layout and batched presentation remain
   approximate. Weapon/sink/leg repair costs follow recovered instructions but
   need broader differential cases; unrelated engine/gyro/sensor damage is kept.
5. **Later campaign:** spy outcomes, more companions, timed NPC routes, healing,
   later BLD actions, original cache puzzles and the ending remain unfinished.
   Unsupported native/script contexts produce visible errors.
6. **Long-route NPC/RNG timing:** the first quiz/mission RNG matches; long
   original waits before keys alter later arrivals/quiz draws. The earlier
   181-checkpoint comparison retains three explicit RNG prerequisites.
   Native input-only playability does not prove complete original timing.
7. **Combat and effects:** earlier live turns and independent friendly orders
   pass their bounded checks. General initiative, broader mixed-party decisions
   and defeat outcomes need original comparisons. The presentation effect queue
   remains bounded to seven events, so larger encounters can omit extra visual
   effects even though numeric attacks resolve. The stationary training shell
   remains the user's deliberate change; original moving-target fixtures remain.
8. **Graphics and audio:** PC speaker title divisors/timing and the building
   portrait table match original instructions. Host PCM volume/filtering, frame
   cadence, beam placement and whole-screen parity are approximate. The
   portrait-entry quality/RNG guard, further animation dispatch, combat sounds,
   PCjr audio and remaining status UI are not fully recovered.
9. **Original GAME compatibility:** supplied saves are 3,913 bytes; original
   import/export requires executed load/save/reload comparisons. Internal
   BTPI/v18 has a 16,384-byte payload / 16,400-byte BTS1 file and preserves
   party, service, music and combat state. v1–v17 migrate only their represented
   contexts. World initialization is still owner-cache-derived.
10. **Portability and distribution:** Windows remains untested. Any requested
    distribution needs asset/licence review; independent C alone provides no
    legal clean-room or asset-rights guarantee.

The immutable-tree guard includes both supplied trees' content, modes, mtimes
and Git metadata. Known external editor metadata drift is restored exactly to
the recorded baseline. Local commits remain on main without pushes. README
acknowledgements credit the reverse-engineering contributors explicitly.
