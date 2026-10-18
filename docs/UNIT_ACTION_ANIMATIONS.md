# Unit animation and construction tools

**VERIFIED (Linux engine, model and Tk):** Sprite editor → **Edit action** defines
idle, walk, fire, jump, damage and destruction sequences. Choose a shared sequence
or eight directions, in N, NE, E, SE, S, SW, W, NW order. Each entry is
`image:duration`, for example `1:4 2:2 3:4`; the UI numbers images from one and
durations are 32 ms logical ticks. **Clone image** adds a pose without shifting
existing frame references. Up to 256 images fit in a sprite; the package retains
its total 1,048,576-pixel limit. Each track has at most 32 entries and 255 ticks.

The optional `animations` object in graphics JSON stores zero-based frame
indices, e.g. `"fire":{"directions":[[{"frame":0,"ticks":4}]],"sound":3}`.
The sprite preview uses these durations. Combat selects idle, movement, jump,
fire, damage and destruction tracks; attack and impact presentation waits for
their configured durations. Idle/travel loop, other actions hold the final pose.
Exploration preserves CHI's step-driven gait: walk-track time advances with the
four gait positions (four ticks per position), rather than walking while idle.
Missing actions retain the existing presentation. No original assets change.

Optional sound IDs 1–18 on fire/damage/destruction replace the corresponding
combat sound at its existing sequential transition. Zero retains the usual
sound. These are the player's existing sounds (or an independent game's sound
table), not arbitrary imported audio. Renderer calls never queue sound. Infantry
destruction stays silent unless an explicit destruction cue is supplied.

Infantry templates now accept an optional `image` referring to a sprite. Roster
**Choose sprite** and **Edit sprite** affect that character only. Library export
and import carry its artwork, named actions and editable pixel layers. Unset
images retain existing project/original infantry defaults.

Roster **Construction guidance** displays adapter movement, armor, critical
entries, heat and ammunition budgets. Two additional authored equipment
behaviors are supported: `engine_heat_sink` adds internal cooling (center torso
only), and `armor_plating` adds front armor points at its location. The existing
structure/cooling limits still apply. These are simplified construction adapters:
mass accounting, tabletop critical sizes, technology eras and component pricing
are not a complete tabletop construction ruleset. Existing heat sinks remain
damageable external components; jump jets retain the chassis jump capability.

Validation: `authored-action-animation`, Python `test_action_tracks.py`, existing
combat presentation/pacing tests and `native_smoke.py --construction-kit-only`.
