"""Editable map footprints compiled into ordinary, independently playable tiles.

The editor retains heights and the style in EDITOR.json. The player only needs
the resulting overlay. Rebuilding replaces that one overlay, never the ground
or another building, so removing a courtyard reveals the original terrain.
"""
import copy
from editor_model import EditorError,encoded
from tile_editing import metadata
from world_editing import identity,line,upgrade
from construction_editing import geometry,supply_parts


def objects(document,map_id,kind=None):
    return [o for o in metadata(document).get('map_constructions',[]) if o['map']==map_id and (kind is None or o['kind']==kind)]

def overlay_index(scene,record):
    layers=scene['overlays'];index=record.get('overlay',-1)
    if 0<=index<len(layers) and layers[index]==record['rendered']:return index
    matches=[i for i,layer in enumerate(layers) if layer==record['rendered']]
    if len(matches)==1:return matches[0]
    raise EditorError('This construction was changed with the tile/layer tools. Undo those changes to edit its footprint, or start a new construction.')

def new_object(document,scene_index,style,stories):
    all_objects=metadata(document).get('map_constructions',[])
    return dict(id=identity(document.manifest['package_id'],all_objects,'map-construction'),
        name=f"{style['kind']} {len(all_objects)+1}",map=document.adventure['maps'][scene_index]['id'],
        kind=style['kind'],style=style['id'],datum=stories,cells=[])

def stroke_cells(start,end,shape,width=1):
    if not 1<=width<=8:raise EditorError('Brush width must be 1..8 tiles.')
    if shape in ('Rectangle','Courtyard'):
        x0,x1=sorted((start[0],end[0]));y0,y1=sorted((start[1],end[1]))
        return {(x,y) for y in range(y0,y1+1) for x in range(x0,x1+1)
                if shape=='Rectangle' or min(x-x0,x1-x,y-y0,y1-y)<width}
    points=[];previous=None
    for point in line(*start,*end):
        # Keep diagonal wall/road drags connected at the cardinal tile edges.
        if previous and point[0]!=previous[0] and point[1]!=previous[1]:points.append(min((point[0],previous[1]),(previous[0],point[1])))
        points.append(point);previous=point
    return {(x+dx,y+dy) for x,y in points for dy in range(width) for dx in range(width)}

def paint_footprint(record,start,end,shape,stories,width=1,erase=False):
    maximum=3 if record['kind']=='Wall' else 32
    if not 1<=stories<=maximum:raise EditorError(f"Choose 1..{maximum} stories.")
    cells={(x,y):h for x,y,h in record['cells']}
    if shape=='Courtyard' and not erase:
        for point in stroke_cells(start,end,'Rectangle')-stroke_cells(start,end,shape,width):cells.pop(point,None)
    for point in stroke_cells(start,end,shape,width):
        if erase or shape=='Erase':cells.pop(point,None)
        else:cells[point]=stories
    record['cells']=[[x,y,h] for (x,y),h in sorted(cells.items())]

def projection(record):
    if not record['cells']:return (0,0),[[' ']]
    x0=min(c[0] for c in record['cells']);y0=min(c[1] for c in record['cells'])
    x1=max(c[0] for c in record['cells']);y1=max(c[1] for c in record['cells'])
    if x1-x0>=64 or y1-y0>=64:raise EditorError('The footprint must fit inside one map.')
    rows=[[0]*(x1-x0+1) for _ in range(y1-y0+1)]
    for x,y,h in record['cells']:rows[y-y0][x-x0]=h
    offset,roles=geometry(dict(kind=record['kind'],footprint=rows,datum=record['datum'],map_drawn=True),with_origin=True)
    # A fixed datum stops existing floors sliding when another floor is raised.
    return (x0+offset[0],y0+offset[1]),roles

def in_bounds(scene,record,at,roles):
    w,h=len(scene['rows'][0]),len(scene['rows'])
    return (all(0<=x<w and 0<=y<h for x,y,_ in record['cells']) and
            min(at)>=0 and at[0]+len(roles[0])<=w and at[1]+len(roles)<=h)


