"""The editor owns live authoring; workers receive detached data only.

Closing a review tab leaves its proposal on disk. Closing/replacing its scope
stops the connection and cancels unfinished jobs. The ordinary Save and Play
controllers remain independent of the local authoring inbox.
"""
import copy
from pathlib import Path
import time
import uuid

from authoring_contract import AuthoringError,diagnostic,read_json
from authoring_service import revision
from editor_tasks import snapshot,signature
from editor_history import refresh_scope
from editor_model import ProjectDocument,encoded
import authoring_review as review
import authoring_session as protocol


class Authoring:
    def __init__(self,workspace):
        self.workspace=workspace;self.sessions={};self.active={};self.paths=[]
        self.index=workspace.state_dir/'authoring-reviews.json'
        try:self.paths=read_json(self.index)
        except (OSError,ValueError,AuthoringError):pass

    def remember(self,path):
        value=str(Path(path).resolve())
        self.paths=[value]+[p for p in self.paths if p!=value]
        self.paths=self.paths[:512];self.index.parent.mkdir(parents=True,exist_ok=True)
        ProjectDocument.atomic_file(self.index,encoded(self.paths))

    def notify(self,scope):
        pane=self.workspace.views.get((id(scope),'changes',None))
        if pane and pane.winfo_exists():pane.controller.refresh()

    def new_folder(self):
        return self.workspace.state_dir/'authoring-reviews'/uuid.uuid4().hex

    def proposals(self,scope):
        result=[]
        for path in self.paths:
            try:
                record=review.read(path)
                if record['project_root']==str(scope.document.root):result.append((Path(path),record))
            except (OSError,ValueError,AuthoringError):continue
        return result

    def prepare(self,scope,request,*,base_dir=None,folder=None,selected=None,allowed_scope=None,retained_imports=None,finished=None):
        candidate=snapshot(scope);stamp=signature(scope);folder=folder or self.new_folder();settings=dict(scope.owner.settings)
        self.remember(folder)
        def done(result):
            if stamp!=signature(scope) and result['status'] in ('ready','conflicts'):
                result['status']='stale';result['diagnostics'].append(diagnostic(AuthoringError('revision.conflict','The editor changed while the proposal was prepared. Request a revision against a fresh snapshot.')))
                review.write(folder,result)
            self.notify(scope)
            scope.owner.status.set('Proposal '+result['status']+'. Open Changes to review it.')
            if finished:finished(result,folder)
        def fail(error):
            try:
                result=review.read(folder)
                result['status']='cancelled' if job.cancelled.is_set() else 'failed';result['diagnostics'].append(diagnostic(error));review.write(folder,result)
            except (OSError,ValueError):result=dict(status='failed',diagnostics=[diagnostic(error)])
            scope.owner.status.set(str(error));self.notify(scope)
            if finished:finished(result,folder)
        job=self.workspace.tasks.submit('Prepare authoring review',scope.owner,
            lambda cancel:review.prepare(candidate,request,folder,base_dir=base_dir,selected=selected,settings=settings,
                allowed_scope=allowed_scope,retained_imports=retained_imports,cancelled=cancel.is_set),done,fail)
        return job,folder

    def apply(self,scope,folder,overrides=(),finished=None):
        candidate=snapshot(scope);stamp=signature(scope)
        def done(prepared):
            if signature(scope)!=stamp:raise AuthoringError('revision.conflict','Human work changed while the application was checked. Request a fresh proposal.')
            # Commit valid human drafts first, as their own history step. The
            # following Undo then reverses only generated changes.
            scope.transact(lambda:None)
            result=review.publish(scope.document,folder,prepared)
            refresh_scope(self.workspace,scope);scope.seen_revision=(id(scope.document),scope.document.revision)
            self.workspace.recovery.write(scope,background=True)
            scope.owner.status.set('Proposal applied. Undo reverses this batch; Save publishes it.')
            self.notify(scope)
            if finished:finished(dict(status='applied',result=result),folder)
        def fail(error):
            scope.owner.status.set(str(error));self.notify(scope)
            if finished:finished(dict(status='failed',diagnostics=[diagnostic(error)]),folder)
            else:
                from editor_session import report
                report(scope.owner,error,category='authoring')
        return self.workspace.tasks.submit('Check reviewed application',scope.owner,
            lambda cancel:review.prepare_apply(candidate,folder,overrides=overrides,cancelled=cancel.is_set),done,fail)

    def start(self,scope,**options):
        candidate=snapshot(scope);self.stop(scope)
        folder=self.workspace.state_dir/'authoring-sessions'/uuid.uuid4().hex
        record=protocol.create(candidate,folder,scope_kind='library' if getattr(scope.owner,'library_context',None) else 'project',**options)
        self.sessions[id(scope)]=dict(scope=scope,folder=folder,document=id(scope.document),root=str(scope.document.root),record=record)
        self.notify(scope);return folder

    def stop(self,scope=None):
        for key,connection in list(self.sessions.items()):
            if scope is not None and connection['scope'] is not scope:continue
            folder=connection['folder'];record=connection['record'];record.update(status='stopped',heartbeat=time.time());protocol.write(folder/'session.json',record)
            for item in protocol.jobs(folder):
                if item['status'] in ('queued','running','interrupted'):
                    protocol.cancel(folder,item['id'])
                    task=self.active.get((str(folder),item['id']))
                    if task:task.cancelled.set()
                    item['status']='cancelled';protocol.write(protocol.job_folder(folder,item['id'])/'job.json',item)
            self.sessions.pop(key,None)

    def poll(self):
        for connection in list(self.sessions.values()):
            scope=connection['scope'];folder=connection['folder'];record=connection['record']
            if not scope.owner.window.winfo_exists() or id(scope.document)!=connection['document'] or str(scope.document.root)!=connection['root']:
                self.stop(scope);continue
            if time.time()-record['heartbeat']>=2:
                record['heartbeat']=time.time();protocol.write(folder/'session.json',record)
            for item in protocol.jobs(folder):
                target=protocol.job_folder(folder,item['id']);key=(str(folder),item['id'])
                task=self.active.get(key)
                if task and (target/'cancel.json').exists():task.cancelled.set()
                if item['status']!='queued' or not (target/'command.json').is_file():continue
                if (target/'cancel.json').exists():
                    item['status']='cancelled';protocol.write(target/'job.json',item);continue
                if len(self.workspace.tasks.jobs)>=8:continue
                self.launch(connection,item,target,key)

    def launch(self,connection,item,target,key):
        scope=connection['scope'];session=connection['record'];folder=connection['folder']
        item=dict(item,status='running');protocol.write(target/'job.json',item)
        def finish(result,review_folder=None):
            self.active.pop(key,None)
            if result['status']!='applied' and ((target/'cancel.json').exists() or id(scope) not in self.sessions):
                result=dict(status='cancelled',diagnostics=result.get('diagnostics',[]))
            # The complete proposal already lives in review.json. Keep the job
            # queue compact even for large map revisions and retained checks.
            summary={k:v for k,v in result.items() if k in ('status','diagnostics','snapshot','revision','summary','result_revision','conflicts')}
            value=dict(item,status=result['status'],result=summary,finished=time.time())
            if review_folder:value['review']=str(review_folder)
            protocol.write(target/'job.json',value);self.notify(scope)
        try:
            command=read_json(target/'command.json')
            if command['kind']=='snapshot':
                candidate=snapshot(scope);stamp=signature(scope)
                def work(cancel):
                    from authoring_inspect import summary
                    candidate.validate()
                    if cancel.is_set():raise AuthoringError('job.cancelled','Snapshot cancelled.')
                    destination=target/'snapshot';destination.mkdir();candidate.stage(destination)
                    return dict(status='completed',snapshot=str(destination),revision=revision(candidate),summary=summary(candidate,candidate.validator))
                def done(result):
                    if stamp!=signature(scope):result=dict(result,status='stale',diagnostics=[diagnostic(AuthoringError('revision.conflict','Editor changed while taking the snapshot; request another.'))])
                    finish(result)
                task=self.workspace.tasks.submit('Authoring snapshot',scope.owner,work,done,
                    lambda error:finish(dict(status='failed',diagnostics=[diagnostic(error)])))
            elif command['kind']=='propose':
                def proposed(result,path):
                    if result['status']=='ready' and session['policy']=='apply_within_scope' and not (target/'cancel.json').exists() and id(scope) in self.sessions:
                        self.active[key]=self.apply(scope,path,finished=finish)
                    else:finish(result,path)
                request=copy.deepcopy(command['request'])
                # Session constraints travel with the review even when an
                # external client omitted its own prose description.
                request.setdefault('brief',session['brief']);request.setdefault('constraints',session['constraints'])
                task,_=self.prepare(scope,request,folder=target/'review',allowed_scope=session['allowed_scope'],
                    retained_imports=review.import_paths(target,command),finished=proposed)
            else:raise AuthoringError('session.invalid','Unsupported local session job.')
            self.active[key]=task
        except Exception as error:finish(dict(status='failed',diagnostics=[diagnostic(error)]))
