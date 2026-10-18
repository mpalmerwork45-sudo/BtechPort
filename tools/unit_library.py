"""Reusable unit blueprints, dependency closure and transactional project imports.

Each library entry is an independent JSON bundle, rather than one compiled
roster. The shared C project validator checks bundles through a small editable
preview project. Owned damage, campaign flags and save records never enter it.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import re
import tempfile
import uuid

from editor_model import EditorError, ProjectDocument, encoded, run_validator

ROOT = Path(__file__).resolve().parents[1]
FORMAT = 'btp-library-unit-v1'
KINDS = ('Mechs', 'Vehicles', 'Infantry')
SOURCE_FILES = ('CREDITS.md', 'LICENSE.md', 'SOURCE-README.md', 'ART-SOURCE-README.md',
                'VEHICLE-SOURCE-README.md', 'sources.json', 'ORIGINAL-ADAPTATION.md')


def read_json(path):
    if path.is_symlink() or path.stat().st_size > 16*1024*1024:
        raise EditorError(f'Invalid or oversized library file: {path.name}')
    try:
        return json.loads(path.read_bytes())
    except (ValueError, RecursionError) as exc:
        raise EditorError(f'Cannot read {path.name}: {exc}') from exc


def closure(document, identity, kind='Mechs'):
    """Export just a blueprint's referenced definitions and owned images."""
    content = copy.deepcopy(document.content)
    art = dict(format='btp-art-v1', schema_version=1, images=[], bindings=[])
    person = None
    if kind == 'Infantry':
        if document.adventure is None: raise EditorError('This project has no infantry templates.')
        person = copy.deepcopy(next(p for p in document.adventure['people'] if p['id'] == identity))
        person.setdefault('name', person['identity'].split(':')[-1].replace('-', ' ').title())
        content['mechs'] = []
    else:
        content['mechs'] = [copy.deepcopy(next(m for m in content['mechs'] if m['id'] == identity))]
        kind = 'Vehicles' if content['mechs'][0].get('kind') == 'vehicle' else 'Mechs'
    weapon_ids = {m['weapon'] for u in content['mechs'] for m in u['loadout']}
    equipment_ids = {m['definition'] for u in content['mechs'] for m in u.get('equipment', [])}
    content['weapons'] = [w for w in content['weapons'] if w['id'] in weapon_ids]
    content['equipment'] = [e for e in content.get('equipment', []) if e['id'] in equipment_ids]
    ammo_ids = {w['ammunition'] for w in content['weapons']}
    content['ammunition'] = [a for a in content['ammunition'] if a['id'] in ammo_ids]
    presentation_ids = {u['presentation'] for u in content['mechs']}
    content['presentations'] = [p for p in content['presentations'] if p['id'] in presentation_ids]
    image_ids = {p['image'] for p in content['presentations'] if p['source'] == 'package:art'}
    if person:
        # Infantry art is a project-wide role in the current runtime. Keep a
        # copy for preview/export, but do not silently replace another game's
        # global infantry artwork during an ordinary person import.
        art['bindings'] = copy.deepcopy([b for b in document.art['bindings'] if b['slot'] in ('npc', 'enemy')])
        image_ids.update(b['image'] for b in art['bindings'])
    art['images'] = copy.deepcopy([i for i in document.art['images'] if i['id'] in image_ids])
    source = {}
    for name in SOURCE_FILES:
        path = document.root / name
        if path.is_file() and not path.is_symlink(): source[name] = path.read_text(encoding='utf-8')
    # Retain imported-source credits without recursively embedding the entire
    # project's attribution file on every round trip through the library.
    inherited=json.loads(document.metadata.get('LIBRARY-SOURCES.json',b'[]'))
    for record in inherited:
        for name,text in record.get('provenance',{}).get('documents',{}).items():
            if name not in source:source[name]=text
    presentation = None
    if 'presentation' in document.manifest:
        presentation = json.loads(document.snapshot[document.manifest['presentation']])
    unit = person or content['mechs'][0]
    editor=json.loads(document.metadata.get('EDITOR.json',b'{}'))
    editing={'pixel_layers':{key:copy.deepcopy(value) for key,value in editor.get('pixel_layers',{}).items() if key in image_ids}}
    return dict(format=FORMAT, schema_version=1, entry_id=identity, revision=1, kind=kind,
                name=unit.get('name', identity), definition=identity, content=content,
                person=person, graphics=art, presentation=presentation,editing=editing,
                infantry_source=('chi:infantry' if person and document.manifest['requires'] != 'none'
                                 and not any(b['slot'] == 'npc' for b in art['bindings']) else 'package'),
                provenance=dict(project=document.manifest['title'], documents=source))


