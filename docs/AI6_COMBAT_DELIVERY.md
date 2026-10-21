# Mission mechanics batch — implementation and verification

Authorized 2026-10-21: AI6b, AI6c and construction-style completion together.
The existing CHI campaign, authored games without these extensions, and both
reference directories remain independent regression targets.

## Delivery boundaries

1. **Combat lifecycle (AI6b).** Named encounter groups, initial/reserve
   deployment, start/round-start/round-end/destruction hooks, round-based timers,
   survival/count queries and explicit scripted outcomes. Reinforcement commands
   are atomic: either every requested unit fits, or the failure route runs.
   A recurring round hook can retry; no hidden unbounded retry queue.
2. **Escort actors (AI6c).** Friendly/neutral groups, engine-controlled waypoints,
   arrival queries/hooks, hostile targeting of protected transports, terrain and
   occupancy checks. Actor state belongs to its encounter; retreat ends that
   attempt. Re-entering deliberately starts a fresh attempt. Objectives and
   ordinary mission variables retain campaign state.
3. **Construction styles.** Report missing parts, provide complete editable
   styles for corners, levels and road junctions, and preserve existing human
   assignments. Library imports and AI drawing must use the same rules.
4. **Playable delivery.** A separate timed-defence/vehicle-escort example,
   recorded authoring commands, editor forms, native scenarios and visual checks.

Each internal delivery receives a local commit; no permission pause is needed
between them. This document tracks intended scope, not verified completion.

## Runtime decisions

- Hooks suspend the existing event interpreter using an explicit saved
  continuation. They run only after queued attack text, graphics and audio have
  drained. `end` returns to combat. Nested battles, transfers and shops are not
  meaningful inside combat hooks and receive explicit validation/errors.
- Round timers count completed simulation rounds, never wall-clock time or UI
  ticks. A hook can name a first round and recurrence interval. Saved pending
  hooks and their ordering prevent duplicate rewards or lost notifications.
- Stable combat IDs, rather than array positions, identify mission units so
  pilot ejection cannot scramble group membership.
- Bounds stay explicit: 16 groups, 32 hooks, at most 12 non-party combat units
  including reserved units, and 24 total combat slots including party/ejections.
- Saves need a new optional version. Audit the existing reserved combat payload
  before choosing its exact layout; existing authored/original encodings must
  remain byte-compatible when the feature is absent.

## Evidence required

- Native loader/schema agreement and atomic command failure/Undo.
- Start, round and completed destruction ordering; simultaneous deaths;
  blocked reserve deployment and explicit retry; repeated hooks and outcomes.
- Save/reload while a hook dialog is held, between round boundaries, after
  reinforcement, during escort movement and after result cleanup.
- Escort movement through corners and obstacles with supported tracked,
  wheeled and hover terrain policies; no teleporting or Python simulation.
- Ordinary-input success, loss and retreat scenarios with bounded ticks/seeds.
- Editor creation/editing, diagnostics, Undo, Save/reopen and Play on a private
  display; construction coverage and library round trips.
- Appropriate original-game regressions, two-job Linux/Windows builds, isolated
  Wine checks where available, and immutable-reference verification.

Native Windows Tk remains unverified until exercised on native Windows.
