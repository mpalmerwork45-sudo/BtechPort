# Essential-character death presentation

The casualty message now uses the original popup over the game view, with the
original font, white text, name selection and wrapping. The old full-screen
replacement and invented recovery instruction have been removed. Acknowledging
the message shows the original replay question. Space and Enter select; No
exits, and Yes resets the campaign and enters the existing new-game flow while
retaining the selected edition and menu settings.

## Evidence and limits

**VERIFIED:** `tools/make_game_over_vectors.py` executes unmodified DOS 1.03
code at `0000:04A4..04DB`, using the audited mixed-party snapshot and explicitly
declared casualty prerequisites for Jason and Rex. Window selection calls
`14D3:17C6`; text passes through `1656:03F5` and `173D:00D5`. Execution stops at
`173D:086A`, before the keyboard/delay boundary. No executable patch is used.

Both native renders match the original-derived RGB hashes for the 200 × 40
interior at x112/y80. Text starts at column 14, row 10 and wraps at 25 columns.
The border uses native window 7 geometry, x104/y72, 216 × 56. The two public
fixtures contain only numeric observations, hashes and prerequisites. Original
text, glyph traces and image crops remain private under `work/jason-death/`.

The following original branch at `0000:04DB..04F2` supplies the replay prompt,
calls the native Yes/No routine and either calls new-game initialization or
sets the exit flag. The port's held prompt, replay/reset and quit behavior are
tested. Full pixel equivalence of the surrounding battlefield, every casualty
context and the screen sequence following DOS new-game initialization remains
**UNKNOWN**; the interior comparison does not establish those claims.

## Cache compatibility and existing campaigns

The local BTTA conversion now appends two extracted endgame strings, IDs 373
and 374, as v25. All earlier text IDs, bytes and font data retain their values.
The loader and editor also accept older 373-entry v24 caches. An old imported
project remains playable with its old content identity and recovery fallback;
merely opening it does not change its resources or saves.

For an existing imported campaign, create a separate updated copy:

```sh
python3 tools/chi_dialogue_update.py --project "path/to/old-game" \
  --data "Original DOS" --output "work/game-with-endgame-fix" \
  --save "path/to/old-save.btp"
```

The output must not exist. `--save` is optional; with it, the output includes
`recovered-save.btp`. Both native validators must accept the migration. Every
runtime file except the appended dialogue cache must be byte-identical; every
earlier string, source tag and font byte must match. The save payload after its
160-byte envelope remains identical. The old project and save are preserved.
This narrow compatibility update cannot migrate map, script, rule or unit edits.
See [saved-game recovery](EDITOR_SAVE_GAMES.md).

## Verification, 2026-10-24

- All 95 Linux native tests and all 95 Windows/Wine native tests pass. Five
  focused native checks on each platform pass after the final dialogue bounds
  adjustment.
- The full Python suite passes 462 tests; all three focused native-dialogue
  migration tests pass, including the copy updater added after that suite run.
- Real SDL window checks on Linux and Windows/Wine pass death display, Space
  acknowledgement, held save/load and No exit. This is not a Windows Tk check.
- Fresh v25 imports reach both declared campaign endings: 75,573 inputs for
  Original and 75,556 for Updated with Legacy selected through Settings.
- The recovered owner's Updated save retains tick 85,092, 33,300 C-bills and
  its entire progress payload after this compatibility update.

Private reports: `work/jason-death/`, `work/game-over-gui.json` and
`work/last-save-recovery.json`. These extend the earlier
[campaign acceptance](CHI_ACCEPTANCE.md); the retained C5 distribution artifacts
predate the subsequent save-retention and death-presentation fixes.
