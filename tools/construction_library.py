"""Portable construction styles and patterns, with their tile/art closure.

This module has no Tk dependency. Library writes and project imports are
separate operations: importing makes an editable project copy, never a live
link that changes other games when a library entry is revised.
"""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import uuid

from editor_model import EditorError,ProjectDocument,encoded,run_validator
from authoring_contract import check,obj,array,integer,enum,ID,read_json
from construction_editing import geometry,compile_rows
from tile_editing import metadata,check_budget
from world_editing import identity,upgrade
from project_lock import project_lock

ROOT=Path(__file__).resolve().parents[1]
FORMAT='btp-construction-library-v1'
KINDS=('Building','Wall','Road','Pattern')
DEFAULT_ROOT=ROOT/'work/construction-library'
NAME=dict(type='string',minLength=1,maxLength=95)
STYLE=obj(dict(id=ID,name=NAME,kind=enum('Building','Wall','Road'),
    footprint=array(array(integer(-1,32),1,32),1,32),parts=dict(type='object',additionalProperties=ID),
    generated_joins=dict(type='object',additionalProperties=dict(type='string',pattern='^[0-9a-f]{64}$'))),
    ['id','name','kind','footprint','parts'])
PATTERN=obj(dict(id=ID,name=NAME,rows=array(array(dict(anyOf=[ID,{'const':' '}]),1,64),1,64)),['id','name','rows'])


def schema():
    tile=json.loads((ROOT/'schemas/adventure-v2.schema.json').read_bytes())['properties']['tiles']['items']
    image=json.loads((ROOT/'schemas/art-v1.schema.json').read_bytes())['properties']['images']['items']
    editing=obj({key:dict(type='object') for key in ('tile_names','tile_sources','pixel_layers','catalogue')})
    return obj(dict(format={'const':FORMAT},schema_version={'const':1},entry_id=ID,revision=integer(1,2147483647),
        name=NAME,kind=enum(*KINDS),design=dict(oneOf=[STYLE,PATTERN]),
        tiles=array(tile,0,4096),images=array(image,0,4096),editing=editing,
        provenance=obj(dict(project=NAME,package=dict(type='string',maxLength=31),
            documents=dict(type='object',additionalProperties=dict(type='string',maxLength=1048576))),
            ['project','package','documents'])),
        ['format','schema_version','entry_id','revision','name','kind','design','tiles','images','editing','provenance'])


def rows(bundle):
    return bundle['design']['rows'] if bundle['kind']=='Pattern' else compile_rows(bundle['design'])


def check_bundle(bundle):
    check(bundle,schema())
    if not bundle['name'].strip() or not bundle['design']['name'].strip():raise EditorError('Give the library design a nonempty name.')
    if len(encoded(bundle))>16*1024*1024:raise EditorError('Construction Library entries are limited to 16 MiB.')
    design=bundle['design']
    if bundle['kind']!='Pattern':
        if design.get('kind')!=bundle['kind']:raise EditorError('Construction type does not match its drawing definition.')
        geometry(design)  # Height limits and rectangular footprints.
        if any(not r.startswith('join|') or r not in design['parts'] for r in design.get('generated_joins',{})):
            raise EditorError('Generated joins must refer to assigned joining parts.')
    elif 'rows' not in design:raise EditorError('A pattern needs its tile rows.')
    grid=rows(bundle)
    if any(len(row)!=len(grid[0]) for row in grid):raise EditorError('Pattern rows must form a rectangle.')
    tiles={t['id']:t for t in bundle['tiles']};images={i['id']:i for i in bundle['images']}
    if len(tiles)!=len(bundle['tiles']) or len(images)!=len(bundle['images']):raise EditorError('Duplicate tile/image IDs in library entry.')
    used=({t for row in grid for t in row if t!=' '} if bundle['kind']=='Pattern' else set(design['parts'].values()))
    if used!=set(tiles):raise EditorError('Library entry must contain exactly the tiles used by its definition.')
    owned=set()
    for tile in tiles.values():
        if tile['sheet']=='package:art':
            owned.add(tile['graphic'])
            if tile['graphic'] not in images:raise EditorError('Library tile artwork is missing.')
        elif tile['sheet']=='package:tiles':raise EditorError('Indexed package tiles must be converted to owned pixels before sharing.')
        elif type(tile['graphic']) is not int:raise EditorError('Original tile references need an atlas index.')
    if owned!=set(images):raise EditorError('Library entry must contain exactly its referenced tile images.')
    for im in images.values():
        if im['kind']!='tile' or im['width']!=16 or im['height']!=16:raise EditorError('Construction artwork must be 16 by 16 tile images.')
        if any(len(f)!=16 or any(len(line)!=128 for line in f) for f in im['frames']):raise EditorError('Invalid tile frame dimensions.')
    allowed={'tile_names':set(tiles),'tile_sources':set(images),'pixel_layers':set(images),
             'catalogue':set(tiles)|set(images)|{design['id']}}
    for key,values in bundle['editing'].items():
        if set(values)-allowed[key]:raise EditorError('Library editing metadata refers to an unrelated asset.')
    from pixel_tools import begin_layers
    for key,value in bundle['editing'].get('pixel_layers',{}).items():begin_layers(images[key],value)
    check_budget(dict(images=bundle['images']),dict(tiles=bundle['tiles']))


