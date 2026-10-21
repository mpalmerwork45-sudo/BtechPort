"""Display-independent asset discovery shared by commands and editor pickers.

Authored names/tags stay in EDITOR.json. Numeric filters and tactical roles are
derived from definitions and are labelled as such, rather than invented lore.
Reading an atlas/library never imports artwork or creates a library directory.
"""
import copy
import json
import re
import shlex
from pathlib import Path

from authoring_contract import AuthoringError, read_json, check, obj, array, TEXT
from event_editing import editor_data, editor_commit

ANNOTATION_SCHEMA = obj(dict(name=dict(type='string', maxLength=120),
    description=dict(type='string', maxLength=2048), tags=array(dict(type='string', minLength=1, maxLength=64),0,32),
    edges=obj({side:dict(type='string',maxLength=64) for side in ('north','east','south','west')})))
KINDS = ('mech','vehicle','infantry','weapon','equipment','ammunition','tile','sprite','icon','screen','construction','pattern','jigsaw')
NUMERIC = {'mass','price','walk','jump','frames','frame_ticks','damage','range'}
FIELDS = {'id','key','kind','collection','class','movement','weapon','role','dependency','source','tag','name','terrain','animated','construction_kind',*NUMERIC}


def metadata(document):
    return editor_data(document).get('catalogue', {})


def atlas_id(sheet, graphic):
    return 'atlas:'+sheet.replace(':','-')+'-'+str(graphic).replace(':','-')


def annotate(document, identity, values):
    check(values, ANNOTATION_SCHEMA)
    # Atlas annotations can be authored without decoding/owning its pixels.
    known = {r['id'] for r in project_records(document)}
    known.update(atlas_id('package:art',i['id']) for i in document.art['images'] if i['kind']=='tile')
    if document.manifest['requires']=='none' and document.manifest.get('presentation'):
        presentation=json.loads(document.snapshot[document.manifest['presentation']])
        known.update(atlas_id('package:tiles',n) for n in range(len(presentation['tiles'])))
    if identity not in known and not re.fullmatch(r'atlas:chi-(land|destroyed)-([0-9]|[1-9][0-9]|[12][0-9][0-9])', identity):
        raise AuthoringError('object.missing','Annotate an existing asset or original atlas tile.',object_id=identity)
    if identity.startswith('atlas:chi-') and int(identity.rsplit('-',1)[1])>=250:
        raise AuthoringError('object.missing','Original atlases contain tiles 0..249.',object_id=identity)
    data=editor_data(document)
    old=data.setdefault('catalogue',{}).setdefault(identity,{})
    old.update(copy.deepcopy(values))
    if 'tags' in old:old['tags']=list(dict.fromkeys(old['tags']))
    editor_commit(document,data)
    return identity


def weight(mass):
    return 'light' if mass<=35 else 'medium' if mass<=55 else 'heavy' if mass<=75 else 'assault'


def record(value, kind, source, annotations=None, **fields):
    notes=(annotations or {}).get(value['id'],{})
    result=dict(id=value['id'],key=source+'/'+value['id'],name=notes.get('name') or value.get('name',value.get('title',value['id'])),
        kind=kind,source=source,description=notes.get('description',''),tags=notes.get('tags',[]),edges=notes.get('edges',{}),**fields)
    return result


def unit_record(unit, content, annotations=None, source='project'):
    weapons={v['id']:v for v in content['weapons']}
    view=next(p for p in content['presentations'] if p['id']==unit['presentation'])
    loaded=[weapons[w['weapon']] for w in unit['loadout']]
    roles=[]
    if any(w['behavior'].startswith('lrm') for w in loaded):roles.append('missile-support')
    if unit['movement'].get('walk',0)>=7:roles.append('scout')
    if unit['movement'].get('jump',0)>0:roles.append('jump-capable')
    if any(w['behavior'].startswith('srm') for w in loaded):roles.append('close-support')
    dependency='chi' if view['source'].startswith('chi:') else 'independent'
    return record(unit,'vehicle' if unit.get('kind')=='vehicle' else 'mech',source,annotations,
        mass=unit['mass_tons'],price=unit['price'],walk=unit['movement']['walk'],jump=unit['movement']['jump'],
        movement=unit['movement'].get('type','walker'),**{'class':weight(unit['mass_tons'])},dependency=dependency,
        weapons=[dict(id=w['id'],name=w['name'],behavior=w['behavior']) for w in loaded],
        derived_roles=roles,role_basis='Heuristics from weapon behavior, walk and jump; not authored tactical doctrine.',
        presentation=view['id'],dependency_closure=dict(
            weapons=sorted({w['id'] for w in loaded}),
            ammunition=sorted({w['ammunition'] for w in loaded if w['ammunition']!='none'}),
            equipment=sorted({s['equipment'] for s in unit.get('equipment',[])}),
            presentations=[view['id']],images=[view['image']] if view['source']=='package:art' else []))


