"""Test authoring and coverage in one ordinary, recoverable workspace tab."""
import copy
import json
import os
from pathlib import Path
import uuid
import tkinter as tk
from tkinter import ttk,filedialog

from adventure_editor import Form
from editor_model import EditorError
from editor_session import scope_of,guard,report
from editor_tasks import snapshot,signature
from editor_ui import flow_toolbar
from editor_workspace import view_window,open_view,workspace_of
from editor_recovery import recoverable_forms
import suite_authoring as model

STEP_KINDS=('pages','walk entrance','walk map','walk world','choose','enter','battle','assert objective','assert map','assert phase','checkpoint','input','capture','advanced JSON')


@recoverable_forms
class Suites:
    def __init__(self,owner):
        self.owner=owner;self.scope=scope_of(owner);self.workspace=workspace_of(owner);self.document=self.scope.document
        self.window=view_window(self,owner,'suites','Test suites and coverage')
        self.current=None;self.current_case=None;self.inventory=None;self.run_stamp=None;self.job=None;self.generation=0
        self.status=tk.StringVar(value='Create or import a suite. Starter cases are unverified until run. Save stores definitions with the project.')
        top=ttk.Frame(self.window,padding=6);top.pack(fill='x')
        self.choice=ttk.Combobox(top,state='readonly',width=25);self.choice.pack(side='left');self.choice.bind('<<ComboboxSelected>>',lambda _:self.select_suite())
        for label,action in [('New suite',self.suite_form),('Properties',lambda:self.suite_form(True)),('Import...',self.import_file),('Export...',self.export),('Remove suite',self.remove_suite)]:self.button(top,label,action)
        flow_toolbar(top)
        self.pages=ttk.Notebook(self.window);self.pages.pack(fill='both',expand=True,padx=6)
        cases=ttk.Frame(self.pages);steps=ttk.Frame(self.pages);coverage=ttk.Frame(self.pages)
        self.pages.add(cases,text='Cases');self.pages.add(steps,text='Steps');self.pages.add(coverage,text='Coverage and failures')
        self.coverage_note=tk.StringVar(value='Inspect dependencies or run a suite. Declared dependencies alone are not coverage.')
        note=ttk.Label(coverage,textvariable=self.coverage_note,padding=6,wraplength=480);note.pack(fill='x')
        note.bind('<Configure>',lambda e:note.configure(wraplength=max(180,e.width-12)),add='+')
        bar=ttk.Frame(cases);bar.pack(fill='x')
        for label,action in [('Add case',self.case_form),('Edit case',lambda:self.case_form(True)),('Clone',self.clone_case),('Remove',self.remove_case),('Run selected',self.run_selected),('Run full suite',lambda:self.run_selected(True)),('Cancel',self.cancel)]:self.button(bar,label,action)
        flow_toolbar(bar)
        self.cases=self.table(cases,('source','seeds','status'),('Scenario / setup','Seeds','Last retained run'))
        self.cases.configure(selectmode='extended')
        self.cases.bind('<<TreeviewSelect>>',lambda _:self.select_case());self.cases.bind('<Double-1>',lambda _:self.pages.select(1))
        self.case_label=tk.StringVar();ttk.Label(steps,textvariable=self.case_label,padding=6).pack(fill='x')
        bar=ttk.Frame(steps);bar.pack(fill='x')
        self.step_kind=ttk.Combobox(bar,values=STEP_KINDS,state='readonly',width=18);self.step_kind.set('walk entrance');self.step_kind.pack(side='left')
        for label,action in [('Add step',self.step_form),('Edit step',lambda:self.step_form(True)),('Up',lambda:self.move_step(-1)),('Down',lambda:self.move_step(1)),('Remove step',self.remove_step)]:self.button(bar,label,action)
        flow_toolbar(bar);self.steps=self.table(steps,('description',),('Ordinary input / assertion',))
        self.steps.bind('<Double-1>',lambda _:guard(self,lambda:self.step_form(True)))
        bar=ttk.Frame(coverage);bar.pack(fill='x')
        for label,action in [('Inspect dependencies',lambda:self.run_selected(inspect=True)),('Load retained coverage...',self.load_report),('Go to selected',self.navigate)]:self.button(bar,label,action)
        flow_toolbar(bar);self.coverage=self.table(coverage,('declared','observed'),('Declared dependency','Observed in retained run'))
        self.coverage.bind('<Double-1>',lambda _:guard(self,self.navigate));self.targets={}
        note=ttk.Label(self.window,textvariable=self.status,padding=8,wraplength=750);note.pack(fill='x')
        note.bind('<Configure>',lambda e:note.configure(wraplength=max(200,e.width-16)),add='+')
        self.window.bind('<Destroy>',self.destroyed,add='+');self.refresh()

    def table(self,parent,columns,titles):
        host=ttk.Frame(parent);host.pack(fill='both',expand=True)
        table=ttk.Treeview(host,columns=columns,show='tree headings',selectmode='browse',height=6)
        table.heading('#0',text='Case / object');table.column('#0',width=210,minwidth=90)
        for key,title in zip(columns,titles):table.heading(key,text=title);table.column(key,width=190,minwidth=70)
        sy=ttk.Scrollbar(host,command=table.yview);sy.pack(side='right',fill='y')
        sx=ttk.Scrollbar(host,orient='horizontal',command=table.xview);sx.pack(side='bottom',fill='x')
        table.configure(yscrollcommand=sy.set,xscrollcommand=sx.set);table.pack(fill='both',expand=True);return table

    def button(self,parent,title,action):
        button=ttk.Button(parent,text=title,command=lambda:guard(self,action,publish=False));button.pack(side='left',padx=3,pady=3);return button

    def show_error(self,error):self.status.set(str(error))
    def destroyed(self,event):
        if event.widget==self.window:self.generation+=1;self.cancel()
    def cancel(self):
        if self.job:self.job.cancelled.set();self.status.set('Cancellation requested; completed artifacts remain available.')
    def suite(self):
        value=next((s for s in model.suites(self.document) if s['id']==self.current),None)
        if value is None:raise EditorError('Create or select a test suite first.')
        return value
    def case(self):
        value=next((c for c in self.suite()['cases'] if c['id']==self.current_case),None)
        if value is None:raise EditorError('Select a case first.')
        return value
    def select_suite(self):
        self.current=self.ids[self.choice.current()];self.current_case=None;self.refresh()
    def select_case(self):
        selected=self.cases.selection()
        if selected:self.current_case=selected[0]
        self.draw_steps()
    def refresh(self):
        self.document=self.scope.document;items=model.suites(self.document);self.ids=[s['id'] for s in items]
        if self.current not in self.ids:self.current=self.ids[0] if self.ids else None
        self.choice['values']=[s['name']+' ('+s['id']+')' for s in items]
        if self.current:self.choice.current(self.ids.index(self.current))
        else:self.choice.set('No suites yet')
        self.cases.delete(*self.cases.get_children())
        if self.current:
            value=self.suite()
            historical=self.run_stamp!=signature(self.scope)
            for case in value['cases']:
                evidence=next((c for c in (self.inventory or {}).get('cases',[]) if c['id']==case['id']),{}) if (self.inventory or {}).get('suite_id')==self.current else {}
                status=evidence.get('status','not_run').replace('_',' ')
                if evidence and historical:status+=' (earlier draft)'
                scenario=case.get('scenario',{});setup='checkpoint' if scenario.get('checkpoint') else 'fixture' if case.get('fixture') or case.get('fixture_commands') else 'new game'
                self.cases.insert('','end',iid=case['id'],text=case['id'],values=(case.get('file','Project steps')+' / '+setup,
                    ', '.join(map(str,case.get('seeds',[scenario.get('seed',model.DEFAULT_SEED)]))) if not scenario.get('checkpoint') else 'Saved RNG',status))
            if self.current_case not in self.cases.get_children():self.current_case=next(iter(self.cases.get_children()),None)
            if self.current_case:self.cases.selection_set(self.current_case)
        self.draw_steps();self.draw_coverage()

    def save_suite(self,value,previous):model.put(self.document,value,previous);self.current=value['id']
    def suite_form(self,edit=False):
        value=self.suite() if edit else dict(id='regression',name='Regression',max_seconds=180,cases=[]);previous=value['id'] if edit else None
        form=Form(self,'Test suite');form.field('id',value['id']);form.field('name',value['name']);form.field('max_seconds',value.get('max_seconds',180))
        def apply(v):
            current=next((s for s in model.suites(self.document) if s['id']==previous),value)
            self.save_suite(dict(current,id=v['id'],name=v['name'],max_seconds=int(v['max_seconds'])),previous)
        form.submit(apply);return form
    def remove_suite(self):model.remove(self.document,self.suite()['id']);self.refresh()
    def import_file(self,path=None):
        path=path or filedialog.askopenfilename(parent=self.window,title='Import scenario suite',filetypes=[('JSON','*.json')])
        if not path:return
        identity='suite-'+uuid.uuid4().hex[:8];value=model.import_suite(path,identity)
        model.put(self.document,value);self.current=identity;self.refresh()
    def case_form(self,edit=False):
        suite_id=self.suite()['id'];value=self.case() if edit else dict(id='case-'+str(len(self.suite()['cases'])+1))
        previous=value['id'] if edit else None;scenario=value.get('scenario',{})
        form=Form(self,'Scenario case');form.field('id',value['id']);form.field('seeds',', '.join(map(str,value.get('seeds',[]))),label='Seeds (blank = scenario/default or saved RNG)')
        form.field('tags',', '.join(value.get('tags',[])));form.field('file',value.get('file',''),label='External scenario file (blank = project steps)')
        form.field('setup','Imported fixture' if value.get('fixture_commands') else 'Fixture file' if value.get('fixture') else 'New game',choices=['New game','Imported fixture','Fixture file'])
        form.field('fixture',value.get('fixture',''),label='Fixture command file (optional)')
        form.field('checkpoint',scenario.get('checkpoint',{}).get('file',''),label='Starting checkpoint (optional; owned steps only)')
        form.field('max_ticks',scenario.get('max_ticks',12000))
        if not edit:
            form.field('starter','start',choices=['start','entrance','map','world','objective'])
            a=self.document.adventure;from world_editing import all_worlds
            targets=[e['id'] for m in a['maps'] for e in m['entrances']]+[o['id'] for o in a['maps']+all_worlds(a)+a.get('objectives',[])]
            form.field('target','',choices=['']+targets);form.field('x',0,label='Movement X (map/world starter)');form.field('y',0,label='Movement Y (map/world starter)')
        def apply(v):
            suite=next(s for s in model.suites(self.document) if s['id']==suite_id)
            case=copy.deepcopy(value);case.update(id=v['id'],tags=[s.strip() for s in v['tags'].split(',') if s.strip()])
            case.pop('seeds',None)
            if v['seeds'].strip():case['seeds']=[int(s.strip()) for s in v['seeds'].split(',')]
            if v['setup']=='Fixture file':
                if not v['fixture'].strip():raise EditorError('Select a fixture command file, or choose New game.')
                case['fixture']=v['fixture'].strip();case.pop('fixture_commands',None)
            elif v['setup']=='Imported fixture':
                if 'fixture_commands' not in case:raise EditorError('This case has no imported fixture. Choose a fixture file or New game.')
            else:case.pop('fixture',None);case.pop('fixture_commands',None)
            if v['file'].strip():
                if v['checkpoint'].strip():raise EditorError('Set checkpoints inside the external scenario, or use project steps.')
                case['file']=v['file'].strip();case.pop('scenario',None)
            else:
                case.pop('file',None)
                if edit and 'scenario' not in value:
                    path=(self.document.root/value['file']).resolve();scenario=model._scenario_paths(model.read_json(path),path.parent)
                else:scenario=copy.deepcopy(value.get('scenario')) if edit else model.scaffold(self.document,v['starter'],v['target'],[int(v['x']),int(v['y'])])
                scenario['max_ticks']=int(v['max_ticks']);scenario.pop('checkpoint',None)
                if v['checkpoint'].strip():scenario['checkpoint']=model.pin_checkpoint(self.document.root/v['checkpoint'].strip());scenario.pop('seed',None)
                case['scenario']=scenario
            if previous is None:suite['cases'].append(case)
            else:suite['cases'][next(i for i,c in enumerate(suite['cases']) if c['id']==previous)]=case
            self.save_suite(suite,suite_id);self.current_case=case['id']
            if v.get('starter')=='objective':self.status.set('Insert the actual route and choices before the objective assertion. This starter does not complete the objective for you.')
        form.submit(apply);return form
    def clone_case(self):
        suite=self.suite();case=copy.deepcopy(self.case());case['id']+='-copy';suite['cases'].append(case);self.save_suite(suite,self.current);self.current_case=case['id'];self.refresh()
    def remove_case(self):
        suite=self.suite();suite['cases']=[c for c in suite['cases'] if c['id']!=self.case()['id']];self.save_suite(suite,self.current);self.refresh()
    def draw_steps(self):
        selected=self.steps.selection();self.steps.delete(*self.steps.get_children());self.case_label.set('Select a case on the Cases page.')
        if not self.current or not self.current_case:return
        case=self.case();self.case_label.set(case['id']+': '+('External reference. Clear the file field to import editable steps.' if 'file' in case else 'Steps execute in order. Map/world coordinates use movement cells.'))
        for i,step in enumerate(case.get('scenario',{}).get('steps',[])):
            self.steps.insert('','end',iid=str(i),text=str(i+1)+'. '+step['op'],values=(json.dumps({k:v for k,v in step.items() if k!='op'},ensure_ascii=False),))
        self.steps.selection_set([s for s in selected if self.steps.exists(s)])
    def step_index(self):
        if not self.steps.selection():raise EditorError('Select a step first.')
        return int(self.steps.selection()[0])
    def step_form(self,edit=False):
        case=self.case()
        if 'file' in case:raise EditorError('Clear the external scenario file in Edit case to import editable steps.')
        index=self.step_index() if edit else len(case['scenario']['steps']);step=case['scenario']['steps'][index] if edit else {};kind=self.step_kind.get()
        if edit:
            kind=step['op']
            if kind in ('walk','assert'):kind+=' '+next((k for k in ('entrance','map','world','objective','phase') if k in step),'JSON')
            if kind not in STEP_KINDS or kind=='assert world':kind='advanced JSON'
            if step['op']=='assert' and len(step)>3:kind='advanced JSON'
        form=Form(self,'Scenario step: '+kind);suite_id=self.current;case_id=case['id']
        op=kind.split()[0]
        fields={}
        if kind=='advanced JSON':fields['json']=json.dumps(step or {'op':'assert','phase':'exploration'})
        elif op=='walk':
            target=kind.split()[1];fields[target]=step.get(target,'')
            if target!='entrance':fields.update(x=step.get('at',[0,0])[0],y=step.get('at',[0,0])[1])
        elif op=='assert':
            target=kind.split()[1];fields[target]=step.get(target,'exploration' if target=='phase' else '')
            if target=='objective':fields['status']=step.get('status','complete')
        elif op=='choose':fields['label']=step.get('label','')
        elif op=='checkpoint':fields['name']=step.get('name','')
        elif op=='battle':fields['control']=step.get('control','computer')
        elif op=='input':fields.update(action=step.get('action','space'),repeat=step.get('repeat',1))
        a=self.document.adventure;from world_editing import all_worlds
        choices={'entrance':[e['id'] for m in a['maps'] for e in m['entrances']], 'map':[m['id'] for m in a['maps']], 'world':[w['id'] for w in all_worlds(a)],
                 'objective':[o['id'] for o in a.get('objectives',[])], 'status':['inactive','active','complete','failed'], 'control':['computer','hold','retreat'],
                 'phase':['exploration','entry','text','choice','shop','battle','fault','complete']}
        for key,value in fields.items():form.field(key,value,choices=choices.get(key))
        def apply(v):
            value=json.loads(v['json']) if kind=='advanced JSON' else dict(step,op=op)
            if kind!='advanced JSON':
                value.update({k:int(v[k]) if isinstance(fields[k],int) else v[k] for k in v if k not in ('x','y')})
                if 'x' in v:value['at']=[int(v['x']),int(v['y'])]
                if value.get('name')=='':value.pop('name')
            suite=next(s for s in model.suites(self.document) if s['id']==suite_id);steps=next(c for c in suite['cases'] if c['id']==case_id)['scenario']['steps']
            if edit:steps[index]=value
            else:steps.append(value)
            self.save_suite(suite,suite_id)
        form.submit(apply);return form
    def move_step(self,delta):
        suite=self.suite();case=next(c for c in suite['cases'] if c['id']==self.current_case);steps=case['scenario']['steps'];i=self.step_index();j=i+delta
        if 0<=j<len(steps):steps[i],steps[j]=steps[j],steps[i];self.save_suite(suite,self.current);self.refresh();self.steps.selection_set(str(j))
    def remove_step(self):
        suite=self.suite();case=next(c for c in suite['cases'] if c['id']==self.current_case);case['scenario']['steps'].pop(self.step_index());self.save_suite(suite,self.current);self.refresh()
    def export(self,target=None):
        parent=target or filedialog.askdirectory(parent=self.window,title='Export new suite folder inside')
        if not parent:return
        candidate=snapshot(self.scope);value=next(s for s in model.suites(candidate) if s['id']==self.current)
        output=Path(parent)/('suite-'+value['id']+'-'+uuid.uuid4().hex[:8])
        return self.workspace.tasks.submit('Export test suite',self,lambda cancel:model.export_suite(candidate,value,output,cancel.is_set),
            lambda _:self.status.set('Exported portable CLI suite: '+str(output/'inputs/suite.json')))
    def run_selected(self,full=False,inspect=False):
        if self.job:raise EditorError('Wait for or cancel the current suite run.')
        candidate=snapshot(self.scope);value=next(s for s in model.suites(candidate) if s['id']==self.current)
        selected=None if full or inspect else list(self.cases.selection()) or [self.case()['id']];stamp=signature(self.scope);generation=self.generation
        output=self.workspace.state_dir/'test-runs'/uuid.uuid4().hex;runner=Path(__file__).resolve().parents[1]/'build'/('btp-author-playtest.exe' if os.name=='nt' else 'btp-author-playtest')
        settings={k:v for k,v in self.scope.owner.settings.items() if k in ('data','dialogue-data','combat-data','world-data') and v}
        def done(result):
            if generation!=self.generation:return
            self.job=None;self.inventory=result['inventory'];self.run_stamp=stamp;self.refresh()
            self.workspace.log('Retained suite coverage: '+str(output/'coverage.json'))
            self.status.set(result['status'].replace('_',' ').capitalize()+'. Coverage describes this retained snapshot; external source files are not rechecked. Report path is in Output.')
        def failed(error):self.job=None;self.status.set(str(error)+' Artifacts: '+str(output));report(self,error)
        operation=(lambda cancel:model.inspect(candidate,value,output,cancel.is_set)) if inspect else (lambda cancel:model.run(candidate,value,output,runner,settings,selected,cancel.is_set))
        self.job=self.workspace.tasks.submit('Inspect suite dependencies' if inspect else 'Run authored test suite',self,operation,done,failed)
        return self.job
    def load_report(self,path=None):
        path=path or filedialog.askopenfilename(parent=self.window,title='Open retained coverage.json',filetypes=[('Coverage','*.json')])
        if not path:return
        inventory=model.read_json(Path(path))
        if inventory.get('format')!='btp-suite-coverage-v1':raise EditorError('Choose a suite coverage.json report.')
        self.inventory=inventory;self.run_stamp=None;self.draw_coverage();self.refresh();self.status.set('Historical coverage loaded from '+str(path)+'. It is evidence for its recorded revision only.')
    def draw_coverage(self):
        self.coverage.delete(*self.coverage.get_children());self.targets={}
        if not self.inventory:return
        self.coverage_note.set('Retained suite '+self.inventory.get('suite_id','')+' / revision '+self.inventory['revision'][:12]+'. '+
            ('Earlier draft. ' if self.run_stamp!=signature(self.scope) else '')+'Unvisited branches and unknown control remain unverified.')
        for case in self.inventory['cases']:
            key=self.coverage.insert('','end',text=case['id']+': '+case['status'].replace('_',' '),values=(str(len(case['dependencies']))+' dependencies',str(len(case['observed_events']))+' events'))
            for text in case['unknown']:self.coverage.insert(key,'end',text='Unknown: '+text,values=('Unknown','Not proven'))
            for diagnostic in case['diagnostics']:
                row=self.coverage.insert(key,'end',text=diagnostic['message'],values=('Failure','Double-click to locate'));self.targets[row]=diagnostic
        for event in self.inventory['events']:
            key=self.coverage.insert('','end',text=event['id'],values=('Declared' if event['declared'] else 'Not declared','Observed' if event['observed'] else 'Unvisited'))
            self.targets[key]=dict(object_id=event['id'],message='Event coverage in retained test run',field_path='')
        for branch in self.inventory['branches']:
            key=self.coverage.insert('','end',text=branch['event']+' / '+branch['branch']+' -> '+branch['target'],values=('Explicit branch','Observed' if branch['observed'] else 'Unvisited'))
            self.targets[key]=dict(object_id=branch['event'],message='Branch coverage in retained test run',field_path='')
    def navigate(self):
        from editor_problems import navigate
        selected=self.coverage.selection()
        if selected and selected[0] in self.targets:
            problem=dict(self.targets[selected[0]],owner=self,scope=self.scope,document=self.scope.document)
            if not navigate(self.workspace,problem):self.status.set('The referenced object is absent from this draft. See the retained report.')


def open_suites(owner):return open_view(owner,'suites',lambda:Suites(owner))
