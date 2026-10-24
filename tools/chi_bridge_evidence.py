"""Build private bridge acceptance fixtures; distribute recipes, never DOS data."""
from pathlib import Path
import copy
import json
import shutil
import subprocess
import sys
import hashlib
import tempfile
from editor_model import ProjectDocument,encoded
from chi_bridge import enable,example,events,put
from chi_bld import data,find,put as put_bld

def nested(document):
    a=events(document)
    def node(name,op,**fields):return dict(id='test:'+name,op=op,**fields)
    def call(name,event,next='test:reward'):
        return node(name,'call',event='test:'+event,next=next,failure='test:fail',cancel='test:cancel')
    a['events'] += [
        node('menu','choice',text='Bridge acceptance paths',options=[dict(label='Bank',next='test:bank'),dict(label='Nested',next='test:one'),dict(label='Depth limit',next='test:deep-one'),dict(label='Cycle limit',next='test:cycle'),dict(label='Tight loop',next='test:spin')],cancel='test:cancel'),
        node('bank','chi_native',call='bridge:bank',next='test:reward',failure='test:fail',cancel='test:cancel'),
        node('reward','reward',credits=100,next='test:done',failure='test:fail'),node('done','return',result='success'),
        node('fail','return',result='failure'),node('cancel','return',result='cancel'),
        call('one','two'),call('two','three','test:done'),call('three','deep-text','test:done'),
        node('deep-text','say',text='Four frames are held. Return without restarting the native building.',next='test:done'),
        call('deep-one','deep-two'),call('deep-two','deep-three','test:done'),
        call('deep-three','deep-four','test:done'),dict(call('deep-four','deep-five','test:done'),failure='test:limit-text'),
        node('deep-five','say',text='Unreachable fifth frame',next='test:done'),
        node('limit-text','say',text='Excess depth was rejected.',next='test:fail'),
        dict(call('cycle','cycle'),failure='test:cycle-text'),node('cycle-text','say',text='Recursive call was rejected.',next='test:fail'),
        call('spin','done','test:spin')]
    with document.command('Prepare mixed continuation fixture'):
        put(document,quest=a)
        scripts=data(document);p=find(scripts,'chi:bld-armor')
        added=[dict(id='test:entry-count',op='add',index=80,value=1),dict(id='test:quest-call',op='event',event='test:menu',next='test:ok-label',failure='test:fail-label',cancel='test:cancel-label')]
        p['nodes'][1:1]=added
        # Append only original-free test instructions, leaving all imported
        # labels/payload ranges and normal menu behavior intact.
        for outcome,value in [('ok',1),('fail',2),('cancel',3)]:
            p['nodes'] += [dict(id='test:'+outcome+'-label',op='set',index=81,value=value)]
            if outcome=='ok':p['nodes'].append(dict(id='test:fault-check',op='if',index=82,target='test:clear'))
            p['nodes'].append(dict(id='test:'+outcome+'-back',op='jump',target='chi:armor-0002'))
        p['nodes'].append(dict(id='test:clear',op='clear'))
        p['nodes'] += [dict(id='test:text-'+str(i),op='text',text='Fault checkpoint test.') for i in range(9)]
        p['nodes'].append(dict(id='test:text-end',op='end'))
        put_bld(document,scripts)

def prepare(source,output,tool):
    source,output=Path(source),Path(output)
    if output.exists():raise ValueError('Use a new evidence output directory: '+str(output))
    output.mkdir(parents=True)
    for edition in ('original','updated'):
        destination=output/edition;shutil.copytree(source/edition,destination)
        d=ProjectDocument(destination,tool);example(d);d.save()
        dest=output/(edition+'-nested');shutil.copytree(destination,dest)
        d=ProjectDocument(dest,tool);nested(d);d.save()
    return output

HELD_LABELS={
    '':('dialogue','choice','company','amount','receipt','service-return','outside','no-cash',
        'sound','film','battle','reward','finished','repeat','retreat','defeat','defeat-return'),
    '-nested':('bld-choice','bld-company','bld-amount','bld-receipt','bld-menu','four-frames',
        'nested-return','depth-rejected','cycle-rejected','budget-fault','bld-cancel','fault-after-reward')}


def artifacts(suffix):
    """The declared 58 holds must each produce a save, frame and next state."""
    return [label+extension for label in HELD_LABELS[suffix] for extension in ('.btp','.ppm','-suffix.bin')]


