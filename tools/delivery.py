"""Build inspectable Construction Kit distributions from local dependencies.

No downloads and no original resources, caches or user saves are copied. Linux
bundles Python/Tk/Pillow/SDL; Windows accepts an optional installed Python tree.
"""
import hashlib,json,os,re,shutil,subprocess,sys,sysconfig,tempfile
from pathlib import Path
from editor_model import EditorError,ProjectDocument,references
ROOT=Path(__file__).resolve().parents[1]

def asset_report(doc):
    def original_source(value):
        # Generated construction joins retain the provenance of both faces.
        return isinstance(value,dict) and (value.get('sheet','').startswith('chi:') or any(original_source(v) for v in value.get('sources',[])))
    sources=json.loads(doc.metadata.get('EDITOR.json',b'{}')).get('tile_sources',{})
    files=doc.files()  # Newly authored graphics may not have a disk snapshot yet.
    return dict(package=doc.manifest['package_id'],requires=doc.manifest['requires'],
        files=[dict(path=n,bytes=len(files[n]),sha256=hashlib.sha256(files[n]).hexdigest()) for n in references(doc.manifest)],
        images=[dict(id=i['id'],name=i['name'],kind=i['kind'],frames=len(i['frames']),
                     origin='Copy of original artwork; original rights still apply' if i['name'].startswith('Original sprite') or original_source(sources.get(i['id'])) else 'Package pixels; consult source documents',
                     source=sources.get(i['id'])) for i in doc.art['images']],
        source_documents=[p.name for p in doc.root.iterdir() if p.is_file() and (p.suffix.lower()=='.md' or 'SOURCE' in p.name)],
        note='Dependency/provenance inventory, not a license clearance. Original game assets must be supplied separately.')

def copy_file(source,target,inventory):
    source,target=Path(source),Path(target);target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source,target);inventory.append(dict(path=str(target),source=str(source.resolve())))

def copy_tree(source,target,inventory):
    source=Path(source)
    for p in sorted(source.rglob('*')):
        if p.is_file() and not any(v in ('__pycache__','site-packages','dist-packages','test','tests','idlelib','ensurepip') for v in p.relative_to(source).parts):
            copy_file(p,Path(target)/p.relative_to(source),inventory)

def write_launchers(stage,platform):
    """Console authoring preserves caller-relative paths, stdout and exit codes.

    Both launchers locate the kit beside themselves. The CLI must not change
    directory like a desktop shortcut: --file and output paths belong to the
    invoking person/agent, and JSON errors must reach its caller unchanged.
    """
    stage=Path(stage)
    if platform=='linux':
        environment='#!/bin/sh\nKIT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\n'
        environment+='export PYTHONHOME="$KIT_ROOT/runtime"\nexport PYTHONPATH=\nexport PYTHONNOUSERSITE=1\n'
        environment+='export TCL_LIBRARY="$KIT_ROOT/runtime/lib/tcl8.6"\nexport TK_LIBRARY="$KIT_ROOT/runtime/lib/tk8.6"\n'
        environment+='export LD_LIBRARY_PATH="$KIT_ROOT/runtime/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"\nexport BTP_BUNDLED_RUNTIME=1\n'
        for name,script in [('ConstructionKit','BtechPort.pyw'),('Author','tools/author.py')]:
            (stage/name).write_text(environment+'exec "$KIT_ROOT/runtime/bin/python3" "$KIT_ROOT/'+script+'" "$@"\n')
            (stage/name).chmod(0o755)
    else:
        (stage/'ConstructionKit.cmd').write_bytes(('@echo off\r\nsetlocal\r\nif exist "%~dp0runtime\\pythonw.exe" (\r\n'
            ' start "" "%~dp0runtime\\pythonw.exe" -E -s "%~dp0BtechPort.pyw" %*\r\n) else (\r\n'
            ' py -3 -E -s "%~dp0BtechPort.pyw" %*\r\n)\r\n').encode('ascii'))
        (stage/'Author.cmd').write_bytes(('@echo off\r\nsetlocal\r\nif exist "%~dp0runtime\\python.exe" (\r\n'
            ' "%~dp0runtime\\python.exe" -E -s "%~dp0tools\\author.py" %*\r\n) else (\r\n'
            ' py -3 -E -s "%~dp0tools\\author.py" %*\r\n)\r\nexit /b %errorlevel%\r\n').encode('ascii'))

