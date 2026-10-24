"""Asset-free reconstruction of edited CHI projects from a user's DOS files.

Recipes contain changed fields and text/pixel splices against a pinned local
import. Original documents, unchanged dialogue, image bases and binaries are
recreated locally. No Python or shell code is evaluated from a recipe.
"""
from __future__ import annotations
import copy,difflib,hashlib,json,struct,tempfile
from pathlib import Path
from editor_model import ProjectDocument,EditorError,encoded,references,child
from chi_import import import_campaigns,plain_path,output_path,publish,check_cancel

FORMAT='btp-chi-recipe-v1'
MAX_CHANGES=32768
MISSING={'$absent':True}

def sha(value):return hashlib.sha256(encoded(value)).hexdigest()
def runtime_files(doc):
    files=doc.files()
    return {n:files[n] for n in [*references(doc.manifest),'EDITOR.json','LIBRARY-SOURCES.json'] if n in files}
def fingerprint(files):
    return sha({name:hashlib.sha256(value).hexdigest() for name,value in sorted(files.items())})
def _get(value,path):
    for part in path:
        if isinstance(part,dict):value=next(v for v in value if isinstance(v,dict) and v.get('id')==part['id'])
        else:value=value[part]
    return value
def _record_list(value):
    return isinstance(value,list) and bool(value) and all(isinstance(v,dict) and isinstance(v.get('id'),str) for v in value) and len({v['id'] for v in value})==len(value)

def diff(old,new,path=(),text_index=None):
    """Keep unchanged original data out of the recipe, including text edits.
    Stable-ID arrays are compared by ID, so inserting a BLD instruction never
    exports the rest of that original program as shifted replacement records.
    """
    if old==new and encoded(old)==encoded(new):return []
    if isinstance(old,dict) and isinstance(new,dict):
        result=[]
        for key in sorted(set(old)|set(new)):
            p=[*path,key]
            if key not in new:result.append(dict(op='remove',path=p,before=sha(old[key])))
            elif key not in old:result.append(dict(op='set',path=p,before=sha(MISSING),value=new[key]))
            else:result+=diff(old[key],new[key],p,text_index)
        if list(old)!=list(new):result.append(dict(op='keys',path=list(path),keys=list(new)))
        return result
    if _record_list(old) and _record_list(new):
        a,b={v['id']:v for v in old},{v['id']:v for v in new};result=[]
        for identity in a.keys()-b.keys():result.append(dict(op='remove',path=[*path,dict(id=identity)],before=sha(a[identity])))
        for row in new:
            identity=row['id'];p=[*path,dict(id=identity)]
            if identity in a:result+=diff(a[identity],row,p,text_index)
            else:
                ignored={'id','origin','original_size','note','name'}
                source=next((v for v in old if {k:x for k,x in v.items() if k not in ignored}=={k:x for k,x in row.items() if k not in ignored}),None)
                result.append(dict(op='copy',path=p,before=sha(MISSING),source=[*path,dict(id=source['id'])]) if source else dict(op='set',path=p,before=sha(MISSING),value=row))
                if source:result+=diff(dict(source,id=identity),row,p,text_index)
        result.append(dict(op='order',path=list(path),ids=[r['id'] for r in new]))
        return result
    if isinstance(old,list) and isinstance(new,list):
        result=[]
        for i in range(min(len(old),len(new))):result+=diff(old[i],new[i],[*path,i],text_index)
        for i in range(len(old)-1,len(new)-1,-1):result.append(dict(op='remove',path=[*path,i],before=sha(old[i])))
        for i in range(len(old),len(new)):
            # Reused animation frames and other unchanged list data stay refs.
            source=next((j for j,v in enumerate(old) if v==new[i]),None)
            result.append(dict(op='copy',path=[*path,i],before=sha(MISSING),source=[*path,source]) if source is not None else dict(op='set',path=[*path,i],before=sha(MISSING),value=new[i]))
        return result
    if isinstance(new,str) and text_index is not None:
        # Match before diffing against a positional neighbour. Inserting a
        # native override can shift unrelated records; their string diff would
        # otherwise turn copied original dialogue into small literal pieces.
        protected=text_index.text_reference(new)
        if protected is not None:return [dict(op='set',path=list(path),before=sha(old),value=protected)]
    if isinstance(old,str) and isinstance(new,str) and len(old)>24:
        # Reverse order keeps offsets relative to the original string. Even
        # a one-word edit to a long native speech stores only that word.
        edits=[dict(at=i,delete=j-i,text=new[a:b]) for tag,i,j,a,b in difflib.SequenceMatcher(None,old,new,autojunk=len(old)>4096).get_opcodes() if tag!='equal']
        return [dict(op='splice',path=list(path),before=sha(old),edits=list(reversed(edits)))]
    return [dict(op='set',path=list(path),before=sha(old),value=new)]

