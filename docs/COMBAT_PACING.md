# Combat pacing correction — 2026-10-17

The combat-speed pause belongs after each attack, rather than between movement
steps. The previous port called the correct delay helper at the wrong boundary.
At the default speed, that inserted ten idle ticks between every pair of
movement steps, including rounds in which nobody fired.

## Original evidence

**VERIFIED control flow:** the owner's unpacked executable runs unchanged in
the existing Unicorn harness. `tools/make_combat_pacing_vectors.py` executes
48 complete `12E8:000C(0)` waves using the existing MAP1 capture. Cases cover
all six speeds, graphics on/off, idle and moving units, and zero/one/two gun
orders. Positions, equipment, skills, seed and the absence of enemy orders
are declared prerequisites. Only numeric observations enter the fixtures;
no executable, graphics, text or RAM is committed.

- `12E8:1002..1286` advances movement without a combat-speed wait.
- `12E8:0D76` calls `0E31:1DCC` after attack presentation. Speeds 0–4 request
  `12 × speed` VGA retraces; speed 5 waits for a key at that attack boundary.
- With graphics disabled, `12E8:12DF` jumps to casualty handling at `1B0C`.
  Invisible attack/impact poses incur no animation waits.
- With graphics enabled, the observed firing-pose waits are five retraces
  each. Impact draws its three frames without individual waits, then holds
  for five retraces. These observations identify a further animation audit;
  this change does not claim exact on-map weapon animation timing.

The harness intercepts screen/speaker/outtake and OS wait boundaries, as
listed in [fixture metadata](../tests/fixtures/combat-pacing-primary.json).
The sequence and wait counts are original-executable observations, not a
wall-clock measurement of an 8 MHz XT. Secondary disassembly helped locate
the routines; no reference implementation was copied into the engine.

## Implementation

Movement now advances once per 32 ms host tick. An attack completes its
sequential sound/effect/outtake presentation, then holds its report for the
selected speed before the next queued attack or movement step. Graphics-off
attacks skip unshown pose delays; casualty sounds and retirement still run.
The existing tick conversion and original sound programs are unchanged.

Speed 5 holds attacks rather than movement. Enter acknowledges an attack;
Space also acknowledges it and interrupts continuous computer play, retaining
individual computer assignments. The current wave drains before its command
menu returns, as before. All behavior applies to Original and Updated editions
through their shared combat engine.

The existing saved delay byte holds the countdown or key wait. Original v40
and Updated v43 formats are unchanged. Existing saved waits finish, and new
attacks use the corrected boundary. The effect age stops at its final pose
while a casualty sound drains, keeping the saved value within valid bounds.

**Measured native comparison:** the same controlled movement-only checkpoint,
default speed 2, sound disabled, prior executable versus revised executable:

| Measurement | Before | After |
|---|---:|---:|
| Interval between movement microsteps | 352 ms | 32 ms |
| Twelve-step wave | 122 ticks / 3,904 ms | 12 ticks / 384 ms |

This is about ten times faster for that whole wave. Battles with attacks still
wait for their authentic sounds and selected report pauses; their total speedup
depends on the events. Physical CPU drawing cost and display scheduling remain
**APPROXIMATE**.

## Verification

The new `combat-primary-pacing` suite consumes all 48 original observations.
It checks final positions, twelve movement advances without extra waits,
all six post-attack delays, zero hidden-pose delays, queued reports, Space
interruption and unchanged final records/RNG across speed selections. Each
tested game tick is compared with a save/restore continuation, including PCM.
The existing sequential-audio test now drains the final report pause before
checking battle completion.

Ordinary input replays were regenerated where their old waits no longer lined
up with combat. This includes training, invasion, arena wins/losses, spy
replacement and the fresh-game ending. The apprenticeship checkpoint generator
reran the original routines against the new route prerequisites. The fresh
ending uses 78,829 inputs; spy replacement uses 62,142. Replays establish native
playability, separately from the bounded original comparisons.

The SDL pacing check deliberately uses the normal clock, without
`--smoke-fast`. Four scenarios check movement, a held attack and Enter/Space
acknowledgement against exact headless input/state/pixels, using an isolated
display and dummy audio device. It uses generated test saves, never player
saves. Current platform results are recorded in [TESTING.md](TESTING.md).

```sh
python3 tools/make_combat_pacing_vectors.py
ctest --test-dir build --output-on-failure -R 'combat-primary-pacing|combat-ui-save-progression'
python3 tools/native_smoke.py --combat-pacing-only
python3 tools/native_smoke.py --windows --combat-pacing-only
```

## Recommended next increment

Compare the complete on-map weapon presentation: firing poses, the point at
which sound starts, projectile/beam travel, and impact-frame timing. The
existing generic pose clock remains approximate even though the combat-speed
pause is now at the verified boundary. Keep that work separate from numeric
combat rules and from any physical XT speaker-calibration claim.
