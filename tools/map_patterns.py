"""Persistent reusable terrain blocks, using stable tile IDs across palette edits."""
import copy
import json
from pathlib import Path
from adventure_editing import composite,paint
from editor_model import EditorError,encoded
from world_editing import identity,token,upgrade,world_size,world_tile,patch_cells,set_patch,get_world
from tile_editing import metadata,check_budget


def check_rows(document,rows):
    if not rows or not rows[0] or len(rows)>64 or len(rows[0])>64 or any(len(r)!=len(rows[0]) for r in rows):
        raise EditorError('A pattern must be a rectangle of 1..64 tiles on each side.')
    valid={t['id'] for t in document.adventure['tiles']}|{' '}
    if any(t not in valid for r in rows for t in r):raise EditorError('A tile used by this pattern is missing. Undo its deletion or replace the reference.')


def capture(document,index,rect,layer=None):
    scene=document.adventure['maps'][index];x0,y0,x1,y1=rect
    if layer is None:grid=composite(scene);ox=oy=0
    else:
        source=scene if layer==0 else scene['overlays'][layer-1];grid=source['rows'];ox,oy=(0,0) if layer==0 else source['at']
    if min(x0-ox,y0-oy)<0 or x1<x0 or y1<y0 or x1-ox>=len(grid[0]) or y1-oy>=len(grid):raise EditorError('The whole selection must fit inside the selected map layer.')
    ids={token(t):t['id'] for t in document.adventure['tiles']};ids[' ']=' '
    return [[ids[t] for t in row[x0-ox:x1-ox+1]] for row in grid[y0-oy:y1-oy+1]]


def cut(document,index,rect,layer=0):
    rows=capture(document,index,rect,layer);a=copy.deepcopy(document.adventure)
    ground=next((t for t in a['tiles'] if t['terrain']=='clear'),a['tiles'][0]);value=token(ground) if layer==0 else ' '
    for y in range(rect[1],rect[3]+1):
        for x in range(rect[0],rect[2]+1):paint(a['maps'][index],layer,x,y,value)
    with document.command('Cut map tiles'):document.replace_adventure(a)
    return rows


def paste(adventure,index,layer,x,y,rows):
    scene=adventure['maps'][index];target=scene if layer==0 else scene['overlays'][layer-1];ox,oy=(0,0) if layer==0 else target['at']
    if x<ox or y<oy or x+len(rows[0])>ox+len(target['rows'][0]) or y+len(rows)>oy+len(target['rows']):
        raise EditorError('The complete pattern must fit in the selected layer. Move it inward or choose a larger layer.')
    ids={t['id']:token(t) for t in adventure['tiles']}
    if any(t!=' ' and t not in ids for row in rows for t in row):raise EditorError('This clipboard uses a missing tile. Copy the area again.')
    for yy,row in enumerate(rows):
        for xx,value in enumerate(row):
            if value!=' ':paint(scene,layer,x+xx,y+yy,ids[value])


def save_pattern(document,rows,name,pattern_id=None):
    check_rows(document,rows)
    if not name.strip() or len(name)>95:raise EditorError('Give the pattern a name of 1..95 characters.')
    data=metadata(document);patterns=data.setdefault('map_patterns',[])
    value=dict(id=pattern_id or identity(document.manifest['package_id'],patterns,'pattern'),name=name,rows=copy.deepcopy(rows))
    old=next((p for p in patterns if p['id']==value['id']),None)
    if old:patterns[patterns.index(old)]=value
    else:patterns.append(value)
    meta=dict(document.metadata);meta['EDITOR.json']=encoded(data)
    with document.command('Save map pattern'):document.replace_all(document.content,document.adventure,document.art,document.manifest,meta)
    return value['id']


