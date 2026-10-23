"""Recorded, provider-independent campaign recipe; outputs ordinary editor data.

The three component missions retain their tested geometry and combat actors.
This module composes them through the public command API, rather than adding
special campaign behavior to the player or executing instructions from a brief.
"""
import copy
import hashlib
import json
from pathlib import Path

from authoring_contract import AuthoringError, check, obj, integer, array
from authoring_service import apply_batch, revision
from editor_model import ProjectDocument, create_project, encoded

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT/'examples/authoring/greybank/recipe.json'
FORMAT = 'btp-greybank-recipe-v1'
SCHEMA = obj(dict(
    format={'const': FORMAT},
    package_id=dict(type='string', pattern=r'^[a-z][a-z0-9-]{0,30}$'),
    title=dict(type='string', minLength=1, maxLength=80),
    starting_credits=integer(100, 1000000), repair_cost=integer(1, 10000),
    assault_reward=integer(0, 100000), recovery_reward=integer(0, 100000),
    defence_reward=integer(0, 100000), escort_reward=integer(0, 100000),
    defence_rounds=integer(3, 8), seeds=array(integer(1, 16777215), 1, 3)),
    ['format', 'package_id', 'title', 'starting_credits', 'repair_cost',
     'assault_reward', 'recovery_reward', 'defence_reward', 'escort_reward',
     'defence_rounds', 'seeds'])


def describe():
    return dict(id='greybank-dispatch', format=FORMAT, schema=SCHEMA,
        brief='examples/authoring/greybank/BRIEF.md', example=str(DEFAULT.relative_to(ROOT)),
        components=['Relay Contract: depot, services and assault',
                    'Argent Recovery: regions, counters, compound checks and bounded Lua',
                    'Cairn Passage: timed defence, reserves, neutral carrier and escort'],
        boundary='Fixed component layouts and roster; parameters tune this recipe. Expanded objects remain fully editable.',
        dependency='chi-original-dos-1.03; original assets supplied separately',
        commands=['recipe list', 'recipe build --file RECIPE --output NEW_DIRECTORY [--check] [--play]'])