def needs_original(bundle):
    # Infantry has no mech presentation. Preserve its external art dependency
    # explicitly instead of accidentally previewing an independent demo sprite.
    return (bundle.get('infantry_source') == 'chi:infantry'
            or any(p['source'].startswith('chi:') for p in bundle['content']['presentations']))


def preview_files(bundle):
    """A minimal project lets existing property/sprite tools edit any entry."""
    template = ROOT / ('examples/battletech-demo' if needs_original(bundle) else 'examples/beacon-demo')
    manifest = read_json(template / 'project.json')
    content = copy.deepcopy(bundle['content'])
    adventure = read_json(template / 'adventure.json')
    fallback = read_json(template / 'content.json')
    manifest.update(package_id='unit-library', content_version='1.0.0', title=bundle['name'],
                    scripts=[], assets=[], definitions='content.json', adventure='adventure.json',
                    graphics='graphics.json', rules_profile=content['rules']['id'])
    content.update(package_id='unit-library', content_version='1.0.0')
    if needs_original(bundle):
        manifest['requires'] = 'chi-original-dos-1.03'
        manifest.pop('presentation', None)
    else:
        manifest['requires'] = 'none'
    person = copy.deepcopy(bundle['person']) if bundle['person'] else copy.deepcopy(adventure['people'][0])
    # A library character is not forced into Jason's start identity: the
    # preview project keeps a neutral lead and exposes the character separately.
    lead = copy.deepcopy(adventure['people'][0])
    lead.update(id='library:preview-pilot', identity='actor:0', name='Preview pilot')
    adventure.update(people=[lead] + ([person] if bundle['person'] else []), shops=[], encounters=[],
                     flags=[], events=[dict(id='library:end', op='end')])
    adventure['maps'] = [adventure['maps'][0]]
    adventure['maps'][0].update(overlays=[], entrances=[])
    adventure['start'] = dict(map=adventure['maps'][0]['id'], at=[24,38], event='library:end',
                              credits=100000, party=[dict(person=lead['id'], mech='none')])
    if bundle['person']:
        if person['identity'] in ('actor:0','chi:jason'):
            adventure['start']['party']=[dict(person=person['id'],mech='none')]
        else:adventure['start']['party'].append(dict(person=person['id'],mech='none'))
    else:adventure['start']['party'][0]['mech']=bundle['definition']
    # The engine's definition contract requires a nonempty roster/weapon set.
    # Neutral support definitions are preview scaffolding, never exported as
    # dependencies of the library's infantry blueprint.
    if not content['mechs']:
        for key in ('mechs', 'weapons', 'ammunition', 'presentations'):
            content[key] = copy.deepcopy(fallback[key])
        # Use one neutral mech; the CHI demo also contains owned vehicle art
        # which is not a dependency of an infantry blueprint.
        content['mechs'] = content['mechs'][:1]
        view = content['mechs'][0]['presentation']
        content['presentations'] = [p for p in content['presentations'] if p['id'] == view]
    presentation = copy.deepcopy(bundle.get('presentation')) or read_json(ROOT / 'examples/beacon-demo/presentation.json')
    files = {'project.json': manifest, 'content.json': content, 'adventure.json': adventure,
             'graphics.json': bundle['graphics'], 'presentation.json': presentation}
    if bundle.get('editing'):files['EDITOR.json']=bundle['editing']
    for name, text in bundle['provenance'].get('documents', {}).items():
        if name in SOURCE_FILES and isinstance(text,str): files[name] = text
    return files


def stage_preview(bundle, root):
    root.mkdir(parents=True, exist_ok=True)
    for name, value in preview_files(bundle).items():
        (root/name).write_bytes(value.encode('utf-8') if isinstance(value, str) else encoded(value))


