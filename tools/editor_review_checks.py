"""Select explained regression cases without leaving the Changes workspace."""
import json
import os
from pathlib import Path
import tkinter as tk
from tkinter import ttk,filedialog

from authoring_contract import AuthoringError
from editor_session import report as report_error
from editor_ui import flow_toolbar,tooltip
import authoring_review as review


class ReviewChecksPane:
    def __init__(self,owner,parent):
        from editor_changes import text_box
        self.owner=owner;self.parent=parent;self.identity=None;self.impact=None
        self.chosen=set();self.generation=0;self.job=None
        self.pages=ttk.Notebook(parent);self.pages.pack(fill='both',expand=True)
        selection=ttk.Frame(self.pages);explanation=ttk.Frame(self.pages);reports=ttk.Frame(self.pages)
        self.pages.add(selection,text='Cases');self.pages.add(explanation,text='Why this case');self.pages.add(reports,text='Reports')
        bar=ttk.Frame(reports);bar.pack(fill='x')
        owner.button(bar,'Check mission',owner.check);owner.button(bar,'Open artifacts',owner.open_artifacts);flow_toolbar(bar)
        self.reports=text_box(reports)
        self.note=tk.StringVar(value='Choose a scenario suite to see which cases the proposed changes may affect.')
        bar=ttk.Frame(selection);bar.pack(fill='x')
        owner.button(bar,'Choose suite...',self.choose)
        note=ttk.Label(bar,textvariable=self.note,wraplength=300,padding=(6,4));note.pack(side='left',fill='x',expand=True)
        note.bind('<Configure>',lambda event:note.configure(wraplength=max(120,event.width-12)),add='+')
        controls=ttk.Frame(selection);controls.pack(fill='x')
        for title,operation in [('Suggested',self.suggested),('All',self.all),('None',self.none)]:owner.button(controls,title,operation)
        self.run_button=owner.button(controls,'Run selected',self.run)
        self.full_button=owner.button(controls,'Run full suite',lambda:self.run(True));flow_toolbar(controls)
        tooltip(self.full_button,'Run every retained case, including those without a known dependency. Suggestions are not proof that other cases are unaffected.')
        host=ttk.Frame(selection);host.pack(fill='both',expand=True)
        self.listing=ttk.Treeview(host,columns=('run','impact','result'),show='tree headings',height=4,selectmode='browse')
        for key,title,width in [('#0','Scenario',150),('run','Run',45),('impact','Dependencies',160),('result','Latest check',120)]:
            self.listing.heading(key,text=title);self.listing.column(key,width=width,minwidth=35,stretch=key!='run')
        sy=ttk.Scrollbar(host,command=self.listing.yview);sy.pack(side='right',fill='y')
        sx=ttk.Scrollbar(host,orient='horizontal',command=self.listing.xview);sx.pack(side='bottom',fill='x')
        self.listing.configure(yscrollcommand=sy.set,xscrollcommand=sx.set);self.listing.pack(fill='both',expand=True)
        self.listing.bind('<Button-1>',self.click)
        self.listing.bind('<space>',lambda event:self.toggle_selected())
        self.listing.bind('<<TreeviewSelect>>',lambda event:self.explain())
        self.listing.bind('<Double-1>',lambda event:self.pages.select(1) if self.listing.identify_column(event.x)!='#1' else None)
        # In the normal dock only ~280 pixels are available. Give explanations
        # their own page instead of clipping them beneath the case table.
        self.details=text_box(explanation,5)
        self.parent.bind('<Destroy>',self.destroyed,add='+');self.buttons()

    def destroyed(self,event):
        if event.widget==self.parent:
            self.generation+=1
            if self.job:self.job.cancelled.set()

    def buttons(self):
        self.run_button.state(['!disabled'] if self.impact and self.chosen and self.job is None else ['disabled'])
        self.full_button.state(['!disabled'] if self.impact and self.job is None else ['disabled'])

    def load(self,record,folder):
        from editor_changes import fill
        identity=(str(folder),record.get('result_revision'))
        if identity!=self.identity:
            self.generation+=1
            if self.job:self.job.cancelled.set();self.job=None
            self.identity=identity;self.impact=None;self.chosen=set();self.listing.delete(*self.listing.get_children())
            self.note.set('Choose a scenario suite to analyse this retained proposal. No scenarios have been run.')
            fill(self.details,'Click the Run cell or press Space to include a case. Select a row to read its dependencies.')
        links=record.get('selections',[])
        path=str(Path(folder)/links[-1]['report']) if links else None
        if path and (not self.impact or self.impact['report']!=path):self.display(review.read_selection(folder,path,record))
        self.update_results(record);self.buttons()

    def display(self,impact):
        self.impact=impact;self.chosen=set(impact['suggested']);self.listing.delete(*self.listing.get_children())
        titles={'affected':'Affected','unknown':'Unknown','no_known_dependency':'No known dependency'}
        for case in impact['cases']:
            self.listing.insert('','end',iid=case['id'],text=case['id'],values=('[x]' if case['id'] in self.chosen else '[ ]',titles[case['classification']],'Not run'))
        self.note.set(('Unknown dependencies: full suite recommended.' if impact['full_suite_recommended'] else
            f"{len(impact['suggested'])} of {len(impact['cases'])} suggested.")+' Retained '+Path(impact['inputs']['source']).name+'.')
        first=impact['cases'][0]['id'];self.listing.selection_set(first);self.explain();self.buttons()

    def choose(self,path=None):
        self.owner.selected()
        path=path or filedialog.askopenfilename(parent=self.owner.window,title='Choose a scenario suite to analyse',filetypes=[('Scenario suite','*.json')])
        if not path:return
        self.generation+=1;generation=self.generation;folder=self.owner.folder;validator=self.owner.document.validator
        if self.job:self.job.cancelled.set()
        self.impact=None;self.chosen=set();self.listing.delete(*self.listing.get_children())
        self.note.set('Reading dependencies and retaining suite inputs. No tests are running.');self.pages.select(0)
        def done(result):
            if generation!=self.generation:return
            self.job=None;self.display(result);self.owner.manager.notify(self.owner.scope)
            self.owner.status.set(f"Suggested {len(result['suggested'])} of {len(result['cases'])} cases; none have run yet.")
        def failed(error):
            if generation!=self.generation:return
            self.job=None;self.note.set(str(error));self.buttons();report_error(self.owner,error)
        self.job=self.owner.workspace.tasks.submit('Suggest scenario cases',self.owner.scope.owner,
            lambda cancel:review.suggest_cases(folder,validator,path,cancelled=cancel.is_set),done,failed)
        self.buttons();return self.job

    def redraw_selection(self):
        for case in self.listing.get_children():self.listing.set(case,'run','[x]' if case in self.chosen else '[ ]')
        self.buttons()

    def suggested(self):
        self.chosen=set(self.impact['suggested']) if self.impact else set();self.redraw_selection()

    def all(self):self.chosen=set(self.listing.get_children());self.redraw_selection()
    def none(self):self.chosen=set();self.redraw_selection()

    def toggle(self,identity):
        if identity in self.chosen:self.chosen.remove(identity)
        else:self.chosen.add(identity)
        self.redraw_selection()

    def click(self,event):
        identity=self.listing.identify_row(event.y)
        if identity and self.listing.identify_column(event.x)=='#1':self.toggle(identity)

    def toggle_selected(self):
        for identity in self.listing.selection():self.toggle(identity)
        return 'break'

    def explain(self):
        from editor_changes import fill
        selected=self.listing.selection()
        if not selected or not self.impact:return
        case=next(c for c in self.impact['cases'] if c['id']==selected[0])
        lines=[case['id']+' — '+case['classification'].replace('_',' '),'Seeds: '+', '.join(map(str,case['seeds'])) if case['seeds'] else 'Uses the pinned checkpoint RNG.']
        for reason in case['reasons']:
            lines.append('Changed '+reason['path']+(' ('+reason['side']+')' if reason.get('side') else ''))
            lines.append('  '+(' -> '.join(reason['via']) if 'via' in reason else reason['basis']))
        lines.extend('Unknown: '+value for value in case['unknown'])
        lines.extend(['',f"{case['dependency_count']} explicit dependencies; showing up to 128 in the retained report.",
            'Suite inputs are retained. Choose suite again to use later edits to its files.',
            'No known dependency is not a pass. Only the cases and seeds in a completed check have test evidence.'])
        fill(self.details,'\n'.join(lines))

    def update_results(self,record):
        if not self.impact:return
        # Each report shows its own selected/omitted cases. Do not carry an old
        # pass into a later partial run and imply that it ran again.
        check=next((c for c in reversed(record.get('checks',[])) if c['kind']=='suite' and
            c['result'].get('selection')==self.impact['report']),None)
        if not check:return
        result=json.loads(Path(check['result']['report']).read_bytes())
        for identity in self.listing.get_children():
            status=result.get('case_results',{}).get(identity,{}).get('status','not_run')
            self.listing.set(identity,'result',status.replace('_',' ').capitalize())

    def run(self,full=False):
        if not self.impact:raise AuthoringError('selection.missing','Choose a scenario suite first.')
        if self.job:raise AuthoringError('job.busy','Wait for this check, or cancel it before starting another.')
        if not full and not self.chosen:raise AuthoringError('selection.empty','Choose at least one case, or Run full suite.')
        folder=self.owner.folder;selection=self.impact['report'];generation=self.generation
        cases=None if full else [c['id'] for c in self.impact['cases'] if c['id'] in self.chosen]
        validator=self.owner.document.validator;settings=dict(self.owner.owner.settings)
        runner=Path(__file__).resolve().parents[1]/'build'/('btp-author-playtest.exe' if os.name=='nt' else 'btp-author-playtest')
        def done(result):
            if generation!=self.generation:return
            self.job=None;self.owner.manager.notify(self.owner.scope);self.buttons()
            self.owner.status.set(f"Selected checks: {result['status']}; {len(result['unselected_cases'])} cases not run.")
        def failed(error):
            if generation!=self.generation:return
            self.job=None;self.owner.manager.notify(self.owner.scope);self.buttons();report_error(self.owner,error)
        self.job=self.owner.workspace.tasks.submit('Run reviewed scenario cases',self.owner.scope.owner,
            lambda cancel:review.check_candidate(folder,validator,runner=runner,settings=settings,selection=selection,case_ids=cases,cancelled=cancel.is_set),done,failed)
        self.buttons();return self.job
