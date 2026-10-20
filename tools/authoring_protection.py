"""Authoring preservation rules, shared by CLI, reviews and the live editor.

Rules constrain generated batches. Manual editing remains available, and a
review can explicitly approve named exceptions without deleting the rules.
They are editor metadata, outside the runtime package/save identity.
"""
import copy
import json
import re

from authoring_contract import AuthoringError, check, obj, array, integer, TEXT, ID, enum
from editor_model import encoded

RULE_SCHEMA = obj(dict(
    id=dict(type='string',minLength=1,maxLength=80,pattern=r'^[a-zA-Z0-9._-]+$'),
    label=TEXT,kind=enum('object','fields','map_region'),path=TEXT,
    fields=array(TEXT,1,32),map=ID,rect=array(integer(0,64),4,4)),['id','label','kind'])


def data(document):
    return json.loads(document.metadata.get('EDITOR.json',b'{}'))


def rules(document):
    values=data(document).get('authoring_protection',[])
    check(values,array(RULE_SCHEMA,0,256))
    if len({v['id'] for v in values})!=len(values):
        raise AuthoringError('protection.invalid','Protection IDs must be unique.')
    for rule in values:check_rule_shape(rule)
    return values


def check_rule_shape(rule):
    """Validate saved policy even if a manually removed target is now absent."""
    region=rule['kind']=='map_region'
    needed={'map','rect'} if region else {'path'}|({'fields'} if rule['kind']=='fields' else set())
    if not needed.issubset(rule) or set(rule)-({'id','label','kind'}|needed):
        raise AuthoringError('protection.invalid','Preservation rule has missing or unrelated fields: '+rule['id'])
    if region and min(rule['rect'][2:])<1:
        raise AuthoringError('protection.invalid','A protected map rectangle must be nonempty.')


def value_at(document,path):
    """Resolve the same section.collection/stable-id paths used by scopes.

    Nested entrance IDs are also addressable: adventure.entrances/door:id.
    Field selectors below use JSON Pointer, so array indices are explicit.
    """
    if path.startswith('scripts/') or path.startswith('provenance/'):
        kind,identity=path.split('/',1)
        name=next((s['file'] for s in document.manifest.get('scripts',[]) if s['id']==identity),None) if kind=='scripts' else identity
        value=document.files().get(name) if name else None
        return dict(bytes=value.hex()) if value is not None else None
    head,separator,identity=path.partition('/')
    parts=head.split('.')
    if parts[0] not in ('manifest','content','adventure','art','editor'):
        raise AuthoringError('protection.invalid','Choose a declared document section: '+path)
    value=data(document) if parts[0]=='editor' else getattr(document,parts[0])
    if head=='adventure.entrances':
        value=[dict(door,map=scene['id']) for scene in (document.adventure or {}).get('maps',[]) for door in scene['entrances']]
    else:
        for part in parts[1:]:value=value.get(part) if isinstance(value,dict) else None
    if separator:
        if isinstance(value,list):value=next((v for v in value if isinstance(v,dict) and v.get('id')==identity),None)
        elif isinstance(value,dict):value=value.get(identity)
        else:value=None
    return copy.deepcopy(value)


def field_at(value,pointer):
    if not pointer.startswith('/'):pointer='/'+pointer
    for part in pointer[1:].split('/'):
        part=part.replace('~1','/').replace('~0','~')
        if isinstance(value,dict) and part in value:value=value[part]
        elif isinstance(value,list) and part.isdecimal() and int(part)<len(value):value=value[int(part)]
        else:return dict(present=False)
    return dict(present=True,value=value)


def region(document,rule):
    scene=next((m for m in (document.adventure or {}).get('maps',[]) if m['id']==rule['map']),None)
    if scene is None:return None
    x,y,w,h=rule['rect'];cells=[];used=set()
    for cy in range(y,y+h):
        for cx in range(x,x+w):
            stack=[]
            for layer in [dict(at=[0,0],rows=scene['rows']),*scene['overlays']]:
                ox,oy=layer['at'];xx,yy=cx-ox,cy-oy
                if 0<=yy<len(layer['rows']) and 0<=xx<len(layer['rows'][yy]):
                    tile=layer['rows'][yy][xx]
                    if tile!=' ':stack.append(tile);used.add(tile)
            cells.append(stack)
    from world_editing import token
    tiles=[v for v in document.adventure['tiles'] if token(v) in used]
    images={t['graphic'] for t in tiles if t['sheet']=='package:art'}
    # Protect the visible handwork as well as tile references: changing shared
    # artwork or terrain properties must not bypass a protected map region.
    return dict(cells=cells,tiles=tiles,images=[im for im in document.art['images'] if im['id'] in images],
                size=[len(scene['rows'][0]),len(scene['rows'])])