def verify(output,windows=False):
    root=Path(__file__).resolve().parents[1];output=Path(output);platform='windows' if windows else 'linux'
    report=dict(status='running',platform=platform,journeys=[],comparisons=[],artifacts=[])
    report_file=output/(platform+'-evidence.json');report_file.write_bytes(encoded(report))
    targets=[(edition+suffix,suffix) for edition in ('original','updated') for suffix in ('','-nested')]
    try:
        if windows:
            baseline=output/'linux-evidence.json'
            if not baseline.exists():raise RuntimeError('Complete Linux bridge acceptance first.')
            prior=json.loads(baseline.read_bytes())
            if prior.get('status')!='passed' or [(r.get('project'),r.get('exit_code')) for r in prior.get('journeys',[])]!=[(target,0) for target,_ in targets]:
                raise RuntimeError('Complete all Linux bridge journeys first.')
            # Never accept an empty/partial glob as a cross-platform proof.
            for target,suffix in targets:
                for name in artifacts(suffix):
                    path=output/('linux-'+target+'-'+name)
                    if not path.is_file():raise RuntimeError('Missing Linux bridge artifact: '+str(path))
            for record in prior.get('artifacts',[]):
                path=output/record['file']
                if hashlib.sha256(path.read_bytes()).hexdigest()!=record['sha256']:
                    raise RuntimeError('Linux bridge artifact changed: '+str(path))
        for target,suffix in targets:
            # A fresh staging directory prevents old output from hiding a
            # missing artifact in a later successful-but-incomplete test run.
            with tempfile.TemporaryDirectory(prefix='bridge-'+platform+'-',dir=output) as temporary:
                prefix=Path(temporary)/'held'
                executable=root/('build-windows/btp-chi-bridge-tests.exe' if windows else 'build/btp-chi-bridge-tests')
                command=([sys.executable,str(root/'tools/windows_check.py')] if windows else [])+[str(executable),str(output/target),str(prefix)]
                if suffix:command.append('nested')
                result=subprocess.run(command,capture_output=True,text=True,timeout=120)
                report['journeys'].append(dict(project=target,exit_code=result.returncode,stdout=result.stdout,stderr=result.stderr))
                if result.returncode:raise RuntimeError(result.stdout+result.stderr)
                for name in artifacts(suffix):
                    candidate=Path(str(prefix)+'-'+name)
                    if not candidate.is_file():raise RuntimeError('Missing generated bridge artifact: '+name)
                    payload=candidate.read_bytes();digest=hashlib.sha256(payload).hexdigest()
                    if windows:
                        original=output/('linux-'+target+'-'+name)
                        if original.read_bytes()!=payload:raise RuntimeError('Platform continuation differs: '+str(original))
                        report['comparisons'].append(dict(file=original.name,bytes=len(payload),sha256=digest))
                    destination=output/(platform+'-'+target+'-'+name);shutil.copy2(candidate,destination)
                    report['artifacts'].append(dict(file=destination.name,bytes=len(payload),sha256=digest))
            report_file.write_bytes(encoded(report));print(platform+': '+target+' passed',flush=True)
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as error:
        report.update(status='failed',error=str(error));report_file.write_bytes(encoded(report));raise
    report['status']='passed';report_file.write_bytes(encoded(report));return report

def defaults(source,output,windows=False,existing=False):
    """An enabled, unused capability must leave native gameplay unchanged."""
    root=Path(__file__).resolve().parents[1];source,output=Path(source),Path(output)
    if not windows and not existing:
        output.mkdir(parents=True,exist_ok=False)
        for edition in ('original','updated'):
            shutil.copytree(source/edition,output/edition)
            doc=ProjectDocument(output/edition,root/'build/btp-project');enable(doc);doc.save()
    platform='windows' if windows else 'linux';rows=[]
    for edition in ('original','updated'):
        for route in ('reference-bank','ordinary-training-combat','ordinary-services'):
            save=output/(edition+'-'+route+'-'+platform+'.btp')
            binary=root/('build-windows/btp-chi-bld-tests.exe' if windows else 'build/btp-chi-bld-tests')
            command=([sys.executable,str(root/'tools/windows_check.py')] if windows else [])+[str(binary),'--compare-bridge',str(source/edition),str(output/edition),str(root/'tests/fixtures'/(route+'.actions')),str(save)]
            result=subprocess.run(command,capture_output=True,text=True,timeout=120)
            row=dict(route=route,edition=edition,exit_code=result.returncode,stdout=result.stdout,stderr=result.stderr)
            if windows and not result.returncode:
                row['identical_save']=save.read_bytes()==(output/(edition+'-'+route+'-linux.btp')).read_bytes()
                if not row['identical_save']:raise RuntimeError('Native default continuation differs: '+str(save))
            rows.append(row);(output/(platform+'-defaults.json')).write_bytes(encoded(rows))
            if result.returncode:raise RuntimeError(result.stdout+result.stderr)
            print(platform+': '+edition+' '+route+' unchanged',flush=True)
    return rows

def main():
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=Path('work/chi-import/first-pair'));p.add_argument('--output',type=Path,required=True)
    p.add_argument('--windows',action='store_true',help='Replay retained fixtures in Wine and compare every held save, frame and suffix.')
    p.add_argument('--verify',action='store_true',help='Rerun retained private fixtures without copying or editing projects.')
    p.add_argument('--defaults',action='store_true',help='Compare unused bridge capability against the native campaign in --source.')
    args=p.parse_args();root=Path(__file__).resolve().parents[1]
    if args.defaults:defaults(args.source,args.output,args.windows,args.verify);return
    if not args.windows and not args.verify:prepare(args.source,args.output,root/'build/btp-project')
    verify(args.output,args.windows)
    print('Private bridge fixtures and held saves: '+str(args.output))
if __name__=='__main__':main()
