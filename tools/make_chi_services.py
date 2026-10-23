"""Generate the native service catalogue/schema from factual numeric contracts.

No extracted dialogue or original assets belong in this generator. Effective
cache-backed defaults are supplied by the native loader, not copied here.
"""
import json
from pathlib import Path
from chi_bld import NATIVE_NAMES

ROOT=Path(__file__).resolve().parents[1]
PARAMETERS=[]
def add(key,label,group,value,low=0,high=65535,source='constant',index=0):
    PARAMETERS.append(dict(id=key,label=label,group=group,default=value,minimum=low,maximum=high,source=source,index=index))
for i,v in enumerate((50,150,200,10000,1000),1):
    add(f'armour.price.{i}',f'Armour menu item {i} price','Personal equipment',v)
    add(f'armour.stock.{i}',f'Armour menu item {i} available','Personal equipment',1,0,1)
for i,v in enumerate((2,10,100,10,20,35,40,80,250,1500,1500),1):
    add(f'weapons.price.{i}',f'Weapon menu item {i} price','Personal equipment',v)
    add(f'weapons.stock.{i}',f'Weapon menu item {i} available','Personal equipment',1,0,1)
    add(f'weapons.item.{i}',f'Weapon menu item {i} equipment ID','Personal equipment',i,1,13)
for i,v in enumerate((1,2,5,20,20),1):add(f'armour.repair.{i}',f'Armour type {i} repair per point','Repairs and ammunition',v)
for key,v in [('armour',4),('structure',9),('heatsink',800),('weapon',300),('jump',200)]:
    add('repair.'+key,key.title()+' repair cost','Repairs and ammunition',v)
add('ammo.machinegun','Native machine gun ammunition cost','Repairs and ammunition',2,1,255)
for i in range(7):add(f'ammo.price.{i}',f'Native ammunition table {i} cost','Repairs and ammunition',0,1,255,'ammo',i)
for i in range(8):add(f'refit.price.{i}',f'Native refit recipe {i} price','Repairs and ammunition',0,0,65535,'refit',i)
for i in range(8):
    add(f'medical.price.{i}',f'Hospital skill {i} price','Healing',0,0,65535,'medical_price',i)
    for j in range(4):add(f'medical.program.{i}.{j}',f'Healing skill {i}, equipment {j+1} program','Healing',0,0,255,'medical_code',i*4+j)
add('medical.cooldown','Healing cooldown ticks','Healing',63,1,127)
add('medical.insufficient_credit','Original insufficient-funds credit adjustment','Healing',25)
add('apprentice.technician','Technician apprenticeship price','Training and recruitment',500)
add('apprentice.medical','Medical apprenticeship price','Training and recruitment',500)
for i in range(5):add(f'class.price.{i}',f'Class price at rank {i}','Training and recruitment',i*125+75)
add('recruit.limit','Maximum party size when recruiting','Training and recruitment',8,1,8)
add('recruit.seed_factor','Recruit identity seed multiplier','Training and recruitment',391,1,65535)
add('recruit.rank','Selected recruit specialty rank','Training and recruitment',3,0,4)
add('recruit.autoseat','Assign recruit to a free passenger seat','Training and recruitment',1,0,1)
add('recruit.spy_chance','Spy chance (0, 50 or 100 percent)','Training and recruitment',50,0,100)
add('recruit.spy_delay','Initial spy countdown','Training and recruitment',31,1,127)
add('prison.start_attempt','Successful distinct boarding attempt','Theft and garage',3,1,4)
add('prison.guard_ticks','Yard ticks before guards arrive','Theft and garage',81,1,255)
add('prison.reward','Encounter mech template awarded after theft','Theft and garage',2,0,2)
add('garage.allocate','Open crew allocation after checkout','Theft and garage',1,0,1)
add('theft.clear_crew','Clear crew before post-theft allocation','Theft and garage',1,0,1)
add('broker.sell_percent','Added-unit resale percent before damage','Broker',50,0,100)
add('broker.original_per_ton','Original model resale credits per ton','Broker',100,0,10000)
add('laser.primary','First laser-shop gift equipment ID','Other buildings',13,1,13)
add('laser.alternate','Alternate laser-shop gift equipment ID','Other buildings',12,1,13)
add('laser.health_base','Laser-shop health cap base multiplier','Other buildings',6,0,9)
add('meal.threshold','Meal applies above this health value','Other buildings',5,1,254)
add('meal.damage','Meal health reduction, clamped safely','Other buildings',4,0,254)
for key,label,group,value in [('medical.facility_fee','Hospital facility fee','Healing',25),('medical.kit_price','Medical kit price','Healing',75),('medical.advanced_kit_price','Field surgery kit price','Healing',375),('garage.fee','Garage fee','Theft and garage',150),('arena.rental_fee','Arena rental fee','Theft and garage',250),('arena.prize','Arena prize','Theft and garage',500),('clothes.price','Clothes price','Other buildings',35),('cinema.funds','Cinema funds requirement','Other buildings',5),('inventor.first_price','Inventor first device price','Other buildings',7000),('inventor.second_price','Inventor second device price','Other buildings',6000)]:add(key,label,group,value,high=32767 if key=='arena.prize' else 65535)
for i,(mask,rate) in enumerate(zip((255,7,1),(96,90,48))):
    add(f'market.mask.{i}',f'Company {i+1} growth RNG mask','Comstar',mask,0,255)
    add(f'market.rate.{i}',f'Company {i+1} growth/loss rate','Comstar',rate,1,255)
