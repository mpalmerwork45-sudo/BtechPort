"""Visible, cancellable recipe export/reconstruction using the shared service."""
from pathlib import Path
import tkinter as tk
from tkinter import ttk,filedialog
from editor_model import ProjectDocument,EditorError
from editor_workspace import open_view,view_window
from editor_session import scope_of,guard

class RecipeView:
    def __init__(self,owner):
        self.owner=owner;self.scope=scope_of(owner);self.window=view_window(self,owner,'chi-recipes','CHI reconstruction recipes')
        self.source=tk.StringVar(value=owner.settings.get('data',''));self.recipe=tk.StringVar();self.output=tk.StringVar();self.status=tk.StringVar(value='Choose original DOS 1.03 files. Recipes contain changes and references; originals are recreated locally.')
        self.result=None
        ttk.Label(self.window,text='Share and reconstruct edited CHI campaigns',style='Title.TLabel',padding=12).pack(anchor='w')
        info=ttk.Label(self.window,text='Export the current project to a new recipe file, or reconstruct a recipe into a new project folder. Existing projects and saves are preserved. Keep the matching Construction Kit version with each recipe.',padding=12,wraplength=680);info.pack(fill='x')
        form=ttk.Frame(self.window,padding=12);form.pack(fill='x');form.columnconfigure(1,weight=1)
        for row,(label,var,kind) in enumerate([('Original DOS 1.03 folder',self.source,'source'),('Recipe JSON file',self.recipe,'recipe'),('New project folder',self.output,'output')]):
            ttk.Label(form,text=label).grid(row=row,column=0,sticky='w',pady=8,padx=(0,8));ttk.Entry(form,textvariable=var).grid(row=row,column=1,sticky='ew')
            ttk.Button(form,text='Open...' if kind=='recipe' else 'Browse...',command=lambda k=kind,v=var:self.browse(k,v)).grid(row=row,column=2,padx=8)
            if kind=='recipe':ttk.Button(form,text='New...',command=lambda:self.browse('new-recipe',self.recipe)).grid(row=row,column=3,padx=(0,8))
        bar=ttk.Frame(self.window,padding=12);bar.pack(fill='x')
        for label,method in [('Export current project recipe',self.export),('Reconstruct recipe',self.build),('Open reconstructed project',self.open)]:ttk.Button(bar,text=label,command=lambda f=method:guard(self,f)).pack(side='left',padx=4)
        from editor_ui import flow_toolbar
        flow_toolbar(bar)
        ttk.Label(self.window,textvariable=self.status,padding=12,wraplength=680).pack(fill='x')
    def browse(self,kind,var):
        parent=self.window.winfo_toplevel()
        if kind=='source':path=filedialog.askdirectory(parent=parent,title='Original DOS 1.03 folder')
        elif kind=='output':
            selected=filedialog.askdirectory(parent=parent,title='Choose parent for a new project folder');path=str(Path(selected)/'Reconstructed CHI') if selected else ''
        elif kind=='recipe':path=filedialog.askopenfilename(parent=parent,title='Open CHI recipe',filetypes=[('CHI recipe','*.json')])
        else:path=filedialog.asksaveasfilename(parent=parent,title='New CHI recipe',defaultextension='.json',filetypes=[('CHI recipe','*.json')])
        if path:var.set(path)
    def export(self):
        from editor_tasks import snapshot
        from chi_recipe import export_recipe
        self.scope.apply_pending();candidate=snapshot(self.scope)
        source,path=Path(self.source.get()),Path(self.recipe.get())
        if not self.recipe.get():raise EditorError('Choose a new recipe filename.')
        self.status.set('Recreating the baseline and checking exact reconstruction...')
        self.submit('Export CHI recipe',lambda cancel:export_recipe(candidate,source,path,cancel),lambda result:self.status.set('Recipe exported: '+result['file']))
    def build(self):
        from authoring_contract import read_json
        from chi_recipe import build_recipe
        if not self.output.get() or not self.recipe.get():raise EditorError('Choose a recipe and a new project folder.')
        value=read_json(Path(self.recipe.get()));source,out=Path(self.source.get()),Path(self.output.get())
        self.status.set('Reconstructing and validating the private project...')
        def ready(result):self.result=result;self.status.set('Ready: '+result['project']+'. Use Open reconstructed project to edit or Play.')
        self.submit('Reconstruct CHI recipe',lambda cancel:build_recipe(value,source,out,self.owner.validator,cancel),ready)
    def submit(self,label,work,ready):
        committed={}
        def worker(cancel):
            result=work(cancel);committed['result']=result;return result
        def failed(error):
            # Cancellation after atomic publication cannot undo a completed
            # result. Report the valid output instead of claiming it vanished.
            if 'result' in committed:ready(committed['result'])
            else:self.failed(error)
        self.window.workspace.tasks.submit(label,self,worker,ready,failed)
    def failed(self,error):self.status.set(str(error)+' Existing files were preserved. Correct the fields and retry.')
    def open(self):
        if not self.result:raise EditorError('Reconstruct a recipe first.')
        if self.owner.discard_or_save():self.owner.set_document(ProjectDocument(Path(self.result['project']),self.owner.validator))

def open_recipes(owner):return open_view(owner,'chi-recipes',lambda:RecipeView(owner))