def project_records(document):
    content=document.content;a=document.adventure or {};data=editor_data(document);notes=data.get('catalogue',{})
    result=[unit_record(u,content,notes) for u in content.get('mechs',[])]
    images={i['id']:i for i in document.art['images']}
    for collection,kind in [('weapons','weapon'),('equipment','equipment'),('ammunition','ammunition')]:
        for value in content.get(collection,[]):
            fields={k:value[k] for k in ('price','damage','behavior') if k in value}
            if 'ranges' in value:fields['range']=value['ranges']['long']
            result.append(record(value,kind,'project',notes,dependency='independent',**fields))
    for person in a.get('people',[]):
        dependency='independent' if person.get('image') or document.manifest['requires']=='none' else 'chi'
        result.append(record(person,'infantry','project',notes,dependency=dependency))
    for tile in a.get('tiles',[]):
        im=images.get(tile['graphic'],{})
        # Source tags carry over to a registered source tile without copying art.
        inherited=dict(notes.get(tile['graphic'],{}) if tile['sheet']=='package:art' else {},
                       **notes.get(atlas_id(tile['sheet'],tile['graphic']),{}))
        tile_notes=dict(notes)
        tile_notes[tile['id']]=dict(inherited,**notes.get(tile['id'],{}))
        if tile['id'] in data.get('tile_names',{}) and not tile_notes[tile['id']].get('name'):
            tile_notes[tile['id']]['name']=data['tile_names'][tile['id']]
        value=dict(tile,name=im.get('name',tile['id']))
        result.append(record(value,'tile','project',tile_notes,collection='tiles',terrain=tile['terrain'],sheet=tile['sheet'],graphic=tile['graphic'],
            frames=len(im.get('frames',[0])),frame_ticks=im.get('frame_ticks',8),animated=len(im.get('frames',[0]))>1,
            dependency='chi' if tile['sheet'].startswith('chi:') else 'independent',animation_checked=not tile['sheet'].startswith('chi:')))
    for image in images.values():
        result.append(record(image,image['kind'],'project',notes,collection='images',dependency='independent',frames=len(image['frames']),
            origin=data.get('tile_sources',{}).get(image['id']),
            frame_ticks=image.get('frame_ticks',8),animated=len(image['frames'])>1,width=image['width'],height=image['height'],
            actions={k:dict(directions=v['directions'],sound=v.get('sound',0)) for k,v in image.get('animations',{}).items()}))
        if image['kind']=='tile':result[-1].update(sheet='package:art',graphic=image['id'],animation_checked=True)
    for collection,kind in [('construction_sets','construction'),('map_patterns','pattern')]:
        for value in data.get(collection,[]):
            from construction_styles import coverage
            result.append(record(value,kind,'project',notes,dependency='project',style=value.get('kind'),
                **(dict(coverage=coverage(value)) if kind=='construction' else {})))
    for value in a.get('jigsaws',[]):result.append(record(value,'jigsaw','project',notes,dependency='project'))
    return result


def bundle_record(bundle, path=None):
    from unit_library import needs_original
    notes=bundle.get('editing',{}).get('catalogue',{})
    if bundle['kind']=='Infantry':
        r=record(bundle['person'],'infantry','library',notes,dependency='chi' if needs_original(bundle) else 'independent')
    else:r=unit_record(bundle['content']['mechs'][0],bundle['content'],notes,'library')
    r.update(id=bundle['entry_id'],key='library/'+bundle['entry_id'],name=notes.get(bundle['definition'],{}).get('name') or bundle['name'],
        revision=bundle['revision'],provenance=bundle['provenance'].get('project'),file=str(path) if path else None)
    return r