def expansion(template, params):
    """Compose an exclusive first contract, service visits and two final fights."""
    from mission_demo import adventure as recovery, SCRIPT
    from combat_mission_demo import adventure as convoy
    a=copy.deepcopy(template.adventure);r=recovery();c=convoy()
    a['maps']+=r['maps']+c['maps'][1:]
    a['tiles']+=r['tiles']+c['tiles']
    a['encounters']+=r['encounters']+c['encounters']
    a['regions']=r['regions'];a['combat_groups']=c['combat_groups'];a['combat_hooks']=c['combat_hooks']
    a['variables']=r['variables']+[dict(id='dispatch:stage',name='Dispatch contract stage',type='counter',initial=0,maximum=5)]
    a['objectives']=[dict(id='relay:contract',title='Clear the relay approach',text='Defeat the Jenner and return to the depot.',initial='inactive')]+r['objectives']+c['objectives']
    for objective in a['objectives']:objective['initial']='inactive'
    a['start'].update(event='dispatch:welcome',credits=params['starting_credits'])
    a['shops'][0]['stock']+=['vehicles:galleon','vehicles:skulker']
    # Keep the working depot, repair/shop and ordinary skirmish interactions.
    keep={'end','to-field','to-town','challenge','challenge-offer','battle',
          'clear-text','retreated','unavailable','workshop','shop','repair','repaired','no-funds','no-work'}
    events={e['id']:e for e in a['events'] if e['id'].split(':')[1] in keep}
    events.update({e['id']:e for e in r['events']})
    events.update({e['id']:e for e in c['events'] if e['id'] not in
                   ('cairn:briefing','cairn:orders','cairn:escort-offer','cairn:escort-choice','cairn:success')})
    def event(identity,op,**fields):
        events[identity]=dict(id=identity,op=op,**fields)
    def say(identity,text,next='relay:end'):event(identity,'say',text=text,next=next)
    def stage(identity,value,next):event(identity,'variable',variable='dispatch:stage',action='set',value=value,once=0,next=next,failure='dispatch:error')
    def objective(identity,target,state,next):event(identity,'objective',objective=target,state=state,next=next,failure='dispatch:error')
    def check_stage(identity,value,yes,no):event(identity,'check',match='all',conditions=[dict(kind='variable',id='dispatch:stage',compare='eq',value=value)],then=yes,**{'else':no})
    def choice(identity,text,choices):event(identity,'choice',text=text,options=[dict(label=label,next=target) for label,target in choices],cancel='relay:end')
    say('dispatch:welcome','Greybank Dispatch. A raider lance has cut this outpost off from its DropShip. Rowan pilots a Phoenix Hawk; Mira brings a Trebuchet. Visit the contract office north of the road. The workshop to the east sells machines and repairs your lance.')
    say('dispatch:error','The contract could not advance. Check the mission journal and regroup at the depot.')
    say('dispatch:see-office','Visit the contract office. The dispatcher arranges your next deployment.')
    check_stage('dispatch:office',0,'dispatch:offer','dispatch:office-one')
    for number,yes,no in [(1,'dispatch:assault-brief','dispatch:office-two'),(2,'recovery:briefing','dispatch:office-three'),
                          (3,'dispatch:defence-offer','dispatch:office-four'),(4,'dispatch:escort-offer','dispatch:debrief')]:
        check_stage('dispatch:office-'+['','one','two','three','four'][number],number,yes,no)
    choice('dispatch:offer','Choose one opening contract. Either opens the route for the convoy; the other will be left to the local militia.',
           [('Clear the relay','dispatch:accept-assault'),('Recover the caches','dispatch:accept-recovery'),('Decide later','relay:end')])
    stage('dispatch:accept-assault',1,'dispatch:assault-active')
    objective('dispatch:assault-active','relay:contract','active','dispatch:assault-brief')
    say('dispatch:assault-brief',f"A Jenner blocks the relay approach. Take the south road, clear the patrol and return here. Payment: {params['assault_reward']:,} C-bills. Retreat leaves this contract open.")
    stage('dispatch:accept-recovery',2,'dispatch:collect-active')
    objective('dispatch:collect-active','recovery:collect','active','dispatch:survey-active')
    objective('dispatch:survey-active','recovery:survey','active','dispatch:extract-active')
    objective('dispatch:extract-active','recovery:extract','active','dispatch:recovery-brief')
    say('dispatch:recovery-brief',f"Take the south road. Upload two caches, survey the northern relay, then return to the western extraction pad. Payment: {params['recovery_reward']:,} C-bills. The raider patrol is optional.")
    check_stage('dispatch:road',1,'relay:to-field','dispatch:road-recovery')
    check_stage('dispatch:road-recovery',2,'dispatch:to-recovery','dispatch:see-office')
    event('dispatch:to-recovery','transfer',map='recovery:valley',at=[12,24],next='recovery:briefing',failure='dispatch:error')
    # Once-only branch rewards are protected by both the contract stage and
    # its terminal objective. A repeat office visit cannot pay again.
    event('relay:challenge','check',match='all',conditions=[dict(kind='objective',id='relay:contract',compare='eq',value='complete')],then='relay:clear-text',**{'else':'relay:challenge-offer'})
    objective('relay:won','relay:contract','complete','dispatch:assault-pay')
    event('dispatch:assault-pay','reward',credits=params['assault_reward'],next='dispatch:assault-paid',failure='dispatch:error')
    stage('dispatch:assault-paid',3,'relay:clear-text')
    event('relay:lost','finish',text='Your lance cannot hold the approach. The militia evacuates Greybank. Contract failed.')
    events['recovery:payment']['credits']=params['recovery_reward']
    events['recovery:payment']['next']='dispatch:recovery-paid'
    stage('dispatch:recovery-paid',3,'recovery:success')
    say('recovery:success','Both caches and the relay survey are secure. Payment received. The depot now needs you to protect the upload vehicle.',next='relay:to-town')
    choice('dispatch:defence-offer',f"The next contract pays {params['defence_reward']:,} C-bills. Protect the relay vehicle for {params['defence_rounds']} rounds. Repair at the workshop before deploying.",
           [('Defend the relay','cairn:defence-active'),('Visit the workshop','relay:end')])
    events['cairn:defence-start']['text']=f"Hold for {params['defence_rounds']} rounds. A Galleon guards the relay vehicle. Raiders approach from the northeast. Losing the vehicle or retreating fails the contract."
    next(h for h in a['combat_hooks'] if h['id']=='cairn:relay-timer')['round']=params['defence_rounds']
    next(o for o in a['objectives'] if o['id']=='cairn:defend')['text']=f"Keep the relay vehicle alive for {params['defence_rounds']} rounds."
    events['cairn:defence-pay'].update(credits=params['defence_reward'],next='dispatch:defence-paid')
    stage('dispatch:defence-paid',4,'dispatch:defence-report')
    say('dispatch:defence-report','Upload complete; payment received. Return to the workshop for repairs, then ask the dispatcher to begin the escort.',next='relay:to-town')
    choice('dispatch:escort-offer',f"Escort the Skulker through the pass for {params['escort_reward']:,} C-bills. Keep it alive until it reaches the landing pad. This is the last contract.",
           [('Begin escort','cairn:escort-active'),('Visit the workshop','relay:end')])
    events['cairn:escort-pay'].update(credits=params['escort_reward'],next='dispatch:escort-paid')
    stage('dispatch:escort-paid',5,'dispatch:escort-report')
    say('dispatch:escort-report','The Skulker reaches the DropShip with the traffic logs. Payment received. Report to the depot dispatcher to close the campaign.',next='relay:to-town')
    choice('dispatch:debrief','Greybank is back on the network. Your lance has brought the convoy home.',
           [('Keep exploring','relay:end'),('Finish campaign','dispatch:finish')])
    event('dispatch:finish','finish',text='Greybank Dispatch complete. The DropShip lifts off with the recovered traffic logs. Your lance has earned its next contract. Press Space to finish.')
    events['relay:repair']['cost']=params['repair_cost']
    repair_label=f"Repair lance - {params['repair_cost']}"
    events['relay:workshop']['options'][1]['label']=repair_label
    for door in a['maps'][0]['entrances']:
        if door['id']=='relay:office':door['event']='dispatch:office'
        if door['id']=='relay:south-road':door['event']='dispatch:road'
    # All hooks and regions are roots. Prune discarded recipe entrances and
    # boilerplate events so the event graph describes this campaign only.
    from event_editing import edges
    roots=[a['start']['event']]+[d['event'] for m in a['maps'] for d in m['entrances']]
    roots += [r[k] for r in a['regions'] for k in ('enter','leave') if k in r]
    roots += [h['event'] for h in a['combat_hooks']]
    reached=set();pending=list(roots)
    while pending:
        identity=pending.pop()
        if identity in reached:continue
        reached.add(identity);pending += [target for _,target in edges(events[identity])]
    a['events']=[e for e in events.values() if e['id'] in reached]
    return a,SCRIPT


