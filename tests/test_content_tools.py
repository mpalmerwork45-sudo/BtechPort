"""Authoring contract checks; needs neither DOS assets nor a built player."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import validate_content_prototype as content


class ContentTools(unittest.TestCase):
    def setUp(self):
        self.sample = content.read_json(ROOT / 'examples/content-demo/content.json')
        self.temporary = tempfile.TemporaryDirectory(prefix='btp authoring ')
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)

    def errors(self, value=None):
        return '\n'.join(content.validate(self.sample if value is None else value, self.directory))

    def test_sample_and_schema(self):
        self.assertEqual(self.errors(), '')
        schema = content.read_json(content.SCHEMA)
        content.check_schema(schema, schema)
        schema['unevaluatedProperties'] = False
        with self.assertRaisesRegex(ValueError, 'unsupported schema keywords'):
            content.check_schema(schema, schema)
        for unsupported in ({'type': 'number'}, {'additionalProperties': {'type': 'integer'}},
                            {'type': 'array', 'items': []}):
            with self.subTest(unsupported=unsupported), self.assertRaises(ValueError):
                content.check_schema(unsupported, schema)

    def test_version_types_and_unknown_fields(self):
        mutations = [('schema_version', True, 'expected integer'),
                     ('schema_version', 2, 'expected 1'),
                     ('rules_profile', 'dos', 'prototype-tactics'),
                     ('surprise', 42, 'unknown field')]
        for key, value, message in mutations:
            with self.subTest(key=key, value=value):
                candidate = copy.deepcopy(self.sample)
                candidate[key] = value
                self.assertIn('/' + key, self.errors(candidate))
                self.assertIn(message, self.errors(candidate))
        self.sample['mechs'][0]['movement']['walk'] = 1.25
        self.assertIn('/mechs/0/movement/walk: expected integer', self.errors())

    def test_missing_and_bounded_fields(self):
        del self.sample['mechs'][0]['structure']['head']
        self.sample['weapons'][0]['damage'] = 256
        self.sample['mechs'][1]['loadout'][0]['slot'] = 11
        errors = self.errors()
        self.assertIn('/structure/head: required', errors)
        self.assertIn('/damage: must be 1..255', errors)
        self.assertIn('/slot: must be 0..10', errors)

    def test_duplicate_and_wrong_namespace_ids(self):
        self.sample['weapons'][0]['id'] = self.sample['assets'][0]['id']
        self.sample['mechs'][0]['id'] = 'another:mech'
        errors = self.errors()
        self.assertIn('/weapons/0/id: duplicate ID', errors)
        self.assertIn('/mechs/0/id: ID must belong', errors)

    def test_wrong_kind_and_missing_references(self):
        self.sample['mechs'][0]['presentation'] = 'workshop:spark-beam'
        self.sample['mechs'][0]['loadout'][0]['weapon'] = 'workshop:missing'
        errors = self.errors()
        self.assertIn('/presentation: unknown asset', errors)
        self.assertIn('/weapon: unknown weapon', errors)

    def test_capabilities_and_jump_consistency(self):
        self.sample['mechs'][0]['capabilities'].append('teleport')
        self.assertIn('/capabilities/3: expected one of', self.errors())
        self.sample['mechs'][0]['capabilities'].pop()
        self.sample['mechs'][2]['movement']['jump'] = 0
        self.assertIn('jump points and jump capability must agree', self.errors())
        self.sample['mechs'][0]['capabilities'] = ['walk', 'walk']
        self.assertIn('items must be unique', self.errors())

    def test_weapon_ranges_ammo_and_mount_slots(self):
        self.sample['weapons'][0]['range']['far'] = 1
        self.sample['weapons'][1]['ammo_per_shot'] = 0
        self.assertIn('near <= medium <= far', self.errors())
        self.assertIn('other kinds need positive ammo', self.errors())
        self.sample['weapons'][1]['ammo_per_shot'] = 1
        self.sample['mechs'][1]['loadout'][0]['ammo'] = 0
        self.sample['mechs'][1]['loadout'][1]['ammo'] = 1
        self.sample['mechs'][1]['loadout'][1]['slot'] = 0
        errors = self.errors()
        self.assertIn('at least one shot', errors)
        self.assertIn('energy mount must have zero', errors)
        self.assertIn('duplicate mount slot', errors)

    def test_animation_geometry_and_missing_states(self):
        asset = self.sample['assets'][0]
        asset['width'] = 127
        asset['states']['walk'] = [7, 48]
        errors = self.errors()
        self.assertIn('multiples of frame dimensions', errors)
        self.assertIn('/states/walk/0', errors)
        self.assertIn('/states/walk/1', errors)
        del asset['states']['wreck']
        self.assertIn('/states/wreck: required', self.errors())

    def test_placeholder_and_external_asset_requirements(self):
        self.assertIn('placeholder needs authored artwork', '\n'.join(content.validate(self.sample, self.directory, True)))
        asset = self.sample['assets'][0]
        asset['path'] = 'art/Unit Sheet.dat'
        self.assertIn('placeholder must not claim an asset file', self.errors())
        asset['kind'] = 'external_sheet'
        self.assertIn('missing or its letter case differs', self.errors())
        (self.directory / 'art').mkdir()
        (self.directory / asset['path']).write_bytes(b'presence check only; image decoding is later')
        self.assertEqual(self.errors(), '')
        asset['path'] = 'art/unit Sheet.dat'
        self.assertIn('letter case differs', self.errors())
        del asset['path']
        self.assertIn('requires a file path', self.errors())

    def test_portable_paths_and_symlinks(self):
        asset = self.sample['assets'][0]
        asset['kind'] = 'external_sheet'
        for path in ('../escape', '/absolute', 'C:/drive', 'art\\sheet', './sheet',
                     'art//sheet', 'CON.png', 'CON .png', 'art/AUX.dat', 'sheet.', 'sheet ', 'a\n'):
            with self.subTest(path=path):
                asset['path'] = path
                self.assertIn('portable relative path', self.errors())
        asset['path'] = 'link'
        try:
            (self.directory / 'link').symlink_to(ROOT)
        except (OSError, NotImplementedError):
            self.skipTest('host does not permit creating symbolic links')
        self.assertIn('must not use symbolic links', self.errors())

    def test_names_and_ids_reject_trailing_control_characters(self):
        for field, value in (('id', 'workshop:unit\n'), ('name', 'Unit\n'), ('name', 'Unit\ud800')):
            with self.subTest(field=field):
                candidate = copy.deepcopy(self.sample)
                candidate['mechs'][0][field] = value
                self.assertIn('required format', self.errors(candidate))

    def test_canonical_identity_is_independent_of_list_order(self):
        before = copy.deepcopy(self.sample)
        canonical = content.canonical_bytes(self.sample)
        self.assertEqual(self.sample, before)
        self.sample['mechs'].reverse()
        self.sample['weapons'].reverse()
        for mech in self.sample['mechs']:
            mech['capabilities'].reverse()
            mech['loadout'].reverse()
        self.assertEqual(content.canonical_bytes(self.sample), canonical)
        self.assertEqual(content.canonical_bytes(json.loads(canonical)), canonical)
        self.sample['assets'][0]['states']['walk'].reverse()
        self.assertNotEqual(content.canonical_bytes(self.sample), canonical)

    def test_malformed_json(self):
        path = self.directory / 'input.json'
        for source in ('{"x":1,"x":2}', '{', '{"x":NaN}', '{"x":Infinity}',
                       '{"x":1e999}', '{"x":1e999999999999999999999}',
                       '{"x":1.00000000000000001}', '['*2000, '\ud800'):
            with self.subTest(source=source[:40]):
                path.write_bytes(source.encode('utf-8', errors='surrogatepass'))
                with self.assertRaises(ValueError):
                    content.read_json(path)
        path.write_text('{"x":1.0}', encoding='utf-8')
        self.assertEqual(content.read_json(path), {'x': 1})
        path.write_bytes(b' ' * (content.MAX_BYTES + 1))
        with self.assertRaisesRegex(ValueError, 'exceeds'):
            content.read_json(path)

    def test_cli_diagnostics_and_canonical_output_without_original_data(self):
        path = self.directory / 'sample with spaces.json'
        path.write_text(json.dumps(self.sample), encoding='utf-8')
        def run(*args):
            return subprocess.run([sys.executable, str(ROOT / 'tools/validate_content_prototype.py'),
                                   str(path), *args], cwd=self.directory,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        success = run('--canonical')
        self.assertEqual(success.returncode, 0, success.stderr)
        self.assertEqual(success.stdout, content.canonical_bytes(self.sample))
        blocked = run('--no-placeholders')
        self.assertEqual(blocked.returncode, 1)
        self.assertIn(b'/assets/0/kind', blocked.stderr)
        self.sample['mechs'][0]['presentation'] = 'workshop:missing'
        path.write_text(json.dumps(self.sample), encoding='utf-8')
        failure = run()
        self.assertEqual(failure.returncode, 1)
        self.assertEqual(failure.stdout, b'')
        self.assertIn(b'/mechs/0/presentation: unknown asset', failure.stderr)


if __name__ == '__main__':
    unittest.main()
