"""Generate typed native campaign settings. Original tables stay in local caches.

Constants here describe the retained native state machines, not extracted art,
dialogue or compiled unit records. Cache offsets are C member references.
"""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PARAMETERS=[]
UNITS=[]
def add(key,label,group,value,low=0,high=255,member=None,word=False):
    PARAMETERS.append(dict(id=key,label=label,group=group,default=value,minimum=low,maximum=high,member=member,word=word))
def unit(key,label,kind,index=0):UNITS.append(dict(id=key,label=label,kind=kind,index=index))
def fields(prefix,group,values):
    for name,value,lo,hi in values:add(prefix+'.'+name,name.replace('_',' ').capitalize(),group,value,lo,hi)

fields('start','New campaign',[('credits',35,0,65535),('allowance_cap',50,0,65535)])
for i,v in enumerate((31,66,171)):add(f'start.rng.{i}',f'Initial gameplay RNG byte {i}','New campaign',v,0,255)
fields('start','New campaign',[('constitution',8,2,12),('dexterity',9,2,12),('charisma',7,2,12)])
for i in range(7):add(f'start.skill.{i}',f'Initial player skill {i}','New campaign',0,0,4)
for m in range(8):
    group=f'Training {m}: '+('driving','recovery','shell','infantry','duel','pair','patrol','invasion')[m]
    p=f'training.{m}'
    fields(p,group,[('start_x',64,2,124),('start_y',79,4,126),('control_prompt',int(m<3),0,1),
        ('enemy_ai',int(m>=3),0,1),('return_x',60,0,124),('return_y_min',73,0,126),('return_y_max',79,0,126),
        ('skill_award',int(m>=5),0,1),('invasion',2 if m==7 else 1 if m==6 else 0,0,2),
        ('return_message',90,0,372),('pass_on_win',1,0,1),('pass_on_retreat',0,0,1),('pass_on_loss',0,0,1)])
    if m>=2:
        fields(p,group,[('enemy_count',3 if m==3 else 2 if m==5 else m-3 if m>=6 else 1,1,6),
            ('count_mask',3 if m==3 else 0,0,3),('spawn_x',101,2,110),('spawn_y',89,2,110),
            ('spawn_mask',7,0,7),('shell_x',114,2,124),('shell',int(m==2),0,1),('infantry',int(m==3),0,1),
            ('infantry_weapons',14,1,14),('infantry_skill_mask',1,0,3)])
        for i in range(6):
            # Unused mech slots get separate positions too, so increasing a
            # force count does not stack newly enabled actors on one cell.
            x=(1,2,0,1,0,0)[i] if m==3 else 4*(i%2)
            y=(2,2,3,3,0,1)[i] if m==3 else 4*(i//2)
            add(p+f'.enemy.{i}.x','Enemy horizontal formation offset',group,x,0,10)
            add(p+f'.enemy.{i}.y','Enemy vertical formation offset',group,y,0,10)
            unit(p+f'.enemy.{i}',group+f' enemy {i+1}','LOAN')
for i in range(3):unit(f'training.loan.{i}',f'Training loan selection {i}','LOAN',i)
fields('quiz','Mech recognition test',[('rounds',3,1,10),('intro_message',55,0,372),('question_message',56,0,372),('failed_message',57,0,372)])
for i,(x,y,answer) in enumerate(zip((151,230,240,221,239,248,213,217,193,157),(186,189,168,120,88,55,69,26,38,95),(2,4,5,7,8,10,18,15,0,16))):
    fields(f'quiz.point.{i}','Mech recognition test',[('x',x,3,316),('y',y,3,196),('answer',answer,0,19)])
fields('driving','Driving and recovery',[('time_limit',215,1,32767),('first_loan_bonus',50,0,32767),
    ('corner_x',120,0,124),('corner_y',124,0,126),('clear_x',61,0,63),('clear_y',61,0,63),
    ('warning_message',78,0,372),('corner_message',79,0,372),('snicker_message',84,0,372),
    ('pickup_message',85,0,371),('rubble_tile',80,0,249),('recovery_rank_cap',3,0,4)])
for i,(x,y) in enumerate(zip((29,55,53,60,59,48,32,31),(15,17,24,33,44,46,48,27))):
    add(f'recovery.{i}.x',f'Recovery site {i+1} tile X','Driving and recovery',x,1,62)
    add(f'recovery.{i}.y',f'Recovery site {i+1} tile Y','Driving and recovery',y,1,62)
fields('invasion','Invasion',[('enemy_count',4,1,6),('ruin_after',3,1,5),('escape',1,0,1),
    ('escape_min',63,0,127),('escape_max',192,128,255),('retain_loan',1,0,1),('skill_award',1,0,1)])
for i in range(6):
    unit(f'invasion.enemy.{i}',f'Invasion attacker {i+1}','JENNER')
    add(f'invasion.message.{i}',f'Invasion message {i} (0 is initial warning)','Invasion',141+i,0,372)
fields('encounter','Encounters',[('enabled',1,0,1),('offer',1,0,1),('avoid_mask',3,0,255),
    ('infantry_slots',8,0,8),('mech_slots',4,0,4),('distance',10,1,24),('distance_mask',7,0,15),
    ('starport_mechs',0,0,1),('updated_roster',1,0,1),('cash_mask',15,0,255),('cash_base',3,0,255),
    ('cash_min',2,0,65535),('field_salvage',1,0,1),('mech_salvage',1,0,1),('salvage_in_towns',0,0,1),
    ('salvage_expert',4,0,4),('heal_after',1,0,1),('essential_people',2,1,2)])
for i in range(3):unit(f'encounter.mech.{i}',f'Random encounter mech {i}','ENCOUNTER',i)
for i in range(22):add(f'encounter.weapon.{i}',f'Infantry weapon roll {i}','Encounters',0,0,13,f'encounter_weapons[{i}]')
fields('rex','Rex and ambush',[('x',105,0,125),('y',94,2,127),('spawn_x',114,0,117),('spawn_y',93,2,117),
    ('enemy_count',2,1,5),('count_mask',3,0,3),('constitution',12,2,12),('dexterity',9,2,12),('charisma',8,2,12),('weapon',7,0,13),
    ('enemy_weapons',8,1,14),('enemy_skill_mask',1,0,3)])
unit('rex.mech','Rex stored mech','COMMANDO')
for i in range(7):add(f'rex.skill.{i}',f'Rex skill {i}','Rex and ambush',0,0,4,f'rex_skills[{i}]')
for i in range(8):
    for axis in ('x','y'):add(f'rex.enemy.{i}.{axis}',f'Ambush member {i} {axis.upper()} offset','Rex and ambush',0,0,8,f'rex_{axis}[{i}]')
fields('prison','Prison mission',[('start_x',16,0,124),('start_y',36,2,126),('exit_x',0,0,124),('exit_y',20,2,126),
    ('mechs_x',20,0,110),('mechs_y',45,2,126),('guard_count',8,1,8),('guard_x',16,0,110),('guard_y',36,2,110),
    ('guard_weapons',14,1,14),('guard_skill_mask',1,0,3)])
unit('prison.reward','Prison stolen mech (empty uses service reward)','ENCOUNTER',2)
fields('arena','Arena',[('player_x',107,66,124),('player_y',87,2,125),('west_x',80,2,110),('east_x',104,2,110),
    ('spawn_y',111,2,118),('spectator_x',70,2,124),('spectator_y',102,2,126),('spectator',1,0,1),
    ('guard_count',2,0,2),('guard_x',61,2,124),('guard_y',48,2,62),('guard_spacing',64,0,64),
    ('return_x',57,0,124),('return_y',93,2,126),('escape_min',1152,0,2047),('escape_max',1287,0,2047),('escape_x',1264,0,2047),
    ('rental_roll_base',3,0,10),('rental_roll_mask',3,0,7),('damage_threshold',4,0,6),('damage_rolls',5,0,32),
    ('system_threshold',5,0,6),('field_variant',4,0,4)])
unit('arena.loan','Arena rental mech','LOAN')
for i in range(11):unit(f'arena.opponent.{i}',f'Arena opponent roll {i}','ARENA',i)
unit('arena.spectator','Arena spectator','SPECTATOR')
for i in range(2):unit(f'arena.guard.{i}',f'Arena pursuit guard {i+1}','URBANMECH')
for i in range(7):add(f'arena.reduction.{i}',f'Arena difficulty {i} armour reduction','Arena',0,0,255,f'arena_reduction[{i}]')
for i in range(16):
    for axis in ('x','y'):add(f'guards.offset.{i}.{axis}',f'Native guard formation {i} {axis.upper()}','Arena and prison formations',0,0,8,f'special_{axis}[{i}]')
# Force-field locations use native tile coordinates. A 0 mask means a fixed
# opening tile; only the original interior cells draw the terrain RNG.
strips=[[(0x1c8f,111,67,0)]+[(0x1c90+i,106,64,3) for i in range(5)]+[(0x1ccd,112,66,0)],
    [(0x1a78,111,65,0)]+[(0x1a79+i,106,64,3) for i in range(4)]+[(0x1ab5+i,106,64,3) for i in range(6)]+[(0x1abb,112,66,0)],
    [(0x1ad9,113,64,0)]+[(0x1c9d+i,107,64,3) for i in range(4,60,8)]+[(0x1cd9,112,65,0)]]
for variant,cells in enumerate(strips,1):
    for i,(raw,closed,opened,mask) in enumerate(cells):
        n=raw-0x101d;x=n//64%8*8+n%8;y=n//512*8+n%64//8
        fields(f'arena.field.{variant}.{i}',f'Arena field layout {variant}',[
            ('x',x,0,63),('y',y,0,63),('closed',closed,0,249),('open',opened,0,246),('mask',mask,0,3)])
fields('cache','Cache access and ending',[('access_flag',54,0,99),('start_x',6,0,125),('start_y',126,0,127),
    ('room_x',4,0,61),('room_y',34,0,47),('room_return_x',69,0,125),('room_return_y',57,0,127),
    ('secret_x_min',1,0,125),('secret_x_max',4,0,125),('secret_y',84,0,127),('hall_x',0,0,61),('hall_y',42,0,58),
    ('supply_x',78,0,126),('supply_y_min',12,0,126),('supply_y_max',16,0,126),
    ('find_x',124,0,126),('find_y',4,0,126),('room_door_x',72,0,126),('room_door_y',56,0,126),
    ('ending_x1',4,0,126),('ending_y1',4,0,126),('ending_x2',2,0,126),('ending_y2',14,0,126),
    ('require_supply',1,0,1),('require_password',1,0,1),('require_find',1,0,1),('quit_at_end',1,0,1)])
for i in range(33):
    for name,member,hi in [('x','tx',125),('y','ty',127),('color','color',2)]:
        add(f'cache.terminal.{i}.{name}',f'Terminal {i+1} {name}','Cache terminals',0,0,hi,f'cache_{member}[{i}]')
for i in range(12):
    for name,member,hi in [('x','dx',120),('y','dy',126),('red','red',33),('blue','blue',33),('yellow','yellow',33)]:
        add(f'cache.door.{i}.{name}',f'Door {i+1} {name}','Cache doors',0,0,hi,f'cache_{member}[{i}]')
for i in range(7):add(f'cache.password.{i}',f'Password marked cell {i+1} (native map order)','Cache puzzle',0,0,767,f'cache_password[{i}]',True)
for i in range(18):add(f'cache.secret.{i}',f'Secret passage tile {i}','Cache puzzle',0,0,249,f'cache_secret[{i}]')
for i in range(12):add(f'cache.door_tile.{i}',f'Door animation tile {i}','Cache puzzle',0,0,249,f'cache_door_tiles[{i}]')

def enum(key):return key.upper().replace('.','_')
def generate():
    header=['/* Generated by tools/make_chi_missions.py. */','enum {']
    header += [f'    BTP_MIS_{enum(p["id"])},' for p in PARAMETERS]+['    BTP_MIS_COUNT','};','enum {']
    header += [f'    BTP_MUNIT_{enum(p["id"])},' for p in UNITS]+['    BTP_MUNIT_COUNT','};','']
    header += ['enum {']+[f'    BTP_TRAIN_{enum(p["id"][11:])} = {i},' for i,p in enumerate(p for p in PARAMETERS if p['id'].startswith('training.2.'))]+['};','']
    (ROOT/'port/data/chi_mission_ids.h').write_text('\n'.join(header))
    rows=[]
    for p in PARAMETERS:
        offset='offsetof(BtpCombatData,'+p['member']+')' if p['member'] else '0'
        rows.append('    {'+','.join([json.dumps(p[k]) for k in ('id','label','group')]+[str(p[k]) for k in ('minimum','maximum','default')]+[offset,str(2 if p['word'] else 1 if p['member'] else 0)])+'},')
    (ROOT/'port/data/chi_mission_parameters.inc').write_text('\n'.join(rows)+'\n')
    (ROOT/'port/data/chi_mission_units.inc').write_text('\n'.join('    {'+','.join((json.dumps(u['id']),json.dumps(u['label']),'BTP_MECH_'+u['kind'],str(u['index'])))+'},' for u in UNITS)+'\n')
    schema={'$schema':'https://json-schema.org/draft/2020-12/schema','title':'Native CHI mission and campaign content','type':'object','additionalProperties':False,
        'required':['format','schema_version','parameters'], 'properties':{'format':{'const':'btp-chi-missions-v1'},'schema_version':{'const':1},
        'parameters':{'type':'object','additionalProperties':False,'properties':{p['id']:{'type':'integer','minimum':p['minimum'],'maximum':p['maximum'],'description':p['label']} for p in PARAMETERS}},
        'units':{'type':'object','additionalProperties':False,'properties':{u['id']:{'type':'string','maxLength':63,'description':u['label']+'; empty retains the native template'} for u in UNITS}}}}
    (ROOT/'schemas/chi-missions-v1.schema.json').write_text(json.dumps(schema,indent=2)+'\n')
if __name__=='__main__':generate()
