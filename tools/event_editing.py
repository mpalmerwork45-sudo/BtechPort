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
    if event.get('op')=='call':result.append(('event',event['event']))
    return result


def event_description(event,data=None):
    """Human-authored intent wins; otherwise summarize actual event fields."""
    note=(data or {}).get('event_descriptions',{}).get(event['id'])
    if note:return note
    if event.get('text'):return ' '.join(event['text'].split())
    op=event['op']
    if op=='end':return 'Return to exploration, or resume the current combat hook.'
    if op=='flag':return f"Set {event.get('flag','flag')} to {event.get('value',0)}."
    if op=='if':return f"Check whether {event.get('flag','flag')} equals {event.get('value',0)}."
    if op=='battle':return 'Fight '+event.get('encounter','the encounter')+'.'
    if op=='transfer':return f"Travel to {event.get('map','map')} at {event.get('at',[])}."
    if op=='reward':return f"Pay {event.get('credits',0):,} credits."
    if op=='lua':return 'Run script '+event.get('script','')+' and follow its chosen route.'
    if op=='recruit':return 'Recruit '+event.get('person','a party member')+'.'
    if op=='shop':return 'Open '+event.get('shop','the shop')+'.'
    if op=='reinforce':return 'Deploy reserve group '+event.get('group','')+'.'
    if op=='battle_end':return 'Resolve this battle as '+event.get('result','')+'.'
    if op=='objective':return f"Mark {event.get('objective','objective')} {event.get('state','')} .".replace(' .','.')
    if op=='variable':return f"{event.get('action','Set').capitalize()} {event.get('variable','variable')} by {event.get('value',0)}."
    if op=='check':return f"Test {event.get('match','all')} of {len(event.get('conditions',[]))} mission conditions."
    return op.replace('_',' ').capitalize()+': '+', '.join(f'{k}={v}' for k,v in event.items() if k not in ('id','op') and not isinstance(v,(dict,list)) and k not in dict(edges(event)))


def describe_event(document,identity,text):
    if not any(e['id']==identity for e in document.adventure['events']):raise EditorError('Choose an existing event.')
    text=text.strip()
    if len(text)>240:raise EditorError('Event descriptions use at most 240 characters.')
    data=editor_data(document);notes=data.setdefault('event_descriptions',{})
    if text:notes[identity]=text
    else:notes.pop(identity,None)
    with document.command('Describe event'):editor_commit(document,data)


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
