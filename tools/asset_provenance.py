#!/usr/bin/env python3
"""Guard original-derived payloads and reconstruct declared tiles locally."""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from editor_model import EditorError,ProjectDocument,encoded

ROOT=Path(__file__).resolve().parents[1]
RECIPE='CHI-TILES.json'


def digest(value):return hashlib.sha256(encoded(value)).hexdigest()


def original_source(value):
    return isinstance(value,dict) and (str(value.get('sheet','')).startswith('chi:') or
        any(original_source(v) for v in value.get('sources',[])))


def derived_images(files):
    manifest=json.loads(files['project.json']);graphics=manifest.get('graphics')
    if not graphics:return []
    images=json.loads(files[graphics])['images']
    sources=json.loads(files.get('EDITOR.json',b'{}')).get('tile_sources',{})
    recipe=json.loads(files.get(RECIPE,b'{}'))
    placeholders={v['id']:v['placeholder_sha256'] for v in recipe.get('tiles',[])}
    return [image for image in images if
        (original_source(sources.get(image['id'])) or image['name'].startswith('Original sprite') or
         image.get('origin') in ('original-derived','unknown')) and
        digest(image['frames'])!=placeholders.get(image['id'])]


def declared_payload(value):
    if isinstance(value,dict):
        if value.get('origin') in ('original-derived','unknown'):return True
        return any(declared_payload(v) for v in value.values())
    return isinstance(value,list) and any(declared_payload(v) for v in value)


def check_files(files):
    """Fail closed for imported campaigns and recognized/declared origins.

    This is not a detector for arbitrary artwork with stripped provenance.
    Origin records must travel with editor/library operations.
    """
    manifest=json.loads(files['project.json'])
    if manifest.get('requires')=='chi-local-dos-1.03':
        raise EditorError('Private imported CHI campaigns contain original-derived resources; export an asset-free recipe instead.')
    unknown=[n for n,data in files.items() if data[:4] in (b'BTTA',b'BTCC',b'BTW3')]
    if unknown:raise EditorError('Original-derived cache cannot be distributed: '+', '.join(unknown))
    for name,data in files.items():
        if name.endswith('.json') and declared_payload(json.loads(data)):
            raise EditorError('Declared original-derived or unknown payload cannot be distributed: '+name)
    images=derived_images(files)
    if images:raise EditorError('Original-derived or unknown artwork requires local reconstruction: '+', '.join(v['id'] for v in images))
    return True


def tile_frame(atlas,index):
    return [''.join(color.lstrip('#')+'ff' for color in row) for row in atlas[index]]


