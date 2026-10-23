"""Bounded native generator overview and the normal jigsaw/pattern editors."""
from __future__ import annotations
import copy
import tkinter as tk
from tkinter import ttk
from adventure_editor import Form
from editor_workspace import open_view,view_window
from editor_session import guard
from editor_canvas import CanvasZoom
from editor_model import EditorError
from chi_spatial import data,change,move_town,find
from chi_resources import world_preview


def open_world(owner):
    view=open_view(owner,'chi-world',lambda:ChiWorld(owner));owner.world_editor=view;return view


class ChiWorld:
    def __init__(self,owner):
        self.owner=owner;self.document=owner.document;self.window=view_window(self,owner,'chi-world','CHI world and jigsaws')
        self.window.geometry('1000x730');self.status=tk.StringVar(value='Loading native world…');self.generation=0;self.image=None;self.drag=None;self.selected=None
        bar=ttk.Frame(self.window,padding=8);bar.pack(fill='x')
        for title,cb in [('Refresh',self.refresh),('Generator inputs',self.generator),('Place / move town',self.town),('Edit town map',self.edit_town),
                         ('Paint jigsaw',self.edit_jigsaw),('Clone jigsaw',self.clone_jigsaw),('Join bindings',self.joins)]:
            ttk.Button(bar,text=title,command=lambda fn=cb:guard(self,fn)).pack(side='left',padx=3)
        from editor_ui import flow_toolbar
        flow_toolbar(bar)
        controls=ttk.Frame(self.window,padding=8);controls.pack(fill='x');self.zoom=tk.StringVar(value='2')
        self.zoom_control=CanvasZoom(controls,self.zoom,self.draw,base=1,steps=(1,2,3,4,6,8,12,16));self.zoom_control.pack(side='left')
        self.ruined=tk.BooleanVar(value=False);ttk.Checkbutton(controls,text='Ruined Citadel state',variable=self.ruined,command=self.refresh).pack(side='left',padx=12)
        ttk.Label(self.window,text='World: 1,024 × 1,024 tiles. Drag towns on the native 64-tile sector grid.',wraplength=460,padding=(8,0)).pack(fill='x')
        ttk.Label(self.window,textvariable=self.status,wraplength=900,padding=8).pack(fill='x')
        host=ttk.Panedwindow(self.window,orient='horizontal');host.pack(fill='both',expand=True)
        side=ttk.Frame(host,padding=8);view=ttk.Frame(host);host.add(side,weight=1);host.add(view,weight=4)
        ttk.Label(side,text='Towns / islands').pack(anchor='w')
        self.towns=ttk.Treeview(side,show='tree',selectmode='browse',height=12);self.towns.pack(fill='x',pady=8)
        self.towns.bind('<<TreeviewSelect>>',lambda _:self.select_town());self.towns.bind('<Double-1>',lambda _:guard(self,self.edit_town))
        ttk.Label(side,text='Terrain join pieces').pack(anchor='w')
        box=ttk.Frame(side);box.pack(fill='both',expand=True);self.listing=ttk.Treeview(box,show='tree',selectmode='browse')
        sy=ttk.Scrollbar(box,command=self.listing.yview);sy.pack(side='right',fill='y');self.listing.configure(yscrollcommand=sy.set);self.listing.pack(fill='both',expand=True)
        self.listing.bind('<Double-1>',lambda _:guard(self,self.edit_jigsaw))
        self.canvas=tk.Canvas(view,background='#263842',highlightthickness=0);sx=ttk.Scrollbar(view,orient='horizontal',command=self.canvas.xview);sy=ttk.Scrollbar(view,command=self.canvas.yview)
        sx.pack(side='bottom',fill='x');sy.pack(side='right',fill='y');self.canvas.pack(fill='both',expand=True);self.canvas.configure(xscrollcommand=sx.set,yscrollcommand=sy.set)
        self.canvas.bind('<Button-1>',self.down);self.canvas.bind('<B1-Motion>',self.motion);self.canvas.bind('<ButtonRelease-1>',lambda e:guard(self,lambda:self.up(e)))
        self.zoom_control.attach(self.canvas);self.refresh()
    @property
    def adventure(self):return self.document.adventure
    def guard(self,fn):return guard(self,fn)
    def refresh(self):
        value=data(self.document);chosen=self.listing.selection();self.towns.delete(*self.towns.get_children());self.listing.delete(*self.listing.get_children())
        for m in value['maps']:
            if m['slot']<=13 and m['slot']!=11:self.towns.insert('','end',iid=m['id'],text=f"{m['name']} ({m['origin'][0]}, {m['origin'][1]})")
        for j in value['world']['jigsaws']:self.listing.insert('','end',iid=j['id'],text=j['name'])
        if chosen and self.listing.exists(chosen[0]):self.listing.selection_set(chosen[0])
        else:self.listing.selection_set(value['world']['jigsaws'][0]['id'])
        self.generation+=1;generation=self.generation;revision=self.document.revision;candidate=self.document.worker_copy();ruined=self.ruined.get()
        self.status.set('Generating a bounded 128 × 128 overview from the native runtime…')
        def ready(image):
            if generation!=self.generation or revision!=self.document.revision:return
            self.image=image;self.draw();self.status.set(f"Seed {value['world']['seed']}. Terrain uses the original midpoint generator and 17 join bindings. Town composition priority follows native map slots.")
        workspace=getattr(self.window,'workspace',None)
        if workspace:workspace.tasks.submit('Preview CHI world',self,lambda cancel:world_preview(candidate,ruined,cancel),ready)
        else:ready(world_preview(candidate,ruined))
    def draw(self):
        if not self.canvas.winfo_exists():return
        self.canvas.delete('all');z=int(self.zoom.get());self.canvas.configure(scrollregion=(0,0,128*z,128*z))
        if self.image:
            raw=tk.PhotoImage(master=self.window,width=128,height=128);raw.put(' '.join('{'+' '.join('#'+row[x:x+6] for x in range(0,len(row),6))+'}' for row in self.image['rows']))
            self.photo=raw.zoom(z);self.canvas.create_image(0,0,image=self.photo,anchor='nw')
        value=data(self.document)
        for m in value['maps']:
            if m['slot']>13 or m['slot']==11:continue
            x,y=m['origin'];color='#ffff66' if m['id']==self.selected else '#ffffff'
            if self.drag and self.drag[0]==m['id']:x,y=self.drag[1:]
            self.canvas.create_rectangle(x/8*z,y/8*z,(x+m['width'])/8*z,(y+m['height'])/8*z,outline=color,width=2)
            self.canvas.create_text(x/8*z+3,y/8*z+3,text=m['name'],fill=color,anchor='nw')
    def select_town(self):
        ids=self.towns.selection()
        if ids:self.selected=ids[0];self.draw()
    def down(self,e):
        z=int(self.zoom.get());x=self.canvas.canvasx(e.x)/z*8;y=self.canvas.canvasy(e.y)/z*8
        for m in data(self.document)['maps']:
            ox,oy=m['origin']
            if m['slot']<=13 and m['slot']!=11 and ox<=x<ox+m['width'] and oy<=y<oy+m['height']:
                self.selected=m['id'];self.towns.selection_set(m['id']);self.drag=(m['id'],ox,oy);return
    def motion(self,e):
        if self.drag:
            z=int(self.zoom.get());x=max(0,min(960,round(self.canvas.canvasx(e.x)/z/8)*64));y=max(0,min(960,round(self.canvas.canvasy(e.y)/z/8)*64))
            self.drag=(self.drag[0],x,y);self.draw()
    def up(self,e):
        if self.drag:
            target,x,y=self.drag;self.drag=None
            change(self.document,lambda a:move_town(a,target,x,y),'Move CHI town');self.owner.refresh()
    def town(self):
        value=data(self.document);m=find(value['maps'],self.selected or 'chi:map-01');f=Form(self,'Move native town / island')
        f.field('map',m['id'],[m['id'] for m in value['maps'] if m['slot']<=13 and m['slot']!=11]);f.field('x',m['origin'][0]);f.field('y',m['origin'][1])
        def apply(v):change(self.document,lambda a:move_town(a,v['map'],int(v['x']),int(v['y'])),'Move CHI town');self.owner.refresh()
        f.submit(apply);return f
    def edit_town(self):
        identity=self.selected or 'chi:map-01';self.owner.scene_index=next(i for i,m in enumerate(self.adventure['maps']) if m['id']==identity);self.owner.refresh();self.owner.window.lift()
    def show_location(self,world,at,message,coordinate_space='world_movement'):
        if world!='chi:world':raise EditorError('This native campaign has one world: chi:world.')
        x,y=at if coordinate_space=='world_tile' else [n/2 for n in at]
        z=int(self.zoom.get());self.canvas.xview_moveto(max(0,x/1024-self.canvas.winfo_width()/(256*z)))
        self.canvas.yview_moveto(max(0,y/1024-self.canvas.winfo_height()/(256*z)));self.status.set(message);self.window.lift()
        self.canvas.create_rectangle((x/8-.5)*z,(y/8-.5)*z,(x/8+.5)*z,(y/8+.5)*z,outline='#ffffff',width=3,tags='problem-location')
    def generator(self):
        w=data(self.document)['world'];f=Form(self,'Native world generator')
        f.field('name',w['name']);f.field('seed',w['seed']);f.field('coarse',','.join(map(str,w['coarse'])),label='336 coarse heights (0–127)')
        f.field('flips',','.join(map(str,w['flips'])),label='96 tile / join flip entries');f.field('mini_colors',','.join(map(str,w['mini_colors'])),label='256 overhead colour indices')
        def apply(v):
            def edit(a):a['world'].update(name=v['name'],seed=int(v['seed']),**{k:[int(n.strip()) for n in v[k].split(',')] for k in ('coarse','flips','mini_colors')})
            change(self.document,edit,'Edit CHI generator inputs');self.owner.refresh()
        f.submit(apply);return f
    def selected_jigsaw(self):
        ids=self.listing.selection();return next((j for j in self.adventure['jigsaws'] if ids and j['id']==ids[0]),None)
    def edit_jigsaw(self):
        j=self.selected_jigsaw()
        if j:
            from world_editor import JigsawEditor
            return open_view(self,'jigsaw',lambda:JigsawEditor(self,j),j['id'])
    def clone_jigsaw(self):
        j=self.selected_jigsaw()
        if j:
            a=copy.deepcopy(self.adventure)
            from world_editing import add_jigsaw
            identity=add_jigsaw(a,self.document.manifest['package_id'],j['rows'],j['name'][:80]+' copy');self.owner.commit(a);self.listing.selection_set(identity)
    def joins(self):
        w=data(self.document)['world'];f=Form(self,'Native terrain joining bindings');choices=[j['id'] for j in w['jigsaws']]
        for i,identity in enumerate(w['joins']):f.field(str(i),identity,choices,label='Join mask '+str(i) if i<16 else 'Level 16 terrain')
        def apply(v):change(self.document,lambda a:a['world'].update(joins=[v[str(i)] for i in range(17)]),'Bind CHI terrain joins');self.owner.refresh()
        f.submit(apply);return f