def catalogue(document, source='project', library=None, decoded=None, construction_library=None):
    if source not in ('project','library','construction-library','atlas','all'):raise AuthoringError('query.invalid','Choose project, library, construction-library, atlas or all.')
    result=project_records(document) if source in ('project','all') else []
    if source in ('library','all'):
        if library and Path(library).is_dir():
            from unit_library import UnitLibrary
            paths=sorted(Path(library).glob('*.unit.json'))
            if len(paths)>4096:raise AuthoringError('query.bounds','Library exceeds 4,096 entries; select a smaller library.')
            for path in paths:
                bundle=read_json(path);UnitLibrary.check_header(bundle)
                result.append(bundle_record(bundle,path))
        elif source=='library':raise AuthoringError('dependency.unavailable','Select an existing Unit Library folder.')
    if source in ('construction-library','all') and (construction_library or source=='construction-library'):
        from construction_library import ConstructionLibrary,DEFAULT_ROOT,summary
        shared=ConstructionLibrary(construction_library or DEFAULT_ROOT,document.validator)
        result.extend(summary(bundle,shared.path(bundle['entry_id'])) for bundle in shared.entries())
    if source in ('atlas','all'):
        from tile_editing import sheet_graphics,source_definition
        from tile_animation import tile_loop
        if decoded is None:raise AuthoringError('dependency.unavailable','Atlas discovery requires decoded source tiles; supply --data for CHI.')
        for sheet,graphic in sheet_graphics(decoded):
            value=source_definition(document,sheet,graphic);value['id']=atlas_id(sheet,graphic)
            loop=tile_loop(decoded,sheet,graphic)
            result.append(record(value,'tile','atlas',metadata(document),collection='atlas',dependency='chi' if sheet.startswith('chi:') else 'independent',
                sheet=sheet,graphic=graphic,terrain=value['terrain'],animated=bool(loop),frames=len(loop.frames) if loop else 1,
                frame_ticks=loop.ticks if loop else 8,animation_checked=True))
    if decoded is not None:
        from tile_animation import tile_loop
        for r in result:
            if r['kind']=='tile' and 'sheet' in r:
                loop=tile_loop(decoded,r['sheet'],r['graphic'])
                r.update(frames=len(loop.frames) if loop else 1,frame_ticks=loop.ticks if loop else 8,animated=bool(loop),animation_checked=True)
    return sorted(result,key=lambda r:(r['kind'],r['name'].casefold(),r['key']))


def parse_query(query):
    try:tokens=shlex.split(query)
    except ValueError as exc:raise AuthoringError('query.invalid',str(exc)) from exc
    result=[]
    for word in tokens:
        match=re.fullmatch(r'([a-z_]+)(:|<=|>=|=|<|>)(.+)',word)
        # A bare stable ID is also a useful search term, even when its
        # namespace happens to look like a search-field name.
        if match and match[1] not in FIELDS and re.fullmatch(r'[a-z][a-z0-9._-]*:[a-z][a-z0-9._-]*',word):match=None
        if match:
            field,op,value=match.groups()
            if field not in FIELDS:raise AuthoringError('query.invalid','Unknown search field: '+field)
            if op!=':' and field not in NUMERIC:raise AuthoringError('query.invalid','Numeric comparison needs a numeric field.')
            if field in NUMERIC:
                try:value=float(value)
                except ValueError:raise AuthoringError('query.invalid','Numeric search value required: '+field)
                if not abs(value)<float('inf'):raise AuthoringError('query.invalid','Search values must be finite.')
            result.append((field,op,value))
        else:result.append((None,':',word.casefold()))
    return result


def matches(item, query):
    terms=parse_query(query) if isinstance(query,str) else query
    for field,op,wanted in terms:
        if field is None:value=json.dumps(item,ensure_ascii=True).casefold()
        elif field=='role':value=item.get('derived_roles',[])+item.get('tags',[])
        elif field=='weapon':value=item.get('weapons',[])
        elif field=='tag':value=item.get('tags',[])
        else:value=item.get(field)
        if field in NUMERIC:
            if not isinstance(value,(int,float)):return False
            if not {':':value==wanted,'=':value==wanted,'<':value<wanted,'>':value>wanted,'<=':value<=wanted,'>=':value>=wanted}[op]:return False
        elif str(wanted).casefold() not in (json.dumps(value,ensure_ascii=True) if not isinstance(value,str) else value).casefold():return False
    return True


def search(records, query='', offset=0, limit=30):
    if not 1<=limit<=100 or offset<0:raise AuthoringError('query.bounds','Use limit 1..100 and nonnegative offset.')
    terms=parse_query(query);found=[r for r in records if matches(r,terms)]
    return dict(total=len(found),offset=offset,items=found[offset:offset+limit],next_offset=offset+limit if offset+limit<len(found) else None)


def search_document(document, query):
    """Index once per picker refresh, not once per visible asset."""
    return {r['id'] for r in project_records(document) if matches(r,parse_query(query))}
