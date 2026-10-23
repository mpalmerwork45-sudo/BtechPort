"""Changes, preservation and local authoring in one workspace page."""
import copy
import json
import os
from pathlib import Path
import re
import tkinter as tk
from tkinter import ttk,filedialog,simpledialog
import webbrowser

from authoring_contract import AuthoringError,read_json
from authoring_service import revision
from authoring_protection import rules,edit_rule
from editor_session import scope_of,guard
from editor_tasks import snapshot
from editor_workspace import view_window,open_view,workspace_of
from editor_ui import flow_toolbar
from editor_recovery import recoverable_forms
import authoring_review as review
import authoring_session as protocol


def text_box(parent,height=12):
    frame=ttk.Frame(parent);frame.pack(fill='both',expand=True)
    text=tk.Text(frame,wrap='word',height=height,width=24,font='TkDefaultFont',borderwidth=0,padx=8,pady=8)
    scroll=ttk.Scrollbar(frame,command=text.yview);scroll.pack(side='right',fill='y')
    text.configure(yscrollcommand=scroll.set);text.pack(fill='both',expand=True)
    return text


def fill(widget,value):
    widget.configure(state='normal');widget.delete('1.0','end');widget.insert('1.0',value);widget.configure(state='disabled')


def scrolling_tree(parent,expand=True,**options):
    host=ttk.Frame(parent);host.pack(fill='both' if expand else 'x',expand=expand)
    tree=ttk.Treeview(host,**options);scroll=ttk.Scrollbar(host,command=tree.yview)
    scroll.pack(side='right',fill='y');tree.configure(yscrollcommand=scroll.set)
    return tree


