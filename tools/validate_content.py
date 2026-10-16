#!/usr/bin/env python3
"""Validate the provisional unit-authoring sample, without original game data.

This is an offline contract experiment, not a player package loader. Structural
rules come from the checked-in schema; cross-record rules live here until M5a
provides one shared validator for the player, tools and eventual editor.
"""
import argparse
import copy
from decimal import Decimal, DecimalException
import hashlib
import json
from pathlib import Path
import re
import sys

SCHEMA = Path(__file__).resolve().parents[1] / 'schemas/content-v1.schema.json'
MAX_BYTES = 1024 * 1024
KEYWORDS = {'$schema', '$defs', '$ref', 'title', 'description', 'type', 'const',
            'enum', 'properties', 'required', 'additionalProperties', 'items',
            'minItems', 'maxItems', 'uniqueItems', 'minimum', 'maximum',
            'minLength', 'maxLength', 'pattern'}


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'duplicate JSON key {key!r}')
        result[key] = value
    return result


def _constant(value):
    raise ValueError(f'non-finite JSON number {value}')


def _decimal(value):
    try:
        number = Decimal(value)
        if not number.is_finite():
            return _constant(value)
        # JSON Schema integers are mathematical integers, including 1.0. Parse
        # exactly: float rounding must not silently turn a fraction into an ID.
        if number != number.to_integral_value():
            raise ValueError('fractional numbers are unsupported by this prototype')
        if abs(number) > 2**53:
            raise ValueError('number exceeds prototype bounds')
        return int(number)
    except DecimalException as exc:
        raise ValueError('number exceeds prototype bounds') from exc


def read_json(path):
    with Path(path).open('rb') as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError(f'JSON exceeds {MAX_BYTES} bytes')
    try:
        return json.loads(raw.decode('utf-8'), object_pairs_hook=_pairs,
                          parse_constant=_constant, parse_float=_decimal)
    except (UnicodeError, RecursionError) as exc:
        raise ValueError('JSON must be UTF-8 and have bounded nesting') from exc


def check_schema(node, root):
    """Fail if our schema grows beyond the small supported keyword subset.

    This deliberately is not a general-purpose JSON Schema implementation;
    only the repository's schema is accepted, with local definition references.
    """
    unknown = set(node) - KEYWORDS
    if unknown:
        raise ValueError(f'unsupported schema keywords: {sorted(unknown)}')
    if 'type' in node and node['type'] not in ('object', 'array', 'string', 'integer'):
        raise ValueError(f'unsupported schema type: {node["type"]!r}')
    if 'additionalProperties' in node and node['additionalProperties'] is not False:
        raise ValueError('schema objects must explicitly forbid additional properties')
    if node.get('type') == 'array' and not isinstance(node.get('items'), dict):
        raise ValueError('schema arrays require one items schema')
    if '$ref' in node:
        ref = node['$ref']
        if not ref.startswith('#/$defs/') or ref[8:] not in root['$defs']:
            raise ValueError(f'unsupported schema reference: {ref}')
    for group in ('properties', '$defs'):
        for child in node.get(group, {}).values():
            check_schema(child, root)
    if 'items' in node:
        check_schema(node['items'], root)


def _pointer(path, key):
    return path + '/' + str(key).replace('~', '~0').replace('/', '~1')


