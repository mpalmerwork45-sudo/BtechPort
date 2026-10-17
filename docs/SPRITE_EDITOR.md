# Direction-aware sprite editing

The sprite editor opens from **right-click the roster animation → Edit sprite**,
or by double-clicking a sprite in **Maps / events → Graphics / sprites**.
Tiles, icons and screens keep the general pixel editor. Original artwork is
copied into the project before editing; neither reference directory is changed.

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
then top-to-bottom. Sprites remain limited to 32 images, each at most 64×64 RGBA
pixels. Clone a complete sprite in the library to make an independent design.

## Verification

Six Python cases cover sheet imports, original mech/character frame mapping,
shared directions, short sheets, usage detection, independent frame pastes,
dimension changes after rotation and non-mutating onion-skin previews. The full
Python suite passes **109/109**.

The actual Linux Tk workflow checks roster and library entry points, frame and
direction buttons, thumbnails, copy/paste/undo/redo, staged edits, independent
playback, timer cleanup, original character aliases, all-image scrolling,
Apply/discard, atomic save/reopen and minimum-window controls. Screenshot:
`work/sprite-editor.png`. Runtime code and save formats are unchanged by the
sprite UI. Native Windows Tk interaction is still unverified.

## Remaining editor work

1. **Animation authoring beyond walking:** named idle/fire/hit/wreck/jump actions,
   per-frame duration, sprite anchors, sound cues and runtime support for these
   declarations. Current previews describe the existing movement layouts.
2. **Richer artwork and scene tools:** pixel selections/layers, resizing/cropping,
   sprite-sheet export/reimport, reusable named building stamps, grouped movement
   of artwork with its entrances, and visible formation/entrance footprints.
3. **Event and quest debugging:** a connected event graph, objective journal,
   flag/command tracing, clickable validation errors and saved test checkpoints.
   Existing event forms and bounded Lua routes remain usable.
4. **More authored gameplay services and construction support:** repair, reload,
   healing and salvage commands with cost/result branches; construction guidance
   for units/equipment and support for additional equipment behaviors. Vehicle
   turret/arcs/critical rules remain a separate engine limitation.
5. **Distribution and compatibility:** a packaged launcher with dependency setup,
   an asset/provenance report, deliberate save migration between package revisions,
   and native Windows GUI verification. Existing export and strict snapshot saves
   work, but edited packages require fresh saves.
