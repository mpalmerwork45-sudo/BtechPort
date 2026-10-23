#!/usr/bin/env python3
"""Import private Original/Updated CHI projects from a supported DOS installation."""
from __future__ import annotations
import argparse
import ctypes
import errno
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import uuid

from chi_audit import ROOT, RESOURCE_FILES, SOURCE_FILES
from editor_model import EditorError, encoded, run_validator

FORMAT='btp-chi-campaign-v1'
RUNTIME_FILES=(*RESOURCE_FILES,'talk-data.bin','combat-data.bin','world-data.bin')
RESOURCE_PATHS=['chi/'+name for name in RUNTIME_FILES]
INVENTORY=ROOT/'docs/chi-import-inventory.json'


class ImportCancelled(EditorError):
    pass


def check_cancel(cancel):
    if cancel is not None and cancel.is_set():raise ImportCancelled('Import cancelled; existing projects and saves were preserved.')


def plain_path(path):
    """Check before resolve, including directory junctions on Windows."""
    path=Path(os.path.abspath(Path(path).expanduser()))
    for part in (path,*path.parents):
        if part.is_symlink() or (part.exists() and getattr(part.stat(),'st_file_attributes',0)&0x400):
            raise EditorError('Import paths cannot contain symlinks or junctions: '+str(part))
    return path


def read_source(source, cancel=None, progress=lambda _:None):
    expected={r['file']:r for r in json.loads(INVENTORY.read_bytes())['files']}
    if set(expected)!=set(SOURCE_FILES):raise EditorError('Importer source inventory is incomplete.')
    result={}
    for i,name in enumerate(SOURCE_FILES):
        check_cancel(cancel);path=plain_path(source/name);row=expected[name]
        if not path.is_file():raise EditorError('Missing original file: '+name)
        if path.stat().st_size!=row['bytes']:raise EditorError('Unsupported or changed original file (size): '+name)
        with path.open('rb') as file:data=file.read(row['bytes']+1)
        if len(data)!=row['bytes'] or hashlib.sha256(data).hexdigest()!=row['sha256']:
            raise EditorError('Unsupported or changed original file (SHA-256): '+name+'; supported version is DOS 1.03.')
        result[name]=data;progress(f'Verified {i+1}/{len(SOURCE_FILES)} original files')
    return result


def run(command,cancel=None):
    with subprocess.Popen([str(v) for v in command],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True) as process:
        deadline=time.monotonic()+30
        while True:
            try:
                check_cancel(cancel)
                if time.monotonic()>deadline:raise EditorError('Import tool exceeded its 30-second budget.')
                stdout,stderr=process.communicate(timeout=.1);break
            except subprocess.TimeoutExpired:continue
            except BaseException:
                process.kill();process.communicate();raise
        if process.returncode:raise EditorError(stderr.strip() or stdout.strip() or 'Import tool failed.')
        return stdout


def publish(stage,target):
    """Publish one complete pair without replacing even an empty destination."""
    if os.name=='nt':os.rename(stage,target);return
    libc=ctypes.CDLL(None,use_errno=True)
    rename=getattr(libc,'renameat2',None)
    if rename is None:raise EditorError('Atomic no-replace directory publication is unavailable on this platform.')
    rename.argtypes=(ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint)
    rename.restype=ctypes.c_int
    if rename(-100,os.fsencode(stage),-100,os.fsencode(target),1):
        number=ctypes.get_errno()
        if number in (errno.EEXIST,errno.ENOTEMPTY):raise EditorError('Import destination appeared during generation; it was preserved.')
        raise OSError(number,os.strerror(number),str(target))


def original_definitions(identity):
    # Original template/actor bytes remain in the exact combat cache. An empty
    # additions container avoids normalizing shells, damage, IDs or prices.
    return dict(format='btp-content-v1',schema_version=1,package_id=identity,content_version='1.0.0',
        rules=dict(id='chi:legacy-v1'),services=dict(
            broker=dict(id='chi:broker',behavior='chi-broker-v1'),
            reload=dict(id='chi:reload',behavior='chi-reload-v1')),
        ammunition=[],presentations=[],weapons=[],equipment=[],mechs=[])


