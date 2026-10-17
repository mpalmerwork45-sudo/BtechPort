#!/usr/bin/env python3
"""Reproducible original pixel art and factual vehicle presets; no copied art.

Run from the repository root. Sarna source links and adaptation notes live next
to the generated library. Facing armor splits, ammo allocations and game prices
are authoring presets, not a claim to reproduce published record sheets.
"""
import json
from pathlib import Path
from PIL import Image,ImageDraw
from unit_editing import add_weapon

ROOT=Path(__file__).resolve().parents[1]/'content/catalogues/vehicles'
# name, drive, mass, cruise MP, sinks, armor total, weapon/location/ammo, color
VEHICLES=[
 ('Patton','tracked',65,4,10,232,[('ac10','turret',20),('lrm5','turret',24),('flamer','rear',0),('small_laser','front',0)],'#8b9f6a'),
 ('Rommel','tracked',65,4,10,176,[('ac20','turret',20),('lrm5','turret',24),('small_laser','front',0)],'#bd9661'),
 ('Pegasus','hover',35,8,3,104,[('srm6','turret',8),('srm6','turret',7),('medium_laser','front',0)],'#689ba5'),
 ('Skulker','wheeled',20,7,3,72,[('medium_laser','front',0)],'#89955c'),
 ('Drillson','hover',50,9,10,116,[('large_laser','turret',0),('srm2','turret',25),('srm2','turret',25),('lrm10','front',12),('machine_gun','left',100),('machine_gun','right',100)],'#879dc5'),
 ('Galleon','tracked',30,6,5,56,[('medium_laser','turret',0),('small_laser','left',0),('small_laser','right',0)],'#b9a786'),
 ('Scorpion','tracked',25,4,0,64,[('ac5','turret',20),('machine_gun','front',100)],'#a78c64'),
 ('Vedette','tracked',50,5,0,96,[('ac5','turret',20),('machine_gun','front',100)],'#668f73'),
 ('LRM Carrier','tracked',60,3,0,48,[('lrm20','front',8)]*3,'#a29b69'),
 ('SRM Carrier','tracked',60,3,0,48,[('srm6','front',10)]*10,'#ad7764')]


def sprite(name,drive,color,index):
    frames=[]
    for direction in range(8):
        for frame in range(4):
            im=Image.new('RGBA',(32,32));d=ImageDraw.Draw(im)
            hull=(9,7,22,25) if index<2 else (10,9,21,24)
            if drive=='hover':
                d.ellipse((6,7,25,26),fill='#293840',outline='#111922');d.ellipse((8,8,23,25),fill=color,outline='#d4e1dc')
                d.line((10,25,21,25),fill=['#5f9dba','#91c9d5','#b7e8ed','#91c9d5'][frame],width=1)
            elif drive=='wheeled':
                for x in (7,22):
                    for y in (10,16,22):d.rectangle((x,y,x+2,y+3),fill='#151e24',outline='#65727a')
            else:
                for x in (6,23):
                    d.rectangle((x,8,x+3,25),fill='#263039',outline='#111b21')
                    for y in range(9+frame%2,25,3):d.line((x,y,x+3,y),fill='#7d8583')
            d.rectangle(hull,fill=color,outline='#202f36');d.line((hull[0]+1,hull[1]+1,hull[2]-1,hull[1]+1),fill='#e2dbb5')
            d.rectangle((12,20,19,23),fill='#3d504b');d.line((13,21,18,21),fill='#18282d');d.line((13,23,18,23),fill='#18282d')
            if 'Carrier' in name:
                d.rectangle((8,10,23,18),fill='#38454d',outline='#d4c8a2')
                for x in range(10,23,3):
                    for y in (12,15):d.rectangle((x,y,x+1,y+1),fill='#111922')
            elif name=='Skulker':d.rectangle((12,11,19,17),fill='#afbd90',outline='#273b37');d.line((16,12,16,6),fill='#c6d7c9')
            else:
                d.ellipse((11,11,21,19),fill=color,outline='#26343e');d.line((12,12,18,12),fill='#e1dfbb')
                if name=='Pegasus':
                    for x in (10,19):d.rectangle((x,8,x+3,14),fill='#3c5364',outline='#bdcdd3');d.point((x+1,9),fill='#e7b26f')
                else:
                    length=3 if name in ('Rommel','Galleon') else 1
                    d.rectangle((15,length+2,17,13),fill='#333f45');d.line((16,length+2,16,12),fill='#d2d6b8')
            d.point((12,18),fill='#ffa46b');d.point((20,19),fill='#729bba')
            rotated=im.rotate(-direction*45,resample=Image.Resampling.NEAREST,expand=False)
            raw=rotated.tobytes();frames.append([raw[y*128:(y+1)*128].hex() for y in range(32)])
    return dict(id='vehicles:'+name.lower().replace(' ','-')+'-sprite',name=name+' driving',kind='sprite',width=32,height=32,frames=frames)


def main():
    ROOT.mkdir(parents=True,exist_ok=True)
    content=dict(format='btp-unit-catalogue-v1',package_id='vehicles',mechs=[],weapons=[],ammunition=[],presentations=[])
    art=dict(format='btp-art-v1',schema_version=1,images=[],bindings=[])
    for index,(name,drive,mass,walk,sinks,total,loadout,color) in enumerate(VEHICLES):
        slug=name.lower().replace(' ','-');identity='vehicles:'+slug;graphic=sprite(name,drive,color,index);art['images'].append(graphic)
        content['presentations'].append(dict(id=identity+'-view',source='package:art',image=graphic['id']))
        turret=not ('Carrier' in name or name=='Skulker');parts=['front','left','right','rear']+(['turret'] if turret else [])
        # Split the source-based/preset total with a modest front bias. Kept
        # explicit/editable until exact published facing allocations are audited.
        armor={p:total//(len(parts)+1) for p in parts};armor['front']=total-sum(armor[p] for p in parts if p!='front')
        armor.setdefault('turret',0);structure={p:max(1,(mass+9)//10) for p in parts};structure.setdefault('turret',0)
        mounts=[]
        for behavior,location,ammo in loadout:
            weapon=next((w for w in content['weapons'] if w['behavior']==behavior),None)
            if weapon is None:
                wid=add_weapon(content,behavior);weapon=next(w for w in content['weapons'] if w['id']==wid)
            mounts.append(dict(weapon=weapon['id'],location=location,ammunition=ammo))
        content['mechs'].append(dict(id=identity,name=name,label=name,kind='vehicle',mass_tons=mass,price=mass*350+len(loadout)*500,
            presentation=identity+'-view',movement=dict(type=drive,walk=walk,jump=0),engine_heat_sinks=sinks,armor=armor,structure=structure,loadout=mounts))
    (ROOT/'units.json').write_text(json.dumps(content,indent=2)+'\n');(ROOT/'graphics.json').write_text(json.dumps(art,indent=2)+'\n')


if __name__=='__main__':main()
