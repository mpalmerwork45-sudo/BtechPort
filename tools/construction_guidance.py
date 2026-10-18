"""CHI adapter budgets, not a claim of full tabletop construction legality."""
def report(content,unit):
    vehicle=unit.get('kind')=='vehicle'
    weapons={w['id']:w for w in content['weapons']}
    equipment={e['id']:e for e in content.get('equipment',[])}
    used={p:0 for p in unit['structure']};cooling=unit['engine_heat_sinks'];jump=unit['movement']['jump']
    armor=dict(unit['armor'])
    for mount in unit['loadout']:used[mount['location']]+=1
    for p,n in unit.get('external_heat_sinks',{}).items():used[p]+=n;cooling+=n
    for item in unit.get('equipment',[]):
        kind=equipment[item['definition']]['behavior'];n=item['quantity'];p=item['location']
        if kind=='heat_sink':used[p]+=n;cooling+=n
        elif kind=='engine_heat_sink':cooling+=n
        elif kind=='armor_plating':armor[p]+=n
        elif kind=='jump_jet':jump+=n
    heat=sum(weapons[m['weapon']]['heat'] for m in unit['loadout'])
    lines=[unit['name'],f"Walk {unit['movement']['walk']} | Run {(unit['movement']['walk']*3+1)//2} | Jump {jump}",
           f"Weapons {len(unit['loadout'])}/10 | Armor {sum(armor.values())} | Structure {sum(unit['structure'].values())}"]
    if not vehicle:
        lines+=[f'Alpha strike heat {heat} | Cooling {cooling}/30 (before damage/terrain)',
                f'Heat gain while walking: {max(0,heat+1-cooling)}', '', 'Critical entries by location:']
        slots=dict(zip(('left_arm','left_torso','left_leg','head','center_torso','right_arm','right_torso','right_leg'),(7,7,2,1,2,7,7,2)))
        lines += [f"  {p.replace('_',' ')}: {used[p]}/{slots[p]}" for p in used]
    lines+=['','Ammunition (full salvos):']
    lines += [f"  {weapons[m['weapon']]['name']}: {m['ammunition']}" for m in unit['loadout'] if m['ammunition']]
    lines+=['','Validate checks these adapter capacities. Tonnage, technology eras,',
            'tabletop critical sizes and component prices are not enforced.']
    return '\n'.join(lines)

def show(editor):
    import tkinter as tk
    from tkinter import ttk
    editor.apply_form();window=tk.Toplevel(editor.window);window.title('Unit construction guidance')
    ttk.Label(window,text=report(editor.document.content,editor.item()),padding=20,justify='left').pack()
