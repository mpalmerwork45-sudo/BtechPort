"""Compare a saved continuation with the same ordinary-input journey in full.

The default world journey uses only included sample art. --cairn additionally
exercises a late contract and an in-progress battle using locally supplied CHI
resources. Every save is produced by the player; no state is patched.
"""
import copy
import json
from pathlib import Path
from authoring_scenarios import run,pin_checkpoint
from editor_model import ProjectDocument,encoded
from world_route_demo import create,journey

ROOT=Path(__file__).resolve().parents[1]


def compare(doc,scenario,split,output,runner,settings=None):
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    full=copy.deepcopy(scenario)
    full['steps'].insert(split,dict(op='checkpoint',name='continuation'))
    (output/'full.json').write_bytes(encoded(full))
    complete=run(doc,full,output/'full',runner,settings)
    if complete['status']!='passed':raise RuntimeError('Full journey failed: '+str(complete))
    saved=output/'full/checkpoint-continuation.btp'
    suffix=dict(format='btp-author-scenario-v1',checkpoint=dict(pin_checkpoint(saved),file='full/'+saved.name),steps=scenario['steps'][split:])
    (output/'continue.json').write_bytes(encoded(suffix))
    resumed=run(doc,suffix,output/'resumed',runner,settings,base_dir=output)
    if resumed['status']!='passed':raise RuntimeError('Continuation failed: '+str(resumed))
    a,b=complete['result'],resumed['result']
    if (output/'full'/a['save']).read_bytes()!=(output/'resumed'/b['save']).read_bytes():
        raise RuntimeError('Full journey and continuation save bytes differ.')
    full_actions=(output/'full/replay.actions').read_text().splitlines()
    resumed_actions=(output/'resumed/replay.actions').read_text().splitlines()
    if full_actions[b['start_tick']-a['start_tick']:]!=resumed_actions:
        raise RuntimeError('Continuation did not use the same ordinary input suffix.')
    evidence=dict(status='passed',full_ticks=a['ticks'],resumed_ticks=b['ticks'],skipped_ticks=a['ticks']-b['ticks'],
        exact_save_equality=True,exact_input_suffix=True,full_report=complete['report'],resumed_report=resumed['report'])
    (output/'comparison.json').write_bytes(encoded(evidence));return evidence


def main():
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--cairn',action='store_true');p.add_argument('--windows',action='store_true',help='Compare saved continuations with the Windows runner under isolated Wine')
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    doc=create(args.output/'game',ROOT/'build/btp-project');route=journey()
    split=next(i for i,s in enumerate(route['steps']) if s.get('world')=='survey:boreal' and s['op']=='walk')
    results=dict(world=compare(doc,route,split,args.output/'world',ROOT/'build/btp-author-playtest'))
    def windows(name,doc,settings=None):
        if not args.windows:return
        from world_route_demo import windows_check
        scenario=json.loads((args.output/name/'continue.json').read_bytes())
        results[name]['windows']=windows_check(doc,scenario,args.output/name/'windows',dict(report=results[name]['resumed_report']),settings)
    windows('world',doc)
    if args.cairn:
        settings={k:str(ROOT/v) for k,v in [('data','Original DOS'),('dialogue-data','work/talk-data.bin'),
            ('combat-data','work/combat-data.bin'),('world-data','work/world-data.bin')]}
        doc=ProjectDocument(ROOT/'examples/cairn-passage',ROOT/'build/btp-project')
        for name,file,op in [('contract','full-contract.json',lambda s:s.get('label')=='Begin escort'),
                             ('battle','defence.json',lambda s:s.get('until_round')==3)]:
            route=json.loads((ROOT/'examples/authoring/cairn'/file).read_bytes())
            split=next(i for i,s in enumerate(route['steps']) if op(s))
            results[name]=compare(doc,route,split,args.output/name,ROOT/'build/btp-author-playtest',settings)
            windows(name,doc,settings)
    (args.output/'report.json').write_bytes(encoded(results));print(json.dumps(results,indent=2))


if __name__=='__main__':main()