class UnitLibrary:
    def __init__(self, root, validator):
        self.root = Path(root).resolve()
        self.validator = Path(validator).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, entry_id):
        return self.root / (hashlib.sha256(entry_id.encode()).hexdigest() + '.unit.json')

    def entries(self):
        values = []
        for path in sorted(self.root.glob('*.unit.json')):
            bundle = read_json(path)
            self.check_header(bundle)
            values.append(bundle)
        return sorted(values, key=lambda b: (b['name'].casefold(), b['entry_id']))

    @staticmethod
    def check_header(bundle):
        if not isinstance(bundle,dict):raise EditorError('A Unit Library entry must be a JSON object.')
        if (bundle.get('format') != FORMAT or bundle.get('schema_version') != 1
                or bundle.get('kind') not in KINDS or type(bundle.get('revision')) is not int or bundle['revision']<1
                or not re.fullmatch(r'[a-z][a-z0-9._-]*:[a-z][a-z0-9._-]*', bundle.get('entry_id', ''))):
            raise EditorError('Unsupported or invalid Unit Library entry.')
        for key in ('content','graphics','provenance'):
            if not isinstance(bundle.get(key),dict):raise EditorError(f'Library entry requires an object: {key}.')
        if not isinstance(bundle.get('name'),str) or not isinstance(bundle.get('definition'),str):
            raise EditorError('Library entry requires a name and definition ID.')
        if bundle['kind']=='Infantry' and not isinstance(bundle.get('person'),dict):
            raise EditorError('Infantry entry requires a character template.')
        if bundle.get('infantry_source', 'package') not in ('package', 'chi:infantry'):
            raise EditorError('Unsupported infantry sprite source.')

    def validate(self, bundle):
        self.check_header(bundle)
        unit = bundle['person'] if bundle['kind'] == 'Infantry' else bundle['content']['mechs'][0]
        if unit['id'] != bundle['definition']: raise EditorError('Library definition ID does not match its blueprint.')
        if bundle['kind'] != 'Infantry' and len(bundle['content']['mechs']) != 1:
            raise EditorError('A library entry must contain exactly one unit.')
        with tempfile.TemporaryDirectory(prefix='btp-library-validate-') as tmp:
            stage_preview(bundle, Path(tmp))
            run_validator(self.validator, Path(tmp))

    def save(self, bundle, expected=None, variant=False):
        value = copy.deepcopy(bundle)
        if variant:
            value['entry_id'] = 'library:variant-' + uuid.uuid4().hex[:16]
            value['definition'] = value['entry_id']
            unit=value['person'] if value['kind']=='Infantry' else value['content']['mechs'][0]
            unit['id']=value['definition']
            value['revision'] = 1
        path = self.path(value['entry_id'])
        if path.exists():
            current = read_json(path)
            if expected is None or current != expected:
                raise EditorError('This library entry already exists or changed in another window. Reload or save a variant.')
            value['revision'] = current['revision'] + 1
        elif expected is not None:
            raise EditorError('This library entry was removed in another window. Save a variant instead.')
        self.validate(value)
        # Validation invokes a subprocess; another window may have saved in
        # the meantime. Recheck before publishing the atomic replacement.
        if path.exists() and (expected is None or read_json(path)!=expected):
            raise EditorError('This library entry changed during validation. Reload it before saving.')
        ProjectDocument.atomic_file(path, encoded(value))
        return value

    def export_unit(self, document, identity, kind='Mechs', variant=False, expected=None):
        bundle = closure(document, identity, kind)
        if expected:
            bundle.update(entry_id=expected['entry_id'], revision=expected['revision'], provenance=expected['provenance'])
        return self.save(bundle, expected, variant)


