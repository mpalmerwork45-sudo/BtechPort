"""Editable native CHI maps/generator inputs, shared by GUI and headless authors.

The native adapter reads this document directly. It is never a preview-only
bake, and it does not turn on the separate authored event interpreter. Original
binary resources remain immutable baselines within the private project.
"""
from __future__ import annotations
import copy
import json
import struct
from editor_model import EditorError, encoded

FILE='chi-spatial.json'
FORMAT='btp-chi-spatial-v1'
NAMES=('Citadel','Starport','Map 3','Map 4','Map 5','Map 6','Map 7','Map 8','Map 9','Map 10',
       'Ruined Citadel',"Inventor's island",'Cache island','Cache corridors','Cache map room')
BANKS=('chi:land','chi:destroyed','chi:cache','chi:maproom')


def tile_id(bank,index):return bank+'-'+str(index)


def decode_map(raw,slot):
    width,height=(32,24) if slot==15 else raw[3:5]
    payload=raw if slot==15 else raw[541:]
    cells=[[payload[((y//8)*(width//8)+x//8)*64+(y%8)*8+x%8] for x in range(width)] for y in range(height)]
    raw=bytes(541) if slot==15 else raw
    xs=struct.unpack_from('<16H',raw,389);ys=struct.unpack_from('<16H',raw,421)
    bank=BANKS[1 if slot==11 else 2 if slot==14 else 3 if slot==15 else 0]
    identity=f'chi:map-{slot:02}'
    def label(data):return ''.join(chr(c) if 32<=c<127 else '?' for c in data.split(b'\0')[0])
    doors=[]
    for i,(x,y) in enumerate(zip(xs,ys)):
        data=raw[133+16*i:149+16*i]
        doors.append(dict(id=identity+f'-door-{i:02}',slot=i,name=label(data),label_bytes=list(data),
            half=[x&127,y&127],active=int(bool(x and y)),packed=[x,y],room=raw[517+i]))
    actors=[]
    for i in range(8):
        data=raw[5+16*i:21+16*i]
        actors.append(dict(id=identity+f'-npc-{i}',slot=i,name=label(data),label_bytes=list(data),route=raw[533+i]))
    return dict(id=identity,slot=slot,name=NAMES[slot-1],width=width,height=height,
        origin=[(xs[0]>>8)*64,(ys[0]>>12)*64],rows=[[tile_id(bank,c) for c in row] for row in cells],
        overlays=[],entrances=doors,npcs=actors)


def extract(files):
    """Convert the checked private byte snapshot, without rereading DOS files."""
    tiles=[dict(id=tile_id(bank,i),name=f'{bank[4:].title()} {i}',sheet=bank,graphic=i,rule=i)
           for bank in BANKS for i in range(250)]
    maps=[decode_map(files['chi/MAP'+str(i)+'.MTP'],i) for i in range(1,16)]
    raw=files['chi/world-data.bin']
    if raw[:4]!=b'BTW3' or len(raw)!=1864:raise EditorError('Reimport CHI to obtain the supported native world inputs.')
    pieces=[]
    for i in range(17):
        source=raw[424+64*i:488+64*i]
        pieces.append(dict(id=f'chi:jigsaw-{i:02}',name=f'Terrain join {i:02}' if i<16 else 'Level 16 terrain',
            rows=[[tile_id('chi:land',c) for c in source[y*8:y*8+8]] for y in range(8)]))
    world=dict(id='chi:world',name='CHI world',width=1024,height=1024,seed=struct.unpack_from('<I',raw,12)[0],
        coarse=list(raw[88:424]),flips=list(raw[1512:1608]),mini_colors=list(raw[1608:1864]),
        jigsaws=pieces,joins=[p['id'] for p in pieces])
    return dict(format=FORMAT,schema_version=1,tiles=tiles,maps=maps,world=world,start=dict(map='chi:map-01',half=[69,25]),
        land=[tile_id('chi:land',i) for i in range(250)])


def data(document):
    if document.manifest.get('requires')!='chi-local-dos-1.03':raise EditorError('Open an imported CHI campaign first.')
    name=document.manifest.get('chi_spatial')
    if not name:raise EditorError('Enable map editing on this C2 import with Project > CHI maps, then Save.')
    if document.adventure and 'chi_native' in document.adventure:
        return from_projection(document.adventure)
    return json.loads(document.metadata[name])


def projection(value):
    """Use the established map/construction/library model as an editing view.

    This projection is never written as an authored adventure or run by its
    event VM. Save serializes it to the native spatial document. Each native
    record stays in chi_native so padding, half-step parity and fixed slots
    survive ordinary tile/structure operations without loss.
    """
    result=dict(format='btp-adventure-v2',schema_version=2,chi_native=copy.deepcopy(value),
        tiles=[],maps=[],people=[],shops=[],encounters=[],flags=[],jigsaws=copy.deepcopy(value['world']['jigsaws']),events=[dict(id=f'chi:building-{i}',op='end') for i in range(26)],
        start=dict(map=value.get('start',{}).get('map',value['maps'][0]['id']),at=list(value.get('start',{}).get('half',[69,25])),event='chi:building-0',credits=35,party=[]))
    for tile in value['tiles']:
        rule=tile['rule'];terrain=projection_terrain(rule,tile.get('water',2))
        result['tiles'].append(dict(id=tile['id'],sheet=tile['sheet'],graphic=tile['graphic'],terrain=terrain,
            mini_color=tile.get('mini_color',value['world']['mini_colors'][rule])))
    for m in value['maps']:
        doors=[dict(id=d['id'],name=d['name'] or 'Entrance '+str(d['slot']),at=[d['half'][0]//2,d['half'][1]//2],
                    event='chi:building-'+str(d['room'] if d['room']<26 else 0)) for d in m['entrances'] if d['active']]
        result['maps'].append(dict(id=m['id'],name=m['name'],origin=list(m['origin']),rows=copy.deepcopy(m['rows']),overlays=copy.deepcopy(m['overlays']),
            entrances=doors,npcs=[],encounters=[]))
    return result


def from_projection(adventure):
    value=copy.deepcopy(adventure['chi_native']);old={t['id']:t for t in value['tiles']};tiles=[]
    expected={'format','schema_version','chi_native','tiles','maps','people','shops','encounters','flags','jigsaws','events','start'}
    if set(adventure)-expected or any(adventure[k] for k in ('people','shops','encounters','flags')) or adventure['events']!=[dict(id=f'chi:building-{i}',op='end') for i in range(26)]:
        raise EditorError('Native CHI keeps its BLD story interpreter. Authored events, people, encounters and mission state require the C4 bridge; these edits were not published.')
    if adventure['start'].get('party') or adventure['start'].get('credits')!=35 or adventure['start'].get('event')!='chi:building-0':
        raise EditorError('C3 exposes the native starting position. Starting party/economy/story changes belong to C4.')
    value['world']['jigsaws']=copy.deepcopy(adventure.get('jigsaws',value['world']['jigsaws']))
    start=dict(map=adventure['start']['map'],half=adventure['start']['at'])
    if 'start' in value or start!=dict(map=value['maps'][0]['id'],half=[69,25]):value['start']=copy.deepcopy(start)
    for t in adventure['tiles']:
        if set(t)-{'id','sheet','graphic','terrain','mini_color'}:raise EditorError('Use chi.update for native rule/water fields; unknown projected tile properties are not accepted.')
        native=old.get(t['id']);rule=native['rule'] if native else {'clear':0,'rough':31,'water':15,'woods':47,'wall':85}[t['terrain']]
        if native:
            old_terrain=projection_terrain(rule,native.get('water',2))
            if t['terrain']!=old_terrain:rule={'clear':0,'rough':31,'water':15,'woods':47,'wall':85}[t['terrain']]
        tiles.append(dict(id=t['id'],name=native['name'] if native else t['id'].split(':')[-1],sheet=t['sheet'],graphic=t['graphic'],rule=rule))
        water=native.get('water',2) if native else (1 if t['terrain']=='water' else 0)
        if native and t['terrain']!=projection_terrain(native['rule'],native.get('water',2)):water=1 if t['terrain']=='water' else 0
        if water!=2 or (native and 'water' in native):tiles[-1]['water']=water
        if not native or 'mini_color' in native or t['mini_color']!=value['world']['mini_colors'][native['rule']]:tiles[-1]['mini_color']=t['mini_color']
    value['tiles']=tiles
    if {m['id'] for m in value['maps']}!={m['id'] for m in adventure['maps']}:
        raise EditorError('Native CHI has 15 fixed map slots. Rename/move a map or clone into another slot; create unrestricted maps in an authored game.')
    for scene in adventure['maps']:
        if set(scene)-{'id','name','origin','rows','overlays','entrances','npcs','encounters'}:raise EditorError('Unknown native map property; use the native map/generator fields.')
        m=find(value['maps'],scene['id']);m.update(name=scene['name'],origin=copy.deepcopy(scene['origin']),rows=copy.deepcopy(scene['rows']),overlays=copy.deepcopy(scene['overlays']),
            width=len(scene['rows'][0]),height=len(scene['rows']))
        if scene.get('npcs') or scene.get('encounters'):raise EditorError('Use CHI NPC routes for town walkers; authored encounters require the C4 story bridge.')
        active={d['id']:d for d in scene['entrances']}
        for d in m['entrances']:
            shown=active.pop(d['id'],None)
            if shown is None:d.update(active=0,packed=[0,0]);continue
            old_at=[d['half'][0]//2,d['half'][1]//2]
            if shown['at']!=old_at:d['half']=[2*shown['at'][0]+d['half'][0]%2,2*shown['at'][1]+d['half'][1]%2]
            if shown['name']!=(d['name'] or 'Entrance '+str(d['slot'])):d['name']=shown['name']
            if shown['event'].startswith('chi:building-'):
                if shown['event']!='chi:building-'+str(d['room'] if d['room']<26 else 0):d['room']=int(shown['event'].rsplit('-',1)[1])
            else:raise EditorError('CHI entrances currently reference existing BLD buildings; new story programs belong to C4.')
        for shown in active.values():
            door=next((d for d in m['entrances'] if not d['active']),None)
            if door is None:raise EditorError('This map already uses all 16 native entrance slots.')
            # A new entrance takes a vacant slot and keeps the authored stable
            # ID, so later drags and headless requests refer to the same door.
            door.update(id=shown['id'],name=shown['name'],active=1,half=[2*shown['at'][0],2*shown['at'][1]],
                        room=int(shown['event'].rsplit('-',1)[1]))
    return value


def projection_terrain(rule,water=2):
    return 'wall' if rule>=85 else 'woods' if 32<=rule<64 else 'water' if rule<16 and water else 'clear'


def enable(document):
    """Upgrade an old C2 project in one reversible, validated shared command."""
    if document.manifest.get('chi_spatial'):return
    with document.command('Enable CHI map editing'):
        value=extract(document.files());manifest=copy.deepcopy(document.manifest);metadata=dict(document.metadata)
        manifest['chi_spatial']=FILE;metadata[FILE]=encoded(value)
        document.replace_all(document.content,projection(value),document.art,manifest,metadata)
        document.validate()


def change(document,operation,label='Edit CHI maps'):
    """GUI, CLI and libraries publish exactly the same candidate and validation."""
    with document.command(label):
        value=data(document);result=operation(value)
        metadata=dict(document.metadata);metadata[document.manifest['chi_spatial']]=encoded(value)
        document.replace_all(document.content,projection(value),document.art,document.manifest,metadata)
        document.validate()
    return result


def find(values,identity):
    matches=[v for v in values if v['id']==identity]
    if len(matches)!=1:raise EditorError('Expected one CHI object: '+str(identity))
    return matches[0]


def paint(value,identity,points,tile,layer=-1):
    from world_editing import paint as paint_cell
    find(value['tiles'],tile)
    scene=find(value['maps'],identity)
    for x,y in points:
        if not 0<=x<scene['width'] or not 0<=y<scene['height']:raise EditorError('All cells must fit the map.')
        paint_cell(scene,layer,x,y,tile)


def move_town(value,identity,x,y):
    if x%64 or y%64 or not 0<=x<=960 or not 0<=y<=960:raise EditorError('Native towns use 64-tile sector origins, from 0 to 960.')
    scene=find(value['maps'],identity)
    if scene['slot']>=14:raise EditorError('Cache interior maps use room coordinates, not world placements.')
    # Keep the Citadel's alternate state attached to the same physical town.
    targets=[m for m in value['maps'] if m['slot'] in (1,11)] if scene['slot'] in (1,11) else [scene]
    for m in targets:m['origin']=[x,y]


def move_entrance(value,identity,door,x,y):
    scene=find(value['maps'],identity);item=find(scene['entrances'],door)
    if not 0<=x<2*scene['width'] or not 0<=y<2*scene['height']:raise EditorError('Entrance movement coordinates must fit the map.')
    item.update(half=[x,y],active=1)


def clone_map(value,source,target):
    """Native scripts/save IDs have 15 fixed slots; copy into an explicit slot.

    The target's stable IDs and origin survive. Copy door geometry and routes
    together with terrain so the new NPC paths cannot end inside a roof.
    """
    old=find(value['maps'],source);out=find(value['maps'],target)
    if old['slot']>=14 or out['slot']>=14:raise EditorError('Clone towns into town slots; cache rooms have specialized rules.')
    for key in ('width','height','rows','overlays'):out[key]=copy.deepcopy(old[key])
    out['name']=old['name'][:58]+' copy'
    for key in ('entrances','npcs'):
        for target,source in zip(out[key],old[key]):
            identity=target['id'];target.update(copy.deepcopy(source));target['id']=identity


def inspect(document):
    value=data(document)
    return dict(format=FORMAT,world=value['world'],tiles=value['tiles'],maps=value['maps'],
        limits=dict(native_map_slots=15,town_origin_alignment=64,world_size=[1024,1024],tiles=4096,jigsaws=1024,
                    entrance_slots=16,npc_route_slots=8),
        note='Coordinates: tiles for maps/town origins; half-tile movement coordinates for entrances. Native BLD execution remains active.')
