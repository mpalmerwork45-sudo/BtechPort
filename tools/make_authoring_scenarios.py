#!/usr/bin/env python3
"""Record ordinary Relay Contract branches and one explicit low-funds fixture."""
import copy
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'examples/authoring/scenarios'


def scenario(steps):
    return dict(format='btp-author-scenario-v1',max_ticks=60000,seed=11223583,steps=steps)


def recipes():
    legacy=json.loads((ROOT/'examples/authoring/relay-contract.scenario.json').read_text())
    battle=next(i for i,s in enumerate(legacy['steps']) if s['op']=='battle')
    win=copy.deepcopy(legacy['steps'])
    win[battle:battle+1]=[dict(op='battle',control='computer',until_round=1),
        dict(op='assert',phase='battle',battle_outcome='pending',round_min=1),dict(op='checkpoint'),
        dict(op='battle',control='computer'),dict(op='assert',battle_outcome='win',owned_mechs=2,alive_party=2)]
    accept=[dict(op='pages'),dict(op='choose',label='Accept contract'),dict(op='pages')]
    approach=accept+[dict(op='walk',entrance='relay:south-road'),dict(op='enter'),
        dict(op='walk',entrance='relay:raider-marker'),dict(op='enter')]
    engaged=approach+[dict(op='choose',label='Engage')]
    cases={
        'victory':scenario(win),
        'decline':scenario([dict(op='pages'),dict(op='choose',label='Decide later'),
            dict(op='assert',phase='exploration',credits=5000,flag='relay:accepted',value=0,objective='relay:contract',status='inactive'),dict(op='checkpoint')]),
        'cancel':scenario([dict(op='pages'),dict(op='input',action='cancel'),
            dict(op='assert',phase='exploration',flag='relay:accepted',value=0),dict(op='checkpoint')]),
        'door-cancel':scenario(accept+[dict(op='walk',entrance='relay:workshop'),dict(op='checkpoint'),
            dict(op='assert',phase='entry'),dict(op='input',action='cancel'),
            dict(op='assert',phase='exploration',credits=5000),dict(op='checkpoint')]),
        'encounter-decline':scenario(approach+[dict(op='choose',label='Withdraw'),
            dict(op='assert',phase='exploration',map='relay:field',flag='relay:cleared',value=0,battle_outcome='none'),
            dict(op='checkpoint'),dict(op='walk',entrance='relay:depot-road'),dict(op='enter'),dict(op='assert',map='relay:town')]),
        'retreat':scenario(engaged+[dict(op='battle',control='retreat'),
            dict(op='assert',battle_outcome='retreat',event='relay:retreated',round_max=0,credits=5000),
            dict(op='checkpoint'),dict(op='pages'),dict(op='assert',map='relay:field',flag='relay:cleared',value=0),
            dict(op='walk',entrance='relay:depot-road'),dict(op='enter'),dict(op='assert',map='relay:town'),dict(op='checkpoint')]),
        'defeat':scenario(engaged+[dict(op='battle',control='hold'),
            dict(op='assert',battle_outcome='loss',event='relay:lost',credits=5000),dict(op='checkpoint'),dict(op='pages'),
            dict(op='assert',map='relay:town',flag='relay:cleared',value=0,objective='relay:contract',status='active'),dict(op='checkpoint')]),
        'unaffordable':scenario(engaged+[dict(op='battle',control='computer'),dict(op='pages'),
            dict(op='assert',battle_outcome='win',credits=0),dict(op='walk',entrance='relay:depot-road'),dict(op='enter'),
            dict(op='walk',entrance='relay:workshop'),dict(op='enter'),dict(op='choose',label='Repair lance - 100'),
            dict(op='assert',event='relay:no-funds',phase='text',credits=0),dict(op='checkpoint'),dict(op='pages'),
            dict(op='choose',label='Leave'),dict(op='walk',entrance='relay:office'),dict(op='enter'),dict(op='pages'),
            dict(op='assert',credits=4000,objective='relay:contract',status='complete'),dict(op='checkpoint')]),
    }
    suite=dict(format='btp-author-suite-v1',max_seconds=120,cases=[
        dict(id=name,file=name+'.json',seeds=[11223583,42,1979] if name=='victory' else [11223583],
             tags=({'victory':['victory','mid-battle-save','reward-once','repeat-visit','completion'],
                    'unaffordable':['unaffordable-service','validated-fixture','reward']} .get(name,[name])),
             **({'fixture':'low-funds.commands.json'} if name=='unaffordable' else {})) for name in cases])
    fixture=dict(api_version=1,request_id='relay-low-funds-fixture-v1',project_id='relay-contract',expected_revision='new',
        label='Controlled fixture: start without credits',scope=['adventure.start'],operations=[dict(op='start.set',changes={'credits':0})])
    return cases,suite,fixture


def main():
    cases,suite,fixture=recipes();FOLDER.mkdir(parents=True,exist_ok=True)
    for name,value in {**{n+'.json':v for n,v in cases.items()},'relay.suite.json':suite,'low-funds.commands.json':fixture}.items():
        (FOLDER/name).write_text(json.dumps(value,indent=2)+'\n')
    print('Recorded 8 route cases, 10 runs, including three victory seeds and one declared low-funds fixture.')


if __name__=='__main__':main()
