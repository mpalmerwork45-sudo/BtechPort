"""Saved-game discovery, exact-revision retention and non-destructive recovery.

Envelope inspection is descriptive. The native player must also accept a save
before Continue or Recover can use it; this module never rewrites identities.
"""
from dataclasses import dataclass
from itertools import chain
from pathlib import Path
import hashlib,json,os,re,shutil,struct,subprocess,tempfile,uuid,zlib
from editor_model import EditorError,ProjectDocument,references,needs_original,encoded


def digest(document):
    return document.validate().rsplit('SHA-256 ',1)[1].strip()


def revision_key(document):
    files=document.files()
    return hashlib.sha256(b''.join(files[n] for n in references(document.manifest))).hexdigest()


def valid_package_id(value):
    # Match the native unnamespaced ID grammar before using a recovered
    # identity from launcher preferences or retained metadata as a directory.
    return isinstance(value,str) and re.fullmatch(r'[a-z][a-z0-9_.-]{0,30}',value) is not None


def retained_package_id(state_dir,source):
    """Identify a moved/invalid working root from private retention records.

    Source paths are a discovery hint only: Continue still validates the exact
    native content fingerprint. A reused path cannot choose between games.
    """
    source=Path(source).resolve();identities=set();base=Path(state_dir)/'save-revisions'
    markers=chain(base.glob('*/*/REVISION.json'),base.glob('*/*/sources/*/SOURCE.json'))
    for index,marker in enumerate(markers):
        if index>=4096:raise EditorError('Retained revision lookup reached its 4,096-record limit. Locate the matching campaign explicitly.')
        try:
            if marker.is_symlink() or not marker.is_file() or marker.stat().st_size>16384:continue
            record=json.loads(marker.read_bytes());identity=record.get('package_id')
            revision=marker.parent if marker.name=='REVISION.json' else marker.parents[2]
            if (record.get('format') in ('btp-save-revision-v1','btp-save-source-v1') and valid_package_id(identity) and
                identity==revision.parent.name and record.get('digest')==revision.name and
                isinstance(record.get('source'),str) and Path(record['source']).resolve()==source):
                identities.add(identity)
        except (OSError,ValueError,TypeError,AttributeError):continue
    if len(identities)>1:raise EditorError('That working path was used by multiple campaigns. Choose the matching retained campaign explicitly.')
    return next(iter(identities),None)


def retain_source(parent,document,signature,source):
    """Remember every editable origin without racing to replace one record.

    Editor Play validates temporary exports, so its actual editable source is
    explicit. Each source has its own atomically published, immutable record.
    """
    source=str(Path(source).resolve())
    record=dict(format='btp-save-source-v1',digest=signature,package_id=document.manifest['package_id'],source=source)
    folder=parent/'sources';folder.mkdir(exist_ok=True)
    target=folder/hashlib.sha256(source.encode('utf-8')).hexdigest()
    def existing():
        try:return not target.is_symlink() and not (target/'SOURCE.json').is_symlink() and json.loads((target/'SOURCE.json').read_bytes())==record
        except (OSError,ValueError):return False
    if target.exists():
        if not existing():raise EditorError('A retained campaign source record was changed: '+str(target))
        return
    from chi_import import publish
    with tempfile.TemporaryDirectory(prefix='.source-',dir=folder) as temporary:
        stage=Path(temporary)/'record';stage.mkdir();(stage/'SOURCE.json').write_bytes(encoded(record))
        try:publish(stage,target)
        except (FileExistsError,EditorError):
            if not existing():raise


