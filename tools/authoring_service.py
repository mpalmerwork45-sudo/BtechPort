"""Transactional authoring over ProjectDocument, used by both GUI and CLI.

Every operation runs on a detached candidate. Only the validated complete
candidate enters the live document, in one history step. External files are
imports, never destinations; publishing still uses the editor's save journal.
"""
import copy
import hashlib
import json
from pathlib import Path
import time

from authoring_contract import API_VERSION, AuthoringError, COLLECTIONS, check_batch, read_json, check, obj, array, integer, TEXT, ID, enum
from editor_model import AUTHORING_RECEIPTS, EditorError, ProjectDocument, encoded
from world_editing import token, upgrade, all_worlds


def revision(document):
    digest = hashlib.sha256()
    receipt = document.source.index.get('files',{}).get(AUTHORING_RECEIPTS,'files/'+AUTHORING_RECEIPTS) if document.source is not None else AUTHORING_RECEIPTS
    for name, data in sorted(document.source_files().items()):
        if name == receipt: continue
        if document.source is not None and name=='SOURCE.json':
            index=json.loads(data);index.get('files',{}).pop(AUTHORING_RECEIPTS,None)
            data=json.dumps(index,sort_keys=True,separators=(',',':')).encode()
        # Names and lengths make concatenation unambiguous. This includes
        # authoring metadata and scripts, not just the game's save fingerprint.
        digest.update(name.encode()); digest.update(b'\0')
        digest.update(str(len(data)).encode()); digest.update(b'\0'); digest.update(data)
    return digest.hexdigest()


def detached(document):
    candidate = copy.copy(document)
    for key in ('manifest','content','adventure','art','metadata'):
        setattr(candidate, key, copy.deepcopy(getattr(document,key)))
    candidate.undo_stack=[]; candidate.redo_stack=[]
    candidate.undo_labels=[]; candidate.redo_labels=[]
    candidate._command_depth=0; candidate._command_label=None
    return candidate


def find(values, identity):
    matches=[(i,v) for i,v in enumerate(values) if v.get('id')==identity]
    if len(matches)!=1:
        raise AuthoringError('object.missing', 'Expected one existing object: '+str(identity),object_id=identity)
    return matches[0]


def put(values, value, mode='create'):
    if not isinstance(value.get('id'),str): raise AuthoringError('request.invalid','An object needs an explicit id.','$.value.id')
    old=next((i for i,v in enumerate(values) if v['id']==value['id']),None)
    if mode=='create':
        if old is not None: raise AuthoringError('object.exists','Object already exists: '+value['id'],object_id=value['id'])
        values.append(copy.deepcopy(value))
    else:
        if old is None: raise AuthoringError('object.missing','Replace needs an existing object: '+value['id'],object_id=value['id'])
        values[old]=copy.deepcopy(value)
    return value['id']


def changed_objects(before, after):
    result=[]
    def compare(section, old, new):
        for key in sorted(set(old)|set(new)):
            if old.get(key)==new.get(key): continue
            left,right=old.get(key),new.get(key)
            named=lambda items:isinstance(items,list) and all(isinstance(i,dict) and 'id' in i for i in items)
            if named(left or []) and named(right or []):
                a={v['id']:v for v in (left or [])}; b={v['id']:v for v in (right or [])}
                for identity in sorted(set(a)|set(b)):
                    if a.get(identity)==b.get(identity):continue
                    x,y=a.get(identity,{}),b.get(identity,{})
                    result.append(dict(path=section+'.'+key+'/'+identity,object_id=identity,
                        change='created' if identity not in a else 'removed' if identity not in b else 'modified',
                        fields=sorted(k for k in set(x)|set(y) if x.get(k)!=y.get(k))))
                # Collection ordering matters for handles and scene identity.
                if set(a)==set(b) and list(a)!=list(b):
                    result.append(dict(path=section+'.'+key,object_id=None,change='reordered',fields=[]))
            else:result.append(dict(path=section+'.'+key,object_id=None,change='modified',fields=[]))
    for section in ('manifest','content','adventure','art'):
        compare(section,getattr(before,section) or {},getattr(after,section) or {})
    compare('editor',json.loads(before.metadata.get('EDITOR.json',b'{}')),json.loads(after.metadata.get('EDITOR.json',b'{}')))
    for name in sorted(set(before.metadata)|set(after.metadata)):
        if name not in ('EDITOR.json',AUTHORING_RECEIPTS) and before.metadata.get(name)!=after.metadata.get(name):
            script=next((s for s in after.manifest.get('scripts',[]) if s['file']==name),None)
            result.append(dict(path=('scripts/'+script['id']) if script else 'provenance/'+name,
                               object_id=script['id'] if script else None,change='modified',fields=[]))
    return result


