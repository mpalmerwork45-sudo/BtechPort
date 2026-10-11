# Open questions after M1 — 2026-10-11

Resolved for the recorded MAP1 scenario: start `(69,25)` in half tiles, party/cursor agreement, 30 arrow actions with successful and blocked moves, gate 85, player collision's horizontal offset, 24×24 working-grid identity, and initial viewport/palette. These observations do not establish all-scene movement or a global property table.

1. **Next gate:** original Citadel entry/dialogue/exit. Recover exact packed trigger comparison, BLD decryption/control flow from `0xA0`, required opcode subset and state/mode changes. Converter annotations remain stale despite byte preservation.
2. Resolve full party/unit footprints, diagonal movement and local/world edge wrapping. M1's single-point collision matches its trace; edge blocking is approximate.
3. Establish outer-world stored/procedural boundaries and generation/RNG. The static 64×64 template assertion is insufficient; the observed local working grid is not proof of a global map.
4. Recover ANIMATE.ICN player/NPC dispatch, masking and facing, original status/border/menu rendering, and camera/palette behavior in additional modes. The 575 differing map-panel pixels are not fully classified.
5. Explain original 3913-byte saves versus reference's 4096 claim; prove load/save/reload before importing/exporting GAME files. The internal BTP1 encoding is unrelated.
6. Calibrate original timing, keyboard repeat, animation and cadet allowance/day/sleep gates. Credits changed 20→35 between recorded startup/walk snapshots; these fields are excluded from native parity.
7. Combat requires actual differential traces for recovered formulas, RNG, AI, heat, ammunition and aftermath. EXE salvage strings contradict inferences based only on absence of BLD wording.
8. Audit all 22 ANMs and reconcile header/dispatch contradictions; determine WWOODBT.SIF and audio/music roles.
9. Test a Windows build. Decide project licensing/distribution only if that work is requested; do not copy substantial GPL implementation without the user's explicit review.
10. Resolve the root's empty read-only `.git/` placeholder before local version-control commits. Leave the supplied reference repository untouched.
