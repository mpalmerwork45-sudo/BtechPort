"""Private C4.1 edit fixtures and native continuations, never public assets."""
import argparse
import copy
import json
from pathlib import Path
import shutil
import subprocess
from chi_import import ROOT,plain_path,import_campaigns
from chi_bld import data,find,put,compiled
from editor_model import ProjectDocument,EditorError,encoded


def relocate(document):
    value=data(document)
    for p in value['programs']:
        text=next((n for n in p['nodes'] if n['op']=='text'),None)
        if text:text['text']+=' '
        nodes=[]
        for n in p['nodes']:
            nodes.append(n)
            if (p['building']==0 and n.get('action') in (3,43)) or (p['building']==1 and n.get('action') in (4,5)):
                nodes.append(dict(id='edit:after-'+n['id'].replace(':','-'),op='set',index=99,value=0))
        p['nodes']=nodes
    put(document,value,'Lengthen dialogue and insert native resume instructions')


def story_setup(document):
    value=data(document);p=find(value,'chi:bld-armor');end=next(n['id'] for n in p['nodes'] if n['op']=='end')
    prefix=[dict(id='edit:clear',op='clear'),dict(id='edit:text',op='text',text='Before the edit.'),dict(id='edit:wait',op='wait'),
        dict(id='edit:zero',op='set',index=80,value=0),dict(id='edit:true',op='set',index=83,value=1),
        dict(id='edit:condition',op='if',index=80,target='edit:hop'),dict(id='edit:fallback',op='jump',target='edit:fail'),
        dict(id='edit:hop',op='jump',target='edit:fail'),dict(id='edit:cash',op='native',action=12),
        dict(id='edit:menu',op='menu',menu=24,targets=['edit:fail','edit:fail']),
        dict(id='edit:pass',op='set',index=81,value=7),dict(id='edit:done',op='jump',target=end),
        dict(id='edit:fail',op='set',index=81,value=99),dict(id='edit:failed',op='jump',target=end)]
    p['nodes'][1:1]=prefix;put(document,value,'Prepare native BLD editing fixture')


def story_request(document):
    from authoring_service import revision
    edits=[('edit:text',dict(text='C4.1 edited building dialogue.\r')),
           ('edit:condition',dict(index=83)),('edit:hop',dict(target='edit:cash')),
           ('edit:menu',dict(targets=['edit:pass','edit:fail'])),('edit:cash',dict(action=10))]
    return dict(api_version=1,request_id='c41-story-edit',project_id=document.manifest['package_id'],
        expected_revision=revision(document),label='Edit native BLD dialogue/control flow',scope=['chi.programs/chi:bld-armor'],
        operations=[dict(op='bld.update',program='chi:bld-armor',id=label,changes=changes) for label,changes in edits])


def generate(source,output):
    from authoring_service import apply_batch
    target=plain_path(output);source=plain_path(source)
    if target.exists() or target.is_relative_to(source) or target.is_relative_to(ROOT/'UnBattletech'):
        raise EditorError('Choose a new evidence directory outside reference/source directories.')
    target.mkdir();tool=ROOT/'build/btp-project';helper=ROOT/'build/btp-chi-bld-tests'
    import_campaigns(source,target/'base',validator=tool);records=[]
    def run(args):
        r=subprocess.run([str(helper),*map(str,args)],capture_output=True,text=True,timeout=45)
        if r.returncode:raise EditorError(r.stdout+r.stderr)
        return r.stdout.strip()
    def edit(name,profile,operation):
        folder=target/name;shutil.copytree(target/'base'/profile,folder);doc=ProjectDocument(folder,tool);before=doc.files()
        with doc.command('C4.1 example'):operation(doc)
        changed=doc.files();doc.undo();assert {k:v for k,v in before.items() if k!='AUTHORING.json'}=={k:v for k,v in doc.files().items() if k!='AUTHORING.json'}
        doc.redo();assert changed==doc.files()
        doc.save();assert ProjectDocument(folder,tool).files()==doc.files();return doc
    for profile in ('original','updated'):
        doc=ProjectDocument(target/'base'/profile,tool)
        for p in data(doc)['programs']:
            result=compiled(doc,p['id']);assert bytes.fromhex(result['encrypted'])==doc.files()['chi/'+p['resource']]
        changed=edit('relocated-'+profile,profile,relocate)
        for fixture in ('reference-class-funded','reference-bank','ordinary-training-combat','ordinary-services','ordinary-alternate-services'):
            text=run(['--compare',doc.root,changed.root,ROOT/'tests/fixtures'/(fixture+'.actions'),target/(fixture+'-'+profile+'.btp')])
            records.append(dict(profile=profile,fixture=fixture,result=text))
    def setup(d):story_setup(d);apply_batch(d,story_request(d))
    doc=edit('story','original',setup)
    story=run(['--story',doc.root,target/'story-held.btp'])
    report=dict(status='passed',byte_identical_programs=52,relocated=records,story=story)
    (target/'evidence.json').write_bytes(encoded(report));return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--data',type=Path,default=ROOT/'Original DOS');p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=generate(a.data,a.output);print(json.dumps(dict(status=r['status'],evidence=str(a.output/'evidence.json'))))
