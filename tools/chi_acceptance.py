"""Combined, bounded CHI campaign/editing acceptance; evidence stays private."""
from pathlib import Path
import hashlib,json,re,subprocess,sys
from chi_import import ROOT,plain_path,import_campaigns
from editor_model import ProjectDocument,EditorError,encoded

ROUTES=('reference-class-funded','reference-bank','ordinary-training-combat','ordinary-services','ordinary-alternate-services','ordinary-fresh-campaign')

def run(output,source=None,updated_route=None):
    output=plain_path(output);source=plain_path(source or ROOT/'Original DOS')
    if output.exists() or any(output.is_relative_to(ROOT/n) for n in ('Original DOS','UnBattletech')):raise EditorError('Choose a new private acceptance output directory.')
    output.mkdir(parents=True);tool=ROOT/'build/btp-project';report=dict(format='btp-chi-acceptance-v1',status='running',records=[])
    def execute(name,binary,args):
        result=subprocess.run([str(ROOT/'build'/binary),*map(str,args)],capture_output=True,text=True,timeout=120)
        report['records'].append(dict(case=name,executable=binary,args=list(map(str,args)),exit_code=result.returncode,stdout=result.stdout,stderr=result.stderr))
        (output/'evidence.json').write_bytes(encoded(report))
        if result.returncode:raise EditorError(name+': '+result.stdout+result.stderr)
        print('PASS '+name,flush=True);return result
    import_campaigns(source,output/'base',validator=tool)
    for edition in ('original','updated'):execute('all-BLD-roundtrips-'+edition,'btp-chi-bld-tests',['--roundtrip',output/'base'/edition])
    caches=output/'base/original/chi'
    execute('complete-default-campaigns-and-isolated-slots','btp-chi-import-tests',[
        source,caches/'talk-data.bin',caches/'combat-data.bin',caches/'world-data.bin',ROOT/'content/updated/roster.json',output/'base/original',output/'base/updated',
        *[ROOT/'tests/fixtures'/(r+'.actions') for r in ROUTES]])
    from chi_coverage import coverage
    if updated_route is None:
        from chi_updated_route import generate
        updated_route=generate(output/'base/updated',output/'updated-route')
    updated_route=Path(updated_route).resolve()
    report['full_routes']={'original':dict(file=str(ROOT/'tests/fixtures/ordinary-fresh-campaign.actions'),rules='Legacy default'),
        'updated':dict(file=str(updated_route),rules='Legacy selected through ordinary Settings; Enhanced remains the default and has separate prepared checks')}
    execute('updated-complete-builtin-parity','btp-chi-import-tests',['--updated-route',output/'base/updated',source,caches/'talk-data.bin',caches/'combat-data.bin',caches/'world-data.bin',ROOT/'content/updated/roster.json',updated_route])
    for edition in ('original','updated'):
        project=output/'base'/edition;prefix=output/edition
        result=execute('complete-ending-'+edition,'btech-headless',['--project',project,'--replay',report['full_routes'][edition]['file'],
            '--save',str(prefix)+'-complete.btp','--frame',str(prefix)+'-complete.ppm','--bld-trace',str(prefix)+'-complete.jsonl'])
        state=json.loads(result.stdout)
        if state['mode']!='ending' or state['script_error']:raise EditorError('Full route did not reach the ending: '+edition)
        (output/(edition+'-complete-state.json')).write_bytes(encoded(state))
        measured=coverage(ProjectDocument(project,tool),[Path(str(prefix)+'-complete.jsonl')])
        (output/(edition+'-coverage.json')).write_bytes(encoded(measured))
        report.setdefault('measured_coverage',{})[edition]=dict(programs=len(measured['programs']),instructions=sum(p['instructions']['observed'] for p in measured['programs']),
            declared_instructions=sum(p['instructions']['declared'] for p in measured['programs']),branches=sum(p['branches']['observed'] for p in measured['programs']),
            declared_branches=sum(p['branches']['declared'] for p in measured['programs']),native_internals='UNKNOWN',faults=len(measured['faults']))
        execute('prepared-multiple-unit-party-'+edition,'btp-chi-import-tests',['--party-proof',project,output/(edition+'-party.btp')])
    from chi_service_evidence import generate as services
    from chi_mission_evidence import generate as missions
    from chi_spatial_evidence import generate as spatial
    services(source,output/'services',output/'base',edited_only=True)
    missions(source,output/'missions',output/'base',edited_only=True)
    spatial(source,output/'spatial')
    from chi_bridge_evidence import prepare,verify
    prepare(output/'base',output/'bridge',tool);verify(output/'bridge')
    report['status']='passed';report['claims']=dict(defaults='VERIFIED against built-in port on the declared complete and service/training routes',
        original_DOS_all_branches='UNKNOWN',native_handler_branch_coverage='UNKNOWN',prepared_party='Declared three-person/two-mech post-training checkpoint; Updated owns added units',
        helper_boundaries='Service/mission/spatial proofs retain their explicit declared checkpoints; they are not input-only full campaigns.')
    report['default_gameplay_ticks']=sum(len([line for line in (ROOT/'tests/fixtures'/(r+'.actions')).read_text().splitlines() if line and not line.startswith('#')]) for r in ROUTES)*2
    report['updated_complete_gameplay_ticks']=sum(bool(line and not line.startswith('#')) for line in updated_route.read_text().splitlines())
    for record in report['full_routes'].values():record['sha256']=hashlib.sha256(Path(record['file']).read_bytes()).hexdigest()
    report['tools']={n:hashlib.sha256((ROOT/'build'/n).read_bytes()).hexdigest() for n in ('btp-project','btech-headless','btp-chi-import-tests','btp-chi-bld-tests')}
    (output/'evidence.json').write_bytes(encoded(report));return report

