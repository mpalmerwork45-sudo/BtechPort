"""Shared CHI service authoring; native catalogue/validator own runtime semantics."""
from __future__ import annotations
import argparse
import copy
import json
import re
from pathlib import Path
from editor_model import EditorError,encoded

FILE='chi-services.json'
FORMAT='btp-chi-services-v1'

def catalogue(document):
    from chi_resources import tool
    return tool(document,['chi-services'])

def data(document):
    if document.manifest.get('requires')!='chi-local-dos-1.03':raise EditorError('Native services require an imported CHI campaign.')
    return json.loads(document.metadata.get(FILE,encoded(dict(format=FORMAT,schema_version=1,parameters={}))))

def prepare(files,catalog):
    """Bind only unmodified original operands/text; custom text stays authoritative.

    Numeric anchors and currency amounts are factual compatibility metadata.
    The actual text is read exclusively from the user's private import.
    """
    from chi_bld import extract,decode
    from chi_editor import native_dialogue
    manifest=json.loads(files['project.json']);campaign=json.loads(files['campaign.json'])
    sources=json.loads(files[manifest['chi_scripts']]) if manifest.get('chi_scripts') else extract(files)
    params={p['id']:p['value'] for p in catalog['parameters']}
    mapping={3:dict(zip(('03ae','0507','0609','06f3','0847','092c','0b5c','0c86','0d85','1015','11d1'),[f'weapons.price.{i}' for i in range(1,12)])),
             4:dict(zip(('02c1','03f1','0512','0674','07c6'),[f'armour.price.{i}' for i in range(1,6)]))}
    money={8:{150:'garage.fee'},9:{25:'medical.facility_fee',75:'medical.kit_price',375:'medical.advanced_kit_price'},10:{250:'arena.rental_fee',500:'arena.prize'},12:{35:'clothes.price'},16:{5:'cinema.funds'},17:{7000:'inventor.first_price',6000:'inventor.second_price'}}
    textmap={**money,5:{500:'apprentice.technician'},9:{**money[9],500:'apprentice.medical',**{params[f'medical.price.{i}']:f'medical.price.{i}' for i in range(1,8)}}}
    currency=re.compile(r'(?<![0-9])([0-9][0-9,]*)(?= C-bills)')
    def replace(text,choices):
        def sub(match):
            key=choices.get(int(match[1].replace(',','')))
            return '{service:'+key+(':comma' if ',' in match[1] else '')+'}' if key else match[0]
        return currency.sub(sub,text)
    for p in sources['programs']:
        originals={n['id']:n for n in decode(files['chi/'+p['resource']],p['resource'][:-4])['nodes']}
        for n in p['nodes']:
            original=originals.get(n['id'])
            if not original:continue
            if n['op']=='text' and n.get('text')==original.get('text'):
                key=mapping.get(p['building'],{}).get(n['id'].rsplit('-',1)[-1])
                choices={params[key]:key} if key else textmap.get(p['building'],{})
                n['text']=replace(n['text'],choices)
            if n['op'] in ('if_money','spend_money','add_money') and n.get('amount')==original.get('amount'):
                key=money.get(p['building'],{}).get(n['amount'])
                if key:n['amount']='{service:'+key+'}'
    # Native fragments remain in the existing dialogue override editor. Expand
    # at load time so quotations and actual payment always share one value.
    from types import SimpleNamespace
    base=native_dialogue(SimpleNamespace(manifest=manifest,metadata={'campaign.json':files['campaign.json']},snapshot=files))
    overrides={v['index']:v for v in campaign['dialogue_overrides']}
    for index,key,old in [(241,'repair.heatsink',800),(245,'repair.weapon',300),(250,'repair.jump',200),(253,'repair.jump',200)]:
        if index not in overrides:overrides[index]=dict(index=index,text=replace(base[index],{old:key}))
    campaign['dialogue_overrides']=sorted(overrides.values(),key=lambda v:v['index'])
    return dict(parameters=dict(format=FORMAT,schema_version=1,parameters=params),scripts=sources,campaign=campaign)

def enable(document):
    if document.manifest.get('chi_services'):return
    data(document);value=prepare(document.files(),catalogue(document))
    with document.command('Enable native service editing'):
        manifest=copy.deepcopy(document.manifest);manifest.update(chi_services=FILE,chi_scripts='chi-scripts.json')
        meta=dict(document.metadata);meta[FILE]=encoded(value['parameters']);meta['chi-scripts.json']=encoded(value['scripts']);meta['campaign.json']=encoded(value['campaign'])
        document.replace_all(document.content,document.adventure,document.art,manifest,meta);document.validate()

def put(document,value):
    with document.command('Edit native services'):
        enable(document);meta=dict(document.metadata);meta[FILE]=encoded(value)
        document.replace_all(document.content,document.adventure,document.art,document.manifest,meta);document.validate()

def update(document,parameter,value):
    with document.command('Edit native service parameter'):
        enable(document);settings=data(document);settings['parameters'][parameter]=value;put(document,settings)

def stock(document,units):
    with document.command('Edit native broker inventory'):
        enable(document);settings=data(document)
        if units is None:settings.pop('broker_stock',None)
        else:settings['broker_stock']=copy.deepcopy(units)
        put(document,settings)

def main():
    from editor_model import ProjectDocument
    from app_runtime import binary
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--project',type=Path,required=True)
    commands=p.add_subparsers(dest='command',required=True);commands.add_parser('enable');commands.add_parser('list')
    edit=commands.add_parser('set');edit.add_argument('parameter');edit.add_argument('value',type=int)
    b=commands.add_parser('stock');b.add_argument('units',nargs='*');b.add_argument('--all',action='store_true')
    a=p.parse_args()
    try:
        d=ProjectDocument(a.project,binary('btp-project'))
        if a.command=='list':print(json.dumps(catalogue(d),indent=2));return
        if a.command=='enable':enable(d)
        elif a.command=='set':update(d,a.parameter,a.value)
        else:stock(d,None if a.all else a.units)
        print(d.save())
    except (EditorError,OSError,ValueError) as e:p.exit(1,str(e)+'\n')

if __name__=='__main__':main()