def commands(document, model):
    """Expand templates into the same operations accepted by author.py apply."""
    ops=[dict(op='unit.import',file='skulker.unit.json'),dict(op='unit.import',file='galleon.unit.json'),
         dict(op='script.import',id='recovery:verify',file='verify.lua',target='verify.lua')]
    for collection in ('events','objectives','shops'):
        ops += [dict(op='object.remove',collection=collection,id=v['id']) for v in document.adventure[collection]]
    for collection in ('maps','tiles','encounters','events','objectives','shops','regions','variables','combat_groups','combat_hooks'):
        existing={v['id'] for v in document.adventure.get(collection,[])} if collection not in ('events','objectives','shops') else set()
        ops += [dict(op='object.put',collection=collection,value=v,mode='replace' if v['id'] in existing else 'create') for v in model[collection]]
    ops.append(dict(op='start.set',changes=model['start']))
    # Existing depot art/styles are retained. Complete styles are portable
    # package artwork; these extra buildings do not obstruct tested routes.
    for name,kind in [('depot','Building'),('barrier','Wall'),('roads','Road')]:
        ops += [dict(op='construction.style',value=dict(id='dispatch:'+name,name='Dispatch '+name,kind=kind,footprint=[[1,1],[1,1]],parts={})),
                dict(op='construction.complete',style='dispatch:'+name)]
    for scene in ('cairn:relay','cairn:pass'):
        ops += [dict(op='road.draw',map=scene,style='dispatch:roads',start=[4,17],end=[34,17],width=2),
                dict(op='construction.draw',map=scene,style='dispatch:barrier',start=[3,23],end=[12,23],stories=0)]
    ops += [dict(op='road.draw',map='cairn:pass',style='dispatch:roads',start=[28,17],end=[28,7],width=2),
            dict(op='construction.draw',map='cairn:pass',style='dispatch:depot',start=[18,10],end=[21,13],shape='Rectangle',stories=1),
            dict(op='construction.draw',map='cairn:relay',style='dispatch:depot',start=[3,5],end=[7,8],shape='Rectangle',stories=2)]
    for identity,text in [('dispatch:office','Route the dispatcher by the persistent campaign stage.'),
                          ('dispatch:offer','Choose exactly one opening contract: assault or data recovery.'),
                          ('recovery:lua-check','Verify both caches, survey and extraction region through read-only Lua queries.'),
                          ('cairn:defence-done','Timed defence succeeds after the configured number of rounds.'),
                          ('cairn:transport-arrived','Escort succeeds only when the living carrier reaches its final waypoint.')]:
        ops.append(dict(op='event.describe',id=identity,text=text))
    return ops


