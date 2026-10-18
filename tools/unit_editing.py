"""Templates and catalogue imports shared by the desktop editor and tests."""
import copy
import json
from pathlib import Path
from editor_model import EditorError
from world_editing import identity

LOCATIONS=('left_arm','left_torso','left_leg','head','center_torso','right_arm','right_torso','right_leg')
VEHICLE_LOCATIONS=('front','left','right','rear','turret')
WEAPONS=('small_laser','medium_laser','large_laser','ppc','ac2','ac5','ac10','ac20','machine_gun','flamer','lrm5','lrm10','lrm15','lrm20','srm2','srm4','srm6')
# Construction presets use standard damage/heat. Range thresholds follow the
# existing CHI adapter; new definitions remain editable and independently named.
PRESETS=((3,1,1,3,6,9),(5,1,3,9,18,27),(8,1,8,15,30,45),(10,1,10,18,36,54),
         (2,1,1,24,48,72),(5,1,1,18,36,54),(10,1,3,15,30,45),(20,1,7,9,18,27),
         (2,1,0,3,6,9),(2,1,3,3,6,9),(1,5,2,21,42,63),(1,10,4,21,42,63),
         (1,15,5,21,42,63),(1,20,6,21,42,63),(2,2,2,9,18,27),(2,4,3,9,18,27),(2,6,4,9,18,27))


def add_ammo(content, price=3):
    value=dict(id=identity(content['package_id'],content['ammunition'],'ammo'),price_per_shot=price)
    content['ammunition'].append(value);return value['id']


def add_equipment(content,behavior='heat_sink',name='Heat sink'):
    if behavior not in ('heat_sink','jump_jet','engine_heat_sink','armor_plating'):raise EditorError('Choose a supported equipment behavior.')
    library=content.setdefault('equipment',[])
    if len(library)>=256:raise EditorError('The equipment library is full (256 definitions).')
    item=dict(id=identity(content['package_id'],library,'equipment'),name=name,label=name[:11],behavior=behavior)
    library.append(item);return item['id']


def add_weapon(content, behavior='medium_laser', name=None):
    i=WEAPONS.index(behavior);damage,count,heat,near,medium,far=PRESETS[i]
    ammo=add_ammo(content) if 4<=i<=8 or i>=10 else 'none'
    name=name or behavior.replace('_',' ').title()
    value=dict(id=identity(content['package_id'],content['weapons'],'weapon'),name=name,label=name[:11],behavior=behavior,
               ammunition=ammo,damage=damage,projectiles=count,heat=heat,ranges=dict(short=near,medium=medium,long=far))
    content['weapons'].append(value);return value['id']


def add_unit(content,kind='mech',name='New mech',presentation=None):
    if not content['presentations']:raise EditorError('Add a sprite presentation first.')
    weapon=next((w for w in content['weapons'] if w['ammunition']=='none'),None)
    weapon_id=weapon['id'] if weapon else add_weapon(content)
    unit=dict(id=identity(content['package_id'],content['mechs'],'unit'),name=name,label=name[:15],mass_tons=50,price=20000,
              presentation=presentation or content['presentations'][0]['id'],engine_heat_sinks=10,
              movement=dict(walk=5,jump=0),loadout=[dict(weapon=weapon_id,location='center_torso',ammunition=0)])
    if kind=='mech':
        unit.update(armor={p:10 for p in LOCATIONS},structure={p:10 for p in LOCATIONS},
                    external_heat_sinks={p:0 for p in LOCATIONS},actuators={p:15 for p in ['left_arm','right_arm','left_leg','right_leg']})
        unit['armor'].update(left_rear=0,center_rear=0,right_rear=0)
    else:
        unit.update(kind='vehicle',armor={p:20 for p in VEHICLE_LOCATIONS},structure={p:5 for p in VEHICLE_LOCATIONS})
        unit['movement']['type']=kind;unit['loadout'][0]['location']='turret'
    content['mechs'].append(unit);return unit['id']


def assign_graphic(content,unit_id,image_id):
    # A fresh presentation isolates this choice from other units which may
    # share the original template. Editing one unit never changes the others.
    p=next((p for p in content['presentations'] if p.get('image')==image_id),None)
    if p is None:
        p=dict(id=identity(content['package_id'],content['presentations'],'sprite'),source='package:art',image=image_id)
        content['presentations'].append(p)
    next(m for m in content['mechs'] if m['id']==unit_id)['presentation']=p['id']


def import_catalogue(document,root,selected=None):
    root=Path(root);catalogue=json.loads((root/'units.json').read_text());graphics=json.loads((root/'graphics.json').read_text())
    content=copy.deepcopy(document.content);art=copy.deepcopy(document.art)
    units=[m for m in catalogue['mechs'] if selected is None or m['id'] in selected]
    weapon_ids={m['weapon'] for u in units for m in u['loadout']}
    weapons=[w for w in catalogue['weapons'] if w['id'] in weapon_ids]
    ammo_ids={w['ammunition'] for w in weapons};presentations={u['presentation'] for u in units}
    additions={'mechs':units,'weapons':weapons,'ammunition':[a for a in catalogue['ammunition'] if a['id'] in ammo_ids],
               'presentations':[p for p in catalogue['presentations'] if p['id'] in presentations]}
    # Re-import is idempotent. Never silently replace an author's edited unit.
    for key,values in additions.items():
        existing={v['id'] for v in content[key]};content[key].extend(copy.deepcopy(v) for v in values if v['id'] not in existing)
        if len(content[key])>256:raise EditorError(f'The {key} library is full (256 definitions).')
    image_ids={p['image'] for p in additions['presentations']};existing={i['id'] for i in art['images']}
    art['images'].extend(copy.deepcopy(i) for i in graphics['images'] if i['id'] in image_ids and i['id'] not in existing)
    manifest=copy.deepcopy(document.manifest)
    if 'graphics' not in manifest:
        if 'graphics.json' not in document.snapshot and (document.root/'graphics.json').exists():raise EditorError('graphics.json exists outside the project declarations; preserve it and declare or rename it first.')
        manifest['graphics']='graphics.json'
    document.replace_all(content,document.adventure,art,manifest)
    return [u['id'] for u in units]
