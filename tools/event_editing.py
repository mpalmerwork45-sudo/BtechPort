"""Headless event/metadata operations shared by the editor and authoring CLI."""
import copy
import json
from editor_model import EditorError, encoded
from world_editing import identity


def editor_data(document):
    return json.loads(document.metadata.get('EDITOR.json', b'{}'))


def editor_commit(document, data):
    metadata = dict(document.metadata)
    metadata['EDITOR.json'] = encoded(data)
    document.replace_all(document.content, document.adventure, document.art, document.manifest, metadata)


def edges(event):
    result = [(key, event[key]) for key in
              ('next', 'failure', 'unchanged', 'then', 'else', 'cancel', 'win', 'loss', 'flee') if key in event]
    result.extend((f'choice {i+1}', o['next']) for i, o in enumerate(event.get('options', [])))
    result.extend((f'route {i+1}', v) for i, v in enumerate(event.get('routes', [])))
    return result


def connect(document, source, branch, target):
    a = copy.deepcopy(document.adventure)
    events = {e['id']: e for e in a['events']}
    if source not in events or target not in events:
        raise EditorError('Choose existing source and destination events.')
    e = events[source]
    if branch not in dict(edges(e)):
        raise EditorError('Choose an existing output branch.')
    if branch.startswith('choice '):
        e['options'][int(branch.split()[1])-1]['next'] = target
    elif branch.startswith('route '):
        e['routes'][int(branch.split()[1])-1] = target
    else:
        e[branch] = target
    document.replace_adventure(a)


def dialogue_branch(document, source, label, text):
    a = copy.deepcopy(document.adventure)
    e = next(e for e in a['events'] if e['id'] == source)
    if e['op'] != 'choice' or len(e['options']) >= 5:
        raise EditorError('Choose a choice event with fewer than five options.')
    if not label or len(label) > 24:
        raise EditorError('A choice label uses 1..24 characters.')
    new = identity(document.manifest['package_id'], a['events'], 'dialogue')
    a['events'].append(dict(id=new, op='say', text=text, next=source))
    e['options'].append(dict(label=label, next=new))
    document.replace_adventure(a)
    return new