def build(params, output, validator):
    """Record inputs, compile ordinary editable objects, then build a package."""
    from unit_library import closure
    from campaign_source import convert, build as compile_source
    check(params,SCHEMA)
    output=Path(output).resolve()
    if output.exists():raise AuthoringError('output.exists','Recipe output must be a new directory; existing games are preserved.')
    output.mkdir(parents=True)
    (output/'recipe.json').write_bytes(encoded(params))
    inputs=output/'inputs';inputs.mkdir()
    # Retain the exact seed package, including source notes, for independent
    # replay of the recorded batch after the shipped templates evolve.
    seed=ProjectDocument(ROOT/'examples/relay-contract',validator,recover=False)
    seed.export(inputs/'template')
    doc=create_project(inputs/'template',output/'expanded',params['package_id'],params['title'],validator)
    vehicle=ProjectDocument(ROOT/'examples/cairn-passage',validator,recover=False)
    for name in ('skulker','galleon'):(inputs/(name+'.unit.json')).write_bytes(encoded(closure(vehicle,'vehicles:'+name)))
    model,script=expansion(doc,params);(inputs/'verify.lua').write_text(script,encoding='ascii')
    request=dict(api_version=1,request_id='greybank-dispatch-v1',project_id=params['package_id'],expected_revision=revision(doc),
                 label='Compose Greybank Dispatch campaign',scope=['*'],operations=commands(doc,model))
    (inputs/'creation.commands.json').write_bytes(encoded(request))
    apply_batch(doc,request,base_dir=inputs,save=True)
    write_documents(doc,params)
    source=convert(doc,output/'source');compiled=compile_source(source,output/'game')
    evidence=dict(format='btp-recipe-build-v1',recipe=params,revision=revision(source),
        package_fingerprint=compiled['fingerprint'],
        inputs={str(p.relative_to(inputs)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(inputs.rglob('*')) if p.is_file()},
        tools={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__),ROOT/'tools/mission_demo.py',ROOT/'tools/combat_mission_demo.py',Path(validator))},
        maps=len(source.adventure['maps']),events=len(source.adventure['events']),
        dependencies=dict(requires=source.manifest['requires'],assets_included=False),
        reproduction='Replay inputs/creation.commands.json against a new copy of inputs/template, then source convert/build. Recorded expansion is deterministic; free-form model sampling is not.')
    (output/'build-report.json').write_bytes(encoded(evidence))
    write_scenarios(params,output/'scenarios')
    return source,evidence


