"""Native resource preview/copy/binding service; no Tk or executable payloads."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import tempfile
from editor_model import EditorError,encoded,child
from chi_import import run

FILE='chi-presentation.json'
FORMAT='btp-chi-presentation-v1'
SHEETS=('BTTLTECH.ICN','DESTRUCT.ICN','ANIMATE.ICN','MECHSHAP.CMP','BTSTATS.CMP','BTBORDER.CMP',
        'BTTITLE.CMP','INFOCOM.CMP','TINYLAND.CMP','STARLEAG.ICN','MAP.ICN','ENDMECH.CMP')


def settings(document):
    return json.loads(document.metadata.get(FILE,encoded(dict(format=FORMAT,schema_version=1,
        bindings=[],sounds=list(range(1,19)),sound_speed=100,music=1))))


def tool(document,command,cancel=None):
    """Decode the effective unsaved snapshot; source file layouts are irrelevant."""
    with tempfile.TemporaryDirectory(prefix='btp-chi-preview-') as temporary:
        root=Path(temporary)
        for name,content in document.files().items():
            path=child(root,name);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(content)
        output=run([document.validator,command[0],root,*command[1:]],cancel)
        if len(output)>4*1024*1024:raise EditorError('Native preview exceeded its four MiB budget.')
        return json.loads(output)


def preview(document,kind,resource,index=0,count=1,cancel=None):
    return tool(document,['chi-resource',kind,resource,str(index),str(count)],cancel)


def world_preview(document,ruined=False,cancel=None):return tool(document,['chi-world',str(int(ruined))],cancel)


# BWE1 is deliberately fixed-size. Tile handles index chi_spatial.tiles (not
# graphic IDs); 65535 denotes a non-renderable cell. Three 128x128 arrays carry
# terrain levels, joining masks and town slots. The 1024x1024 miniature is an
# indexed image using the actual game's display palette, not a terrain tint.
WORLD_SIDE=1024
WORLD_BLOCKS=128
WORLD_PREVIEW_BYTES=4+48+3*WORLD_BLOCKS*WORLD_BLOCKS+3*WORLD_SIDE*WORLD_SIDE


def decode_world_editor_preview(raw):
    import array,sys
    if len(raw)!=WORLD_PREVIEW_BYTES or raw[:4]!=b'BWE1':
        raise EditorError('Invalid bounded native world preview response.')
    offset=52;size=WORLD_BLOCKS*WORLD_BLOCKS
    levels=raw[offset:offset+size];offset+=size
    joins=raw[offset:offset+size];offset+=size
    towns=raw[offset:offset+size];offset+=size
    if any(value>15 for value in joins) or any(value>13 for value in towns):
        raise EditorError('Invalid native world preview block metadata.')
    grid=array.array('H');grid.frombytes(raw[offset:offset+2*WORLD_SIDE*WORLD_SIDE]);offset+=2*WORLD_SIDE*WORLD_SIDE
    if sys.byteorder!='little':grid.byteswap()
    pixels=raw[offset:]
    if any(value>15 for value in pixels):raise EditorError('Invalid native world preview palette index.')
    palette=raw[4:52]
    return dict(width=WORLD_SIDE,height=WORLD_SIDE,grid=grid,levels=levels,joins=joins,towns=towns,
        mini=dict(width=WORLD_SIDE,height=WORLD_SIDE,pixels=pixels,palette_bytes=palette,
                  palette=[palette[3*i:3*i+3].hex() for i in range(16)]))


def world_editor_preview(document,ruined=False,underlay=False,cancel=None):
    """One exact unsaved native render for the overview and detail canvases.

    ``mini`` can be displayed with Pillow Image.frombytes('P', (1024,1024),
    pixels) and putpalette(palette_bytes), or expanded using its RGB hex list.
    It includes all 66 original TINYLAND glyphs, their town-aware joins and
    per-tile town/custom miniature colours. No original pixels are persisted.
    """
    from editor_tiles import _capture_preview
    from chi_import import check_cancel
    check_cancel(cancel)
    with tempfile.TemporaryDirectory(prefix='btp-chi-world-editor-') as temporary:
        root=Path(temporary)
        for name,content in document.files().items():
            check_cancel(cancel)
            path=child(root,name);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(content)
        raw=_capture_preview([str(document.validator),'chi-world-editor',str(root),str(int(ruined)),str(int(underlay))],
            timeout=30,max_preview=WORLD_PREVIEW_BYTES,cancel=cancel)
    return decode_world_editor_preview(raw)


def grid(document,underlay=False):
    """One bounded 2 MiB index array; no million-object tile dictionary."""
    import array,sys
    from editor_tiles import _capture_preview
    with tempfile.TemporaryDirectory(prefix='btp-chi-grid-') as temporary:
        root=Path(temporary)
        for name,content in document.files().items():
            path=child(root,name);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(content)
        raw=_capture_preview([str(document.validator),'chi-grid',str(root),str(int(underlay))],max_preview=4+2*1024*1024)
    if raw[:4]!=b'BTG1' or len(raw)!=4+2*1024*1024:raise EditorError('Invalid bounded native grid response.')
    result=array.array('H');result.frombytes(raw[4:])
    if sys.byteorder!='little':result.byteswap()
    return result


def tile_atlases(document,sheet=None):
    from editor_tiles import CHI_SHEETS,CHI_IMPORT_SHEETS,_capture_preview,decode_atlas,load_original_animations,art_tiles
    from tile_animation import TileGraphics
    result=TileGraphics()
    banks=(CHI_IMPORT_SHEETS if document.manifest.get('chi_spatial') else CHI_SHEETS) if sheet is None else (sheet,)
    if any(bank not in CHI_IMPORT_SHEETS for bank in banks):raise EditorError('Unknown native tile bank.')
    with tempfile.TemporaryDirectory(prefix='btp-chi-atlas-') as temporary:
        root=Path(temporary)
        for name,content in document.files().items():
            path=child(root,name);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(content)
        for bank in banks:result[bank]=decode_atlas(_capture_preview([str(document.validator),'preview-tiles','--project',str(root),'--sheet',bank]))
        if 'chi:land' in banks:result.animations.update(load_original_animations(document.validator,root,project=True))
    if sheet is None:result.update(art_tiles(document))
    return result


def put_settings(document,value,label='Edit CHI presentation'):
    with document.command(label):
        manifest=copy.deepcopy(document.manifest);manifest['chi_presentation']=FILE
        meta=dict(document.metadata);meta[FILE]=encoded(value)
        document.replace_all(document.content,document.adventure,document.art,manifest,meta);document.validate()


def detach(document,kind,resource,index=0,count=1,decoded=None):
    """Copy-on-edit, retaining origin through pixel edits, clones and libraries."""
    from art_editing import clone_image
    from tile_editing import metadata
    image=copy.deepcopy(decoded if decoded is not None else preview(document,kind,resource,index,count))
    units=image.pop('native_units',None)
    image=clone_image(image,document.manifest['package_id'],document.art['images'])
    image['name']=f'Package portrait {index}' if kind=='portrait' else f'Original {resource} {index}'
    # Native resources are assigned explicitly. No implicit role binding can
    # replace every actor merely because somebody inspected one frame.
    value=settings(document);value['bindings']=[b for b in value['bindings'] if (b['kind'],b['resource'],b['index'])!=(kind,resource,index)]
    palette='sprite' if kind in ('sprite','animation','portrait') or resource=='TINYLAND.CMP' else 'direct' if kind=='font' or resource=='BTBORDER.CMP' else 'phoenix' if resource=='ENDMECH.CMP' else 'title' if resource in ('BTTITLE.CMP','INFOCOM.CMP') else 'terrain'
    binding=dict(kind=kind,resource=resource,index=index,image=image['id'],palette=palette)
    if units is not None:binding['units']=units
    value['bindings'].append(binding)
    with document.command('Copy native resource for editing'):
        art=copy.deepcopy(document.art);art['images'].append(image)
        manifest=copy.deepcopy(document.manifest);manifest.update(chi_presentation=FILE,graphics=manifest.get('graphics','graphics.json'))
        origin=dict(sheet='chi:resource',graphic=index,resource=resource,kind=kind)
        if kind=='portrait':
            import hashlib
            slots=('broker','training','lounge','prison','inventor','cinema','hospital','comstar','clothes','video-hut','mayor')
            slot=slots[index];asset=next((a for a in document.manifest['assets'] if a['slot']==slot),None)
            known=Path(__file__).resolve().parents[1]/'content/updated/art'/f'{slot}.anm'
            raw=document.files().get(asset['file']) if asset else None
            if raw is not None and known.is_file() and hashlib.sha256(raw).digest()==hashlib.sha256(known.read_bytes()).digest():
                origin.update(sheet='package:portrait',source='content/updated/art/README.md',sha256=hashlib.sha256(raw).hexdigest())
            else:origin['origin']='unknown'
        editing=metadata(document);editing.setdefault('tile_sources',{})[image['id']]=origin
        meta=dict(document.metadata);meta[FILE]=encoded(value);meta['EDITOR.json']=encoded(editing)
        document.replace_all(document.content,document.adventure,art,manifest,meta);document.validate()
    return image


def inventory(document):
    files=document.files();result=[]
    for sheet in SHEETS:
        tile=sheet.endswith('.ICN') or sheet in ('BTBORDER.CMP',)
        kind='tile' if tile and sheet!='BTBORDER.CMP' else 'screen'
        result.append(dict(kind=kind,resource=sheet,count=250 if kind=='tile' else 1))
    result.extend([dict(kind='sprite',resource='MECHSHAP.CMP',count=376),dict(kind='font',resource='BTTA.FONT',count=1)])
    for index in range(22):
        raw=files['chi/O'+str(index)+'.ANM'];count=raw[:32].index(0)
        result.append(dict(kind='animation',resource='O.ANM',index=index,count=count))
    for i,slot in enumerate(('broker','training','lounge','prison','inventor','cinema','hospital','comstar','clothes','video-hut','mayor')):
        asset=next((a for a in document.manifest['assets'] if a['slot']==slot),None)
        binding=next((b for b in settings(document)['bindings'] if b['kind']=='portrait' and b['index']==i),None)
        if binding:count=len(next(im for im in document.art['images'] if im['id']==binding['image'])['frames'])
        elif asset:count=files[asset['file']][:32].index(0)
        else:continue
        result.append(dict(kind='portrait',resource='PORTRAITS',index=i,count=count,name=slot))
    return dict(resources=result,palettes=['terrain','sprite','direct','phoenix','title'],
        sounds=[dict(slot=i,program=settings(document)['sounds'][i-1]) for i in range(1,19)],
        limits=dict(art_pixels=1048576,animation_frames=31,custom_tile_handles=4096),
        note='Native sheet/sprite replacements are quantized to the selected 16-colour display palette. Custom map tile images retain full RGBA. Native film frame counts remain fixed; duration units are retraces.')
