"""Versioned authoring descriptors; no GUI or model dependency.

Descriptors are JSON Schemas using a deliberately small structural subset.
The shared C loader remains authoritative for game semantics and references.
"""
import json
import re
from editor_model import EditorError

API_VERSION = 1
MAX_REQUEST_BYTES = 16 * 1024 * 1024


class AuthoringError(EditorError):
    def __init__(self, code, message, path='$', object_id=None, location=None):
        super().__init__(message)
        self.diagnostic = dict(code=code, severity='error', message=message,
                               field_path=path, object_id=object_id, location=location)


def diagnostic(error):
    if isinstance(error, AuthoringError): return error.diagnostic
    # C loader messages already carry a JSON path with stable object IDs.
    message = str(error)
    match = re.search(r': (\$[^\n]*?): (.*)', message)
    path = match[1] if match else '$'
    identity = re.search(r'\[([a-z][a-z0-9._-]*:[a-z][a-z0-9._-]*)\]', path)
    code = ('revision.conflict' if 'outside this editor' in message else
            'project.busy' if 'another process' in message else
            'recovery.required' if 'Interrupted save' in message else 'content.invalid')
    return dict(code=code, severity='error', message=message, field_path=path,
                object_id=identity[1] if identity else None, location=None)


def read_json(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result: raise AuthoringError('request.invalid', f'Duplicate JSON field: {key}')
            result[key] = value
        return result
    try:
        if hasattr(path, 'read'): data = path.read(MAX_REQUEST_BYTES+1)
        else:
            with path.open('rb') as stream: data=stream.read(MAX_REQUEST_BYTES+1)
        if len(data) > MAX_REQUEST_BYTES:
            raise AuthoringError('request.too_large', 'JSON input exceeds 16 MiB.')
        return json.loads(data, object_pairs_hook=pairs,
                          parse_constant=lambda v: (_ for _ in ()).throw(ValueError('Non-finite number: '+v)))
    except (ValueError, RecursionError) as exc:
        raise AuthoringError('request.invalid', f'Cannot read JSON: {exc}') from exc


def check(value, schema, path='$'):
    """Validate the documented structural subset (also used for conformance tests)."""
    def fail(message): raise AuthoringError('request.invalid', message, path)
    if schema is True: return
    if schema is False: fail('This value is not permitted.')
    if 'const' in schema and (value != schema['const'] or type(value) is not type(schema['const'])): fail('Unexpected constant.')
    if 'enum' in schema and value not in schema['enum']: fail('Expected one of: '+', '.join(map(str, schema['enum'])))
    kind = schema.get('type')
    types = dict(object=dict, array=list, string=str, integer=int, boolean=bool, number=(int,float), null=type(None))
    if kind and (not isinstance(value, types[kind]) or (kind in ('integer','number') and isinstance(value,bool))): fail('Expected '+kind+'.')
    if isinstance(value, dict):
        for key in schema.get('required', []):
            if key not in value: raise AuthoringError('request.invalid', 'Missing required field: '+key, path+'.'+key)
        props = schema.get('properties', {})
        for key, item in value.items():
            if key in props: check(item, props[key], path+'.'+key)
            elif schema.get('additionalProperties') is False:
                raise AuthoringError('request.invalid', 'Unknown field: '+key, path+'.'+key)
            elif isinstance(schema.get('additionalProperties'), dict): check(item, schema['additionalProperties'], path+'.'+key)
    if isinstance(value, list):
        if len(value) < schema.get('minItems',0) or len(value) > schema.get('maxItems',10**9): fail('Array length is outside the supported range.')
        for index, item in enumerate(value):
            if 'items' in schema: check(item, schema['items'], f'{path}[{index}]')
    if isinstance(value, str):
        if len(value) < schema.get('minLength',0) or len(value) > schema.get('maxLength',10**9): fail('Text length is outside the supported range.')
        if 'pattern' in schema and not re.search(schema['pattern'], value): fail('Text does not match the required pattern.')
    if type(value) in (int,float):
        if value < schema.get('minimum',float('-inf')) or value > schema.get('maximum',float('inf')): fail('Number is outside the supported range.')
    for branch in schema.get('allOf',[]): check(value,branch,path)
    def matches(branch):
        try: check(value,branch,path); return True
        except AuthoringError: return False
    for key in ('oneOf','anyOf'):
        if key in schema:
            count=sum(matches(b) for b in schema[key])
            if not count or (key=='oneOf' and count!=1): fail('Value does not match a supported schema alternative.')
    if 'not' in schema and matches(schema['not']): fail('This combination is not permitted.')
    if 'if' in schema:
        branch='then' if matches(schema['if']) else 'else'
        if branch in schema: check(value,schema[branch],path)


def obj(props, required=()):
    return dict(type='object', properties=props, required=list(required), additionalProperties=False)


def integer(low=0, high=65535): return dict(type='integer',minimum=low,maximum=high)
def array(item, low=0, high=4096): return dict(type='array',items=item,minItems=low,maxItems=high)
def enum(*values): return dict(enum=list(values))
TEXT = dict(type='string', minLength=1, maxLength=1024)
ID = dict(type='string', maxLength=63, pattern=r'^[a-z][a-z0-9._-]*:[a-z][a-z0-9._-]*$')
POINT = array(integer(0,1023),2,2)
RECORD = dict(type='object')
COLLECTIONS = {
    'maps':'adventure','tiles':'adventure','jigsaws':'adventure','people':'adventure',
    'shops':'adventure','encounters':'adventure','events':'adventure','objectives':'adventure',
    'variables':'adventure','regions':'adventure',
    'mechs':'content','weapons':'content','equipment':'content','ammunition':'content',
    'presentations':'content','images':'art',
}
OPERATIONS = {}


def operation(name, description, properties, required, writes, example):
    OPERATIONS[name] = dict(description=description, writes=writes,
        schema=obj(dict(op={'const':name},**properties), ['op',*required]), example=dict(op=name,**example))


operation('object.put','Create or replace one explicit definition. Supply its complete format-schema record.',
          dict(collection=enum(*COLLECTIONS),value=RECORD,mode=enum('create','replace')),['collection','value'],['selected collection'],
          dict(collection='events',value={'id':'demo:end','op':'end'},mode='create'))
operation('object.patch','Update selected top-level fields; preserve every other field of the object.',
          dict(collection=enum(*COLLECTIONS),id=ID,changes=RECORD),['collection','id','changes'],['selected object'],
          dict(collection='events',id='demo:briefing',changes={'text':'Defend the relay.'}))
operation('object.remove','Remove one object; complete batch must resolve all runtime and metadata references.',
          dict(collection=enum(*COLLECTIONS),id=ID),['collection','id'],['selected object'],dict(collection='events',id='demo:unused'))
operation('project.configure','Change project title, version or rules; keep definition identity in sync.',
          dict(changes=obj(dict(title=TEXT,content_version=TEXT,rules_profile=enum('chi:legacy-v1','chi:updated-lrm-v1')))),['changes'],['manifest','content'],dict(changes={'title':'Relay Contract'}))
operation('start.set','Patch the starting location, party, credits or briefing; movement coordinates.',
          dict(changes=RECORD),['changes'],['adventure.start'],dict(changes={'event':'demo:briefing'}))
operation('flags.add','Declare persistent mission flags, without duplicating existing IDs.',dict(ids=array(ID,1,64)),['ids'],['adventure.flags'],dict(ids=['demo:complete']))
operation('map.create','Create a local map filled with a named tile; dimensions and origin in tiles.',
          dict(id=ID,name=TEXT,width=integer(16,64),height=integer(16,64),tile=ID,origin=POINT),['id','name','width','height','tile'],['adventure.maps'],dict(id='demo:town',name='Relay town',width=32,height=24,tile='demo:grass'))
operation('map.paint','Paint visible surface (-1), base (0), or overlay (1+), preserving construction details.',
          dict(map=ID,tile=ID,start=POINT,end=POINT,tool=enum('Paint','Rectangle','Fill'),layer=integer(-1,32)),['map','tile','start'],['adventure.maps','editor.map_constructions'],dict(map='demo:town',tile='demo:road',start=[2,3],end=[9,3]))
operation('entrance.put','Create/replace a named entrance; at uses movement half-tiles, not map tiles.',
          dict(map=ID,value=RECORD,mode=enum('create','replace')),['map','value'],['adventure.maps'],dict(map='demo:town',value={'id':'demo:office','name':'Contract office','at':[18,20],'event':'demo:briefing'}))
operation('marker.move','Move a start, entrance, NPC, party or enemy through the same editor rules.',
          dict(map=ID,kind=enum('start','entrance','npc','party','enemy'),id=TEXT,at=POINT,enemy_index=integer(0,11)),['map','kind','id','at'],['adventure.maps','adventure.start','adventure.encounters'],dict(map='demo:town',kind='entrance',id='demo:office',at=[20,20]))
operation('event.connect','Connect a declared branch: next/win/loss/flee/choice N/route N, etc.',
          dict(source=ID,branch=TEXT,target=ID),['source','branch','target'],['adventure.events'],dict(source='demo:briefing',branch='next',target='demo:end'))
operation('world.create','Create a planet with the original world dimensions by default.',
          dict(name=TEXT,width=integer(8,128),height=integer(8,128)),['name'],['adventure.world','adventure.worlds','adventure.jigsaws'],dict(name='New Avalon'))
operation('world.paint','Paint a rectangle of world pieces with one jigsaw. Coordinates are jigsaw cells.',
          dict(world=ID,jigsaw=ID,start=POINT,end=POINT),['world','jigsaw','start'],['adventure.world','adventure.worlds'],dict(world='demo:world',jigsaw='demo:plain',start=[0,0],end=[3,3]))
operation('world.generate','Fill using explicit seed and weights; optionally require matching terrain edges.',
          dict(world=ID,seed=integer(0,4294967295),weights=dict(type='object',additionalProperties=integer(1,1000)),match_edges=dict(type='boolean')),['world','seed','weights'],['adventure.world','adventure.worlds','editor.world_generation'],dict(world='demo:world',seed=42,weights={'demo:plain':1}))
operation('world.patch','Paint an explicit world-tile rectangle, excluding city overlays.',
          dict(world=ID,at=POINT,rows=array(array(ID,1,64),1,64)),['world','at','rows'],['adventure.world','adventure.worlds'],dict(world='demo:world',at=[5,5],rows=[['demo:grass']]))
operation('city.place','Place/remove a local map over a planet; at is a world-tile coordinate.',
          dict(world=ID,map=ID,at=POINT,enabled=dict(type='boolean')),['world','map'],['adventure.maps','adventure.world','adventure.worlds'],dict(world='demo:world',map='demo:town',at=[64,64]))
operation('construction.style','Define building/wall/road parts and demo footprint; missing parts receive editable art.',
          dict(value=RECORD),['value'],['editor.construction_sets','editor.tile_names','art.images','adventure.tiles'],dict(value={'id':'demo:building','name':'Depot','kind':'Building','footprint':[[1,1],[1,1]],'parts':{}}))
operation('construction.draw','Draw or extend a building/wall footprint, retaining hand-painted details.',
          dict(map=ID,style=ID,id=ID,start=POINT,end=POINT,shape=enum('Brush','Rectangle','Courtyard','Erase'),stories=integer(1,32),width=integer(1,8),erase=dict(type='boolean')),['map','style','start','stories'],['adventure.maps','adventure.tiles','art.images','editor.map_constructions','editor.construction_sets','editor.tile_names'],dict(map='demo:town',style='demo:building',start=[4,4],end=[7,7],shape='Courtyard',stories=2))
operation('road.draw','Draw connected roads using the editor junction generator.',
          dict(map=ID,style=ID,start=POINT,end=POINT,width=integer(1,8),layer=integer(-1,32),erase=dict(type='boolean')),['map','style','start','end'],['adventure.maps','adventure.tiles','art.images','editor.construction_sets','editor.tile_names','editor.map_constructions'],dict(map='demo:town',style='demo:road',start=[3,10],end=[18,10]))
operation('pattern.capture','Store a named tile rectangle in the project Pattern Library.',
          dict(map=ID,rect=array(integer(0,63),4,4),name=TEXT),['map','rect','name'],['editor.map_patterns'],dict(map='demo:town',rect=[3,3,8,8],name='Checkpoint'))
operation('pattern.place','Place a stored pattern, preserving manual construction details.',
          dict(map=ID,id=ID,at=POINT,layer=integer(-1,32)),['map','id','at'],['adventure.maps','editor.map_constructions'],dict(map='demo:town',id='demo:pattern-1',at=[12,4]))
operation('unit.import','Import a unit bundle and its dependency closure; path relative to the request file.',
          dict(file=TEXT,policy=enum('keep','replace','variant'),infantry_art=dict(type='boolean')),['file'],['content','art','adventure.people','editor','provenance'],dict(file='units/locust.json'))
operation('art.import','Import an image/sprite sheet through the existing converter; explicit frame dimensions.',
          dict(file=TEXT,kind=enum('tile','sprite','icon','screen'),frame_width=integer(1,320),frame_height=integer(1,200),id=ID,name=TEXT),['file','kind'],['art.images'],dict(file='art/relay.png',kind='screen',id='demo:relay'))
operation('art.clone','Clone one owned image and its animation tracks into an independent editable image.',
          dict(source=ID,id=ID,name=TEXT),['source','id'],['art.images'],dict(source='demo:grass',id='demo:grass-dark'))
operation('art.bind','Bind an owned sprite to a supported runtime actor slot.',
          dict(slot=enum('player','npc','enemy','locust','stinger','wreck'),image=ID),['slot','image'],['art.bindings'],dict(slot='player',image='demo:pilot'))
operation('script.import','Import a bounded Lua source and declare its ID; events still declare allowed continuations.',
          dict(id=ID,file=TEXT,target=dict(type='string',pattern=r'^[a-zA-Z0-9_-]+\.lua$'),mode=enum('create','replace')),
          ['id','file','target'],['manifest.scripts','scripts'],dict(id='demo:contract',file='scripts/contract.lua',target='contract.lua'))
operation('asset.annotate','Describe an asset for both human pickers and automated discovery; metadata does not change gameplay.',
          dict(id=ID,changes=obj(dict(name=dict(type='string',maxLength=120),description=dict(type='string',maxLength=2048),
              tags=array(dict(type='string',minLength=1,maxLength=64),0,32),
              edges=obj({s:dict(type='string',maxLength=64) for s in ('north','east','south','west')})))),
          ['id','changes'],['editor.catalogue'],dict(id='demo:grass',changes={'description':'Open grassland','tags':['grassland','outdoors']}))

GROUP_SCHEMA=obj(dict(id=dict(type='string',minLength=1,maxLength=64,pattern=r'^[a-zA-Z0-9._-]+$'),label=TEXT,
    operations=array(integer(0,511),1,512),requires=array(TEXT,0,64)),['id','label','operations'])
BATCH_SCHEMA = obj(dict(api_version={'const':API_VERSION},request_id=dict(type='string',minLength=1,maxLength=96,pattern=r'^[a-zA-Z0-9._-]+$'),
    project_id=dict(type='string',minLength=1,maxLength=31),expected_revision=dict(anyOf=[dict(type='string',pattern='^[0-9a-f]{64}$'),{'const':'new'}]),
    label=dict(type='string',minLength=1,maxLength=160),scope=array(TEXT,1,64),
    brief=dict(type='string',maxLength=4096),constraints=array(TEXT,0,32),groups=array(GROUP_SCHEMA,1,64),
    operations=array(dict(oneOf=[d['schema'] for d in OPERATIONS.values()]),1,512)),
    ['api_version','request_id','project_id','expected_revision','label','scope','operations'])


def check_batch(request):
    # Report a bad operation at its exact field, rather than a generic oneOf failure.
    schema=dict(BATCH_SCHEMA,properties=dict(BATCH_SCHEMA['properties'],operations=array(RECORD,1,512)))
    check(request,schema)
    for i, op in enumerate(request['operations']):
        if op.get('op') not in OPERATIONS:
            raise AuthoringError('operation.unsupported','Unsupported operation: '+str(op.get('op')),f'$.operations[{i}].op')
        check(op,OPERATIONS[op['op']]['schema'],f'$.operations[{i}]')
    groups=request.get('groups',[])
    if groups:
        identities={g['id'] for g in groups};indices=[i for g in groups for i in g['operations']]
        if len(identities)!=len(groups) or sorted(indices)!=list(range(len(request['operations']))):
            raise AuthoringError('group.invalid','Groups need unique IDs and must assign each operation exactly once.')
        for group in groups:
            if set(group.get('requires',[]))-identities or group['id'] in group.get('requires',[]):
                raise AuthoringError('group.invalid','Group dependencies must name other existing groups.')
