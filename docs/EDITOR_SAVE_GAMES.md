# Saved games when using editor Play

Ordinary **Play from start** keeps six slots for the exact project revision
between launches. Logs and execution traces still get a separate run folder.
**Play here** and checkpoint experiments use isolated test saves so they cannot
replace the ordinary Play campaign.

The workspace reports the saved-game directory when it starts the player. The
run's `PLAY.json` records that path. Project saves are separate from the normal
Original/Updated launcher games, and from saves belonging to other projects.

## Saved games screen

Choose a game in the launcher and press **Saved games...**, or choose **Play →
Saved games** in the editor. The shared screen shows all six slots, local save
dates, content revisions and their locations: Launcher, Editor, Earlier editor
run or Backup. Empty current slots remain visible. Click headings to sort.

- **Continue selected** validates the save with the native player, retains its
  matching project revision and starts that campaign. It backs up the selected
  save and any existing destination quicksave before launching. Later in-game
  saves use stable slots for that revision. The active editor project is unchanged.
- **Back up selected** creates a separate dated copy. **Open backup folder**
  opens those copies in the desktop file manager. Backups appear in the table.
- **Recover copy** copies a validated save to the chosen empty slot for its
  original revision. An occupied slot produces a clear error and is preserved.
  Source bytes and timestamps are retained.
- **Locate matching campaign...** accepts an exact old project or retained
  snapshot when an earlier save has no matching revision on disk. It checks and
  retains that project; it never changes the save fingerprint to fit another game.

Launcher and editor slots remain separate and are both visible. Recovery targets
the location from which the screen was opened. An earlier save stays attached
to its earlier content, even when the working project has been edited.
Refresh the screen after making further edits or saving in a running game.

If the working project has moved or contains invalid edits, Saved games can
still find retained revisions using the registered campaign ID or its recorded
working path. Invalid pending editor fields also leave older saves accessible.
The screen explains when the current project is unavailable and shows existing
saves without inventing empty slots for an unknown current revision. A reused
path associated with multiple campaign IDs requires an explicit matching choice.

Before launching a project, the application retains one validated private copy
per runtime digest in `work/roster-editor/save-revisions/ID/DIGEST/game`. This
keeps project-owned data available after editing or moving the working project.
Games with external original-file requirements still need their configured
resources. Retained revisions/backups are never automatically deleted; keep
them with the saves when backing up the application state directory. Imported
resources remain private original-derived content.

Retained metadata records each editable source path separately, including when
editor Play runs a temporary exported project. These paths aid discovery;
native content validation still decides whether a save can be continued.

Discovery is bounded to 4,096 files and 4,096 earlier editor runs; it reports
limits rather than claiming an exhaustive filesystem search. A missing,
damaged, foreign or incompatible save cannot be continued/recovered merely
because its filename looks correct. Header/checksum inspection is descriptive;
the native decoder is the final authority for each action.

## Existing saves from older editor versions

Older editor Play launched every session with a new save directory. The files
were retained under `work/roster-editor/play-snapshots/run-…/play/`, but the next
launch did not look there. Current Play copies matching slots into its stable
save directory when that slot is vacant. It checks project ID, exact native
content digest, envelope length and checksum, chooses the newest valid source,
and preserves the original files. Existing current slots are never overwritten.

## After editing a game

A map, dialogue, rule or other runtime edit changes the content identity.
Saves from the previous revision remain attached to that exact revision; they
cannot be loaded by changing a filename or choosing another edition. This
prevents old positions, script labels and unit ordinals from being interpreted
against incompatible content.

Keep the old project or its retained `play-snapshots/run-…/game` folder to
continue that campaign. Preserve the newer edited project separately. The
existing **Migrate an old save** tool supports its documented authored-project
cosmetic/appended-definition policy; it does not silently migrate native CHI
terrain/script changes. One explicit native compatibility update can append
the two newly extracted endgame strings while proving all gameplay content
unchanged. [Migration limits](CONSTRUCTION_KIT_DELIVERY.md),
[endgame update utility](GAME_OVER_PRESENTATION.md#cache-compatibility-and-existing-campaigns).

## Recovery performed on 2026-10-24

The owner's recent Updated save was found in a retained editor session and
loaded successfully: Starport, 33,300 C-bills, tick 85,092. Both the matching
project and the later edited revision were preserved in ignored
`work/save-recovery-20261024-ajjxdoxc/`, along with the original save and previous
launcher registration. Matching copies were restored to stable editor/launcher
slots. The imported Updated registration now selects the recovered project;
the old original import remains untouched.

From this checkout, `./work/Resume-Recovered-Updated.sh` continues that exact
save and writes subsequent progress to its recovered campaign slots. Recovery
artifacts contain original-derived material and stay private.

The resume script now selects `recovered-game-with-endgame-fix`, a further
validated copy with the corrected original death popup. Its migrated save has
the identical progress payload. The earlier recovered project/save, latest
edited revision and pre-update launcher registration remain in the same backup
folder. New saves use the stable recovered campaign slots.