def windows(output):
    output=plain_path(output);report=json.loads((output/'evidence.json').read_bytes())
    if report['status']!='passed':raise EditorError('Complete Linux acceptance first.')
    rows=[]
    for record in report['records']:
        binary=record['executable'];args=list(record['args'])
        if binary not in ('btp-chi-import-tests','btp-chi-bld-tests','btech-headless'):raise EditorError('Unknown acceptance executable.')
        original=[]
        for i,arg in enumerate(args):
            if arg.endswith(('.btp','.ppm','.jsonl')):
                target=Path(arg)
                if not target.resolve().is_relative_to(output):raise EditorError('Acceptance output escapes its private directory.')
                replacement=target.with_name(target.stem+'-windows'+target.suffix);original.append((target,replacement));args[i]=str(replacement)
        result=subprocess.run([sys.executable,str(ROOT/'tools/windows_check.py'),str(ROOT/'build-windows'/(binary+'.exe')),*args],capture_output=True,text=True,timeout=180)
        row=dict(case=record['case'],exit_code=result.returncode,stdout=result.stdout,stderr=result.stderr,comparisons=[]);rows.append(row)
        if result.returncode:raise EditorError(result.stdout+result.stderr)
        if binary=='btech-headless' and json.loads(result.stdout)!=json.loads(record['stdout']):raise EditorError('Platform canonical state differs: '+record['case'])
        for a,b in original:
            if a.read_bytes()!=b.read_bytes():raise EditorError('Platform artifact differs: '+str(a))
            row['comparisons'].append(dict(file=a.name,sha256=hashlib.sha256(a.read_bytes()).hexdigest()))
        (output/'windows-evidence.json').write_bytes(encoded(dict(status='running',records=rows)))
        print('PASS Windows '+record['case'],flush=True)
    # Mission/bridge helpers compare every held continuation in their own
    # retained reports, preserving the exact Linux project revisions.
    from chi_mission_evidence import replay_windows
    from chi_bridge_evidence import verify
    replay_windows(output/'missions');verify(output/'bridge',windows=True)
    return windows_details(output)

