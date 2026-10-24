# Enhanced-only campaign verification

**VERIFIED on Linux and Windows/Wine, 2026-10-24:** the imported Updated
campaign reaches its ending from a fresh game while retaining its default
Enhanced combat rules. This closes the Enhanced-only walkthrough gap recorded
at the earlier [C4.5 acceptance](CHI_ACCEPTANCE.md).

## Declared route

`tools/chi_enhanced_route.py` generates 36,316 ordinary inputs through driving,
rubble recovery, shell/infantry/duel/pair training victories, Rick's device,
the invasion and physical escape. It then recruits a five-person party, pays
for the technician/medic apprenticeships, earns the disk/password prerequisites
and completes all eleven cache doors, map room, power sequence and ending.

The Chameleon is selected through the normal loan menu. Computer combat uses
the normal control/order options. The route tries bounded ordinary outdoor
waits before the random patrol/invasion draw, answers each actual quiz and
records the chosen inputs. Recruitment also uses bounded ordinary input delays.
It uses the owner's authorized money shortcut. No rule, save field, quest flag,
rank, coordinate or RNG byte is changed to progress. The escape helper consults
the known destroyed terrain in a planning copy; it emits ordinary orders and
does not modify the played state. Planning/replay artifacts remain private.

This is one successful, declared route. It does not establish every random
patrol outcome, every unit composition, combat balance or every DOS branch.
The route targets the supported unedited import, not arbitrary modified maps.

## Comparisons and continuations

- `btp-chi-import-tests --enhanced-route` compares the built-in and imported
  Updated game after every input. It asserts Enhanced remains selected on
  every tick and compares canonical state/RNG and rendered boundaries.
- The same test resumes the real route from 44 decoded held contexts on each
  platform. The existing stable-unit identity mapping is test-only; all other
  state bytes remain checked. It does not weaken production save validation.
- Eight fresh-process checkpoints resume to the identical ending state and
  exact final save: training orders, training victory, invasion orders, Rex's
  film, hospital recruitment, a cache-door opening, map room and ending film.
- Linux/Windows ending saves, rendered frame, canonical JSON and BLD trace
  match byte-for-byte. All eight paired held saves also match.
- The ending trace observes **17/26 programs, 826/1,816 instructions and
  152/578 branch destinations**, with zero script faults. Declared programs
  are counted separately from programs actually executed. Native C-handler
  internal branch coverage remains UNKNOWN.

## Reproduce

Build the native tools, then choose a new private output folder:

```sh
python3 tools/chi_enhanced_acceptance.py --output work/enhanced-proof
python3 tools/chi_enhanced_acceptance.py --output work/enhanced-proof --windows
```

The first command imports fresh Updated content from `Original DOS`, plans the
full input stream and runs the Linux checks. The second uses the same project
and inputs with the Windows build under Wine. `--data PATH` selects a supported
DOS 1.03 installation. Original resources, decoded content, routes, saves and
screens are not committed. Existing game registrations and personal saves are
not involved.

Retained evidence: `work/chi-enhanced-verified-20261024/`, including both
platform reports, input hash, binary hashes, endings, eight held continuations
and both parity logs. Planner development attempts are retained separately in
`work/chi-enhanced-route-20261024/`. Earlier C4.5 Legacy-selected comparisons
remain separate evidence and retain their original scope.

Native Windows Tk and independent Astra review remain pending. This follow-up
does not refresh the earlier C5 application archives or publish a release.