def write_documents(doc, params):
    """Keep human-readable credits beside the machine-readable import ledger."""
    (doc.root/'README.md').write_text(campaign_readme(params),encoding='utf-8')
    ledger=json.loads(doc.metadata['LIBRARY-SOURCES.json'])
    mech=next(v for v in ledger if v['definition']=='chi-expanded:phoenix-hawk-pxh-1')
    notes=mech['provenance']['documents']
    for name in ('SOURCE-README.md','sources.json'):
        (doc.root/name).write_text(notes[name],encoding='utf-8')
    (doc.root/'VEHICLE-SOURCE-README.md').write_bytes((ROOT/'content/catalogues/vehicles/README.md').read_bytes())
    (doc.root/'CREDITS.md').write_text('''# Credits and provenance

Greybank Dispatch is an original fan scenario assembled with AI assistance,
continuing this project's use of Sol 6.1 and Astra under human direction.
The underlying independent port relies on the research credited in the
repository README, especially the UnBattletech contributors. It does not use
the original game's source code.

Phoenix Hawk, Trebuchet and Jenner statistics reuse this repository's Updated
roster adaptations of the MegaMek mm-data contributors' records.
SOURCE-README.md and sources.json retain the inherited source pack's notes,
pinned links/hashes and adaptation limits. Those documents describe a broader
roster than this game's three mechs. Numeric adaptations retain CC BY-NC-SA 4.0;
the engine's GPL does not relicense them. LIBRARY-SOURCES.json retains the
complete imported credit/license documents with each definition.

Skulker and Galleon presets reuse the vehicle catalogue's design facts and
independent adaptations. VEHICLE-SOURCE-README.md credits the Sarna contributors
and distinguishes checked design facts, provisional values and rule limits.
Their driving sprites and the generated construction artwork are independently
drawn repository artwork. Original CHI terrain, font, border, sound and proxy
mech sprites are external runtime references, not included pixels.

Scenario text and the depot/mission composition reuse the repository's Relay
Contract, Argent Recovery and Cairn Passage examples. This is not a canonical
BattleTech story or a claim of full tabletop rules. See LICENSE.md.
''',encoding='utf-8')
    prefix='''# Package licensing

Scenario code, text and independently generated construction/vehicle artwork
use GPL-3.0-only, to the extent copyright applies. The full license follows.
Adapted mech records retain their inherited CC BY-NC-SA 4.0 terms; see
CREDITS.md, SOURCE-README.md and LIBRARY-SOURCES.json. Original game resources
are not included and retain their owners' rights. These licenses do not grant
rights to BattleTech trademarks or separately supplied CHI resources.

'''
    (doc.root/'LICENSE.md').write_text(prefix+(ROOT/'LICENSE').read_text(),encoding='utf-8')


def campaign_readme(p):
    return f'''# {p['title']}

An authored BattleTech campaign using the Construction Kit and CHI-adapted rules.
Start in Greybank with Rowan's Phoenix Hawk and Mira's Trebuchet. The contract
office is north of the road; the workshop is east. Choose either the Jenner
assault or cache recovery, then defend the relay and escort the Skulker.
Return to the depot between operations; repairs cost {p['repair_cost']} C-bills.
The dispatcher closes the campaign after the escort. Space selects menus;
arrow/numpad keys walk. The space menu includes journal, map, save and load.

Original CHI 1.03 assets must be supplied separately. No original assets are
included. See SOURCE-README.md, LIBRARY-SOURCES.json and vehicle source notes
for numeric/art attribution. This is an original scenario, not an original CHI
campaign or a claim of complete tabletop rules. AI (Sol 6.1 and Astra) has
assisted this project's research and development; see the repository README.

Open this directory in the Construction Kit, or run btech-port --project PATH.
The sibling source/ directory contains editable campaign modules; build it
before distributing. The native game needs neither Python nor an AI service.
The recipe, commands, scenarios and build report sit alongside the package.
'''


