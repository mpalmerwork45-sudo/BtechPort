"""Encounter groups, reserves and lifecycle hooks in the shared mission view."""
import copy
import tkinter as tk
from tkinter import ttk
from adventure_editing import new_id
from editor_model import EditorError
from editor_session import guard


def description(collection,value):
    if collection=='combat_groups':
        return f"{value['affiliation']} / {'reserve' if value['reserve'] else 'initial'} / {len(value['units'])} units / {value['encounter']}"
    timer=f" / round {value['round']}"+(f" then every {value['every']}" if value.get('every') else '') if 'round' in value else ''
    return f"{value['when']}{timer} / {value['encounter']}"


def edit(editor,collection,new=False,identity=None):
    from adventure_editor import Form
    doc=editor.document;a=doc.adventure;listing=editor.listings[collection]
    identity=identity or (listing.selection()[0] if listing.selection() else None)
    if not new and not identity:return
    original=next((r for r in a.get(collection,[]) if r['id']==identity),None) if not new else None
    if not new and original is None:raise EditorError('This combat mission definition no longer exists.')
    if not a['encounters']:raise EditorError('Create an encounter in the map editor first, then add its groups and hooks.')
    groups=collection=='combat_groups';kind='group' if groups else 'hook'
    default=dict(id=new_id(doc,collection,kind),encounter=a['encounters'][0]['id'])
    if groups:default.update(name='New group',affiliation='hostile',reserve=1,units=[])
    else:default.update(when='round_end',repeat='once',round=3,every=0,event=next((e['id'] for e in a['events'] if e['op']=='end'),a['events'][0]['id']))
    record=copy.deepcopy(original or default)
    f=Form(editor,'Combat group / escort actors' if groups else 'Combat hook / round timer');f.track(record)
    f.field('id',record['id']);f.field('encounter',record['encounter'],[e['id'] for e in a['encounters']])
    if groups:
        f.field('name',record['name']);f.field('affiliation',record['affiliation'],['hostile','friendly','neutral'])
        f.field('reserve',str(record['reserve']),['0','1'],label='Reserve (1 waits for Reinforce; 0 starts deployed)')
        ttk.Label(f.body,text='Actor positions and waypoints use half-tiles (8 pixels). Friendly actors return fire; neutral actors only travel.\n'
                  'Routes stop at each waypoint before continuing next round. Combat groups never join the owned party.',wraplength=540).grid(row=f.row,column=0,columnspan=2,sticky='w',padx=8,pady=8);f.row+=1
        units=tk.Listbox(f.body,height=6,width=65,exportselection=False);units.grid(row=f.row,column=0,columnspan=2,sticky='ew',padx=8);f.row+=1
        def refresh():
            units.delete(0,'end')
            for u in record['units']:units.insert('end',f"{u['definition']} at {u['at']} / {len(u.get('waypoints',[]))} waypoints")
        def actor(editing=False,recovered_index=None):
            selected=units.curselection();index=recovered_index if recovered_index is not None else selected[0] if editing and selected else None
            if editing and index is None:return
            encounter=next(e for e in a['encounters'] if e['id']==f.values['encounter'].get())
            unit=record['units'][index] if index is not None else dict(kind='mech',definition=doc.content['mechs'][0]['id'],at=[min(120,encounter['party_at'][0]+8),encounter['party_at'][1]])
            child=Form(f,'Mission actor');child.recovery_action=dict(method='actor',args=[editing,index])
            control=child.field('kind',unit['kind'],['mech','person'],label='Unit type (mech includes vehicles)')
            def choices():return [v['id'] for v in (doc.content['mechs'] if child.values['kind'].get()=='mech' else a['people'])]
            definition=child.field('definition',unit['definition'],choices())
            control.bind('<<ComboboxSelected>>',lambda _:(definition.configure(values=choices()),child.values['definition'].set(choices()[0])))
            child.field('x',unit['at'][0]);child.field('y',unit['at'][1])
            child.field('movement',unit.get('movement','walk'),['walk','run'])
            child.field('waypoints','; '.join(f'{x},{y}' for x,y in unit.get('waypoints',[])),label='Route: x,y; x,y (up to 16 waypoints)')
            def apply_actor(v):
                try:points=[[int(n.strip()) for n in p.split(',')] for p in v['waypoints'].split(';') if p.strip()]
                except ValueError:raise EditorError('Waypoints use whole-number pairs, for example 20,24; 20,36.')
                if len(points)>16 or any(len(p)!=2 or any(n<0 or n>127 for n in p) for p in points):raise EditorError('Use up to 16 x,y pairs, each coordinate 0..127.')
                result=dict(kind=v['kind'],definition=v['definition'],at=[int(v['x']),int(v['y'])])
                if points:result.update(waypoints=points,movement=v['movement'])
                if index is None:
                    if len(record['units'])==12:raise EditorError('A combat group supports up to 12 actors.')
                    record['units'].append(result)
                else:record['units'][index]=result
                refresh()
            child.submit(apply_actor);return child
        bar=ttk.Frame(f.body);bar.grid(row=f.row,column=0,columnspan=2,sticky='w',padx=8,pady=8);f.row+=1
        for label,callback in [('Add actor',actor),('Edit actor',lambda:actor(True))]:ttk.Button(bar,text=label,command=lambda fn=callback:guard(editor,fn)).pack(side='left',padx=3)
        def remove():
            if units.curselection():record['units'].pop(units.curselection()[0]);refresh()
        ttk.Button(bar,text='Remove',command=remove).pack(side='left',padx=3)
        units.bind('<Double-1>',lambda _:guard(editor,lambda:actor(True)))
        f.recovery_children={'actor':actor};f.on_restore=refresh;refresh()
    else:
        f.field('when',record['when'],['start','round_start','round_end','destroyed','arrival'])
        f.field('repeat',record['repeat'],['once','always'])
        f.field('round',record.get('round',1),label='First round (round hooks only)')
        f.field('every',record.get('every',0),label='Repeat every N rounds (0 = only first round)')
        f.field('group',record.get('group','any'),['any']+[g['id'] for g in a.get('combat_groups',[])],label='Group (destruction / arrival only)')
        f.field('event',record['event'],[e['id'] for e in a['events']])
        ttk.Label(f.body,text='Hooks wait for completed combat messages, effects and sounds. End returns to combat.\n'
                  'Round timers use simulation rounds; menus and dialogues do not advance them. Use Always for recurring timers.\n'
                  'Arrival fires for each actor reaching its final waypoint. Check group arrived/alive counts to require everyone.',wraplength=540).grid(row=f.row,column=0,columnspan=2,sticky='w',padx=8,pady=8);f.row+=1
    def apply(v):
        if original and v['id']!=original['id']:raise EditorError('Existing IDs stay stable; create a new definition to change its identity.')
        result=dict(id=v['id'],encounter=v['encounter'])
        if groups:result.update(name=v['name'],affiliation=v['affiliation'],reserve=int(v['reserve']),units=copy.deepcopy(record['units']))
        else:
            result.update(when=v['when'],repeat=v['repeat'],event=v['event'])
            if v['when'] in ('round_start','round_end'):result.update(round=int(v['round']),every=int(v['every']))
            if v['when']=='arrival' or (v['when']=='destroyed' and v['group']!='any'):result['group']=v['group']
        data=copy.deepcopy(doc.adventure);items=data.setdefault(collection,[])
        if original:items[next(i for i,r in enumerate(items) if r['id']==original['id'])]=result
        else:items.append(result)
        doc.replace_adventure(data);doc.validate();editor.owner.refresh();editor.refresh();listing.selection_set(result['id'])
    f.submit(apply);return f
