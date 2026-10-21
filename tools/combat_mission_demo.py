#!/usr/bin/env python3
"""Create Cairn Passage: timed defence followed by a vehicle escort."""
import argparse
import copy
from pathlib import Path
from authoring_service import apply_batch,revision
from editor_model import create_project,encoded
from unit_editing import import_catalogue

ROOT=Path(__file__).resolve().parents[1]


def adventure():
    def ref(name):return 'cairn:'+name
    end=ref('end');error=ref('error')
    def event(name,op,**fields):return dict(id=ref(name),op=op,**fields)
    def say(name,text,next=end):return event(name,'say',text=text,next=next)
    def objective(name,target,state,next=end):return event(name,'objective',objective=ref(target),state=state,next=next,failure=error)
    def check(name,conditions,yes,no=end):return event(name,'check',match='all',conditions=conditions,then=ref(yes),**{'else':no})
    def group(kind,name,value):return dict(kind='group_'+kind,id=ref(name),compare='eq',value=value)
    events=[event('end','end'),say('briefing','Cairn Passage. Hold the relay while ComStar recovers its traffic logs, then escort a Skulker scout carrying the data to the landing zone. Your Phoenix Hawk and Trebuchet are the convoy guard.',ref('orders')),
        event('orders','choice',text='Two contracts, one route out of the valley. Choose the operation to begin.',
              options=[dict(label='Defend the relay',next=ref('defence-active')),dict(label='Escort the transport',next=ref('escort-active'))],cancel=end),
        say('error','Mission command could not be completed. Check the mission log and deployment area.'),
        objective('defence-active','defend','active',ref('defence-battle')),
        event('defence-battle','battle',encounter=ref('defence'),win=ref('defence-complete'),loss=ref('defence-failed'),flee=ref('defence-failed'),failure=error),
        say('defence-start','Hold for five rounds. A Galleon guards the relay vehicle. Raiders are approaching from the northeast. Losing the relay vehicle ends the contract.'),
        say('incoming','A second raider is entering the valley. The relay upload is still running.',ref('reinforce')),
        event('reinforce','reinforce',group=ref('raider-wave'),radius=2,next=end,failure=ref('blocked-wave')),
        say('blocked-wave','The reinforcements cannot deploy yet. They will try again next round.'),
        check('retry-wave',[group('deployed','raider-wave',0)],'reinforce'),
        check('defence-death',[group('alive','relay-vehicle',0)],'combat-loss'),
        event('combat-loss','battle_end',result='loss',next=end,failure=error),
        event('defence-done','battle_end',result='win',next=end,failure=error),
        objective('defence-complete','defend','complete',ref('defence-pay')),
        event('defence-pay','reward',credits=3000,next=ref('escort-offer'),failure=error),
        say('escort-offer','Upload complete. The relay crew pays 3,000 C-bills. Now escort the data carrier through the pass.',ref('escort-choice')),
        event('escort-choice','choice',text='The Skulker crew is ready to leave.',options=[dict(label='Begin escort',next=ref('escort-active')),dict(label='Stay at base',next=end)],cancel=end),
        objective('defence-failed','defend','failed',ref('defence-loss')),
        event('defence-loss','finish',text='The relay contract has failed. The surviving crew evacuates without its data.'),
        objective('escort-active','escort','active',ref('escort-battle')),
        event('escort-battle','battle',encounter=ref('escort'),win=ref('escort-complete'),loss=ref('escort-failed'),flee=ref('escort-failed'),failure=error),
        say('escort-start','Keep the Skulker alive. It follows the marked road around the depot to the northeast landing pad. Raiders can attack the transport. The crew drives; you control the two escort mechs.'),
        say('escort-incoming','Movement detected east of the depot. Keep the carrier covered.',ref('escort-reinforce')),
        event('escort-reinforce','reinforce',group=ref('ambush'),radius=2,next=end,failure=ref('escort-blocked')),
        say('escort-blocked','The ambush is delayed. Watch the eastern approach.'),
        check('escort-retry',[group('deployed','ambush',0)],'escort-reinforce'),
        check('transport-death',[group('alive','transport',0)],'combat-loss'),
        check('transport-arrived',[group('arrived','transport',1),group('alive','transport',1)],'escort-done'),
        event('escort-done','battle_end',result='win',next=end,failure=error),
        objective('escort-complete','escort','complete',ref('escort-pay')),
        event('escort-pay','reward',credits=4000,next=ref('success'),failure=error),
        event('success','finish',text='The data carrier reaches the DropShip. Cairn Passage is secure. Your lance receives 4,000 C-bills for the escort. Press Space to finish.'),
        objective('escort-failed','escort','failed',ref('escort-loss')),
        event('escort-loss','finish',text='The transport did not reach the landing zone. The escort contract has failed.'),
    ]
    maps=[]
    for name,title in [('base','Cairn staging ground'),('relay','Cairn relay'),('pass','Cairn mountain pass')]:
        rows=[[ref('grass')]*40 for _ in range(32)]
        for y in range(15,20):
            for x in range(4,35):rows[y][x]=ref('road')
        if name=='pass':
            for y in range(6,18):
                for x in range(26,30):rows[y][x]=ref('road')
            for y in range(5,9):
                for x in range(27,32):rows[y][x]=ref('pad')
        maps.append(dict(id=ref(name),name=title,origin=[0,0],rows=rows,overlays=[],entrances=[]))
    maps[0]['entrances']=[dict(id=ref('dispatch'),name='Contract dispatcher',at=[24,34],event=ref('orders'))]
    groups=[
        dict(id=ref('relay-vehicle'),name='Relay data carrier',encounter=ref('defence'),affiliation='neutral',reserve=0,units=[dict(kind='mech',definition='vehicles:skulker',at=[18,28])]),
        dict(id=ref('relay-guard'),name='Relay Galleon',encounter=ref('defence'),affiliation='friendly',reserve=0,units=[dict(kind='mech',definition='vehicles:galleon',at=[24,30])]),
        dict(id=ref('raider-wave'),name='Second raider wave',encounter=ref('defence'),affiliation='hostile',reserve=1,units=[dict(kind='mech',definition='chi-expanded:jenner-jr7-d',at=[54,32])]),
        dict(id=ref('transport'),name='Skulker data carrier',encounter=ref('escort'),affiliation='neutral',reserve=0,units=[dict(kind='mech',definition='vehicles:skulker',at=[22,34],movement='walk',waypoints=[[38,34],[54,34],[56,22],[56,14]])]),
        dict(id=ref('ambush'),name='Pass ambush',encounter=ref('escort'),affiliation='hostile',reserve=1,units=[dict(kind='mech',definition='vehicles:galleon',at=[64,22])]),
    ]
    hooks=[]
    def hook(name,battle,when,event,repeat='once',**fields):hooks.append(dict(id=ref(name),encounter=ref(battle),when=when,event=ref(event),repeat=repeat,**fields))
    hook('relay-briefing','defence','start','defence-start')
    hook('relay-wave','defence','round_start','incoming',round=2,every=0)
    hook('relay-retry','defence','round_start','retry-wave','always',round=3,every=1)
    hook('relay-casualty','defence','destroyed','defence-death','always',group=ref('relay-vehicle'))
    hook('relay-timer','defence','round_end','defence-done',round=5,every=0)
    hook('pass-briefing','escort','start','escort-start')
    hook('pass-wave','escort','round_start','escort-incoming',round=3,every=0)
    hook('pass-retry','escort','round_start','escort-retry','always',round=4,every=1)
    hook('pass-casualty','escort','destroyed','transport-death','always',group=ref('transport'))
    hook('pass-arrival','escort','arrival','transport-arrived','always',group=ref('transport'))
    return dict(maps=maps,tiles=[dict(id=ref(name),sheet='chi:land',graphic=graphic,terrain=terrain,mini_color=color) for name,graphic,terrain,color in
        [('grass',64,'clear',2),('road',82,'clear',7),('pad',72,'clear',14),('wall',144,'wall',8)]],events=events,
        objectives=[dict(id=ref('defend'),title='Hold the relay',text='Keep the relay data carrier alive for five rounds.',initial='inactive'),
                    dict(id=ref('escort'),title='Escort the carrier',text='Keep the Skulker alive until it reaches the landing pad.',initial='inactive')],
        encounters=[dict(id=ref(name),map=ref(scene),party_at=[14,34],completion='scripted',
                         enemies=[dict(kind='mech',definition='chi-expanded:jenner-jr7-d',at=at)]) for name,scene,at in [('defence','relay',[54,18]),('escort','pass',[60,34])]],
        combat_groups=groups,combat_hooks=hooks,
        start=dict(map=ref('base'),at=[14,34],event=ref('briefing'),credits=5000,party=[dict(person='relay:rowan',mech='chi-expanded:phoenix-hawk-pxh-1'),dict(person='relay:mira',mech='chi-expanded:trebuchet-tbt-5n')]))