def patch(value,changes):
    baseline=copy.deepcopy(value);value=copy.deepcopy(value)
    for change in changes:
        path=change['path'];op=change['op']
        if op=='keys':
            obj=_get(value,path)
            if not isinstance(obj,dict) or set(change['keys'])!=set(obj) or len(change['keys'])!=len(obj):raise EditorError('Recipe object order mismatch.')
            ordered={key:obj[key] for key in change['keys']};obj.clear();obj.update(ordered);continue
        if not path:
            if op!='set' or sha(value)!=change['before']:raise EditorError('Recipe root/precondition mismatch.')
            value=copy.deepcopy(change['value']);continue
        if op=='order':
            rows=_get(value,path);by_id={v['id']:v for v in rows}
            if len(by_id)!=len(rows) or len(change['ids'])!=len(rows) or set(change['ids'])!=set(by_id):raise EditorError('Recipe record order mismatch.')
            rows[:]=[by_id[i] for i in change['ids']];continue
        parent=_get(value,path[:-1]);key=path[-1]
        if isinstance(key,dict):
            key=next((i for i,v in enumerate(parent) if v.get('id')==key['id']),len(parent))
        present=(key<len(parent) if isinstance(parent,list) and type(key) is int else key in parent)
        old=parent[key] if present else MISSING
        if sha(old)!=change['before']:raise EditorError('Recipe precondition mismatch at '+str(path))
        if op=='remove':del parent[key];continue
        if op=='splice':
            if not isinstance(old,str):raise EditorError('Recipe splice requires a string.')
            updated=old;limit=len(old)
            for edit in change['edits']:
                start,count=edit['at'],edit['delete']
                if min(start,count)<0 or start+count>limit:raise EditorError('Invalid or overlapping recipe splice.')
                updated=updated[:start]+edit['text']+updated[start+count:];limit=start
        elif op=='copy':
            updated=copy.deepcopy(_get(baseline,change['source']))
            if isinstance(path[-1],dict):updated['id']=path[-1]['id']
        elif op=='set':updated=copy.deepcopy(change['value'])
        else:raise EditorError('Unknown recipe operation: '+str(op))
        if isinstance(parent,list) and not present:parent.append(updated)
        else:parent[key]=updated
    return value

def art_bases(doc):
    sources=json.loads(doc.metadata.get('EDITOR.json',b'{}')).get('tile_sources',{});result=[]
    for image in doc.art['images']:
        source=sources.get(image['id'],{})
        if source.get('sheet')=='chi:resource' or source.get('sheet')=='package:portrait':
            result.append(dict(id=image['id'],kind=source['kind'],resource=source['resource'],index=source['graphic'],count=len(image['frames'])))
        elif source.get('sheet','').startswith('chi:'):
            resource={'chi:land':'BTTLTECH.ICN','chi:destroyed':'DESTRUCT.ICN','chi:cache':'STARLEAG.ICN','chi:maproom':'MAP.ICN'}.get(source['sheet'])
            if not resource:raise EditorError('Recipe needs a supported original art source for '+image['id'])
            result.append(dict(id=image['id'],kind='tile',resource=resource,index=source['graphic'],count=1))
        elif image.get('origin') in ('original-derived','unknown') or image['name'].startswith('Original '):
            raise EditorError('Missing reconstructable art provenance: '+image['id'])
    return result

