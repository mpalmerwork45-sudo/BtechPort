"""Retained C4.3 native settings/continuation proofs; original assets stay local."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
from chi_import import ROOT,plain_path,import_campaigns
from editor_model import ProjectDocument,EditorError,encoded
from chi_missions import data,put
from chi_bld import data as scripts,find,put as scripts_put

def configure(document,values,units=None):
    v=data(document);v['parameters'].update(values)
    if units:v.setdefault('units',{}).update(units)
    put(document,v)
def training(document,assignment=4):
    v=scripts(document);p=find(v,'chi:bld-training');end=next(n['id'] for n in p['nodes'] if n['op']=='end')
    back=next(n['id'] for n in p['nodes'] if n['op']=='native' and n['action']==3)
    p['nodes'][1:1]=[dict(id='proof:clear',op='clear'),dict(id='proof:confirm',op='confirm',target='proof:assignment'),dict(id='proof:assignment',op='set',index=0,value=assignment),
        dict(id='proof:loan',op='set',index=2,value=1),dict(id='proof:start',op='native',action='native.start-training-mission'),
        dict(id='proof:outcome',op='set',index=81,value=43),dict(id='proof:wait',op='wait'),dict(id='proof:return',op='jump',target=end if assignment==7 else back)]
    scripts_put(document,v,'Prepare declared training mission entry')
    from chi_editor import set_dialogue
    set_dialogue(document,90,'C4.3 return to the training base.')
def arena(document):
    v=scripts(document);p=find(v,'chi:bld-arena');end=next(n['id'] for n in p['nodes'] if n['op']=='end')
    p['nodes'][1:1]=[dict(id='proof:clear',op='clear'),dict(id='proof:rent',op='native',action='native.prepare-arena-party'),
        dict(id='proof:wait',op='wait'),dict(id='proof:start',op='native',action='native.start-arena-combat'),
        dict(id='proof:outcome',op='set',index=81,value=44),dict(id='proof:wait2',op='wait'),dict(id='proof:end',op='jump',target=end)]
    scripts_put(document,v,'Prepare declared arena entry')
def cache(document):
    v=scripts(document);p=find(v,'chi:bld-entrance');end=next(n['id'] for n in p['nodes'] if n['op']=='end')
    p['nodes'][1:1]=[dict(id='proof:access',op='set',index=80,value=1),dict(id='proof:enter',op='jump',target=end)]
    scripts_put(document,v,'Prepare declared cache access')

def generate(source,output,previous,edited_only=False):
    source=plain_path(source);target=plain_path(output);previous=plain_path(previous)
    if target.exists() or target.is_relative_to(source) or target.is_relative_to(ROOT/'UnBattletech'):raise EditorError('Choose a new evidence directory outside reference trees.')
    target.mkdir();tool=ROOT/'build/btp-project';helper=ROOT/'build/btp-chi-mission-native-tests';bld=ROOT/'build/btp-chi-bld-tests'
    import_campaigns(source,target/'base',validator=tool);records=[]
    def run(exe,args):
        result=subprocess.run([str(exe),*map(str,args)],capture_output=True,text=True,timeout=90)
        records.append(dict(executable=exe.name,args=list(map(str,args)),exit_code=result.returncode,stdout=result.stdout,stderr=result.stderr))
        (target/'evidence.json').write_bytes(encoded(dict(status='running' if not result.returncode else 'failed',records=records)))
        if result.returncode:raise EditorError(result.stdout+result.stderr)
    def edit(name,base,operation):
        folder=target/name;shutil.copytree(base,folder);doc=ProjectDocument(folder,tool);before=doc.files()
        with doc.command('C4.3 mission example'):operation(doc)
        changed=doc.files();doc.undo();assert doc.files()==before;doc.redo();assert doc.files()==changed
        doc.save();assert ProjectDocument(folder,tool).files()==doc.files();return doc
    for profile in ('original','updated'):
        base=target/'base'/profile;run(bld,['--roundtrip',base])
        for fixture in (() if edited_only else ('reference-class-funded','reference-bank','ordinary-training-combat','ordinary-services','ordinary-alternate-services','ordinary-fresh-campaign')):
            run(bld,['--compare',previous/profile,base,ROOT/'tests/fixtures'/(fixture+'.actions'),target/(fixture+'-'+profile+'-linux.btp')])
        def train(d):
            configure(d,{'training.4.start_x':68,'training.4.return_x':70,'training.4.control_prompt':1,'training.4.enemy_count':2,'training.4.pass_on_retreat':1},
                {'training.4.enemy.0':d.content['mechs'][0]['id'] if profile=='updated' else 'native:jenner.0','training.4.enemy.1':'native:commando.0'})
            training(d)
        def invaded(d):configure(d,{'invasion.ruin_after':1,'invasion.escape_min':127});training(d,7)
        def arena_edit(d):
            configure(d,{'arena.spectator_x':72,'arena.guard_count':1,'arena.escape_max':1340,'arena.field_variant':1},{'arena.loan':'native:commando.0'});arena(d)
        def cache_edit(d):
            configure(d,{'cache.access_flag':80,'cache.start_x':8,'cache.terminal.0.color':2,'cache.require_supply':0,'cache.require_password':0,'cache.require_find':0,'cache.hall_x':10,'cache.hall_y':30});cache(d)
        def encounter(d):configure(d,{'encounter.avoid_mask':0,'encounter.mech_slots':0,'encounter.cash_base':40,'encounter.cash_mask':0,'encounter.field_salvage':0,'encounter.mech_salvage':0,'encounter.heal_after':0})
        for name,operation in [('start',lambda d:configure(d,{'start.credits':77,'start.allowance_cap':123,'start.constitution':10,'start.skill.6':2})),('training',train),('invasion',invaded),('quiz',lambda d:configure(d,{'quiz.rounds':4,'quiz.point.0.answer':1})),('arena',arena_edit),('cache',cache_edit),('encounter',encounter)]:
            changed=edit(name+'-'+profile,base,operation);run(helper,['--'+name,changed.root,target/(name+'-'+profile+'-linux.btp')])
    report=dict(status='passed',byte_identical_programs=52,baseline_comparisons=not edited_only,records=records,
        declared_checkpoints=['ordinary doorway fixtures suppress unrelated encounters','training source selects a declared mission before native startup','arena alarm starts from the declared spectator-hit boundary','encounter reward proof declares a victory boundary','cache final prerequisites tested at a declared final-door position'])
    (target/'evidence.json').write_bytes(encoded(report));return report

def replay_windows(output):
    """Use the retained Linux fixtures and compare every final save byte.

    Sequential Wine processes share the isolated test prefix. Normal saves,
    reference directories and the Linux evidence files are never rewritten.
    """
    output=plain_path(output);report=json.loads((output/'evidence.json').read_text())
    if report.get('status')!='passed':raise EditorError('Finish the Linux evidence run first.')
    records=[];pairs=0
    for record in report['records']:
        name=record['executable']
        if name not in ('btp-chi-bld-tests','btp-chi-mission-native-tests'):raise EditorError('Unexpected evidence executable.')
        args=list(record['args']);original=Path(args[-1]) if args[-1].endswith('-linux.btp') else None
        if original:args[-1]=str(original.with_name(original.name.replace('-linux.btp','-windows.btp')))
        result=subprocess.run([sys.executable,str(ROOT/'tools/windows_check.py'),str(ROOT/'build-windows'/(name+'.exe')),*args],capture_output=True,text=True,timeout=120)
        entry=dict(executable=name,args=args,exit_code=result.returncode,stdout=result.stdout,stderr=result.stderr)
        records.append(entry)
        if original and not result.returncode:
            entry['identical_save']=original.read_bytes()==Path(args[-1]).read_bytes()
            if not entry['identical_save']:raise EditorError('Linux/Windows held save differs: '+str(original))
            pairs+=1
        (output/'windows-evidence.json').write_bytes(encoded(dict(status='running' if not result.returncode else 'failed',identical_saves=pairs,records=records)))
        if result.returncode:raise EditorError(result.stdout+result.stderr)
        print('PASS Windows: '+name+' '+args[0]+(' / '+args[1] if len(args)>1 else ''),flush=True)
    (output/'windows-evidence.json').write_bytes(encoded(dict(status='passed',identical_saves=pairs,records=records)))

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--data',type=Path,default=ROOT/'Original DOS');p.add_argument('--output',type=Path,required=True);p.add_argument('--previous',type=Path)
    p.add_argument('--edited-only',action='store_true',help='Run changed-content journeys without repeating baseline comparisons.')
    p.add_argument('--windows',action='store_true',help='Replay an existing successful evidence run under isolated Wine and compare saved bytes.')
    a=p.parse_args()
    if a.windows:replay_windows(a.output)
    else:
        if not a.previous:p.error('--previous is required for a new evidence run')
        generate(a.data,a.output,a.previous,a.edited_only)
    print('Mission evidence passed: '+str(a.output/('windows-evidence.json' if a.windows else 'evidence.json')))