def build(output,validator):
    output=Path(output)
    if output.exists():raise ValueError('Choose a new directory; existing projects are preserved.')
    doc=create_project(ROOT/'examples/relay-contract',output,'cairn-passage','BattleTech - Cairn Passage',validator)
    doc.metadata.pop('EDITOR.json',None);doc.metadata.pop('AUTHORING.json',None)
    # The template supplies numeric roster definitions; its unrelated map
    # artwork is not part of this mission's reproducible construction recipe.
    doc.art=dict(format='btp-art-v1',schema_version=1,images=[],bindings=[])
    import_catalogue(doc,ROOT/'content/catalogues/vehicles',['vehicles:skulker','vehicles:galleon','vehicles:pegasus'])
    doc.metadata['VEHICLE-SOURCE-README.md']=(ROOT/'content/catalogues/vehicles/README.md').read_bytes()
    model=adventure();operations=[]
    for collection in ('maps','tiles','events','encounters','objectives','shops','jigsaws'):
        operations.extend(dict(op='object.remove',collection=collection,id=v['id']) for v in doc.adventure.get(collection,[]))
    for collection in ('maps','tiles','events','encounters','objectives','combat_groups','combat_hooks'):
        operations.extend(dict(op='object.put',collection=collection,value=v) for v in model[collection])
    operations.append(dict(op='start.set',changes=model['start']))
    for name,kind,footprint in [('depot','Building',[[1,1],[1,1]]),('barrier','Wall',[[-1,-1,-1]]),('roads','Road',[[1,1,1],[0,1,0]])]:
        operations.extend([dict(op='construction.style',value=dict(id='cairn:'+name,name='Cairn '+name,kind=kind,footprint=footprint,parts={})),
                           dict(op='construction.complete',style='cairn:'+name)])
    for scene in ('base','relay','pass'):
        operations.extend([dict(op='road.draw',map='cairn:'+scene,style='cairn:roads',start=[4,17],end=[34,17],width=2),
            dict(op='construction.draw',map='cairn:'+scene,style='cairn:barrier',start=[3,23],end=[12,23],stories=0)])
    operations.extend([dict(op='road.draw',map='cairn:pass',style='cairn:roads',start=[28,17],end=[28,7],width=2),
        dict(op='construction.draw',map='cairn:pass',style='cairn:depot',start=[18,10],end=[21,13],shape='Rectangle',stories=1),
        dict(op='construction.draw',map='cairn:relay',style='cairn:depot',start=[3,5],end=[7,8],shape='Rectangle',stories=2),
        dict(op='construction.draw',map='cairn:base',style='cairn:depot',start=[10,5],end=[16,9],shape='Courtyard',stories=2)])
    request=dict(api_version=1,request_id='cairn-passage-combat-missions',project_id='cairn-passage',expected_revision=revision(doc),
                 label='Create Cairn Passage defence and escort',scope=['adventure','art','editor'],operations=operations)
    apply_batch(doc,request,save=True);(output/'creation.commands.json').write_bytes(encoded(request))
    (output/'README.md').write_text('''# BattleTech - Cairn Passage

A small authored defence-and-escort demonstration for AI6b/AI6c. Uses the
original CHI runtime art supplied separately by the player, CHI-adapted unit
definitions, and original editable construction/vehicle artwork.

From the repository root:

```sh
./build/btech-port --project examples/cairn-passage --data "Original DOS"
./BtechPort
```

In the launcher, select Cairn Passage, then Open editor to edit the mission.
Choose defence or escort at the briefing. Defence holds the relay vehicle for
five rounds against two raider waves, with an allied Galleon guard. Success
offers the escort immediately. Escort protects an engine-controlled Skulker
along the road to the northeast landing pad; a reserve ambush enters on round
three. Loss of the protected carrier or retreat fails the current contract.
The Phoenix Hawk and Trebuchet remain player controlled or use normal computer
combat. Both contracts together pay 7,000 C-bills.

Mission state in the editor exposes groups, actor waypoints, timers and hooks.
Construction styles include all roof/face parts, all sixteen road connections,
and zero-story walls. Their compiled tiles work in the ordinary player.

Regenerate into a new directory with:

```sh
python3 tools/combat_mission_demo.py --output work/cairn-copy
python3 tools/author.py suite examples/cairn-passage --file examples/authoring/cairn/suite.json --output work/cairn-check
```

The suite covers bounded seeds, success, retreat, transport loss, the combined
contract and save/reload checkpoints. It does not establish general AI balance
or guarantee that arbitrary waypoint layouts are reachable. See
[combat mission semantics](../../docs/COMBAT_MISSIONS.md) and the accompanying
source/credit documents for unit attribution. `creation.commands.json` records
the authoring batch against the generator's initialized template revision.
''')
    return doc


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--validator',type=Path,default=ROOT/'build/btp-project');args=parser.parse_args()
    build(args.output,args.validator);print('Created playable mission:',args.output)
