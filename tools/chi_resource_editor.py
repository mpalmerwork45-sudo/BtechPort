"""Native resource inventory using the kit's existing pixel and sprite editors."""
from __future__ import annotations
import copy
import tkinter as tk
from tkinter import ttk
from adventure_editor import Form
from editor_session import guard,scope_of
from editor_workspace import open_view,view_window
from editor_model import EditorError
from chi_resources import preview,detach,inventory,settings,put_settings,SHEETS


def open_resources(owner):return open_view(owner,'chi-resources',lambda:ResourceView(owner))


class ResourceView:
    def __init__(self,owner):
        self.owner=owner;self.document=owner.document;self.editor=scope_of(owner).owner
        self.window=view_window(self,owner,'chi-resources','CHI resources');self.window.geometry('950x700')
        self.status=tk.StringVar(value='Select a resource. Preview uses the effective project, including unsaved changes.')
        self.decoded=None;self.generation=0;self.timer=None;self.frame=0
        top=ttk.Frame(self.window,padding=8);top.pack(fill='x')
        for title,cb in [('Preview',self.load),('Copy and edit',self.edit),('Assign existing image',self.assign),('Building portrait',self.portrait),('Film timing',self.timing),('Audio settings',self.audio),('Artwork library',self.artwork)]:
            ttk.Button(top,text=title,command=lambda fn=cb:guard(self,fn)).pack(side='left',padx=3)
        from editor_ui import flow_toolbar
        flow_toolbar(top)
        controls=ttk.Frame(self.window,padding=8);controls.pack(fill='x')
        self.index=tk.StringVar(value='0');self.count=tk.StringVar(value='1')
        for title,var,maximum in [('First frame / tile',self.index,375),('Frames to copy',self.count,31)]:
            ttk.Label(controls,text=title).pack(side='left',padx=5);ttk.Spinbox(controls,from_=0 if var is self.index else 1,to=maximum,textvariable=var,width=5).pack(side='left')
        ttk.Label(controls,text='Films retain their native frame count.').pack(side='left',padx=12)
        ttk.Label(self.window,textvariable=self.status,wraplength=820,padding=10).pack(fill='x')
        body=ttk.Panedwindow(self.window,orient='horizontal');body.pack(fill='both',expand=True)
        left=ttk.Frame(body,padding=8);right=ttk.Frame(body,padding=8);body.add(left,weight=2);body.add(right,weight=3)
        self.table=ttk.Treeview(left,columns=('kind','count'),show='tree headings',selectmode='browse')
        self.table.heading('#0',text='Resource');self.table.heading('kind',text='Type');self.table.heading('count',text='Frames / tiles')
        self.table.column('#0',width=165);self.table.column('kind',width=70);self.table.column('count',width=85)
        sy=ttk.Scrollbar(left,command=self.table.yview);sy.pack(side='right',fill='y');self.table.configure(yscrollcommand=sy.set);self.table.pack(fill='both',expand=True)
        self.rows=inventory(self.document)['resources']
        for i,row in enumerate(self.rows):self.table.insert('','end',iid=str(i),text=row['resource']+(' '+str(row.get('name',row['index'])) if 'index' in row else ''),values=(row['kind'],row['count']))
        self.table.bind('<<TreeviewSelect>>',lambda _:guard(self,self.select));self.table.bind('<Double-1>',lambda _:guard(self,self.edit))
        self.canvas=tk.Canvas(right,background='#dfe5e8',highlightthickness=0);self.canvas.pack(fill='both',expand=True)
        self.details=tk.StringVar(value=inventory(self.document)['note']);ttk.Label(right,textvariable=self.details,wraplength=450,padding=8).pack(fill='x')
        self.window.bind('<Destroy>',self.destroyed,add='+')
        self.table.selection_set('0')

    def current(self):
        ids=self.table.selection()
        if not ids:raise EditorError('Select a native resource first.')
        return self.rows[int(ids[0])]
    def request(self):
        row=self.current();return row['kind'],row['resource'],int(self.index.get()),int(self.count.get())
    def select(self):
        row=self.current();self.index.set(str(row.get('index',0)));self.count.set('16' if row['kind']=='sprite' else '1');self.load()
    def load(self,then=None):
        request=self.request();self.generation+=1;generation=self.generation;stamp=self.document.revision
        self.decoded=None;self.status.set('Decoding project resource…');candidate=self.document.worker_copy()
        def ready(value):
            if generation!=self.generation or stamp!=self.document.revision:
                self.status.set('Project changed during preview; refresh to show the latest resource.');return
            self.decoded=value;self.preview_request=request;self.frame=0;self.draw()
            self.status.set('Preview ready. Copy and edit creates a project-owned override; Undo removes it.')
            if then:then()
        workspace=getattr(self.window,'workspace',None)
        if workspace:workspace.tasks.submit('Decode CHI resource',self,lambda cancel:preview(candidate,*request,cancel=cancel),ready)
        else:ready(preview(candidate,*request))
    def draw(self):
        if self.timer:self.window.after_cancel(self.timer);self.timer=None
        if not self.decoded:return
        from graphics_editor import photo
        im=self.decoded;z=max(1,min(4,380//max(im['width'],im['height'])))
        self.photo=photo(self.window,im,self.frame,z);self.canvas.delete('all');self.canvas.create_image(10,10,image=self.photo,anchor='nw')
        self.details.set(f"{im['width']} × {im['height']} | frame {self.frame+1}/{len(im['frames'])}\n"+inventory(self.document)['note'])
        if len(im['frames'])>1:
            units=im.get('native_units');duration=max(32,round(units[self.frame]*1000/70)) if units else 128
            self.frame=(self.frame+1)%len(im['frames']);self.timer=self.window.after(duration,self.draw)
    def edit(self):
        if self.decoded is None or self.preview_request!=self.request():return self.load(self.edit)
        kind,resource,index,count=self.request()
        bound=next((b for b in settings(self.document)['bindings'] if (b['kind'],b['resource'],b['index'])==(kind,resource,index)),None)
        if bound:image=next(im for im in self.document.art['images'] if im['id']==bound['image'])
        else:image=detach(self.document,kind,resource,index,count,self.decoded)
        graphics=self.editor.graphics_editor();graphics.selected=image['id'];graphics.refresh()
        from graphics_editor import open_image_editor
        return open_image_editor(graphics,image)
    def artwork(self):return self.editor.graphics_editor()
    def portrait(self):
        slots=('broker','training','lounge','prison','inventor','cinema','hospital','comstar','clothes','video-hut','mayor')
        f=Form(self,'Assign building portrait');f.field('building','training',slots)
        f.field('image','',[im['id'] for im in self.document.art['images'] if (im['width'],im['height'])==(88,88)])
        def apply(v):
            index=slots.index(v['building']);value=settings(self.document)
            value['bindings']=[b for b in value['bindings'] if b['kind']!='portrait' or b['index']!=index]
            value['bindings'].append(dict(kind='portrait',resource='PORTRAITS',index=index,image=v['image'],palette='sprite'))
            put_settings(self.document,value,'Assign native building portrait');self.status.set('Building portrait assigned. It appears in native building views; reopen resources to refresh the inventory.')
        f.submit(apply);return f
    def assign(self):
        kind,resource,index,count=self.request();f=Form(self,'Assign native resource override')
        f.field('image','',[im['id'] for im in self.document.art['images']]);f.field('palette','sprite' if kind in ('sprite','animation','portrait') else 'terrain',['terrain','sprite','direct','phoenix','title'])
        def apply(v):
            value=settings(self.document);value['bindings']=[b for b in value['bindings'] if (b['kind'],b['resource'],b['index'])!=(kind,resource,index)]
            b=dict(kind=kind,resource=resource,index=index,image=v['image'],palette=v['palette'])
            if kind=='animation':
                if self.decoded is None:raise EditorError('Preview this film before assigning its replacement.')
                b['units']=self.decoded['native_units']
            value['bindings'].append(b);put_settings(self.document,value);self.load()
        f.submit(apply);return f
    def timing(self):
        kind,resource,index,count=self.request()
        if kind!='animation':raise EditorError('Choose an O.ANM film. Tile timing is edited in its pixel editor; walkers advance with movement.')
        b=next((b for b in settings(self.document)['bindings'] if b['kind']=='animation' and b['index']==index),None)
        if not b:
            if self.decoded is None:return self.load(self.timing)
            detach(self.document,kind,resource,index,count,self.decoded);b=settings(self.document)['bindings'][-1]
        f=Form(self,'Film frame durations');f.field('units',','.join(map(str,b['units'])),label='Retraces per frame (comma separated)')
        def apply(v):
            value=settings(self.document);next(a for a in value['bindings'] if a['kind']=='animation' and a['index']==index)['units']=[int(n.strip()) for n in v['units'].split(',')]
            put_settings(self.document,value,'Edit native film timing');self.load()
        f.submit(apply);return f
    def audio(self):
        value=settings(self.document);f=Form(self,'Native audio references')
        f.field('sounds',','.join(map(str,value['sounds'])),label='Programs for effect slots 1–18')
        f.field('sound_speed',value['sound_speed'],label='Playback speed, percent (100 = original)');f.field('music',value['music'],['0','1'],label='Title music enabled')
        def apply(v):
            value.update(sounds=[int(n.strip()) for n in v['sounds'].split(',')],sound_speed=int(v['sound_speed']),music=int(v['music']))
            put_settings(self.document,value,'Edit native audio references')
        f.submit(apply);return f
    def destroyed(self,event):
        if event.widget is self.window and self.timer:self.window.after_cancel(self.timer);self.timer=None
