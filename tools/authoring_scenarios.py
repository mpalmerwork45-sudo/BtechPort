"""Minimal scenario/replay evidence, backed by the actual C player."""
import hashlib
import json
from pathlib import Path
import subprocess
import time
from authoring_contract import API_VERSION,AuthoringError,check,obj,enum,integer,array,TEXT,ID
from authoring_service import revision
from editor_model import encoded

STEP_SCHEMAS = [
    obj(dict(op={'const':'input'},action=TEXT,repeat=integer(1,120000)),['op','action']),
    *[obj(dict(op={'const':name}),['op']) for name in ('pages','enter','checkpoint','capture')],
    obj(dict(op={'const':'walk'},entrance=ID),['op','entrance']),
    obj(dict(op={'const':'choose'},label=TEXT),['op','label']),
    obj(dict(op={'const':'battle'},control={'const':'computer'}),['op','control']),
    dict(**obj(dict(op={'const':'assert'},credits=integer(0,16777215),party_count=integer(1,8),
        phase=enum('exploration','entry','text','choice','shop','battle','fault','complete'),
        map=ID,event=ID,flag=ID,value=integer(0,255),objective=ID,status=enum('inactive','active','complete')),['op']),
        anyOf=[dict(required=[key]) for key in ('credits','party_count','phase','map','event','flag','objective')],
        allOf=[dict(**{'if':dict(required=['flag'])},then=dict(required=['value'])),
               dict(**{'if':dict(required=['objective'])},then=dict(required=['status']))]),
]
SCHEMA = obj(dict(format={'const':'btp-author-scenario-v1'},max_ticks=integer(1,120000),
                  expected_revision=dict(type='string',pattern='^[0-9a-f]{64}$'),
                  steps=array(dict(oneOf=STEP_SCHEMAS),1,256)),['format','steps'])


def run(document, scenario, output, runner, settings=None):
    check(scenario,SCHEMA);base=revision(document)
    if scenario.get('expected_revision',base)!=base:
        raise AuthoringError('revision.conflict','Scenario belongs to another content revision; regenerate its setup.')
    output=Path(output).resolve();runner=Path(runner).resolve()
    if output.is_relative_to(document.root):raise AuthoringError('output.invalid','Run scenarios in an artifact directory outside the project.')
    if output.exists():raise AuthoringError('output.exists','Scenario output must be a new directory.')
    if not runner.is_file():raise AuthoringError('runtime.unavailable','Build btp-author-playtest before running scenarios.')
    document.unchanged_on_disk();output.mkdir(parents=True)
    # A private exact snapshot prevents edits during the run from changing
    # its evidence. It is removed from neither the original nor other jobs.
    game=output/'game';game.mkdir();document.stage(game)
    payload=dict(scenario);payload.pop('expected_revision',None)
    source=output/'scenario.json';source.write_bytes(encoded(payload))
    command=[str(runner),'--project',str(game),'--scenario',str(source)]
    for key,path in (settings or {}).items():command.extend(['--'+key,str(Path(path).resolve())])
    start=time.monotonic();timeout=False
    # File-backed diagnostics bound memory even when a runtime fault writes
    # repetitive output. Tick/step limits bound normal recordings and traces.
    with (output/'steps.jsonl').open('wb') as log,(output/'stderr.txt').open('wb') as errors:
        try:process=subprocess.run(command,cwd=output,stdout=log,stderr=errors,timeout=45)
        except subprocess.TimeoutExpired:timeout=True;process=None
    elapsed=time.monotonic()-start;path=output/'steps.jsonl'
    records=[]
    if path.stat().st_size<=4*1024*1024:
        try:records=[json.loads(line) for line in path.read_text().splitlines() if line]
        except ValueError:records=[]
    final=records[-1] if records and 'status' in records[-1] else {}
    passed=not timeout and process.returncode==0 and final.get('status')=='passed'
    message=('Scenario exceeded 45 seconds.' if timeout else final.get('message') or (output/'stderr.txt').read_text()[:4000])
    report=dict(api_version=API_VERSION,status='passed' if passed else 'failed',project_id=document.manifest['package_id'],
                revision=base,runtime_sha256=hashlib.sha256(runner.read_bytes()).hexdigest(),
                scenario_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),elapsed_seconds=round(elapsed,4),
                coverage='Ordinary input from the normal new-game state; assertions cover this declared route only.',
                result=final,steps=[r for r in records if 'step' in r],
                artifacts=[dict(path=str(p),bytes=p.stat().st_size) for p in sorted(output.iterdir()) if p.is_file()],
                diagnostics=[] if passed else [dict(code='scenario.timeout' if timeout else 'scenario.failed',severity='error',
                    message=message or 'Scenario runner failed; inspect stderr.txt.',field_path='$.steps',
                    object_id=final.get('state',{}).get('event'),location=final.get('state',{}).get('at'))])
    (output/'report.json').write_bytes(encoded(report))
    # Console response stays compact. Full per-step evidence is in the report.
    return dict(api_version=API_VERSION,status=report['status'],revision=base,report=str(output/'report.json'),
                elapsed_seconds=report['elapsed_seconds'],result=final,diagnostics=report['diagnostics'])
