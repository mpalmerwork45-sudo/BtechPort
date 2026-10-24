# Independent Astra audit — 2026-10-24

**Scope:** review of the editable CHI campaign milestones and the subsequent
save-management/Enhanced-route work at `223af14`, followed by focused fixes.
The review inspected implementation, negative cases and retained evidence;
it did not repeat the original reverse-engineering project or certify every
DOS branch. Three parallel reviews covered saves, import/delivery boundaries,
and campaign/continuation evidence. The primary review integrated the fixes
and exercised the launcher/editor.

## Findings and disposition

All seven findings below are fixed in source. No personal save or imported
campaign was migrated as part of the audit.

| ID | Severity | Reproduction and impact | Fix and affected gate |
| --- | --- | --- | --- |
| A1 | P1 | Clone an original BLD speech, then edit its text. The old exporter could include the entire original speech in an otherwise accepted reconstruction recipe. An edited native dialogue override had the same problem because its baseline lived in a binary cache. Private reproductions retained 480 and 51 original characters respectively. | [Recipe export](../tools/chi_recipe.py) now references matching original text spans, including the indexed native dialogue table. Rebuilding obtains those spans from the recipient's local originals. Regression cases check both literal exclusion and exact reconstruction. C5 provenance/delivery. |
| A2 | P2 | Choose a different copy of the DOS files as input, then request generated output beneath this checkout's `Original DOS/`. Import, reconstruction and the endgame updater protected the chosen source and `UnBattletech/`, but omitted the fixed original directory in this case. | Shared [output-path guard](../tools/chi_import.py) protects both reference roots as well as supplied sources/projects, before staging or extraction. Tests use simulated reference roots; the actual references were never written. C1/C2/C5 immutability. |
| A3 | P2 | Move or invalidate the editable project after it has retained a playable revision. Opening Saved games first required loading that working project, hiding intact retained saves. An invalid pending editor form could also block discovery. | [Catalogue](../tools/save_catalogue.py) supports a known campaign identity independently of its working document; [GUI](../tools/saved_games_view.py) uses registered/retained origins and clears stale rows on failed refresh. Native fingerprint checks still govern Continue/Recover. Each editable origin is retained even when Play validates a temporary export. C5 recovery. |
| A4 | P2 | A project whose ID ends in `-2` through `-6` has a quicksave filename resembling a numbered slot. Generic suffix parsing mislabeled that quicksave and its backup. | Slot parsing first resolves the campaign ID from the native save envelope. Six-slot regression covers the collision. C5 save management. |
| A5 | P2 | Windows bridge verification could succeed with an empty Linux artifact glob; stale output could conceal missing new artifacts. Held tests decoded and compared a save but then continued the original in-memory state after one idle input. | [Bridge evidence](../tools/chi_bridge_evidence.py) requires four successful Linux journeys and all 174 declared artifacts, records hashes/failures and stages fresh native output. [Native tests](../tests/test_chi_bridge_native.c) now drive subsequent inputs from decoded state. Acceptance also rejects faults/unresolved observations. C4.4/C5 evidence. |
| A6 | P2 | Enhanced acceptance accepted `--data`, but parity and several inherited planner reads still used this checkout's default DOS directory. This prevented reproducing the proof with only the selected installation. | [Acceptance](../tools/chi_enhanced_acceptance.py) records and propagates the selected source through parity, quiz, map and cache planning. It also checks the retained input-route hash before re-verification. C4.5 reproducibility. |
| A7 | P2 | C4.5 JSON used the length of the declared program catalogue for its measured program count: 26 rather than 17. The Markdown tables already distinguished observed and declared coverage correctly. | [C4.5 reporting](../tools/chi_acceptance.py) counts programs with executed instructions and records `declared_programs` separately. Historical reports remain intact, with their ambiguous field explicitly corrected here. C4.5 evidence reporting. |

## Verification

- Fresh Linux and Windows/Wine bridge runs pass all four journeys and 58 held
  save points per platform. All **174 paired save/frame/next-state artifacts**
  match. Subsequent journey inputs now use the decoded states.
- Real Linux launcher/editor journeys pass with both Linux and Windows/Wine
  players: six slots, native Continue/F5/quit, backups, occupied/vacant recovery,
  earlier revisions, a moved working project, an invalid editor draft and a
  failed refresh without stale actionable rows.
- **78 affected Python tests pass**, with zero skips/failures (42.84 s).
  Catalogue, play-recovery and evidence-guard tests cover the new failure
  cases; recipe/import/endgame checks verify reconstruction and reference
  rejection. Exact suite patterns and commands are in [TESTING.md](TESTING.md).
- The retained Enhanced route's hash, recorded native binary hashes, eight
  full saved continuations and final Linux/Windows save/frame/state/trace bytes
  were independently checked. Coverage was recomputed from the traces:
  **17/26 programs, 826/1,816 instructions, 152/578 branch destinations**, zero
  faults or unresolved observations. The 36,316-input full route was not
  regenerated during this audit.
- Both earlier C4.5 ending traces independently recompute to **17/26 programs,
  872/1,816 instructions, 181/578 branch destinations**, zero faults/unresolved
  observations. The legacy-selected Updated route remains distinct from the
  Enhanced-only route.
- A real **4,418-input** Enhanced driving/recovery prefix also passes with a
  copied DOS source while Python reads from the default source are denied.
  This checks the source-selection fix without replaying the entire campaign.

Private reproductions and reports live in `work/audit-astra-20261024/`, including
`campaign-evidence-audit.json`, `import-delivery/` and the fresh `bridge/`
Linux/Windows evidence. Earlier GUI reports are preserved under `prior-gui/`;
the new GUI reports remain `work/saved-games-gui{,-windows}.json`.
Original-derived dialogue, recipes, projects, screenshots and saves stay private.

## Remaining limits and next steps

The audit closes the separate Astra-review action for this declared scope.
It does not close native Windows Python/Tk verification: this host provides
Linux Tk and the Windows player under Wine, with no configured native Windows
desktop available for the wizard/editor journey.

The previous application archives predated the latest save/death/audit changes.
The subsequent [delivery refresh](DELIVERY_REFRESH_20261024.md) now ships those
fixes and passes packaged setup/import/edit/reconstruction/save checks on Linux,
plus the Windows binaries under Wine. That is separate follow-up evidence;
no archive was published remotely and native Windows Tk remains unverified.

Original DOS fidelity outside the measured comparisons, all possible scripts
and combat outcomes, general migration across gameplay edits, and arbitrary
content with deliberately stripped provenance remain outside this sign-off.
The text-reference fix protects ordinary cloned/edited original spans; it is
not a licence determination or a universal detector for rewritten content.

Both references retain all **1,287 content/mode/mtime entries**. The owner's
three pending demo edits and twenty normal saves match the existing hashes
(and save mtimes); the recovered source and restored progress payloads also
match. None is part of the audit commits.