def base_project(source,folder,header,validator,cancel=None,progress=lambda _:None):
    import_campaigns(source,folder,header['edition'],validator,cancel,progress)
    doc=ProjectDocument(Path(folder)/header['edition'],validator)
    manifest=copy.deepcopy(doc.manifest);manifest.update(package_id=header['package_id'],content_version=header['content_version'],title=header['title'])
    content=copy.deepcopy(doc.content);content.update(package_id=header['package_id'],content_version=header['content_version'])
    doc.replace_all(content,doc.adventure,doc.art,manifest,doc.metadata)
    if header['spatial']:
        from chi_spatial import enable
        enable(doc)
    if header['bridge']:
        from chi_bridge import enable
        enable(doc)
    if header['art_bases']:
        from chi_resources import preview
        art=copy.deepcopy(doc.art)
        for source_ref in header['art_bases']:
            check_cancel(cancel);im=preview(doc,source_ref['kind'],source_ref['resource'],source_ref['index'],source_ref['count']);im.pop('native_units',None)
            im['id']=source_ref['id'];art['images'].append(im)
        doc.replace_art(art)
    return doc

def check_recipe(value):
    from authoring_contract import check
    check(value,schema())
    if len(encoded(value))>16*1024*1024:raise EditorError('Recipe exceeds 16 MiB.')
    if sum(len(v['changes']) for v in value['files'])>MAX_CHANGES:raise EditorError('Recipe exceeds 32,768 changes.')
    if len({v['file'] for v in value['files']})!=len(value['files']):raise EditorError('Duplicate recipe file.')
    def selector(path):
        if not isinstance(path,list) or len(path)>32:raise EditorError('Invalid recipe path.')
        for part in path:
            if not (isinstance(part,str) or type(part) is int and 0<=part<=1048576 or isinstance(part,dict) and set(part)=={'id'} and isinstance(part['id'],str)):
                raise EditorError('Invalid recipe path selector.')
    def refs(obj):
        if isinstance(obj,dict):
            if '$chi_base' in obj:
                ref=obj['$chi_base']
                if set(obj)!={'$chi_base'} or not isinstance(ref,dict) or set(ref)!={'file','path'} or not isinstance(ref['file'],str):raise EditorError('Invalid original baseline reference.')
                child(Path('/recipe-check'),ref['file']);selector(ref['path'])
                if ref['file']=='chi/talk-data.bin':
                    if len(ref['path'])!=1 or type(ref['path'][0]) is not int or not 0<=ref['path'][0]<375:raise EditorError('Invalid native dialogue reference.')
                elif not ref['file'].endswith('.json'):raise EditorError('Baseline references must address JSON fields or native dialogue.')
            elif '$chi_text' in obj:
                parts=obj['$chi_text']
                if set(obj)!={'$chi_text'} or not isinstance(parts,list) or not 1<=len(parts)<=65536:raise EditorError('Invalid original text reconstruction.')
                for part in parts:
                    if isinstance(part,str):continue
                    if not isinstance(part,dict) or set(part)!={'source','at','length'} or any(type(part[k]) is not int or not 0<=part[k]<=16777216 for k in ('at','length')):raise EditorError('Invalid original text span.')
                    refs({'$chi_base':part['source']})
            else:
                for item in obj.values():refs(item)
        elif isinstance(obj,list):
            for item in obj:refs(item)
    for row in value['files']:
        name=row['file'];child(Path('/recipe-check'),name)
        if not name.endswith(('.json','.lua')) or name.startswith('chi/') or name in ('IMPORT.json','AUTHORING.json'):
            raise EditorError('Recipe cannot carry native binaries, caches or arbitrary files: '+name)
        for change in row['changes']:
            fields={'set':{'before','value'},'remove':{'before'},'copy':{'before','source'},'order':{'ids'},'keys':{'keys'},'splice':{'before','edits'}}[change['op']]
            if set(change)!={'op','path'}|fields:raise EditorError('Recipe operation has missing or unrelated fields.')
            selector(change['path']);selector(change.get('source',[]));refs(change)
            if isinstance(change.get('value'),dict) and change['value'].get('op')=='data':raise EditorError('New raw BLD data must reference its original source, not embed bytes.')
    return value