def _structure(value, schema, root, path, errors):
    def error(message):
        errors.append(f'{path or "/"}: {message}')
    if '$ref' in schema:
        _structure(value, root['$defs'][schema['$ref'][8:]], root, path, errors)
    kind = schema.get('type')
    types = {'object': dict, 'array': list, 'string': str, 'integer': int}
    if kind and type(value) is not types[kind]:
        error(f'expected {kind}')
        return
    if 'const' in schema and value != schema['const']:
        error(f'expected {schema["const"]!r}')
    if 'enum' in schema and value not in schema['enum']:
        error(f'expected one of {schema["enum"]}')
    if kind == 'object':
        for key in schema.get('required', []):
            if key not in value:
                errors.append(f'{_pointer(path, key)}: required field is missing')
        props = schema.get('properties', {})
        if schema.get('additionalProperties') is False:
            for key in sorted(set(value) - set(props)):
                errors.append(f'{_pointer(path, key)}: unknown field')
        for key in props:
            if key in value:
                _structure(value[key], props[key], root, _pointer(path, key), errors)
    elif kind == 'array':
        if not schema.get('minItems', 0) <= len(value) <= schema.get('maxItems', MAX_BYTES):
            error(f'item count must be {schema.get("minItems", 0)}..{schema.get("maxItems", MAX_BYTES)}')
            return
        if schema.get('uniqueItems') and len({json.dumps(v, sort_keys=True) for v in value}) != len(value):
            error('items must be unique')
        for i, item in enumerate(value):
            _structure(item, schema['items'], root, _pointer(path, i), errors)
    elif kind == 'integer':
        if value < schema.get('minimum', value) or value > schema.get('maximum', value):
            error(f'must be {schema.get("minimum")}..{schema.get("maximum")}')
    elif kind == 'string':
        if not schema.get('minLength', 0) <= len(value) <= schema.get('maxLength', MAX_BYTES):
            error('string length is outside the schema bounds')
        if 'pattern' in schema and not re.search(schema['pattern'], value):
            error('string does not match the required format')


def _asset_path(root, value):
    """One portable spelling on Windows/Linux; never inspect escaped paths."""
    parts = value.split('/')
    reserved = re.compile(r'^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])$', re.I)
    for part in parts:
        if (not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_. -]*', part)
                or part.endswith(('.', ' ')) or reserved.fullmatch(part.split('.')[0].rstrip(' .'))):
            return 'use a portable relative path with forward slashes; no traversal, drive or reserved names'
    base = root.resolve()
    current = base
    try:
        for part in parts:
            # Explicit case checking also works on case-insensitive hosts.
            if part not in {entry.name for entry in current.iterdir()}:
                return 'asset file is missing or its letter case differs'
            current = current / part
            if current.is_symlink():
                return 'asset paths must not use symbolic links'
            # Also covers Windows junctions/reparse points that may not be
            # reported as symlinks by the host Python version.
            try:
                current.resolve(strict=True).relative_to(base)
            except ValueError:
                return 'asset path escapes its content directory'
        if not current.is_file():
            return 'asset path must name a regular file'
    except OSError:
        return 'asset path cannot be read'
    return None


