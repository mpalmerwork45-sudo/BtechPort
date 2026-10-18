"""Portable labelled SVG/PNG evidence; no Tk, Pillow or browser required.

Each visual embeds its pixels and records stable source IDs and content hashes.
Original art is decoded locally by the shared tools, never added to a package.
"""
import base64
import hashlib
import html
import json
from pathlib import Path
import struct
import zlib

from adventure_editing import composite,scene_markers
from authoring_contract import API_VERSION,AuthoringError
from authoring_service import find,revision
from art_editing import display_rows
from editor_model import EditorError,encoded
from event_editing import editor_data,edges
from world_editing import token


def png(rows):
    width,height=len(rows[0]),len(rows)
    def chunk(kind,body):return struct.pack('>I',len(body))+kind+body+struct.pack('>I',zlib.crc32(kind+body)&0xffffffff)
    pixels=b''.join(b'\0'+b''.join(bytes.fromhex(c.lstrip('#')) for c in row) for row in rows)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(pixels))+chunk(b'IEND',b'')


def image_svg(rows,x,y,width,height):
    data=base64.b64encode(png(rows)).decode()
    return f'<image x="{x}" y="{y}" width="{width}" height="{height}" preserveAspectRatio="xMinYMin meet" style="image-rendering:pixelated" href="data:image/png;base64,{data}"/>'


def text(x,y,value,size=12,color='#273b45'):
    return f'<text x="{x}" y="{y}" font-family="sans-serif" font-size="{size}" fill="{color}">{html.escape(str(value))}</text>'


def svg(width,height,body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
            f'<rect width="100%" height="100%" fill="#f1f4f3"/>'+''.join(body)+'</svg>').encode()


def artifact(document,output,data,format,**fields):
    output=Path(output).resolve()
    if output.is_relative_to(document.root):raise AuthoringError('output.invalid','Write preview artifacts outside the game project.')
    document.unchanged_on_disk();output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('xb') as stream:stream.write(data)
    return dict(api_version=API_VERSION,status='rendered',revision=revision(document),artifact=dict(
        path=str(output),format=format,sha256=hashlib.sha256(data).hexdigest(),**fields))


class VisualSource:
    def __init__(self,document,settings=None):
        self.document=document;self.settings=settings or {};self._tiles=None;self.last_image=None

    @property
    def tiles(self):
        if self._tiles is None:
            from editor_tiles import load_tiles
            try:self._tiles=load_tiles(self.document,self.settings)
            except EditorError as exc:raise AuthoringError('dependency.unavailable',str(exc)) from exc
        return self._tiles

    def tile_frames(self,tile):
        from tile_animation import tile_loop
        loop=tile_loop(self.tiles,tile['sheet'],tile['graphic'])
        return (list(loop.frames),loop.ticks) if loop else ([self.tiles[tile['sheet']][tile['graphic']]],8)

    def grid(self,rows):
        definitions={t['id']:t for t in (self.document.adventure or {})['tiles']}
        result=[[] for _ in range(len(rows)*16)]
        decoded={}
        for y,line in enumerate(rows):
            for identity in line:
                if identity==' ':image=[['#dbe3e5']*16]*16
                else:
                    if identity not in decoded:decoded[identity]=self.tile_frames(definitions[identity])[0][0]
                    image=decoded[identity]
                for py,pixels in enumerate(image):result[y*16+py].extend(pixels)
        return result

    def frames(self,item):
        from editor_units import unit_sprite,person_sprite
        doc=self.document;identity=item['id'];kind=item['kind']
        if item['source']=='library':
            from authoring_contract import read_json
            from unit_library import preview_files
            from types import SimpleNamespace
            bundle=read_json(Path(item['file']));files=preview_files(bundle)
            source=SimpleNamespace(manifest=files['project.json'],content=files['content.json'],adventure=files['adventure.json'],
                art=files['graphics.json'],snapshot={k:encoded(v) for k,v in files.items()},validator=doc.validator)
            im=person_sprite(source,self.settings,bundle['person']) if kind=='infantry' else unit_sprite(source,self.settings,source.content['mechs'][0])
        elif kind=='tile':return self.tile_frames(item)
        elif kind in ('mech','vehicle'):im=unit_sprite(doc,self.settings,find(doc.content['mechs'],identity)[1])
        elif kind=='infantry':im=person_sprite(doc,self.settings,find(doc.adventure['people'],identity)[1])
        elif kind in ('sprite','icon','screen'):im=find(doc.art['images'],identity)[1]
        elif kind in ('pattern','jigsaw'):
            collection=editor_data(doc)['map_patterns'] if kind=='pattern' else doc.adventure['jigsaws']
            rows=find(collection,identity)[1]['rows']
            if kind=='jigsaw':
                ids={token(t):t['id'] for t in doc.adventure['tiles']};rows=[[ids[c] for c in row] for row in rows]
            return [self.grid(rows)],8
        elif kind=='construction':
            # Construction parts are previewed in their stored demo layout,
            # through the same generators as the designer, without committing.
            from construction_editing import compile_rows
            style=find(editor_data(doc)['construction_sets'],identity)[1]
            rows=compile_rows(style)
            return [self.grid(rows)],8
        else:raise AuthoringError('preview.unsupported','This asset has numeric definitions only.',object_id=identity)
        self.last_image=im
        return [display_rows(im,n) for n in range(len(im['frames']))],im.get('frame_ticks',8)


