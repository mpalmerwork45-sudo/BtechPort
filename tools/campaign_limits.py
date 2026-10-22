"""Explicit campaign upgrades shared by human and automated authoring."""
import copy
from editor_model import EditorError

EXPANDED = dict(maps=64, encounters=64, events=1024, objectives=128, variables=128)
LEGACY = dict(maps=16, encounters=16, events=256, objectives=32, variables=32)


def limits(adventure):
    return EXPANDED if adventure.get('schema_version', 1) >= 3 else LEGACY


def upgrade_campaign(document):
    from authoring_inspect import capabilities
    from world_editing import upgrade
    if document.adventure is None:
        raise EditorError('This project has no authored campaign to upgrade.')
    if document.adventure['schema_version'] >= 3:
        return
    if 'btp-adventure-v3' not in capabilities(document.validator)['runtime']['formats']:
        raise EditorError('Campaign v3 requires runtime 0.2.0 or later. Rebuild or select a newer validator.')
    adventure = copy.deepcopy(document.adventure)
    upgrade(adventure)
    adventure.update(format='btp-adventure-v3', schema_version=3)
    # This is an ordinary undoable content edit. No save is relabelled or
    # silently migrated: the strict package fingerprint changes on purpose.
    document.replace_adventure(adventure)


def schema():
    import json
    from pathlib import Path
    value = json.loads((Path(__file__).resolve().parents[1]/'schemas/adventure-v2.schema.json').read_bytes())
    value['$id'] = 'https://btechport.local/schemas/adventure-v3.schema.json'
    value['title'] = 'BtechPort authored campaign v3 (runtime 0.2.0+)'
    value['properties']['format']['const'] = 'btp-adventure-v3'
    value['properties']['schema_version']['const'] = 3
    for key, maximum in EXPANDED.items():
        value['properties'][key]['maxItems'] = maximum
    return value