def needs_original(bundle):
    return any(t['sheet'].startswith('chi:') for t in bundle['tiles'])


def closure(document,design_id):
    """Read current unsaved data; never copy unrelated tiles, maps or scripts."""
    data=metadata(document)
    design=next((p for key in ('construction_sets','map_patterns') for p in data.get(key,[]) if p['id']==design_id),None)
    if design is None:raise EditorError('Select an existing construction set or saved pattern.')
    design=copy.deepcopy(design);kind=design.get('kind','Pattern')
    used=set(design['parts'].values()) if kind!='Pattern' else {t for row in design['rows'] for t in row if t!=' '}
    values={t['id']:t for t in document.adventure['tiles']}
    if used-set(values):raise EditorError('The design uses a missing tile. Restore or replace that part before sharing.')
    tiles=[copy.deepcopy(values[k]) for k in sorted(used)]
    image_ids={t['graphic'] for t in tiles if t['sheet']=='package:art'}
    images=[copy.deepcopy(im) for im in document.art['images'] if im['id'] in image_ids]
    editing={key:{i:copy.deepcopy(v) for i,v in data.get(key,{}).items() if i in
        (used if key=='tile_names' else image_ids|used|{design_id} if key=='catalogue' else image_ids)}
        for key in ('tile_names','tile_sources','pixel_layers','catalogue')}
    # Independent indexed palettes belong to their source project. Materialize
    # those authored pixels once; original CHI references stay external.
    indexed={}
    for tile in tiles:
        tile.pop('key',None)
        if tile['sheet']!='package:tiles':continue
        graphic=tile['graphic']
        if graphic not in indexed:
            from editor_tiles import _package_tiles
            from art_editing import new_image
            im=new_image('library',images,'Imported palette tile '+str(graphic))
            pixels=_package_tiles(document)[graphic]
            im['frames']=[[''.join(c.lstrip('#')+'ff' for c in line) for line in pixels]]
            images.append(im);indexed[graphic]=im['id']
            editing['tile_sources'][im['id']]=dict(sheet='package:tiles',graphic=graphic,package=document.manifest['package_id'])
        tile.update(sheet='package:art',graphic=indexed[graphic])
    documents={}
    from unit_library import SOURCE_FILES
    for name in SOURCE_FILES:
        path=document.root/name
        if path.is_file() and not path.is_symlink() and path.stat().st_size<=1048576:documents[name]=path.read_text()
    # Preserve attribution through another export without nesting old bundles.
    for record in json.loads(document.metadata.get('LIBRARY-SOURCES.json',b'[]')):
        documents.update(record.get('provenance',{}).get('documents',{}))
    bundle=dict(format=FORMAT,schema_version=1,entry_id=design_id,revision=1,name=design['name'],kind=kind,
        design=design,tiles=tiles,images=images,editing=editing,
        provenance=dict(project=document.manifest['title'],package=document.manifest['package_id'],documents=documents))
    check_bundle(bundle);return bundle


