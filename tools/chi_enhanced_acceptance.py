"""Fresh Enhanced-only ending, built-in parity and held/cross-platform evidence."""
from pathlib import Path
import hashlib,json,subprocess,sys
from chi_import import ROOT,import_campaigns,plain_path
from editor_model import EditorError,ProjectDocument,encoded


def execute(binary,args,windows=False):
    command=[str(ROOT/('build-windows' if windows else 'build')/(binary+('.exe' if windows else ''))),*map(str,args)]
    if windows:command=[sys.executable,str(ROOT/'tools/windows_check.py'),*command]
    result=subprocess.run(command,capture_output=True,text=True,timeout=180)
    if result.returncode:raise EditorError(result.stdout+result.stderr)
    return result.stdout


def verify(output,windows=False):
    output=plain_path(output);report=json.loads((output/'evidence.json').read_bytes())
    if windows and report.get('linux',{}).get('status')!='passed':raise EditorError('Complete Linux Enhanced acceptance first.')
    project=output/'base/updated';route=Path(report['route']);keys=route.read_text().splitlines();suffix='-windows' if windows else ''
    source=Path(report.get('source',ROOT/'Original DOS'))
    if hashlib.sha256(route.read_bytes()).hexdigest()!=report['sha256']:raise EditorError('Enhanced route changed after its acceptance run.')
    caches=project/'chi'
    parity=execute('btp-chi-import-tests',['--enhanced-route',project,source,caches/'talk-data.bin',caches/'combat-data.bin',caches/'world-data.bin',ROOT/'content/updated/roster.json',route],windows)
    (output/('parity'+suffix+'.log')).write_text(parity);print(parity,flush=True)
    final=output/('ending'+suffix)
    text=execute('btech-headless',['--project',project,'--replay',route,'--save',final.with_suffix('.btp'),'--frame',final.with_suffix('.ppm'),'--bld-trace',final.with_suffix('.jsonl')],windows)
    state=json.loads(text)
    if state['mode']!='ending' or state['combat_rules']!='enhanced' or sum(p[0]!=255 for p in state['people'])!=5:raise EditorError('Enhanced full ending assertion failed.')
    final.with_suffix('.json').write_bytes(encoded(state))
    facts=json.loads(route.with_suffix('.json').read_bytes());points=facts['checkpoints']
    labels=('training-combat-start','training-victory','invasion-start','rex-crest','hospital-companion-pause','door-1-opening','map-room','ending-start')
    held=[]
    for label in labels:
        candidates=[p for p in points if p['label']==label]
        if not candidates:raise EditorError('Missing declared Enhanced checkpoint: '+label)
        point=candidates[0];prefix=output/(label+'-prefix.actions');tail=output/(label+'-tail.actions')
        prefix.write_text('\n'.join(keys[:point['tick']])+'\n');tail.write_text('\n'.join(keys[point['tick']:])+'\n')
        save=output/(label+suffix+'.btp');continued=output/(label+'-continued'+suffix+'.btp')
        execute('btech-headless',['--project',project,'--replay',prefix,'--save',save],windows)
        resumed=json.loads(execute('btech-headless',['--project',project,'--load',save,'--replay',tail,'--save',continued],windows))
        if resumed!=state or continued.read_bytes()!=final.with_suffix('.btp').read_bytes():raise EditorError('Enhanced continuation differs: '+label)
        if windows and save.read_bytes()!=(output/(label+'.btp')).read_bytes():raise EditorError('Platform held save differs: '+label)
        held.append(dict(label=label,tick=point['tick'],sha256=hashlib.sha256(save.read_bytes()).hexdigest()))
        print('PASS held Enhanced '+label,flush=True)
    if windows:
        for extension in ('.btp','.ppm','.jsonl','.json'):
            if final.with_suffix(extension).read_bytes()!=(output/'ending').with_suffix(extension).read_bytes():raise EditorError('Enhanced platform artifact differs: '+extension)
    from chi_coverage import coverage
    measured=coverage(ProjectDocument(project,ROOT/'build/btp-project'),[final.with_suffix('.jsonl')])
    if measured['faults'] or measured['unresolved_observations']:raise EditorError('Enhanced ending trace has faults or unresolved observations.')
    result=dict(status='passed',inputs=len(keys),rules='Enhanced throughout, asserted after every ordinary input',held=held,
        people=5,ending=state['mode'],parity=parity,coverage=dict(programs=sum(p['instructions']['observed']>0 for p in measured['programs']),declared_programs=len(measured['programs']),
            instructions=sum(p['instructions']['observed'] for p in measured['programs']),declared_instructions=sum(p['instructions']['declared'] for p in measured['programs']),
            branches=sum(p['branches']['observed'] for p in measured['programs']),declared_branches=sum(p['branches']['declared'] for p in measured['programs']),faults=len(measured['faults'])),
        tools={name:hashlib.sha256((ROOT/('build-windows' if windows else 'build')/(name+('.exe' if windows else ''))).read_bytes()).hexdigest() for name in ('btech-headless','btp-chi-import-tests')})
    (output/('windows-evidence.json' if windows else 'linux-evidence.json')).write_bytes(encoded(result))
    report['windows' if windows else 'linux']=result;report['status']='passed' if not windows or report.get('linux',{}).get('status')=='passed' else 'failed'
    (output/'evidence.json').write_bytes(encoded(report));return report


def run(output,source):
    output=plain_path(output);source=plain_path(source)
    if output.exists() or any(output.is_relative_to(ROOT/n) for n in ('Original DOS','UnBattletech')):raise EditorError('Choose a new private output directory.')
    output.mkdir(parents=True)
    report=dict(format='btp-chi-enhanced-acceptance-v1',status='running',stage='import',source=str(source),
        scope='Fresh input-only Updated campaign with default Enhanced rules. Bounded ordinary outdoor waits and owner-authorized credit inputs; no state/RNG/rule edits. Equivalence to current built-in Updated, not all DOS branches.')
    (output/'evidence.json').write_bytes(encoded(report));import_campaigns(source,output/'base','updated',ROOT/'build/btp-project')
    report['stage']='planning ordinary input route';(output/'evidence.json').write_bytes(encoded(report))
    from chi_enhanced_route import generate
    route=generate(output/'base/updated',output/'route',source=source)
    report.update(stage='verification',route=str(route),sha256=hashlib.sha256(route.read_bytes()).hexdigest())
    (output/'evidence.json').write_bytes(encoded(report));return verify(output)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--data',type=Path,default=ROOT/'Original DOS');parser.add_argument('--windows',action='store_true');a=parser.parse_args()
    try:verify(a.output,True) if a.windows else run(a.output,a.data)
    except (EditorError,OSError,ValueError,RuntimeError,subprocess.SubprocessError) as error:
        path=a.output/'evidence.json'
        if path.exists():
            report=json.loads(path.read_bytes());report.update(status='failed',error=str(error));path.write_bytes(encoded(report))
        parser.exit(1,str(error)+'\n')