def _bounds(scene, layer, points):
    if layer > len(scene['overlays']): raise AuthoringError('object.missing','Overlay does not exist.')
    target=scene if layer<=0 else scene['overlays'][layer-1]
    ox,oy=(0,0) if layer<=0 else target['at']
    if any(not ox<=x<ox+len(target['rows'][0]) or not oy<=y<oy+len(target['rows']) for x,y in points):
        raise AuthoringError('coordinate.bounds','All selected cells must fit in the target layer.')


def apply_operation(doc, op, imports):
    name=op['op']; a=copy.deepcopy(doc.adventure)
    if name=='campaign.upgrade':
        from campaign_limits import upgrade_campaign
        upgrade_campaign(doc);return doc.manifest['package_id']
    if name.startswith(('map.','entrance.','marker.','world.','city.','construction.','road.','pattern.','event.','start.','flags.')) and a is None:
        raise AuthoringError('capability.unavailable','This operation requires an authored adventure.')
    scene_index=find(a['maps'],op['map'])[0] if 'map' in op else None
    if name.startswith('object.'):
        collection=op['collection']; section=COLLECTIONS[collection]
        data=copy.deepcopy(getattr(doc,section))
        if data is None: raise AuthoringError('capability.unavailable','Project has no '+section+'.')
        if collection not in data:data[collection]=[]
        values=data[collection]
        if name=='object.put': identity=put(values,op['value'],op.get('mode','create'))
        else:
            identity=op['id']; index,value=find(values,identity)
            if name=='object.remove': values.pop(index)
            else:
                if 'id' in op['changes'] and op['changes']['id']!=identity:
                    raise AuthoringError('identity.immutable','Use a new object ID and explicitly reconnect references.')
                value.update(copy.deepcopy(op['changes']))
        if section=='art': doc.replace_art(data)
        elif section=='adventure': doc.replace_adventure(data)
        else: doc.replace(data)
        return identity
    if name=='project.configure':
        manifest=copy.deepcopy(doc.manifest);manifest.update(op['changes']);content=copy.deepcopy(doc.content)
        content['content_version']=manifest['content_version']
        # rules_profile in content is separate from the package field, and
        # the shared loader diagnoses incompatible explicit overrides.
        if 'rules_profile' in op['changes']:
            # Selecting a built-in profile uses its native defaults. Fine
            # tuning a new combat policy is outside this authoring pass.
            content['rules']={'id':op['changes']['rules_profile']}
        doc.replace_all(content,a,doc.art,manifest);return manifest['package_id']
    if name=='asset.annotate':
        from asset_catalogue import annotate
        return annotate(doc,op['id'],op['changes'])
    if name=='start.set': a['start'].update(copy.deepcopy(op['changes']))
    elif name=='flags.add': a['flags'].extend(v for v in op['ids'] if v not in a['flags'])
    elif name=='map.create':
        value=token(find(a['tiles'],op['tile'])[1])
        row=value*op['width'] if a['schema_version']==1 else [value]*op['width']
        return_id=put(a['maps'],dict(id=op['id'],name=op['name'],origin=op.get('origin',[0,0]),
                     rows=[copy.deepcopy(row) for _ in range(op['height'])],overlays=[],entrances=[]))
        doc.replace_adventure(a);return return_id
    elif name=='map.paint':
        from world_editing import draw,fill
        from map_construction import commit_tiles
        scene=a['maps'][scene_index];layer=op.get('layer',-1);start=op['start'];end=op.get('end',start)
        _bounds(scene,layer,[start,end]);value=token(find(a['tiles'],op['tile'])[1])
        if op.get('tool')=='Fill':fill(scene,layer,*start,value)
        else:draw(scene,layer,start,end,value,op.get('tool','Paint'))
        commit_tiles(doc,a);return scene['id']
    elif name=='entrance.put':
        put(a['maps'][scene_index]['entrances'],op['value'],op.get('mode','create'))
    elif name=='marker.move':
        from adventure_editing import move_marker
        move_marker(a,scene_index,(op['kind'],op['map'],op['id'],op.get('enemy_index')),op['at'])
    elif name=='event.connect':
        from event_editing import connect
        connect(doc,op['source'],op['branch'],op['target']);return op['source']
    elif name=='event.describe':
        from event_editing import describe_event
        describe_event(doc,op['id'],op['text']);return op['id']
    elif name=='world.create':
        from world_editing import create_world
        identity=create_world(a,doc.manifest['package_id'],op.get('width',128),op.get('height',128),op['name'])
        doc.replace_adventure(a);return identity
    elif name=='world.patch':
        from map_patterns import world_paste,check_rows
        find(all_worlds(a),op['world']);check_rows(doc,op['rows'])
        world_paste(a,op['world'],*op['at'],op['rows'])
    elif name in ('world.paint','world.generate','city.place'):
        world=find(all_worlds(a),op['world'])[1] # Never silently fall back to another planet.
        if name=='world.paint':
            find(a['jigsaws'],op['jigsaw']);start=op['start'];end=op.get('end',start)
            x0,x1=sorted((start[0],end[0]));y0,y1=sorted((start[1],end[1]))
            if x1>=len(world['pieces'][0]) or y1>=len(world['pieces']):raise AuthoringError('coordinate.bounds','Rectangle leaves the world.')
            for y in range(y0,y1+1):
                for x in range(x0,x1+1):world['pieces'][y][x]=op['jigsaw']
        elif name=='world.generate':
            from scene_tools import generate_world
            generate_world(doc,op['world'],op['seed'],op['weights'],op.get('match_edges',True));return op['world']
        else:
            from world_editing import assign_city
            assign_city(a,op['map'],op.get('at'),op.get('enabled',True),op['world'])
    elif name=='construction.style':
        from construction_editing import put_profile
        from construction_library import STYLE
        check(op['value'],STYLE)
        rows=op['value']['footprint']
        if any(len(row)!=len(rows[0]) for row in rows):raise AuthoringError('request.invalid','Footprint must be rectangular.')
        return put_profile(doc,op['value'])
    elif name=='construction.complete':
        from construction_styles import complete_profile
        return complete_profile(doc,op['style'],op.get('refresh',True))
    elif name=='construction.draw':
        from construction_editing import put_profile
        from map_construction import new_object,paint_footprint,commit,objects
        from event_editing import editor_data
        style=find(editor_data(doc).get('construction_sets',[]),op['style'])[1]
        if style['kind'] not in ('Building','Wall'):raise AuthoringError('request.invalid','Use road.draw for a road style.')
        old=next((o for o in objects(doc,op['map']) if o['id']==op.get('id')),None)
        record=copy.deepcopy(old) if old else new_object(doc,scene_index,style,op['stories'])
        if old and old['style']!=style['id']:raise AuthoringError('request.invalid','Existing construction uses another style.')
        if 'id' in op:record['id']=op['id']
        paint_footprint(record,op['start'],op.get('end',op['start']),op.get('shape','Brush'),op['stories'],op.get('width',1),op.get('erase',False))
        return commit(doc,scene_index,record)
    elif name=='road.draw':
        from construction_editing import prepare_road,draw_road
        from event_editing import editor_data
        from map_construction import commit_tiles
        style=find(editor_data(doc).get('construction_sets',[]),op['style'])[1]
        if style['kind']!='Road':raise AuthoringError('request.invalid','Choose a Road style.')
        style=prepare_road(doc,style);a=copy.deepcopy(doc.adventure)
        layer=op.get('layer',-1);_bounds(a['maps'][scene_index],layer,[op['start'],op['end']])
        draw_road(a,scene_index,layer,op['start'],op['end'],style,op.get('width',1),erase=op.get('erase',False))
        commit_tiles(doc,a);return op['map']
    elif name in ('pattern.capture','pattern.place'):
        from map_patterns import capture,save_pattern,paste
        from event_editing import editor_data
        from map_construction import commit_tiles
        if name=='pattern.capture':return save_pattern(doc,capture(doc,scene_index,op['rect']),op['name'])
        pattern=find(editor_data(doc).get('map_patterns',[]),op['id'])[1]
        layer=op.get('layer',-1);_bounds(a['maps'][scene_index],layer,[op['at']])
        paste(a,scene_index,layer,*op['at'],pattern['rows']);commit_tiles(doc,a);return op['id']
    elif name=='unit.import':
        from unit_library import import_units
        return import_units(doc,[read_json(imports[op['file']])],op.get('policy','keep'),op.get('infantry_art',False),validate=False)
    elif name=='construction.import':
        from construction_library import import_bundle
        return import_bundle(doc,read_json(imports[op['file']]),op.get('id'),validate_result=False)
    elif name=='script.import':
        from editor_model import references,child
        manifest=copy.deepcopy(doc.manifest);scripts=manifest.setdefault('scripts',[])
        existing=next((s for s in scripts if s['id']==op['id']),None)
        if existing and existing['file']!=op['target']:
            raise AuthoringError('request.invalid','Replacement retains its declared target filename.')
        if not existing and (op['target'] in references(manifest) or child(doc.root,op['target']).exists()):
            raise AuthoringError('object.exists','Script target is already occupied.')
        source=imports[op['file']].read_bytes()
        if len(source)>65536:raise AuthoringError('capacity.exceeded','Lua source is limited to 64 KiB.')
        put(scripts,dict(id=op['id'],file=op['target']),op.get('mode','create'))
        meta=dict(doc.metadata);meta[op['target']]=source
        doc.replace_all(doc.content,a,doc.art,manifest,meta);return op['id']
    elif name in ('art.import','art.clone','art.bind'):
        from art_editing import import_image,clone_image,bind
        art=copy.deepcopy(doc.art)
        if name=='art.bind':bind(art,op['slot'],op['image']);identity=op['image']
        else:
            image=(import_image(imports[op['file']],doc.manifest['package_id'],art['images'],op['kind'],op.get('frame_width'),op.get('frame_height'))
                   if name=='art.import' else clone_image(find(art['images'],op['source'])[1],doc.manifest['package_id'],art['images']))
            if 'id' in op:image['id']=op['id']
            if 'name' in op:image['name']=op['name']
            identity=put(art['images'],image)
        doc.replace_art(art);return identity
    else:raise AuthoringError('operation.unsupported','Unsupported operation: '+name)
    doc.replace_adventure(a)
    return op.get('id',op.get('map',op.get('world')))


