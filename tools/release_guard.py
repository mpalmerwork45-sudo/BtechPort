"""Inspect actual staged/package/archive payloads before distribution.

Known raw-file hashes, cache signatures, private CHI formats, provenance and
recognized original tile pixels are checked. Stripped/altered arbitrary assets
cannot be identified reliably; this is an enforcement aid, not license clearance.
"""
from __future__ import annotations
import hashlib,json,stat,subprocess,tarfile,zipfile
from pathlib import Path,PurePosixPath
from editor_model import EditorError
from asset_provenance import check_files,declared_payload,digest
ROOT=Path(__file__).resolve().parents[1]
MAX_FILE=64*1024*1024
MAX_TOTAL=512*1024*1024
PRIVATE={'btp-chi-campaign-v1','btp-chi-spatial-v1','btp-chi-scripts-v1'}

def known():
    inventory=json.loads((ROOT/'docs/chi-import-inventory.json').read_bytes())
    raw={r['sha256'] for r in inventory['files']};pixels=set()
    for path in (ROOT/'examples').glob('*/CHI-TILES.json'):
        pixels.update(r['original_sha256'] for r in json.loads(path.read_bytes()).get('tiles',[]))
    return raw,pixels

def check_payload(name,data,signatures=None):
    raw,pixels=signatures or known()
    if len(data)>MAX_FILE:raise EditorError('Distribution file exceeds 64 MiB: '+name)
    if hashlib.sha256(data).hexdigest() in raw or data[:4] in (b'BTTA',b'BTCC',b'BTW3'):
        raise EditorError('Original-game file/cache in distribution: '+name)
    if not name.endswith('.json'):return
    try:value=json.loads(data)
    except (ValueError,UnicodeError) as error:raise EditorError('Invalid distribution JSON: '+name) from error
    if isinstance(value,dict) and value.get('format')=='btp-chi-recipe-v1':
        from chi_recipe import check_recipe
        check_recipe(value)
    elif declared_payload(value):raise EditorError('Declared original-derived/unknown payload in distribution: '+name)
    def visit(v):
        if isinstance(v,dict):
            if isinstance(v.get('format'),str) and v['format'] in PRIVATE or v.get('requires')=='chi-local-dos-1.03':
                raise EditorError('Private imported campaign document in distribution: '+name)
            if 'frames' in v and digest(v['frames']) in pixels:
                raise EditorError('Recognized original tile pixels in distribution: '+name)
            for item in v.values():visit(item)
        elif isinstance(v,list):
            for item in v:visit(item)
    visit(value)

def check_name(name):
    path=PurePosixPath(name)
    if path.is_absolute() or not path.parts or any(p in ('','..','.') or '\\' in p or ':' in p for p in path.parts):
        raise EditorError('Unsafe distribution entry: '+name)
    return path

def inspect_files(files):
    signatures=known();total=0
    for name,data in files.items():
        check_name(name);total+=len(data);check_payload(name,data,signatures)
    if total>MAX_TOTAL:raise EditorError('Distribution exceeds 512 MiB inspection budget.')
    projects=0
    for name,data in files.items():
        if name=='project.json' or name.endswith('/project.json'):
            prefix=name[:-len('project.json')]
            check_files({key[len(prefix):]:value for key,value in files.items() if key.startswith(prefix)})
            projects+=1
    return dict(status='passed',files=len(files),bytes=total,projects=projects,
        limitations=['Recognizes known/declared original payloads; stripped or altered arbitrary assets still require provenance review.'])

def directory(folder,inventory=True):
    folder=Path(folder);files={};total=0
    for path in sorted(folder.rglob('*')):
        if path.is_symlink():raise EditorError('Distribution contains a symlink: '+str(path))
        if path.is_file():
            size=path.stat().st_size;total+=size
            if size>MAX_FILE or total>MAX_TOTAL:raise EditorError('Distribution exceeds inspection budget: '+str(path))
            files[path.relative_to(folder).as_posix()]=path.read_bytes()
    if inventory:
        if 'DISTRIBUTION.json' not in files:raise EditorError('Missing DISTRIBUTION.json.')
        report=json.loads(files['DISTRIBUTION.json']);expected={'DISTRIBUTION.json'}
        for row in report['files']:
            name=row['path'];check_name(name)
            if name in expected:raise EditorError('Duplicate distribution inventory entry: '+name)
            expected.add(name)
            if name not in files or len(files[name])!=row['bytes'] or hashlib.sha256(files[name]).hexdigest()!=row['sha256']:
                raise EditorError('Distribution inventory mismatch: '+name)
        if expected!=set(files):raise EditorError('Uninventoried files in distribution: '+', '.join(sorted(set(files)-expected)[:4]))
    return inspect_files(files)

def archive(path):
    path=Path(path);files={};total=0
    def add(name,data):
        nonlocal total
        check_name(name)
        if name in files:raise EditorError('Duplicate archive entry: '+name)
        total+=len(data)
        if total>MAX_TOTAL:raise EditorError('Archive exceeds inspection budget.')
        files[name]=data
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as bundle:
            for entry in bundle.infolist():
                check_name(entry.filename)
                if entry.is_dir():continue
                if stat.S_ISLNK(entry.external_attr>>16) or entry.file_size>MAX_FILE:raise EditorError('Archive link/oversized file: '+entry.filename)
                add(entry.filename,bundle.read(entry))
    else:
        with tarfile.open(path,'r:*') as bundle:
            for entry in bundle:
                check_name(entry.name)
                if entry.isdir():continue
                if not entry.isfile() or entry.size>MAX_FILE:raise EditorError('Archive link/oversized file: '+entry.name)
                add(entry.name,bundle.extractfile(entry).read())
    # Enforce the package inventory inside the archive as well as scanning
    # all actual members. Never extract untrusted archive paths to disk.
    inventories=[n for n in files if n.endswith('/DISTRIBUTION.json') or n=='DISTRIBUTION.json']
    if len(inventories)!=1:raise EditorError('Archive requires one distribution inventory.')
    name=inventories[0];prefix=name[:-len('DISTRIBUTION.json')];report=json.loads(files[name]);expected={name}
    for row in report['files']:
        check_name(row['path']);entry=prefix+row['path']
        if entry in expected:raise EditorError('Duplicate archive inventory entry: '+entry)
        expected.add(entry)
        if entry not in files or len(files[entry])!=row['bytes'] or hashlib.sha256(files[entry]).hexdigest()!=row['sha256']:
            raise EditorError('Archive inventory mismatch: '+entry)
    if set(files)!=expected:raise EditorError('Archive contains uninventoried entries.')
    return inspect_files(files)

def staged():
    names=subprocess.check_output(['git','diff','--cached','--name-only','--diff-filter=ACMR','-z'],cwd=ROOT).decode().split('\0')
    signatures=known();count=0
    for name in names:
        if name:check_payload(name,subprocess.check_output(['git','show',':'+name],cwd=ROOT),signatures);count+=1
    return dict(status='passed',staged_files=count)

def main():
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('path',type=Path,nargs='?');p.add_argument('--staged',action='store_true');a=p.parse_args()
    try:
        if a.staged:result=staged()
        elif a.path:result=directory(a.path) if a.path.is_dir() else archive(a.path)
        else:p.error('Choose a distribution directory/archive, or --staged.')
        print(json.dumps(result,indent=2))
    except (OSError,ValueError,EditorError,KeyError,tarfile.TarError,zipfile.BadZipFile) as e:p.exit(1,str(e)+'\n')
if __name__=='__main__':main()