def retain_revision(document,state_dir,source=None):
    """Keep one validated playable snapshot per content digest, before playing.
    Editing/moving the working project must not orphan its existing save slots.
    Retained snapshots are private original-derived data when the project is.
    """
    signature=digest(document);source=document.root if source is None else source
    parent=Path(state_dir)/'save-revisions'/document.manifest['package_id']/signature
    target=parent/'game'
    if target.exists():
        if target.is_symlink() or digest(ProjectDocument(target,document.validator))!=signature:
            raise EditorError('A retained save revision was changed. Preserve it separately before continuing: '+str(target))
        retain_source(parent,document,signature,source)
        return target
    parent.mkdir(parents=True,exist_ok=True)
    from chi_import import publish
    with tempfile.TemporaryDirectory(prefix='.revision-',dir=parent) as temporary:
        staged=Path(temporary)/'game';document.export(staged)
        if digest(ProjectDocument(staged,document.validator))!=signature:raise EditorError('Retained revision differs from the validated project.')
        try:publish(staged,target)
        except (FileExistsError,EditorError):
            if not target.is_dir():raise
            if digest(ProjectDocument(target,document.validator))!=signature:raise EditorError('Conflicting retained revision: '+str(target))
    try:
        with (parent/'REVISION.json').open('xb') as record:
            record.write(encoded(dict(format='btp-save-revision-v1',digest=signature,
                package_id=document.manifest['package_id'],title=document.manifest['title'],source=str(Path(source).resolve()))))
    except FileExistsError:pass
    retain_source(parent,document,signature,source)
    return target


@dataclass
class SavedGame:
    path: Path
    slot: int
    location: str
    mtime: float=0
    signature: str=''
    package: str=''
    version: str=''
    tag: str=''
    project: Path|None=None
    error: str=''
    current: bool=False

    @property
    def status(self):
        if self.error:return self.error
        if not self.path.exists():return 'Empty slot'
        if self.tag=='BTG1' and self.project is None:return 'Matching campaign revision needed'
        return 'Current revision' if self.current else 'Earlier revision' if self.tag=='BTG1' else 'Available'


def inspect(path,location,slot=None):
    path=Path(path);match=re.search(r'-([2-6])\.btp$',path.name)
    row=SavedGame(path,slot or (int(match[1]) if match else 1),location)
    if not path.exists():return row
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size>65536:raise ValueError('Unsupported save file')
        row.mtime=path.stat().st_mtime;data=path.read_bytes();row.tag=data[:4].decode('ascii',errors='replace')
        if len(data)<40 or row.tag not in ('BTS1','BTU1','BTU2','BTG1'):raise ValueError('Unsupported save format')
        if struct.unpack_from('<I',data,4)[0]!=len(data)-16 or zlib.crc32(data[16:])!=struct.unpack_from('<I',data,8)[0]:raise ValueError('Damaged save (length or checksum)')
        if row.tag=='BTG1':
            if len(data)<184:raise ValueError('Truncated project save')
            row.package=data[16:48].split(b'\0')[0].decode('ascii');row.version=data[48:80].split(b'\0')[0].decode('ascii');row.signature=data[80:112].hex()
            # A project ID can itself end in "-2" through "-6". Parse the
            # native base name using the envelope ID, before its slot suffix.
            if slot is None:
                native=re.fullmatch(r'game(?:-project-'+re.escape(row.package)+r')?(?:-([2-6]))?\.btp',path.name)
                if native:row.slot=int(native[1]) if native[1] else 1
        elif row.tag.startswith('BTU'):
            if len(data)<136:raise ValueError('Truncated Updated save')
            row.version=data[48:80].split(b'\0')[0].decode('ascii');row.signature=data[80:84].hex()
        else:row.version='Original'
    except (OSError,ValueError,UnicodeError) as error:row.error=str(error)
    return row


def copy_exclusive(source,target):
    """Copy bytes only into a vacant slot; retain source and its timestamp."""
    source,target=Path(source),Path(target)
    if target.exists() or target.is_symlink():raise EditorError('That slot is occupied. Choose an empty slot; existing progress is preserved.')
    if source.is_symlink() or not source.is_file() or source.stat().st_size>65536:raise EditorError('Choose a regular saved-game file.')
    data=source.read_bytes();target.parent.mkdir(parents=True,exist_ok=True)
    output=target.open('xb')
    try:
        with output:output.write(data)
        shutil.copystat(source,target)
    except BaseException:
        # Only this action's new incomplete copy is disposable; an occupied
        # destination failed exclusive creation before entering this block.
        target.unlink(missing_ok=True);raise
    return target