def linux_runtime(stage,inventory):
    python=Path('/usr/bin/python3').resolve()
    probe=subprocess.run([str(python),'-c','import sys,sysconfig;print(sysconfig.get_path("stdlib"));print("%d.%d"%sys.version_info[:2])'],capture_output=True,text=True,check=True)
    stdlib,version=probe.stdout.strip().splitlines();lib=stage/'runtime/lib';dest=lib/f'python{version}'
    copy_file(python,stage/'runtime/bin/python3',inventory);copy_tree(stdlib,dest,inventory)
    # This development host has a local distribution Tk extraction. Prefer
    # its antialiased Tk over Conda's older X core font build.
    local=ROOT/'local-deps/editor-tk/root/usr/lib'/f'python{version}'
    if local.exists():copy_tree(local,dest,inventory)
    pillow=Path('/usr/lib/python3/dist-packages/PIL')
    if not pillow.is_dir():raise EditorError('Linux bundling needs distribution Python and Pillow installed locally.')
    copy_tree(pillow,dest/'PIL',inventory)
    if not (dest/'tkinter').is_dir():raise EditorError('Linux bundling needs a local Tkinter installation matching system Python.')
    for name in ('tcl8.6','tk8.6'):
        source=Path('/usr/share/tcltk')/name
        if not source.is_dir():source=Path('/usr/lib')/name
        copy_tree(source,lib/name,inventory)
    # ldd is used only on binaries built here or installed local interpreter
    # modules. The host loader/glibc remain an explicit platform requirement.
    skip=re.compile(r'^(ld-linux|lib(c|m|dl|rt|pthread|resolv|nss_[^.]+)\.so)')
    inputs=[stage/'runtime/bin/python3',*sorted(dest.rglob('*.so')),stage/'build/btech-port',stage/'build/btp-project']
    dependencies={}
    for binary in inputs:
        result=subprocess.run(['ldd',str(binary)],capture_output=True,text=True,timeout=10)
        for line in result.stdout.splitlines():
            if 'not found' in line:raise EditorError(f'Missing library for {binary.name}: {line.strip()}')
            match=re.search(r'=> (/\S+)',line)
            if match:
                path=Path(match[1]);name=line.split()[0]
                if not skip.match(name):dependencies[name]=path
    for name,path in dependencies.items():copy_file(path,lib/name,inventory)
    # Retain installed copyright notices for every packaged distribution
    # dependency, including transitive libraries, not just the headline tools.
    packages={'python'+version,'python3-pil','python3-tk','tk8.6','tcl8.6','libsdl2-2.0-0'}
    for path in dependencies.values():
        result=subprocess.run(['dpkg-query','-S',str(path.resolve())],capture_output=True,text=True)
        if result.returncode==0:
            for line in result.stdout.splitlines():packages.add(line.split(': ')[0].split(':')[0])
    for name in packages:
        notice=Path('/usr/share/doc')/name/'copyright'
        if not notice.exists():notice=ROOT/'local-deps/editor-tk/root/usr/share/doc'/name/'copyright'
        if notice.exists():copy_file(notice,stage/'licenses'/f'{name}.txt',inventory)
    write_launchers(stage,'linux')
    libc=subprocess.run(['getconf','GNU_LIBC_VERSION'],capture_output=True,text=True,check=True).stdout.strip()
    return ['Linux x86_64 with '+libc+' or newer, an X11 display and system fonts.',
            'Python '+version+', Tk 8.6, Pillow, SDL and transitive non-glibc libraries are bundled.']