add('market.loss_divisor','Market loss divisor','Comstar',110,1,65535)
add('market.split_threshold','Third company split threshold','Comstar',18000)
add('market.split_shift','Third company split right shift','Comstar',2,0,8)
add('cadet.allowance','Cadet allowance per eligible wrap','Comstar',15)

# Every audited (building, F5 action) pair, including presentation-only calls.
CONTEXTS=[[1,2,3,12,43],[4,5,12],[6,7,8,12],[10,11,12],[9,10,12,13,14,31,32],
 [10,12,13,14,15,16,17,18,19,20,29,44],[12],[12],[10,17,28,29,46],
 [10,12,13,14,21,22,23,24,25,26],[12,14,17,27,29,33,34,35],[14,30],[10],
 [14,36,37,38,39,40],[14,47],[14,41],[42],[14],[],[14],[],[],[45],[],[],[]]
GROUPS=[('Training and recruitment','core/training.c',[1,2,3,43],'Native training state and valid mission selection; C4.3 owns mission definitions.','Mission result and suspended training return.','Mission/checkpoint state; may enter combat.','mission'),
 ('Training and recruitment','core/school.c',[4,5],'Cadet Citadel class anchor, skill rank 0..4 and a valid course.','Prices or transcript and story byte 9.','Credits, skill rank and allowance notification.','none'),
 ('Comstar','core/bank.c',[6,7,8],'Comstar and valid native text/account state.','Accounts, numeric trade receipt or insufficient-funds result.','Credits, investments, input and receipt state.','bank-input'),
 ('Personal equipment','core/shop.c',[9,10,11],'Matching shop/menu selection; credits for purchases; text before cash insertion.','Story byte 11 and recipient/swap selection, or inserted cash.','Payment once, inventory and party equipment; dropping never refunds.','recipient'),
 ('Dialogue','core/talk.c',[12],'Valid native conversation context and checkpoint.','Conversation result and return to its calling script.','Dialogue, story/economy effects and RNG as in the native talk routine.','conversation'),
 ('Repairs and ammunition','core/service.c',[13,18,19,20,32,44],'Living recipient or owned mech, eligible damage/ammunition and matching building.','Selected recipient, quote, repair/rearm/refit result.','Credits, selected equipment/damage/ammunition and saved service phases.','service-input'),
 ('Party queries','core/shop.c',[14,16,17,22,23,29,31,36,38],'Valid selected party member or native party/mech state.','Native story query bytes or inserted character name.','Query/text state; no invented transaction.','none'),
 ('Training and recruitment','core/story.c',[15,21],'Selected eligible apprentice and matching service context.','Story byte 14 success or insufficient-funds result.','Credits, selected skill and apprenticeship bits.','none'),
 ('Healing','core/story.c',[24,25,26],'Hospital selected skill 0..7 or native kit grant.','Held original healing message or kit ownership.','Credits, health, cooldown, RNG and kit state; treatment executes once.','healing-page'),
 ('Theft and garage','core/story.c',[27,28,33,34,35,37,39,40,46],'Matching prison/arena/garage and preserved party/checkpoint state.','Stored/restored mechs, selected crew or theft/arena continuation.','Ownership, crew, temporary party, native yard and combat state.','crew-yard-combat'),
 ('Other buildings','core/story.c',[30,41,42,45,47],'Matching Rex/laser/cinema/cache/mayor context and native preconditions.','Recruit encounter, gifts, cinema exit, LAM view or meal aftermath.','Native party, health, placement, encounter and RNG effects.','context-dependent')]

