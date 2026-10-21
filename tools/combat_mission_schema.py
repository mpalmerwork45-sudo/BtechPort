"""Structural mission-combat descriptors shared by docs and conformance tests.

The native loader additionally resolves encounter/group references, checks
deployment/waypoint terrain and rejects unsafe combat-hook event routes.
"""
from authoring_contract import ID,TEXT,obj,array,enum,integer

POINT=array(integer(0,127),2,2)
CONDITIONS=[obj(dict(kind={'const':kind},id=ID,compare=enum('eq','ne','lt','le','gt','ge'),value=integer(0,1 if kind=='group_deployed' else 12)),
                ['kind','id','compare','value']) for kind in ('group_alive','group_destroyed','group_deployed','group_arrived')]
CONDITIONS.append(obj(dict(kind={'const':'combat_round'},compare=enum('eq','ne','lt','le','gt','ge'),value=integer(0,65535)),['kind','compare','value']))
GROUP=obj(dict(id=ID,name=dict(type='string',minLength=1,maxLength=63),encounter=ID,affiliation=enum('hostile','friendly','neutral'),reserve=integer(0,1),
    units=array(obj(dict(kind=enum('mech','person'),definition=ID,at=POINT,waypoints=array(POINT,0,16),movement=enum('walk','run')),['kind','definition','at']),1,12)),
    ['id','name','encounter','affiliation','reserve','units'])
HOOKS=[]
for when in ('start','round_start','round_end','destroyed','arrival'):
    properties=dict(id=ID,encounter=ID,when={'const':when},repeat=enum('once','always'),event=ID)
    required=list(properties)
    if when in ('round_start','round_end'):
        properties.update(round=integer(1,65535),every=integer(0,65535));required+=['round','every']
    if when in ('destroyed','arrival'):properties['group']=ID
    if when=='arrival':required+=['group']
    HOOKS.append(obj(properties,required))
EVENTS=[obj(dict(id=ID,op={'const':'reinforce'},group=ID,radius=integer(0,8),next=ID,failure=ID),['id','op','group','radius','next','failure']),
        obj(dict(id=ID,op={'const':'battle_end'},result=enum('win','loss','flee'),next=ID,failure=ID),['id','op','result','next','failure'])]


def extend(schema):
    p=schema['properties'];p['combat_groups']=array(GROUP,0,16);p['combat_hooks']=array(dict(oneOf=HOOKS),0,32)
    encounter=p['encounters']['items'];encounter['properties']['completion']=enum('eliminate','scripted')
    encounter['properties']['enemies']['minItems']=0
    events=p['events']['items']['oneOf']
    events[:]=[e for e in events if e['properties']['op'].get('const') not in ('reinforce','battle_end')]+EVENTS
    check_event=next(e for e in events if e['properties']['op'].get('const')=='check')
    conditions=check_event['properties']['conditions']['items']['oneOf']
    conditions[:]=[c for c in conditions if c['properties']['kind'].get('const') not in ('group_alive','group_destroyed','group_deployed','group_arrived','combat_round')]+CONDITIONS
    return schema
