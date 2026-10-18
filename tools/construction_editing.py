"""CHI-style tile construction from footprints, heights and editable parts.

Height is an authoring projection, not a new runtime elevation system. Roofs
and visible south/east faces compile to ordinary collision-bearing map tiles.
The two triangular halves of each face tile keep concave footprints connected.
"""
import copy
from editor_model import EditorError,encoded
from world_editing import identity,graphic_tile
from art_editing import new_image
from tile_editing import metadata,check_budget

NEIGHBOURS=((0,-1),(1,0),(0,1),(-1,0))


def preset(kind,width=9,height=9,stories=2,shape='Cross'):
    if not 1<=width<=32 or not 1<=height<=32:raise EditorError('Footprints are 1..32 cells on each side.')
    if kind=='Road':stories=1
    rows=[[0]*width for _ in range(height)]
    for y in range(height):
        for x in range(width):
            if shape=='Rectangle':inside=True
            elif shape=='Cross':inside=(x==width//2 or y==height//2) if kind in ('Wall','Road') else (width//3<=x<(2*width+2)//3 or height//3<=y<(2*height+2)//3)
            elif shape=='L shape':inside=x<(1 if kind in ('Wall','Road') else max(1,width//3)) or y>=height-(1 if kind in ('Wall','Road') else max(1,height//3))
            elif shape=='Courtyard':inside=x in (0,width-1) or y in (0,height-1)
            elif shape=='Line':inside=y==height//2
            else:inside=False
            if inside:rows[y][x]=stories
    return rows


def geometry(profile):
    """Return a rectangular grid of part names, with transparent outside cells."""
    rows=profile['footprint'];kind=profile['kind'];maximum=3 if kind=='Wall' else 1 if kind=='Road' else 8
    if not rows or not rows[0] or len(rows)>32 or len(rows[0])>32 or any(len(r)!=len(rows[0]) for r in rows):raise EditorError('Use a rectangular footprint up to 32×32 cells.')
    if any(type(v)!=int or not 0<=v<=maximum for r in rows for v in r):raise EditorError(f'{kind} heights must be 0..{maximum}; zero is empty.')
    width,height=len(rows[0]),len(rows);highest=max(map(max,rows));cells={}
    def at(x,y):return rows[y][x] if 0<=x<width and 0<=y<height else 0
    def half(x,y,index,value):
        cells.setdefault((x,y),['empty','empty'])[index]=value
    for x,y in sorted(((x,y) for y in range(height) for x in range(width) if at(x,y)),key=lambda p:(p[0]+p[1],p[1])):
        h=at(x,y)
        if kind=='Road':
            mask=sum(1<<i for i,(dx,dy) in enumerate(NEIGHBOURS) if at(x+dx,y+dy))
            cells[x,y]=['road_'+str(mask)]*2;continue
        # Far columns precede near columns. Faces are projected one tile east
        # and south per story, then their own roof covers the rear face halves.
        for level in range(1,h+1):
            px,py=x+highest-level,y+highest-level
            band='single' if h==1 else 'base' if level==1 else 'top' if level==h else 'middle'
            if at(x+1,y)<level:
                half(px+1,py,1,'east_'+band);half(px+1,py+1,0,'east_'+band)
            if at(x,y+1)<level:
                half(px,py+1,0,'south_'+band);half(px+1,py+1,1,'south_'+band)
        mask=sum(1<<i for i,(dx,dy) in enumerate(NEIGHBOURS) if at(x+dx,y+dy)<h)
        corners=((1,-1,0,1),(1,1,1,2),(-1,1,2,3),(-1,-1,3,0))
        inner=sum(1<<i for i,(dx,dy,a,b) in enumerate(corners) if not mask&(1<<a|1<<b) and at(x+dx,y+dy)<h)
        cells[x+highest-h,y+highest-h]=[f'roof_{mask}_{inner}']*2
    if not cells:return [[' ']]
    x0=min(x for x,y in cells);y0=min(y for x,y in cells);x1=max(x for x,y in cells);y1=max(y for x,y in cells)
    result=[[' ']*(x1-x0+1) for _ in range(y1-y0+1)]
    for (x,y),parts in cells.items():result[y-y0][x-x0]=parts[0] if parts[0]==parts[1] else 'join|'+parts[0]+'|'+parts[1]
    return result


def part_name(role):
    if role==' ':return 'Empty'
    if role.startswith('join|'):return ' / '.join(part_name(p) if p!='empty' else 'outside' for p in role.split('|')[1:])
    if role.startswith('roof_'):
        _,mask,inner=role.split('_');edges=' '.join(n for i,n in enumerate(('N','E','S','W')) if int(mask)&(1<<i))
        corners=' '.join(n for i,n in enumerate(('NE','SE','SW','NW')) if int(inner)&(1<<i))
        return 'Roof '+(edges+' edge' if edges else 'centre')+(' / inner '+corners if corners else '')
    if role.startswith('road_'):
        return 'Road '+(' '.join(n for i,n in enumerate(('N','E','S','W')) if int(role[5:])&(1<<i)) or 'isolated')
    return role.replace('_',' ').title()


def default_pixels(role,kind='Building'):
    """Small original editor presets; every generated tile remains editable."""
    if role.startswith('join|'):
        _,a,b=role.split('|');one=default_pixels(a,kind);two=default_pixels(b,kind)
        return [[one[y][x] if x>=y else two[y][x] for x in range(16)] for y in range(16)]
    # Runtime maps flatten layers to one tile per cell. Outside wedges need
    # a painted ground colour, not alpha that would reveal the framebuffer.
    pixels=[['48644aff']*16 for _ in range(16)]
    if role=='empty':return pixels
    if role.startswith('road_'):
        mask=int(role[5:])
        for y in range(16):
            for x in range(16):
                inside=(2<=x<14 and 2<=y<14) or (mask&1 and y<8 and 2<=x<14) or (mask&2 and x>=8 and 2<=y<14) or (mask&4 and y>=8 and 2<=x<14) or (mask&8 and x<8 and 2<=y<14)
                pixels[y][x]='535965ff' if inside else '48644aff'
                if inside and ((mask==5 and x==7 and y%8<4) or (mask==10 and y==7 and x%8<4)):pixels[y][x]='dfc475ff'
        return pixels
    roof=role.startswith('roof_');mask=int(role.split('_')[1]) if roof else 0;inner=int(role.split('_')[2]) if roof else 0
    for y in range(16):
        for x in range(16):
            if roof:
                color='acb9bdff' if kind=='Building' else '99917fff'
                if x%8==0 or y%8==0:color='99a7adff' if kind=='Building' else '817967ff'
                if (mask&1 and y<2) or (mask&8 and x<2):color='d9e4e5ff'
                if (mask&2 and x>13) or (mask&4 and y>13):color='586c79ff'
                for i,(cx,cy) in enumerate(((15,0),(15,15),(0,15),(0,0))):
                    if inner&(1<<i) and abs(x-cx)<3 and abs(y-cy)<3:color='405564ff'
            else:
                color='728692ff' if role.startswith('south') else '43576aff'
                if y in (0,15):color='26394bff'
                if kind=='Building' and 4<=y<11 and x in (3,4,5,10,11,12):color='add2caff' if role.startswith('south') else '6e96a3ff'
                if kind=='Wall' and (y==8 or x==(0 if y<8 else 8)):color='293e4bff'
            pixels[y][x]=color
    return pixels


def compile_rows(profile):
    roles=geometry(profile)
    missing={p for row in roles for p in row if p!=' ' and p not in profile['parts']}
    if missing:raise EditorError('Assign tiles to these construction parts: '+', '.join(part_name(p) for p in sorted(missing)))
    return [[profile['parts'][p] if p!=' ' else ' ' for p in row] for row in roles]


def put_profile(document,profile,label='Edit construction set'):
    profile=copy.deepcopy(profile);roles=geometry(profile);a=copy.deepcopy(document.adventure);art=copy.deepcopy(document.art);data=metadata(document);prefix=document.manifest['package_id']
    valid={t['id'] for t in a['tiles']}
    for role in sorted({p for row in roles for p in row if p!=' '}):
        if role in profile['parts']:
            if profile['parts'][role] not in valid:raise EditorError('A construction part uses a deleted tile. Replace it or Undo.')
            continue
        image=new_image(prefix,art['images'],part_name(role)[:95]);image['frames']=[[''.join(row) for row in default_pixels(role,profile['kind'])]];art['images'].append(image)
        value=graphic_tile(a,prefix,'package:art',image['id'],'clear' if profile['kind']=='Road' else 'wall',8)
        profile['parts'][role]=value;data.setdefault('tile_names',{})[value]=part_name(role)
    check_budget(art,a);profiles=data.setdefault('construction_sets',[])
    old=next((p for p in profiles if p['id']==profile['id']),None)
    if old:profiles[profiles.index(old)]=profile
    else:profiles.append(profile)
    meta=dict(document.metadata);meta['EDITOR.json']=encoded(data)
    with document.command(label):document.replace_art(art,a,meta)
    return profile['id']


def new_profile(document,kind='Building',name=None):
    profiles=metadata(document).get('construction_sets',[])
    value=dict(id=identity(document.manifest['package_id'],profiles,'construction'),name=name or kind+' set',kind=kind,
               footprint=preset(kind,9,9,2,'Cross' if kind=='Building' else 'L shape' if kind=='Wall' else 'Cross'),parts={})
    return put_profile(document,value,'New '+kind.lower()+' set')


def draw_road(adventure,scene_index,layer,start,end,profile,width=1):
    """Merge neighbour masks after a stroke, including old endpoints/junctions."""
    from adventure_editing import paint
    from world_editing import line,token
    if not 1<=width<=8:raise EditorError('Road width must be 1..8 tiles.')
    scene=adventure['maps'][scene_index];ids={token(t):t['id'] for t in adventure['tiles']};keys={t['id']:token(t) for t in adventure['tiles']}
    target=scene if layer==0 else scene['overlays'][layer-1];ox,oy=(0,0) if layer==0 else target['at']
    road_ids={v for k,v in profile['parts'].items() if k.startswith('road_')}
    occupied={(x+ox,y+oy) for y,row in enumerate(target['rows']) for x,t in enumerate(row) if ids.get(t) in road_ids}
    points=[];previous=None
    for point in line(*start,*end):
        if previous and point[0]!=previous[0] and point[1]!=previous[1]:
            # Roads use cardinal connection tiles. Bridge diagonal mouse
            # samples so a quick slanting drag cannot leave isolated squares.
            # A canonical bridge also makes a reversed stroke follow itself.
            points.append(min((point[0],previous[1]),(previous[0],point[1])))
        points.append(point);previous=point
    stroke={(x+xx,y+yy) for x,y in points for xx in range(width) for yy in range(width)}
    def inside(p):return ox<=p[0]<ox+len(target['rows'][0]) and oy<=p[1]<oy+len(target['rows'])
    if not all(inside(p) for p in stroke):raise EditorError('The whole road brush must fit in the selected layer.')
    occupied|=stroke;affected=stroke|{(x+dx,y+dy) for x,y in stroke for dx,dy in NEIGHBOURS}
    for x,y in affected&occupied:
        if not inside((x,y)):continue
        mask=sum(1<<i for i,(dx,dy) in enumerate(NEIGHBOURS) if (x+dx,y+dy) in occupied)
        paint(scene,layer,x,y,keys[profile['parts']['road_'+str(mask)]])


def prepare_road(document,profile):
    """Generate every junction variant before drawing directly on the map."""
    profile=copy.deepcopy(profile);a=copy.deepcopy(document.adventure);art=copy.deepcopy(document.art);data=metadata(document);prefix=document.manifest['package_id']
    for mask in range(16):
        role='road_'+str(mask)
        if role in profile['parts']:continue
        image=new_image(prefix,art['images'],part_name(role));image['frames']=[[''.join(r) for r in default_pixels(role,'Road')]];art['images'].append(image)
        profile['parts'][role]=graphic_tile(a,prefix,'package:art',image['id'],'clear',8)
    check_budget(art,a)
    profiles=data['construction_sets'];profiles[next(i for i,p in enumerate(profiles) if p['id']==profile['id'])]=profile
    meta=dict(document.metadata);meta['EDITOR.json']=encoded(data)
    with document.command('Prepare road brush'):document.replace_art(art,a,meta)
    return profile