def preview_files(bundle):
    """A neutral validator/preview project has no dependency on user maps."""
    check_bundle(bundle)
    files={name:json.loads((ROOT/'examples/beacon-demo'/name).read_bytes())
           for name in ('project.json','content.json','presentation.json')}
    manifest=files['project.json'];original=needs_original(bundle)
    manifest.update(package_id='construction-library',title=bundle['name'],assets=[],scripts=[],
        requires='chi-original-dos-1.03' if original else 'none',definitions='content.json',
        adventure='adventure.json',graphics='graphics.json',content_version='1.0.0')
    files['content.json'].update(package_id=manifest['package_id'],content_version='1.0.0')
    if original:
        manifest.pop('presentation',None);files.pop('presentation.json')
        for p in files['content.json']['presentations']:p['source']='chi:locust'
    images=copy.deepcopy(bundle['images']);tiles=copy.deepcopy(bundle['tiles'])
    from art_editing import new_image
    ground=new_image('preview',images,'Preview ground');ground['frames']=[['314754ff'*16]*16];images.append(ground)
    floor=identity('preview',tiles,'floor');tiles.append(dict(id=floor,sheet='package:art',graphic=ground['id'],terrain='clear',mini_color=2))
    files['graphics.json']=dict(format='btp-art-v1',schema_version=1,images=images,bindings=[])
    files['adventure.json']=dict(format='btp-adventure-v2',schema_version=2,tiles=tiles,
        maps=[dict(id='preview:map',name='Construction preview',origin=[0,0],rows=[[floor]*32 for _ in range(24)],overlays=[],entrances=[])],
        people=[dict(id='preview:pilot',identity='actor:0',name='Preview',attributes=[8,8,8],skills=[1]*7,weapon=0,armor=0)],
        shops=[],encounters=[],flags=[],events=[dict(id='preview:end',op='end')],
        start=dict(map='preview:map',at=[16,24],event='preview:end',credits=0,party=[dict(person='preview:pilot',mech='none')]))
    editing=copy.deepcopy(bundle['editing']);editing['map_patterns' if bundle['kind']=='Pattern' else 'construction_sets']=[copy.deepcopy(bundle['design'])]
    files['EDITOR.json']=editing
    return files


def validate(bundle,validator):
    files=preview_files(bundle)
    with tempfile.TemporaryDirectory(prefix='construction-validate-') as temporary:
        folder=Path(temporary)
        for name,value in files.items():(folder/name).write_bytes(encoded(value))
        run_validator(validator,folder)


def import_bundle(document,bundle,design_id=None,validate_result=True):
    """One Undo transaction; remap conflicts without replacing project assets."""
    check_bundle(bundle)
    if document.adventure is None:raise EditorError('Open an authored project before importing constructions.')
    if needs_original(bundle) and document.manifest['requires']=='none':
        raise EditorError('This design references original CHI tiles. Choose a CHI project or share a version using owned tiles.')
    a=copy.deepcopy(document.adventure);art=copy.deepcopy(document.art);data=metadata(document);upgrade(a)
    prefix=document.manifest['package_id'];image_map={};tile_map={};editing=bundle['editing']
    # IDs are remapped together with their editing metadata. Different pixels,
    # collisions or layer data never overwrite a same-named project resource.
    for collection,target,note_keys in [('images',art['images'],('pixel_layers','tile_sources','catalogue')),
                                        ('tiles',a['tiles'],('tile_names','catalogue'))]:
        for old in bundle[collection]:
            value=copy.deepcopy(old)
            if collection=='tiles' and value['sheet']=='package:art':value['graphic']=image_map[value['graphic']]
            existing=next((v for v in target if v['id']==value['id']),None)
            equivalent=existing==value and all(data.get(k,{}).get(value['id'])==editing.get(k,{}).get(old['id']) for k in note_keys)
            if existing is not None and not equivalent:value['id']=identity(prefix,target,'image' if collection=='images' else 'tile');existing=None
            if existing is None:target.append(value)
            (image_map if collection=='images' else tile_map)[old['id']]=value['id']
    collection='map_patterns' if bundle['kind']=='Pattern' else 'construction_sets'
    target=data.setdefault(collection,[]);design=copy.deepcopy(bundle['design'])
    if design_id:
        check(design_id,ID)
        if any(p['id']==design_id for p in target):raise EditorError('That construction/pattern ID already exists. Use a new ID.')
        design['id']=design_id
    elif any(p['id']==design['id'] for p in target):
        design['id']=identity(prefix,target,'pattern' if bundle['kind']=='Pattern' else 'construction')
        design['name']=(design['name']+' copy')[:95]
    if bundle['kind']=='Pattern':design['rows']=[[tile_map[t] if t!=' ' else ' ' for t in row] for row in design['rows']]
    else:design['parts']={role:tile_map[t] for role,t in design['parts'].items()}
    target.append(design)
    for key,values in editing.items():
        mapping=(tile_map if key=='tile_names' else {**image_map,**tile_map,bundle['design']['id']:design['id']}
                 if key=='catalogue' else image_map)
        for old,value in values.items():data.setdefault(key,{})[mapping[old]]=copy.deepcopy(value)
    check_budget(art,a)
    meta=dict(document.metadata);meta['EDITOR.json']=encoded(data)
    sources=json.loads(meta.get('LIBRARY-SOURCES.json',b'[]'))
    source=dict(entry_id=bundle['entry_id'],revision=bundle['revision'],kind=bundle['kind'],provenance=bundle['provenance'])
    if source not in sources:sources.append(source)
    meta['LIBRARY-SOURCES.json']=encoded(sources)
    with document.command('Import '+bundle['kind'].lower()+' from Construction Library'):
        document.replace_art(art,a,meta)
        if validate_result:document.validate()
    return design['id']


