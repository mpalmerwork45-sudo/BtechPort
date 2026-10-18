"""Find explicit package references before destructive authoring operations.

Lua is opaque: references in script source are never guessed or rewritten.
"""
import copy
import json
from dataclasses import dataclass
from editor_model import EditorError

TEXT_KEYS={'name','label','text','description','message','title','notes','source_url','author','license'}


@dataclass
class Usage:
    section: str
    path: tuple
    asset: str
    value: object

    @property
    def location(self):return self.section+'.'+'.'.join(map(str,self.path))


def definitions(document):
    result={}
    for section in ('content','adventure','art'):
        data=getattr(document,section) or {}
        for collection,values in data.items():
            if not isinstance(values,list):continue
            for index,value in enumerate(values):
                if isinstance(value,dict) and 'id' in value:result[value['id']]=(section,collection,index,value)
                elif collection=='flags' and isinstance(value,str):result[value]=(section,collection,index,{'id':value})
    return result


def usages(document,identity):
    found=[];definition=definitions(document).get(identity)
    own=definition[:3] if definition else None
    tile_key=definition[3].get('key') if definition and definition[1]=='tiles' else None
    def walk(value,section,path=(),asset=None):
        if own and (section,*path)==own:return
        if isinstance(value,dict):
            asset=value.get('id',asset)
            for key,item in value.items():
                if key not in TEXT_KEYS and key!='id':walk(item,section,path+(key,),asset)
        elif isinstance(value,list):
            for index,item in enumerate(value):walk(item,section,path+(index,),asset)
        elif isinstance(value,str):
            exact=value==identity or (value.startswith('package:') and value[8:]==identity)
            row=tile_key and 'rows' in path and document.adventure.get('schema_version')==1 and tile_key in value
            if exact or row:found.append(Usage(section,path,asset or section,value))
    for section in ('content','adventure','art','manifest'):walk(getattr(document,section),section)
    name=document.manifest.get('presentation')
    if name:walk(json.loads(document.metadata.get(name,document.snapshot[name])),'presentation')
    return found


def replacements(document,identity):
    all_items=definitions(document);original=all_items.get(identity)
    if not original:return []
    section,collection,_,value=original
    return [item for item,info in all_items.items() if item!=identity and info[:2]==(section,collection)
            and (collection!='images' or (info[3].get('kind'),info[3].get('width'),info[3].get('height'))==(value.get('kind'),value.get('width'),value.get('height')))
            and (collection!='mechs' or info[3].get('unit_type','mech')==value.get('unit_type','mech'))]


def remove(document,identity,replacement=None):
    all_items=definitions(document)
    if identity not in all_items:raise EditorError('The selected asset no longer exists.')
    section,collection,index,value=all_items[identity];refs=usages(document,identity)
    if replacement and replacement not in replacements(document,identity):raise EditorError('Choose a compatible replacement from this collection.')
    if refs and not replacement:raise EditorError(f'{identity} is used in {len(refs)} places. Choose a replacement or update those references first.')
    data={name:copy.deepcopy(getattr(document,name)) for name in ('content','adventure','art','manifest')}
    metadata=dict(document.metadata)
    name=document.manifest.get('presentation')
    if name:data['presentation']=json.loads(metadata.get(name,document.snapshot[name]))
    for ref in refs:
        target=data[ref.section]
        for part in ref.path[:-1]:target=target[part]
        old=target[ref.path[-1]]
        if collection=='tiles' and document.adventure['schema_version']==1 and 'rows' in ref.path:
            new=old.replace(value['key'],all_items[replacement][3]['key'])
        else:new='package:'+replacement if old=='package:'+identity else replacement
        target[ref.path[-1]]=new
    data[section][collection].pop(index)
    if any(ref.section=='presentation' for ref in refs):
        from editor_model import encoded
        metadata[name]=encoded(data['presentation'])
    with document.command('Delete '+value.get('name',identity)):
        document.replace_all(*(data[k] for k in ('content','adventure','art','manifest')),metadata)
        # Compatibility includes domain constraints, beyond collection/kind.
        # Roll back if replacement would invalidate an encounter, sprite or map.
        document.validate()


def dialog(owner,identity,delete=False):
    import tkinter as tk
    from tkinter import ttk
    from adventure_editor import Form
    from editor_session import scope_of
    scope=scope_of(owner);document=scope.document
    scope.transact(lambda:None)
    refs=usages(document,identity);f=Form(owner,'Delete asset' if delete else 'Find usages')
    ttk.Label(f.body,text=identity+'\n'+str(len(refs))+' explicit package reference(s)',wraplength=520).grid(row=f.row,column=0,columnspan=3,sticky='w');f.row+=1
    listing=tk.Listbox(f.body,width=65,height=10);listing.grid(row=f.row,column=0,columnspan=3,sticky='ew');f.row+=1
    for ref in refs:listing.insert('end',ref.asset+' / '+ref.location)
    def navigate(_=None):
        if not listing.curselection():return
        ref=refs[listing.curselection()[0]];known=definitions(document).get(ref.asset)
        if not known:return
        section,collection,index,item=known
        workspace=getattr(scope,'workspace',None)
        if not workspace:return
        f.window.destroy()
        if collection=='events':workspace.open_event(ref.asset)
        elif collection=='maps':workspace.open_map(ref.asset)
        elif collection=='images':scope.owner.graphics_editor().selected=ref.asset;scope.owner.graphics_editor().edit()
        elif collection in ('mechs','weapons','equipment','people'):
            kind={'mechs':'Mechs','weapons':'Weapons','equipment':'Equipment','people':'Infantry'}[collection]
            workspace.open_unit(kind,ref.asset,scope.owner)
        else:scope.owner.edit_adventure();scope.owner.map_editor.tabs.select(scope.owner.map_editor.world_tab)
    listing.bind('<Double-1>',navigate);listing.bind('<Return>',navigate)
    ttk.Button(f.body,text='Open selected usage',command=navigate).grid(row=f.row,column=0,columnspan=3,sticky='w');f.row+=1
    scripts=document.manifest.get('scripts',[])
    if scripts:
        ttk.Label(f.body,text='Lua may refer to this asset. Review scripts manually; the editor only replaces explicit package references.',wraplength=520).grid(row=f.row,column=0,columnspan=3,sticky='w');f.row+=1
    if delete:
        choices=replacements(document,identity)
        if refs:f.field('replacement',choices[0] if choices else 'none',choices or ['none'])
        if scripts:f.field('scripts_reviewed','No',['No','Yes'],label='I reviewed Lua references')
        def apply(values):
            if scripts and values['scripts_reviewed']!='Yes':raise EditorError('Review Lua references before deleting this asset.')
            remove(document,identity,values.get('replacement'))
            if hasattr(scope,'workspace'):
                from editor_history import refresh_scope
                refresh_scope(scope.workspace,scope)
        f.submit(apply)
    else:ttk.Button(f.window,text='Close',command=f.window.destroy).pack(pady=8)
    return f
