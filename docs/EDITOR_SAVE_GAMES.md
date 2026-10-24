# Saved games when using editor Play

Ordinary **Play from start** keeps six slots for the exact project revision
between launches. Logs and execution traces still get a separate run folder.
**Play here** and checkpoint experiments use isolated test saves so they cannot
replace the ordinary Play campaign.

The workspace reports the saved-game directory when it starts the player. The
run's `PLAY.json` records that path. Project saves are separate from the normal
Original/Updated launcher games, and from saves belonging to other projects.

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
