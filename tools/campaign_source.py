"""Optional campaign sources; the native engine still loads ordinary packages.

The index explicitly orders modules. Arrays are never sorted by display name:
their order supplies runtime handles and is therefore gameplay content. Source
paths and notes are authoring data, outside the native save fingerprint.
"""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import re
import tempfile

from editor_model import EditorError, child, encoded, references, METADATA_FILES

INDEX = 'SOURCE.json'
FORMAT = 'btp-campaign-source-v1'
MAX_FILES = 4096
MAX_BYTES = 128 * 1024 * 1024
SECTIONS = {'manifest': None, 'content': 'definitions', 'adventure': 'adventure',
            'art': 'graphics', 'presentation': 'presentation', 'chi_spatial':'chi_spatial',
            'chi_presentation':'chi_presentation', 'chi_campaign':'campaign','chi_scripts':'chi_scripts'}
DOCUMENTS = ('README.md','LICENSE.md','SOURCE-README.md','ART-SOURCE-README.md',
             'VEHICLE-SOURCE-README.md','sources.json','CREDITS.md')


def schema():
    from authoring_contract import obj,array
    path=dict(type='string',minLength=1,maxLength=512)
    return obj(dict(format={'const':FORMAT},schema_version={'const':1},
        sections=obj({s:path for s in SECTIONS},['manifest','content']),
        modules=array(obj(dict(section=dict(enum=list(SECTIONS)[1:]),collection=dict(type='string',pattern='^[a-z_]+$'),file=path),
                          ['section','collection','file']),0,MAX_FILES-1),
        texts=array(path,0,MAX_FILES-1),files=dict(type='object',additionalProperties=path),
        order=dict(type='object',additionalProperties=array(dict(type='string'),0,4096)),notes=dict(type='object')),
        ['format','schema_version','sections'])


class SourceError(EditorError):
    def __init__(self, message, file=INDEX, path='$', code='source.invalid', object_id=None):
        super().__init__(f'{file}: {path}: {message}')
        self.diagnostic = dict(code=code, severity='error', message=str(self),
            field_path=path, object_id=object_id, location=None,
            source=dict(file=file, field_path=path))


def canonical(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)+'\n').encode('ascii')


def parse(data, name):
    def pairs(values):
        result = {}
        for key, value in values:
            if key in result: raise ValueError('Duplicate field: '+key)
            result[key] = value
        return result
    try:
        return json.loads(data, object_pairs_hook=pairs,
            parse_constant=lambda v: (_ for _ in ()).throw(ValueError('Non-finite number: '+v)))
    except (ValueError, RecursionError) as error:
        raise SourceError(str(error), name) from error


def filename(identity):
    slug = re.sub('[^a-zA-Z0-9._-]+', '-', identity)[:70].strip('.') or 'object'
    return slug+'-'+hashlib.sha256(identity.encode()).hexdigest()[:10]+'.json'


