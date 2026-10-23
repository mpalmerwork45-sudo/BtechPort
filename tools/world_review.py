"""Bounded world composition and change locations for review and preservation.

Rows are composed on demand. Even a maximum-size planet never becomes a
million-entry coordinate dictionary or a full-resolution 16384-pixel image.
These are authoring views; the native loader still validates playable content.
"""
import hashlib
import json
from adventure_editing import composite
from authoring_contract import AuthoringError
from world_editing import all_worlds,token


def overlap(a,b):
    x,y=max(a[0],b[0]),max(a[1],b[1]);right=min(a[0]+a[2],b[0]+b[2]);bottom=min(a[1]+a[3],b[1]+b[3])
    return [x,y,right-x,bottom-y] if x<right and y<bottom else None


def city_rect(city):return [*city['origin'],len(city['rows'][0]),len(city['rows'])]


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()


class Surface:
    def __init__(self,document,identity):
        self.document=document;a=document.adventure or {}
        self.world=next((w for w in all_worlds(a) if w['id']==identity),None)
        if self.world is None:raise AuthoringError('object.missing','World is absent: '+identity,object_id=identity)
        self.width=8*len(self.world['pieces'][0]);self.height=8*len(self.world['pieces'])
        self.jigsaws={p['id']:p['rows'] for p in a['jigsaws']}
        self.cities={m['id']:m for m in a['maps'] if m['id'] in self.world['cities']}
        self.city_rows={key:composite(m) for key,m in self.cities.items()}
        self.patches={}
        for patch in self.world['patches']:
            x,y=patch['at']
            for dy,row in enumerate(patch['rows']):self.patches.setdefault(y+dy,[]).append((x,row))

    def row(self,y,x=0,width=None,cities=True):
        width=self.width if width is None else width;result=[None]*width
        if not 0<=y<self.height:return result
        left,right=max(0,x),min(self.width,x+width)
        for piece in range(left//8,(right+7)//8):
            start,end=max(left,piece*8),min(right,(piece+1)*8)
            source=self.jigsaws[self.world['pieces'][y//8][piece]][y%8]
            result[start-x:end-x]=source[start-piece*8:end-piece*8]
        for px,row in self.patches.get(y,[]):
            start,end=max(left,px),min(right,px+len(row))
            if start<end:result[start-x:end-x]=row[start-px:end-px]
        if cities:
            for key,city in self.cities.items():
                cx,cy,cw,ch=city_rect(city);start,end=max(left,cx),min(right,cx+cw)
                if start<end and cy<=y<cy+ch:result[start-x:end-x]=self.city_rows[key][y-cy][start-cx:end-cx]
        return result


def tile_values(document):
    images={im['id']:im for im in (document.art or {}).get('images',[])}
    # The independent presentation has a shared palette. Fingerprint the
    # actual referenced pixels so palette edits cannot bypass preservation,
    # and changing an unused palette entry does not block an unrelated region.
    name=document.manifest.get('presentation');presentation=json.loads(document.files()[name]) if name else {}
    package={i:[[presentation['palette'][int(c,16)] for c in row] for row in rows]
             for i,rows in enumerate(presentation.get('tiles',[]))}
    return {token(t):dict(tile=t,image=images.get(t['graphic']) if t['sheet']=='package:art' else package.get(t['graphic']) if t['sheet']=='package:tiles' else None)
            for t in (document.adventure or {}).get('tiles',[])}


def changes(before,after,cancelled=lambda:False):
    """Scan at most the two packages' world tiles, retaining 64-tile bounds.

    Include ground beneath cities and shared tile/art changes. Region summaries
    are bounding boxes, not assertions that every enclosed tile was changed.
    """
    worlds=[{w['id']:w for w in all_worlds(d.adventure or {})} for d in (before,after)]
    signatures=[{k:hashlib.sha256(canonical(v)).digest() for k,v in tile_values(d).items()} for d in (before,after)]
    result=[]
    for identity in sorted(set(worlds[0])|set(worlds[1])):
        if signatures[0]==signatures[1] and worlds[0].get(identity)==worlds[1].get(identity):
            ids=set(worlds[0][identity]['cities'])
            towns=[{m['id']:m for m in (d.adventure or {}).get('maps',[]) if m['id'] in ids} for d in (before,after)]
            if towns[0]==towns[1]:continue
        surfaces=[Surface(d,identity) if identity in w else None for d,w in zip((before,after),worlds)]
        left,right=surfaces;bounds={};count=0;scanned=0
        for y in range(max(s.height if s else 0 for s in surfaces)):
            if y%16==0 and cancelled():raise AuthoringError('job.cancelled','World review cancelled.')
            width=max(s.width if s and y<s.height else 0 for s in surfaces);scanned+=width
            ground=[s.row(y,width=width,cities=False) if s else [None]*width for s in surfaces]
            visible=[s.row(y,width=width) if s else [None]*width for s in surfaces]
            for x in range(width):
                if (signatures[0].get(ground[0][x]),signatures[0].get(visible[0][x]))==(signatures[1].get(ground[1][x]),signatures[1].get(visible[1][x])):continue
                count+=1;key=(x//64,y//64)
                if key not in bounds:bounds[key]=[x,y,x,y,1]
                else:
                    b=bounds[key];b[:4]=[min(b[0],x),min(b[1],y),max(b[2],x),max(b[3],y)];b[4]+=1
        towns=[];city_sets=[s.cities if s else {} for s in surfaces]
        for key in sorted(set(city_sets[0])|set(city_sets[1])):
            a,b=city_sets[0].get(key),city_sets[1].get(key)
            if a==b:continue
            towns.append(dict(id=key,name=(b or a)['name'],change='placed' if a is None else 'removed' if b is None else 'moved' if a['origin']!=b['origin'] else 'edited',
                before=city_rect(a) if a else None,after=city_rect(b) if b else None))
        if count or towns or worlds[0].get(identity)!=worlds[1].get(identity):
            result.append(dict(id=identity,name=(right or left).world['name'],
                before=[left.width,left.height] if left else None,after=[right.width,right.height] if right else None,
                changed_tiles=count,scanned_tiles=scanned,areas=[dict(rect=[x,y,xx-x+1,yy-y+1],changed_tiles=n) for x,y,xx,yy,n in bounds.values()],towns=towns))
    return result


def overview(document,change,output,settings=None,cancelled=lambda:False):
    """Sample actual tile pixels at 1..4 pixels/tile, capped at 1024² pixels."""
    from authoring_visuals import VisualSource
    surface=Surface(document,change['id']);source=VisualSource(document,settings)
    maximum=max(*(change.get('before') or [0]),*(change.get('after') or [0]))
    scale=max(1,min(4,1024//maximum));definitions={token(t):t for t in document.adventure['tiles']};decoded={}
    pixels=[]
    for y in range(surface.height):
        if y%16==0 and cancelled():raise AuthoringError('job.cancelled','World preview cancelled.')
        scan=[[] for _ in range(scale)]
        for tile in surface.row(y):
            if tile not in decoded:
                frame=source.tile_frames(definitions[tile])[0][0]
                decoded[tile]=[[frame[(2*dy+1)*16//(2*scale)][(2*dx+1)*16//(2*scale)] for dx in range(scale)] for dy in range(scale)]
            for dy in range(scale):scan[dy].extend(decoded[tile][dy])
        pixels.extend(scan)
    if cancelled():raise AuthoringError('job.cancelled','World preview cancelled.')
    return publish(document,change,surface,pixels,[0,0,surface.width,surface.height],scale,output,True)


def detail(document,change,output,rect,settings=None,cancelled=lambda:False):
    """A clipped full-resolution crop using exactly the overview compositor."""
    from authoring_visuals import VisualSource
    surface=Surface(document,change['id']);x,y,w,h=rect
    ids={token(t):t['id'] for t in document.adventure['tiles']}
    rows=[[ids[c] for c in surface.row(cy,x,w)] for cy in range(y,y+h)]
    pixels=VisualSource(document,settings).grid(rows)
    if cancelled():raise AuthoringError('job.cancelled','World detail cancelled.')
    return publish(document,change,surface,pixels,rect,16,output,False)


def publish(document,change,surface,pixels,rect,scale,output,sampled):
    from authoring_visuals import artifact,image_svg,svg,text
    from authoring_protection import rules
    towns=[dict(id=key,name=city['name'],rect=city_rect(city)) for key,city in surface.cities.items()]
    protections=[dict(id=r['id'],label=r['label'],rect=r['rect']) for r in rules(document) if r['kind']=='world_region' and r['world']==change['id']]
    x,y,w,h=rect;label='sampled overview' if sampled else 'world tiles '+str(rect)
    body=[text(12,24,surface.world['name']+' | '+change['id']+' | '+label),image_svg(pixels,12,40,w*scale,h*scale)]
    for items,color in [(change['areas'],'#ff8050'),(towns,'#ffff50'),(protections,'#32d5ed')]:
        for item in items:
            hit=overlap(item['rect'],rect)
            if not hit:continue
            cx,cy,cw,ch=hit;left=12+(cx-x)*scale;top=40+(cy-y)*scale
            body.append(f'<rect x="{left}" y="{top}" width="{cw*scale}" height="{ch*scale}" fill="none" stroke="{color}" stroke-width="1"/>')
            if 'name' in item:body.append(text(left+2,top+11,item['name'],10,'#ffffff'))
    body.append(text(12,56+h*scale,'Orange: changed bounds | Yellow: towns | Cyan: protected world regions',10))
    return artifact(document,output,svg(w*scale+24,h*scale+64,body),'svg',world=change['id'],
        rect=rect,pixels_per_tile=scale,towns=towns,regions=change['areas'],protections=protections,
        basis=('Sampled' if sampled else 'Full-resolution')+' actual first-frame tile pixels. Changed bounds can enclose unchanged tiles.')
