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
    for name in ('capabilities','schema','inspect','catalogue','contact-sheet','animation','graph','world-preview','lint','validate','create','apply','export','render','scenario','suite'):
        s=sub.add_parser(name)
        s.add_argument('--validator',type=Path,default=Path(os.environ.get('BTP_PROJECT_TOOL',ROOT/'build'/('btp-project.exe' if os.name=='nt' else 'btp-project'))))
        if name not in ('capabilities','schema'):s.add_argument('project',type=Path)
        if name=='schema':s.add_argument('--operation',choices=list(OPERATIONS))
        if name=='inspect':
            s.add_argument('--query',default='summary',choices=['summary','objects','object','usages','map','routes','inventory'])
            s.add_argument('--collection');s.add_argument('--id');s.add_argument('--offset',type=int,default=0);s.add_argument('--limit',type=int,default=30)
            s.add_argument('--rect',type=int,nargs=4,metavar=('X','Y','WIDTH','HEIGHT'))
        if name in ('catalogue','contact-sheet','animation'):
            s.add_argument('--source',choices=['project','library','atlas','all'],default='project')
            s.add_argument('--library',type=Path,default=ROOT/'work/unit-library')
            s.add_argument('--query',default='');s.add_argument('--offset',type=int,default=0)
            s.add_argument('--limit',type=int,default=16 if name=='contact-sheet' else 30)
            s.add_argument('--data',type=Path)
        if name in ('contact-sheet','animation','graph','world-preview'):s.add_argument('--output',type=Path,required=True)
        if name=='contact-sheet':s.add_argument('--columns',type=int,default=3)
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
    if args.command in ('catalogue','contact-sheet','animation'):
        from asset_catalogue import catalogue,search
        from authoring_visuals import VisualSource,contact_sheet,animation_strip
        settings={'data':str(args.data)} if args.data else {}
        decoded=VisualSource(doc,settings).tiles if args.source in ('atlas','all') or args.data else None
        values=catalogue(doc,args.source,args.library,decoded)
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
        return event_graph(doc,args.output)
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
        if args.command=='suite':return run_suite(doc,read_json(args.file),args.file.parent,args.output,args.runner,settings,cancelled)
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