def commit_tiles(document,adventure,label='Paint map tiles'):
    """Keep hand-painted construction details and their tiles in one Undo step.

    Only reconcile ordinary tile edits with unchanged layer bounds/order.
    External layer moves/deletions still use overlay_index's stale-data guard.
    Details use map coordinates, so extending a footprint does not shift them.
    """
    data=metadata(document);changed=False
    old_maps={s['id']:s for s in document.adventure['maps']};new_maps={s['id']:s for s in adventure['maps']}
    for record in data.get('map_constructions',[]):
        before=old_maps.get(record['map']);after=new_maps.get(record['map'])
        if before is None or after is None:continue
        try:index=overlay_index(before,record)
        except EditorError:continue
        if index>=len(after['overlays']):continue
        old=before['overlays'][index];new=after['overlays'][index]
        if old==new or old['at']!=new['at'] or [len(r) for r in old['rows']]!=[len(r) for r in new['rows']]:continue
        details={(x,y):tile for x,y,tile in record.get('details',[])};ox,oy=new['at']
        for y,row in enumerate(new['rows']):
            for x,tile in enumerate(row):
                if tile!=old['rows'][y][x]:details[x+ox,y+oy]=tile
        record.update(overlay=index,rendered=copy.deepcopy(new),details=[[x,y,t] for (x,y),t in sorted(details.items())]);changed=True
    meta=dict(document.metadata)
    if changed:meta['EDITOR.json']=encoded(data)
    with document.command(label):document.replace_all(document.content,adventure,document.art,document.manifest,meta)

def commit(document,scene_index,record):
    a=copy.deepcopy(document.adventure);art=copy.deepcopy(document.art);data=metadata(document)
    scene=a['maps'][scene_index];saved=data.setdefault('map_constructions',[])
    old=next((o for o in saved if o['id']==record['id']),None)
    if scene['id']!=record['map']:raise EditorError('This footprint belongs to another map.')
    index=overlay_index(scene,old) if old else len(scene['overlays'])
    if not record['cells']:
        if old:
            scene['overlays'].pop(index);saved.remove(old)
            meta=dict(document.metadata);meta['EDITOR.json']=encoded(data)
            with document.command('Erase construction'):document.replace_all(document.content,a,art,document.manifest,meta)
        return None
    at,roles=projection(record)
    if not in_bounds(scene,record,at,roles):raise EditorError('The footprint and all projected floors must fit inside the map. Draw farther from the edge or reduce the height.')
    if not old and len(scene['overlays'])>=32:raise EditorError('This map already has 32 overlays. Extend an existing construction or remove a layer first.')
    style=next((p for p in data.get('construction_sets',[]) if p['id']==record['style'] and p['kind']==record['kind']),None)
    if not style:raise EditorError('Choose an existing construction style.')
    upgrade(a);supply_parts(a,art,data,document.manifest['package_id'],style,roles)
    layer=dict(at=list(at),rows=[[style['parts'][r] if r!=' ' else ' ' for r in row] for row in roles])
    # Retain custom roof/face tiles while those cells still belong to the
    # rebuilt shape. Erasing that section also removes its painted detail.
    details=[]
    for x,y,tile in record.get('details',[]):
        xx,yy=x-at[0],y-at[1]
        if 0<=yy<len(roles) and 0<=xx<len(roles[0]) and roles[yy][xx]!=' ':
            layer['rows'][yy][xx]=tile;details.append([x,y,tile])
    if old:scene['overlays'][index]=layer
    else:scene['overlays'].append(layer)
    value=copy.deepcopy(record);value.update(overlay=index,rendered=copy.deepcopy(layer))
    if 'details' in value:value['details']=details
    if old:saved[saved.index(old)]=value
    else:saved.append(value)
    meta=dict(document.metadata);meta['EDITOR.json']=encoded(data)
    with document.command('Draw '+record['kind'].lower()):document.replace_art(art,a,meta)
    return value['id']