def native_texts(data):
    """Read only the bounded string table; no executable or arbitrary bytes."""
    if len(data)<72 or data[:4]!=b'BTTA':raise EditorError('Invalid native dialogue baseline.')
    count=struct.unpack_from('<H',data,6)[0];base=72+4*count
    if count not in (373,375) or base>len(data):raise EditorError('Invalid native dialogue baseline.')
    result=[]
    for i in range(count):
        offset,size=struct.unpack_from('<HH',data,72+4*i)
        if base+offset+size>len(data):raise EditorError('Invalid native dialogue baseline range.')
        try:result.append(data[base+offset:base+offset+size].decode('ascii'))
        except UnicodeError as error:raise EditorError('Invalid native dialogue baseline text.') from error
    return result


class TextReferenceIndex(dict):
    """Refer copied spans back to local inputs even after cloning and editing.

    Twelve-character anchors avoid comparing every new string with every
    original speech/pixel row. A retained span of 24 characters necessarily
    includes an anchor, regardless of the text's new position.
    """
    def __init__(self):
        super().__init__();self.strings={};self.anchors=None;self.cache={}

    def add(self,value,ref):
        self.setdefault(sha(value),ref)
        if isinstance(value,str):self.strings.setdefault(value,ref)

    def text_reference(self,value):
        if len(value)<24:return None
        if value in self.cache:return self.cache[value]
        if value in self.strings:return {'$chi_base':self.strings[value]}
        if self.anchors is None:
            self.anchors={}
            for original,ref in self.strings.items():
                for at in range(0,len(original)-11,12):
                    self.anchors.setdefault(original[at:at+12],[]).append((original,ref,at))
        parts=[];cursor=0;pos=0
        while pos+12<=len(value):
            best=None
            for original,ref,at in self.anchors.get(value[pos:pos+12],[]):
                # Compare spans in C via string slices instead of walking
                # thousands of repeated transparent pixels in Python.
                left=0;limit=min(pos-cursor,at)
                while left<limit:
                    middle=(left+limit+1)//2
                    if value[pos-middle:pos]==original[at-middle:at]:left=middle
                    else:limit=middle-1
                right=12;limit=min(len(value)-pos,len(original)-at)
                while right<limit:
                    middle=(right+limit+1)//2
                    if value[pos:pos+middle]==original[at:at+middle]:right=middle
                    else:limit=middle-1
                length=left+right
                if length>=24 and (best is None or length>best[0]):best=(length,pos-left,at-left,ref)
            if best is None:pos+=1;continue
            length,start,at,ref=best
            if start>cursor:parts.append(value[cursor:start])
            parts.append(dict(source=ref,at=at,length=length));cursor=start+length;pos=cursor
        if not parts:result=None
        else:
            if cursor<len(value):parts.append(value[cursor:])
            result={'$chi_text':parts}
        self.cache[value]=result;return result


def base_index(files):
    result=TextReferenceIndex()
    def visit(value,file,path):
        if (isinstance(value,str) and len(value)>=24) or (isinstance(value,list) and len(value)>=8):
            result.add(value,dict(file=file,path=path))
        if isinstance(value,dict):
            for key,item in value.items():visit(item,file,[*path,key])
        elif isinstance(value,list):
            for i,item in enumerate(value):visit(item,file,[*path,i])
    for name,data in files.items():
        if name.endswith('.json'):visit(json.loads(data),name,[])
    if 'chi/talk-data.bin' in files:
        for i,text in enumerate(native_texts(files['chi/talk-data.bin'])):
            if len(text)>=24:result.add(text,dict(file='chi/talk-data.bin',path=[i]))
    return result

def references_only(value,index):
    # New objects may reuse a speech/frame from a different original object.
    # Store a reference into the pinned local baseline, never that payload.
    if isinstance(value,(dict,list,str)) and sha(value) in index:return {'$chi_base':index[sha(value)]}
    if isinstance(value,str) and isinstance(index,TextReferenceIndex):return index.text_reference(value) or value
    if isinstance(value,dict) and ('$chi_base' in value or '$chi_text' in value):return value
    if isinstance(value,dict):return {k:references_only(v,index) for k,v in value.items()}
    if isinstance(value,list):return [references_only(v,index) for v in value]
    return value

