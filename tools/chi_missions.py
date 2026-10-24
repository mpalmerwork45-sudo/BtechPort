"""Shared typed mission/campaign editing for imported native CHI projects."""
from __future__ import annotations
import argparse
import copy
import json
from pathlib import Path
from editor_model import EditorError,encoded

FILE='chi-missions.json'
FORMAT='btp-chi-missions-v1'
def catalogue(document):
    from chi_resources import tool
    return tool(document,['chi-missions'])
def data(document):
    if document.manifest.get('requires')!='chi-local-dos-1.03':raise EditorError('Native mission settings require an imported CHI campaign.')
    return json.loads(document.metadata.get(FILE,encoded(dict(format=FORMAT,schema_version=1,parameters={},units={}))))
def prepare(catalog):
    return dict(format=FORMAT,schema_version=1,parameters={p['id']:p['value'] for p in catalog['parameters']},units={})
def enable(document):
    if document.manifest.get('chi_missions'):return
    data(document);value=prepare(catalogue(document))
    with document.command('Enable native mission editing'):
        manifest=copy.deepcopy(document.manifest);manifest['chi_missions']=FILE
        meta=dict(document.metadata);meta[FILE]=encoded(value)
        document.replace_all(document.content,document.adventure,document.art,manifest,meta);document.validate()
def put(document,value):
    with document.command('Edit native mission settings'):
        enable(document);meta=dict(document.metadata);meta[FILE]=encoded(value)
        document.replace_all(document.content,document.adventure,document.art,document.manifest,meta);document.validate()
def update(document,parameter,value):
    with document.command('Edit native mission parameter'):
        enable(document);v=data(document);v['parameters'][parameter]=value;put(document,v)
def unit(document,role,definition):
    with document.command('Choose mission unit'):
        enable(document);v=data(document);v.setdefault('units',{})[role]=definition;put(document,v)
def main():
    from editor_model import ProjectDocument
    from app_runtime import binary
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--project',type=Path,required=True)
    commands=p.add_subparsers(dest='command',required=True);commands.add_parser('enable');commands.add_parser('list')
    edit=commands.add_parser('set');edit.add_argument('parameter');edit.add_argument('value',type=int)
    u=commands.add_parser('unit');u.add_argument('role');u.add_argument('definition',help='Roster ID, native:kind.index, or empty for default')
    a=p.parse_args()
    try:
        d=ProjectDocument(a.project,binary('btp-project'))
        if a.command=='list':print(json.dumps(catalogue(d),indent=2));return
        if a.command=='enable':enable(d)
        elif a.command=='set':update(d,a.parameter,a.value)
        else:unit(d,a.role,a.definition)
        print(d.save())
    except (EditorError,OSError,ValueError) as e:p.exit(1,str(e)+'\n')
if __name__=='__main__':main()
