"""Construction coverage and bounded composition of package-owned tile art.

The 47 roof masks are the valid outer/inner corner combinations. Joining
authored faces is independent of the demo footprint, so a library style can
draw a new courtyard or stepped building without inventing unrelated faces.
Original atlas references are never silently copied into package artwork.
"""
import copy
import hashlib
import math

from editor_model import EditorError,encoded
from tile_editing import metadata


def primitive_roles(kind):
    if kind=='Road':return ['road_'+str(mask) for mask in range(16)]
    roofs=[]
    for outer in range(16):
        allowed=sum(1<<i for i,(a,b) in enumerate(((0,1),(1,2),(2,3),(3,0))) if not outer&(1<<a|1<<b))
        roofs.extend(f'roof_{outer}_{inner}' for inner in range(16) if not inner&~allowed)
    return roofs+[side+'_'+band for side in ('east','south') for band in ('single','base','middle','top')]+['empty']


def coverage(profile):
    from construction_editing import geometry,part_name
    roles=primitive_roles(profile['kind']);parts=profile['parts']
    visible={r for row in geometry(profile) for r in row if r!=' '}
    missing=[dict(role=r,name=part_name(r)) for r in roles if r not in parts]
    return dict(required=len(roles),assigned=len(roles)-len(missing),missing=missing,
        preview_missing=sorted(visible-set(parts)),joins=sum(r.startswith('join|') for r in parts),
        generated_joins=len(profile.get('generated_joins',{})),complete=not missing)


def tile_art(a,art,identity):
    tile=next((t for t in a['tiles'] if t['id']==identity),None)
    image=next((im for im in art['images'] if tile and tile['sheet']=='package:art' and im['id']==tile['graphic']),None)
    return tile,image


def fingerprint(tile,image):
    if image is None:return None
    return hashlib.sha256(encoded(dict(frames=image['frames'],frame_ticks=image.get('frame_ticks',8),
        terrain=tile['terrain'],mini_color=tile['mini_color']))).hexdigest()


def joined_art(a,art,profile,role):
    """Exact triangular composition, preserving both source animation clocks."""
    roles=role.split('|')[1:];images=[];sources=[]
    for part in roles:
        tile,im=tile_art(a,art,profile['parts'][part])
        if not im:
            from construction_editing import part_name
            raise EditorError(f'{part_name(role)} needs package-owned pixels for {part_name(part)}. '
                              'Clone that part into project artwork, or assign a tile to this join explicitly.')
        images.append(im);sources.append(im['id'])
    # Static faces do not constrain cadence. For two different loops, sample
    # the common period at their GCD; reject excessive combinations atomically.
    animated=[im for im in images if len(im['frames'])>1]
    ticks=math.gcd(*(im.get('frame_ticks',8) for im in animated)) if animated else 8
    period=math.lcm(*(len(im['frames'])*im.get('frame_ticks',8) for im in animated)) if animated else ticks
    if period//ticks>256:raise EditorError('This join would need more than 256 animation frames. Use compatible frame counts/timing or assign an explicit join tile.')
    frames=[]
    for time in range(0,period,ticks):
        first,second=[im['frames'][(time//im.get('frame_ticks',8))%len(im['frames'])] for im in images]
        frames.append([second[y][:y*8]+first[y][y*8:] for y in range(16)])
    result=dict(frames=frames)
    if len(frames)>1:result['frame_ticks']=ticks
    return result,sources


def refresh_joins(a,art,data,prefix,profile):
    """Refresh generated joins; manual assignments/pixel edits become overrides.

    New images/tiles leave already-painted maps and other styles alone. Redraw
    an existing construction to apply the revised style; per-cell details stay.
    """
    from construction_editing import add_part
    generated=profile.setdefault('generated_joins',{})
    for role,old_hash in list(generated.items()):
        tile,im=tile_art(a,art,profile['parts'].get(role))
        if not im or fingerprint(tile,im)!=old_hash:
            generated.pop(role,None);continue
        value,sources=joined_art(a,art,profile,role)
        if value['frames']==im['frames'] and value.get('frame_ticks',8)==im.get('frame_ticks',8):continue
        add_part(a,art,data,prefix,profile,role,value,sources)
    if not generated:profile.pop('generated_joins',None)


def complete_profile(document,identity,refresh=True):
    """Fill missing primitive roles and update derived joins in one Undo step."""
    from construction_editing import supply_parts,geometry
    a=copy.deepcopy(document.adventure);art=copy.deepcopy(document.art);data=metadata(document)
    profile=next((p for p in data.get('construction_sets',[]) if p['id']==identity),None)
    if not profile:raise EditorError('Choose an existing construction style.')
    prefix=document.manifest['package_id']
    supply_parts(a,art,data,prefix,profile,[primitive_roles(profile['kind'])]+geometry(profile))
    if refresh:refresh_joins(a,art,data,prefix,profile)
    from tile_editing import check_budget
    check_budget(art,a)
    meta=dict(document.metadata);meta['EDITOR.json']=encoded(data)
    with document.command('Complete construction style'):document.replace_art(art,a,meta)
    return coverage(profile)
