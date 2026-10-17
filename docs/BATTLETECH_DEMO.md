# BattleTech demo and the next editor work

Implemented 2026-10-17. **BattleTech: Last Beacon** turns the demonstration into
a short mercenary adventure with recognizable BattleMechs and the original
CHI graphics, font, borders and combat sound. The original asset-free Beacon
example remains available for independent-engine tests and new-game templates.

Play: `sh scripts/play-battletech-demo.sh`.
Edit: `python3 tools/game_editor.py examples/battletech-demo`.
See the [scenario README](../examples/battletech-demo/README.md) for dependencies,
controls, saving, a walkthrough and exact limits.

The package contains three maps, nine sourced variants, two starting MechWarriors,
an optional recruit, a nine-model broker, ComStar information, two battles,
54 event nodes, two endings and persistent once-only payments. Full completion
without purchases pays 23,000 C-bills on top of the initial 18,000. Declining the
second contract ends after the first 8,000 payment. Retreat leaves the relevant
contract open. Updated's existing Enhanced tactical profile is the default.

Named authored characters now display correctly in the CHI frontend's party,
crew, inspection and combat text instead of falling back to Jason/Rex. The
original identity aliases and strings remain the fallback for non-authored games.
This changes presentation only, not character-loss rules or the save layout.

## Verification

The dedicated `battletech-demo-contracts` test uses ordinary input for the full
two-battle route and saves/reloads after every exploration/decision input and
regular combat checkpoints. It also checks withdrawal, the early ending,
the optional recruit/purchase/crew branch, authored names, the overhead map,
duplicate-payment protection, the final ending and quit. Optional purchase and
crew checks use the same domain APIs as the existing broker/assignment menus;
the completed recorded route needs neither a purchase nor a third pilot.

Reproduce it with:

```sh
ctest --test-dir build -R battletech-demo-contracts --output-on-failure
python3 tools/native_smoke.py --battletech-demo-only
```

**VERIFIED**, 2026-10-17:

| Check | Result |
| --- | --- |
| Full native CTest | **68/68**, 43.95 s |
| Full Python tools suite | **69/69**, 2.96 s |
| Focused Windows/Wine CTest | **4/4**, 14.12 s |
| Focused ASan/UBSan/LeakSanitizer CTest | **4/4**, 4.33 s |
| Linux SDL | **12/12** held F5/F9 screens, identical resumed headless state/pixels; full two-battle route passed |
| Windows/Wine SDL | **12/12** held F5/F9 screens, identical Linux headless state/pixels; full two-battle route passed |
| Editor document workflow | New copy, C validation, export, declared assets and attribution preserved |
| Launcher | Fresh authored campaign, 18,000 C-bills, Enhanced combat |

The focused platform checks cover the demo, authored continuations, original
content lifetime and combat UI/save progression. The ordinary full route wins
its battles in 1,447 and 1,890 simulation ticks, respectively, using the default
seed. This is a completed route, not a randomized balance survey. Screenshots
of the actual original-style map, dialogue and battle prompts were inspected.
Native Windows hardware/Tk and physical audio were not tested in this increment.
No new DOS equivalence claims are made for the invented maps or scenario.

Builds used two jobs, one platform at a time. Native and Windows builds produced
no warnings; sanitizer compilation retains the two previously recorded sign
conversion warnings in original-renderer code, with no runtime sanitizer error.
Logs/screenshots are in ignored `work/battletech-demo-*.log`, `work/bt-demo-*`
and `work/adventure-*.ppm`. The package's validated content digest is
`03af2458539d9b184815bd6d76820e2d39fcce47c29703efdd059a0cfdb40d9c`.
Both reference directories pass the 1,287-entry content/mode/mtime guard.

## Recommended next five milestones

1. **Show real CHI tiles in the editor.** Decode a preview atlas from the player's
   supplied files through the shared loader. Add a visual tile palette, selection
   stamps for complete buildings/trees/shorelines, and entrance/formation footprint
   overlays. Keep numeric IDs for diagnostics. The present CHI map editor uses
   swatches, making coherent original scenery unnecessarily hard to assemble.
   Gate: build and play a new town using the GUI without consulting tile numbers.

2. **Author repairs, reloads and salvage.** Add validated service commands through
   the shared gameplay APIs, with explicit cost, target selection, failure and
   success continuations. Put a working Mech-It service in Grayhaven and implement
   a defined salvage award after a contract. Do not call arbitrary BLD service
   addresses from Lua. Gate: damage a mech, repair/reload it, collect salvage once,
   then save/reload at every held prompt without duplicating costs or rewards.

3. **Add an objective journal and event debugger.** Named objectives with
   offered/active/completed/failed states should drive both journal text and map
   markers. Show event history, current flags and validation errors in the editor;
   allow starting a test from a declared checkpoint. Gate: trace both demo endings
   and a retreat without manually inspecting JSON or replaying the whole scenario.

4. **Build a presentation/asset workspace.** Preview sprites by mech, import
   images through the existing converter, select building portraits by asset ID,
   and author bounded animation/sound sequences. Decouple portraits from the old
   fixed building slots. Gate: add one new character portrait, a complete new mech
   sprite set and a building animation entirely through the GUI, with correct
   runtime palettes and preserved attribution.

5. **Make editable packages practical to distribute and update.** Add a project
   launcher, dependency setup, validation report, packaged player build and a
   deliberately versioned save migration path based on stable IDs. Preserve exact
   snapshot loading; migrations must validate references and fail without touching
   the original save. Gate: export a custom game, launch it on Linux and native
   Windows, then load its save after a supported content revision.

Start with **1**, then **2**. Those remove the largest visible authoring and
gameplay gaps in this demo. The current core already supports more authored
maps, conversations and contracts; increasing content alone would not solve the
editor's tile selection, service and playtesting limitations.
