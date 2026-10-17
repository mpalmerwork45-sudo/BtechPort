#!/usr/bin/env python3
"""Rebuild the library's 25 numeric presets from pinned local research files.

No downloads, prose, original-game assets or third-party executable code are
included. Source paths, hashes, credit and data licence accompany the catalogue.
The conversion choices below are CHI adaptations, not a tabletop rules engine.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

from library_defaults import REVERSE_JOINTED
from unit_editing import LOCATIONS, add_weapon

ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = ROOT / 'content/catalogues/mechs'
ARMOR = dict(zip(('LA','LT','LL','HD','CT','RA','RT','RL','RTL','RTC','RTR'),
                (*LOCATIONS, 'left_rear','center_rear','right_rear')))
# Standard internal structure by tonnage: arm, side torso, leg, centre torso.
STRUCTURE = {20:(3,5,4,6),30:(5,7,7,10),35:(6,8,8,11),40:(6,10,10,12),
             50:(8,12,12,16),55:(9,13,13,18),60:(10,14,14,20),65:(10,15,15,21),
             70:(11,15,15,22),75:(12,16,16,23),80:(13,17,17,25),85:(14,18,18,27),
             90:(15,19,19,29),95:(16,20,20,30),100:(17,21,21,31)}
BEHAVIOR = {'Small Laser':'small_laser','Medium Laser':'medium_laser','Large Laser':'large_laser',
            'PPC':'ppc','AC/2':'ac2','AC/5':'ac5','AC/10':'ac10','AC/20':'ac20',
            'Machine Gun':'machine_gun','Flamer':'flamer',
            **{f'{kind.upper()} {size}':f'{kind}{size}' for kind,sizes in
               [('lrm',(5,10,15,20)),('srm',(2,4,6))] for size in sizes}}
AMMO = {'ac2':('IS Ammo AC/2',45),'ac5':('IS Ammo AC/5',20),
        'ac10':('IS Ammo AC/10',10),'ac20':('IS Ammo AC/20',5),
        'machine_gun':('IS Ammo MG - Full',200),
        **{f'{kind}{size}':(f'IS Ammo {kind.upper()}-{size}',shots) for kind,sizes in
           [('lrm',((5,24),(10,12),(15,8),(20,6))),('srm',((2,50),(4,25),(6,15)))] for size,shots in sizes}}


def convert(text, content):
    fields = dict(re.findall(r'^([^:\n]+):([^\n]*)',text,re.M))
    name = fields['chassis']+' '+fields['model']
    slug = re.sub(r'[^a-z0-9]+','-',name.lower()).strip('-')
    sections = {}
    for location in LOCATIONS:
        title=location.replace('_',' ').title()
        sections[location]=re.search(r'^'+title+r':\n(.*?)\n\n',text,re.M|re.S)[1].splitlines()
    mass = int(fields['mass']);arm,side,leg,center = STRUCTURE[mass]
    external = {part:slots.count('Heat Sink') for part,slots in sections.items()}
    sinks = int(fields['heat sinks'].split()[0]) - sum(external.values())
    assert sinks >= 0 and max(external.values()) <= 7, name
    weapons = [line.split(', ') for line in re.search(r'Weapons:\d+\n(.*?)\n\n',text,re.S)[1].splitlines()]
    counts = Counter(BEHAVIOR[w] for w,part in weapons);assigned=Counter();mounts=[]
    criticals = Counter(slot for slots in sections.values() for slot in slots)
    for weapon,part in weapons:
        behavior = BEHAVIOR[weapon]
        existing=next((w for w in content['weapons'] if w['behavior']==behavior),None)
        wid=existing['id'] if existing else add_weapon(content,behavior)
        ammo=0
        if behavior in AMMO:
            key,shots=AMMO[behavior];total=criticals[key]*shots
            # CHI attaches ammunition to individual guns; split a shared bin
            # without multiplying its supply or silently discarding odd rounds.
            ammo=total//counts[behavior]+(assigned[behavior]<total%counts[behavior])
            assigned[behavior]+=1
            assert 0 < ammo <= 254, (name,behavior,ammo)
        location=part.lower().replace(' ','_')
        if fields['chassis']=='King Crab' and behavior=='ac20':
            # MTF lists the torso portion of these split weapons. CHI models
            # one mount location, so keep the firing barrel in its actual arm.
            location=location.replace('torso','arm')
        mounts.append(dict(weapon=wid,location=location,ammunition=ammo))
    source='chi:locust' if fields['chassis'].casefold() in REVERSE_JOINTED else 'chi:red-stinger'
    # Long variant names remain visible in the library; CHI's in-game compact
    # label is bounded to 15 characters and always begins with an uppercase.
    unit=dict(id='mech-library:'+slug,name=name,label=fields['chassis'][:15],mass_tons=mass,
              price=mass*350+len(mounts)*500,presentation=source,
              movement=dict(walk=int(fields['walk mp']),jump=int(fields['jump mp'])),engine_heat_sinks=sinks,
              armor={part:int(fields[key+' armor']) for key,part in ARMOR.items()},
              structure=dict(zip(LOCATIONS,(arm,side,leg,3,center,arm,side,leg))),
              actuators={part:sum(bit for bit,label in ((8,'Shoulder'),(4,'Upper Arm Actuator'),
                         (2,'Lower Arm Actuator'),(1,'Hand Actuator')) if label in sections[part])
                         for part in ('left_arm','right_arm')},
              external_heat_sinks=external,loadout=mounts)
    unit['actuators'].update(left_leg=15,right_leg=15)
    return unit, sum(slot.endswith(' (R)') for slots in sections.values() for slot in slots)


def build(source_dir, sources):
    base=json.loads((ROOT/'examples/battletech-demo/content.json').read_text())
    content={k:base[k] for k in ('format','schema_version','rules','services')}
    content.update(package_id='mech-library',content_version='1.0.0',ammunition=[],weapons=[],mechs=[],
                   presentations=[dict(id=s,source=s) for s in ('chi:locust','chi:red-stinger')])
    for record in sources['mechs']:
        raw=(source_dir/record['filename']).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=record['sha256']:
            raise ValueError('Source hash changed: '+record['filename'])
        unit,rear=convert(raw.decode('utf-8'),content)
        assert unit['id']==record['id'] and rear==record['rear_weapons'],record['filename']
        content['mechs'].append(unit)
    return content


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir',type=Path,default=ROOT/'work/library-mech-research')
    parser.add_argument('--output',type=Path,default=CATALOGUE/'units.json')
    args=parser.parse_args()
    content=build(args.source_dir,json.loads((CATALOGUE/'sources.json').read_text()))
    args.output.write_text(json.dumps(content,indent=2)+'\n')
    print(f"Wrote {len(content['mechs'])} library mechs to {args.output}")


if __name__=='__main__':main()
