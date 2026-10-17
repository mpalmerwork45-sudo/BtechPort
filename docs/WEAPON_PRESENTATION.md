# Weapon presentation and persistent fire — 2026-10-17

The on-map weapon presentation now follows the original firing poses, sound
order, directional beam origins, missile paths and impact hold. Fire animation
uses map redraws rather than the host tick. Numeric attacks, ammunition, damage,
heat and AI choices are unchanged by this presentation work.

## Original observations

**VERIFIED in the recorded bounds:**

- `make_weapon_presentation_vectors.py` executes the original `12E8:12C7`
  routine and `0000:1732` animation interpreter for **2,400 sequences**: both
  mech sprite families and infantry, applicable weapons, all eight directions,
  hits/misses, infantry targets, graphics off, close and offscreen positions.
- Firing poses precede weapon sound. Each visible actor pose requests five
  VGA retraces. Offscreen actors advance their programs without that wait.
- Missile weapons play their launch sound, then advance a repeating six-frame
  program four pixels per draw. The former midpoint icon used the wrong
  program and position. Offscreen samples still advance the program phase.
- Energy beams start at the original family/direction-specific muzzle offset.
  The line rasterization completes before its weapon sound. Personal energy
  weapons use VGA yellow/green; vehicle lasers use red/magenta.
- A hit plays sound 4. For weapons 7 onward and a visible target, three impact
  frames redraw consecutively without individual waits. The final frame then
  holds for five retraces. Its anchor is the ground coordinate, eight pixels
  above a mech. The previous port spread those frames over six host ticks and
  offset their drawing incorrectly.
- `make_fire_animation_vectors.py` executes `0000:2A93` for **720 observations**
  across viewport edges and sector seams. Visible fire flips 124/125 once per
  map redraw; offscreen fire and static debris retain their sprite bytes.
  Both outdoor `0000:051B` and combat `0000:0E4B` use that same persistent ring.

Only numeric observations/hashes enter the fixtures. Drawing, audio playback,
screen flips, outtakes and waits are declared harness boundaries; original
trajectory and animation instructions run unchanged. The existing ignition
generator `make_fire_vectors.py` retains its separate RNG/ring-insertion role.

## Native implementation and limits

Visible pose waits accumulate the five-retrace durations before conversion to
32 ms ticks, keeping rounding within one host tick for the entire program.
The final impact frame holds for three ticks (96 ms, rounding the requested
five retraces). Its preceding rapid frames are represented by the original
ordered program; the retained frame is what the host renderer presents.

Missiles draw the correct six-frame program at successive visible positions;
beams use the original integer path, muzzle data and palette. Firing/beam/hit/
retirement sounds drain sequentially. The actor retains its firing pose through
the event. Queued actors stay pending during an earlier report pause, keeping
the next pose and report from appearing prematurely. Deaths remain hidden
until their own retirement event.

**APPROXIMATE:** the original missile loop and beam rasterizer have no explicit
per-sample retrace wait. Their physical duration depends on the CPU, video
adapter and blitter. The port presents missile samples at its 32 ms display
boundary and completes beam drawing within one such boundary. This verifies
geometry, frame order, sound order and explicit waits; it does not establish
cycle-exact XT drawing or physical speaker response.

Fire now advances during visible movement, firing-pose changes, missile draws,
impact redraws and outdoor updates. Idle outdoor frames use the existing
eleven-retrace clock, averaging about 157 ms per change. A movement key triggers
one outdoor update, including two/four-step mode. Speaker holds, empty combat
microsteps and held menus do not run an unrelated flame clock. The early
training-drive host clock and CPU drawing costs retain their documented
approximations.

Fire, corpses and wrecks remain visible during ordinary exploration at their
world positions. They survive scene changes and saves until replaced in the
original 64-entry ring. This persistence already existed in the port; the audit
adds original redraw/visibility comparisons and an outdoor regression.

## Cache and save compatibility

**BTCC/v12** adds 48 signed muzzle offsets and eight six-frame missile loops to
the local numeric combat cache. `prepare_combat.py` extracts them reproducibly
from the hash-checked executable. No original assets are added to the repo.

New internal saves use **BTPi/v44**, retaining the 20,480-byte payload and the
separate Original `BTS1` / Updated `BTU1` envelopes. The existing effect stage/
age bytes now distinguish the new presentation states; no struct bytes are
implicitly serialized. Older v40–v43 held effects keep their old stage/clock
interpretation and finish without replaying a sound. New queues then use the
verified sequence. Older tick-driven fire phases migrate to the same displayed
frame, after which redraws drive them. Original DOS GAME imports remain supported.

## Verification and reproduction

The presentation suite compares all 2,400 pose, retrace, trajectory, impact and
sound-dispatch observations. It also runs 200 timed/sound sequences, save/PCM
continuations and all seven older presentation stages. The world-mark suite
adds 720 redraw comparisons, persistent outdoor fire/wrecks, six idle changes
over thirty host ticks, menu holds, movement versus empty microsteps and phase
migration. Linux and Windows SDL each exercise F5/F9 during firing, missile
flight, beam sound, impact and outdoor fire, comparing complete state/pixels
with headless continuation. These use generated test saves and dummy audio.

```sh
python3 tools/prepare_combat.py
python3 tools/make_weapon_presentation_vectors.py
python3 tools/make_fire_animation_vectors.py
ctest --test-dir build --output-on-failure -R 'weapon-presentation-primary|world-marks-primary'
python3 tools/native_smoke.py --weapon-effects-only
python3 tools/native_smoke.py --windows --weapon-effects-only
```

The dependent ordinary input routes were regenerated with
`python3 tools/make_followup_replays.py --training --complete`. The fresh ending
uses 75,573 inputs and spy replacement 58,886; these are native playability
routes, separately from the bounded original comparisons. Current platform
results are recorded in [TESTING.md](TESTING.md).
