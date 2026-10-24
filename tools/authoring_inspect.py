"""Bounded, read-only projections for people and automated authors."""
import hashlib
import json
import subprocess
from pathlib import Path
from authoring_contract import API_VERSION, OPERATIONS, COLLECTIONS, AuthoringError
from authoring_service import revision, find
from event_editing import edges, editor_data
from world_editing import all_worlds, token


def capabilities(tool):
    from asset_catalogue import FIELDS,NUMERIC,KINDS
    try:
        p=subprocess.run([str(Path(tool).resolve()),'capabilities'],capture_output=True,text=True,timeout=10)
        if p.returncode:raise ValueError(p.stderr.strip() or 'Rebuild btp-project with authoring support.')
        runtime=json.loads(p.stdout)
    except (OSError,ValueError,subprocess.TimeoutExpired) as exc:
        raise AuthoringError('runtime.unavailable',str(exc)) from exc
    return dict(api_version=API_VERSION,runtime=runtime,runtime_sha256=hashlib.sha256(Path(tool).read_bytes()).hexdigest(),
        operations=OPERATIONS, features=dict(transactional_batches=True,expected_revision=True,dry_run=True,
        persisted_requests=True,gui_undo=True,live_remote_session=False,live_local_session=True,protected_regions=True,
        change_review=True,partial_change_groups=True,named_protection_overrides=True,shared_construction_library=True,
        native_chi_spatial=True,native_chi_presentation=True,native_chi_bld_sources=True,native_chi_event_bridge=True,native_chi_reconstruction_recipes=True,
        mission_regions=True,typed_mission_variables=True,explicit_objective_states=True,compound_conditions=True,
        combat_hooks=True,round_timers=True,reinforcements=True,escort_waypoints=True,
        campaign_source_modules=True,deterministic_source_builds=True,source_diagnostics=True,recorded_campaign_recipes=True,
        reinforcement_events=False,escort_events=False,asset_search=True,contact_sheets=True,animation_strips=True,event_graph_preview=True,
        world_city_previews=True,native_navigation_checks=True,objective_access_warnings=True,scenario_suites=True,
        scenario_seeds=True,scenario_checkpoints=True,scenario_checkpoint_starts=True,named_checkpoints=True,
        combat_sampling=True,fixture_batches=True,selected_case_reruns=True,
        world_route_scenarios=True,world_navigation_checks=True,world_discovery_assertions=True,
        world_change_review=True,world_region_protection=True,review_scenario_suggestions=True,retained_suite_inputs=True),
        discovery=dict(sources=['project','library','construction-library','atlas','all'],kinds=list(KINDS),fields=sorted(FIELDS),numeric_fields=sorted(NUMERIC),
            examples=['kind:mech class:light weapon:lrm walk>=5','kind:tile tag:industrial animated:true','kind:construction tag:industrial']),
        scenarios=dict(format='btp-author-scenario-v1',suite_format='btp-author-suite-v1',battle_policies=['computer','hold','retreat'],
            seed_encoding='24-bit integer, little-endian RNG bytes; default 11223583',
            walk_destinations=['entrance ID','map ID + local movement coordinates','world ID + world movement coordinates'],
            discovery_coordinates='World tiles; each discovery cell covers 8 by 8 tiles, with a 3 by 3 reveal around the cursor.',
            coverage='Declared inputs and actual world travel; bounded initial-party local/world geometry. Arbitrary conditions/Lua and general balance are unproven.'),
        bounds=dict(operations_per_batch=512,request_bytes=16777216,query_page=100,receipts=512,contact_sheet_items=32,
            animation_frames_per_strip=32,preview_region_tiles=64,scenario_steps=256,scenario_ticks=120000,scenario_seconds=45,
            suite_runs=32,suite_cases=16,seeds_per_case=8,suite_seconds=300,
            route_positions_default=262144,route_positions_max=1048576,analysis_world_positions=262144),
        collaboration=dict(transport='local-file-inbox',session_format='btp-author-session-v1',review_format='btp-author-review-v1',
            policies=['review','apply_within_scope'],scope='One explicitly opened project or library editing scope; rules and actual diffs are checked.',
            protection_kinds=['object','fields','map_region','world_region'],rules_max=256,session_jobs_max=256,queued_jobs_max=8,
            world_protected_cells_max=4194304,world_overview_pixels_max=1024,world_detail_crops_max=64,
            reviewed_request_bytes=2097152,import_file_bytes=16777216,import_total_bytes=67108864,
            preview_maps_max=8,checks_per_review=32,heartbeat_seconds=15,
            scenario_selections_per_review=32,dependency_nodes=16384,dependency_edges=262144,
            suite_input_files=256,suite_input_bytes=67108864),
        source_projects=dict(format='btp-campaign-source-v1',index='SOURCE.json',files_max=4096,bytes_max=134217728,
            commands=['source convert','source build','source locations'],runtime_limits='See runtime.limits and format_limits; campaign.upgrade opts into v3.'),
        recipes=dict(commands=['recipe list','recipe build'],format='btp-greybank-recipe-v1',guide='docs/CAMPAIGN_RECIPES.md'),
        chi_recipes=dict(commands=['chi-recipe export','chi-recipe build'],format='btp-chi-recipe-v1',schema='schemas/chi-recipe-v1.schema.json',guide='docs/CHI_RECONSTRUCTION.md',dependency='User-supplied unmodified DOS 1.03 files; matching importer revision'),
        schemas='schemas/',guide='docs/AI_AUTHORING_GUIDE.md')