def package(output,platform='linux',python_runtime=None):
    output=Path(output).resolve()
    if output.exists():raise EditorError('Distribution output must be a new directory.')
    output.parent.mkdir(parents=True,exist_ok=True);inventory=[]
    with tempfile.TemporaryDirectory(prefix='kit-package-',dir=output.parent) as tmp:
        stage=Path(tmp)/'kit';stage.mkdir()
        # Only version-controlled authoring resources enter the kit. Never
        # recursively copy the checkout or follow untracked caches/saves.
        tracked=subprocess.run(['git','ls-files','-z'],cwd=ROOT,capture_output=True,check=True).stdout.decode().split('\0')
        for name in tracked:
            if not name:continue
            p=Path(name)
            if (p.parts[0] in ('tools','docs','content','examples','port','third_party','tests','cmake','schemas') and p.suffix in ('.py','.md','.json','.anm','.txt','.lua','.c','.h','.actions','.cmake')) or name in ('BtechPort.pyw','BtechPort.cmd','LICENSE','README.md','CMakeLists.txt','third_party/lua/COPYRIGHT','third_party/lua/LICENSE'):
                copy_file(ROOT/p,stage/p,inventory)
        # Also include new delivery tools before their first incremental commit.
        for name in ('delivery.py','save_migration.py','delivery_gui.py','runtime_probe.py'):
            if (ROOT/'tools'/name).exists():copy_file(ROOT/'tools'/name,stage/'tools'/name,inventory)
        folder=ROOT/('build-windows' if platform=='windows' else 'build');suffix='.exe' if platform=='windows' else ''
        for name in ('btech-port','btech-headless','btp-project','btp-author-playtest','btp-author-analyze'):copy_file(folder/(name+suffix),stage/'build'/(name+suffix),inventory)
        if platform=='linux':requirements=linux_runtime(stage,inventory)
        else:
            for dll in folder.glob('*.dll'):copy_file(dll,stage/'build'/dll.name,inventory)
            for notice in (ROOT/'local-deps/windows').glob('SDL2-*/LICENSE.txt'):
                copy_file(notice,stage/'licenses'/(notice.parent.name+'.txt'),inventory)
            for name in ('gcc-mingw-w64-base','mingw-w64-common','mingw-w64-x86-64-dev','libz-mingw-w64'):
                notice=ROOT/'local-deps/windows/root/usr/share/doc'/name/'copyright'
                if notice.exists():copy_file(notice,stage/'licenses'/(name+'.txt'),inventory)
            if python_runtime:
                runtime=Path(python_runtime)
                if not all((runtime/name).is_file() for name in ('python.exe','pythonw.exe')) or not all((runtime/name).is_dir() for name in ('Lib/tkinter','Lib/site-packages/PIL')):
                    raise EditorError('Windows Python runtime must include python.exe, pythonw.exe, Lib/tkinter and Lib/site-packages/PIL.')
                # The supplied full installation (including Pillow and its
                # license) is explicit input; embeddable Python has no Tk.
                shutil.copytree(runtime,stage/'runtime')
            write_launchers(stage,'windows')
            requirements=['Windows 10/11 x64; SDL DLLs are bundled.',
                          'Bundled full Python installation supplied by the packager.' if python_runtime else 'Install Python 3.10+ with Tk; install Pillow for image import/export. No Python runtime was supplied.',
                          'Cross-build/Wine checks do not establish native Windows GUI verification.']
        reports=[]
        for manifest in sorted((stage/'examples').glob('*/project.json')):
            doc=ProjectDocument(manifest.parent,ROOT/'build/btp-project');reports.append(asset_report(doc))
        (stage/'ASSETS.json').write_text(json.dumps(reports,indent=2)+'\n')
        cli='Author' if platform=='linux' else 'Author.cmd'
        (stage/'START-HERE.txt').write_text('BattleTech Construction Kit\n\nRun '+('ConstructionKit' if platform=='linux' else 'ConstructionKit.cmd')+' to open the launcher.\n\n'+'\n'.join(requirements)+'\n\nOriginal CHI assets are not included. Beacon demo and Vehicle lab run independently.\nSource and build instructions: README.md; licenses: LICENSE and licenses/.\n\n'
            +'Offline authoring CLI: '+cli+' capabilities\n'+cli+' recipe list\n'
            +'Recipes and one-command generate/check/play: docs/CAMPAIGN_RECIPES.md\n'
            +'External AI applications use the same JSON CLI or explicitly opened local editor session. No account, model or network is required.\n')
        report=dict(platform=platform,requirements=requirements,files=[])
        origins={str(Path(v['path']).relative_to(stage)):v['source'] for v in inventory}
        for path in sorted(stage.rglob('*')):
            if path.is_file():report['files'].append(dict(path=str(path.relative_to(stage)),bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),source=origins.get(str(path.relative_to(stage)),'Generated or supplied runtime')))
        (stage/'DISTRIBUTION.json').write_text(json.dumps(report,indent=2)+'\n');stage.rename(output)
    return report

def archive(output,platform):
    """Archive only inventoried deliverables, excluding later caches/saves."""
    import tarfile,zipfile
    output=Path(output);report=json.loads((output/'DISTRIBUTION.json').read_bytes())
    names=[v['path'] for v in report['files']]+['DISTRIBUTION.json']
    target=output.with_name(output.name+('.zip' if platform=='windows' else '.tar.gz'))
    if platform=='windows':
        with zipfile.ZipFile(target,'x',compression=zipfile.ZIP_DEFLATED) as bundle:
            for name in names:bundle.write(output/name,str(Path(output.name)/name))
    else:
        with tarfile.open(target,'x:gz') as bundle:
            for name in names:bundle.add(output/name,arcname=str(Path(output.name)/name),recursive=False)
    return target

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path);p.add_argument('--platform',choices=('linux','windows'),default='linux');p.add_argument('--python-runtime',type=Path);p.add_argument('--archive',action='store_true')
    args=p.parse_args()
    try:
        result=package(args.output,args.platform,args.python_runtime);print(f"Created {args.output}: {len(result['files'])} files");print('\n'.join(result['requirements']))
        if args.archive:print('Archive: '+str(archive(args.output,args.platform)))
    except (OSError,EditorError,subprocess.SubprocessError) as exc:p.exit(1,str(exc)+'\n')
