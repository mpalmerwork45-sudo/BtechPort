#!/usr/bin/env python3
"""Reproduce the AI6a extraction example through the normal command API."""
import argparse
import copy
import json
from pathlib import Path
from authoring_service import apply_batch,revision
from editor_model import create_project,encoded

ROOT=Path(__file__).resolve().parents[1]


def adventure():
    def identity(value):return 'recovery:'+value
    def event(name,op,**values):return dict(id=identity(name),op=op,**values)
    end=identity('end');failure=identity('error')
    def variable(name,key,action,value,next=end,once=0):
        return event(name,'variable',variable=identity(key),action=action,value=value,once=once,next=next,failure=failure)
    def objective(name,key,state,next=end):
        return event(name,'objective',objective=identity(key),state=state,next=next,failure=failure)
    def condition(kind,key,value,compare='eq'):return dict(kind=kind,id=identity(key),compare=compare,value=value)
    def check(name,conditions,yes,no=end):
        return event(name,'check',match='all',conditions=conditions,then=identity(yes),**{'else':no})
    events=[
        event('end','end'),
        event('briefing','say',portrait='training',text='Argent Recovery. Two data caches lie east along the road. Survey the relay north of the road, then return to the western landing pad. Your Phoenix Hawk and Trebuchet can challenge the raider in the east. The southern pad abandons the contract.',next=end),
        event('error','say',text='Mission command rejected. No counter or terminal objective was changed.',next=end),
        variable('collect-west','data','add',1,identity('count-data'),1),
        variable('collect-east','data','add',1,identity('count-data'),1),
        check('count-data',[condition('variable','data',2)],'collected',identity('one-cache')),
        objective('collected','collect','complete',identity('two-caches')),
        event('one-cache','say',text='First cache uploaded. One more remains along the road to the east.',next=end),
        event('two-caches','say',text='Both caches secured. Survey the northern relay, then bring the data to the western pad.',next=end),
        variable('survey','surveyed','set',1,identity('survey-complete'),1),
        objective('survey-complete','survey','complete',identity('survey-message')),
        event('survey-message','say',text='Relay survey complete. The landing pad can now authenticate both data caches.',next=end),
        variable('pad-enter','visits','add',1,identity('extract-check')),
        variable('pad-leave','departures','add',1),
        check('extract-check',[condition('variable','data',2),condition('variable','surveyed',1),condition('objective','extract','active'),condition('region','landing-pad',1)],'lua-check',identity('not-ready')),
        event('not-ready','say',text='Extraction requires both caches and the northern relay survey. Follow the road east; the relay is above its midpoint.',next=end),
        event('lua-check','lua',script=identity('verify'),routes=[identity('extract-complete'),failure],failure=failure),
        objective('extract-complete','extract','complete',identity('payment')),
        event('payment','reward',credits=4000,next=identity('success'),failure=failure),
        event('success','finish',text='The DropShip lifts off with both caches. Argent Recovery completed. Your lance receives 4,000 credits. Press Space to finish.'),
        objective('abandon','extract','failed',identity('abandoned')),
        event('abandoned','finish',text='You withdraw without the data. The extraction contract has failed. Your surviving lance can seek another employer.'),
        event('raider-choice','choice',text='A raider guards the eastern approach. Engage?',options=[dict(label='Engage',next=identity('battle')),dict(label='Leave',next=end)],cancel=end),
        event('battle','battle',encounter=identity('raider'),win=identity('raider-win'),loss=identity('abandon'),flee=identity('raider-retreat'),failure=failure),
        event('raider-win','say',text='The eastern approach is clear. Recover the data and return to the landing pad.',next=end),
        event('raider-retreat','say',text='Your lance breaks contact. The caches and relay remain available; retreat from this skirmish does not cancel the contract.',next=end),
    ]
    rows=[['recovery:grass']*32 for _ in range(24)]
    for y in range(11,14):
        for x in range(3,29):rows[y][x]='recovery:road'
    for x,y,w,h in ([3,11,3,3],[10,11,3,3],[18,11,3,3],[14,7,3,3],[3,18,3,3]):
        for yy in range(y,y+h):
            for xx in range(x,x+w):rows[yy][xx]='recovery:pad'
    scene=dict(id=identity('valley'),name='Argent Valley',origin=[0,0],rows=rows,overlays=[],entrances=[
        dict(id=identity('raider-marker'),name='Raider patrol',at=[52,24],event=identity('raider-choice'))])
    regions=[]
    for name,label,rect,enter,leave,repeat in [
        ('landing-pad','Extraction pad',[3,11,3,3],'pad-enter','pad-leave','always'),
        ('west-cache','West cache',[10,11,3,3],'collect-west',None,'once'),
        ('east-cache','East cache',[18,11,3,3],'collect-east',None,'once'),
        ('relay','Survey relay',[14,7,3,3],'survey',None,'once'),
        ('withdrawal','Abandon contract',[3,18,3,3],'abandon',None,'once')]:
        r=dict(id=identity(name),name=label,map=scene['id'],rect=rect,repeat=repeat,enter=identity(enter))
        if leave:r['leave']=identity(leave)
        regions.append(r)
    return dict(maps=[scene],tiles=[
        dict(id=identity('grass'),sheet='chi:land',graphic=64,terrain='clear',mini_color=2),
        dict(id=identity('road'),sheet='chi:land',graphic=82,terrain='clear',mini_color=7),
        dict(id=identity('pad'),sheet='chi:land',graphic=72,terrain='clear',mini_color=14)],
        events=events,regions=regions,
        variables=[dict(id=identity(k),name=name,type='counter',initial=0,maximum=maximum) for k,name,maximum in
            [('data','Recovered data caches',2),('visits','Landing pad visits',1000000),('departures','Landing pad departures',1000000)]]+
            [dict(id=identity('surveyed'),name='Relay surveyed',type='boolean',initial=0)],
        objectives=[dict(id=identity(k),title=title,text=text,initial='active') for k,title,text in [
            ('collect','Recover two caches','Cross both marked caches on the east road. Each cache counts once.'),
            ('survey','Survey the relay','Reach the marked relay north of the road.'),
            ('extract','Extract the data','With both caches and the survey, return to the western landing pad. The southern pad abandons this contract.')]],
        encounters=[dict(id=identity('raider'),map=scene['id'],party_at=[12,24],enemies=[dict(kind='mech',definition='chi-expanded:jenner-jr7-d',at=[42,22])])],
        start=dict(map=scene['id'],at=[12,24],event=identity('briefing'),credits=5000,party=[
            dict(person='relay:rowan',mech='chi-expanded:phoenix-hawk-pxh-1'),dict(person='relay:mira',mech='chi-expanded:trebuchet-tbt-5n')]))