def write_scenarios(p, folder):
    """Ordinary inputs and checkpoints; no runtime mutation or forced wins."""
    folder.mkdir()
    def op(name,**kw):return dict(op=name,**kw)
    def walk(door):return [op('walk',entrance=door),op('enter')]
    def start(label):return [op('pages'),op('capture')]+walk('relay:office')+[op('choose',label=label),op('pages'),op('checkpoint')]
    def repair():return walk('relay:workshop')+[op('choose',label=f"Repair lance - {p['repair_cost']}"),op('pages'),op('input',action='cancel'),op('checkpoint')]
    def final_contracts():
        steps=repair()+walk('relay:office')+[op('choose',label='Defend the relay'),op('battle',control='computer',until_round=2),op('checkpoint'),op('capture'),
                op('battle',control='computer'),op('pages'),op('assert',map='relay:town',objective='cairn:defend',status='complete'),op('checkpoint')]
        steps+=repair()+walk('relay:office')+[op('choose',label='Begin escort'),op('battle',control='computer',until_round=3),op('checkpoint'),
                op('battle',control='computer'),op('pages'),op('assert',map='relay:town',objective='cairn:escort',status='complete'),op('checkpoint')]
        steps+=walk('relay:office')+[op('choose',label='Keep exploring')]+walk('relay:office')+[op('choose',label='Finish campaign'),op('pages'),op('assert',phase='complete'),op('checkpoint'),op('capture')]
        return steps
    assault=start('Clear the relay')+walk('relay:south-road')+walk('relay:raider-marker')+[op('choose',label='Engage'),op('battle',control='computer'),op('pages'),
        op('assert',objective='relay:contract',status='complete',credits=p['starting_credits']+p['assault_reward']),op('checkpoint')]
    # Revisit the cleared battle marker: payment must be idempotent.
    assault+=walk('relay:raider-marker')+[op('pages'),op('assert',credits=p['starting_credits']+p['assault_reward'])]+walk('relay:depot-road')+final_contracts()
    recovery=start('Recover the caches')+walk('relay:south-road')+[op('pages')]
    original=json.loads((ROOT/'examples/authoring/extraction/success.json').read_bytes())['steps']
    # The final pad transfers back to town after the acknowledgement, so keep
    # the actual movement/cache assertions and replace only its standalone end.
    segment=copy.deepcopy(original[1:20])
    for step in segment:
        if 'credits' in step:step['credits']=p['starting_credits']+p['recovery_reward']
    recovery+=segment+[op('pages'),op('assert',map='relay:town',variable='dispatch:stage',value=3),op('checkpoint')]+final_contracts()
    retreat=start('Clear the relay')+walk('relay:south-road')+walk('relay:raider-marker')+[op('choose',label='Engage'),op('battle',control='retreat'),op('pages'),
        op('assert',objective='relay:contract',status='active',credits=p['starting_credits']),op('checkpoint')]
    defer=[op('pages')]+walk('relay:south-road')+[op('pages'),op('assert',map='relay:town',variable='dispatch:stage',value=0)]+walk('relay:office')+[op('choose',label='Decide later')]
    defer+=repair()+[op('assert',credits=p['starting_credits'],variable='dispatch:stage',value=0),op('checkpoint')]
    abandon=start('Recover the caches')+walk('relay:south-road')+[op('pages')]
    abort=json.loads((ROOT/'examples/authoring/extraction/abandon.json').read_bytes())['steps']
    abandon+=copy.deepcopy(abort[1:])
    for step in abandon:
        if 'credits' in step:step['credits']=p['starting_credits']
    # Directly test the composed defence failure after the ordinary assault.
    before_defence=assault[:next(i for i,s in enumerate(assault) if s.get('label')=='Defend the relay')+1]
    failed=before_defence+[op('battle',control='retreat'),op('pages'),op('assert',objective='cairn:defend',status='failed',phase='complete'),op('checkpoint')]
    routes={'assault':assault,'recovery':recovery,'retreat':retreat,'defer':defer,'abandon':abandon,'defence-failure':failed}
    for name,steps in routes.items():(folder/(name+'.json')).write_bytes(encoded(dict(format='btp-author-scenario-v1',max_ticks=120000,steps=steps)))
    suite=dict(format='btp-author-suite-v1',cases=[dict(id=name,file=name+'.json',seeds=p['seeds'] if name in ('assault','recovery') else p['seeds'][:1]) for name in routes])
    (folder/'suite.json').write_bytes(encoded(suite))
