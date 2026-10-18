"""Selection, canvas and layered pixel operations, independent of Tk."""
import copy
import math
from pathlib import Path
from art_editing import TRANSPARENT,pixels,write_pixels,new_image
from editor_model import EditorError

def begin_layers(image,saved=None):
    result=copy.deepcopy(image)
    if saved is not None and not isinstance(saved,dict):raise EditorError('Invalid saved editing metadata.')
    if saved and saved.get('flattened')==image['frames']:
        layers=saved.get('layers')
        if not isinstance(layers,list) or not 1<=len(layers)<=8:raise EditorError('Invalid saved editing layers.')
        for layer in layers:
            if not isinstance(layer,dict) or not isinstance(layer.get('name'),str) or type(layer.get('visible'))!=bool or len(layer.get('frames',[]))!=len(image['frames']):raise EditorError('Invalid saved editing layer.')
            for frame in layer['frames']:
                if len(frame)!=image['height'] or any(not isinstance(row,str) or len(row)!=8*image['width'] or any(c not in '0123456789abcdef' for c in row) for row in frame):raise EditorError('Saved editing layers have invalid pixels or dimensions.')
        active=saved.get('active',0)
        if type(active)!=int or not 0<=active<len(layers):raise EditorError('Invalid active editing layer.')
        result['_layers']=copy.deepcopy(saved['layers']);result['_layer']=active
    else:result['_layers']=[dict(name='Base',visible=True,frames=copy.deepcopy(image['frames']))];result['_layer']=0
    return result

def target(image):
    return dict(image,frames=image['_layers'][image['_layer']]['frames']) if '_layers' in image else image

def flatten(image,frame=None):
    if '_layers' not in image:return
    for index in range(len(image['frames'])) if frame is None else [frame]:
        rows=[[TRANSPARENT]*image['width'] for _ in range(image['height'])]
        for layer in image['_layers']:
            if not layer['visible']:continue
            for y,row in enumerate(layer['frames'][index]):
                for x in range(image['width']):
                    src=row[x*8:x*8+8];sa=int(src[6:],16)
                    if sa==255:rows[y][x]=src;continue
                    if not sa:continue
                    dst=rows[y][x];da=int(dst[6:],16);den=sa*255+da*(255-sa)
                    rgb=[(int(src[k:k+2],16)*sa*255+int(dst[k:k+2],16)*da*(255-sa)+den//2)//den for k in (0,2,4)]
                    rows[y][x]=''.join(f'{c:02x}' for c in [*rgb,(den+127)//255])
        write_pixels(image,index,rows)

def export_layers(image):
    clean={k:copy.deepcopy(v) for k,v in image.items() if not k.startswith('_')}
    return clean,dict(layers=copy.deepcopy(image['_layers']),active=image['_layer'],flattened=copy.deepcopy(image['frames']))

def add_layer(image,name='Layer'):
    if len(image['_layers'])>=8:raise EditorError('An image supports up to eight editing layers.')
    image['_layers'].append(dict(name=name,visible=True,frames=[[TRANSPARENT*image['width'] for _ in range(image['height'])] for _ in image['frames']]))
    image['_layer']=len(image['_layers'])-1

def selected_pixels(image,frame,rect):
    x0,y0,x1,y1=rect;rows=pixels(target(image),frame)
    return [row[x0:x1+1] for row in rows[y0:y1+1]]

def paste_selection(image,frame,clipboard,x,y):
    rows=pixels(target(image),frame)
    for sy,row in enumerate(clipboard):
        for sx,color in enumerate(row):
            if 0<=y+sy<image['height'] and 0<=x+sx<image['width']:rows[y+sy][x+sx]=color
    write_pixels(target(image),frame,rows);flatten(image,frame)

def resize_canvas(image,width,height,x=0,y=0):
    # Validate before changing dimensions. All animation frames and layers
    # receive the same crop/pad; there is no implicit image resampling.
    new_image('check',[],'Check',image['kind'],width,height,len(image['frames']))
    oldw,oldh=image['width'],image['height']
    for layer in image.get('_layers',[dict(frames=image['frames'])]):
        result=[]
        for frame in layer['frames']:
            result.append([''.join(frame[sy][sx*8:sx*8+8] if 0<=sx<oldw and 0<=sy<oldh else TRANSPARENT
                                   for sx in range(x,x+width)) for sy in range(y,y+height)])
        layer['frames'][:]=result
    image['width']=width;image['height']=height;flatten(image)

def export_sheet(image,path,columns=4):
    try:from PIL import Image
    except ImportError as exc:raise EditorError('PNG sheet export needs Pillow (python3-pil).') from exc
    if not 1<=columns<=len(image['frames']):raise EditorError('Columns must fit the image count.')
    w,h=image['width'],image['height'];sheet=Image.new('RGBA',(w*columns,h*math.ceil(len(image['frames'])/columns)))
    for i,frame in enumerate(image['frames']):sheet.paste(Image.frombytes('RGBA',(w,h),bytes.fromhex(''.join(frame))),((i%columns)*w,(i//columns)*h))
    sheet.save(Path(path),format='PNG')