def resolve_references(value,files):
    def source(ref):
        try:
            raw=files[ref['file']]
            return copy.deepcopy(_get(native_texts(raw) if ref['file']=='chi/talk-data.bin' else json.loads(raw),ref['path']))
        except (KeyError,IndexError,TypeError,StopIteration) as error:raise EditorError('Recipe original reference does not exist: '+str(ref)) from error
    if isinstance(value,dict):
        if set(value)=={'$chi_base'}:
            return source(value['$chi_base'])
        if set(value)=={'$chi_text'}:
            parts=[];size=0
            for part in value['$chi_text']:
                if isinstance(part,str):text=part
                else:
                    text=source(part['source']);at,length=part['at'],part['length']
                    if not isinstance(text,str) or at+length>len(text):raise EditorError('Recipe original text span is out of range.')
                    text=text[at:at+length]
                size+=len(text)
                if size>16*1024*1024:raise EditorError('Reconstructed recipe text exceeds 16 MiB.')
                parts.append(text)
            return ''.join(parts)
        return {k:resolve_references(v,files) for k,v in value.items()}
    if isinstance(value,list):return [resolve_references(v,files) for v in value]
    return value

def export_recipe(document,source,output,cancel=None,progress=lambda _:None):
    if document.manifest.get('requires')!='chi-local-dos-1.03':raise EditorError('Open an imported CHI campaign to export its reconstruction recipe.')
    source=plain_path(source);output=output_path(output,source)
    if output.exists():raise EditorError('Recipe output already exists; choose a new filename.')
    if not output.parent.is_dir():raise EditorError('Choose an existing recipe output parent.')
    campaign=json.loads(document.metadata['campaign.json'])
    header=dict(edition=campaign['edition'],package_id=document.manifest['package_id'],content_version=document.manifest['content_version'],title=document.manifest['title'],
        spatial=bool(document.manifest.get('chi_spatial')),bridge=bool(document.manifest.get('chi_bridge')),art_bases=art_bases(document))
    document.validate();target=runtime_files(document)
    with tempfile.TemporaryDirectory(prefix='.chi-recipe-export-',dir=output.parent) as temp:
        base=base_project(source,Path(temp)/'base',header,document.validator,cancel,progress);before=runtime_files(base);rows=[];index=base_index(before)
        for name in sorted(set(before)|set(target)):
            check_cancel(cancel)
            if name not in target:
                if name.endswith('.json'):rows.append(dict(file=name,changes=diff(json.loads(before[name]),None),encoding='pretty'))
                continue
            if before.get(name)==target[name]:continue
            if name.endswith('.json'):
                value=json.loads(target[name]);changes=diff(json.loads(before[name]) if name in before else None,value,text_index=index)
                from campaign_source import canonical
                style='pretty' if encoded(value)==target[name] else 'canonical' if canonical(value)==target[name] else None
                if style is None:raise EditorError('Save this JSON through the editor before recipe export: '+name)
            elif name.endswith('.lua'):changes=diff(before.get(name,b'').decode('utf-8'),target[name].decode('utf-8'),text_index=index);style='text'
            else:raise EditorError('Modified binary resource cannot be included in an asset-free recipe: '+name+'. Use the resource/pixel editors so its source and edits remain reconstructable.')
            rows.append(dict(file=name,changes=changes,encoding=style))
        for row in rows:
            for change in row['changes']:
                if 'value' in change:change['value']=references_only(change['value'],index)
                for edit in change.get('edits',[]):edit['text']=references_only(edit['text'],index)
        recipe=dict(format=FORMAT,schema_version=1,base=header,base_digest=fingerprint(before),result_digest=fingerprint(target),files=rows)
        check_recipe(recipe)
        # Prove exact reconstruction before giving the user a shareable recipe.
        rebuilt=apply_files(before,recipe)
        if fingerprint(rebuilt)!=recipe['result_digest']:raise EditorError('Recipe did not reproduce the edited runtime files.')
        check_cancel(cancel);pending=Path(temp)/'recipe.json';pending.write_bytes(encoded(recipe));publish(pending,output)
    return dict(status='exported',file=str(output),changes=sum(len(r['changes']) for r in rows),result_digest=recipe['result_digest'])

def apply_files(files,recipe):
    if fingerprint(files)!=recipe['base_digest']:raise EditorError('Recipe baseline differs from this importer/runtime revision. Use the matching kit or export a new recipe.')
    result=dict(files)
    for row in recipe['files']:
        name=row['file'];old=result.get(name)
        value=(json.loads(old) if name.endswith('.json') else old.decode('utf-8')) if old is not None else None
        updated=patch(value,resolve_references(row['changes'],files))
        if updated is None:result.pop(name,None)
        else:
            from campaign_source import canonical
            result[name]=canonical(updated) if row['encoding']=='canonical' else encoded(updated) if name.endswith('.json') else updated.encode('utf-8')
    return result