@recoverable_forms
class Changes:
    def __init__(self,owner):
        self.owner=owner;self.scope=scope_of(owner);self.document=owner.document
        self.workspace=workspace_of(owner);self.manager=self.workspace.authoring
        self.window=view_window(self,owner,'changes','Changes and authoring')
        self.folder=None;self.record=None;self.photos=[];self.last_session=None;self.selection_stamp=None
        self.status=tk.StringVar(value='Load a proposal to review its actual changes before applying.')
        footer=ttk.Frame(self.window,padding=8);footer.pack(side='bottom',fill='x')
        ttk.Label(footer,textvariable=self.status,wraplength=850).pack(fill='x')
        self.pages=ttk.Notebook(self.window);self.pages.pack(fill='both',expand=True,padx=8,pady=8)
        self.review_page=ttk.Frame(self.pages);self.protection_page=ttk.Frame(self.pages);self.session_page=ttk.Frame(self.pages)
        for page,title in [(self.review_page,'Review changes'),(self.protection_page,'Protected content'),(self.session_page,'Local session')]:self.pages.add(page,text=title)
        self.build_review();self.build_protection();self.build_session();self.refresh()
        self.timer=self.window.after(700,self.poll)

    def show_error(self,error):self.status.set(str(error))

    def button(self,parent,label,operation):
        button=ttk.Button(parent,text=label,width=0,command=lambda:guard(self,operation,publish=False));button.pack(side='left',padx=3,pady=3)
        return button

    def build_review(self):
        bar=ttk.Frame(self.review_page,padding=4);bar.pack(fill='x')
        self.button(bar,'Load commands...',self.load_file);self.button(bar,'Open review...',self.open_saved)
        self.button(bar,'Refresh',self.refresh);self.button(bar,'Cancel tasks',lambda:self.workspace.tasks.cancel(self.scope))
        flow_toolbar(bar)
        actions=ttk.Frame(self.review_page,padding=4);actions.pack(side='bottom',fill='x')
        self.apply_button=self.button(actions,'Apply changes',self.apply)
        self.button(actions,'Discard',lambda:self.decide('discard'));self.button(actions,'Request changes...',lambda:self.decide('request_changes'))
        self.button(actions,'Recheck groups',self.recheck);flow_toolbar(actions)
        body=ttk.Panedwindow(self.review_page,orient='horizontal');body.pack(fill='both',expand=True)
        left=ttk.Frame(body);right=ttk.Frame(body);body.add(left,weight=1);body.add(right,weight=4)
        compact=ttk.Frame(self.review_page,padding=4)
        self.compact_proposals=ttk.Combobox(compact,state='readonly',width=25);self.compact_proposals.pack(fill='x',expand=True)
        self.compact_proposals.bind('<<ComboboxSelected>>',lambda _:self.choose_compact())
        def resized(_):
            narrow=body.winfo_width()<700
            visible=str(left) in body.panes()
            if narrow and visible:
                body.forget(left);compact.pack(fill='x',before=body)
            elif not narrow and not visible:
                compact.pack_forget();body.insert(0,left,weight=1)
        body.bind('<Configure>',resized)
        self.proposals=scrolling_tree(left,columns=('status',),show='tree headings',height=8,selectmode='browse')
        self.proposals.heading('#0',text='Proposal');self.proposals.heading('status',text='Status')
        self.proposals.column('#0',width=175);self.proposals.column('status',width=90,stretch=False)
        self.proposals.pack(fill='both',expand=True);self.proposals.bind('<<TreeviewSelect>>',lambda _:guard(self,self.select,publish=False))
        self.detail=ttk.Notebook(right);self.detail.pack(fill='both',expand=True)
        summary=ttk.Frame(self.detail);diff=ttk.Frame(self.detail);maps=ttk.Frame(self.detail);events=ttk.Frame(self.detail);checks=ttk.Frame(self.detail)
        for page,title in [(summary,'Summary'),(diff,'Before / after'),(maps,'Maps'),(events,'Events'),(checks,'Checks')]:self.detail.add(page,text=title)
        from adventure_editor import scroll_frame
        summary_shell,summary_body=scroll_frame(summary,width=260,height=250);summary_shell.pack(fill='both',expand=True)
        self.summary_scroll=next(w for w in summary_shell.winfo_children() if isinstance(w,tk.Canvas))
        self.summary=text_box(summary_body,7)
        controls=ttk.Frame(summary_body);controls.pack(fill='x')
        ttk.Label(controls,text='Groups (Ctrl-click; required groups are included):',wraplength=420).pack(anchor='w',padx=6)
        self.groups=tk.Listbox(controls,selectmode='extended',exportselection=False,height=3);self.groups.pack(fill='x',padx=6,pady=4)
        ttk.Label(controls,text='Allow these protection exceptions for this application:',wraplength=420).pack(anchor='w',padx=6)
        self.overrides=tk.Listbox(controls,selectmode='extended',exportselection=False,height=2);self.overrides.pack(fill='x',padx=6,pady=(4,8))
        self.objects=scrolling_tree(diff,expand=False,columns=('change','fields'),show='tree headings',height=5,selectmode='browse')
        for key,title,width in [('#0','Object',230),('change','Change',70),('fields','Fields',170)]:self.objects.heading(key,text=title);self.objects.column(key,width=width)
        self.objects.pack(fill='x');self.objects.bind('<<TreeviewSelect>>',lambda _:self.show_diff())
        pair=ttk.Panedwindow(diff,orient='horizontal');pair.pack(fill='both',expand=True);self.diffs={}
        for side in ('before','after'):
            host=ttk.Frame(pair);pair.add(host,weight=1);ttk.Label(host,text=side.title(),style='Section.TLabel').pack(anchor='w',padx=8,pady=4)
            self.diffs[side]=text_box(host)
        self.map_id=tk.StringVar();self.map_choice=ttk.Combobox(maps,textvariable=self.map_id,state='readonly')
        self.map_choice.pack(fill='x',padx=6,pady=6);self.map_choice.bind('<<ComboboxSelected>>',lambda _:guard(self,self.show_maps,publish=False))
        pair=ttk.Panedwindow(maps,orient='horizontal');pair.pack(fill='both',expand=True);self.canvases={};self.zooms={}
        from editor_canvas import CanvasZoom
        for side in ('before','after'):
            host=ttk.Frame(pair);pair.add(host,weight=1);bar=ttk.Frame(host);bar.pack(fill='x')
            ttk.Label(bar,text=side.title(),style='Section.TLabel').pack(side='left',padx=6)
            scale=tk.StringVar(value='1');self.zooms[side]=scale
            control=CanvasZoom(bar,scale,self.show_maps,base=2,steps=(1,2,3,4));control.pack(side='right')
            area=ttk.Frame(host);area.pack(fill='both',expand=True)
            canvas=tk.Canvas(area,background='#dce3e7',highlightthickness=0)
            sy=ttk.Scrollbar(area,command=canvas.yview);sy.pack(side='right',fill='y')
            sx=ttk.Scrollbar(area,orient='horizontal',command=canvas.xview);sx.pack(side='bottom',fill='x')
            canvas.configure(xscrollcommand=sx.set,yscrollcommand=sy.set);canvas.pack(fill='both',expand=True);control.attach(canvas)
            self.canvases[side]=canvas
        pair=ttk.Panedwindow(events,orient='horizontal');pair.pack(fill='both',expand=True);self.routes={}
        for side in ('before','after'):
            host=ttk.Frame(pair);pair.add(host,weight=1);ttk.Label(host,text=side.title(),style='Section.TLabel').pack(anchor='w',padx=6,pady=6);self.routes[side]=text_box(host)
        from editor_review_checks import ReviewChecksPane
        self.review_checks=ReviewChecksPane(self,checks);self.checks=self.review_checks.reports
        from editor_world_review import WorldReviewPane
        self.worlds_page=ttk.Frame(self.detail);self.detail.add(self.worlds_page,text='Worlds')
        self.world_review=WorldReviewPane(self,self.worlds_page)

    def build_protection(self):
        bar=ttk.Frame(self.protection_page,padding=6);bar.pack(fill='x')
        self.button(bar,'Add protection...',self.protection_form);self.button(bar,'Edit selected...',lambda:self.protection_form(True));self.button(bar,'Remove selected',self.remove_protection)
        flow_toolbar(bar)
        ttk.Label(self.protection_page,text='Protect whole objects, selected fields, local map rectangles or world regions from generated batches. World regions also protect overlapping town tiles and shared tile artwork. Manual editing remains available. Changes use Undo and Save.',wraplength=800,padding=8).pack(fill='x')
        self.protected=scrolling_tree(self.protection_page,columns=('kind','target'),show='tree headings',selectmode='browse')
        for key,label,width in [('#0','Keep',200),('kind','Rule',90),('target','Object / region',400)]:self.protected.heading(key,text=label);self.protected.column(key,width=width)
        self.protected.pack(fill='both',expand=True,padx=8,pady=8)

    def build_session(self):
        from adventure_editor import scroll_frame
        footer=ttk.Frame(self.session_page,padding=6);footer.pack(side='bottom',fill='x')
        self.button(footer,'Start session',self.start_session);self.button(footer,'Stop session',self.stop_session)
        self.button(footer,'Copy connection path',self.copy_connection);self.button(footer,'Cancel selected job',self.cancel_job);flow_toolbar(footer)
        shell,body=scroll_frame(self.session_page);shell.pack(fill='both',expand=True)
        ttk.Label(body,text='Local authoring uses an explicit snapshot of this editing scope, including valid forms. External tools submit proposals here; no model or network service runs in the editor.',wraplength=800,padding=8).pack(fill='x')
        self.session_values={}
        for key,label,default in [('brief','Brief',''),('constraints','Constraints (one per line)',''),('scope','Allowed write scope (one path per line)','*')]:
            ttk.Label(body,text=label,padding=(8,4)).pack(anchor='w')
            field=tk.Text(body,height=2,width=60,wrap='word',font='TkDefaultFont');field.pack(fill='x',padx=8);field.insert('1.0',default);self.session_values[key]=field
        row=ttk.Frame(body,padding=8);row.pack(fill='x');ttk.Label(row,text='Application policy').pack(side='left')
        self.policy=tk.StringVar(value='Review each proposal');ttk.Combobox(row,textvariable=self.policy,state='readonly',values=['Review each proposal','Apply within declared scope'],width=30).pack(side='left',padx=10)
        self.connection=tk.StringVar(value='No active session.');ttk.Label(body,textvariable=self.connection,wraplength=800,padding=8).pack(fill='x')
        self.jobs=scrolling_tree(body,columns=('kind','status'),show='tree headings',height=8,selectmode='browse')
        for key,label,width in [('#0','Job',280),('kind','Work',100),('status','Status',140)]:self.jobs.heading(key,text=label);self.jobs.column(key,width=width)
        self.jobs.pack(fill='both',expand=True,padx=8,pady=6);self.jobs.bind('<Double-1>',lambda _:guard(self,self.open_job,publish=False))

    def refresh(self):
        selected=str(self.folder) if self.folder else None
        self.proposals.delete(*self.proposals.get_children())
        for path,record in self.manager.proposals(self.scope):
            self.proposals.insert('','end',iid=str(path),text=record['request']['label'],values=(record['status'],))
        self.compact_paths=list(self.proposals.get_children())
        self.compact_proposals.configure(values=[self.proposals.item(p,'text')+' — '+self.proposals.item(p,'values')[0] for p in self.compact_paths])
        if selected and self.proposals.exists(selected):self.proposals.selection_set(selected)
        elif self.proposals.get_children():self.proposals.selection_set(self.proposals.get_children()[0])
        self.protected.delete(*self.protected.get_children())
        for rule in rules(self.document):
            target=rule.get('path',rule.get('world',rule.get('map','')))+(' '+str(rule['rect']) if 'rect' in rule else ' '+', '.join(rule.get('fields',[])))
            self.protected.insert('','end',iid=rule['id'],text=rule['label'],values=(rule['kind'],target))
        self.select();self.refresh_jobs()

    def choose_compact(self):
        index=self.compact_proposals.current()
        if 0<=index<len(self.compact_paths):
            self.proposals.selection_set(self.compact_paths[index]);self.select()

    def selected(self):
        if self.folder is None:raise AuthoringError('review.unavailable','Select a proposal first.')
        return review.read(self.folder)

    def select(self):
        choices=self.proposals.selection()
        if not choices:return
        self.folder=Path(choices[0]);record=self.record=review.read(self.folder)
        if choices[0] in self.compact_paths:self.compact_proposals.current(self.compact_paths.index(choices[0]))
        stamp=(str(self.folder),record)
        if stamp==self.selection_stamp:return
        self.selection_stamp=copy.deepcopy(stamp)
        lines=[record['request']['label'],'Status: '+record['status'],'Base revision: '+record['base_revision'][:16],
               'Write scope: '+', '.join(record['allowed_scope']),record.get('brief',''),*record.get('constraints',[])]
        lines+=['',f"{len(record['changes'])} changed objects; {len(record['conflicts'])} protection conflicts."]
        lines.extend(p['message'] for p in record['diagnostics'])
        lines.extend(c['message'] for c in record['conflicts'])
        if record.get('displaced_details'):lines+=['Hand-painted construction details displaced: '+json.dumps(record['displaced_details'])]
        if record.get('dependency_before')!=record.get('dependency_after'):lines+=['Dependencies/provenance changed; inspect Checks / artifacts for both records.']
        fill(self.summary,'\n'.join(lines))
        self.groups.delete(0,'end')
        for i,group in enumerate(record['groups']):
            self.groups.insert('end',group['label']+(' — requires '+', '.join(group['requires']) if group.get('requires') else ''))
            if group['id'] in record['selected']:self.groups.selection_set(i)
        self.overrides.delete(0,'end')
        for conflict in record['conflicts']:self.overrides.insert('end',conflict['label']+' ['+conflict['rule']+']')
        self.apply_button.state(['!disabled'] if record['status'] in ('ready','conflicts') else ['disabled'])
        self.objects.delete(*self.objects.get_children())
        for i,change in enumerate(record['changes']):self.objects.insert('','end',iid=str(i),text=change['path'],values=(change['change'],', '.join(change['fields'])))
        if record['changes']:self.objects.selection_set('0');self.show_diff()
        maps=list(dict.fromkeys(a['id'] for a in record['artifacts'] if a['kind']=='map'));self.map_choice.configure(values=maps)
        if self.map_id.get() not in maps:self.map_id.set(maps[0] if maps else '')
        self.show_maps();self.show_routes()
        self.world_review.load(record,self.folder)
        self.review_checks.load(record,self.folder)
        fill(self.checks,json.dumps(dict(validation=record.get('result',{}).get('validation'),checks=record.get('checks',[]),
            dependencies_before=record.get('dependency_before'),dependencies_after=record.get('dependency_after'),
            artifacts=[a.get('artifact') for a in record['artifacts']],diagnostics=record['diagnostics']),indent=2))

    def show_diff(self):
        selected=self.objects.selection()
        if not selected or not self.record:return
        change=self.record['changes'][int(selected[0])]
        for side in ('before','after'):fill(self.diffs[side],change[side])

    def show_maps(self):
        self.photos=[]
        for side,canvas in self.canvases.items():
            canvas.delete('all')
            found=next((a for a in (self.record or {}).get('artifacts',[]) if a['kind']=='map' and a['side']==side and a['id']==self.map_id.get()),None)
            if not found:canvas.create_text(12,15,anchor='nw',text='No changed map preview for this side.',width=280);continue
            artifact=found['artifact'];body=Path(artifact['path']).read_text();match=re.search(r'href="data:image/png;base64,([^"]+)"',body)
            if not match:continue
            original=tk.PhotoImage(master=self.window,data=match[1],format='png');step=int(self.zooms[side].get())
            photo=original.zoom(step).subsample(2);self.photos.append(photo)
            canvas.create_image(0,0,anchor='nw',image=photo);canvas.configure(scrollregion=(0,0,photo.width(),photo.height()))
            for marker in artifact.get('markers',[]):
                x,y=marker['at'];scale=step/2;x=x*8*scale;y=y*8*scale
                canvas.create_rectangle(x-2,y-2,x+2,y+2,fill='#ffff55',outline='#17232d')
        self.status.set('Map previews use the exact before/after tile pixels. Ctrl + wheel zooms; scroll to compare edges.')

    def show_routes(self):
        from event_editing import edges
        for side in ('before','after'):
            manifest=self.folder/side/'project.json'
            if not manifest.exists():fill(self.routes[side],'No retained candidate.');continue
            package=read_json(manifest);name=package.get('adventure')
            events=read_json(self.folder/side/name)['events'] if name else []
            fill(self.routes[side],'\n\n'.join(e['id']+' — '+e['op']+'\n'+ '\n'.join('  '+branch+' → '+target for branch,target in edges(e)) for e in events))

    def load_file(self,path=None):
        path=path or filedialog.askopenfilename(parent=self.window,title='Review authoring command file',filetypes=[('JSON commands','*.json')])
        if not path:return
        path=Path(path);job,self.folder=self.manager.prepare(self.scope,read_json(path),base_dir=path.parent,finished=self.prepared);return job

    def prepared(self,result,folder):
        # Treeview selection events from the previous proposal can arrive while
        # the worker prepares the replacement. Select its completed record,
        # without activating the tab or stealing focus from other editing.
        if self.window.winfo_exists():
            self.folder=Path(folder);self.selection_stamp=None;self.refresh()

    def open_saved(self,path=None):
        path=path or filedialog.askdirectory(parent=self.window,title='Open directory containing review.json')
        if not path:return
        record=review.read(path)
        if record['project_root']!=str(self.document.root):raise AuthoringError('project.mismatch','This review belongs to another project or library scope.')
        self.folder=Path(path);self.manager.remember(path);self.refresh()

    def apply(self):
        record=self.selected();overrides=[record['conflicts'][i]['rule'] for i in self.overrides.curselection()]
        chosen=[record['groups'][i]['id'] for i in self.groups.curselection()]
        if set(chosen)!=set(record['selected']):raise AuthoringError('review.unchecked_groups','Recheck the selected groups before applying; the visible proposal must match the accepted selection.')
        return self.manager.apply(self.scope,self.folder,overrides)

    def decide(self,action):
        self.selected();note=''
        if action=='request_changes':
            note=simpledialog.askstring('Request a narrower revision','Describe what should be revised or retained:',parent=self.window)
            if note is None:return
        review.decide(self.folder,action,note);self.refresh()

    def recheck(self):
        record=self.selected();candidate=snapshot(self.scope)
        if revision(candidate)!=record['base_revision']:raise AuthoringError('revision.conflict','The project changed. Take a fresh snapshot and revise the request before rechecking.')
        chosen=[record['groups'][i]['id'] for i in self.groups.curselection()]
        job,self.folder=self.manager.prepare(self.scope,record['request'],selected=chosen,allowed_scope=record['allowed_scope'],retained_imports=review.import_paths(self.folder,record),finished=self.prepared);return job

    def check(self,suite=False):
        if suite:return self.review_checks.choose()
        self.selected()
        folder=self.folder;settings=dict(self.owner.settings);suffix='.exe' if os.name=='nt' else '';build=Path(__file__).resolve().parents[1]/'build'
        def done(result):self.manager.notify(self.scope);self.owner.status.set('Proposed game check: '+result['status'])
        return self.workspace.tasks.submit('Check proposed game',self.scope.owner,
            lambda cancel:review.check_candidate(folder,self.document.validator,settings=settings,analyzer=build/('btp-author-analyze'+suffix),runner=build/('btp-author-playtest'+suffix),cancelled=cancel.is_set),done)

    def open_artifacts(self):
        self.selected();webbrowser.open(self.folder.as_uri())

    def protection_form(self,edit=False,initial=None):
        from adventure_editor import Form
        current=next((r for r in rules(self.document) if self.protected.selection() and r['id']==self.protected.selection()[0]),None) if edit else None
        if edit and current is None:raise AuthoringError('object.missing','Select a protection rule.')
        current=current or dict(id='keep-'+str(len(rules(self.document))+1),label='Keep manual work',kind='object')
        if initial:current.update(initial)
        paths=[]
        for section in ('content','adventure','art'):
            for key,values in (getattr(self.document,section) or {}).items():
                if isinstance(values,list):paths.extend(section+'.'+key+'/'+v['id'] for v in values if isinstance(v,dict) and 'id' in v)
        scenes=(self.document.adventure or {}).get('maps',[])
        paths.extend('adventure.entrances/'+d['id'] for m in scenes for d in m['entrances'])
        form=Form(self,'Protect authored content')
        form.field('id',current['id']);form.field('label',current['label']);form.field('kind',current['kind'],['object','fields','map_region','world_region'])
        form.field('path',current.get('path',paths[0] if paths else ''),paths,label='Object (object / fields rules)')
        form.field('fields',', '.join(current.get('fields',['text'])),label='Fields or JSON pointers, comma separated')
        form.field('map',current.get('map',scenes[0]['id'] if scenes else ''),[m['id'] for m in scenes],label='Map (map_region)')
        from world_editing import all_worlds
        worlds=all_worlds(self.document.adventure or {})
        form.field('world',current.get('world',worlds[0]['id'] if worlds else ''),[w['id'] for w in worlds],label='Planet (world_region)')
        form.field('rect',', '.join(map(str,current.get('rect',[0,0,1,1]))),label='Tile rectangle: x, y, width, height')
        def apply(values):
            rule={k:values[k] for k in ('id','label','kind')}
            if rule['kind'] in ('map_region','world_region'):
                field='map' if rule['kind']=='map_region' else 'world';rule.update({field:values[field]},rect=[int(v.strip()) for v in values['rect'].split(',')])
            else:
                rule['path']=values['path']
                if rule['kind']=='fields':rule['fields']=[v.strip() for v in values['fields'].split(',') if v.strip()]
            if edit and rule['id']!=current['id']:raise AuthoringError('identity.immutable','Keep the rule ID when editing; add another rule to clone it.')
            edit_rule(self.document,rule);self.refresh()
        form.submit(apply);return form

    def remove_protection(self):
        selected=self.protected.selection()
        if not selected:raise AuthoringError('object.missing','Select a protection rule.')
        edit_rule(self.document,remove=selected[0]);self.refresh()

    def start_session(self):
        values={k:w.get('1.0','end-1c').strip() for k,w in self.session_values.items()}
        self.last_session=self.manager.start(self.scope,brief=values['brief'],constraints=values['constraints'].splitlines(),allowed_scope=values['scope'].splitlines(),
            policy='review' if self.policy.get()=='Review each proposal' else 'apply_within_scope')
        self.refresh_jobs();return self.last_session

    def stop_session(self):self.manager.stop(self.scope);self.refresh_jobs()

    def refresh_jobs(self):
        connection=self.manager.sessions.get(id(self.scope))
        if connection:self.last_session=connection['folder']
        if not self.last_session:
            root=self.workspace.state_dir/'authoring-sessions'
            for file in sorted(root.glob('*/session.json'),key=lambda p:p.stat().st_mtime,reverse=True):
                if read_json(file).get('project_root')==str(self.document.root):self.last_session=file.parent;break
        if not self.last_session:return
        record=protocol.info(self.last_session);self.connection.set(record['status'].title()+' — '+str(self.last_session)+'\nScope: '+record['scope_kind']+' | '+', '.join(record['allowed_scope']))
        selected=self.jobs.selection();self.jobs.delete(*self.jobs.get_children())
        for job in protocol.jobs(self.last_session):self.jobs.insert('','end',iid=job['id'],text=job['id'],values=(job['kind'],job['status']))
        if selected and self.jobs.exists(selected[0]):self.jobs.selection_set(selected[0])

    def copy_connection(self):
        if not self.last_session:raise AuthoringError('session.disconnected','Start a session first.')
        self.window.clipboard_clear();self.window.clipboard_append(str(self.last_session));self.status.set('Local session path copied.')

    def cancel_job(self):
        if not self.last_session or not self.jobs.selection():raise AuthoringError('object.missing','Select a local authoring job.')
        protocol.cancel(self.last_session,self.jobs.selection()[0]);self.status.set('Cancellation requested for this job.')

    def open_job(self):
        if not self.jobs.selection():return
        job=read_json(protocol.job_folder(self.last_session,self.jobs.selection()[0])/'job.json')
        if job.get('review'):self.open_saved(job['review']);self.pages.select(self.review_page)
        else:self.status.set(json.dumps(job.get('result',job)))

    def poll(self):
        self.timer=None
        if self.window.winfo_exists():
            self.refresh_jobs();self.timer=self.window.after(700,self.poll)


def open_changes(owner,session=False):
    view=open_view(owner,'changes',lambda:Changes(owner))
    if session:view.pages.select(view.session_page)
    return view