def generate():
    enum=[];rows=[]
    for p in PARAMETERS:
        symbol='BTP_SVC_'+p['id'].upper().replace('.','_');enum.append(symbol)
        rows.append('{'+','.join([json.dumps(p[k]) for k in ('id','label','group')]+[str(p[k])+'u' for k in ('minimum','maximum','default')]+['BTP_SVC_SOURCE_'+p['source'].upper(),str(p['index'])])+'},')
    (ROOT/'port/data/chi_service_parameters.inc').write_text('/* Generated by tools/make_chi_services.py. */\n'+'\n'.join(rows)+'\n')
    (ROOT/'port/data/chi_service_ids.h').write_text('/* Generated by tools/make_chi_services.py. */\n#ifndef BTP_CHI_SERVICE_IDS_H\n#define BTP_CHI_SERVICE_IDS_H\nenum {\n    '+',\n    '.join(enum)+',\n    BTP_SVC_COUNT\n};\n#endif\n')
    actions=[]
    for action in range(1,48):
        group,consumer,_,requires,outputs,mutations,yields=next(g for g in GROUPS if action in g[2])
        consumer=({15:'core/shop.c',22:'core/story.c',23:'core/story.c',31:'core/story.c',36:'core/story.c',38:'core/story.c',27:'core/story.c',28:'core/shop.c',33:'core/yard.c',34:'core/yard.c',35:'core/yard.c',37:'core/story.c',39:'core/story.c',40:'core/yard.c',46:'core/shop.c',30:'core/campaign.c',45:'core/cache.c'}).get(action,consumer)
        mask=sum(1<<b for b,values in enumerate(CONTEXTS) if action in values)
        name='native.'+'-'.join(NATIVE_NAMES[action].lower().replace("'",'').split())
        actions.append('{'+','.join([str(action),str(mask)+'u']+[json.dumps(v) for v in (name,NATIVE_NAMES[action],group,consumer,requires,outputs,mutations,yields,'Invalid context/operands fault visibly; transactions retain native insufficient-funds results.')])+'},')
    (ROOT/'port/data/chi_service_actions.inc').write_text('/* Generated factual context registry; no extracted text. */\n'+'\n'.join(actions)+'\n')
    schema=dict(type='object',additionalProperties=False,required=['format','schema_version','parameters'],properties=dict(format={'const':'btp-chi-services-v1'},schema_version={'const':1},parameters=dict(type='object',additionalProperties=False,properties={p['id']:dict(type='integer',minimum=p['minimum'],maximum=p['maximum']) for p in PARAMETERS}),broker_stock=dict(type='array',maxItems=256,uniqueItems=True,items=dict(type='string',maxLength=63))))
    schema['properties']['parameters']['properties']['recruit.spy_chance']={'enum':[0,50,100]}
    (ROOT/'schemas/chi-services-v1.schema.json').write_text(json.dumps(schema,indent=2)+'\n')

if __name__=='__main__':generate()