def build_recipe(recipe,source,output,validator,cancel=None,progress=lambda _:None):
    check_recipe(recipe);source=plain_path(source);output=output_path(output,source)
    if output.exists():raise EditorError('Choose a new recipe output outside original/reference directories.')
    if not output.parent.is_dir():raise EditorError('Choose an existing output parent folder.')
    with tempfile.TemporaryDirectory(prefix='.chi-recipe-',dir=output.parent) as temp:
        root=Path(temp);doc=base_project(source,root/'base',recipe['base'],validator,cancel,progress)
        files=apply_files(runtime_files(doc),recipe)
        if fingerprint(files)!=recipe['result_digest']:raise EditorError('Reconstructed recipe content digest mismatch.')
        stage=root/'game';stage.mkdir()
        # Preserve generated provenance/credits; overlay only declarative files.
        for name,data in {**doc.files(),**files}.items():
            if name in runtime_files(doc) and name not in files:continue
            path=child(stage,name);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        candidate=ProjectDocument(stage,validator);candidate.validate()
        if candidate.manifest['requires']!='chi-local-dos-1.03' or json.loads(candidate.metadata['campaign.json'])['edition']!=recipe['base']['edition']:
            raise EditorError('A CHI recipe must retain its native dependency and edition.')
        check_cancel(cancel);publish(stage,output)
    return dict(status='built',project=str(output),edition=recipe['base']['edition'],result_digest=recipe['result_digest'])

def schema():
    from authoring_contract import obj,array,integer,ID,TEXT,enum
    digest=dict(type='string',pattern='^[0-9a-f]{64}$')
    # Paths are validated structurally here; runtime lookup/precondition checks
    # reject invalid selectors before any files are published.
    change=obj(dict(op=enum('set','remove','copy','order','keys','splice'),path=array(True,0,32),before=digest,value=True,source=array(True,0,32),ids=array(ID,0,4096),keys=array(TEXT,0,4096),edits=array(obj(dict(at=integer(0,16777216),delete=integer(0,16777216),text=True),['at','delete','text']),0,65536)),['op','path'])
    art=obj(dict(id=ID,kind=enum('tile','sprite','screen','font','animation','portrait'),resource=TEXT,index=integer(0,375),count=integer(1,376)),['id','kind','resource','index','count'])
    package=dict(type='string',pattern='^[a-z][a-z0-9._-]{0,62}$')
    base=obj(dict(edition=enum('original','updated'),package_id=package,content_version=TEXT,title=TEXT,spatial={'type':'boolean'},bridge={'type':'boolean'},art_bases=array(art,0,256)),['edition','package_id','content_version','title','spatial','bridge','art_bases'])
    return obj(dict(format={'const':FORMAT},schema_version={'const':1},base=base,base_digest=digest,result_digest=digest,files=array(obj(dict(file=TEXT,encoding=enum('pretty','canonical','text'),changes=array(change,0,MAX_CHANGES)),['file','changes','encoding']),0,256)),['format','schema_version','base','base_digest','result_digest','files'])

def main():
    import argparse
    from app_runtime import binary
    from authoring_contract import read_json
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='action',required=True)
    for action in ('export','build'):
        sub=s.add_parser(action);sub.add_argument('--data',type=Path,required=True);sub.add_argument('--output',type=Path,required=True);sub.add_argument('--validator',type=Path)
        sub.add_argument('--project' if action=='export' else '--file',type=Path,required=True)
    args=p.parse_args();tool=args.validator or binary('btp-project')
    try:
        result=export_recipe(ProjectDocument(args.project,tool),args.data,args.output) if args.action=='export' else build_recipe(read_json(args.file),args.data,args.output,tool)
        print(json.dumps(result,indent=2))
    except (EditorError,OSError,ValueError,KeyError,IndexError,TypeError,StopIteration) as error:p.exit(1,str(error)+'\n')
if __name__=='__main__':main()