SCRIPT="""-- Queries are immutable; the engine commits the declared continuation.
if game.variable("recovery:data") == 2 and game.variable("recovery:surveyed")
   and game.objective("recovery:extract") == "active"
   and game.in_region("recovery:landing-pad") then
    return game.command("recovery:extract-complete")
end
return game.command("recovery:error")
"""

README="""# BattleTech - Argent Recovery

An AI6a mission example: lead a Phoenix Hawk and Trebuchet to two data caches,
survey the northern relay, then return to the western landing pad. Crossing
the southern pad abandons the contract. The raider patrol is optional;
retreating from its skirmish leaves the extraction mission open.

From the repository root:

```sh
./build/btech-port --project examples/argent-recovery
python3 tools/game_editor.py examples/argent-recovery
```

Original CHI resources and prepared caches must be supplied by the player,
as for Relay Contract. Unit adaptations and attribution come from that
example and travel in `LIBRARY-SOURCES.json`. No original assets are embedded.
This custom mission does not claim original CHI story or full tabletop rules.

The editor's **Region** tool draws trigger rectangles; **Mission state** edits
regions and typed variables. **Objectives / journal** edits objective states.
The event inspector edits `variable`, `objective` and `check` commands.
All coordinates in region rectangles are map tiles, not movement half-tiles.

Reproduce in a new directory with:

```sh
python3 tools/mission_demo.py --output work/my-argent-recovery
```

The generator records its batch in `creation.commands.json`; this applies to
the generator's initialized template revision, not an arbitrary existing game.
Its Lua script only queries state and selects a declared engine continuation.
See [mission lifecycle](../../docs/MISSION_STATE.md) and the scenarios in
`examples/authoring/extraction/` for success, failure, retreat, repeated visits
and checkpoint evidence.
"""


def build(output,validator):
    output=Path(output)
    if output.exists():raise ValueError('Choose a new directory; existing authored work is never replaced.')
    doc=create_project(ROOT/'examples/relay-contract',output,'argent-recovery','BattleTech - Argent Recovery',validator)
    # The template supplies the attributed roster. Its map-construction notes
    # belong to its old maps, not this new authored mission.
    doc.metadata.pop('EDITOR.json',None);doc.metadata.pop('AUTHORING.json',None)
    doc.manifest['scripts']=[dict(id='recovery:verify',file='verify.lua')]
    doc.metadata['verify.lua']=SCRIPT.encode('ascii')
    model=adventure();operations=[]
    for collection in ('maps','tiles','events','encounters','objectives','shops','jigsaws'):
        operations.extend(dict(op='object.remove',collection=collection,id=v['id']) for v in doc.adventure.get(collection,[]))
    for collection in ('maps','tiles','events','encounters','objectives','variables','regions'):
        operations.extend(dict(op='object.put',collection=collection,value=v) for v in model[collection])
    operations.append(dict(op='start.set',changes=model['start']))
    request=dict(api_version=1,request_id='argent-recovery-ai6a',project_id='argent-recovery',expected_revision=revision(doc),
                 label='Create Argent Recovery mission',scope=['adventure'],operations=operations)
    apply_batch(doc,request,save=True)
    (output/'creation.commands.json').write_bytes(encoded(request))
    (output/'README.md').write_text(README)
    return doc


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--validator',type=Path,default=ROOT/'build/btp-project')
    args=parser.parse_args();build(args.output,args.validator)
    print('Created playable mission:',args.output)
