"""Run Linux delivery checks with the kit's interpreter, modules and binaries.

The caller supplies a private X display. Proofs stay outside the distribution;
the kit receives no copied DOS installation, development caches or user saves.
"""
from pathlib import Path
import hashlib,json,os,subprocess,tempfile
from chi_import import ROOT,output_path
from editor_model import EditorError,encoded


def environment(kit,base):
    kit=Path(kit)
    env=dict(base,PYTHONHOME=str(kit/'runtime'),PYTHONPATH='',PYTHONNOUSERSITE='1',SDL_AUDIODRIVER='dummy',
        PYTHONDONTWRITEBYTECODE='1',BTP_BUNDLED_RUNTIME='1',
        TCL_LIBRARY=str(kit/'runtime/lib/tcl8.6'),TK_LIBRARY=str(kit/'runtime/lib/tk8.6'),
        LD_LIBRARY_PATH=str(kit/'runtime/lib')+(':'+base['LD_LIBRARY_PATH'] if base.get('LD_LIBRARY_PATH') else ''))
    return env


def run(kit,base,source=None,output=None):
    kit=Path(kit).resolve();source=Path(source).resolve() if source else None
    protected=[kit,*([source] if source else [])]
    if output:
        output=output_path(output,*protected)
        if output.exists():raise EditorError('Delivery evidence needs a new directory; earlier proofs are preserved.')
        output.mkdir(parents=True)
    else:
        (ROOT/'work').mkdir(exist_ok=True)
        output=Path(tempfile.mkdtemp(prefix='packaged-proof-',dir=ROOT/'work'))
    report=dict(status='running',kit=str(kit),desktop='Linux Tk',steps=[],
        distribution_sha256=hashlib.sha256((kit/'DISTRIBUTION.json').read_bytes()).hexdigest(),
        windows_native_Tk='UNKNOWN')
    evidence=output/'evidence.json';evidence.write_bytes(encoded(report))
    env=environment(kit,base);python=str(kit/'runtime/bin/python3')
    # Import paths in the child refer only to the delivered tools. CWD is an
    # external proof directory, so checkout-relative resource fallbacks fail.
    def invoke(name,command,timeout=180):
        with (output/(name+'.log')).open('w',encoding='utf-8') as log:
            result=subprocess.run(command,cwd=output,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=timeout)
        report['steps'].append(dict(name=name,exit_code=result.returncode))
        evidence.write_bytes(encoded(report))
        if result.returncode:raise EditorError('Packaged '+name+' failed; see '+str(output/(name+'.log')))
        print('PASS packaged '+name,flush=True)
    try:
        invoke('runtime-and-authoring',[str(kit/'ConstructionKit'),'--check-runtime'])
        if source:
            invoke('chi-import-and-reconstruction',[python,'-B',str(kit/'tools/chi_delivery_probe.py'),
                '--data',str(source),'--output',str(output/'campaigns')])
            script="import os,sys;from pathlib import Path;sys.path.insert(0,sys.argv[1]);from editor_chi_import_smoke import run;run(os.environ,Path(sys.argv[2]),source=Path(sys.argv[3]))"
            invoke('chi-editor',[python,'-B','-c',script,str(kit/'tools'),str(output),str(source)])
        script="import os,sys;from pathlib import Path;sys.path.insert(0,sys.argv[1]);from saved_games_smoke import run;run(os.environ,Path(sys.argv[2]))"
        invoke('saved-games',[python,'-B','-c',script,str(kit/'tools'),str(output)])
        report['artifacts']=[]
        for name in (['campaigns/evidence.json','chi-import-gui.json'] if source else [])+['saved-games-gui.json']:
            payload=(output/name).read_bytes()
            if json.loads(payload).get('status')!='passed':raise EditorError('Packaged proof did not pass: '+name)
            report['artifacts'].append(dict(file=name,sha256=hashlib.sha256(payload).hexdigest()))
        report['status']='passed';evidence.write_bytes(encoded(report))
    except (OSError,ValueError,EditorError,subprocess.SubprocessError) as error:
        report.update(status='failed',error=str(error));evidence.write_bytes(encoded(report));raise
    print('Packaged evidence: '+str(output),flush=True)
    return report
