"""Delivery actions share the same validated package/export path as the editor."""
import json
from pathlib import Path
import tkinter as tk
from tkinter import ttk,filedialog
from editor_model import EditorError
from delivery import asset_report

def report(editor):
    if not editor.document:return
    editor.apply_form();editor.document.validate()
    result=asset_report(editor.document);window=tk.Toplevel(editor.window);window.title('Assets and dependencies');window.geometry('850x620')
    text=tk.Text(window,wrap='word');text.pack(fill='both',expand=True,padx=12,pady=12)
    text.insert('1.0',json.dumps(result,indent=2));text.configure(state='disabled')
    def save():
        path=filedialog.asksaveasfilename(parent=window,title='Save asset report',initialfile='ASSETS.json',defaultextension='.json')
        if path:Path(path).write_text(json.dumps(result,indent=2)+'\n')
    ttk.Button(window,text='Save report...',command=lambda:editor.guarded(save)).pack(pady=(0,12))

def menu(editor,parent):
    button=ttk.Menubutton(parent,text='Delivery');options=tk.Menu(button,tearoff=False);button.configure(menu=options)
    options.add_command(label='Export game...',command=lambda:editor.guarded(editor.export_project))
    options.add_command(label='Assets and dependencies...',command=lambda:editor.guarded(lambda:report(editor)))
    from save_migration import dialog
    options.add_command(label='Migrate an old save...',command=lambda:editor.guarded(lambda:dialog(editor)))
    button.pack(side='left',padx=2)
