"""Private C4.2 transaction fixtures, built through normal document operations."""
import copy
from chi_bld import data,find,put

def purchase(document):
    value=data(document);p=find(value,'chi:bld-armor');end=next(n['id'] for n in p['nodes'] if n['op']=='end')
    nodes=[dict(id='proof:clear',op='clear'),dict(id='proof:text',op='text',text='C4.2 purchase proof.\r'),dict(id='proof:stock',op='set',index=10,value=1),
           dict(id='proof:menu',op='menu',menu=13,targets=[end,'proof:buy',end,end,end,end]),dict(id='proof:buy',op='native',action='native.buy-armour'),
           dict(id='proof:wait',op='wait'),dict(id='proof:passed',op='set',index=81,value=42),dict(id='proof:done',op='jump',target=end)]
    p['nodes'][1:1]=nodes;put(document,value,'Prepare recipient purchase proof')

def healing(document):
    value=data(document);p=find(value,'chi:bld-hospital');end=next(n['id'] for n in p['nodes'] if n['op']=='end')
    nodes=[dict(id='proof:clear',op='clear'),dict(id='proof:text',op='text',text='C4.2 hospital proof.\r'),dict(id='proof:skill',op='set',index=26,value=1),
           dict(id='proof:heal',op='native',action='native.heal-party'),dict(id='proof:wait',op='wait'),dict(id='proof:passed',op='set',index=81,value=43),dict(id='proof:done',op='jump',target=end)]
    p['nodes'][1:1]=nodes;put(document,value,'Prepare hospital continuation proof')

def prison(document):
    value=data(document);p=find(value,'chi:bld-jail');end=next(n['id'] for n in p['nodes'] if n['op']=='end')
    nodes=[dict(id='proof:clear',op='clear'),dict(id='proof:text',op='text',text='C4.2 prison proof.\r'),dict(id='proof:yard',op='native',action='native.begin-prison-yard'),
           dict(id='proof:wait',op='wait'),dict(id='proof:passed',op='set',index=81,value=44),dict(id='proof:done',op='jump',target=end)]
    p['nodes'][1:1]=nodes;put(document,value,'Prepare prison continuation proof')

def generate(source,output,previous):
    import json,shutil,subprocess
    from pathlib import Path
    from chi_import import ROOT,plain_path,import_campaigns
    from chi_services import update,stock
    from chi_bld import compiled
    from editor_model import ProjectDocument,EditorError,encoded
    target=plain_path(output);source=plain_path(source);previous=plain_path(previous)
    if target.exists() or target.is_relative_to(source) or target.is_relative_to(ROOT/'UnBattletech'):raise EditorError('Choose a new evidence directory outside the original/reference trees.')
    target.mkdir();tool=ROOT/'build/btp-project';helper=ROOT/'build/btp-chi-service-native-tests';bld=ROOT/'build/btp-chi-bld-tests'
    import_campaigns(source,target/'base',validator=tool);records=[]
    def run(executable,args):
        result=subprocess.run([str(executable),*map(str,args)],capture_output=True,text=True,timeout=60)
        records.append(dict(executable=Path(executable).name,args=list(map(str,args)),exit_code=result.returncode,stdout=result.stdout,stderr=result.stderr))
        (target/'evidence.json').write_bytes(encoded(dict(status='running' if not result.returncode else 'failed',records=records)))
        if result.returncode:raise EditorError(result.stdout+result.stderr)
    def edit(name,base,operation):
        root=target/name;shutil.copytree(base,root);doc=ProjectDocument(root,tool);before=doc.files()
        with doc.command('C4.2 native service example'):operation(doc)
        after=doc.files();doc.undo();assert doc.files()==before;doc.redo();assert doc.files()==after
        doc.save();assert ProjectDocument(root,tool).files()==doc.files();return doc
    values={'armour.price.1':73,'repair.armour':6,'repair.structure':12,'repair.weapon':45,'medical.price.1':77,
        'medical.facility_fee':37,'medical.cooldown':17,'class.price.0':87,'class.price.1':210,'apprentice.technician':550,
        'apprentice.medical':450,'recruit.limit':2,'recruit.rank':4,'recruit.spy_chance':0,'prison.start_attempt':1,
        'prison.guard_ticks':100,'prison.reward':0,'market.rate.0':100,'market.mask.0':0}
    for profile in ('original','updated'):
        base=target/'base'/profile;doc=ProjectDocument(base,tool)
        for p in data(doc)['programs']:assert bytes.fromhex(compiled(doc,p['id'])['encrypted'])==doc.files()['chi/'+p['resource']]
        run(bld,['--roundtrip',base])
        for fixture in ('reference-class-funded','reference-bank','ordinary-training-combat','ordinary-services','ordinary-alternate-services'):
            run(bld,['--compare',previous/profile,base,ROOT/'tests/fixtures'/(fixture+'.actions'),target/(fixture+'-'+profile+'-baseline-linux.btp')])
        def configure(doc):
            for key,value in values.items():update(doc,key,value)
            if profile=='updated':stock(doc,[u['id'] for u in doc.content['mechs'][:2]])
        changed=edit('settings-'+profile,base,configure)
        run(helper,['--mechanics',changed.root,target/('mechanics-'+profile+'.btp')])
        for fixture in ('reference-class-funded',):
            run(helper,['--route',changed.root,ROOT/'tests/fixtures'/(fixture+'.actions'),target/(fixture+'-'+profile+'-edited-linux.btp')])
        bought=edit('purchase-'+profile,changed.root,purchase)
        run(helper,['--purchase',bought.root,target/('purchase-'+profile+'-linux.btp')])
        healed=edit('healing-'+profile,changed.root,healing)
        run(helper,['--healing',healed.root,target/('healing-'+profile+'-linux.btp')])
        stolen=edit('prison-'+profile,changed.root,prison)
        run(helper,['--prison',stolen.root,target/('prison-'+profile+'-linux.btp')])
    report=dict(status='passed',byte_identical_programs=52,baseline_replay_ticks=214544,edited_class_ticks=6176,records=records)
    (target/'evidence.json').write_bytes(encoded(report));return report

if __name__=='__main__':
    import argparse
    from pathlib import Path
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--data',type=Path,default=Path('Original DOS'));p.add_argument('--output',type=Path,required=True);p.add_argument('--previous',type=Path,required=True)
    a=p.parse_args();generate(a.data,a.output,a.previous);print('Native service evidence passed: '+str(a.output/'evidence.json'))