def import_units(document, bundles, policy='keep', infantry_art=False):
    """Merge as one undo transaction; validate before changing the document.

    Replacements update the selected blueprint but preserve conflicting shared
    dependencies by assigning fresh IDs to incoming definitions. This prevents
    editing one imported weapon from changing unrelated project units.
    """
    if document.adventure is None: raise EditorError('Open an authored game to import units or infantry.')
    if policy not in ('keep', 'replace', 'variant'): raise EditorError('Unknown import policy.')
    content, adventure, art, manifest = map(copy.deepcopy,
        (document.content, document.adventure, document.art, document.manifest))
    imported = []
    editor=json.loads(document.metadata.get('EDITOR.json',b'{}'))
    source_records = json.loads(document.metadata.get('LIBRARY-SOURCES.json', b'[]'))
    for original in bundles:
        bundle = copy.deepcopy(original)
        UnitLibrary.check_header(bundle)
        unit = bundle['person'] if bundle['kind'] == 'Infantry' else bundle['content']['mechs'][0]
        target = adventure['people'] if bundle['kind'] == 'Infantry' else content['mechs']
        found = next((v for v in target if v['id'] == unit['id']), None)
        if found is not None and policy == 'keep': continue
        mapping = {}
        libraries = [('ammunition', content['ammunition']), ('weapons', content['weapons']),
                     ('equipment', content.setdefault('equipment', [])),
                     ('images', art['images']), ('presentations', content['presentations'])]
        incoming = {**bundle['content'], 'images': bundle['graphics']['images']}
        for key, values in libraries:
            for item in incoming.get(key, []):
                # Rewrite dependency references before checking equivalence.
                value = rewrite(item, mapping)
                existing = next((v for v in values if v['id'] == value['id']), None)
                if existing is not None and existing != value:
                    value['id'] = fresh_id(document.manifest['package_id'], values, key)
                    mapping[item['id']] = value['id']
                    existing = None
                if existing is None: values.append(value)
        # Independent legacy sprite sheets become owned RGBA images when
        # crossing projects. CHI references stay explicit external references.
        for presentation in bundle['content']['presentations']:
            if presentation['source'].startswith('package:walker'):
                from editor_units import indexed_sprite
                image = indexed_sprite(bundle['presentation'], 0 if presentation['source'].endswith('a') else 1)
                image.update(id=fresh_id(document.manifest['package_id'], art['images'], 'sprite'), name=bundle['name']+' sprite')
                art['images'].append(image)
                current = next(p for p in content['presentations'] if p['id'] == mapping.get(presentation['id'], presentation['id']))
                current.update(source='package:art', image=image['id'])
        value = rewrite(unit, mapping)
        if policy == 'variant': value['id'] = fresh_id(document.manifest['package_id'], target, 'unit' if bundle['kind'] != 'Infantry' else 'person')
        if needs_original(bundle) and manifest['requires'] == 'none':
            raise EditorError(f"{bundle['name']} needs CHI sprites. Choose a package sprite in the library first, or import into a CHI game.")
        if bundle['kind'] == 'Infantry':
            # Match the destination identity spelling and find a free actor
            # slot so imported recruits cannot alias an existing companion.
            slots = ('jason','rex','edward','russ','rick','zeke','possum','marco','rusty','hunter')
            replaced = found if policy!='variant' else None
            occupied = {int(p['identity'][-1]) if p['identity'].startswith('actor:') else slots.index(p['identity'][4:])
                        for p in target if p is not replaced}
            identity = next((i for i in range(1,10) if i not in occupied), None)
            if replaced: value['identity'] = found['identity']
            elif identity is None: raise EditorError('No free infantry actor identity (ten identities per game).')
            else: value['identity'] = f'actor:{identity}' if manifest['requires'] == 'none' else 'chi:'+slots[identity]
            if infantry_art:
                if bundle.get('infantry_source') == 'chi:infantry':
                    # Removing overrides restores the native CHI infantry
                    # animations. Original pixels remain external assets.
                    art['bindings'] = [b for b in art['bindings'] if b['slot'] not in ('npc', 'enemy')]
                for binding in bundle['graphics']['bindings']:
                    art['bindings'] = [b for b in art['bindings'] if b['slot'] != binding['slot']]
                    art['bindings'].append(rewrite(binding, mapping))
        if found is not None and policy != 'variant': target[target.index(found)] = value
        else: target.append(value)
        imported.append((bundle['kind'], value['id']))
        for image_id,layer_data in bundle.get('editing',{}).get('pixel_layers',{}).items():
            resolved=mapping.get(image_id,image_id)
            if any(i['id']==resolved for i in art['images']):editor.setdefault('pixel_layers',{})[resolved]=copy.deepcopy(layer_data)
        source_records = [s for s in source_records if s['definition'] != value['id']]
        source_records.append(dict(definition=value['id'], entry_id=bundle['entry_id'],
                                   revision=bundle['revision'], provenance=bundle['provenance']))
    if not imported: return []
    if art != document.art:
        if 'graphics' not in manifest and (document.root/'graphics.json').exists():
            raise EditorError('graphics.json already exists outside the project declarations.')
        manifest.setdefault('graphics', 'graphics.json')
    # Validate a detached candidate without touching shared history or disk.
    with tempfile.TemporaryDirectory(prefix='btp-library-import-') as tmp:
        directory = Path(tmp)
        document.stage(directory)
        for name, value in ((manifest['definitions'], content), (manifest['adventure'], adventure),
                            ('project.json', manifest)):
            (directory/name).write_bytes(encoded(value))
        if 'graphics' in manifest: (directory/manifest['graphics']).write_bytes(encoded(art))
        run_validator(document.validator, directory)
    metadata = copy.deepcopy(document.metadata)
    metadata['LIBRARY-SOURCES.json'] = encoded(source_records)
    if editor:metadata['EDITOR.json']=encoded(editor)
    document.replace_all(content, adventure, art, manifest, metadata)
    return imported


def fresh_id(prefix, values, kind):
    ids = {v['id'] for v in values}
    serial = 1
    while f'{prefix}:library-{kind}-{serial}' in ids: serial += 1
    return f'{prefix}:library-{kind}-{serial}'


def rewrite(value, mapping):
    if isinstance(value, dict): return {k: rewrite(v, mapping) for k, v in value.items()}
    if isinstance(value, list): return [rewrite(v, mapping) for v in value]
    return mapping.get(value, value) if isinstance(value, str) else value
