"""Project-owned, portable map blocks with visual selection and placement."""
import copy
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from adventure_editor import Form
from editor_model import EditorError,encoded
from editor_session import guard,visible_parent
from editor_workspace import view_window
from editor_recovery import recoverable_forms
from tile_editing import metadata
from map_patterns import save_pattern,export_pattern,import_pattern


@recoverable_forms
class PatternLibrary:
    def __init__(self,owner):
        self.owner=owner;self.document=owner.document;self.selected=None;self.target=owner
        self.window=view_window(self,owner,'patterns','Pattern Library');self.window.geometry('960x700')
        bar=ttk.Frame(self.window,padding=8);bar.pack(fill='x')
        for label,callback in [('Save selection',self.capture),('Use on map',self.use),('Rename',self.rename),('Clone',self.clone),('Remove',self.remove),('Import...',self.import_file),('Export...',self.export_file),
                               ('Construction Library',owner.construction_library),('Save to library',self.save_library)]:
            ttk.Button(bar,text=label,width=0,command=lambda f=callback:guard(self,f)).pack(side='left',padx=3)
        from editor_ui import flow_toolbar
        flow_toolbar(bar)
        self.info=tk.StringVar(value='Select a map rectangle and Save selection. Patterns travel with the project; Export shares their tiles and owned artwork.')
        ttk.Label(self.window,textvariable=self.info,wraplength=900,padding=8).pack(side='bottom',fill='x')
        body=ttk.Panedwindow(self.window,orient='horizontal');body.pack(fill='both',expand=True,padx=8,pady=8)
        left=ttk.Frame(body);right=ttk.Frame(body);body.add(left,weight=1);body.add(right,weight=3)
        self.query=tk.StringVar();search=ttk.Entry(left,textvariable=self.query);search.pack(fill='x',pady=(0,8))
        search.bind('<Return>',lambda _:guard(self,self.refresh))
        self.listing=ttk.Treeview(left,show='tree',selectmode='browse');self.listing.column('#0',width=230)
        sy=ttk.Scrollbar(left,command=self.listing.yview);self.listing.configure(yscrollcommand=sy.set)
        sy.pack(side='right',fill='y');self.listing.pack(fill='both',expand=True)
        self.listing.bind('<<TreeviewSelect>>',self.select);self.listing.bind('<Double-1>',lambda _:guard(self,self.use))
        self.overlay=tk.BooleanVar(value=False)
        ttk.Checkbutton(right,text='Place as a new overlay (local maps)',variable=self.overlay).pack(anchor='w',pady=(0,8))
        shell=ttk.Frame(right);shell.pack(fill='both',expand=True)
        self.canvas=tk.Canvas(shell,background='#273b45',highlightthickness=0)
        sx=ttk.Scrollbar(shell,orient='horizontal',command=self.canvas.xview);sy=ttk.Scrollbar(shell,command=self.canvas.yview)
        sx.pack(side='bottom',fill='x');sy.pack(side='right',fill='y');self.canvas.pack(fill='both',expand=True)
        self.canvas.configure(xscrollcommand=sx.set,yscrollcommand=sy.set)
        self.refresh()

    def values(self):return metadata(self.document).get('map_patterns',[])
    def current(self):return next((p for p in self.values() if p['id']==self.selected),None)
    def refresh(self):
        self.listing.delete(*self.listing.get_children())
        from asset_catalogue import search_document
        matching=search_document(self.document,self.query.get()) if self.query.get() else None
        values=[p for p in self.values() if matching is None or p['id'] in matching]
        for p in values:self.listing.insert('','end',iid=p['id'],text=p['name']+f"  ({len(p['rows'][0])} × {len(p['rows'])})")
        if values:
            if self.selected not in {p['id'] for p in values}:self.selected=values[0]['id']
            self.listing.selection_set(self.selected)
        else:self.selected=None
        self.draw()
    def select(self,_=None):
        selected=self.listing.selection()
        if selected:self.selected=selected[0];self.draw()
    def draw(self):
        self.canvas.delete('all');p=self.current()
        if not p:
            self.canvas.create_text(18,18,anchor='nw',fill='white',text='No patterns yet.\nSelect terrain on a map, then Save selection.');return
        rows=p['rows'];values={t['id']:t for t in self.document.adventure['tiles']}
        size=24;self.canvas.configure(scrollregion=(0,0,len(rows[0])*size,len(rows)*size))
        for y,row in enumerate(rows):
            for x,identity in enumerate(row):
                t=values.get(identity)
                if t:
                    image=self.owner.tile_image(t['sheet'],t['graphic'],size)
                    if image:self.canvas.create_image(x*size,y*size,image=image,anchor='nw')
        self.info.set(p['name']+': '+str(len(rows[0]))+' × '+str(len(rows))+' tiles. Empty cells preserve the destination terrain.')
    def capture(self):return self.target.save_pattern()
    def use(self):
        p=self.current()
        if p:self.target.use_pattern(p['rows'],p['name'],overlay=self.overlay.get())
    def rename(self):
        p=self.current()
        if not p:raise EditorError('Select a pattern first.')
        f=Form(self,'Pattern name');f.field('name',p['name'])
        def apply(v):save_pattern(self.document,p['rows'],v['name'],p['id']);self.refresh()
        f.submit(apply);return f
    def clone(self):
        p=self.current()
        if p:self.selected=save_pattern(self.document,p['rows'],(p['name']+' copy')[:95]);self.refresh()
    def remove(self):
        p=self.current()
        if not p:return
        # Removing a saved pattern never removes placed tiles or its images.
        data=metadata(self.document);data['map_patterns']=[v for v in data['map_patterns'] if v['id']!=p['id']]
        meta=dict(self.document.metadata);meta['EDITOR.json']=encoded(data)
        with self.document.command('Remove map pattern'):
            self.document.replace_all(self.document.content,self.document.adventure,self.document.art,self.document.manifest,meta)
        self.refresh()
    def import_file(self):
        path=filedialog.askopenfilename(parent=visible_parent(self),title='Import map pattern',filetypes=[('Map pattern','*.pattern.json'),('JSON','*.json')])
        if path:self.selected=import_pattern(self.document,path);self.owner.refresh();self.refresh()
    def export_file(self):
        p=self.current()
        if not p:raise EditorError('Select a pattern first.')
        path=filedialog.asksaveasfilename(parent=visible_parent(self),title='Export map pattern',defaultextension='.pattern.json',initialfile=p['id'].split(':')[-1]+'.pattern.json',filetypes=[('Map pattern','*.pattern.json')])
        if path:export_pattern(self.document,p,path);self.info.set('Exported '+path)
    def save_library(self):
        p=self.current()
        if not p:raise EditorError('Select a pattern first.')
        return self.owner.construction_library().export_dialog(p['id'])