def contact_sheet(document,items,output,settings=None,columns=3):
    if not 1<=len(items)<=32 or not 1<=columns<=6:raise AuthoringError('query.bounds','Choose 1..32 assets and 1..6 columns.')
    source=VisualSource(document,settings);body=[];manifest=[];cellw,cellh=360,160
    for index,item in enumerate(items):
        x=(index%columns)*cellw;y=(index//columns)*cellh
        body.append(f'<rect x="{x+4}" y="{y+4}" width="352" height="152" rx="5" fill="white" stroke="#bccbce"/>')
        body.extend([text(x+12,y+23,item['name'][:46],13),text(x+12,y+42,item['key'],10)])
        entry=dict(key=item['key'],id=item['id'],name=item['name'],dependency=item.get('dependency'),cell=[x,y,cellw,cellh])
        try:
            frames,ticks=source.frames(item);rows=frames[0];scale=min(96/len(rows[0]),86/len(rows),4)
            body.append(image_svg(rows,x+12,y+52,len(rows[0])*scale,len(rows)*scale))
            digest=hashlib.sha256(png(rows)).hexdigest();entry.update(frames=len(frames),frame_ticks=ticks,pixel_sha256=digest)
            body.extend([text(x+124,y+75,item['kind']+' | '+str(item.get('dependency','project'))),
                         text(x+124,y+95,str(len(frames))+' frame(s), '+str(ticks*32)+' ms/frame'),
                         text(x+124,y+115,', '.join(item.get('tags',[]))[:30])])
        except (EditorError,KeyError) as exc:
            entry['diagnostic']=dict(code=getattr(exc,'diagnostic',{}).get('code','preview.unavailable'),message=str(exc))
            body.append(text(x+12,y+80,str(exc)[:46],11,'#994030'))
        manifest.append(entry)
    result=artifact(document,output,svg(columns*cellw,((len(items)+columns-1)//columns)*cellh,body),'svg',items=manifest)
    return result


def animation_strip(document,item,output,settings=None,start=0,limit=32,direction=None,action=None):
    if not 1<=limit<=32 or start<0:raise AuthoringError('query.bounds','Use nonnegative frame offset and 1..32 frames.')
    source=VisualSource(document,settings);frames,ticks=source.frames(item);indices=list(range(len(frames)));roles={};durations=[ticks]*len(frames);sound=0
    if source.last_image and item['kind'] in ('mech','vehicle','infantry','sprite'):
        from sprite_editing import sequence,DIRECTIONS,default_view
        view=('Character movement' if item['kind']=='infantry' else 'Unit movement' if len(frames)==32 else 'Original mech movement') if item['kind'] in ('mech','vehicle','infantry') else default_view(document,source.last_image)
        for facing,name in enumerate(DIRECTIONS):
            for phase,frame in enumerate(sequence(source.last_image,view,facing)):
                roles.setdefault(frame,[]).append(name+' '+str(phase+1))
        if direction is not None or action:
            indices=list(sequence(source.last_image,action or view,0 if direction is None else direction))
            if action:
                from action_tracks import entries
                track=entries(source.last_image,action,0 if direction is None else direction)
                if not track:raise AuthoringError('preview.unavailable','This sprite has no authored '+action+' track.')
                durations=[e['ticks'] for e in track];sound=source.last_image['animations'][action].get('sound',0)
            else:durations=[ticks]*len(indices)
    elif direction is not None or action:raise AuthoringError('preview.unsupported','Directional/action views require a sprite.')
    original=frames;frames=[original[i] for i in indices]
    if start>=len(frames):raise AuthoringError('query.bounds','Frame offset is outside this animation.')
    selected=frames[start:start+limit];w,h=len(frames[0][0]),len(frames[0]);scale=min(4,160/max(w,h));cell=max(96,int(w*scale)+12)
    columns=min(8,len(selected));body=[text(10,22,item['key']+' | '+str(ticks*32)+' ms/frame')]
    for n,rows in enumerate(selected):
        x=(n%columns)*cell;y=36+(n//columns)*(int(h*scale)+32)
        index=indices[start+n]
        body.append(image_svg(rows,x+6,y,w*scale,h*scale));body.append(text(x+6,y+h*scale+18,'Image '+str(index),11))
    return artifact(document,output,svg(columns*cell,40+((len(selected)+columns-1)//columns)*(int(h*scale)+32),body),'svg',
        asset=item['key'],frames_total=len(frames),frame_offset=start,frames_shown=len(selected),frame_ticks=ticks,
        frames=[dict(image=indices[start+n],ticks=durations[start+n],roles=roles.get(indices[start+n],[])) for n in range(len(selected))],sound=sound,
        next_offset=start+limit if start+limit<len(frames) else None)


def world_svg(document,identity,output,settings=None,rect=None):
    from world_editing import get_world,world_size,world_tile
    a=document.adventure or {};world=get_world(a,identity)
    if not world or world['id']!=identity:raise AuthoringError('object.missing','Select an existing world.')
    width,height=world_size(a,identity);x,y,w,h=rect or (0,0,min(32,width),min(32,height))
    if min(x,y)<0 or min(w,h)<1 or max(w,h)>64 or x+w>width or y+h>height:
        raise AuthoringError('coordinate.bounds','Choose an in-bounds world rectangle, at most 64 by 64 tiles.')
    ids={token(t):t['id'] for t in a['tiles']}
    rows=[[ids[world_tile(a,cx,cy,world_id=identity)] for cx in range(x,x+w)] for cy in range(y,y+h)]
    pixels=VisualSource(document,settings).grid(rows);body=[image_svg(pixels,12,40,w*16,h*16)];cities=[]
    for map_id in world['cities']:
        city=find(a['maps'],map_id)[1];cx,cy=city['origin'];cw,ch=len(city['rows'][0]),len(city['rows'])
        if cx>=x+w or cy>=y+h or cx+cw<=x or cy+ch<=y:continue
        left,top,right,bottom=max(cx,x),max(cy,y),min(cx+cw,x+w),min(cy+ch,y+h)
        body.append(f'<rect x="{12+(left-x)*16}" y="{40+(top-y)*16}" width="{(right-left)*16}" height="{(bottom-top)*16}" fill="none" stroke="#ffff50" stroke-width="2"/>')
        body.append(text(16+(left-x)*16,52+(top-y)*16,map_id,11,'#ffffff'));cities.append(map_id)
    body.append(text(12,24,world['name']+' | '+identity+' | world tiles '+str([x,y,w,h])))
    return artifact(document,output,svg(w*16+24,h*16+52,body),'svg',world=identity,rect=[x,y,w,h],cities=cities)


def event_graph(document,output):
    events=(document.adventure or {}).get('events',[])
    if not events:raise AuthoringError('preview.unavailable','This project has no authored events.')
    # A bounded grid is predictable for cycles and disconnected components;
    # editor-authored node positions remain untouched.
    positions={e['id']:((n%4)*300+20,(n//4)*130+30) for n,e in enumerate(events)}
    body=[]
    for e in events:
        x,y=positions[e['id']]
        for branch,target in edges(e):
            if target not in positions:continue
            tx,ty=positions[target];body.append(f'<path d="M {x+130} {y+70} L {tx+130} {ty}" fill="none" stroke="#7a9aab"/>')
            body.append(text((x+tx)/2+130,(y+ty)/2+30,branch,9))
    for e in events:
        x,y=positions[e['id']];body.append(f'<rect x="{x}" y="{y}" width="260" height="70" rx="5" fill="white" stroke="#286c80"/>')
        body.extend([text(x+8,y+22,e['id'],11),text(x+8,y+43,e['op'],12),text(x+8,y+61,e.get('text','')[:32],10)])
    return artifact(document,output,svg(1200,((len(events)+3)//4)*130+25,body),'svg',events=len(events))


def map_svg(document,identity,output,settings=None,tick=0,rect=None,overlays=()):
    from tile_animation import tile_loop
    a=document.adventure or {};scene=find(a.get('maps',[]),identity)[1];source=VisualSource(document,settings)
    grid=composite(scene);x0,y0,w,h=rect or (0,0,len(grid[0]),len(grid))
    if min(x0,y0)<0 or min(w,h)<1 or w>64 or h>64 or x0+w>len(grid[0]) or y0+h>len(grid):
        raise AuthoringError('coordinate.bounds','Choose an in-bounds rectangle of at most 64 by 64 tiles.')
    if tick<0:raise AuthoringError('query.bounds','Tick must be nonnegative.')
    definitions={token(t):t for t in a['tiles']};rows=[[] for _ in range(h*16)];body=[]
    for y,line in enumerate(grid[y0:y0+h]):
        for x,key in enumerate(line[x0:x0+w]):
            tile=definitions[key];frames,ticks=source.tile_frames(tile);pixels=frames[(tick//ticks)%len(frames)]
            for py,p in enumerate(pixels):rows[y*16+py].extend(p)
            if 'collision' in overlays and tile['terrain']=='wall':
                body.append(f'<rect x="{x*16}" y="{y*16}" width="16" height="16" fill="#ed384b" opacity=".45"/>')
    body.insert(0,image_svg(rows,0,0,w*16,h*16))
    if 'grid' in overlays:
        for x in range(w+1):body.append(f'<path d="M {x*16} 0 V {h*16}" stroke="#d5e0e0" opacity=".3"/>')
        for y in range(h+1):body.append(f'<path d="M 0 {y*16} H {w*16}" stroke="#d5e0e0" opacity=".3"/>')
    markers=scene_markers(a,find(a['maps'],identity)[0]);selected=[]
    for marker in markers:
        kind=marker['ref'][0]
        if kind not in ('entrance','npc','start') or 'entrances' not in overlays:continue
        x,y=marker['at'][0]*8-x0*16,marker['at'][1]*8-y0*16
        if not 0<=x<w*16 or not 0<=y<h*16:continue
        body.append(f'<rect x="{x-3}" y="{y-3}" width="7" height="7" fill="#ffff50" stroke="#17232d"/>')
        body.append(text(x+5,y,marker['ref'][2],9,'#ffffff'));selected.append(dict(id=marker['ref'][2],at=marker['at']))
    if 'formations' in overlays:
        from scene_tools import formation_data,formation_cells
        formation=formation_data(document,settings or {})
        anchors=[m for m in markers if m['ref'][0] in ('start','party')]
        for m in anchors:
            for cx,cy,blocked in formation_cells(document,find(a['maps'],identity)[0],m['at'],formation):
                body.append(f'<rect x="{(cx-x0)*16}" y="{(cy-y0)*16}" width="16" height="16" fill="none" stroke="'+('#ff5050' if blocked else '#70ffff')+'" stroke-width="2"/>')
    body=[f'<g transform="translate(12,40)">',*body,'</g>',text(12,24,scene['name']+' | '+identity+' | map tiles '+str([x0,y0,w,h]))]
    return artifact(document,output,svg(w*16+24,h*16+52,body),'svg',map=identity,rect=[x0,y0,w,h],tick=tick,overlays=list(overlays),markers=selected)
