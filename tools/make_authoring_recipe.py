#!/usr/bin/env python3
"""Reproduce the recorded command recipe; generation itself uses author.py.

Only reads existing examples. The demo's unit bundles retain their source
documents; the user's revised Last Beacon package is never regenerated.
"""
import json
from pathlib import Path
from editor_model import ProjectDocument,encoded
from unit_library import closure

ROOT=Path(__file__).resolve().parents[1]


def main():
    root=ROOT/'examples/authoring';(root/'units').mkdir(parents=True,exist_ok=True)
    doc=ProjectDocument(ROOT/'examples/battletech-demo',ROOT/'build/btp-project',recover=False)
    for slug,identity in [('phoenix-hawk','chi-expanded:phoenix-hawk-pxh-1'),('trebuchet','chi-expanded:trebuchet-tbt-5n'),('jenner','chi-expanded:jenner-jr7-d')]:
        (root/'units'/f'{slug}.json').write_bytes(encoded(closure(doc,identity)))
    base=json.loads((ROOT/'examples/adventure-demo/adventure.json').read_text());ops=[]
    def add(command,**kw):ops.append(dict(op=command,**kw))
    def put(collection,**kw):add('object.put',collection=collection,value=kw)
    def event(identity,action,**kw):put('events',id='relay:'+identity,op=action,**kw)
    for slug in ['phoenix-hawk','trebuchet','jenner']:add('unit.import',file=f'units/{slug}.json')
    for col in ['maps','people','shops','encounters','events']:
        for v in base[col]:add('object.remove',collection=col,id=v['id'])
    for identity,name,kind in [('depot','Relay depot','Building'),('wall','Compound wall','Wall'),('road','Depot roads','Road')]:
        add('construction.style',value=dict(id='relay:'+identity,name=name,kind=kind,footprint=[[1,1,1],[1,1,1],[1,1,1]],parts={}))
    for identity,name in [('town','Greybank Relay Depot'),('field','Relay Approach')]:
        add('map.create',id='relay:'+identity,name=name,width=32,height=24,tile='frontier:grass')
    for start,end in [([1,1],[6,6]),([2,17],[4,21]),([24,16],[29,21])]:
        add('map.paint',map='relay:town',tile='frontier:forest',start=start,end=end,tool='Rectangle')
    add('map.paint',map='relay:town',tile='frontier:water',start=[0,10],end=[3,15],tool='Rectangle')
    add('construction.draw',map='relay:town',style='relay:depot',id='relay:office-building',start=[10,3],end=[15,6],shape='Rectangle',stories=2)
    add('construction.draw',map='relay:town',style='relay:depot',id='relay:workshop-building',start=[22,3],end=[26,6],shape='Courtyard',stories=1)
    add('construction.draw',map='relay:town',style='relay:wall',id='relay:compound',start=[29,3],end=[29,11],stories=1)
    for start,end in [([6,10],[27,10]),([8,10],[8,19]),([12,9],[12,10]),([24,8],[24,10])]:add('road.draw',map='relay:town',style='relay:road',start=start,end=end)
    add('pattern.capture',map='relay:town',rect=[10,3,17,8],name='Relay office')
    for start,end in [([2,2],[6,7]),([24,15],[28,20])]:add('map.paint',map='relay:field',tile='frontier:forest',start=start,end=end,tool='Rectangle')
    add('road.draw',map='relay:field',style='relay:road',start=[5,18],end=[24,9])
    for n,name in [('rowan','Rowan'),('mira','Mira')]:put('people',id='relay:'+n,identity='actor:0' if n=='rowan' else 'actor:1',name=name,attributes=[9,9,9],skills=[3,3,3,4,4,2,2],weapon=7,armor=2)
    add('flags.add',ids=['relay:accepted','relay:cleared','relay:paid'])
    put('objectives',id='relay:contract',title='Secure the relay',text='Clear the raider on the relay approach, then return to the depot for payment.',active='relay:accepted',complete='relay:paid')
    put('shops',id='relay:stock',stock=['chi-expanded:phoenix-hawk-pxh-1','chi-expanded:trebuchet-tbt-5n','chi-expanded:jenner-jr7-d'])
    put('encounters',id='relay:raider',map='relay:field',party_at=[12,36],enemies=[dict(kind='mech',definition='chi-expanded:jenner-jr7-d',at=[42,22])])
    event('end','end')
    event('welcome','say',portrait='none',text='Greybank has lost contact with its relay. Your Phoenix Hawk and Trebuchet are the only machines available. The depot offers 4,000 credits to clear the approach.',next='relay:offer')
    event('offer','choice',portrait='none',text='Will you take the relay contract?',options=[dict(label='Accept contract',next='relay:accept'),dict(label='Decide later',next='relay:end')],cancel='relay:end')
    event('accept','flag',flag='relay:accepted',value=1,next='relay:briefing')
    event('briefing','say',portrait='none',text='Take the south road to the relay. A Jenner is blocking the approach. Withdraw if necessary. Return here when the route is clear.',next='relay:end')
    event('office','if',flag='relay:cleared',value=1,then='relay:receipt',**{'else':'relay:accepted-check'})
    event('accepted-check','if',flag='relay:accepted',value=1,then='relay:briefing',**{'else':'relay:offer'})
    event('receipt','if',flag='relay:paid',value=1,then='relay:debrief',**{'else':'relay:pay'})
    event('pay','reward',credits=4000,next='relay:paid',failure='relay:end')
    event('paid','flag',flag='relay:paid',value=1,next='relay:thanks')
    event('thanks','say',portrait='none',text='The relay is transmitting again. Your account has been credited with 4,000. Good work, commander.',next='relay:debrief')
    event('debrief','choice',portrait='none',text='The contract is complete. Explore the depot or end this mission.',options=[dict(label='Keep exploring',next='relay:end'),dict(label='Finish mission',next='relay:finish')],cancel='relay:end')
    event('finish','finish',portrait='none',text='Greybank is back on the network. Contract complete.')
    event('to-field','transfer',map='relay:field',at=[12,38],next='relay:end',failure='relay:end')
    event('to-town','transfer',map='relay:town',at=[16,38],next='relay:end',failure='relay:end')
    event('challenge','if',flag='relay:cleared',value=1,then='relay:clear-text',**{'else':'relay:challenge-offer'})
    event('challenge-offer','choice',portrait='none',text='A Jenner guards the relay approach. Engage the raider?',options=[dict(label='Engage',next='relay:battle'),dict(label='Withdraw',next='relay:end')],cancel='relay:end')
    event('battle','battle',encounter='relay:raider',win='relay:won',loss='relay:lost',flee='relay:retreated',failure='relay:unavailable')
    event('won','flag',flag='relay:cleared',value=1,next='relay:clear-text')
    event('clear-text','say',portrait='none',text='The approach is secure. Return to the depot for your payment.',next='relay:end')
    event('lost','say',portrait='none',text='The raider holds the relay. Return to the depot and regroup.',next='relay:to-town')
    event('retreated','say',portrait='none',text='You withdraw from the relay. The contract remains open.',next='relay:end')
    event('unavailable','say',portrait='none',text='The lance cannot deploy here. Return to the depot.',next='relay:end')
    event('workshop','choice',portrait='none',text='The depot offers machines and basic repairs.',options=[dict(label='Browse machines',next='relay:shop'),dict(label='Repair lance - 100',next='relay:repair'),dict(label='Leave',next='relay:end')],cancel='relay:end')
    event('shop','shop',shop='relay:stock',next='relay:workshop')
    event('repair','repair',cost=100,next='relay:repaired',failure='relay:no-funds',unchanged='relay:no-work')
    for n,text in [('repaired','The lance is repaired.'),('no-funds','You cannot afford repairs.'),('no-work','Your machines need no repairs.')]:event(n,'say',portrait='none',text=text,next='relay:workshop')
    for m,identity,name,at,target in [('town','office','Contract office',[25,18],'office'),('town','workshop','Mech workshop',[48,18],'workshop'),('town','south-road','Relay road',[16,42],'to-field'),('field','depot-road','Depot road',[12,42],'to-town'),('field','raider-marker','Relay approach',[28,30],'challenge')]:
        add('entrance.put',map='relay:'+m,value=dict(id='relay:'+identity,name=name,at=at,event='relay:'+target))
    add('start.set',changes=dict(map='relay:town',at=[12,34],event='relay:welcome',credits=5000,party=[dict(person='relay:rowan',mech='chi-expanded:phoenix-hawk-pxh-1'),dict(person='relay:mira',mech='chi-expanded:trebuchet-tbt-5n')]))
    request=dict(api_version=1,request_id='relay-contract-001',project_id='relay-contract',expected_revision='new',label='Create Relay Contract mission',scope=['*'],operations=ops)
    (root/'relay-contract.commands.json').write_bytes(encoded(request))
    steps=[dict(op='pages'),dict(op='choose',label='Accept contract'),dict(op='pages'),dict(op='assert',flag='relay:accepted',value=1,credits=5000,party_count=2),dict(op='checkpoint'),dict(op='capture'),dict(op='walk',entrance='relay:workshop'),dict(op='enter'),dict(op='choose',label='Repair lance - 100'),dict(op='pages'),dict(op='assert',credits=5000),dict(op='input',action='cancel'),dict(op='walk',entrance='relay:south-road'),dict(op='enter'),dict(op='assert',map='relay:field'),dict(op='walk',entrance='relay:raider-marker'),dict(op='enter'),dict(op='choose',label='Engage'),dict(op='capture'),dict(op='battle',control='computer'),dict(op='pages'),dict(op='assert',flag='relay:cleared',value=1),dict(op='checkpoint'),dict(op='walk',entrance='relay:depot-road'),dict(op='enter'),dict(op='walk',entrance='relay:office'),dict(op='enter'),dict(op='pages'),dict(op='assert',credits=9000,objective='relay:contract',status='complete'),dict(op='checkpoint'),dict(op='choose',label='Keep exploring'),dict(op='walk',entrance='relay:office'),dict(op='enter'),dict(op='assert',credits=9000),dict(op='choose',label='Finish mission'),dict(op='pages'),dict(op='assert',phase='complete'),dict(op='checkpoint'),dict(op='capture')]
    (root/'relay-contract.scenario.json').write_bytes(encoded(dict(format='btp-author-scenario-v1',max_ticks=120000,steps=steps)))
    print(f'Wrote {len(ops)} commands and {len(steps)} scenario steps.')


if __name__=='__main__':main()