def validate_rule(document,rule):
    check(rule,RULE_SCHEMA)
    check_rule_shape(rule)
    if rule['kind']=='map_region':
        if set(rule)-{'id','label','kind','map','rect'} or 'map' not in rule or 'rect' not in rule:
            raise AuthoringError('protection.invalid','A map-region rule needs map and rect only.')
        scene=value_at(document,'adventure.maps/'+rule['map'])
        x,y,w,h=rule['rect']
        if not scene or min(w,h)<1 or x+w>len(scene['rows'][0]) or y+h>len(scene['rows']):
            raise AuthoringError('coordinate.bounds','Protect an existing, nonempty rectangle in map-tile coordinates.')
    else:
        allowed={'id','label','kind','path'}|({'fields'} if rule['kind']=='fields' else set())
        if set(rule)-allowed or 'path' not in rule or (rule['kind']=='fields' and not rule.get('fields')):
            raise AuthoringError('protection.invalid','Choose an object path and, for selected fields, field names or JSON pointers.')
        if rule['path'].startswith('editor.authoring_protection'):
            raise AuthoringError('protection.invalid','Protection settings are managed separately.')
        value=value_at(document,rule['path'])
        if value is None:raise AuthoringError('object.missing','Cannot protect a missing object: '+rule['path'])
        if rule['kind']=='fields' and any(not field_at(value,f)['present'] for f in rule['fields']):
            raise AuthoringError('object.missing','Every protected field must exist when the rule is created.')


def edit_rule(document,rule=None,remove=None):
    values=rules(document)
    if remove is not None:
        if not any(r['id']==remove for r in values):raise AuthoringError('object.missing','Unknown protection: '+remove)
        values=[r for r in values if r['id']!=remove]
    else:
        validate_rule(document,rule)
        values=[r for r in values if r['id']!=rule['id']]+[copy.deepcopy(rule)]
    if len(values)>256:raise AuthoringError('capacity.exceeded','At most 256 preservation rules are supported.')
    metadata=dict(document.metadata);notes=data(document);notes['authoring_protection']=values;metadata['EDITOR.json']=encoded(notes)
    with document.command('Edit authoring protection'):
        document.replace_all(document.content,document.adventure,document.art,document.manifest,metadata)


def conflicts(before,after):
    if rules(before)!=rules(after):
        raise AuthoringError('protection.policy_changed','Generated batches cannot change preservation rules. Use the protection editor explicitly.')
    result=[]
    for rule in rules(before):
        if rule['kind']=='map_region':left,right=region(before,rule),region(after,rule)
        else:
            left,right=value_at(before,rule['path']),value_at(after,rule['path'])
            if rule['kind']=='fields':
                left={f:field_at(left,f) for f in rule['fields']};right={f:field_at(right,f) for f in rule['fields']}
        if left!=right:
            result.append(dict(code='protection.conflict',severity='error',rule=rule['id'],label=rule['label'],
                message='This batch changes protected content: '+rule['label'],path=rule.get('path'),
                map=rule.get('map'),rect=rule.get('rect'),fields=rule.get('fields',[])))
    return result


def enforce(before,after,overrides=()):
    known={r['id'] for r in rules(before)}
    if set(overrides)-known:raise AuthoringError('protection.invalid','An override names an unknown protection rule.')
    blocked=[c for c in conflicts(before,after) if c['rule'] not in overrides]
    if blocked:
        error=AuthoringError('protection.conflict','Protected content would change: '+', '.join(c['label'] for c in blocked))
        error.diagnostic['conflicts']=blocked
        raise error


def displaced_details(before,after):
    old=data(before).get('map_constructions',[]);new={v['id']:v for v in data(after).get('map_constructions',[])}
    lost=[]
    for building in old:
        remaining={(x,y):tile for x,y,tile in new.get(building['id'],{}).get('details',[])}
        for x,y,tile in building.get('details',[]):
            if remaining.get((x,y))!=tile:
                lost.append(dict(construction=building['id'],map=building['map'],at=[x,y],tile=tile))
    return lost
