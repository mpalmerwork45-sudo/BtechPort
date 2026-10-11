# Open questions after M2a — 2026-10-11

Resolved for the recorded MAP1 scenarios: initial movement/collision, working grid and palette; Citadel packed entrance `(69,20)`, deferred outdoor step, payload decryption matching all runtime bytes, five-choice menu, six Hall texts, retained choice and exit. State byte 10 becomes 1 on entry and stays 1 outside; its complete semantic meaning is still unknown. See [Citadel evidence](M2_CITADEL_EVIDENCE.md). These observations do not establish all-scene movement, complete BLD behavior or a global property table.

1. **Next gate (M2b):** Request to see Katrina → first conversation → return to menu. Verify persistent flag changes and required indexed dispatch/setter/native-action opcodes. The other three Citadel choices currently fail visibly; do not silently skip them. Converter annotations remain stale despite byte preservation.
2. Resolve full party/unit footprints, diagonal movement and local/world edge wrapping. M1's single-point collision matches its trace; edge blocking is approximate.
3. Establish outer-world stored/procedural boundaries and generation/RNG. The static 64×64 template assertion is insufficient; the observed local working grid is not proof of a global map.
4. Recover ANIMATE.ICN player/NPC dispatch, masking and facing, original status/border/menu rendering, and camera/palette behavior in additional modes. The 575 differing map-panel pixels are not fully classified.
5. Explain original 3913-byte saves versus reference's 4096 claim; prove load/save/reload before importing/exporting GAME files. The tested internal BTP2 encoding (with BTP1 migration) is unrelated.
6. Calibrate original timing, keyboard repeat/input flushing, animation and allowance/day/sleep gates. Credits changed 20→35 between startup/walk snapshots but stay 35 on the Hall loop; economy is absent from the core. `F2` records a delay request; its original cadence is not reproduced.
7. Combat requires actual differential traces for recovered formulas, RNG, AI, heat, ammunition and aftermath. EXE salvage strings contradict inferences based only on absence of BLD wording.
8. Audit all 22 ANMs and reconcile header/dispatch contradictions; determine WWOODBT.SIF and audio/music roles.
9. Test a Windows build. Decide project licensing/distribution only if that work is requested; do not copy substantial GPL implementation without the user's explicit review.
Local Git is now initialized on `main`; incremental commits exclude both supplied directories and proprietary artifacts. No Git configuration changes or pushes occurred. The reference repository remains untouched.