def windows_details(output):
    """Resume only the remaining service/spatial checks from retained evidence."""
    output=plain_path(output);previous=json.loads((output/'windows-evidence.json').read_bytes())
    linux=json.loads((output/'evidence.json').read_bytes());rows=previous['records']
    if linux['status']!='passed' or [r['case'] for r in rows]!=[r['case'] for r in linux['records']] or any(r['exit_code'] for r in rows):
        raise EditorError('Complete all baseline Windows cases first.')
    for name in ('missions','bridge'):
        if json.loads((output/name/'windows-evidence.json').read_bytes())['status']!='passed':raise EditorError('Complete Windows '+name+' evidence first.')
    # Some mechanism-only helpers intentionally remove their temporary save.
    # Compare retained artifacts; absence is not an additional save proof.
    service=json.loads((output/'services/evidence.json').read_bytes());service_rows=[]
    for record in service['records']:
        binary=record['executable'];args=list(record['args']);slot=Path(args[-1]) if args[-1].endswith('.btp') else None
        if binary not in ('btp-chi-bld-tests','btp-chi-service-native-tests'):raise EditorError('Unknown service executable.')
        if slot:args[-1]=str(slot.with_name(slot.stem+'-windows.btp'))
        result=subprocess.run([sys.executable,str(ROOT/'tools/windows_check.py'),str(ROOT/'build-windows'/(binary+'.exe')),*args],capture_output=True,text=True,timeout=120)
        if result.returncode:raise EditorError(result.stdout+result.stderr)
        retained=bool(slot and slot.exists())
        if retained and slot.read_bytes()!=Path(args[-1]).read_bytes():raise EditorError('Service platform continuation differs: '+record['args'][0])
        service_rows.append(dict(case=record['args'][0],exit_code=0,identical_retained_save=retained,stdout=result.stdout))
    spatial=json.loads((output/'spatial/evidence.json').read_bytes());spatial_rows=[]
    cases=[['--proof',r['base'],r['project'],r['kind']] for r in spatial['examples']]
    cases+=[['--held-film',output/'spatial/film',ROOT/'tests/fixtures/ordinary-training-combat.actions',output/'spatial/film-held-windows.btp'],
        ['--moved-route',output/'spatial/base/original',output/'spatial/citadel',ROOT/'tests/fixtures/ordinary-training-combat.actions']]
    for args in cases:
        result=subprocess.run([sys.executable,str(ROOT/'tools/windows_check.py'),str(ROOT/'build-windows/btp-chi-spatial-tests.exe'),*map(str,args)],capture_output=True,text=True,timeout=120)
        if result.returncode:raise EditorError(result.stdout+result.stderr)
        spatial_rows.append(dict(args=list(map(str,args)),exit_code=0,stdout=result.stdout))
    report=dict(status='passed',records=rows,services=service_rows,spatial=spatial_rows)
    (output/'windows-evidence.json').write_bytes(encoded(report));print('PASS Windows services and spatial continuations',flush=True);return report

def main():
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--data',type=Path,default=ROOT/'Original DOS');p.add_argument('--windows',action='store_true');p.add_argument('--windows-details',action='store_true',help='Resume retained Windows service/spatial checks after baseline, mission and bridge success.');p.add_argument('--updated-route',type=Path,help='Reuse a retained private input-only Updated route. Ending and built-in parity are still checked.');a=p.parse_args()
    try:windows_details(a.output) if a.windows_details else windows(a.output) if a.windows else run(a.output,a.data,a.updated_route)
    except (OSError,ValueError,EditorError,RuntimeError,subprocess.TimeoutExpired) as e:
        report=a.output/'evidence.json'
        if report.exists() and not a.windows and not a.windows_details:
            value=json.loads(report.read_bytes());value.update(status='failed',error=str(e));report.write_bytes(encoded(value))
        p.exit(1,str(e)+'\n')
if __name__=='__main__':main()