def check_metadata(document):
    """Editor-only dependencies need checks too: the runtime never reads them."""
    from event_editing import editor_data
    data=editor_data(document); a=document.adventure or {}
    tiles={t['id'] for t in a.get('tiles',[])};maps={m['id'] for m in a.get('maps',[])}
    styles={s['id'] for s in data.get('construction_sets',[])}
    for style in data.get('construction_sets',[]):
        if any(t not in tiles for t in style['parts'].values()):
            raise AuthoringError('reference.missing','Construction style refers to a missing tile.',object_id=style['id'])
    for pattern in data.get('map_patterns',[]):
        if any(t!=' ' and t not in tiles for row in pattern['rows'] for t in row):
            raise AuthoringError('reference.missing','Pattern refers to a missing tile.',object_id=pattern['id'])
    for building in data.get('map_constructions',[]):
        if building['map'] not in maps or building['style'] not in styles:
            raise AuthoringError('reference.missing','Construction refers to a missing map or style.',object_id=building['id'])


def check_capacity(document):
    """Report exhausted installed budgets before the C loader's first error.

    Malformed structures still go to the loader for their precise JSON path.
    This is a preflight diagnostic, not a replacement for semantic validation.
    """
    from authoring_inspect import summary
    try:capacity=summary(document,document.validator)['capacity']
    except (KeyError,TypeError,IndexError,ZeroDivisionError):return
    for key,value in capacity.items():
        if value['remaining']<0:
            raise AuthoringError('capacity.exceeded',f"{key}: {value['used']} entries exceed the installed limit {value['limit']}.",key)