class CampaignSource:
    def __init__(self, root, supplied=None):
        self.root = Path(root)
        self.disk = {}
        self.supplied = supplied
        self.total = 0
        self.index = self.read_json(INDEX)
        index = self.index
        from authoring_contract import check,AuthoringError
        try:check(index,schema())
        except AuthoringError as error:raise SourceError(str(error),INDEX,error.diagnostic['field_path']) from error
        if not isinstance(index, dict) or index.get('format') != FORMAT or index.get('schema_version') != 1:
            raise SourceError('Expected btp-campaign-source-v1, schema_version 1.')
        if set(index)-{'format','schema_version','sections','modules','texts','files','order','notes'}:
            raise SourceError('Unknown source index field.')
        if not isinstance(index.get('sections'), dict) or not {'manifest','content'} <= set(index['sections']) <= set(SECTIONS):
            raise SourceError('Declare manifest and content sections, plus supported optional sections.')
        if not isinstance(index.get('modules', []), list) or not isinstance(index.get('texts', []), list) or not isinstance(index.get('files', {}), dict):
            raise SourceError('modules/texts must be lists; files must map runtime paths to source paths.')
        self.sections = {key:self.read_json(name) for key,name in index['sections'].items()}
        if any(not isinstance(v, dict) for v in self.sections.values()):
            raise SourceError('Each base section must contain a JSON object.')
        self.texts = {}; self.text_owners = {}
        for name in index.get('texts', []):
            values = self.read_json(name)
            if not isinstance(values, dict) or any(not isinstance(v,str) for v in values.values()):
                raise SourceError('A text file maps unique keys to strings.', name)
            for key,value in values.items():
                if key in self.texts: raise SourceError('Duplicate text key: '+key, name)
                self.texts[key] = value; self.text_owners[key] = name
        self.modules = []
        declared=[*index['sections'].values(),*index.get('texts',[]),INDEX]
        if len(declared)!=len(set(declared)):raise SourceError('A source file may only have one declared role.')
        used = set(declared)
        for module in index.get('modules', []):
            if not isinstance(module,dict) or set(module) != {'section','collection','file'}:
                raise SourceError('Each module requires section, collection and file.')
            section, collection, name = (module[k] for k in ('section','collection','file'))
            if section not in self.sections or section == 'manifest' or not isinstance(collection,str) or not collection:
                raise SourceError('Module needs a declared data section and collection.')
            if name in used: raise SourceError('Source file declared more than once: '+str(name))
            used.add(name)
            values = self.read_json(name)
            if not isinstance(values,list): raise SourceError('A collection module must contain a JSON array.',name)
            self.modules.append((module, values))
        for target,name in index.get('files', {}).items():
            child(self.root,target)
            if target in ('SOURCE.json','SOURCE-MAP.json') or name in used:
                raise SourceError('Conflicting source file mapping: '+target)
            used.add(name); self.read(name)
        self.package, self.locations = self.compile()

    def read(self, name):
        if not isinstance(name,str): raise SourceError('A source path must be a string.')
        path = child(self.root,name)
        if name not in self.disk:
            if len(self.disk) >= MAX_FILES: raise SourceError('Source exceeds 4096 files.')
            try:
                if self.supplied is None:
                    with path.open('rb') as stream: data=stream.read(MAX_BYTES-self.total+1)
                else: data=self.supplied[name]
            except (OSError,KeyError) as error: raise SourceError('Cannot read source: '+str(error),name) from error
            self.total += len(data)
            if self.total > MAX_BYTES: raise SourceError('Source exceeds 128 MiB.',name)
            self.disk[name] = data
        return self.disk[name]

    def read_json(self, name): return parse(self.read(name),name)

    def expand(self, value, name, path='$'):
        if isinstance(value,dict):
            if '$text' in value:
                if set(value) != {'$text'} or not isinstance(value['$text'],str) or value['$text'] not in self.texts:
                    raise SourceError('Unknown or malformed text reference.',name,path)
                return self.texts[value['$text']]
            return {k:self.expand(v,name,path+'.'+k) for k,v in value.items()}
        if isinstance(value,list): return [self.expand(v,name,f'{path}[{i}]') for i,v in enumerate(value)]
        return value

    def compile(self):
        values = {k:self.expand(v,self.index['sections'][k]) for k,v in self.sections.items()}
        locations = []
        def locate(section,collection,items,name):
            for i,item in enumerate(items):
                if isinstance(item,dict) and isinstance(item.get('id'),str):
                    locations.append(dict(section=section,collection=collection,id=item['id'],file=name,field_path=f'$[{i}]'))
        for section,data in values.items():
            for key,items in data.items():
                if isinstance(items,list):
                    locate(section,key,items,self.index['sections'][section])
                    for item in locations:
                        if item['section']==section and item['collection']==key:item['field_path']='$.'+key+item['field_path'][1:]
        for module,raw in self.modules:
            section,collection,name = (module[k] for k in ('section','collection','file'))
            items = self.expand(raw,name)
            target = values[section].setdefault(collection,[])
            if not isinstance(target,list): raise SourceError('A module cannot append to a non-array field.',name)
            locate(section,collection,items,name);target.extend(items)
        for section,data in values.items():
            for key,items in data.items():
                if not isinstance(items,list):continue
                ids=[v['id'] for v in items if isinstance(v,dict) and isinstance(v.get('id'),str)]
                if len(ids)!=len(set(ids)):
                    identity=next(i for i in ids if ids.count(i)>1)
                    origin=next(v for v in locations if v['section']==section and v['collection']==key and v['id']==identity)
                    raise SourceError('Duplicate object ID: '+identity,origin['file'],'$.'+key+'['+identity+']',object_id=identity)
        orders=self.index.get('order',{})
        if not isinstance(orders,dict):raise SourceError('order must map section.collection to ID arrays.')
        for key,order in orders.items():
            section,_,collection=key.partition('.')
            items=values.get(section,{}).get(collection)
            if not isinstance(items,list) or not isinstance(order,list) or any(not isinstance(v,dict) or 'id' not in v for v in items):
                raise SourceError('Ordering requires a named object collection: '+key)
            ids=[v['id'] for v in items]
            if any(not isinstance(v,str) for v in order) or len(order)!=len(ids) or set(order)!=set(ids):
                raise SourceError('Order must list every object exactly once: '+key)
            by_id={v['id']:v for v in items};values[section][collection]=[by_id[i] for i in order]
        self.values=copy.deepcopy(values)
        manifest=values['manifest']; package={}
        for section,data in values.items():
            name='project.json' if section=='manifest' else manifest.get(SECTIONS[section])
            # Keep inactive optional sections as source-owned data. Undoing a
            # first graphics import can remove its runtime manifest reference;
            # Redo must be able to restore it without overwriting orphan files.
            if name is None and section not in ('manifest','content'):continue
            if not isinstance(name,str):raise SourceError('Section missing its runtime path: '+section)
            child(self.root,name)
            if name in package or name in (INDEX,'SOURCE-MAP.json'):raise SourceError('Conflicting runtime output: '+name)
            package[name]=canonical(data)
        for target,name in self.index.get('files',{}).items():
            if target in package:raise SourceError('File mapping conflicts with a generated section: '+target)
            package[target]=self.disk[name]
        try: missing=set(references(manifest))-set(package)
        except (KeyError,TypeError) as error:raise SourceError('Incomplete project manifest.') from error
        if missing:raise SourceError('Undeclared dependencies: '+', '.join(sorted(missing)))
        allowed=set(references(manifest)) | set(METADATA_FILES)
        if set(package)-allowed:raise SourceError('Undeclared runtime files: '+', '.join(sorted(set(package)-allowed)))
        for loc in locations:
            loc['runtime_file']='project.json' if loc['section']=='manifest' else manifest.get(SECTIONS[loc['section']])
        return package,locations

    def locate_error(self,error):
        from authoring_contract import diagnostic
        record=diagnostic(error);path=record['field_path']
        for loc in self.locations:
            prefix='$.'+loc['collection']+'['+loc['id']+']'
            if path.startswith(prefix):
                message=str(error).split(': '+path+': ',1)[-1]
                result=SourceError(message,loc['file'],path,code=record['code'],object_id=loc['id'])
                result.diagnostic['source']['field_path']=loc['field_path']+path[len(prefix):]
                return result
        return error

    def updated(self, package):
        """Scatter editor objects back to their owners; retain shared text links.

        Deleted records leave an empty module, so a crash-safe save never needs
        to remove user files. New records go to the collection's last module.
        An explicit ordering table preserves reordering across module boundaries.
        """
        result=dict(self.disk);index=copy.deepcopy(self.index);sections={};text_changes={}
        manifest=parse(package['project.json'],'project.json')
        for section,key in SECTIONS.items():
            target='project.json' if key is None else manifest.get(key)
            if target:
                sections[section]=parse(package[target],target)
                if section not in index['sections']:index['sections'][section]='source/'+section+'.json'
        for section in set(index['sections'])-set(sections):sections[section]=copy.deepcopy(self.values[section])
        def retain(value, template):
            if isinstance(template,dict) and set(template)=={'$text'} and isinstance(value,str):
                key=template['$text']
                if key in text_changes and text_changes[key]!=value:
                    raise SourceError('Shared text has conflicting edits; use separate text keys: '+key,self.text_owners[key])
                text_changes[key]=value;return template
            if isinstance(value,dict):return {k:retain(v,template.get(k) if isinstance(template,dict) else None) for k,v in value.items()}
            if isinstance(value,list):
                old=template if isinstance(template,list) else []
                by_id={v['id']:v for v in old if isinstance(v,dict) and 'id' in v}
                return [retain(v,by_id.get(v['id']) if isinstance(v,dict) and 'id' in v else old[i] if i<len(old) else None) for i,v in enumerate(value)]
            return value
        def store_json(name,value):
            # Retain comments-as-fields/formatting for untouched source files.
            if name not in self.disk or parse(self.disk[name],name)!=value:result[name]=encoded(value)
        grouped={}
        for module,raw in self.modules:grouped.setdefault((module['section'],module['collection']),[]).append((module,raw))
        for (section,collection),modules in grouped.items():
            items=sections[section].get(collection,[])
            oldbase=self.sections[section].get(collection,[])
            allraw=[*oldbase,*[v for _,raw in modules for v in raw]]
            named=all(isinstance(v,dict) and 'id' in v for v in [*allraw,*items])
            if not named:
                # Primitive arrays have no stable IDs: preserve their original
                # partition sizes, placing additions in the last module.
                cursor=len(oldbase);sections[section][collection]=items[:cursor]
                for i,(module,raw) in enumerate(modules):
                    count=len(raw) if i<len(modules)-1 else len(items)-cursor
                    store_json(module['file'],retain(items[cursor:cursor+count],raw));cursor+=count
                continue
            desired={v['id']:v for v in items};assigned=set();composed=[]
            def take(raw,extra=False):
                owned=[v['id'] for v in raw if v['id'] in desired]
                if extra:owned += [v['id'] for v in items if v['id'] not in assigned and v['id'] not in owned]
                assigned.update(owned);composed.extend(owned)
                return retain([desired[i] for i in owned],raw)
            sections[section][collection]=take(oldbase)
            for i,(module,raw) in enumerate(modules):store_json(module['file'],take(raw,i==len(modules)-1))
            key=section+'.'+collection;order=[v['id'] for v in items]
            if composed!=order:index.setdefault('order',{})[key]=order
            else:index.get('order',{}).pop(key,None)
        for section,data in sections.items():store_json(index['sections'][section],retain(data,self.sections.get(section,{})))
        for name in index.get('texts',[]):
            values=parse(self.disk[name],name)
            values.update({key:value for key,value in text_changes.items() if self.text_owners[key]==name})
            store_json(name,values)
        outputs={'project.json',*[manifest[key] for key in SECTIONS.values() if key and key in manifest]}
        for target,data in package.items():
            if target in outputs:continue
            name=index.setdefault('files',{}).setdefault(target,'files/'+target)
            child(self.root,name);result[name]=data
        store_json(INDEX,index)
        # Reload the exact proposed source before publication. This catches
        # conflicting declarations and prevents GUI/compiler semantic drift.
        compiled=CampaignSource(self.root,result)
        if compiled.package!=package:raise SourceError('The source layout cannot represent this edit without changing content.')
        return result


