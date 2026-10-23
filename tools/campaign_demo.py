"""Generate, diagnose, repair, verify and deliver the recorded AI8 campaign."""
import json
import subprocess
import time
from pathlib import Path

from authoring_contract import AuthoringError, diagnostic
from authoring_service import apply_batch, revision
from editor_model import ProjectDocument, EditorError, create_project, encoded
from campaign_recipe import build, ROOT


def dependencies(settings):
    """Report absent caller-supplied assets before invoking gameplay tools."""
    missing=[]
    for key in ('data','dialogue-data','combat-data','world-data'):
        path=Path(settings[key]) if settings.get(key) else None
        present=bool(path and (path.is_dir() and (path/'BTECH.EXE').is_file() if key=='data' else path.is_file()))
        if not present:missing.append(dict(code='dependency.missing',severity='error',field_path='settings.'+key,
            message='Supply --'+key+' with '+('the original CHI DOS directory.' if key=='data' else 'its prepared cache file.'),
            path=str(path) if path else None))
    return missing


def batch(doc, folder, name, operations, scope):
    request=dict(api_version=1,request_id='ai8-'+name,project_id=doc.manifest['package_id'],expected_revision=revision(doc),
        label=name.replace('-',' ').title(),scope=scope,operations=operations)
    (folder/(name+'.commands.json')).write_bytes(encoded(request))
    return apply_batch(doc,request,base_dir=folder,save=True)


def verify(doc, output, runner, analyzer, settings, cancelled=lambda:False):
    from authoring_analysis import analyze
    from authoring_scenarios import run, run_suite
    from authoring_visuals import map_svg,event_graph,contact_sheet
    from asset_catalogue import catalogue,search
    from scene_tools import formation_data
    from campaign_source import convert,build as compile_source
    missing=dependencies(settings)
    if missing:return dict(status='failed',diagnostics=missing)
    output=Path(output);evidence=output/'checks';evidence.mkdir()
    before=analyze(doc,analyzer,settings,output=evidence/'lint-before.json')
    if before['status']=='failed':raise AuthoringError('recipe.invalid','Initial mission checks failed; inspect checks/lint-before.json.')
    encounter=next(e for e in doc.adventure['encounters'] if e['id']=='relay:raider')
    at=list(encounter['enemies'][0]['at']);dx,dy=formation_data(doc,settings)['mechs'][0]
    broken_at=[encounter['party_at'][0]+dx,encounter['party_at'][1]+dy]
    move=dict(op='marker.move',map=encounter['map'],kind='enemy',id=encounter['id'],enemy_index=0,at=broken_at)
    scope=['adventure.encounters/'+encounter['id']]
    batch(doc,evidence,'break-deployment',[move],scope)
    # Always restore the deliberate defect, even when a tool is unavailable.
    # Reports and exact requests remain alongside the undamaged final game.
    try:
        broken=analyze(doc,analyzer,settings,output=evidence/'lint-broken.json')
        if not any(d['code']=='deployment.overlap' for d in broken['diagnostics']):raise AuthoringError('recipe.diagnosis','Expected deployment.overlap was not diagnosed.')
        scenario=json.loads((output/'scenarios/assault.json').read_bytes())
        failed=run(doc,scenario,evidence/'broken-route',runner,settings,cancelled)
        if failed['status']!='failed':raise AuthoringError('recipe.diagnosis','Overlapping deployment unexpectedly completed the campaign.')
    finally:
        batch(doc,evidence,'repair-deployment',[dict(move,at=at)],scope)
    repaired=analyze(doc,analyzer,settings,output=evidence/'lint-repaired.json')
    if repaired['status']=='failed':raise AuthoringError('recipe.invalid','Repaired mission checks failed.')
    suite_path=output/'scenarios/suite.json'
    suite=run_suite(doc,json.loads(suite_path.read_bytes()),suite_path.parent,evidence/'suite',runner,settings,cancelled)
    # Also exercise the tiny independent fixture with no original resources.
    independent=ProjectDocument(ROOT/'examples/beacon-demo',doc.validator,recover=False)
    small=run(independent,dict(format='btp-author-scenario-v1',steps=[dict(op='pages'),dict(op='checkpoint'),dict(op='capture')]),
              evidence/'independent',runner,{},cancelled)
    visuals=output/'visuals';visuals.mkdir()
    for scene in ('relay:town','recovery:valley','cairn:pass'):
        map_svg(doc,scene,visuals/(scene.replace(':','-')+'.svg'),settings,overlays=['entrances','formations','grid'])
    event_graph(doc,visuals/'contracts.svg','dispatch:office',4)
    units=search(catalogue(doc),'kind:mech')['items']
    contact_sheet(doc,units,visuals/'roster.svg',settings)
    # Replay the recorded batch, not a second sampling/generation request.
    inputs=output/'inputs';p=json.loads((output/'recipe.json').read_bytes())
    replay=create_project(inputs/'template',evidence/'replayed',p['package_id'],p['title'],doc.validator)
    apply_batch(replay,json.loads((inputs/'creation.commands.json').read_bytes()),base_dir=inputs,save=True)
    source=convert(replay,evidence/'replayed-source');rebuilt=compile_source(source,evidence/'replayed-game')
    original=json.loads((output/'build-report.json').read_bytes())
    deterministic=rebuilt['fingerprint']==original['package_fingerprint']
    if not deterministic:raise AuthoringError('recipe.reproduction','Replaying the recorded commands changed the playable content.')
    # The repaired source and deliverable must also match, including Lua bytes.
    repaired_build=compile_source(doc,evidence/'repaired-game')
    if repaired_build['fingerprint']!=rebuilt['fingerprint']:raise AuthoringError('recipe.repair','Repair did not restore the original playable content.')
    return dict(status='passed' if suite['status']=='passed' and small['status']=='passed' else 'failed',
        diagnosed='deployment.overlap',broken_route=failed['status'],suite=suite,independent=small['status'],
        reproduction=dict(identical=True,fingerprint=rebuilt['fingerprint']),revision=revision(doc),visuals=str(visuals))


def run(params, output, validator, runner, analyzer, settings, checks=False, play=False, player=None, cancelled=lambda:False):
    if cancelled():raise AuthoringError('job.cancelled','Recipe cancelled before creating output.')
    started=time.monotonic();doc,built=build(params,output,validator);output=Path(output).resolve()
    report=dict(api_version=1,status='created',project=str(output/'game'),source=str(doc.root),build=built,
                dependencies=dict(requires=doc.manifest['requires'],diagnostics=dependencies(settings)))
    try:
        if checks or play:
            report['checks']=verify(doc,output,runner,analyzer,settings,cancelled)
            report['status']=report['checks']['status']
        if play and report['status']=='passed':
            if not player or not Path(player).is_file():raise AuthoringError('runtime.unavailable','Build or specify the native player before using --play.')
            save=output/'play';save.mkdir()
            command=[str(Path(player).resolve()),'--project',str(output/'game'),'--save-file',str(save/'game.btp')]
            for key,path in settings.items():command+=['--'+key,str(Path(path).resolve())]
            with (save/'player.log').open('w') as log:
                process=subprocess.Popen(command,cwd=save,stdout=log,stderr=log)
            report['play']=dict(pid=process.pid,command=command,log=str(save/'player.log'))
    except (EditorError,OSError,ValueError,subprocess.SubprocessError) as exc:
        report.update(status='failed',diagnostics=[diagnostic(exc)])
    finally:
        report['elapsed_seconds']=round(time.monotonic()-started,3)
        (output/'demo-report.json').write_bytes(encoded(report))
    return report