def placeholder():
    # Independently drawn checkerboard. Recipe reconstruction replaces only
    # this exact placeholder, never artwork the user subsequently changes.
    return [[''.join('593b70ff' if (x//4+y//4)%2 else 'b08e52ff' for x in range(16)) for y in range(16)]]


def sanitize_tiles(files,validator,data,allow_base_substitution=False):
    from editor_tiles import load_original_atlas
    files=dict(files);manifest=json.loads(files['project.json'])
    if manifest.get('requires')=='chi-local-dos-1.03':raise EditorError('Imported campaign export must exclude original content.')
    graphics=manifest.get('graphics');images=derived_images(files);recipe=json.loads(files.get(RECIPE,b'{"format":"btp-chi-tile-recipe-v1","tiles":[]}'))
    if not images:check_files(files);return files
    art=json.loads(files[graphics]);by_id={v['id']:v for v in art['images']}
    sources=json.loads(files.get('EDITOR.json',b'{}')).get('tile_sources',{});atlases={}
    for image in images:
        source=sources.get(image['id'],{})
        if set(source)!={'sheet','graphic'} or not str(source.get('sheet','')).startswith('chi:') or image['kind']!='tile' or image['width']!=16 or image['height']!=16:
            raise EditorError('No lossless asset-free reconstruction for '+image['id']+'; retain it privately.')
        sheet=source['sheet']
        if sheet not in atlases:atlases[sheet]=load_original_atlas(validator,data,sheet)
        base=[tile_frame(atlases[sheet],source['graphic'])]
        modified=image['frames']!=base
        if modified and not allow_base_substitution:
            raise EditorError('Original-derived tile has custom edits and cannot be reduced to a source recipe: '+image['id'])
        record=dict(id=image['id'],sheet=source['sheet'],graphic=source['graphic'],
            original_sha256=digest(base),placeholder_sha256=digest(placeholder()),
            reconstruction='original-base' if modified else 'exact')
        if modified:record['private_derivative_sha256']=digest(image['frames'])
        old=next((v for v in recipe['tiles'] if v['id']==image['id']),None)
        if old and old!=record:raise EditorError('Conflicting reconstruction recipe: '+image['id'])
        if not old:recipe['tiles'].append(record)
        by_id[image['id']]['frames']=placeholder()
    files[graphics]=encoded(art);files[RECIPE]=encoded(recipe);check_files(files);return files


def public_files(files):
    """Exclude recognized private tile variants with an existing base recipe.

    The original base can be reconstructed; private pixel edits remain local.
    Never pretend the recipe reproduces those edits or include their pixels.
    """
    files=dict(files);recipe=json.loads(files.get(RECIPE,b'{}'))
    records={v['id']:v for v in recipe.get('tiles',[])}
    images=derived_images(files)
    if images:
        manifest=json.loads(files['project.json']);art=json.loads(files[manifest['graphics']])
        ids={v['id'] for v in images}
        for image in art['images']:
            if image['id'] not in ids:continue
            record=records.get(image['id'])
            if not record or record['placeholder_sha256']!=digest(placeholder()):
                raise EditorError('No declared public placeholder for private artwork: '+image['id'])
            image['frames']=placeholder()
        files[manifest['graphics']]=encoded(art)
    check_files(files);return files


def reconstructed_document(document,data):
    from editor_tiles import load_original_atlas
    files=document.files();recipe=json.loads(files.get(RECIPE,b'{}'))
    if recipe.get('format')!='btp-chi-tile-recipe-v1':raise EditorError('No supported tile reconstruction recipe in this project.')
    art=copy.deepcopy(document.art);by_id={v['id']:v for v in art['images']};atlases={}
    for tile in recipe['tiles']:
        image=by_id.get(tile['id'])
        if image is None:raise EditorError('Recipe references a missing image: '+tile['id'])
        current=digest(image['frames'])
        if current==tile['original_sha256']:continue
        if current!=tile['placeholder_sha256']:
            raise EditorError('Recipe would replace an edited tile; preserve that project privately: '+tile['id'])
        sheet=tile['sheet']
        if sheet not in atlases:atlases[sheet]=load_original_atlas(document.validator,Path(data),sheet)
        frames=[tile_frame(atlases[sheet],tile['graphic'])]
        if digest(frames)!=tile['original_sha256']:raise EditorError('Original tile fingerprint disagrees with recipe: '+tile['id'])
        image['frames']=frames
    candidate=document.worker_copy();candidate.replace_art(art);return candidate


def reconstruct(document,output,data):
    output=Path(output)
    if output.exists():raise EditorError('Reconstruction needs a new output folder; user projects are preserved.')
    candidate=reconstructed_document(document,data);candidate.export(output)
    return output


def local_project(document,settings,state_dir):
    """Resolve distributed placeholders into a private, content-pinned copy."""
    from editor_model import references
    if RECIPE not in document.metadata:return document
    recipe=json.loads(document.metadata[RECIPE]);by_id={v['id']:v for v in document.art['images']}
    if not any(digest(by_id[v['id']]['frames'])==v['placeholder_sha256'] for v in recipe['tiles'] if v['id'] in by_id):return document
    candidate=reconstructed_document(document,settings.get('data',''))
    files=candidate.files();identity=hashlib.sha256(b''.join(files[n] for n in references(candidate.manifest))).hexdigest()
    target=Path(state_dir)/'local-resources'/identity/'game'
    if target.exists():
        existing=ProjectDocument(target,document.validator)
        if any(existing.snapshot.get(n)!=files[n] for n in references(candidate.manifest)):
            raise EditorError('A private reconstructed project was edited. Preserve it separately before reusing this launcher cache.')
        return existing
    candidate.export(target);return ProjectDocument(target,document.validator)


def export_public(document,output):
    files=public_files(document.files());candidate=document.worker_copy()
    if candidate.manifest.get('graphics'):
        candidate.replace_art(json.loads(files[candidate.manifest['graphics']]))
    candidate.export(Path(output));return Path(output)


def stage_baseline(data,validator):
    """Remove known public payloads without changing the dirty working files.

    Only the HEAD graphics baseline is staged. Never stage the owner's pending
    graphics/editor/map edits. A retained local backup makes the action reviewable.
    """
    root=ROOT/'examples/battletech-demo';names=('project.json','graphics.json','EDITOR.json')
    staged=subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).splitlines()
    if any(n.startswith('examples/battletech-demo/') for n in staged):raise EditorError('Last Beacon already has staged work; preserve it before baseline cleanup.')
    before={p:p.read_bytes() for p in (root/'graphics.json',root/'EDITOR.json',root/'adventure.json')}
    files={name:subprocess.check_output(['git','show','HEAD:examples/battletech-demo/'+name],cwd=ROOT) for name in names}
    clean=sanitize_tiles(files,validator,Path(data),allow_base_substitution=True);backup=ROOT/'work/chi-import/asset-cleanup';backup.mkdir(parents=True,exist_ok=True)
    (backup/'graphics-before.json').write_bytes(files['graphics.json']);(backup/'graphics-public.json').write_bytes(clean['graphics.json'])
    target=root/RECIPE
    if target.exists() and target.read_bytes()!=clean[RECIPE]:raise EditorError('An existing reconstruction recipe differs; it was preserved.')
    target.write_bytes(clean[RECIPE])
    sha=subprocess.check_output(['git','hash-object','-w','--stdin'],input=clean['graphics.json'],cwd=ROOT).decode().strip()
    subprocess.run(['git','update-index','--cacheinfo','100644,'+sha+',examples/battletech-demo/graphics.json'],cwd=ROOT,check=True)
    assert all(p.read_bytes()==value for p,value in before.items()),'Working files changed during baseline cleanup'
    print('Staged asset-free HEAD graphics and wrote reconstruction recipe. Three owner working files unchanged.')


def check_staged():
    from release_guard import staged
    staged()
    names=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
    inventory=json.loads((ROOT/'docs/chi-import-inventory.json').read_bytes())
    raw_hashes={v['sha256'] for v in inventory['files']}
    groups={};changed=set(subprocess.check_output(['git','diff','--cached','--name-only','-z'],cwd=ROOT).decode().split('\0'))
    for name in names:
        if not name:continue
        # Only inspect candidate blobs, never unrelated dirty working copies.
        if name in changed:
            value=subprocess.check_output(['git','show',':'+name],cwd=ROOT)
            if hashlib.sha256(value).hexdigest() in raw_hashes or value[:4] in (b'BTTA',b'BTCC',b'BTW3'):
                raise EditorError('Original-derived binary staged: '+name)
            if name.endswith('.json') and declared_payload(json.loads(value)):
                raise EditorError('Declared original-derived/unknown payload staged: '+name)
        if name.endswith('/project.json'):
            prefix=name[:-len('project.json')]
            project={}
            manifest=json.loads(subprocess.check_output(['git','show',':'+name],cwd=ROOT))
            for leaf in ('project.json',manifest.get('graphics','graphics.json'),'EDITOR.json',RECIPE):
                full=prefix+leaf
                if full in names:project[leaf]=subprocess.check_output(['git','show',':'+full],cwd=ROOT)
            check_files(project);groups[prefix]=True
    print('Provenance check passed for staged binaries and '+str(len(groups))+' tracked project manifests.')


def main():
    from app_runtime import binary
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='action',required=True)
    sub.add_parser('check-staged')
    stage=sub.add_parser('stage-baseline');stage.add_argument('--data',type=Path,required=True)
    restore=sub.add_parser('reconstruct');restore.add_argument('--project',type=Path,required=True);restore.add_argument('--output',type=Path,required=True);restore.add_argument('--data',type=Path,required=True)
    public=sub.add_parser('public-export');public.add_argument('--project',type=Path,required=True);public.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    try:
        if args.action=='check-staged':check_staged()
        elif args.action=='stage-baseline':stage_baseline(args.data,binary('btp-project'))
        elif args.action=='public-export':print(export_public(ProjectDocument(args.project,binary('btp-project')),args.output))
        else:print(reconstruct(ProjectDocument(args.project,binary('btp-project')),args.output,args.data))
    except (EditorError,OSError,ValueError) as error:parser.exit(1,str(error)+'\n')


if __name__=='__main__':main()
