"""Read the same unit presentations used by the player without changing files."""
import copy
import json
from art_editing import original_sprite
from editor_model import EditorError


def indexed_sprite(source, index):
    frames=[[''.join(source['palette'][int(c,16)]+('ff' if c!='0' else '00') for c in row)
             for row in frame] for frame in source['sprites'][index]]
    return dict(id='library:indexed-sprite',name='Indexed sprite',kind='sprite',width=16,height=16,frames=frames)


def person_sprite(document, settings, person=None):
    if person and person.get("image"):
        return copy.deepcopy(next(i for i in document.art["images"] if i["id"]==person["image"]))
    binding=next((b for b in document.art['bindings'] if b['slot']=='npc'),None)
    if binding:return copy.deepcopy(next(i for i in document.art['images'] if i['id']==binding['image']))
    if document.manifest['requires']!='none':return original_sprite(document,settings,270,16)
    return indexed_sprite(json.loads(document.snapshot[document.manifest['presentation']]),2)


def unit_sprite(document,settings,unit):
    view=next(p for p in document.content['presentations'] if p['id']==unit['presentation'])
    if view['source']=='package:art':
        return copy.deepcopy(next(i for i in document.art['images'] if i['id']==view['image']))
    if view['source'] in ('chi:locust','chi:red-stinger'):
        return original_sprite(document,settings,0 if view['source']=='chi:locust' else 146,16)
    source=json.loads(document.snapshot[document.manifest['presentation']])
    index=0 if view['source']=='package:walker-a' else 1
    image=indexed_sprite(source,index);image.update(id=view['id'],name=unit['name']+' sprite');return image