def convert(document, target):
    """Create a separate source project. Never convert a user's directory in place."""
    from editor_model import ProjectDocument
    target=Path(target).resolve();document.validate()
    if target.exists() or target.is_relative_to(document.root):raise EditorError('Conversion requires a new directory outside the current project.')
    if document.source is not None:raise EditorError('This is already a source project; copy its source directory to duplicate it.')
    package=document.files();manifest=json.loads(package['project.json'])
    index=dict(format=FORMAT,schema_version=1,sections={},modules=[],texts=['text/dialogue.json'],files={})
    source={};texts={}
    for section,key in SECTIONS.items():
        runtime='project.json' if key is None else manifest.get(key)
        if not runtime:continue
        base=copy.deepcopy(json.loads(package[runtime]));name='source/'+section+'.json';index['sections'][section]=name
        for collection,items in list(base.items()):
            if section=='manifest' or not isinstance(items,list) or not items or not all(isinstance(v,dict) and isinstance(v.get('id'),str) for v in items):continue
            base[collection]=[]
            for item in items:
                path=section+'/'+collection+'/'+filename(item['id'])
                # Dialogue stays easy to edit without rewriting maps or pixels.
                if section=='adventure' and collection=='events':
                    for field in ('text','prompt'):
                        if isinstance(item.get(field),str):
                            text_id=item['id']+'.'+field;texts[text_id]=item[field];item[field]={'$text':text_id}
                index['modules'].append(dict(section=section,collection=collection,file=path));source[path]=encoded([item])
        source[name]=encoded(base)
    outputs={'project.json',*[manifest[key] for key in SECTIONS.values() if key and key in manifest]}
    for runtime,data in package.items():
        if runtime in outputs:continue
        name='files/'+runtime;index['files'][runtime]=name;source[name]=data
    source['text/dialogue.json']=encoded(texts);source[INDEX]=encoded(index)
    target.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.btp-source-',dir=target.parent) as temp:
        stage=Path(temp)/'source';stage.mkdir()
        for name,data in source.items():
            path=child(stage,name);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        ProjectDocument(stage,document.validator,recover=False)
        for name in DOCUMENTS:
            original=child(document.root,name)
            if original.is_file():child(stage,name).write_bytes(original.read_bytes())
        if target.exists():raise EditorError('Source destination appeared during conversion.')
        stage.rename(target)
    return ProjectDocument(target,document.validator)


def build(document, target):
    """Publish a fresh, independently playable package with source attribution."""
    target=Path(target).resolve()
    if target.is_relative_to(document.root):raise EditorError('Build into a separate output directory, outside the source project.')
    if target.exists():raise EditorError('Build requires a new output directory; existing files are preserved.')
    source=document.source
    current=CampaignSource(document.root,document.source_files()) if source else None
    target.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.btp-build-',dir=target.parent) as temp:
        stage=Path(temp)/'game';document.export(stage)
        if current:(stage/'SOURCE-MAP.json').write_bytes(encoded(dict(format='btp-source-map-v1',objects=current.locations)))
        document.unchanged_on_disk()
        if target.exists():raise EditorError('Build destination appeared while compiling.')
        stage.rename(target)
    runtime={name:data for name,data in document.files().items() if name in references(document.manifest)}
    digest=hashlib.sha256()
    for name in references(document.manifest):digest.update(hashlib.sha256(runtime[name]).digest())
    return dict(status='built',output=str(target),fingerprint=digest.hexdigest(),
        files=[dict(file=name,sha256=hashlib.sha256(data).hexdigest(),bytes=len(data)) for name,data in sorted(runtime.items())],
        source_map='SOURCE-MAP.json' if source else None)
