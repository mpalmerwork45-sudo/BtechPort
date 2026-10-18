"""Explicit jigsaw world painting and draggable local-map overlays."""
from __future__ import annotations
import copy
import tkinter as tk
from tkinter import ttk
from adventure_editor import Form
from adventure_editing import composite
from editor_model import EditorError
from editor_session import guard, register, apply_draft, scope_of
from editor_workspace import view_window,open_view
from world_editing import (create_world, add_jigsaw, assign_city, world_size,
                           patch_cells, set_patch, line, token, all_worlds, get_world)


class WorldEditor:
    def __init__(self, owner):
        self.owner=owner; self.document=owner.document
        self.window=view_window(self,owner,'world','Worlds and planets');self.window.geometry('1000x730');self.window.minsize(840,600)
        self.stroke=None;self.drag=None;self.cache={};self.pending=False;self.last=None;self.city=None;self.world_id=None
        bar=ttk.Frame(self.window,padding=8);bar.pack(fill='x')
        for title,cb in [('Create world',self.new_world),('Place city',self.city_form),('Edit city',self.edit_city),('Remove city',self.remove_city),('Undo',owner.undo),('Redo',owner.redo),('Save',owner.save),('Validate',owner.validate)]:
            ttk.Button(bar,text=title,width=0,style='Toolbar.TButton',command=lambda f=cb:self.guard(f)).pack(side='left',padx=3)
        controls=ttk.Frame(self.window,padding=(8,0,8,8));controls.pack(fill='x')
        self.planet=ttk.Combobox(controls,state='readonly',width=22);self.planet.pack(side='left',padx=(0,8));self.planet.bind('<<ComboboxSelected>>',lambda _:self.change_planet())
        ttk.Button(controls,text='Rename',command=lambda:self.guard(self.rename_world)).pack(side='left',padx=(0,8))
        ttk.Button(controls,text='Generate...',command=lambda:self.guard(self.generate)).pack(side='left',padx=(0,8))
        self.tool=tk.StringVar(value='Jigsaw');ttk.Combobox(controls,textvariable=self.tool,state='readonly',values=['Jigsaw','Tile','Erase patch','Move city','Play here'],width=16).pack(side='left')
        self.zoom=tk.StringVar(value='4');z=ttk.Combobox(controls,textvariable=self.zoom,values=['1','2','4','8','16'],state='readonly',width=4);z.pack(side='left',padx=8);z.bind('<<ComboboxSelected>>',lambda _:self.draw())
        ttk.Label(controls,text='Tile brush: map palette',style='Muted.TLabel',wraplength=170).pack(side='left')
        body=ttk.Panedwindow(self.window,orient='horizontal');body.pack(fill='both',expand=True,padx=8)
        side=ttk.Frame(body);view=ttk.Frame(body);body.add(side,weight=1);body.add(view,weight=5)
        ttk.Label(side,text='JIGSAWS',style='Section.TLabel',padding=6).pack(anchor='w')
        shell=ttk.Frame(side);shell.pack(fill='both',expand=True)
        self.listing=ttk.Treeview(shell,show='tree',selectmode='browse',style='Tiles.Treeview');self.listing.column('#0',width=200)
        scroll=ttk.Scrollbar(shell,command=self.listing.yview);self.listing.configure(yscrollcommand=scroll.set);scroll.pack(side='right',fill='y');self.listing.pack(fill='both',expand=True)
        self.listing.bind('<Double-1>',lambda _:self.guard(self.edit_jigsaw))
        for title,cb in [('New jigsaw',self.new_jigsaw),('Clone jigsaw',self.clone_jigsaw),('Paint jigsaw',self.edit_jigsaw)]:ttk.Button(side,text=title,command=lambda f=cb:self.guard(f)).pack(fill='x',pady=3)
        view.rowconfigure(0,weight=1);view.columnconfigure(0,weight=1)
        self.canvas=tk.Canvas(view,background='#263842',highlightthickness=0)
        sx=ttk.Scrollbar(view,orient='horizontal',command=lambda *args:self.scroll('x',args));sy=ttk.Scrollbar(view,command=lambda *args:self.scroll('y',args))
        self.canvas.configure(xscrollcommand=sx.set,yscrollcommand=sy.set)
        self.canvas.grid(row=0,column=0,sticky='nsew');sx.grid(row=1,column=0,sticky='ew');sy.grid(row=0,column=1,sticky='ns')
        self.canvas.bind('<Configure>',lambda _:self.schedule())
        self.canvas.bind('<Button-1>',lambda e:self.guard(lambda:self.pointer(e,True)))
        self.canvas.bind('<B1-Motion>',lambda e:self.guard(lambda:self.pointer(e,False)))
        self.canvas.bind('<ButtonRelease-1>',lambda _:self.guard(self.finish))
        self.window.bind('<Escape>',lambda _:self.cancel())
        self.window.protocol('WM_DELETE_WINDOW',lambda:self.guard(self.close))
        self.info=tk.StringVar();ttk.Label(self.window,textvariable=self.info,style='Status.TLabel',padding=8).pack(fill='x')
        self.refresh()
        self.draft=register(self,pending=lambda:self.stroke is not None,apply=self.finish,
            capture=lambda:dict(stroke=copy.deepcopy(self.stroke),drag=self.drag),restore=self.restore_draft,priority=30)
    def guard(self, fn):return guard(self,fn)
    def restore_draft(self,state):self.stroke=state['stroke'];self.drag=state['drag'];self.draw()
    def close(self):
        if scope_of(self).confirm_close(self):self.cancel();self.window.destroy()
    @property
    def adventure(self):return self.stroke or self.document.adventure
    def scroll(self,axis,args):getattr(self.canvas,axis+'view')(*args);self.schedule()
    def schedule(self):
        if not self.pending:self.pending=True;self.window.after_idle(self.draw)
    def current_world(self,a=None):return get_world(self.adventure if a is None else a,self.world_id)
    def change_planet(self):
        self.cancel();self.world_id=all_worlds(self.document.adventure)[self.planet.current()]['id'];self.city=None;self.cache={};self.draw()
    def refresh(self):
        worlds=all_worlds(self.document.adventure);self.planet.configure(values=[w['name'] for w in worlds])
        if worlds:
            w=get_world(self.document.adventure,self.world_id);self.world_id=w['id'];self.planet.current(worlds.index(w))
            if self.city not in w['cities']:self.city=None
        selected=self.listing.selection();self.cache={};self.listing.delete(*self.listing.get_children())
        for j in self.document.adventure.get('jigsaws',[]):self.listing.insert('','end',iid=j['id'],text=j['name'])
        if selected and self.listing.exists(selected[0]):self.listing.selection_set(selected[0])
        elif self.listing.get_children():self.listing.selection_set(self.listing.get_children()[0])
        self.draw()
    def new_world(self):
        f=Form(self,'Create world');f.field('name','World');f.field('width',32,label='Width in 8x8 jigsaws');f.field('height',32,label='Height in 8x8 jigsaws')
        def apply(v):
            a=copy.deepcopy(self.document.adventure);self.world_id=create_world(a,self.document.content['package_id'],int(v['width']),int(v['height']),v['name']);self.owner.commit(a)
        f.submit(apply)
    def rename_world(self):
        world=self.current_world()
        if not world:raise EditorError('Create a world first.')
        identity=world['id'];f=Form(self,'Planet name');f.field('name',world['name'])
        def apply(v):
            if not v['name'] or len(v['name'])>63:raise EditorError('Use a planet name of 1-63 characters.')
            a=copy.deepcopy(self.document.adventure);get_world(a,identity)['name']=v['name'];self.owner.commit(a)
        f.submit(apply)
    def generate(self):
        from event_workbench import editor_data
        from scene_tools import generate_world
        world=self.current_world();saved=editor_data(self.document).get('world_generation',{}).get(world['id'],{})
        f=Form(self,'Generate world from weighted jigsaws');f.field('seed',saved.get('seed',1));f.field('edges','Yes' if saved.get('match_edges',True) else 'No',['Yes','No'],label='Match terrain at jigsaw edges')
        for j in self.adventure['jigsaws']:f.field(j['id'],saved.get('weights',{}).get(j['id'],1),label=j['name']+' weight (0 excludes)')
        def apply(v):
            weights={j['id']:int(v[j['id']]) for j in self.adventure['jigsaws'] if int(v[j['id']])}
            generate_world(self.document,world['id'],int(v['seed']),weights,v['edges']=='Yes');self.owner.refresh()
        f.submit(apply)
    def selected_jigsaw(self):
        selected=self.listing.selection()
        return next((j for j in self.adventure.get('jigsaws',[]) if selected and j['id']==selected[0]),None)
    def new_jigsaw(self):
        a=copy.deepcopy(self.document.adventure);identity=add_jigsaw(a,self.document.content['package_id']);self.owner.commit(a);self.listing.selection_set(identity);self.edit_jigsaw()
    def clone_jigsaw(self):
        old=self.selected_jigsaw()
        if old:
            a=copy.deepcopy(self.document.adventure);identity=add_jigsaw(a,self.document.content['package_id'],old['rows'],old['name'][:88]+' copy');self.owner.commit(a);self.listing.selection_set(identity)
    def edit_jigsaw(self):
        j=self.selected_jigsaw()
        if j:return open_view(self,'jigsaw',lambda:JigsawEditor(self,j),j['id'])
    def city_form(self):
        if not all_worlds(self.adventure):raise EditorError('Create a world first.')
        f=Form(self,'Place city on world');f.field('map',self.city or self.adventure['maps'][0]['id'],[m['id'] for m in self.adventure['maps']]);f.field('x',0);f.field('y',0)
        def apply(v):
            a=copy.deepcopy(self.document.adventure);assign_city(a,v['map'],(int(v['x']),int(v['y'])),world_id=self.world_id);self.city=v['map'];self.owner.commit(a)
        f.submit(apply)
    def remove_city(self):
        if self.city:
            a=copy.deepcopy(self.document.adventure);assign_city(a,self.city,enabled=False,world_id=self.world_id);self.city=None;self.owner.commit(a)
    def edit_city(self):
        if not self.city:raise EditorError('Choose Move city and click a city, or place one first.')
        self.owner.scene_index=next(i for i,m in enumerate(self.adventure['maps']) if m['id']==self.city);self.owner.layer_choice.current(0);self.owner.refresh();self.owner.window.lift()
    def picture(self,j,z,tiles):
        key=(j['id'],z)
        if key not in self.cache:
            colors=[]
            for y in range(8*z):
                row=[]
                for x in range(8*z):
                    tile=tiles[j['rows'][y//z][x//z]];sheet=self.owner.graphics.get(tile['sheet'],{})
                    try:rgb=sheet[tile['graphic']][(y%z)*16//z][(x%z)*16//z]
                    except (KeyError,IndexError,TypeError):rgb={'clear':'#28574d','rough':'#947b64','water':'#457caa','woods':'#397557','wall':'#b45a60'}[tile['terrain']]
                    row.append(rgb)
                colors.append('{'+ ' '.join(row)+'}')
            im=tk.PhotoImage(master=self.window,width=8*z,height=8*z);im.put(' '.join(colors));self.cache[key]=im
        return self.cache[key]
    def draw(self):
        self.pending=False
        if not self.window.winfo_exists():return
        self.canvas.delete('all');a=self.adventure
        if not all_worlds(a):
            self.info.set('Create a world, paint jigsaws, then place local maps as cities.');return
        z=int(self.zoom.get());w,h=world_size(a,self.world_id);self.canvas.configure(scrollregion=(0,0,w*z,h*z))
        x0=max(0,int(self.canvas.canvasx(0)//z));y0=max(0,int(self.canvas.canvasy(0)//z))
        x1=min(w,int(self.canvas.canvasx(self.canvas.winfo_width())//z)+2);y1=min(h,int(self.canvas.canvasy(self.canvas.winfo_height())//z)+2)
        tiles={token(t):t for t in a['tiles']};jigs={j['id']:j for j in a['jigsaws']}
        for py in range(y0//8,(y1+7)//8):
            for px in range(x0//8,(x1+7)//8):
                j=jigs[self.current_world(a)['pieces'][py][px]];self.canvas.create_image(px*8*z,py*8*z,image=self.picture(j,z,tiles),anchor='nw')
                if z>=4:self.canvas.create_rectangle(px*8*z,py*8*z,(px+1)*8*z,(py+1)*8*z,outline='#57615f')
        cells=patch_cells(self.current_world(a))
        # Only draw the visible viewport. A 1024-square world must not create
        # a million Tk canvas items every time a brush moves.
        for m in a['maps']:
            if m['id'] not in self.current_world(a)['cities']:continue
            ox,oy=m['origin'];grid=composite(m)
            for y in range(max(0,y0-oy),min(len(grid),y1-oy)):
                for x in range(max(0,x0-ox),min(len(grid[0]),x1-ox)):cells[ox+x,oy+y]=grid[y][x]
        for (x,y),value in cells.items():
            if not(x0<=x<x1 and y0<=y<y1):continue
            tile=tiles[value];im=self.owner.tile_image(tile['sheet'],tile['graphic'],z)
            if im:self.canvas.create_image(x*z,y*z,image=im,anchor='nw')
            else:self.canvas.create_rectangle(x*z,y*z,(x+1)*z,(y+1)*z,fill='#558866',outline='')
        for m in a['maps']:
            if m['id'] not in self.current_world(a)['cities']:continue
            ox,oy=m['origin'];color='#ffff88' if m['id']==self.city else '#ffffff'
            self.canvas.create_rectangle(ox*z,oy*z,(ox+len(m['rows'][0]))*z,(oy+len(m['rows']))*z,outline=color,width=2)
            self.canvas.create_text(ox*z+3,oy*z+3,text=m['name'],fill=color,anchor='nw')
        self.info.set(f"{self.current_world(a)['name']} | {w} x {h} tiles | {len(a['jigsaws'])} jigsaws | {len(self.current_world(a)['cities'])} cities")
    def pointer(self,e,start):
        if not all_worlds(self.adventure):raise EditorError('Create a world first.')
        z=int(self.zoom.get());p=(int(self.canvas.canvasx(e.x)//z),int(self.canvas.canvasy(e.y)//z));w,h=world_size(self.adventure,self.world_id)
        if not(0<=p[0]<w and 0<=p[1]<h):return
        if start:
            self.stroke=copy.deepcopy(self.document.adventure);self.last=p
            if self.tool.get()=='Move city':
                self.drag=None
                for m in self.stroke['maps']:
                    ox,oy=m['origin']
                    if m['id'] in self.current_world(self.stroke)['cities'] and ox<=p[0]<ox+len(m['rows'][0]) and oy<=p[1]<oy+len(m['rows']):self.city=m['id'];self.drag=(p[0]-ox,p[1]-oy);break
            elif self.tool.get()=='Play here':
                self.cancel();self.owner.save();self.owner.parent.launch_player((f"world:{'planet-'+str(all_worlds(self.adventure).index(self.current_world())+1)+'-' if 'worlds' in self.adventure else ''}sector-{p[0]//64}-{p[1]//64}",(p[0]%64)*2,(p[1]%64)*2));return
        if self.stroke is None:return
        if self.tool.get()=='Move city':
            if self.drag:
                m=next(m for m in self.stroke['maps'] if m['id']==self.city);m['origin']=[max(0,min(w-len(m['rows'][0]),p[0]-self.drag[0])),max(0,min(h-len(m['rows']),p[1]-self.drag[1]))]
        elif self.tool.get()=='Jigsaw':
            j=self.selected_jigsaw()
            if j:
                for x,y in line(self.last[0]//8,self.last[1]//8,p[0]//8,p[1]//8):self.current_world(self.stroke)['pieces'][y][x]=j['id']
        else:
            cells=patch_cells(self.current_world(self.stroke));selected=self.owner.brush.curselection()
            if not selected or selected[0]>=len(self.stroke['tiles']):raise EditorError('Select a tile in the map palette first.')
            value=token(self.stroke['tiles'][selected[0]])
            for x,y in line(*self.last,*p):
                if self.tool.get()=='Erase patch':cells.pop((x,y),None)
                else:cells[x,y]=value
            set_patch(self.current_world(self.stroke),cells)
        self.last=p;self.draw()
    def finish(self):
        if self.stroke is None:return
        a=self.stroke
        try:
            if self.drag:assign_city(a,self.city,world_id=self.world_id)
        finally:self.stroke=None;self.drag=None
        self.owner.commit(a)
    def cancel(self):self.stroke=None;self.drag=None;self.draw()


class JigsawEditor:
    def __init__(self,owner,jigsaw):
        self.owner=owner;self.original=copy.deepcopy(jigsaw);self.jigsaw=copy.deepcopy(jigsaw);self.history=[];self.future=[];self.before=None;self.last=None
        self.window=view_window(self,owner,'jigsaw',jigsaw['name'],jigsaw['id']);self.window.geometry('550x480')
        bar=ttk.Frame(self.window,padding=8);bar.pack(fill='x');self.name=tk.StringVar(value=jigsaw['name']);ttk.Entry(bar,textvariable=self.name).pack(side='left',fill='x',expand=True)
        for label,cb in [('Undo',self.undo),('Redo',self.redo),('Apply',self.apply)]:ttk.Button(bar,text=label,command=lambda f=cb:owner.guard(f)).pack(side='left')
        self.tile=ttk.Combobox(self.window,state='readonly',values=[t['id'] for t in owner.adventure['tiles']],width=55);self.tile.pack(pady=8);selected=owner.owner.brush.curselection();self.tile.current(min(selected[0] if selected else 0,len(owner.adventure['tiles'])-1))
        self.canvas=tk.Canvas(self.window,width=320,height=320,highlightthickness=0);self.canvas.pack()
        self.canvas.bind('<Button-1>',lambda e:self.paint(e,True));self.canvas.bind('<B1-Motion>',lambda e:self.paint(e,False));self.canvas.bind('<ButtonRelease-1>',lambda _:self.finish());self.draw()
        self.draft=register(self,pending=lambda:self.jigsaw!=self.original or self.name.get()!=self.original['name'],
            apply=self.apply_pending,capture=self.capture_draft,restore=self.restore_draft,accept=self.accept_draft,priority=50)
        self.window.protocol('WM_DELETE_WINDOW',lambda:guard(self,self.close))
    def capture_draft(self):return dict(jigsaw=copy.deepcopy(self.jigsaw),original=copy.deepcopy(self.original),name=self.name.get(),history=copy.deepcopy(self.history),future=copy.deepcopy(self.future))
    def restore_draft(self,state):
        self.jigsaw=state['jigsaw'];self.original=state['original'];self.name.set(state['name']);self.history=state['history'];self.future=state['future'];self.draw()
    def accept_draft(self):self.original=copy.deepcopy(self.jigsaw)
    def close(self):
        from tkinter import messagebox
        if self.draft and self.draft.pending():
            answer=messagebox.askyesnocancel('Unfinished jigsaw','Apply changes before closing?',parent=self.window)
            if answer is None:return
            if answer:apply_draft(self)
        self.window.destroy()
    def draw(self):
        self.canvas.delete('all');tiles={t['id']:t for t in self.owner.adventure['tiles']}
        for y,row in enumerate(self.jigsaw['rows']):
            for x,value in enumerate(row):
                tile=tiles[value];im=self.owner.owner.tile_image(tile['sheet'],tile['graphic'],40)
                if im:self.canvas.create_image(x*40,y*40,image=im,anchor='nw')
                self.canvas.create_rectangle(x*40,y*40,(x+1)*40,(y+1)*40,outline='#999999')
    def paint(self,e,start):
        p=e.x//40,e.y//40
        if not(0<=p[0]<8 and 0<=p[1]<8):return
        if start:self.before=copy.deepcopy(self.jigsaw);self.last=p
        if self.before is None:return
        for x,y in line(*self.last,*p):self.jigsaw['rows'][y][x]=self.tile.get()
        self.last=p;self.draw()
    def finish(self):
        if self.before is not None and self.before!=self.jigsaw:self.history.append(self.before);self.future=[]
        self.before=None
    def undo(self):
        self.finish()
        if self.history:self.future.append(self.jigsaw);self.jigsaw=self.history.pop();self.draw()
    def redo(self):
        if self.future:self.history.append(self.jigsaw);self.jigsaw=self.future.pop();self.draw()
    def apply_pending(self):
        a=copy.deepcopy(self.owner.document.adventure);old=next(j for j in a['jigsaws'] if j['id']==self.original['id'])
        if old!=self.original:raise EditorError('This jigsaw changed while the dialog was open. Reopen it.')
        self.jigsaw['name']=self.name.get();a['jigsaws'][a['jigsaws'].index(old)]=self.jigsaw;self.owner.owner.commit(a)
    def apply(self):apply_draft(self);self.window.destroy()
