#!/usr/bin/env python3
"""Build the independently drawn vehicle proving ground and two-planet sample."""
import copy
import json
from pathlib import Path
from world_editing import create_world,assign_city,upgrade

ROOT=Path(__file__).resolve().parents[1]


def main():
    target=ROOT/'examples/vehicle-lab';target.mkdir(exist_ok=True)
    def read(path):return json.loads((ROOT/path).read_text())
    def write(name,value):(target/name).write_text(json.dumps(value,indent=2)+'\n')
    c=read('content/catalogues/vehicles/units.json');c.update(format='btp-content-v1',schema_version=1,package_id='vehicle-lab',content_version='1.0.0')
    base=read('examples/beacon-demo/content.json');c['rules']=base['rules'];c['services']=base['services'];write('content.json',c)
    write('graphics.json',read('content/catalogues/vehicles/graphics.json'))
    write('presentation.json',read('examples/beacon-demo/presentation.json'))
    manifest=read('examples/beacon-demo/project.json');manifest.update(package_id='vehicle-lab',title='BattleTech: Vehicle proving ground',scripts=[],graphics='graphics.json');write('project.json',manifest)
    a=read('examples/beacon-demo/adventure.json');a['events']=[];a['flags']=[];a['shops']=[dict(id='lab:stock',stock=[m['id'] for m in c['mechs']])]
    a['people']=copy.deepcopy(a['people'][:3])
    while len(a['people'])<3:
        p=copy.deepcopy(a['people'][0]);p.update(id='lab:scout',identity='actor:2');a['people'].append(p)
    for index,p in enumerate(a['people']):p['name']=['Captain','Gunner','Scout'][index]
    a['maps']=[]
    for identity,name,origin in [('lab:yard','New Avalon test yard',[64,64]),('lab:range','Dustball test range',[64,64])]:
        grid=[list('.'*32) for _ in range(32)]
        for y in range(5,9):
            for x in range(6,11):grid[y][x]='#'
        grid[9][8]='D'
        a['maps'].append(dict(id=identity,name=name,origin=origin,rows=[''.join(r) for r in grid],overlays=[],entrances=[]))
    a['maps'][0]['entrances']=[dict(id='lab:depot-door',name='Vehicle depot',at=[16,20],event='lab:shop'),dict(id='lab:shuttle-door',name='Shuttle to Dustball',at=[32,20],event='lab:travel')]
    a['maps'][1]['entrances']=[dict(id='lab:range-door',name='Start live-fire test',at=[16,20],event='lab:fight'),dict(id='lab:return-door',name='Shuttle to New Avalon',at=[32,20],event='lab:return')]
    a['encounters']=[dict(id='lab:trial',map='lab:range',party_at=[24,38],enemies=[dict(kind='mech',definition='vehicles:scorpion',at=[42,38]),dict(kind='mech',definition='vehicles:vedette',at=[44,44])])]
    a['events']=[dict(id='lab:end',op='end'),dict(id='lab:welcome',op='say',text='Vehicle proving ground. Your patrol has a Patton, Pegasus and Skulker. The depot stocks all ten vehicles. Take the shuttle east of the depot to the test range on Dustball.',next='lab:end'),
        dict(id='lab:shop',op='shop',shop='lab:stock',next='lab:end'),dict(id='lab:travel',op='transfer',map='lab:range',at=[24,38],next='lab:arrival',failure='lab:blocked'),
        dict(id='lab:arrival',op='say',text='Dustball test range. Enter the control building for a live-fire exercise. The shuttle returns to New Avalon. Each planet retains its own explored map.',next='lab:end'),
        dict(id='lab:return',op='transfer',map='lab:yard',at=[24,38],next='lab:end',failure='lab:blocked'),
        dict(id='lab:blocked',op='say',text='The destination formation is blocked. Clear the landing area in the editor.',next='lab:end'),
        dict(id='lab:fight',op='battle',encounter='lab:trial',win='lab:won',loss='lab:lost',flee='lab:fled',failure='lab:blocked'),
        dict(id='lab:won',op='say',text='Exercise complete. The opposition has been defeated. Return to the depot to try another vehicle.',next='lab:end'),
        dict(id='lab:lost',op='say',text='Your patrol was defeated.',next='lab:end'),dict(id='lab:fled',op='say',text='Exercise ended. Your patrol withdrew.',next='lab:end')]
    a['start']=dict(map='lab:yard',at=[24,38],event='lab:welcome',credits=200000,party=[dict(person=p['id'],mech=m) for p,m in zip(a['people'],['vehicles:patton','vehicles:pegasus','vehicles:skulker'])])
    upgrade(a);earth=create_world(a,'lab',32,32,'New Avalon');assign_city(a,'lab:yard',world_id=earth)
    dust=create_world(a,'lab',32,32,'Dustball');assign_city(a,'lab:range',world_id=dust)
    # Different terrain palettes make changing planets immediately visible.
    from world_editing import add_jigsaw,get_world
    # A dusty-looking clear tile allows the wheeled scout to leave the yard.
    # Terrain behavior and imagery are deliberately independent properties.
    tile=copy.deepcopy(next(t for t in a['tiles'] if t['terrain']=='rough'));tile.update(id='lab:dust',terrain='clear');a['tiles'].append(tile)
    piece=add_jigsaw(a,'lab',[[tile['id']]*8 for _ in range(8)],'Dustball soil')
    get_world(a,dust)['pieces']=[[piece]*32 for _ in range(32)]
    write('adventure.json',a)


if __name__=='__main__':main()