def summary(bundle,path=None):
    from asset_catalogue import record
    design=bundle['design'];grid=rows(bundle)
    from construction_styles import coverage
    return record(dict(id=bundle['entry_id'],name=bundle['name']),
        'pattern' if bundle['kind']=='Pattern' else 'construction','construction-library',
        {bundle['entry_id']:bundle['editing'].get('catalogue',{}).get(design['id'],{})},
        construction_kind=bundle['kind'],revision=bundle['revision'],definition=design['id'],
        width=len(grid[0]),height=len(grid),tiles=len(bundle['tiles']),images=len(bundle['images']),
        dependency='chi' if needs_original(bundle) else 'independent',file=str(path) if path else None,
        **(dict(coverage=coverage(design)) if bundle['kind']!='Pattern' else {}))


class ConstructionLibrary:
    def __init__(self,root=DEFAULT_ROOT,validator=None):
        self.root=Path(root).resolve();self.validator=validator
    def path(self,entry_id):
        check(entry_id,ID)
        return self.root/(hashlib.sha256(entry_id.encode()).hexdigest()+'.construction.json')
    def entries(self):
        paths=sorted(self.root.glob('*.construction.json'))
        if len(paths)>4096:raise EditorError('Select a Construction Library with at most 4096 entries.')
        values=[]
        for path in paths:
            if path.is_symlink():raise EditorError('Library entries must be ordinary files.')
            value=read_json(path);check_bundle(value)
            if self.path(value['entry_id'])!=path:raise EditorError('Library filename does not match its entry ID.')
            values.append(value)
        return sorted(values,key=lambda v:(v['kind'],v['name'].casefold(),v['entry_id']))
    def save(self,bundle,expected=None,variant=False):
        value=copy.deepcopy(bundle)
        if variant:value.update(entry_id='library:construction-'+uuid.uuid4().hex[:16],revision=1)
        validate(value,self.validator)
        # The OS lock and optimistic revision cover competing editor windows;
        # an atomic file replacement also leaves the previous entry on failure.
        self.root.mkdir(parents=True,exist_ok=True)
        with project_lock(self.root):
            path=self.path(value['entry_id'])
            if path.is_symlink():raise EditorError('Library entries must be ordinary files.')
            if path.exists():
                current=read_json(path)
                if expected is None or current!=expected:raise EditorError('This library entry exists or changed. Reload it or save a new copy.')
                if current['revision']>=2147483647:raise EditorError('Revision limit reached. Save a new library copy.')
                value['revision']=current['revision']+1
            elif expected is not None:raise EditorError('This library entry was removed. Save a new copy.')
            elif len(list(self.root.glob('*.construction.json')))>=4096:
                raise EditorError('This library already contains 4096 entries. Select another library folder.')
            if len(encoded(value))>16*1024*1024:raise EditorError('Construction Library entry exceeds 16 MiB.')
            ProjectDocument.atomic_file(path,encoded(value))
        return value
    def export_design(self,document,design_id,expected=None,variant=False):
        value=closure(document,design_id)
        if expected:value.update(entry_id=expected['entry_id'],revision=expected['revision'])
        return self.save(value,expected,variant)
