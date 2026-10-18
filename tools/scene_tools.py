"""Building stamps, grouped markers and deterministic authored world fills."""
import copy
import random
import json
import subprocess
from adventure_editing import composite,scene_markers,move_marker
from editor_model import EditorError,encoded
from event_editing import editor_data,editor_commit
from world_editing import identity,get_world,token

def formation_data(document,settings):
    if document.manifest['requires']=='none':
        p=json.loads(document.snapshot[document.manifest['presentation']])
        return {kind:[[x-8,y-8] for x,y in p[key]] for kind,key in [('people','people_formation'),('mechs','mech_formation')]}
    result=subprocess.run([str(document.validator),'formation','--combat-data',settings['combat-data']],capture_output=True,text=True,timeout=15)
    if result.returncode:raise EditorError(result.stderr.strip())
    return json.loads(result.stdout)

def formation_cells(document,scene_index,at,formation):
    grid=composite(document.adventure['maps'][scene_index]);tiles={token(t):t for t in document.adventure['tiles']}
    units={u['id']:u for u in document.content['mechs']};result=[];counts={'people':0,'mechs':0}
    for member in document.adventure['start']['party']:
        unit=units.get(member['mech']);kind='mechs' if unit else 'people';dx,dy=formation[kind][counts[kind]];counts[kind]+=1
        x,y=at[0]+dx,at[1]+dy;cells=[(x//2,y//2),(x//2+1,y//2)] if unit else [((x+1)//2,y//2)]
        drive=unit.get('movement',{}).get('type') if unit else None
        for cx,cy in cells:
            terrain=tiles[grid[cy][cx]]['terrain'] if 0<=cy<len(grid) and 0<=cx<len(grid[0]) else 'wall'
            blocked=terrain=='wall' or (drive=='tracked' and terrain=='water') or (drive=='wheeled' and terrain in ('woods','rough','water')) or (drive=='hover' and terrain=='woods')
            result.append((cx,cy,blocked))
    return result

def capture_stamp(document,scene_index,rect,name):
    scene=document.adventure['maps'][scene_index];x0,y0,x1,y1=rect;grid=composite(scene)
    if not name or min(x0,y0)<0 or x1<x0 or y1<y0 or x1>=len(grid[0]) or y1>=len(grid):raise EditorError('Select an in-bounds building rectangle and give it a name.')
    doors=[]
    for door in scene['entrances']:
        x,y=door['at']
        if 2*x0<=x<2*(x1+1) and 2*y0<=y<2*(y1+1):
            d=copy.deepcopy(door);d['at']=[x-2*x0,y-2*y0];doors.append(d)
    data=editor_data(document);stamps=data.setdefault('building_stamps',[])
    ids={token(t):t['id'] for t in document.adventure['tiles']}
    stamp=dict(id=identity(document.manifest['package_id'],stamps,'building'),name=name,
               rows=[[ids[t] for t in row[x0:x1+1]] for row in grid[y0:y1+1]],entrances=doors)
    stamps.append(stamp);editor_commit(document,data);return stamp['id']

def place_stamp(document,scene_index,stamp_id,x,y):
    a=copy.deepcopy(document.adventure);scene=a['maps'][scene_index]
    stamp=next(s for s in editor_data(document).get('building_stamps',[]) if s['id']==stamp_id)
    w,h=len(stamp['rows'][0]),len(stamp['rows'])
    if min(x,y)<0 or x+w>len(scene['rows'][0]) or y+h>len(scene['rows']):raise EditorError('The complete building and its entrances must fit on the map.')
    valid={t['id'] for t in a['tiles']};events={e['id'] for e in a['events']};people={p['id'] for p in a['people']}
    if any(t not in valid for row in stamp['rows'] for t in row):raise EditorError('A tile used by this stamp has been deleted.')
    tokens={t['id']:token(t) for t in a['tiles']}
    rows=[''.join(tokens[t] for t in row) for row in stamp['rows']] if a['schema_version']==1 else copy.deepcopy(stamp['rows'])
    scene['overlays'].append(dict(at=[x,y],rows=rows))
    for old in stamp['entrances']:
        if old['event'] not in events or ('person' in old and old['person'] not in people):raise EditorError('A stamp event/person no longer exists.')
        door=copy.deepcopy(old);door.update(id=identity(document.manifest['package_id'],[d for m in a['maps'] for d in m['entrances']],'entrance'),at=[old['at'][0]+2*x,old['at'][1]+2*y]);scene['entrances'].append(door)
    document.replace_adventure(a);return len(scene['overlays'])

def move_group(document,scene_index,layer_index,x,y):
    a=copy.deepcopy(document.adventure);scene=a['maps'][scene_index]
    if not 0<=layer_index<len(scene['overlays']):raise EditorError('Select a building overlay first.')
    layer=scene['overlays'][layer_index];ox,oy=layer['at'];w,h=len(layer['rows'][0]),len(layer['rows'])
    if min(x,y)<0 or x+w>len(scene['rows'][0]) or y+h>len(scene['rows']):raise EditorError('The complete building must remain on the map.')
    for marker in scene_markers(a,scene_index):
        px,py=marker['at']
        if 2*ox<=px<2*(ox+w) and 2*oy<=py<2*(oy+h):move_marker(a,scene_index,marker['ref'],[px+2*(x-ox),py+2*(y-oy)])
    layer['at']=[x,y];document.replace_adventure(a)

def generate_world(document,world_id,seed,weights,match_edges=True):
    """Generate explicit pieces; saving never depends on a future Python RNG.

    Edge compatibility compares collision terrain, so differently painted
    water/forest edge tiles can still connect. Incompatible sets fail atomically.
    """
    a=copy.deepcopy(document.adventure);world=get_world(a,world_id);jigs={j['id']:j for j in a['jigsaws']}
    if not weights or any(k not in jigs or type(v)!=int or not 1<=v<=1000 for k,v in weights.items()):raise EditorError('Choose existing jigsaws with integer weights 1..1000.')
    terrain={token(t):t['terrain'] for t in a['tiles']}
    sides={k:([terrain[t] for t in j['rows'][0]],[terrain[r[-1]] for r in j['rows']],
              [terrain[t] for t in j['rows'][-1]],[terrain[r[0]] for r in j['rows']]) for k,j in jigs.items()}
    rng=random.Random(int(seed));height,width=len(world['pieces']),len(world['pieces'][0]);pieces=[]
    for attempt in range(32):
        pieces=[];failed=False
        for y in range(height):
            row=[]
            for x in range(width):
                allowed=[k for k in weights if not match_edges or ((not x or sides[row[-1]][1]==sides[k][3]) and (not y or sides[pieces[-1][x]][2]==sides[k][0]))]
                if not allowed:failed=True;break
                row.append(rng.choices(allowed,[weights[k] for k in allowed])[0])
            if failed:break
            pieces.append(row)
        if not failed:break
    if failed:raise EditorError('These weighted jigsaws cannot form a matching world with this seed. Add compatible pieces or disable edge matching.')
    world['pieces']=pieces;data=editor_data(document);data.setdefault('world_generation',{})[world['id']]=dict(seed=int(seed),weights=weights,match_edges=bool(match_edges))
    metadata=dict(document.metadata);metadata['EDITOR.json']=encoded(data)
    document.replace_all(document.content,a,document.art,document.manifest,metadata)
