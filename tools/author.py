#!/usr/bin/env python3
"""Model-independent Construction Kit authoring interface (JSON in/out)."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
from authoring_contract import API_VERSION, BATCH_SCHEMA, OPERATIONS, AuthoringError, diagnostic, read_json
from authoring_inspect import capabilities, summary, query
from authoring_service import apply_batch, revision
from editor_model import EditorError, ProjectDocument, create_project, AUTHORING_RECEIPTS
from project_lock import project_lock


def parser():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='command',required=True)
    for name in ('capabilities','schema','inspect','catalogue','contact-sheet','animation','graph','world-preview','lint','validate','create','apply','export','render','scenario','suite','construction-export'):
        s=sub.add_parser(name)
        s.add_argument('--validator',type=Path,default=Path(os.environ.get('BTP_PROJECT_TOOL',ROOT/'build'/('btp-project.exe' if os.name=='nt' else 'btp-project'))))
        if name not in ('capabilities','schema'):s.add_argument('project',type=Path)
        if name=='schema':s.add_argument('--operation',choices=list(OPERATIONS))
        if name=='inspect':
            s.add_argument('--query',default='summary',choices=['summary','objects','object','usages','map','routes','inventory'])
            s.add_argument('--collection');s.add_argument('--id');s.add_argument('--offset',type=int,default=0);s.add_argument('--limit',type=int,default=30)
            s.add_argument('--rect',type=int,nargs=4,metavar=('X','Y','WIDTH','HEIGHT'))
        if name in ('catalogue','contact-sheet','animation'):
            s.add_argument('--source',choices=['project','library','construction-library','atlas','all'],default='project')
            s.add_argument('--library',type=Path,default=ROOT/'work/unit-library')
            s.add_argument('--construction-library',type=Path,default=ROOT/'work/construction-library')
            s.add_argument('--query',default='');s.add_argument('--offset',type=int,default=0)
            s.add_argument('--limit',type=int,default=16 if name=='contact-sheet' else 30)
            s.add_argument('--data',type=Path)
        if name in ('contact-sheet','animation','graph','world-preview'):s.add_argument('--output',type=Path,required=True)
        if name=='contact-sheet':s.add_argument('--columns',type=int,default=3)
        if name=='graph':s.add_argument('--id');s.add_argument('--depth',type=int,default=2)
        if name=='animation':
            s.add_argument('--id',required=True);s.add_argument('--frame-offset',type=int,default=0);s.add_argument('--frames',type=int,default=32)
            s.add_argument('--direction',type=int,choices=range(8));s.add_argument('--action',choices=['walk','idle','fire','damage','destruction','jump'])
        if name=='world-preview':
            s.add_argument('--world',required=True);s.add_argument('--rect',type=int,nargs=4);s.add_argument('--data',type=Path)
        if name=='lint':
            s.add_argument('--analyzer',type=Path,default=ROOT/'build'/('btp-author-analyze.exe' if os.name=='nt' else 'btp-author-analyze'))
            s.add_argument('--static-only',action='store_true');s.add_argument('--output',type=Path)
            for key in ('data','dialogue-data','combat-data','world-data'):s.add_argument('--'+key,type=Path)
        if name in ('apply','create'):
            s.add_argument('--request',type=Path,required=name=='apply',help='JSON batch; - reads standard input')
            s.add_argument('--dry-run',action='store_true');s.add_argument('--cancel-file',type=Path)
        if name=='create':
            s.add_argument('--template',type=Path,default=ROOT/'examples/beacon-demo')
            s.add_argument('--id',required=True);s.add_argument('--title',required=True)
        if name=='export':s.add_argument('--output',type=Path,required=True)
        if name=='construction-export':
            s.add_argument('--id',required=True,help='Project construction set or pattern ID')
            s.add_argument('--construction-library',type=Path,default=ROOT/'work/construction-library')
            s.add_argument('--variant',action='store_true',help='Save a new shared copy if this design already exists')
            s.add_argument('--entry',help='Existing library entry to update (requires --expected-revision)')
            s.add_argument('--expected-revision',type=int)
        if name=='render':
            s.add_argument('--map',required=True);s.add_argument('--output',type=Path,required=True)
            s.add_argument('--data',type=Path);s.add_argument('--tick',type=int,default=0);s.add_argument('--collision',action='store_true')
            s.add_argument('--rect',type=int,nargs=4);s.add_argument('--overlays',nargs='*',choices=['collision','entrances','formations','grid'],default=[])
            s.add_argument('--combat-data',type=Path)
        if name in ('scenario','suite'):
            s.add_argument('--file',type=Path,required=True);s.add_argument('--output',type=Path,required=True)
            s.add_argument('--runner',type=Path,default=ROOT/'build'/('btp-author-playtest.exe' if os.name=='nt' else 'btp-author-playtest'))
            for key in ('data','dialogue-data','combat-data','world-data'):s.add_argument('--'+key,type=Path)
            s.add_argument('--cancel-file',type=Path)
            if name=='suite':s.add_argument('--case',action='append',dest='case_ids',help='Run only this case; repeat for several affected cases.')
    review=sub.add_parser('review',help='Prepare, inspect and accept durable change proposals.')
    actions=review.add_subparsers(dest='review_action',required=True)
    for name in ('prepare','show','apply','discard','request-changes','recheck','check'):
        s=actions.add_parser(name)
        if name in ('prepare','apply','recheck'):
            s.add_argument('project',type=Path)
            s.add_argument('--validator',type=Path,default=ROOT/'build'/('btp-project.exe' if os.name=='nt' else 'btp-project'))
        if name!='prepare':s.add_argument('folder',type=Path)
        if name=='prepare':s.add_argument('--request',type=Path,required=True)
        if name in ('prepare','recheck'):
            s.add_argument('--output',type=Path,required=True);s.add_argument('--group',action='append',dest='groups')
            s.add_argument('--data',type=Path);s.add_argument('--cancel-file',type=Path)
        if name=='apply':s.add_argument('--override',action='append',default=[],help='Explicit exception for this named protection rule.')
        if name=='request-changes':s.add_argument('--note',required=True)
        if name=='check':
            s.add_argument('--validator',type=Path,default=ROOT/'build'/('btp-project.exe' if os.name=='nt' else 'btp-project'))
            for key,tool in [('analyzer','btp-author-analyze'),('runner','btp-author-playtest')]:s.add_argument('--'+key,type=Path,default=ROOT/'build'/(tool+('.exe' if os.name=='nt' else '')))
            for key in ('data','dialogue-data','combat-data','world-data'):s.add_argument('--'+key,type=Path)
            s.add_argument('--suite',type=Path);s.add_argument('--cancel-file',type=Path)
    protection=sub.add_parser('protection',help='List or deliberately edit preservation rules.')
    protection.add_argument('project',type=Path)
    protection.add_argument('--validator',type=Path,default=ROOT/'build'/('btp-project.exe' if os.name=='nt' else 'btp-project'))
    changes=protection.add_mutually_exclusive_group();changes.add_argument('--file',type=Path);changes.add_argument('--remove')
    protection.add_argument('--expected-revision')
    session=sub.add_parser('session',help='Connect to an explicitly started local editor session.')
    actions=session.add_subparsers(dest='session_action',required=True)
    for name in ('status','snapshot','propose','cancel','wait'):
        s=actions.add_parser(name);s.add_argument('folder',type=Path)
        if name in ('cancel','wait'):s.add_argument('job')
        if name=='propose':s.add_argument('--request',type=Path,required=True)
        if name in ('snapshot','propose'):s.add_argument('--job-id');s.add_argument('--wait',type=float,default=0)
        if name=='wait':s.add_argument('--seconds',type=float,default=30)
    source=sub.add_parser('source',help='Convert packages to editable modules, build, or locate source objects.')
    actions=source.add_subparsers(dest='source_action',required=True)
    for name in ('convert','build','locations'):
        s=actions.add_parser(name);s.add_argument('project',type=Path)
        s.add_argument('--validator',type=Path,default=Path(os.environ.get('BTP_PROJECT_TOOL',ROOT/'build'/('btp-project.exe' if os.name=='nt' else 'btp-project'))))
        if name in ('convert','build'):s.add_argument('--output',type=Path,required=True)
        if name=='locations':
            s.add_argument('--id');s.add_argument('--offset',type=int,default=0);s.add_argument('--limit',type=int,default=30)
    return p


def load_request(path):
    return read_json(sys.stdin.buffer if str(path)=='-' else path)


def create(args):
    if args.project.exists():raise AuthoringError('project.exists','Creation needs a new directory; existing projects are preserved.')
    request=load_request(args.request) if args.request else None
    # Stage the complete first batch before exposing a new package. Dry-run
    # uses the temporary directory only and never creates the target parent.
    if not args.dry_run:args.project.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.btp-author-new-',dir=None if args.dry_run else args.project.parent) as temporary:
        doc=create_project(args.template,Path(temporary)/'game',args.id,args.title,args.validator)
        result=None
        if request:
            if request.get('expected_revision')!='new':
                raise AuthoringError('revision.conflict','Initial creation batch must use expected_revision "new".')
            request=dict(request,expected_revision=revision(doc))
            result=apply_batch(doc,request,base_dir=args.request.parent,dry_run=False,save=True,
                               cancelled=lambda:bool(args.cancel_file and args.cancel_file.exists()))
        if args.cancel_file and args.cancel_file.exists():raise AuthoringError('job.cancelled','Creation cancelled.')
        output=dict(api_version=API_VERSION,status='validated' if args.dry_run else 'created',project=str(args.project),revision=revision(doc),batch=result)
        if not args.dry_run:
            if args.project.exists():raise AuthoringError('project.exists','Destination appeared during validation.')
            doc.root.rename(args.project)
        return output


def dispatch(args):
    if args.command=='source':
        from campaign_source import convert,build
        doc=ProjectDocument(args.project,args.validator,recover=False)
        if args.source_action=='convert':
            source=convert(doc,args.output)
            return dict(api_version=API_VERSION,status='converted',output=str(source.root),revision=revision(source),
                save_compatibility='Compilation canonicalizes JSON. Keep the original package for existing saves; start a new campaign or use the explicit save migration tool.')
        if args.source_action=='build':return dict(api_version=API_VERSION,**build(doc,args.output))
        if doc.source is None:raise AuthoringError('source.required','This is a package project. Convert a copy to modules first.')
        if args.offset<0 or not 1<=args.limit<=100:raise AuthoringError('query.bounds','Use a nonnegative offset and limit 1..100.')
        items=[v for v in doc.source.locations if args.id is None or v['id']==args.id]
        return dict(api_version=API_VERSION,status='ok',revision=revision(doc),total=len(items),items=items[args.offset:args.offset+args.limit])
    if args.command=='session':
        import authoring_session as session
        action=args.session_action
        if action=='status':return dict(status='ok',session=session.info(args.folder),jobs=session.jobs(args.folder))
        if action=='cancel':return session.cancel(args.folder,args.job)
        if action=='wait':return session.wait(args.folder,args.job,args.seconds)
        request=read_json(args.request) if action=='propose' else None
        result=session.submit(args.folder,action,request=request,base_dir=args.request.parent if request else None,job_id=args.job_id)
        return session.wait(args.folder,result['id'],args.wait) if args.wait else result
    if args.command=='review':
        import authoring_review as review
        action=args.review_action
        if action=='show':return review.read(args.folder)
        if action=='check':
            settings={k:str(getattr(args,k.replace('-','_'))) for k in ('data','dialogue-data','combat-data','world-data') if getattr(args,k.replace('-','_'))}
            return review.check_candidate(args.folder,args.validator,settings=settings,analyzer=args.analyzer,runner=args.runner,suite=args.suite,
                cancelled=lambda:bool(args.cancel_file and args.cancel_file.exists()))
        if action in ('discard','request-changes'):return review.decide(args.folder,action.replace('-','_'),getattr(args,'note',''))
        if action=='apply':
            with project_lock(args.project):
                return review.apply(ProjectDocument(args.project,args.validator),args.folder,overrides=args.override,save=True)
        doc=ProjectDocument(args.project,args.validator,recover=False)
        settings={'data':str(args.data)} if args.data else {}
        cancelled=lambda:bool(args.cancel_file and args.cancel_file.exists())
        if action=='recheck':return review.recheck(doc,args.folder,args.output,args.groups,settings=settings,cancelled=cancelled)
        return review.prepare(doc,read_json(args.request),args.output,base_dir=args.request.parent,selected=args.groups,settings=settings,cancelled=cancelled)
    if args.command=='protection':
        from authoring_protection import rules,edit_rule
        if not args.file and not args.remove:
            doc=ProjectDocument(args.project,args.validator,recover=False)
            return dict(status='ok',revision=revision(doc),rules=rules(doc))
        with project_lock(args.project):
            doc=ProjectDocument(args.project,args.validator)
            if revision(doc)!=args.expected_revision:raise AuthoringError('revision.conflict','Supply the current --expected-revision to edit preservation rules.')
            edit_rule(doc,read_json(args.file) if args.file else None,remove=args.remove);doc.save()
            return dict(status='saved',revision=revision(doc),rules=rules(doc))
    if args.command=='capabilities':return capabilities(args.validator)
    if args.command=='schema':
        return dict(**(OPERATIONS[args.operation]['schema'] if args.operation else BATCH_SCHEMA),
                    **{'$schema':'https://json-schema.org/draft/2020-12/schema'})
    if args.command=='create':return create(args)
    if args.command=='apply':
        request=load_request(args.request)
        def run():
            doc=ProjectDocument(args.project,args.validator,recover=not args.dry_run)
            return apply_batch(doc,request,base_dir=args.request.parent,dry_run=args.dry_run,save=not args.dry_run,
                cancelled=lambda:bool(args.cancel_file and args.cancel_file.exists()))
        if args.dry_run:return run()
        with project_lock(args.project):return run()
    # Queries never recover an interrupted save or create files in a package.
    doc=ProjectDocument(args.project,args.validator,recover=False)
    if args.command=='construction-export':
        from construction_library import ConstructionLibrary,summary as construction_summary,closure
        shared=ConstructionLibrary(args.construction_library,args.validator);bundle=closure(doc,args.id);expected=None
        if args.entry:
            if args.variant or args.expected_revision is None:raise AuthoringError('request.invalid','Updating a library entry requires --expected-revision, without --variant.')
            expected=read_json(shared.path(args.entry))
            if expected['revision']!=args.expected_revision:raise AuthoringError('revision.conflict','Library revision changed; inspect it again.')
            if expected['kind']!=bundle['kind']:raise AuthoringError('request.invalid','Select a library entry of the same type.')
            bundle.update(entry_id=expected['entry_id'],revision=expected['revision'])
        elif args.expected_revision is not None:raise AuthoringError('request.invalid','--expected-revision requires --entry.')
        doc.unchanged_on_disk();saved=shared.save(bundle,expected,args.variant)
        return dict(api_version=API_VERSION,status='exported',data=construction_summary(saved,shared.path(saved['entry_id'])))
    if args.command in ('catalogue','contact-sheet','animation'):
        from asset_catalogue import catalogue,search
        from authoring_visuals import VisualSource,contact_sheet,animation_strip
        settings={'data':str(args.data)} if args.data else {}
        decoded=VisualSource(doc,settings).tiles if args.source in ('atlas','all') or args.data else None
        values=catalogue(doc,args.source,args.library,decoded,args.construction_library)
        if args.command=='animation':
            selected=[r for r in values if args.id in (r['id'],r['key'])]
            if len(selected)!=1:raise AuthoringError('object.missing','Choose one exact catalogue key for the animation.')
            return animation_strip(doc,selected[0],args.output,settings,args.frame_offset,args.frames,args.direction,args.action)
        result=search(values,args.query,args.offset,args.limit)
        if args.command=='contact-sheet':
            return contact_sheet(doc,result['items'],args.output,settings,args.columns)
        doc.unchanged_on_disk()
        return dict(api_version=API_VERSION,status='ok',revision=revision(doc),data=result)
    if args.command=='graph':
        from authoring_visuals import event_graph
        return event_graph(doc,args.output,args.id,args.depth)
    if args.command=='world-preview':
        from authoring_visuals import world_svg
        return world_svg(doc,args.world,args.output,{'data':str(args.data)} if args.data else {},args.rect)
    if args.command=='inspect':
        data=summary(doc,args.validator) if args.query=='summary' else query(doc,args.query,args.collection,args.id,args.offset,args.limit,args.rect)
        doc.unchanged_on_disk()
        return dict(api_version=API_VERSION,status='ok',revision=revision(doc),data=data)
    if args.command=='validate':return dict(api_version=API_VERSION,status='valid',revision=revision(doc),validation=doc.validate(),diagnostics=[])
    if args.command=='lint':
        from authoring_analysis import analyze
        return analyze(doc,args.analyzer,{k:str(getattr(args,k.replace('-','_'))) for k in ('data','dialogue-data','combat-data','world-data') if getattr(args,k.replace('-','_'))},not args.static_only,args.output)
    if args.command=='export':
        doc.export(args.output)
        return dict(api_version=API_VERSION,status='exported',output=str(args.output),revision=revision(doc))
    if args.command=='render':
        if args.output.suffix.lower()=='.svg' or args.overlays or args.rect:
            from authoring_visuals import map_svg
            if args.output.suffix.lower()!='.svg':raise AuthoringError('output.invalid','Use an .svg output for labelled/region map previews.')
            settings={key:str(getattr(args,key.replace('-','_'))) for key in ('data','combat-data') if getattr(args,key.replace('-','_'))}
            return map_svg(doc,args.map,args.output,settings,args.tick,args.rect,list(set(args.overlays+(['collision'] if args.collision else []))))
        from authoring_preview import render_map
        return render_map(doc,args.map,args.output,{'data':str(args.data)} if args.data else {},args.tick,args.collision)
    if args.command in ('scenario','suite'):
        from authoring_scenarios import run,run_suite
        settings={k:str(getattr(args,k.replace('-','_'))) for k in ('data','dialogue-data','combat-data','world-data') if getattr(args,k.replace('-','_'))}
        cancelled=lambda:bool(args.cancel_file and args.cancel_file.exists())
        if args.command=='suite':return run_suite(doc,read_json(args.file),args.file.parent,args.output,args.runner,settings,cancelled,case_ids=args.case_ids)
        return run(doc,read_json(args.file),args.output,args.runner,settings,cancelled)


def main(argv=None):
    args=parser().parse_args(argv)
    try:
        result=dispatch(args);code=130 if result.get('status')=='cancelled' else 1 if result.get('status')=='failed' else 0
    except (EditorError,OSError,ValueError,KeyError,TypeError,RecursionError) as exc:
        result=dict(api_version=API_VERSION,status='error',diagnostics=[diagnostic(exc)]);code=1
    except KeyboardInterrupt:
        result=dict(api_version=API_VERSION,status='cancelled',diagnostics=[diagnostic(AuthoringError('job.cancelled','Interrupted; any interrupted save is recovered on reopen.'))]);code=130
    print(json.dumps(result,ensure_ascii=True,sort_keys=True,indent=2))
    return code


if __name__=='__main__':raise SystemExit(main())
