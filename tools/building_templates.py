"""Reusable service buildings assembled from normal, editable event nodes."""
import copy
from editor_model import EditorError
from world_editing import identity

PRESETS={'Repair depot':('repair','rearm'),'Clinic':('heal',),'Salvage yard':('salvage',),
         'Full service depot':('repair','rearm','heal','salvage')}

def service_building(document,preset,name,costs,mech=None,door=None):
    if preset not in PRESETS:raise EditorError('Choose a service building template.')
    a=copy.deepcopy(document.adventure);events=a['events'];prefix=document.manifest['package_id']
    end=next(e['id'] for e in events if e['op']=='end')
    def add(op,**fields):
        e=dict(id=identity(prefix,events,'service'),op=op,**fields);events.append(e);return e
    menu=add('choice',text=f'{name}. Prices cover the selected service for your whole party.',portrait='none',options=[],cancel=end)
    for op in PRESETS[preset]:
        cost=int(costs[op])
        if not 0<=cost<=999999:raise EditorError('Service prices must be 0..999999.')
        ok=add('say',text='Work completed. Your account has been charged the agreed price.',next=menu['id'])
        fail=add('say',text='Unable to complete this work. Check your funds, crew and available bays. No payment was taken.',next=menu['id'])
        unchanged=add('say',text='There is no work to do. No payment was taken.',next=menu['id'])
        command=add(op,cost=cost,next=ok['id'],failure=fail['id'],unchanged=unchanged['id'])
        if op=='salvage':
            if not mech:raise EditorError('Choose a salvage chassis.')
            command['mech']=mech
        menu['options'].append(dict(label=f'{op.title()} ({cost})',next=command['id']))
    menu['options'].append(dict(label='Leave',next=end))
    if door:
        selected=next((d for m in a['maps'] for d in m['entrances'] if d['id']==door),None)
        if not selected:raise EditorError('The selected entrance no longer exists.')
        selected['event']=menu['id']
    from campaign_limits import limits
    maximum=limits(a)['events']
    if len(events)>maximum:raise EditorError(f'This building exceeds the {maximum}-event limit for this campaign format.')
    document.replace_adventure(a)
    return menu['id']