def world_capture(document,world_id,rect):
    x0,y0,x1,y1=rect;w,h=world_size(document.adventure,world_id)
    if min(x0,y0)<0 or x1>=w or y1>=h or x1<x0 or y1<y0 or x1-x0>=64 or y1-y0>=64:raise EditorError('Select an in-bounds world rectangle up to 64×64 tiles.')
    return [[world_tile(document.adventure,x,y,world_id=world_id) for x in range(x0,x1+1)] for y in range(y0,y1+1)]


def world_paste(adventure,world_id,x,y,rows):
    w,h=world_size(adventure,world_id)
    if min(x,y)<0 or x+len(rows[0])>w or y+len(rows)>h:raise EditorError('The complete pattern must fit in the world.')
    world=get_world(adventure,world_id)
    for scene in adventure['maps']:
        ox,oy=scene['origin']
        if scene['id'] in world['cities'] and x<ox+len(scene['rows'][0]) and ox<x+len(rows[0]) and y<oy+len(scene['rows']) and oy<y+len(rows):
            raise EditorError('This area overlaps a city. Edit its local map to change the visible tiles.')
    cells=patch_cells(world)
    for yy,row in enumerate(rows):
        for xx,value in enumerate(row):
            if value!=' ':cells[x+xx,y+yy]=value
    set_patch(world,cells)


def export_pattern(document,pattern,path):
    check_rows(document,pattern['rows']);used={t for row in pattern['rows'] for t in row if t!=' '}
    tiles=[copy.deepcopy(t) for t in document.adventure['tiles'] if t['id'] in used]
    images={t['graphic'] for t in tiles if t['sheet']=='package:art'}
    data=dict(format='btp-map-pattern-v1',pattern=pattern,tiles=tiles,
              images=[im for im in document.art['images'] if im['id'] in images],
              source=dict(package=document.manifest['package_id'],title=document.manifest['title']))
    # Explicit user-chosen destination, with atomic replacement like other
    # editor exports. No originals or unrelated images enter this pattern.
    from editor_model import ProjectDocument
    ProjectDocument.atomic_file(Path(path),encoded(data))


def import_pattern(document,path):
    path=Path(path)
    if path.stat().st_size>32*1024*1024:raise EditorError('Pattern files are limited to 32 MiB.')
    data=json.loads(path.read_bytes())
    if data.get('format')!='btp-map-pattern-v1':raise EditorError('Choose an exported Construction Kit map pattern.')
    a=copy.deepcopy(document.adventure);art=copy.deepcopy(document.art);upgrade(a);prefix=document.manifest['package_id'];images={};tiles={}
    for old in data['images']:
        existing=next((i for i in art['images'] if i==old),None)
        if existing:images[old['id']]=existing['id'];continue
        value=copy.deepcopy(old);value['id']=identity(prefix,art['images'],'image');art['images'].append(value);images[old['id']]=value['id']
    for old in data['tiles']:
        if old['sheet'].startswith('chi:') and document.manifest['requires']=='none':raise EditorError('This pattern needs original CHI artwork. Use owned tile copies in independent projects.')
        value=copy.deepcopy(old);value.pop('key',None)
        if value['sheet']=='package:art':value['graphic']=images[value['graphic']]
        elif value['sheet']=='package:tiles' and data['source']['package']!=prefix:
            raise EditorError('This pattern uses its source game’s indexed palette. Clone those graphics to owned tiles before exporting across games.')
        existing=next((t for t in a['tiles'] if {k:v for k,v in t.items() if k!='id'}=={k:v for k,v in value.items() if k!='id'}),None)
        if existing:tiles[old['id']]=existing['id'];continue
        value['id']=identity(prefix,a['tiles'],'tile');a['tiles'].append(value);tiles[old['id']]=value['id']
    rows=[[tiles[t] if t!=' ' else ' ' for t in row] for row in data['pattern']['rows']]
    check_budget(art,a)
    with document.command('Import map pattern'):
        document.replace_art(art,a)
        result=save_pattern(document,rows,data['pattern']['name'])
        document.validate()
    return result