class SaveCatalogue:
    def __init__(self,state_dir,paths,choice='My project',document=None,location='Launcher',validator=None,package_id=None):
        from app_runtime import binary
        self.state_dir=Path(state_dir).resolve();self.paths=dict(paths);self.choice=choice;self.document=document
        self.location=location;self.validator=validator or binary('btp-project');self.warnings=[];self.rows=[];self.projects={}
        self.project_mode=document is not None or package_id is not None
        self.identity=document.manifest['package_id'] if document else package_id if package_id is not None else choice.lower()
        if self.project_mode:
            if not valid_package_id(self.identity):raise EditorError('Invalid saved-game campaign ID.')
            if package_id is not None and self.identity!=package_id:raise EditorError('Saved-game campaign ID disagrees with the project.')
        elif choice not in ('Original','Updated'):raise EditorError('Choose a game or project first.')

    def directory(self,document=None):
        doc=document or self.document
        if doc is None:
            if self.project_mode:raise EditorError('An exact campaign revision is required for its save slots.')
            return self.state_dir/'games'/self.choice.lower()
        key=revision_key(doc)
        return self.state_dir/('play' if self.location=='Editor' else 'games')/self.identity/key[:20 if self.location=='Editor' else 16]

    def leaf(self,slot,document=None):
        from app_runtime import project_slot_name
        doc=document or self.document
        if doc:return project_slot_name(doc,slot)
        return 'game'+('-updated' if self.choice=='Updated' else '')+('' if slot==1 else '-'+str(slot))+'.btp'

    def scan(self,cancel=None):
        self.rows=[];self.warnings=[];self.projects={}
        current=''
        if self.document:
            try:current=digest(self.document)
            except (EditorError,OSError,ValueError) as error:
                # A broken/relocated editable root must not hide older intact
                # campaigns. The known package ID remains the discovery key.
                self.warnings.append('Current project is unavailable; showing retained saves. '+str(error))
                self.document=None
        if self.document:self.projects[current]=self.document.root
        primary=self.directory() if self.document or not self.project_mode else None;paths={}
        def add(folder,label):
            if folder.is_dir() and not folder.is_symlink():
                for path in sorted(folder.glob('*.btp')):
                    if len(paths)>=4096:self.warnings.append('Save scan reached its 4,096-file limit.');return
                    paths.setdefault(path,label)
        if self.project_mode:
            for area,label in (('games','Launcher'),('play','Editor')):
                for folder in sorted((self.state_dir/area/self.identity).glob('*')):add(folder,label)
            runs=sorted((self.state_dir/'play-snapshots').glob('run-*'),key=lambda p:p.name)
            if len(runs)>4096:self.warnings.append('Only the first 4,096 retained editor runs were scanned. Locate a matching campaign if needed.')
            for run in runs[:4096]:
                if cancel and cancel.is_set():raise EditorError('Saved-game scan cancelled.')
                for folder in (run/'play'/self.identity).glob('*'):add(folder,'Earlier editor run')
        else:
            add(primary,'Launcher')
            # The normal legacy command-line saves are outside desktop state.
            # Only inspect that known location for the real workspace.
            from app_runtime import ROOT,STATE
            if self.state_dir==STATE.resolve():
                edition='-updated' if self.choice=='Updated' else ''
                for slot in range(1,7):
                    p=ROOT/'work'/('player-save'+edition+('' if slot==1 else '-'+str(slot))+'.btp')
                    if p.is_file():paths.setdefault(p.resolve(),'Legacy command line')
        for folder in (self.state_dir/'save-backups'/self.identity).glob('*'):add(folder,'Backup')
        for path,label in paths.items():
            row=inspect(path,label)
            if not row.error:
                if self.project_mode and (row.tag!='BTG1' or row.package!=self.identity):row.error='Belongs to another game'
                elif not self.project_mode and (row.tag=='BTG1' or (row.tag=='BTS1')!=(self.choice=='Original')):row.error='Belongs to another edition'
            row.current=bool(self.document and row.signature==current);self.rows.append(row)
        wanted={r.signature for r in self.rows if r.tag=='BTG1' and not r.error}-self.projects.keys()
        roots=[]
        if wanted:
            roots.extend(self.state_dir/'save-revisions'/self.identity/key/'game' for key in sorted(wanted))
            roots.extend(run/'game' for run in runs[:4096])
            # Older modular launcher builds also retained their compiled game.
            roots.extend((self.state_dir/'games'/self.identity).glob('*/package'))
        seen=set()
        for root in roots:
            if not wanted:break
            if cancel and cancel.is_set():raise EditorError('Saved-game scan cancelled.')
            if root in seen or not root.is_dir() or root.is_symlink():continue
            seen.add(root)
            try:
                doc=ProjectDocument(root,self.validator)
                if doc.manifest['package_id']!=self.identity:continue
                key=digest(doc)
                if key in wanted:self.projects[key]=root;wanted.remove(key)
            except (EditorError,OSError,ValueError):continue
        for row in self.rows:
            if row.tag=='BTG1':row.project=self.projects.get(row.signature)
        occupied={row.path for row in self.rows}
        for slot in range(1,7) if primary is not None else ():
            path=primary/self.leaf(slot)
            if path not in occupied:self.rows.append(SavedGame(path,slot,self.location,current=True))
        self.rows.sort(key=lambda r:(r.path.parent!=primary,r.slot,-r.mtime,str(r.path)))
        return self.rows

    def checked(self,row):
        if row.error or not row.path.is_file():raise EditorError(row.error or 'Choose an occupied save slot.')
        from app_runtime import prepare_original
        doc=None
        if row.tag=='BTG1':
            if row.project is None:raise EditorError('Restore or locate the exact campaign revision for this save.')
            # The current draft may differ from disk. Retain the checked bytes
            # rather than accidentally launching a later edited working root.
            doc=self.document if row.current else ProjectDocument(row.project,self.validator)
            project=retain_revision(doc,self.state_dir);doc=ProjectDocument(project,self.validator)
            command=[str(Path(self.paths['player']).resolve()),'--project',str(project)]
            if digest(doc)!=row.signature:raise EditorError('Matching campaign changed since the scan. Refresh saved games.')
            original=needs_original(doc.manifest)
        else:
            command=[str(Path(self.paths['player']).resolve()),'--edition',self.choice.lower()];original=True
        if original:
            prepare_original(self.paths)
            for key in ('data','dialogue-data','combat-data','world-data'):command+=['--'+key,str(Path(self.paths[key]).resolve())]
        result=subprocess.run([*command,'--headless','--load',str(row.path)],capture_output=True,text=True,timeout=30)
        if result.returncode:raise EditorError(result.stderr.strip() or 'The native player rejected this save.')
        return doc,command,json.loads(result.stdout)

    def backup(self,row):
        doc,_,_=self.checked(row)
        return self._backup(row,doc)

    def _backup(self,row,doc):
        from datetime import datetime
        folder=self.state_dir/'save-backups'/self.identity/(datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8])
        return copy_exclusive(row.path,folder/self.leaf(row.slot,doc))

    def recover(self,row,slot):
        if type(slot) is not int or not 1<=slot<=6:raise EditorError('Choose slot 1 through 6.')
        doc,_,_=self.checked(row)
        target=self.directory(doc)/self.leaf(slot,doc)
        return copy_exclusive(row.path,target)

    def resume(self,row):
        doc,command,state=self.checked(row)
        # Keep the selected original before any subsequent in-game quicksave.
        self._backup(row,doc)
        folder=self.directory(doc);folder.mkdir(parents=True,exist_ok=True)
        quick=folder/self.leaf(1,doc)
        if quick.exists() and quick!=row.path:
            self._backup(inspect(quick,self.location),doc)
        return [*command,'--load',str(row.path),'--save-file',str(folder/'game.btp')],state

    def locate(self,project,signature=None):
        doc=ProjectDocument(Path(project),self.validator)
        if doc.manifest['package_id']!=self.identity:raise EditorError('That project belongs to a different game.')
        if signature and digest(doc)!=signature:raise EditorError('That project is a different revision. Locate the exact content used by the selected save.')
        root=retain_revision(doc,self.state_dir)
        self.projects[digest(doc)]=root
        return root