def apply_batch(document, request, *, base_dir=None, dry_run=False, save=False, cancelled=lambda:False,
                frozen_imports=None,protection_overrides=(),allowed_scope=None,expected_result=None):
    check_batch(request)
    if request['project_id']!=document.manifest['package_id']:
        raise AuthoringError('project.mismatch','Request names a different project.','$.project_id')
    def checkpoint():
        if cancelled():raise AuthoringError('job.cancelled','Batch cancelled; no changes applied.')
    checkpoint();document.unchanged_on_disk();base=revision(document)
    imports={};fingerprint=dict(request=request,imports={})
    from authoring_contract import IMPORT_OPERATIONS
    for op in request['operations']:
        if op['op'] in IMPORT_OPERATIONS:
            path=Path((frozen_imports or {}).get(op['file'],op['file']))
            if not path.is_absolute():path=Path(base_dir or document.root)/path
            if path.is_symlink() or not path.is_file() or path.stat().st_size>16*1024*1024:
                raise AuthoringError('import.unavailable','Import needs a regular file up to 16 MiB: '+str(path))
            imports[op['file']]=path.resolve()
            fingerprint['imports'][op['file']]=hashlib.sha256(path.read_bytes()).hexdigest()
    request_hash=hashlib.sha256(json.dumps(fingerprint,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    ledger=json.loads(document.metadata.get(AUTHORING_RECEIPTS,b'{"format":"btp-authoring-receipts-v1","requests":{}}'))
    receipts=ledger['requests'];old=receipts.get(request['request_id'])
    if old:
        if old['hash']!=request_hash:raise AuthoringError('request.reused','This request ID was already used with different content.','$.request_id')
        return dict(old['result'],status='already_applied',current_revision=base,matches_result=base==old['result']['result_revision'])
    if base!=request['expected_revision']:
        raise AuthoringError('revision.conflict','Project changed since this batch was prepared. Inspect it and rebase the requested edits.','$.expected_revision')
    if len(receipts)>=512:raise AuthoringError('history.full','This project has 512 authoring receipts. Export a new project identity before starting another authoring session.')
    candidate=detached(document);outputs=[];started=time.monotonic()
    # One candidate command avoids retaining forty copies of large artwork
    # while a batch draws many tiles. The live document gets one history step.
    with candidate.command(request['label']):
        for index,op in enumerate(request['operations']):
            checkpoint()
            if time.monotonic()-started>60:raise AuthoringError('job.timeout','Batch exceeded 60 seconds; no changes applied.')
            try: outputs.append(dict(operation=index,result=apply_operation(candidate,op,imports)))
            except (KeyError,IndexError,TypeError,ValueError,StopIteration) as exc:
                raise AuthoringError('operation.invalid',f'{op["op"]}: {exc}',f'$.operations[{index}]') from exc
    changes=changed_objects(document,candidate)
    for change in changes:
        if not any(scope=='*' or change['path']==scope or change['path'].startswith(scope+'.') or change['path'].startswith(scope+'/') for scope in request['scope']):
            raise AuthoringError('scope.denied','Batch would change an object outside its declared scope: '+change['path'],object_id=change['object_id'])
        if allowed_scope is not None and not any(scope=='*' or change['path']==scope or change['path'].startswith(scope+'.') or change['path'].startswith(scope+'/') for scope in allowed_scope):
            raise AuthoringError('scope.denied','Batch exceeds this authoring session scope: '+change['path'],object_id=change['object_id'])
    from authoring_protection import enforce,displaced_details
    if expected_result is not None and revision(candidate)!=expected_result:
        raise AuthoringError('review.changed','The proposed result changed since review. Prepare and review it again.')
    check_metadata(candidate);check_capacity(candidate);checkpoint();validation=candidate.validate();checkpoint()
    # Preservation composes referenced terrain/art. Validate shape, references
    # and runtime capacities first, so malformed candidates get native field
    # diagnostics instead of crashing or expanding an unbounded preview.
    enforce(document,candidate,protection_overrides,cancelled);checkpoint()
    # Imports can be edited while a batch validates. Never acknowledge a
    # request whose recorded input hash differs from the bytes it imported.
    if any(hashlib.sha256(path.read_bytes()).hexdigest()!=fingerprint['imports'][name] for name,path in imports.items()):
        raise AuthoringError('revision.conflict','An imported file changed during this batch.')
    document.unchanged_on_disk()
    if revision(document)!=base:raise AuthoringError('revision.conflict','Live document changed while the batch was running.')
    result=dict(api_version=API_VERSION,status='validated' if dry_run else 'applied',request_id=request['request_id'],
                base_revision=base,result_revision=revision(candidate),changes=changes,operations=outputs,validation=validation,diagnostics=[],
                protection_overrides=list(protection_overrides),displaced_details=displaced_details(document,candidate))
    if dry_run:return result
    receipts[request['request_id']]=dict(hash=request_hash,result=copy.deepcopy(result))
    meta=dict(candidate.metadata);meta[AUTHORING_RECEIPTS]=encoded(ledger)
    if len(meta[AUTHORING_RECEIPTS])>16*1024*1024:
        raise AuthoringError('history.full','Authoring receipts exceed 16 MiB. Create a new project identity to start another session.')
    # Restore memory/history as well as disk if publishing fails. The journal
    # handles process death, including a partially written receipt file.
    previous=dict(document.__dict__)
    for key in ('undo_stack','redo_stack','undo_labels','redo_labels'):previous[key]=list(previous[key])
    previous['snapshot']=dict(document.snapshot)
    try:
        with document.command(request['label']):
            document.replace_all(candidate.content,candidate.adventure,candidate.art,candidate.manifest,meta)
            if save:document.save()
    except Exception:
        document.__dict__.clear();document.__dict__.update(previous);raise
    return result
