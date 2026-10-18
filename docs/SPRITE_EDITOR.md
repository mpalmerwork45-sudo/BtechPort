# Direction-aware sprite editing

The sprite editor opens from **right-click the roster animation → Edit sprite**,
or by double-clicking a sprite in **Maps / events → Graphics / sprites**.
Tiles, icons and screens keep the general pixel editor. Original artwork is
copied into the project before editing; neither reference directory is changed.
The [Unit Library](UNIT_LIBRARY_AND_LAUNCHER.md) also opens this editor for stored
designs. **Save to library** retains their edited sprites with the blueprint;
importing a design then carries its owned unit graphics into a game.

## Editing movement

1. Choose a direction using the eight compass buttons. The heading identifies
   the direction, movement frame and stored image, for example **Right - movement
   frame 2 of 4 | Image 10 of 32**. Image numbers in the UI start at one.
2. Click a thumbnail, use **Previous frame / Next frame**, or press
   **Alt+Left / Alt+Right**. **Alt+Up / Alt+Down** changes direction.
3. Draw with pencil, line, rectangle, fill or erase. RGBA colours, eyedropper,
   Flip X/Y, rotation, nudge, wrap and the grid work on the selected image.
   **All frames** applies a transform to the whole sprite.
4. **Copy frame / Paste frame** duplicates artwork into another pose. It replaces
   pixels without inserting/removing direction slots. The copy is independent;
   changing the pasted frame does not change its source. Undo/Redo includes pastes.
5. **Show previous frame faintly** places the preceding pose behind transparent
   pixels to help alignment. This ghost is only a preview and is never saved.
6. **Play preview** loops the selected direction in the separate preview box.
   Playback does not move the editing selection. The FPS control affects this
   preview only; game animation speed is unchanged.
7. **Apply** places all staged edits in shared document history. Then **Save** in
   the project editor writes the validated package. Closing without applying
   discards staged pixel edits. The roster animation refreshes after Apply.

Frame thumbnails scroll horizontally in **All images** mode. Navigation wraps
at the first/last pose and scrolls the selected thumbnail into view.

## Existing layouts and shared artwork

The editor follows the layouts already used by the player, without adding a new
animation format or remapping an existing sheet. **Preview as** selects a view;
it does not change the image's runtime assignment or package fingerprint.
The default comes from the unit presentation, sprite role or known source copy.

| Preview | Interpretation |
| --- | --- |
| Unit movement, 32 images | Four poses for each direction: up, up-right, right, down-right, down, down-left, left, up-left |
| Unit movement, other image counts | Original mech gait, reduced modulo the stored image count as in the renderer |
| Character movement | Up uses images 9–12; right and its diagonals use 5–8; down uses 1–4; left and its diagonals use 13–16 |
| Original mech movement | CHI's shared 16-image gait, also used by the global Locust/Stinger sprite roles |
| All images | Every stored image, in file order, without assuming movement directions |

Original mech diagonal/cardinal gaits reuse images with different cyclic starting
positions. The editor labels shared directions explicitly: an edit to one of
these images affects every direction that references it. Very short sheets
also reuse images; no extra poses are invented. A 32-image **per-unit** sprite
has eight independent directions, whereas global character/CHI role bindings
still use the original gait indices. Use **All images** to reach images unused
by a chosen role.

Create a new sheet through **Graphics / sprites → New**, choosing kind **sprite**
and 32 images for a new directional unit or 16 for an original-style character.
Importing a sheet accepts explicit frame dimensions and reads cells left-to-right,
then top-to-bottom. Sprites support up to 256 images, each at most 64×64 RGBA
pixels. Clone a complete sprite in the library to make an independent design.

## Named actions and artwork tools

**Edit action** defines idle/walk/fire/jump/damage/destruction tracks with image
order, duration and sequential combat sound cues. **Clone image** adds a pose.
See [the action contract](UNIT_ACTION_ANIMATIONS.md) and
[selection/layer/stamp tools](CONSTRUCTION_KIT_ART_TOOLS.md).

## Verification and remaining bounds

The current Linux engine, Python and Tk checks cover action timing, fallback,
individual infantry art, library import/export, layers, direction/frame controls,
copy/paste/undo, staged edits and save/reopen. See [TESTING](TESTING.md).

The [five editor milestones](EDITOR_COMPLETION_MILESTONES.md) are implemented.
Remaining extensions include arbitrary sprite anchors, imported audio cues,
full tabletop construction/vehicle rules, general save remapping after gameplay
changes, and native Windows Tk verification. Original gait and optional named
tracks coexist; exploration still advances with CHI's logical movement steps.