def import_campaigns(source,output,edition='both',validator=None,cancel=None,progress=lambda _:None):
    from prepare_talk import extract as talk
    from prepare_combat import extract as combat
    from prepare_world import extract as world
    source=plain_path(source);target=plain_path(output)
    from app_runtime import binary
    validator=Path(validator or binary('btp-project')).resolve()
    if edition not in ('original','updated','both'):raise EditorError('Choose original, updated or both.')
    if not validator.is_file():raise EditorError('Build the application before importing CHI.')
    if target.exists():raise EditorError('Choose a new import destination; existing directories are preserved.')
    if target.is_relative_to(source) or target.is_relative_to(ROOT/'UnBattletech'):
        raise EditorError('Import destination must be outside the original/reference directories.')
    if not target.parent.is_dir():raise EditorError('Choose an existing parent folder for the new import destination.')
    snapshot=read_source(source,cancel,progress);check_cancel(cancel)
    progress('Extracting native text, combat and world data')
    caches={}
    for name,extract,args in [('talk-data.bin',talk,(snapshot['BTECH.EXE'],)),
                              ('combat-data.bin',combat,(snapshot['BTECH.EXE'],)),
                              ('world-data.bin',world,(snapshot['BTECH.EXE'],snapshot['MAP1.MTP']))]:
        check_cancel(cancel);caches[name]=extract(*args)[0]
    profiles=('original','updated') if edition=='both' else (edition,)
    token=uuid.uuid4().hex[:12];records=[]
    with tempfile.TemporaryDirectory(prefix='.chi-import-',dir=target.parent) as temporary:
        stage=Path(temporary)/'campaigns';stage.mkdir()
        extraction=Path(temporary)/'combat-data.bin';extraction.write_bytes(caches['combat-data.bin'])
        for profile in profiles:
            check_cancel(cancel);progress('Creating '+profile+' campaign')
            project=stage/profile;identity='chi-'+profile+'-'+token
            if profile=='updated':
                run([validator,'export',project,'--roster',ROOT/'content/updated/roster.json','--combat-data',extraction],cancel)
                manifest=json.loads((project/'project.json').read_bytes())
                content=json.loads((project/'content.json').read_bytes())
            else:
                project.mkdir();content=original_definitions(identity)
                manifest=dict(format='btp-project-v1',schema_version=1,assets=[])
            content.update(package_id=identity,content_version='1.0.0')
            manifest.update(package_id=identity,content_version='1.0.0',
                title='Editable CHI - '+profile.title(),requires='chi-local-dos-1.03',startup='chi-import-v1',
                save_policy='strict-content-v1',rules_profile=content['rules']['id'],definitions='content.json',
                campaign='campaign.json',resources=RESOURCE_PATHS)
            (project/'content.json').write_bytes(encoded(content));(project/'project.json').write_bytes(encoded(manifest))
            (project/'campaign.json').write_bytes(encoded(dict(format=FORMAT,schema_version=1,edition=profile,dialogue_overrides=[])))
            (project/'chi').mkdir()
            origins=[]
            for name in RUNTIME_FILES:
                check_cancel(cancel);data=caches[name] if name in caches else snapshot[name]
                (project/'chi'/name).write_bytes(data)
                origins.append(dict(file='chi/'+name,sha256=hashlib.sha256(data).hexdigest(),
                    origin='original-derived',source=[name] if name in snapshot else ['BTECH.EXE',*(['MAP1.MTP'] if name=='world-data.bin' else [])]))
            from chi_spatial import extract as spatial,FILE as spatial_file
            editable=spatial({'chi/'+n:caches[n] if n in caches else snapshot[n] for n in RUNTIME_FILES},profile)
            (project/spatial_file).write_bytes(encoded(editable));manifest['chi_spatial']=spatial_file
            from chi_bld import extract as bld_sources,FILE as bld_file
            (project/bld_file).write_bytes(encoded(bld_sources({'chi/'+n:snapshot[n] for n in RUNTIME_FILES if n.endswith('.BLD')})))
            manifest['chi_scripts']=bld_file
            (project/'project.json').write_bytes(encoded(manifest))
            provenance=dict(format='btp-chi-import-v1',schema_version=1,extractor='chi-import-v1',edition=profile,
                inputs=[dict(file=n,sha256=hashlib.sha256(snapshot[n]).hexdigest()) for n in SOURCE_FILES],
                resources=origins,capabilities=dict(editable=['native-dialogue-overrides','native-maps','world-generator','town-placements',
                    'entrances','NPC-routes','jigsaws','presentation-resources','labelled-BLD-source',*(['added-unit-definitions','broker-entrance'] if profile=='updated' else [])],
                    compatibility_only=['BLD','native-services','mission-settings'],
                    pending_milestones=['C4','C5']),
                distribution='Private original-derived content; use an asset-free reconstruction recipe for sharing.')
            (project/'IMPORT.json').write_bytes(encoded(provenance))
            (project/'.gitignore').write_text('# Private original-derived campaign. Share a recipe, not these files.\n*\n')
            (project/'README.md').write_text('Editable CHI - '+profile.title()+'\n\nPrivate local import from DOS 1.03. No original executable or personal saves copied.\n'
                'Open this folder in the Construction Kit or run the player with --project PATH.\n'
                'Text: Project > CHI campaign. Maps/world: Project > CHI maps and world. Art/audio: Project > CHI resources.\n'
                'BLD dialogue/control flow: Project > CHI scripts. Service rules, mission definitions and the new-event bridge remain C4.2 onwards.\n'
                'Keep this exact project for its saves. Reimport to a NEW folder; never overwrite edited projects.\n'
                'IMPORT.json records provenance and current editing limits. Original rights still apply to derived content.\n')
            progress('Validating '+profile+' campaign');check_cancel(cancel)
            run([validator,'validate',project],cancel)
            records.append(dict(edition=profile,package_id=identity,path=str(target/profile)))
        # Re-read every supported input so changes during extraction cannot
        # publish a project with misleading provenance or mixed source data.
        progress('Rechecking original files before publication');read_source(source,cancel)
        check_cancel(cancel);plain_path(target);plain_path(target.parent)
        (stage/'IMPORT.json').write_bytes(encoded(dict(format='btp-chi-import-set-v1',projects=records)))
        (stage/'.gitignore').write_text('*\n')
        publish(stage,target)
    progress('Import complete')
    return dict(output=str(target),projects=records)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--edition',choices=('original','updated','both'),default='both')
    parser.add_argument('--validator',type=Path)
    args=parser.parse_args()
    try:result=import_campaigns(args.data,args.output,args.edition,args.validator)
    except (EditorError,OSError,ValueError) as error:parser.exit(1,str(error)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
