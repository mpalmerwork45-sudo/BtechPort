"""Explicit jigsaw world painting and draggable local-map overlays."""
from __future__ import annotations
import copy
import tkinter as tk
from tkinter import ttk
from adventure_editor import Form
from adventure_editing import composite
from editor_recovery import recoverable_forms
from editor_model import EditorError
from editor_session import guard, register, apply_draft, scope_of
from editor_workspace import view_window,open_view
from world_editing import (create_world, add_jigsaw, assign_city, world_size,
                           patch_cells, set_patch, line, token, all_worlds, get_world)


@recoverable_forms
class WorldEditor:
    def __init__(self, owner):
        self.owner=owner; self.document=owner.document
        self.window=view_window(self,owner,'world','Worlds and planets');self.window.geometry('1000x730');self.window.minsize(840,600)
        self.stroke=None;self.drag=None;self.cache={};self.pending=False;self.last=None;self.city=None;self.world_id=None
        self.selection_rect=None;self.clipboard=None;self.select_start=None
        bar=ttk.Frame(self.window,padding=8);bar.pack(fill='x')
        for title,cb in [('Create world',self.new_world),('Place city',self.city_form),('Edit city',self.edit_city),('Remove city',self.remove_city),('Undo',owner.undo),('Redo',owner.redo),('Save',owner.save),('Validate',owner.validate)]:
            ttk.Button(bar,text=title,width=0,style='Toolbar.TButton',command=lambda f=cb:self.guard(f)).pack(side='left',padx=3)
        controls=ttk.Frame(self.window,padding=(8,0,8,8));controls.pack(fill='x')
        self.planet=ttk.Combobox(controls,state='readonly',width=22);self.planet.pack(side='left',padx=(0,8));self.planet.bind('<<ComboboxSelected>>',lambda _:self.change_planet())
        ttk.Button(controls,text='Rename',command=lambda:self.guard(self.rename_world)).pack(side='left',padx=(0,8))
        ttk.Button(controls,text='Generate...',command=lambda:self.guard(self.generate)).pack(side='left',padx=(0,8))
        self.tool=tk.StringVar(value='Jigsaw')
        ttk.Button(controls,text='Patterns...',command=lambda:self.guard(self.patterns)).pack(side='left',padx=4)
        from editor_canvas import CanvasZoom,DrawingTools
        self.zoom=tk.StringVar(value='4');self.zoom_control=CanvasZoom(controls,self.zoom,self.draw,steps=(1,2,4,8,12,16,24,32));self.zoom_control.pack(side='left',padx=8)
        self.drawing_tools=DrawingTools(self.window,self.tool,[('World',[
            ('Jigsaw','Jigsaw','Paint with the selected 8 by 8 jigsaw.'),('Tile','Tile','Paint individual terrain tiles.'),
            ('Erase patch','Erase','Remove tile patches to reveal the jigsaw beneath.'),('Select','Select','Select a block to copy or save as a pattern.'),
            ('Paste','Paste','Place a copied block or pattern.'),('Move city','Move city','Drag a city overlay to a new location.'),
            ('Play here','Play here','Click to playtest from this location.')])],lambda _:self.guard(self.finish))
        self.drawing_tools.pack(fill='x')
        body=ttk.Panedwindow(self.window,orient='horizontal');body.pack(fill='both',expand=True,padx=8)
        side=ttk.Frame(body);view=ttk.Frame(body);body.add(side,weight=1);body.add(view,weight=5)
        from editor_pickers import ReferenceBox,pick_reference
        self.tile_id=tk.StringVar(value=owner.adventure['tiles'][0]['id'])
        ttk.Label(side,text='Tile brush',style='Section.TLabel').pack(anchor='w',pady=6)
        self.tile_choice=ReferenceBox(side,self,self.tile_id,[t['id'] for t in owner.adventure['tiles']],width=22);self.tile_choice.pack(fill='x')
        ttk.Button(side,text='Browse tiles...',command=lambda:self.owner.graphic_picker(choose=self.tile_id.set,selected=self.tile_id.get())).pack(fill='x',pady=(4,8))
        ttk.Label(side,text='JIGSAWS',style='Section.TLabel',padding=6).pack(anchor='w')
        shell=ttk.Frame(side);shell.pack(fill='both',expand=True)
        self.listing=ttk.Treeview(shell,show='tree',selectmode='browse',style='Tiles.Treeview');self.listing.column('#0',width=200)
        scroll=ttk.Scrollbar(shell,command=self.listing.yview);self.listing.configure(yscrollcommand=scroll.set);scroll.pack(side='right',fill='y');self.listing.pack(fill='both',expand=True)
        self.listing.bind('<Double-1>',lambda _:self.guard(self.edit_jigsaw))
        jigsaw_actions=ttk.Frame(side);jigsaw_actions.pack(side='bottom',fill='x',before=shell)
        for title,cb in [('New jigsaw',self.new_jigsaw),('Clone jigsaw',self.clone_jigsaw),('Paint jigsaw',self.edit_jigsaw)]:ttk.Button(jigsaw_actions,text=title,command=lambda f=cb:self.guard(f)).pack(fill='x',pady=3)
        view.rowconfigure(0,weight=1);view.columnconfigure(0,weight=1)
        self.canvas=tk.Canvas(view,background='#263842',highlightthickness=0)
        sx=ttk.Scrollbar(view,orient='horizontal',command=lambda *args:self.scroll('x',args));sy=ttk.Scrollbar(view,command=lambda *args:self.scroll('y',args))
        self.canvas.configure(xscrollcommand=sx.set,yscrollcommand=sy.set)
        self.canvas.grid(row=0,column=0,sticky='nsew');sx.grid(row=1,column=0,sticky='ew');sy.grid(row=0,column=1,sticky='ns')
        self.canvas.bind('<Configure>',lambda _:self.schedule())
        self.canvas.bind('<Button-1>',lambda e:self.guard(lambda:self.pointer(e,True)))
        self.canvas.bind('<B1-Motion>',lambda e:self.guard(lambda:self.pointer(e,False)))
        self.canvas.bind('<ButtonRelease-1>',lambda _:self.guard(self.finish))
        self.canvas.bind('<Double-1>',lambda e:self.guard(lambda:self.open_city(e)))
        self.canvas.bind('<Control-c>',lambda _:self.guard(self.copy_selection))
        self.canvas.bind('<Control-x>',lambda _:self.guard(self.cut_selection))
        self.canvas.bind('<Control-v>',lambda _:self.tool.set('Paste'))
        self.zoom_control.attach(self.canvas,self.schedule)
        self.window.bind('<Escape>',lambda _:self.cancel())
        self.window.protocol('WM_DELETE_WINDOW',lambda:self.guard(self.close))
        self.info=tk.StringVar();ttk.Label(self.window,textvariable=self.info,style='Status.TLabel',padding=8).pack(side='bottom',fill='x',before=body)
        self.refresh()
        self.draft=register(self,pending=lambda:self.stroke is not None,apply=self.finish,
            capture=lambda:dict(stroke=copy.deepcopy(self.stroke),drag=self.drag),restore=self.restore_draft,priority=30)
        from editor_ui import flow_toolbar
        flow_toolbar(bar);flow_toolbar(controls)
    def guard(self, fn):return guard(self,fn)
    def patterns(self):
        view=self.owner.patterns();view.target=self;view.info.set('World patterns: select up to 64 × 64 tiles, then Save selection. Paste adds terrain patches.');return view
    def copy_selection(self):
        from map_patterns import world_capture
        if not self.selection_rect:raise EditorError('Choose Select and drag a rectangle first; Ctrl+C copies and Ctrl+V pastes.')
        self.clipboard=world_capture(self.document,self.world_id,self.selection_rect);self.info.set('Copied world terrain. Ctrl+V, then click to place.')
    def cut_selection(self):
        from map_patterns import world_paste
        self.copy_selection();a=copy.deepcopy(self.adventure)
        ground=next(t['id'] for t in a['tiles'] if t['terrain']=='clear')
        world_paste(a,self.world_id,*self.selection_rect[:2],[[ground]*len(self.clipboard[0]) for _ in self.clipboard]);self.owner.commit(a)
    def use_pattern(self,rows,name='Pattern',overlay=False):
        from map_patterns import check_rows
        if not self.current_world():raise EditorError('Create or select a world first.')
        check_rows(self.document,rows);self.clipboard=copy.deepcopy(rows);self.tool.set('Paste');self.window.lift();self.canvas.focus_set()
        self.info.set(name+': click to place terrain. City maps must be edited in their local map view.')
    def save_pattern(self):
        from map_patterns import world_capture,save_pattern
        if not self.selection_rect:raise EditorError('Choose Select and drag a rectangle first.')
        rows=world_capture(self.document,self.world_id,self.selection_rect);f=Form(self,'Save world pattern');f.field('name','World pattern');f.submit(lambda v:save_pattern(self.document,rows,v['name']));return f
    def restore_draft(self,state):self.stroke=state['stroke'];self.drag=state['drag'];self.draw()
    def close(self):
        if hasattr(self.window,'workspace'):
            if scope_of(self).confirm_view(self):self.cancel();self.window.workspace.hide(self.window)
            return
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
        self.tile_choice.configure(values=[t['id'] for t in self.document.adventure['tiles']])
        worlds=all_worlds(self.document.adventure);self.planet.configure(values=[w['name'] for w in worlds])
        if worlds:
            w=get_world(self.document.adventure,self.world_id);self.world_id=w['id'];self.planet.current(worlds.index(w))
            if self.city not in w['cities']:self.city=None
        selected=self.listing.selection();self.cache={};self.listing.delete(*self.listing.get_children())
        for j in self.document.adventure.get('jigsaws',[]):self.listing.insert('','end',iid=j['id'],text=j['name'])
        if selected and self.listing.exists(selected[0]):self.listing.selection_set(selected[0])
        elif self.listing.get_children():self.listing.selection_set(self.listing.get_children()[0])
        self.draw()
    def open_city(self,event):
        z=int(self.zoom.get());x=self.canvas.canvasx(event.x)/z;y=self.canvas.canvasy(event.y)/z
        world=self.current_world()
        if not world:return
        for scene in self.adventure['maps']:
            ox,oy=scene['origin']
            if scene['id'] in world['cities'] and ox<=x<ox+len(scene['rows'][0]) and oy<=y<oy+len(scene['rows']):
                self.cancel();self.owner.map_choice.current(self.adventure['maps'].index(scene));self.owner.change_map();self.owner.tabs.select(self.owner.map_tab);self.owner.window.lift();return
    def new_world(self):
        from world_editing import ORIGINAL_WORLD_JIGSAWS
        f=Form(self,'Create world');f.field('name','World');f.field('width',ORIGINAL_WORLD_JIGSAWS,label='Width in 8x8 jigsaws');f.field('height',ORIGINAL_WORLD_JIGSAWS,label='Height in 8x8 jigsaws')
        f.field('cities','Yes' if not all_worlds(self.adventure) else 'No',['Yes','No'],label='Place current local maps as cities')
        ttk.Label(f.body,text='Original CHI size: 1024 × 1024 tiles. Planets currently share 256 sectors; choose smaller dimensions when dividing that space between planets.',wraplength=480).grid(row=f.row,column=0,columnspan=3,padx=10,pady=8);f.row+=1
        def apply(v):
            a=copy.deepcopy(self.document.adventure);world_id=create_world(a,self.document.content['package_id'],int(v['width']),int(v['height']),v['name'])
            if v['cities']=='Yes':
                for scene in a['maps']:
                    if not any(scene['id'] in w['cities'] for w in all_worlds(a)):assign_city(a,scene['id'],world_id=world_id)
            self.owner.commit(a);self.world_id=world_id;self.refresh()
        f.submit(apply,'Create world')
        return f
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
        if self.selection_rect:
            x,y,xx,yy=self.selection_rect;self.canvas.create_rectangle(x*z,y*z,(xx+1)*z,(yy+1)*z,outline='#ffdb6e',width=2)
        self.info.set(f"{self.current_world(a)['name']} | {w} x {h} tiles | {len(a['jigsaws'])} jigsaws | {len(self.current_world(a)['cities'])} cities")
    def pointer(self,e,start):
        if not all_worlds(self.adventure):raise EditorError('Create a world first.')
        z=int(self.zoom.get());p=(int(self.canvas.canvasx(e.x)//z),int(self.canvas.canvasy(e.y)//z));w,h=world_size(self.adventure,self.world_id)
        if not(0<=p[0]<w and 0<=p[1]<h):return
        if start:self.canvas.focus_set()
        if self.tool.get()=='Select':
            if start:self.select_start=p
            if self.select_start:
                self.selection_rect=(min(p[0],self.select_start[0]),min(p[1],self.select_start[1]),max(p[0],self.select_start[0]),max(p[1],self.select_start[1]));self.draw()
            return
        if self.tool.get()=='Paste':
            if start and self.clipboard:
                from map_patterns import world_paste
                a=copy.deepcopy(self.document.adventure);world_paste(a,self.world_id,*p,self.clipboard);self.owner.commit(a)
            return
        if start:
            if self.tool.get() not in ('Move city','Play here') and not (getattr(e,'state',0)&4):
                for city in self.document.adventure['maps']:
                    ox,oy=city['origin']
                    if city['id'] in self.current_world()['cities'] and ox<=p[0]<ox+len(city['rows'][0]) and oy<=p[1]<oy+len(city['rows']):
                        self.city=city['id'];self.draw();return
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
            cells=patch_cells(self.current_world(self.stroke))
            tile=next((t for t in self.stroke['tiles'] if t['id']==self.tile_id.get()),None)
            if tile is None:raise EditorError('Choose a tile in this world view first.')
            value=token(tile)
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


@recoverable_forms
class JigsawEditor:
    shared_art = True
    def __init__(self,owner,jigsaw):
        self.owner=owner;self.document=owner.document;self.original=copy.deepcopy(jigsaw);self.jigsaw=copy.deepcopy(jigsaw);self.history=[];self.future=[];self.before=None;self.last=None;self.clipboard=None;self.start=None
        self.window=view_window(self,owner,'jigsaw',jigsaw['name'],jigsaw['id']);self.window.geometry('760x620')
        bar=ttk.Frame(self.window,padding=8);bar.pack(fill='x');self.name=tk.StringVar(value=jigsaw['name']);ttk.Entry(bar,textvariable=self.name).pack(side='left',fill='x',expand=True)
        for label,cb in [('Undo',self.undo),('Redo',self.redo),('Apply',self.apply)]:ttk.Button(bar,text=label,command=lambda f=cb:owner.guard(f)).pack(side='left')
        controls=ttk.Frame(self.window,padding=8);controls.pack(fill='x')
        self.tile=ttk.Combobox(controls,state='readonly',values=[t['id'] for t in owner.adventure['tiles']],width=28);self.tile.pack(side='left');selected=owner.owner.brush.curselection();self.tile.current(min(selected[0] if selected else 0,len(owner.adventure['tiles'])-1))
        ttk.Button(controls,text='Choose tile...',command=lambda:guard(self,self.choose_tile)).pack(side='left',padx=3)
        self.tool=tk.StringVar(value='Paint')
        ttk.Button(controls,text='Patterns...',command=lambda:guard(self,self.patterns)).pack(side='left',padx=3)
        from editor_canvas import CanvasZoom,DrawingTools
        self.zoom=tk.StringVar(value='40');self.zoom_control=CanvasZoom(controls,self.zoom,self.draw,steps=(8,16,24,32,40,48,64,96));self.zoom_control.pack(side='left',padx=6)
        self.drawing_tools=DrawingTools(self.window,self.tool,[('Jigsaw',[
            ('Paint','Paint','Drag to paint tiles.'),('Line','Line','Drag a straight line of tiles.'),
            ('Rectangle','Rectangle','Drag a filled rectangle.'),('Fill','Fill','Fill a connected area.'),
            ('Eyedropper','Pick tile','Pick the tile under the pointer.'),('Paste','Paste','Place a pattern from the Pattern Library.')])],lambda _:guard(self,self.finish))
        self.drawing_tools.pack(fill='x')
        from editor_ui import flow_toolbar
        flow_toolbar(bar);flow_toolbar(controls)
        ttk.Label(self.window,text='Drag to draw. Right-click a cell to choose, create, clone or edit its tile.\nJigsaws remain 8 × 8 tiles, matching the game’s world format.',padding=8,wraplength=650).pack(side='bottom',fill='x')
        shell=ttk.Frame(self.window);shell.pack(fill='both',expand=True)
        self.canvas=tk.Canvas(shell,width=320,height=320,highlightthickness=0,background='#273b45',scrollregion=(0,0,320,320))
        sx=ttk.Scrollbar(shell,orient='horizontal',command=self.canvas.xview);sy=ttk.Scrollbar(shell,command=self.canvas.yview);sx.pack(side='bottom',fill='x');sy.pack(side='right',fill='y');self.canvas.pack(fill='both',expand=True);self.canvas.configure(xscrollcommand=sx.set,yscrollcommand=sy.set)
        self.canvas.bind('<Button-1>',lambda e:guard(self,lambda:self.paint(e,True)));self.canvas.bind('<B1-Motion>',lambda e:guard(self,lambda:self.paint(e,False)));self.canvas.bind('<ButtonRelease-1>',lambda _:guard(self,self.finish))
        self.canvas.bind('<Button-3>',lambda e:guard(self,lambda:self.context(e)));self.window.bind('<Escape>',lambda _:self.cancel())
        self.zoom_control.attach(self.canvas);self.draw()
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
        z=int(self.zoom.get());self.canvas.configure(scrollregion=(0,0,8*z,8*z))
        self.tile.configure(values=list(tiles))
        if self.tile.get() not in tiles:self.tile.current(0)
        for y,row in enumerate(self.jigsaw['rows']):
            for x,value in enumerate(row):
                tile=tiles.get(value)
                if tile is None:continue
                im=self.owner.owner.tile_image(tile['sheet'],tile['graphic'],z)
                if im:self.canvas.create_image(x*z,y*z,image=im,anchor='nw')
                self.canvas.create_rectangle(x*z,y*z,(x+1)*z,(y+1)*z,outline='#999999')
    def paint(self,e,start):
        z=int(self.zoom.get());p=int(self.canvas.canvasx(e.x)//z),int(self.canvas.canvasy(e.y)//z)
        if not(0<=p[0]<8 and 0<=p[1]<8):return
        tool=self.tool.get()
        if tool=='Eyedropper':self.tile.set(self.jigsaw['rows'][p[1]][p[0]]);return
        if start:self.before=copy.deepcopy(self.jigsaw);self.last=self.start=p
        if self.before is None:return
        if tool in ('Line','Rectangle'):self.jigsaw=copy.deepcopy(self.before)
        if tool=='Fill':
            from world_editing import flood
            flood(self.jigsaw['rows'],*p,self.tile.get())
        elif tool=='Paste':
            if start and self.clipboard:
                if p[0]+len(self.clipboard[0])>8 or p[1]+len(self.clipboard)>8:self.before=None;raise EditorError('The complete pattern must fit in this 8 × 8 jigsaw.')
                for y,row in enumerate(self.clipboard):
                    for x,value in enumerate(row):
                        if value!=' ':self.jigsaw['rows'][p[1]+y][p[0]+x]=value
        else:
            points=((x,y) for y in range(min(self.start[1],p[1]),max(self.start[1],p[1])+1) for x in range(min(self.start[0],p[0]),max(self.start[0],p[0])+1)) if tool=='Rectangle' else line(*(self.start if tool=='Line' else self.last),*p)
            for x,y in points:self.jigsaw['rows'][y][x]=self.tile.get()
        self.last=p;self.draw()
    def cancel(self):
        if self.before is not None:self.jigsaw=self.before;self.before=None;self.draw()
        else:self.tool.set('Paint')
    def choose_tile(self):return self.owner.owner.graphic_picker(choose=self.tile.set,selected=self.tile.get())
    def context(self,e):
        z=int(self.zoom.get());x,y=int(self.canvas.canvasx(e.x)//z),int(self.canvas.canvasy(e.y)//z)
        if not(0<=x<8 and 0<=y<8):return
        from construction_editor import tile_menu
        def assign(value):
            self.before=copy.deepcopy(self.jigsaw);self.jigsaw['rows'][y][x]=value;self.tile.set(value);self.finish();self.draw()
        tile_menu(self,self.owner.owner,self.jigsaw['rows'][y][x],assign,e)
    def patterns(self):
        view=self.owner.owner.patterns();view.target=self;view.info.set('Save this jigsaw as a pattern, or use an existing pattern up to 8 × 8.');return view
    def use_pattern(self,rows,name='Pattern',overlay=False):
        from map_patterns import check_rows
        check_rows(self.document,rows)
        if len(rows)>8 or len(rows[0])>8:raise EditorError('Choose a pattern no larger than 8 × 8 tiles for a jigsaw.')
        self.clipboard=copy.deepcopy(rows);self.tool.set('Paste');self.window.lift()
    def save_pattern(self):
        from map_patterns import save_pattern
        self.finish();f=Form(self,'Save jigsaw pattern');f.field('name',self.name.get());f.submit(lambda v:save_pattern(self.document,self.jigsaw['rows'],v['name']));return f
    def finish(self):
        if self.before is not None and self.before!=self.jigsaw:self.history.append(self.before);self.future=[]
        self.before=None
        from editor_session import publish_art
        publish_art(self)
    def undo(self):
        if hasattr(self.window,'workspace'):return self.window.workspace.edit_history(False)
        self.finish()
        if self.history:self.future.append(self.jigsaw);self.jigsaw=self.history.pop();self.draw()
    def redo(self):
        if hasattr(self.window,'workspace'):return self.window.workspace.edit_history(True)
        if self.future:self.history.append(self.jigsaw);self.jigsaw=self.future.pop();self.draw()
    def apply_pending(self):
        a=copy.deepcopy(self.owner.document.adventure);old=next(j for j in a['jigsaws'] if j['id']==self.original['id'])
        if old!=self.original:raise EditorError('This jigsaw changed while the dialog was open. Reopen it.')
        self.jigsaw['name']=self.name.get();a['jigsaws'][a['jigsaws'].index(old)]=self.jigsaw;self.owner.owner.commit(a)
    def apply(self):apply_draft(self);self.window.destroy()
