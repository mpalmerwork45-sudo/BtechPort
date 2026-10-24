"""Resolve validation paths against current IDs, without retaining temp files."""
import re
from editor_dependencies import definitions
from editor_session import FieldError,scope_of


def target(document,problem):
    from authoring_contract import diagnostic
    path=problem.get('field_path') or diagnostic(Exception(problem['message']))['field_path']
    if document.manifest.get('chi_missions') and 'chi-missions.json' in problem.get('message',''):
        if path.startswith('$.parameters.'):return dict(collection='native_missions',parameter=path[len('$.parameters.'):])
        if path.startswith('$.units.'):return dict(collection='native_missions',parameter='unit:'+path[len('$.units.'):])
    if document.manifest.get('chi_services') and path.startswith('$.parameters.'):

        return dict(collection='native_services',parameter=path[len('$.parameters.'):])
    if document.manifest.get('chi_services') and path.startswith('$.broker_stock'):
        return dict(collection='native_services',parameter=None)
    ids=re.findall(r'\[([a-z][a-z0-9._-]*:[a-z][a-z0-9._-]*)\]',path)
    if problem.get('object_id') and problem['object_id'] not in ids:ids.append(problem['object_id'])
    a=document.adventure or {}
    if document.manifest.get('chi_bridge') and ('chi-events.json' in problem.get('message','') or 'chi-bridge.json' in problem.get('message','') or path.startswith(('quest.','bridge.'))):
        from chi_bridge import events,data
        known={v['id'] for key in ('events','maps') for v in events(document)[key]}|{v['id'] for key in ('entrances','native_calls') for v in data(document)[key]}
        for identity in reversed(ids):
            if identity in known:return dict(collection='chi_quests',id=identity)
    location=problem.get('location')
    if isinstance(location,dict) and (location.get('map') or location.get('world')):
        return dict(collection='location',id=problem.get('object_id'),**location)
    # The deepest ID is the entrance/enemy owner, not the first map ID.
    for identity in reversed(ids):
        if document.manifest.get('requires')=='chi-local-dos-1.03':
            from chi_bld import data as bld_data
            for program in bld_data(document)['programs']:
                if identity==program['id']:return dict(collection='native_scripts',program=program['id'])
                if any(n['id']==identity for n in program['nodes']):return dict(collection='native_scripts',program=program['id'],label=identity)
        if a.get('chi_native'):
            from chi_spatial import data
            for m in data(document)['maps']:
                for key in ('npcs','entrances'):
                    v=next((v for v in m[key] if v['id']==identity),None)
                    if v is not None:return dict(collection='native_'+key,id=identity,map=m['id'],slot=v['slot'])
        for scene in a.get('maps',[]):
            for entrance in scene['entrances']:
                if entrance['id']==identity:return dict(collection='entrances',id=identity,map=scene['id'],at=entrance['at'])
        found=definitions(document).get(identity)
        if found:
            section,collection,index,value=found
            return dict(collection=collection,id=identity,index=index,path=path,value=value)
    if path.startswith('$.start') and a.get('start'):
        return dict(collection='start',map=a['start']['map'],at=a['start']['at'])
    return None


def navigate(workspace,problem):
    scope=problem.get('scope') or scope_of(problem['owner'])
    if not scope or not scope.document or scope.document is not problem.get('document',scope.document):return False
    destination=target(scope.document,problem)
    if not destination:return False
    owner=scope.owner;collection=destination['collection'];identity=destination.get('id')
    if collection=='chi_quests':
        from chi_bridge_editor import open_quests
        open_quests(owner).show_location(identity);return True
    if collection=='native_missions':
        from chi_missions_editor import open_missions
        open_missions(owner).show_location(destination.get('parameter'));return True
    if collection=='native_services':
        from chi_services_editor import open_services
        open_services(owner).show_location(destination.get('parameter'));return True
    if collection=='native_scripts':
        from chi_bld_editor import open_scripts
        open_scripts(owner).show_location(destination['program'],destination.get('label'));return True
    if collection in ('native_npcs','native_entrances'):
        owner.edit_adventure();maps=owner.map_editor
        maps.scene_index=next(i for i,m in enumerate(maps.adventure['maps']) if m['id']==destination['map']);maps.refresh()
        maps.npc_routes(destination['slot']) if collection=='native_npcs' else maps.door_slots(destination['slot'])
        return True
    if collection in ('mechs','weapons','equipment','people'):
        kind={'mechs':'Vehicles' if destination['value'].get('kind')=='vehicle' else 'Mechs',
              'weapons':'Weapons','equipment':'Equipment','people':'Infantry'}[collection]
        workspace.open_unit(kind,identity,owner)
        suffix=destination.get('path','').rsplit(']',1)[-1].lstrip('.')
        if suffix:owner.show_error(FieldError(problem['message'],tuple(suffix.split('.'))))
        return True
    if collection=='images':
        art=owner.graphics_editor();art.selected=identity;art.edit();return True
    owner.edit_adventure();maps=owner.map_editor
    if collection=='location' and destination.get('world') and not destination.get('map'):
        from world_editing import all_worlds
        if not any(w['id']==destination['world'] for w in all_worlds(maps.adventure)):return False
        maps.edit_landscape()
        maps.world_editor.show_location(destination['world'],destination['at'],problem['message'],
            destination.get('coordinate_space','world_movement'))
        return True
    if collection=='events':
        graph=maps.event_graph();graph.selected=identity;graph.edit();graph.window.lift();graph.fit()
        field=destination.get('path','').rsplit(']',1)[-1].lstrip('.')
        if graph.properties and field:graph.properties.show_error(FieldError(problem['message'],field))
        return True
    if collection in ('variables','regions','combat_groups','combat_hooks'):
        editor=maps.missions();editor.listings[collection].selection_set(identity)
        editor.tabs.select(('regions','variables','combat_groups','combat_hooks').index(collection))
        if collection=='regions':editor.show_map()
        return True
    if collection=='objectives':
        editor=maps.event_graph().objectives();editor.listing.selection_clear(0,'end');editor.listing.selection_set(destination['index']);return True
    if collection=='encounters':
        encounter=destination['value'];destination.update(map=encounter['map'],at=encounter['party_at'])
    if collection=='maps':destination.update(map=identity,at=[0,0])
    if 'map' not in destination:return False
    from adventure_editing import scene_markers
    index=next((i for i,m in enumerate(maps.adventure['maps']) if m['id']==destination['map']),None)
    if index is None:return False
    maps.map_choice.current(index);maps.change_map();at=destination['at'];maps.cursor=tuple(at)
    marker=next((m for m in scene_markers(maps.adventure,index) if m['ref'][2]==identity or (identity is None and m['at']==at)),None)
    maps.selected_marker=marker['ref'] if marker else None
    maps.refresh_markers();maps.draw();maps.tabs.select(maps.map_tab);maps.window.lift()
    size=int(maps.zoom.get());scene=maps.scene()
    maps.canvas.xview_moveto(max(0,(at[0]*size/2-maps.canvas.winfo_width()/2)/(len(scene['rows'][0])*size)))
    maps.canvas.yview_moveto(max(0,(at[1]*size/2-maps.canvas.winfo_height()/2)/(len(scene['rows'])*size)))
    if marker:
        maps.sidebar.select(1)
        selected=maps.markers.curselection()
        if selected:maps.markers.see(selected[0])
    workspace.update_inspector();maps.status.set(problem['message']);return True
