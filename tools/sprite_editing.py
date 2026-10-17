"""Describe the player's existing sprite layouts without rewriting artwork.

Preview modes are views of the same image slots, not new animation metadata.
Keep the CHI sequences aligned with core/animation.c and core/combat.c; a
32-image per-unit presentation follows frontend/art.c's eight-direction layout.
"""
import copy

DIRECTIONS = ('Up', 'Up right', 'Right', 'Down right', 'Down', 'Down left', 'Left', 'Up left')
VIEWS = ('Unit movement', 'Character movement', 'Original mech movement', 'All images')
MECH_FRAMES = ((0,1,2,3), (4,5,6,7), (6,7,4,5), (5,6,7,4),
               (8,9,10,11), (12,13,14,15), (15,12,13,14), (14,15,12,13))
PERSON_FIRST = (8,4,4,4,0,12,12,12)


def sequence(image, view, direction=0):
    count = len(image['frames'])
    if view == 'All images': return tuple(range(count))
    if view in ('Unit movement', 'Original mech movement'):
        frames = range(direction*4, direction*4+4) if count == 32 and view == 'Unit movement' else MECH_FRAMES[direction]
    else: frames = range(PERSON_FIRST[direction], PERSON_FIRST[direction]+4)
    return tuple(i % count for i in frames)


def default_view(document, image):
    identity = image['id']
    if any(p.get('image') == identity for p in document.content['presentations']): return VIEWS[0]
    roles = {b['slot'] for b in document.art['bindings'] if b['image'] == identity}
    if roles & {'player', 'npc', 'enemy'}: return VIEWS[1]
    if roles & {'locust', 'stinger'}: return 'Original mech movement'
    # Known copies retain their source name even after getting an owned ID.
    if image['name'].startswith(('Original sprite 166', 'Original sprite 270')): return VIEWS[1]
    if image['name'].startswith(('Original sprite 0', 'Original sprite 146')) or len(image['frames']) == 32: return VIEWS[0]
    return 'All images'


def describe(image, view, direction, frame, phase=None):
    frames = sequence(image, view, direction)
    place = phase if phase is not None else (frames.index(frame) if frame in frames else 0)
    if view == 'All images': return f"Image {frame+1} of {len(image['frames'])} | {image['name']}"
    return f"{DIRECTIONS[direction]} - movement frame {place+1} of {len(frames)} | Image {frame+1} of {len(image['frames'])}"


def sharing_note(image, view, direction):
    if view == 'All images': return 'All stored images. Choose a movement preview to see which images the player uses.'
    frames = set(sequence(image, view, direction))
    shared = [DIRECTIONS[d] for d in range(8) if d != direction and frames & set(sequence(image, view, d))]
    if shared: return 'Shared artwork: edits also affect ' + ', '.join(shared) + '.'
    return 'Four images for this direction. Copy/paste replaces an image without changing the sheet layout.'


def paste_frame(image, frame, source):
    """Copy pixels, not frame identities: fixed direction slots stay in place."""
    if source is None: return
    if len(source) != image['height'] or any(len(row) != image['width']*8 for row in source):
        from editor_model import EditorError
        raise EditorError('The copied frame has different dimensions. Copy a frame again after rotating the sprite.')
    image['frames'][frame] = copy.deepcopy(source)


def onion_rows(image, frame, previous):
    """Previous pose at one-quarter alpha under the current pose, preview only."""
    from art_editing import pixels
    rows, ghost = pixels(image, frame), pixels(image, previous)
    result = []
    for y, row in enumerate(rows):
        colors = []
        for x, rgba in enumerate(row):
            prior = ghost[y][x];alpha = int(rgba[6:],16);ghost_alpha = int(prior[6:],16)//4
            base = 190 if (x//4+y//4)%2 else 225
            below = [(int(prior[k:k+2],16)*ghost_alpha+base*(255-ghost_alpha)+127)//255 for k in (0,2,4)]
            colors.append('#'+''.join(f'{(int(rgba[k:k+2],16)*alpha+b*(255-alpha)+127)//255:02x}' for k,b in zip((0,2,4),below)))
        result.append(tuple(colors))
    return tuple(result)
