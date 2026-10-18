"""Tile management shared by the chooser, construction previews and jigsaws.

Original/indexed sheets are read-only sources. Clones own independent RGBA
pixels; a definition and its image always enter history together.
"""
import copy
import json
from editor_model import EditorError, encoded
from world_editing import identity, upgrade, graphic_tile
from art_editing import new_image, clone_image


def metadata(document):return json.loads(document.metadata.get('EDITOR.json',b'{}'))


def tile(document,identity):
    value=next((t for t in document.adventure['tiles'] if t['id']==identity),None)
    if value is None:raise EditorError('This tile no longer exists. Select another tile or Undo its removal.')
    return value


def source_definition(document,sheet,graphic):
    known=next((t for t in document.adventure['tiles'] if t['sheet']==sheet and t['graphic']==graphic),None)
    if known:return dict(known)
    terrain='clear'
    if sheet in ('chi:land','chi:destroyed') and isinstance(graphic,int):
        # CHI's terrain bands (also used by core collision) supply a useful
        # default for previously unregistered atlas cells. Project overrides
        # above win; authors can refine individual building/entrance tiles.
        terrain='wall' if graphic>=85 else 'water' if 0<graphic<16 else 'rough' if 16<=graphic<32 else 'woods' if 32<=graphic<64 else 'clear'
    return dict(sheet=sheet,graphic=graphic,terrain=terrain,mini_color=2)


def check_budget(art,adventure):
    if len(adventure['tiles'])>4096 or len(art['images'])>4096:raise EditorError('A game supports up to 4096 tile definitions and 4096 images.')
    if sum(i['width']*i['height']*len(i['frames']) for i in art['images'])>1048576:
        raise EditorError('These copies exceed the game’s 1,048,576 pixel artwork budget. Copy fewer tiles or remove unused artwork.')


def source_origin(data,source):
    # Carry the root source through repeated clones, so exported pattern
    # artwork does not lose its provenance when its parent image stays behind.
    return copy.deepcopy(data.get('tile_sources',{}).get(source['graphic'],dict(sheet=source['sheet'],graphic=source['graphic']))) if source['sheet']=='package:art' else dict(sheet=source['sheet'],graphic=source['graphic'])


def copy_graphic(art,prefix,decoded,sheet,graphic,name='Tile copy'):
    if sheet=='package:art':
        old=next((i for i in art['images'] if i['id']==graphic),None)
        if not old or old['kind']!='tile':raise EditorError('Choose an existing 16×16 tile image.')
        image=clone_image(old,prefix,art['images'])
    else:
        from tile_animation import copy_frames
        try:frames=copy_frames(decoded,sheet,graphic)
        except (KeyError,IndexError,TypeError):raise EditorError('This graphic is unavailable. Reload graphics or choose a package tile.')
        image=new_image(prefix,art['images'],name)
        image.update(frames)
    image['name']=name[:95];art['images'].append(image);return image


def sheet_graphics(decoded,sheet=None):
    """Identify graphics by both bank and index; two banks can share index 0."""
    return [(bank,key) for bank in ([sheet] if sheet else decoded)
            for key in (decoded.get(bank,{}) if isinstance(decoded.get(bank),dict) else range(len(decoded.get(bank,()))))]


def create_tile(document,decoded=None,source=None,name='New tile',terrain=None):
    """Create blank pixels or clone a graphic/definition, returning stable ID."""
    a=copy.deepcopy(document.adventure);art=copy.deepcopy(document.art);data=metadata(document);prefix=document.manifest['package_id']
    if source:
        source=tile(document,source) if isinstance(source,str) else {**source_definition(document,source['sheet'],source['graphic']),**source}
        image=copy_graphic(art,prefix,decoded or {},source['sheet'],source['graphic'],name)
        terrain=terrain or source.get('terrain','clear');mini=source.get('mini_color',2)
        data.setdefault('tile_sources',{})[image['id']]=source_origin(data,source)
        layers=data.get('pixel_layers',{}).get(source['graphic']) if source['sheet']=='package:art' else None
        if layers:data['pixel_layers'][image['id']]=copy.deepcopy(layers)
    else:
        image=new_image(prefix,art['images'],name);art['images'].append(image);terrain=terrain or 'clear';mini=2
    value=graphic_tile(a,prefix,'package:art',image['id'],terrain,mini)
    data.setdefault('tile_names',{})[value]=name
    check_budget(art,a);meta=dict(document.metadata);meta['EDITOR.json']=encoded(data)
    with document.command('Create tile' if source is None else 'Clone tile'):document.replace_art(art,a,meta)
    return value


def clone_sheet(document,decoded,sheet,sources=None):
    """One undoable transaction; the source sheet is never edited or removed."""
    hidden=metadata(document).get('hidden_tile_graphics',[])
    if sources is None:
        sources=([dict(t) for t in document.adventure['tiles']] if sheet=='Project tiles' else
                 [source_definition(document,bank,key) for bank,key in sheet_graphics(decoded,None if sheet=='All tiles' else sheet) if [bank,str(key)] not in hidden])
    else:sources=[{**source_definition(document,s['sheet'],s['graphic']),**s} for s in sources]
    if not sources:raise EditorError('There are no tiles to clone in this sheet.')
    a=copy.deepcopy(document.adventure);art=copy.deepcopy(document.art);data=metadata(document);prefix=document.manifest['package_id'];result=[]
    # Preflight before allocating the copied frames. Budget rejection changes
    # neither the document nor its history, even for a large atlas.
    if len(a['tiles'])+len(sources)>4096 or len(art['images'])+len(sources)>4096:raise EditorError('Copying this sheet would exceed the 4096 tile/image limit.')
    for source in sources:
        name=f"{source['sheet']} {source['graphic']} copy"[:95]
        image=copy_graphic(art,prefix,decoded,source['sheet'],source['graphic'],name)
        value=graphic_tile(a,prefix,'package:art',image['id'],source.get('terrain','clear'),source.get('mini_color',2));result.append(value)
        data.setdefault('tile_names',{})[value]=name
        data.setdefault('tile_sources',{})[image['id']]=source_origin(data,source)
        layers=data.get('pixel_layers',{}).get(source['graphic']) if source['sheet']=='package:art' else None
        if layers:data['pixel_layers'][image['id']]=copy.deepcopy(layers)
    check_budget(art,a);meta=dict(document.metadata);meta['EDITOR.json']=encoded(data)
    with document.command('Clone all sheet tiles'):document.replace_art(art,a,meta)
    return result


def ensure_tile(document,sheet,graphic):
    source=source_definition(document,sheet,graphic)
    a=copy.deepcopy(document.adventure);value=graphic_tile(a,document.manifest['package_id'],sheet,graphic,source['terrain'],source['mini_color'])
    document.replace_adventure(a)
    return next(t['id'] for t in a['tiles'] if t.get('key',t['id'])==value)


def select_tile(maps,identity):
    maps.refresh();index=next(i for i,t in enumerate(maps.document.adventure['tiles']) if t['id']==identity)
    maps.brush.selection_set(str(index));maps.brush.see(str(index));maps.select_brush();return index


def edit_pixels(maps,identity,context=None):
    select_tile(maps,identity);return maps.edit_tile_pixels(context)


def tile_label(document,value):
    return metadata(document).get('tile_names',{}).get(value['id'],value['id'].split(':')[-1])
