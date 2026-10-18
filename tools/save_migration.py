"""Explicit migration of compatible project revisions; never edit an old save."""
import copy,hashlib,json,os,re,struct,subprocess,tempfile,zlib
from pathlib import Path
from editor_model import EditorError,ProjectDocument,references

def compatible(old,new):
    """Preserve every existing ordinal and rule; permit presentation edits and
    append-only definitions. Reject ambiguous remaps rather than guessing."""
    for key in ('package_id','requires','startup','rules_profile','save_policy'):
        if old.manifest.get(key)!=new.manifest.get(key):raise EditorError(f'Migration changes {key}.')
    if old.adventure is None or new.adventure is None:raise EditorError('Migration currently supports authored adventures only.')
    def equal(a,b,label):
        if a!=b:raise EditorError(f'Incompatible {label}; existing IDs, order and gameplay rules must be retained.')
    def strip(value,fields):return {k:v for k,v in value.items() if k not in fields}
    def prefix(a,b,label,fields=()):
        if len(b)<len(a):raise EditorError(f'Migration removes {label}.')
        for i,v in enumerate(a):equal(strip(v,fields) if isinstance(v,dict) else v,strip(b[i],fields) if isinstance(v,dict) else b[i],f'{label}[{i}]')
    for key in ('rules','services'):equal(old.content.get(key),new.content.get(key),key)
    # Presentation IDs may be changed, but weapon/ammo/equipment handles are
    # ordinal inside mutable instance records and therefore remain prefixes.
    for key in ('weapons','ammunition','equipment','mechs'):
        prefix(old.content.get(key,[]),new.content.get(key,[]),key,('name','presentation') if key=='mechs' else ('name',))
    a,b=copy.deepcopy(old.adventure),copy.deepcopy(new.adventure)
    for key,fields in (('people',('name','image')),('events',('text','labels','image','portrait')),('flags',()),('objectives',('title','text'))):
        prefix(a.pop(key,[]),b.pop(key,[]),key,fields)
    for tile in a.get('tiles',[]):
        for key in ('sheet','graphic','color'):tile.pop(key,None)
    for tile in b.get('tiles',[]):
        for key in ('sheet','graphic','color'):tile.pop(key,None)
    for doc in (a,b):
        for scene in doc.get('maps',[]):
            scene.pop('name',None)
            for door in scene.get('entrances',[]):door.pop('name',None);door.pop('image',None)
    equal(a,b,'map topology, encounters or starting party')
    equal(old.manifest.get('scripts',[]),new.manifest.get('scripts',[]),'script declarations')
    for script in old.manifest.get('scripts',[]):equal(old.snapshot[script['file']],new.snapshot[script['file']],'script source')
    if old.manifest.get('presentation'):
        a=json.loads(old.snapshot[old.manifest['presentation']]);b=json.loads(new.snapshot[new.manifest['presentation']])
        # Formation and combat inputs are gameplay. Indexed pixels/sounds are
        # replaceable presentation; the destination parser checks their limits.
        fields=('palette','font','tiles','sprites','portraits','sounds')
        equal(strip(a,fields),strip(b,fields),'independent rules/formation')
    return ['Existing unit, weapon, person, event and flag ordinals preserved.',
            'Map topology, encounters, rules and script source unchanged.',
            'Presentation changes and appended definitions accepted.']

def project_digest(doc):
    result=subprocess.run([str(doc.validator),'validate',str(doc.root)],capture_output=True,text=True,timeout=30)
    match=re.search(r'SHA-256 ([0-9a-f]{64})',result.stdout)
    if result.returncode or not match:raise EditorError(result.stderr or 'Validator did not return a content digest.')
    return bytes.fromhex(match[1])

def check_save(doc,settings,path):
    command=[str(Path(settings['player']).resolve()),'--headless','--project',str(doc.root),'--load',str(path)]
    if doc.manifest['requires']!='none':
        for key in ('data','dialogue-data','combat-data','world-data'):
            if not settings.get(key):raise EditorError('Configure original resources in Player setup for this game.')
            command.extend(['--'+key,str(Path(settings[key]).resolve())])
    result=subprocess.run(command,capture_output=True,text=True,timeout=30)
    if result.returncode:raise EditorError(result.stderr.strip() or 'Player rejected the save.')
    return json.loads(result.stdout)

def migrate(old,new,source,target,settings):
    source,target=Path(source),Path(target)
    if target.exists() or target.is_symlink():raise EditorError('Choose a new save filename; migration never overwrites saves.')
    checks=compatible(old,new);before=check_save(old,settings,source)
    data=bytearray(source.read_bytes())
    if len(data)<160 or data[:4]!=b'BTG1':raise EditorError('Expected a project save (BTG1).')
    if data[80:112]!=project_digest(old):raise EditorError('The supplied old project does not match this save.')
    version=new.manifest['content_version'].encode('ascii')
    data[48:80]=version.ljust(32,b'\0');data[80:112]=project_digest(new)
    struct.pack_into('<I',data,8,zlib.crc32(data[16:]))
    # Both real-player decoders must accept it before the exclusive output
    # appears. Payload bytes remain identical, including damage and progress.
    with tempfile.TemporaryDirectory(prefix='btp-migrate-') as tmp:
        candidate=Path(tmp)/'candidate.btp';candidate.write_bytes(data)
        after=check_save(new,settings,candidate)
    report=dict(source=str(source.resolve()),destination=str(target.resolve()),
                source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                target_sha256=hashlib.sha256(data).hexdigest(),checks=checks,
                tick=after['tick'],credits=after['credits'])
    if before['tick']!=after['tick'] or before['credits']!=after['credits']:raise EditorError('Migration changed progress unexpectedly.')
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as out:out.write(data)
    return report

def dialog(editor):
    from tkinter import filedialog,messagebox
    editor.apply_form();editor.document.save()
    root=filedialog.askdirectory(title='Old project snapshot used by the save',parent=editor.window)
    if not root:return
    source=filedialog.askopenfilename(title='Old project save',filetypes=[('Project save','*.btp')],parent=editor.window)
    if not source:return
    target=filedialog.asksaveasfilename(title='New migrated save copy',defaultextension='.btp',parent=editor.window)
    if not target:return
    report=migrate(ProjectDocument(Path(root),editor.validator),editor.document,source,target,editor.settings)
    editor.status.set('Migrated save copy: '+str(target))
    messagebox.showinfo('Save migrated','Saved a validated copy.\n'+ '\n'.join(report['checks']),parent=editor.window)

if __name__=='__main__':
    import argparse
    from app_runtime import settings,binary
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ('old-project','new-project','save','output'):p.add_argument('--'+arg,required=True,type=Path)
    args=p.parse_args()
    try:print(json.dumps(migrate(ProjectDocument(args.old_project,binary('btp-project')),ProjectDocument(args.new_project,binary('btp-project')),args.save,args.output,settings()),indent=2))
    except (EditorError,OSError,ValueError) as exc:p.exit(1,str(exc)+'\n')