def validate(document, directory, no_placeholders=False):
    schema = read_json(SCHEMA)
    check_schema(schema, schema)
    errors = []
    _structure(document, schema, schema, '', errors)
    if errors:
        return errors
    tables = {name: {} for name in ('assets', 'weapons', 'mechs')}
    identities = {}
    prefix = document['package_id'] + ':'
    for name, table in tables.items():
        for i, item in enumerate(document[name]):
            path = f'/{name}/{i}/id'
            identity = item['id']
            if not identity.startswith(prefix):
                errors.append(f'{path}: ID must belong to package {document["package_id"]!r}')
            if identity in identities:
                errors.append(f'{path}: duplicate ID {identity!r}; first at {identities[identity]}')
            identities[identity] = path
            table[identity] = item
    for i, asset in enumerate(document['assets']):
        path = f'/assets/{i}'
        if asset['width'] % asset['frame_width'] or asset['height'] % asset['frame_height']:
            errors.append(f'{path}: sheet dimensions must be multiples of frame dimensions')
        frames = (asset['width'] // asset['frame_width']) * (asset['height'] // asset['frame_height'])
        for state, bases in asset['states'].items():
            for j, base in enumerate(bases):
                if base % 8 or base + 8 > frames:
                    errors.append(f'{path}/states/{state}/{j}: eight-direction frame block exceeds sheet or is misaligned')
        if asset['kind'] == 'placeholder':
            if 'path' in asset:
                errors.append(f'{path}/path: a placeholder must not claim an asset file')
            if no_placeholders:
                errors.append(f'{path}/kind: placeholder needs authored artwork')
        elif 'path' not in asset:
            errors.append(f'{path}/path: external_sheet requires a file path')
        else:
            error = _asset_path(Path(directory), asset['path'])
            if error:
                errors.append(f'{path}/path: {error}')
    for i, weapon in enumerate(document['weapons']):
        path = f'/weapons/{i}'
        ranges = weapon['range']
        if not ranges['near'] <= ranges['medium'] <= ranges['far']:
            errors.append(f'{path}/range: require near <= medium <= far')
        if (weapon['kind'] == 'energy') != (weapon['ammo_per_shot'] == 0):
            errors.append(f'{path}/ammo_per_shot: energy uses zero ammo; other kinds need positive ammo')
    for i, mech in enumerate(document['mechs']):
        path = f'/mechs/{i}'
        capabilities = mech['capabilities']
        if 'walk' not in capabilities or 'run' not in capabilities:
            errors.append(f'{path}/capabilities: this profile requires walk and run')
        if ('jump' in capabilities) != (mech['movement']['jump'] > 0):
            errors.append(f'{path}/movement/jump: jump points and jump capability must agree')
        if mech['presentation'] not in tables['assets']:
            errors.append(f'{path}/presentation: unknown asset ID {mech["presentation"]!r}')
        slots = set()
        for j, mount in enumerate(mech['loadout']):
            place = f'{path}/loadout/{j}'
            if mount['slot'] in slots:
                errors.append(f'{place}/slot: duplicate mount slot')
            slots.add(mount['slot'])
            weapon = tables['weapons'].get(mount['weapon'])
            if weapon is None:
                errors.append(f'{place}/weapon: unknown weapon ID {mount["weapon"]!r}')
            elif weapon['kind'] == 'energy' and mount['ammo']:
                errors.append(f'{place}/ammo: energy mount must have zero ammunition')
            elif weapon['kind'] != 'energy' and mount['ammo'] < weapon['ammo_per_shot']:
                errors.append(f'{place}/ammo: starting loadout must supply at least one shot')
    return errors


def canonical_bytes(document):
    """Canonical definitions only, not an asset digest or save compatibility ID.

    Identity and slot order are explicit; frame order is animation time order
    and must not be sorted. Never mutate the caller's authored source.
    """
    result = copy.deepcopy(document)
    for name in ('assets', 'weapons', 'mechs'):
        result[name].sort(key=lambda item: item['id'])
    for mech in result['mechs']:
        mech['capabilities'].sort()
        mech['loadout'].sort(key=lambda item: item['slot'])
    return (json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('content', type=Path)
    parser.add_argument('--canonical', action='store_true', help='write canonical JSON to stdout after validation')
    parser.add_argument('--no-placeholders', action='store_true', help='require referenced artwork files (does not decode images)')
    args = parser.parse_args(argv)
    try:
        document = read_json(args.content)
        errors = validate(document, args.content.parent, args.no_placeholders)
    except (OSError, ValueError, RecursionError) as exc:
        print(f'{args.content}: {exc}', file=sys.stderr)
        return 1
    if errors:
        for error in errors:
            print(f'{args.content}:{error}', file=sys.stderr)
        return 1
    canonical = canonical_bytes(document)
    if args.canonical:
        sys.stdout.buffer.write(canonical)
    else:
        placeholders = sum(a['kind'] == 'placeholder' for a in document['assets'])
        print(f'VALID prototype: mechs={len(document["mechs"])}, weapons={len(document["weapons"])}, '
              f'assets={len(document["assets"])}, placeholders={placeholders}')
        print('Definition SHA-256: ' + hashlib.sha256(canonical).hexdigest())
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