def inventory(doc):
    files=[]
    for name,data in sorted(doc.files().items()):
        files.append(dict(file=name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
    original=doc.manifest['requires'] not in ('none','chi-local-dos-1.03')
    return dict(files=files,dependency=doc.manifest['requires'],
        play_assets=dict(status='not_checked' if original else 'included',
                         reason='Set --data/--combat-data/--world-data/--dialogue-data for player previews.' if original else None),
        provenance_files=[name for name in ('LIBRARY-SOURCES.json','sources.json','SOURCE-README.md','ART-SOURCE-README.md','CREDITS.md','README.md') if (doc.root/name).is_file()],
        tile_sources=editor_data(doc).get('tile_sources',{}),
        scripts=dict(count=len(doc.manifest.get('scripts',[])),analysis='Explicit routes only; Lua source is opaque to reference queries.'))


def summary(doc, tool):
    caps=capabilities(tool)['runtime'];a=doc.adventure or {}
    limits=dict(caps['limits'],**caps.get('format_limits',{}).get(a.get('format'),{}))
    counts={key:len(a.get(key,[])) for key in ('maps','events','flags','tiles','jigsaws','people','shops','encounters','objectives','variables','regions','combat_groups','combat_hooks')}
    worlds=all_worlds(a);counts['worlds']=len(worlds)
    counts.update(images=len(doc.art['images']),art_pixels=sum(im['width']*im['height']*len(im['frames']) for im in doc.art['images']),
        animation_tracks=sum(len(im.get('animations',{})) for im in doc.art['images']),
        world_sectors_total=sum(len(w['pieces'])*len(w['pieces'][0])//64 for w in worlds))
    placed={c for w in worlds for c in w['cities']}
    counts['discovery_cells']=sum(len(w['pieces'])*len(w['pieces'][0]) for w in worlds)
    if worlds or a.get('schema_version',1)>=3:
        counts['discovery_cells']+=sum(((m['origin'][0]%8+len(m['rows'][0])+7)//8)*((m['origin'][1]%8+len(m['rows'])+7)//8)
                                       for m in a.get('maps',[]) if m['id'] not in placed)
    native=a.get('chi_native')
    if native:
        counts.update(worlds=1,events=0,world_sectors_total=256,discovery_cells=16384)
        limits.update(maps=15,worlds=1,events=0,flags=0,people=0,shops=0,encounters=0)
    capacity={key:dict(used=count,limit=limits[key],remaining=limits[key]-count) for key,count in counts.items()}
    for key in ('mechs','weapons','equipment','ammunition','presentations'):
        count=len(doc.content.get(key,[]));maximum=limits['definitions_per_collection']
        capacity[key]=dict(used=count,limit=maximum,remaining=maximum-count)
    return dict(api_version=API_VERSION,project=dict(id=doc.manifest['package_id'],title=doc.manifest['title'],
        content_version=doc.manifest['content_version'],requires=doc.manifest['requires'],rules_profile=doc.manifest['rules_profile']),
        revision=revision(doc),authoring=dict(mode='source' if doc.source is not None else 'package',
            index='SOURCE.json' if doc.source is not None else 'project.json'),
        capacity=capacity,start=a.get('start'),coordinate_spaces=caps['coordinate_spaces'],
        protection=editor_data(doc).get('authoring_protection',[]),
        maps=[dict(id=m['id'],name=m['name'],width=len(m['rows'][0]),height=len(m['rows']),origin=m['origin'],entrances=len(m['entrances']),overlays=len(m['overlays'])) for m in a.get('maps',[])],
        worlds=[dict(id=w['id'],name=w['name'],width_tiles=8*len(w['pieces'][0]),height_tiles=8*len(w['pieces']),cities=w['cities']) for w in worlds],
        objectives=a.get('objectives',[]),flags=a.get('flags',[]),scripts=doc.manifest.get('scripts',[]),
        animated_tiles=[dict(id=i['id'],frames=len(i['frames']),frame_ticks=i.get('frame_ticks',8)) for i in doc.art['images'] if i['kind']=='tile' and len(i['frames'])>1][:30],
        animated_tile_count=sum(i['kind']=='tile' and len(i['frames'])>1 for i in doc.art['images']),
        native_chi=(dict(spatial=doc.manifest.get('chi_spatial'),presentation=doc.manifest.get('chi_presentation'),services=native.get('services',{}),
            world=native['world'],map_slots=15,story='native BLD execution with labelled source and service content and mission settings',
            operations=['chi.update','chi.town.move','chi.jigsaw.bind','chi.art.copy']) if native else None),
        native_bld=dict(source=doc.manifest.get('chi_scripts'),programs=26,instructions_per_program=2048,program_bytes=9000,
            operations=['bld.enable','bld.update','bld.insert','bld.remove'],service_parameters=doc.manifest.get('chi_services'),mission_settings=doc.manifest.get('chi_missions')) if doc.manifest.get('chi_edition') or doc.manifest.get('requires')=='chi-local-dos-1.03' else None,
        native_quests=quest_summary(doc),
        queries=['objects','object','usages','map','routes','inventory'])


def quest_summary(doc):
    if not doc.manifest.get('chi_bridge'):return None
    from chi_bridge import events,data
    a,b=events(doc),data(doc)
    return dict(events=len(a['events']),maps=len(a['maps']),entrances=len(b['entrances']),native_calls=len(b['native_calls']),
        frames=4,services=['ComStar buy shares','ComStar sell shares'],
        collections=['quest-events','quest-maps','quest-encounters','bridge-entrances','bridge-calls'],
        startup='Native campaign; quest start/party fields are editor defaults only.',guide='docs/CHI_QUEST_AUTHORING.md')


def records(doc, collection):
    if collection in ('quest-events','quest-maps','quest-encounters','bridge-entrances','bridge-calls'):
        from chi_bridge import events,data
        if collection.startswith('quest-'):return events(doc)[collection[6:]]
        return data(doc)['entrances' if collection=='bridge-entrances' else 'native_calls']
    if collection in ('native-mission-parameters','native-mission-units'):
        from chi_missions import catalogue
        value=catalogue(doc);return value['parameters' if collection=='native-mission-parameters' else 'units']
    if collection in ('native-service-parameters','native-actions'):
        from chi_services import catalogue
        value=catalogue(doc);return value['parameters' if collection=='native-service-parameters' else 'actions']
    if collection in ('native-scripts','native-instructions'):
        from chi_bld import data
        programs=data(doc)['programs']
        return programs if collection=='native-scripts' else [dict(n,program=p['id']) for p in programs for n in p['nodes']]
    if collection=='native-services':
        from chi_spatial import data
        return list(data(doc).get('services',{}).values())
    if (doc.adventure or {}).get('chi_native') and collection in ('maps','tiles','jigsaws','native-npcs','native-entrances'):
        from chi_spatial import data
        value=data(doc)
        if collection in ('maps','tiles'):return value[collection]
        if collection=='jigsaws':return value['world']['jigsaws']
        return [dict(v,map=m['id']) for m in value['maps'] for v in m['npcs' if collection=='native-npcs' else 'entrances']]
    if collection=='worlds':
        if (doc.adventure or {}).get('chi_native'):
            from chi_spatial import data
            return [data(doc)['world']]
        return all_worlds(doc.adventure or {})
    if collection=='native-resources':
        from chi_resources import inventory
        return inventory(doc)['resources']
    if collection in ('construction_sets','map_patterns','map_constructions'):
        return editor_data(doc).get(collection,[])
    if collection=='entrances':return [dict(e,map=m['id']) for m in (doc.adventure or {}).get('maps',[]) for e in m['entrances']]
    if collection not in COLLECTIONS:raise AuthoringError('query.invalid','Choose a declared collection.')
    return (getattr(doc,COLLECTIONS[collection]) or {}).get(collection,[])


def compact(value):
    result=dict(value)
    for key in ('rows','frames','pieces','overlays','cells','rendered','footprint','nodes'):
        if key in result:
            data=result.pop(key)
            result[key+'_summary']=dict(count=len(data),width=len(data[0]) if data and isinstance(data[0],(list,str)) else None)
    return result


def query(doc, kind, collection=None, identity=None, offset=0, limit=30, rect=None):
    if not 1<=limit<=100 or offset<0:raise AuthoringError('query.bounds','Use limit 1..100 and a nonnegative offset.')
    if kind in ('objects','object'):
        values=records(doc,collection)
        if kind=='object':return compact(find(values,identity)[1])
        return dict(total=len(values),offset=offset,items=[compact(v) for v in values[offset:offset+limit]],
                    next_offset=offset+limit if offset+limit<len(values) else None)
    if kind=='usages':
        from editor_dependencies import usages
        values=usages(doc,identity)
        return dict(total=len(values),offset=offset,items=[dict(object_id=v.asset,path=v.location) for v in values[offset:offset+limit]],
                    next_offset=offset+limit if offset+limit<len(values) else None,lua='Not analysed')
    if kind=='routes':
        values=(doc.adventure or {}).get('events',[])
        return dict(total=len(values),offset=offset,items=[dict(id=e['id'],op=e['op'],edges=[dict(branch=b,target=t) for b,t in edges(e)]) for e in values[offset:offset+limit]],
                    next_offset=offset+limit if offset+limit<len(values) else None)
    if kind=='map':
        from adventure_editing import composite,scene_markers
        a=doc.adventure or {};i,scene=find(a.get('maps',[]),identity);x,y,w,h=rect or (0,0,8,8)
        if not 1<=w<=32 or not 1<=h<=32 or min(x,y)<0 or x+w>len(scene['rows'][0]) or y+h>len(scene['rows']):
            raise AuthoringError('coordinate.bounds','Choose an in-bounds map rectangle, at most 32 by 32 tiles.')
        grid=composite(scene);ids={token(t):t['id'] for t in a['tiles']};definitions={t['id']:t for t in a['tiles']}
        rows=[[ids[t] for t in row[x:x+w]] for row in grid[y:y+h]];used={t for row in rows for t in row}
        return dict(id=scene['id'],coordinate_space='map_tile',rect=[x,y,w,h],rows=rows,
                    tiles=[definitions[t] for t in sorted(used)],markers=[m for m in scene_markers(a,i) if x*2<=m['at'][0]<(x+w)*2 and y*2<=m['at'][1]<(y+h)*2],
                    marker_coordinate_space='movement')
    if kind=='inventory':
        data=inventory(doc)
        # Even attribution tables and file lists are paginated; artwork bytes
        # never enter a routine inspection response.
        sources=list(data.pop('tile_sources').items());files=data.pop('files')
        return dict(**data,files=dict(total=len(files),items=files[offset:offset+limit]),
                    tile_sources=dict(total=len(sources),items=[dict(image=k,source=v) for k,v in sources[offset:offset+limit]]))
    raise AuthoringError('query.invalid','Unsupported query: '+kind)
