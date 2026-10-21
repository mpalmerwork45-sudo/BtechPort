"""Read the visible 3 x 3 neighbourhood without changing any map or tile."""
from adventure_editing import composite
from art_editing import display_rows
from editor_model import EditorError
from world_editing import token


def context_grid(document,context):
    """Keep the clicked placement, including concave corners and projected faces."""
    at=context.get('at')
    if 'construction' in context:
        from tile_editing import metadata
        from construction_editing import compile_rows,geometry,part_name,road_junction_grid,ROAD_T_JUNCTIONS
        source=next((p for p in metadata(document).get('construction_sets',[]) if p['id']==context['construction']),None)
        if source is None:return None
        role=context['role']
        direction=next((direction for direction,value in ROAD_T_JUNCTIONS if value==role),None)
        if source['kind']=='Road' and direction and context.get('road_sample')==role:
            # This explicitly labelled sample supplies surrounding road tiles
            # without changing the project's saved demonstration footprint.
            roles=road_junction_grid(source,role)
            grid=[[source['parts'].get(value,' ') for value in row] for row in roles]
            return source['name']+' — '+part_name(role)+' (junction sample)',grid,(1,1),'Empty',True
        roles=geometry(source);grid=compile_rows(source)
        if at is None or not (0<=at[1]<len(roles) and 0<=at[0]<len(roles[at[1]]) and roles[at[1]][at[0]]==role):
            at=next(([x,y] for y,row in enumerate(roles) for x,value in enumerate(row) if value==role),None)
        if at is None:
            # Stored styles can include unused parts. Do not invent neighbours
            # for a part that has no placement in the current demo footprint.
            return source['name']+' — '+part_name(role)+' (unused in this footprint)',[[source['parts'].get(role,' ')]],(0,0),'Empty',True
        return source['name']+' — '+part_name(role),grid,at,'Empty',True
    if 'jigsaw' in context:
        source=next((j for j in document.adventure.get('jigsaws',[]) if j['id']==context['jigsaw']),None)
        return (source['name'],source['rows'],at,'Outside jigsaw',True) if source else None
    source=next((m for m in document.adventure['maps'] if m['id']==context['map']),None)
    return (source['name'],composite(source),at,'Map edge',False) if source else None


def neighbours(document, decoded, context, image=None, frame=0):
    source=context_grid(document,context)
    if source is None:return None
    _,grid,(x,y),_,ids=source
    tiles={(t['id'] if ids else token(t)):t for t in document.adventure['tiles']}
    art={i['id']:i for i in document.art['images']}
    # Repeated placements of this artwork must show the in-progress stroke,
    # otherwise a seam could look correct until the shared tile is committed.
    if image is not None:art[image['id']]=image
    result=[]
    for dy in (-1,0,1):
        row=[]
        for dx in (-1,0,1):
            tx,ty=x+dx,y+dy
            if not (0<=ty<len(grid) and 0<=tx<len(grid[ty])) or grid[ty][tx]==' ':row.append(None);continue
            tile=tiles[grid[ty][tx]]
            try:
                if tile['sheet']=='package:art':
                    source=art[tile['graphic']];colors=display_rows(source,frame if image is not None and source is image else 0)
                else:colors=decoded[tile['sheet']][tile['graphic']]
            except (KeyError,IndexError):raise EditorError('Wait for the map graphics to load, then edit this tile again.')
            row.append(dict(tile=tile['id'],rows=colors))
        result.append(row)
    return result
