"""Read-only full-map preview using the editor's actual tile decoder."""
import hashlib
from pathlib import Path
from adventure_editing import composite
from authoring_contract import API_VERSION, AuthoringError
from authoring_service import find, revision
from world_editing import token
from editor_tiles import load_tiles
from editor_model import EditorError
from tile_animation import tile_loop


def render_map(document, identity, output, settings=None, tick=0, collision=False):
    output=Path(output).resolve()
    if output.is_relative_to(document.root):
        raise AuthoringError('output.invalid','Write preview artifacts outside the project directory.')
    if tick<0 or tick>4294967295:raise AuthoringError('request.invalid','Tick must be 0..4294967295.')
    a=document.adventure or {};scene=find(a.get('maps',[]),identity)[1]
    try:graphics=load_tiles(document,settings or {})
    except EditorError as exc:
        raise AuthoringError('dependency.unavailable' if document.manifest['requires']!='none' else 'preview.unavailable',str(exc)) from exc
    tiles={token(t):t for t in a['tiles']};grid=composite(scene)
    width,height=len(grid[0])*16,len(grid)*16;pixels=bytearray(width*height*3)
    for y,row in enumerate(grid):
        for x,cell in enumerate(row):
            tile=tiles[cell];sheet,graphic=tile['sheet'],tile['graphic'];loop=tile_loop(graphics,sheet,graphic)
            image=loop.frames[(tick//loop.ticks)%len(loop.frames)] if loop else graphics[sheet][graphic]
            for py,line in enumerate(image):
                for px,color in enumerate(line):
                    rgb=bytes.fromhex(color.lstrip('#'))
                    if collision and tile['terrain']=='wall':rgb=bytes((min(255,rgb[0]//2+128),rgb[1]//2,rgb[2]//2))
                    at=((y*16+py)*width+x*16+px)*3;pixels[at:at+3]=rgb
    data=f'P6\n{width} {height}\n255\n'.encode()+pixels
    document.unchanged_on_disk();output.parent.mkdir(parents=True,exist_ok=True)
    # Exclusive artifacts avoid accidentally replacing an earlier comparison.
    with output.open('xb') as stream:stream.write(data)
    return dict(api_version=API_VERSION,status='rendered',revision=revision(document),map=identity,tick=tick,
                collision_overlay=collision,artifact=dict(path=str(output),format='ppm',width=width,height=height,sha256=hashlib.sha256(data).hexdigest()))
