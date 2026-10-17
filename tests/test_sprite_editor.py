"""Sprite-sheet interpretation, pose duplication and non-destructive previews."""
import copy
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from art_editing import new_image, import_image, pixels, brush, transform, display_rows
from editor_model import EditorError
from sprite_editing import sequence, default_view, describe, sharing_note, paste_frame, onion_rows


class SpriteEditingTests(unittest.TestCase):
    def test_imported_sheet_keeps_clockwise_direction_groups(self):
        from PIL import Image
        with tempfile.TemporaryDirectory(prefix='btp-sprite-sheet-') as tmp:
            path = Path(tmp) / 'driving.png'
            sheet = Image.new('RGBA', (64, 128))
            for frame in range(32):
                sheet.paste((frame, 100, 200, 255),
                            ((frame%4)*16, (frame//4)*16, (frame%4+1)*16, (frame//4+1)*16))
            sheet.save(path)
            image = import_image(path, 'test', [], 'sprite', 16, 16)
        for direction in range(8):
            chosen = sequence(image, 'Unit movement', direction)
            self.assertEqual([int(pixels(image, f)[0][0][:2], 16) for f in chosen],
                             list(range(direction*4, direction*4+4)))
        self.assertEqual(describe(image, 'Unit movement', 2, 9),
                         'Right - movement frame 2 of 4 | Image 10 of 32')

    def test_original_mech_shared_direction_phase(self):
        image = new_image('test', [], 'Locust', 'sprite', 16, 16, 16)
        self.assertEqual(sequence(image, 'Unit movement', 2), (6, 7, 4, 5))
        self.assertEqual(sequence(image, 'Unit movement', 6), (15, 12, 13, 14))
        self.assertIn('Up right, Down right', sharing_note(image, 'Unit movement', 2))
        # A 32-image *role binding* still takes CHI's original walk index;
        # only per-unit presentations have the eight independent direction sets.
        image['frames'] *= 2
        self.assertEqual(sequence(image, 'Original mech movement', 2), (6, 7, 4, 5))
        self.assertEqual(sequence(image, 'Unit movement', 2), (8, 9, 10, 11))

    def test_character_directions_and_shared_short_animations(self):
        image = new_image('test', [], 'Person', 'sprite', 16, 16, 16)
        self.assertEqual(sequence(image, 'Character movement', 0), (8, 9, 10, 11))
        self.assertEqual(sequence(image, 'Character movement', 4), (0, 1, 2, 3))
        for direction in (1, 2, 3):
            self.assertEqual(sequence(image, 'Character movement', direction), (4, 5, 6, 7))
        image['frames'] = image['frames'][:1]
        self.assertEqual(sequence(image, 'Character movement', 7), (0, 0, 0, 0))
        self.assertIn('movement frame 3 of 4', describe(image, 'Character movement', 7, 0, 2))
        self.assertEqual(sequence(image, 'All images'), (0,))

    def test_usage_selects_preview_without_changing_package(self):
        image = new_image('test', [], 'Arbitrary art', 'sprite')
        doc = SimpleNamespace(content={'presentations': []}, art={'bindings': []})
        self.assertEqual(default_view(doc, image), 'All images')
        doc.art['bindings'] = [dict(slot='player', image=image['id'])]
        self.assertEqual(default_view(doc, image), 'Character movement')
        doc.art['bindings'][0]['slot'] = 'locust'
        self.assertEqual(default_view(doc, image), 'Original mech movement')
        doc.content['presentations'] = [dict(image=image['id'])]
        before = copy.deepcopy(doc)
        self.assertEqual(default_view(doc, image), 'Unit movement')
        self.assertEqual(doc, before)

    def test_paste_detaches_pose_and_rejects_rotated_dimensions(self):
        image = new_image('test', [], 'Non-square', 'sprite', 3, 2, 16)
        brush(image, 0, (0, 0), (0, 0), 'aa440080')
        original = copy.deepcopy(image)
        clipboard = copy.deepcopy(image['frames'][0])
        paste_frame(image, 7, clipboard)
        brush(image, 7, (0, 0), (0, 0), '123456ff')
        self.assertEqual(image['frames'][0], original['frames'][0])
        self.assertEqual(clipboard, original['frames'][0])
        self.assertEqual(len(image['frames']), 16)
        transform(image, 'Rotate right', all_frames=True)
        rotated = copy.deepcopy(image)
        with self.assertRaisesRegex(EditorError, 'different dimensions'):
            paste_frame(image, 7, clipboard)
        self.assertEqual(image, rotated)

    def test_onion_skin_only_changes_preview_of_transparent_pixels(self):
        image = new_image('test', [], 'Ghost', 'sprite', 2, 1, 2)
        image['frames'] = [['ff0000ff00000000'], ['000000000000ffff']]
        original = copy.deepcopy(image)
        ghost = onion_rows(image, 1, 0)
        plain = display_rows(image, 1)
        self.assertNotEqual(ghost[0][0], plain[0][0])
        self.assertEqual(ghost[0][1], '#0000ff')
        self.assertEqual(image, original)


if __name__ == '__main__': unittest.main()
