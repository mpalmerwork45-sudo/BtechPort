"""Delivery actions share the same validated package/export path as the editor."""
import json
from pathlib import Path
import tkinter as tk
from tkinter import ttk,filedialog
from editor_model import EditorError
from delivery import asset_report
from editor_workspace import view_window,existing_view
from editor_session import guard

def report(editor):
    if not editor.document:return
    existing=existing_view(editor,'asset-report')
    if existing:return existing
    workspace=getattr(editor._editor_scope,'workspace',None)
    if not workspace:editor._editor_scope.transact(editor.document.validate)
    from types import SimpleNamespace
    view=SimpleNamespace(owner=editor)
    result={};window=view_window(view,editor,'asset-report','Assets and dependencies');view.window=window;window.geometry('850x620')
    text=tk.Text(window,wrap='word');text.pack(fill='both',expand=True,padx=12,pady=12)
    def display(value):
        result.clear();result.update(value);text.configure(state='normal');text.delete('1.0','end');text.insert('1.0',json.dumps(result,indent=2));text.configure(state='disabled')
    if workspace:
        from editor_tasks import snapshot
        candidate=snapshot(editor._editor_scope)
        def work(cancel):candidate.validate();return asset_report(candidate)
        workspace.tasks.submit('Inspecting assets and dependencies',view,work,display)
        text.insert('1.0','Checking package dependencies…');text.configure(state='disabled')
    else:display(asset_report(editor.document))
    def save():
        if not result:raise EditorError('Wait for the asset report to finish.')
        path=filedialog.asksaveasfilename(parent=window,title='Save asset report',initialfile='ASSETS.json',defaultextension='.json')
        if path:Path(path).write_text(json.dumps(result,indent=2)+'\n')
    ttk.Button(window,text='Save report...',command=lambda:guard(view,save)).pack(side='bottom',pady=(0,12),before=text)
    return view

def menu(editor,parent):
    button=ttk.Menubutton(parent,text='Delivery');options=tk.Menu(button,tearoff=False);button.configure(menu=options)
    options.add_command(label='Export game...',command=lambda:editor.guarded(editor.export_project))
    options.add_command(label='Assets and dependencies...',command=lambda:editor.guarded(lambda:report(editor)))
    from save_migration import dialog
    options.add_command(label='Migrate an old save...',command=lambda:editor.guarded(lambda:dialog(editor)))
    button.pack(side='left',padx=2)
