"""Native CHI world painting, with actual TINYLAND and resolved terrain tiles.

The overview and detail view use the same native snapshot as gameplay. Brushes
store explicit overrides; they never replace the original generator or assets.
"""
from __future__ import annotations
import copy
import tkinter as tk
from tkinter import ttk
from adventure_editor import Form,scroll_frame
from editor_workspace import open_view,view_window
from editor_session import guard,register
from editor_canvas import CanvasZoom,DrawingTools
from editor_model import EditorError
from chi_spatial import data,change,move_town,find
from world_editing import line


def raster_photo(parent,image):
    """Tk reads RGB PPM directly; Pillow's optional ImageTk is not required."""
    rgb=image.convert('RGB');header=f'P6\n{rgb.width} {rgb.height}\n255\n'.encode('ascii')
    return tk.PhotoImage(master=parent,data=header+rgb.tobytes(),format='PPM')


def open_world(owner):
    view=open_view(owner,'chi-world',lambda:ChiWorld(owner));owner.world_editor=view;return view


class ChiWorld:
    def __init__(self,owner):
        self.owner=owner;self.document=owner.document;self.window=view_window(self,owner,'chi-world','CHI world and jigsaws')
        self.window.geometry('1180x800');self.status=tk.StringVar(value='Loading native world...')
        self.generation=0;self.image=None;self.drag=None;self.selected=None;self.job=None;self.pending=False
        self.stroke=None;self.last=None;self.start=None;self.hover=None;self.problem_location=None;self.photos=[]
        bar=ttk.Frame(self.window,padding=6);bar.pack(fill='x')
        for title,cb in [('Save',owner.save),('Undo',owner.undo),('Redo',owner.redo),('Refresh',self.refresh),
                         ('Place / move town',self.town),('Edit town map',self.edit_town),
                         ('Advanced generator',self.generator),('Join bindings',self.joins),('TINYLAND art',self.tinyland_art)]:
            ttk.Button(bar,text=title,command=lambda fn=cb:guard(self,fn)).pack(side='left',padx=3)
        from editor_ui import flow_toolbar
        flow_toolbar(bar)
        self.tool=tk.StringVar(value='Terrain')
        self.tools=DrawingTools(self.window,self.tool,[('World',[
            ('Terrain','Terrain / TINYLAND','Draw terrain levels; native joins and TINYLAND update together.'),
            ('Jigsaw','Jigsaw','Stamp the selected 8 by 8 piece; remove covered individual tile patches.'),
            ('Tile','Tile','Paint exact terrain tiles in the detailed view.'),
            ('Erase','Restore generated','Remove all overrides in an 8 by 8 block.'),
            ('Pick','Pick','Pick a tile, terrain level and placed jigsaw from the world.'),
            ('Move town','Move town','Drag towns on the original 64-tile grid.')])],self.choose_tool)
        self.tools.pack(fill='x')
        controls=ttk.Frame(self.window,padding=6);controls.pack(fill='x')
        self.view=tk.StringVar(value='TINYLAND');combo=ttk.Combobox(controls,textvariable=self.view,values=['TINYLAND','Detailed tiles'],state='readonly',width=15)
        combo.pack(side='left');combo.bind('<<ComboboxSelected>>',lambda _:self.change_view())
        self.zoom=tk.StringVar(value='1');self.zoom_control=CanvasZoom(controls,self.zoom,self.draw,base=16,steps=(1,2,4,8,16,24,32,48));self.zoom_control.pack(side='left',padx=8)
        self.shape=tk.StringVar(value='Brush');ttk.Combobox(controls,textvariable=self.shape,values=['Brush','Line','Rectangle'],state='readonly',width=11).pack(side='left',padx=3)
        ttk.Label(controls,text='Brush size').pack(side='left');self.size=tk.StringVar(value='1');ttk.Combobox(controls,textvariable=self.size,values=['1','2','4','8'],state='readonly',width=3).pack(side='left',padx=3)
        self.show_towns=tk.BooleanVar(value=True);ttk.Checkbutton(controls,text='Town overlays',variable=self.show_towns,command=self.refresh).pack(side='left',padx=6)
        self.ruined=tk.BooleanVar(value=False);ttk.Checkbutton(controls,text='Ruined Citadel',variable=self.ruined,command=self.refresh).pack(side='left',padx=6)
        flow_toolbar(controls)
        self.info=ttk.Label(self.window,textvariable=self.status,wraplength=1100,padding=6);self.info.pack(side='bottom',fill='x')
        self.info.bind('<Configure>',lambda e:self.info.configure(wraplength=max(180,e.width-12)))
        host=ttk.Panedwindow(self.window,orient='horizontal');host.pack(fill='both',expand=True)
        # Keep jigsaw actions and town selection reachable on smaller screens.
        # A plain packed column lets its fixed previews squeeze both lists
        # completely below the viewport; this side panel has its own scrollbar.
        side_shell,side=scroll_frame(host,width=250,height=510);view=ttk.Frame(host)
        host.add(side_shell,weight=1);host.add(view,weight=5);self.side_shell=side_shell
        self.overview=tk.Canvas(side,width=192,height=192,background='#263842',highlightthickness=1)
        self.overview.pack();self.overview.bind('<Button-1>',self.navigate);self.overview.bind('<B1-Motion>',self.navigate)
        ttk.Label(side,text='Click overview to navigate. Ctrl + wheel zooms.',wraplength=235).pack(fill='x',pady=4)
        brushes=ttk.Frame(side);brushes.pack(fill='x')
        ttk.Label(brushes,text='Terrain level').grid(row=0,column=0,sticky='w');self.level=tk.StringVar(value='32')
        # Only these levels have a complete original TINYLAND glyph family.
        # Preserve higher imported/API values, but do not offer a normal brush
        # that would paint black overhead gaps with the unmodified mini atlas.
        level_names={str(n):f'{n} '+name for n,name in ((0,'Water / shore'),(16,'Open ground'),(32,'Light woods'),(48,'Dense woods'),(64,'Rocks'))}
        levels=ttk.Combobox(brushes,values=list(level_names.values()),state='readonly',width=17);self.level_choice=levels
        levels.grid(row=1,column=0,sticky='ew');levels.set(level_names[self.level.get()]);brushes.columnconfigure(0,weight=1)
        levels.bind('<<ComboboxSelected>>',lambda _:(self.level.set(levels.get().split(' ',1)[0]),self.brush_changed()))
        self.level.trace_add('write',lambda *_:levels.set(level_names.get(self.level.get(),self.level.get()+' (advanced)')))
        ttk.Label(brushes,text='Jigsaw orientation').grid(row=2,column=0,sticky='w');self.flip=tk.StringVar(value='0')
        orientations={'0':'0 Normal','1':'1 Flip Y','2':'2 Flip X','3':'3 Flip X and Y'}
        flip=ttk.Combobox(brushes,values=list(orientations.values()),state='readonly',width=17);self.flip_choice=flip
        flip.grid(row=3,column=0,sticky='ew');flip.set(orientations['0'])
        flip.bind('<<ComboboxSelected>>',lambda _:(self.flip.set(flip.get().split(' ',1)[0]),self.brush_changed()))
        self.flip.trace_add('write',lambda *_:flip.set(orientations.get(self.flip.get(),self.flip.get())))
        self.brush_canvas=tk.Canvas(side,width=128,height=128,background='#263842',highlightthickness=0);self.brush_canvas.pack(pady=4)
        self.tile_id=tk.StringVar(value=owner.adventure['tiles'][0]['id'])
        ttk.Button(side,text='Choose tile...',command=lambda:guard(self,self.choose_tile)).pack(fill='x')
        ttk.Label(side,text='Jigsaws',style='Section.TLabel').pack(anchor='w',pady=(6,2))
        box=ttk.Frame(side);box.pack(fill='both',expand=True)
        self.listing=ttk.Treeview(box,show='tree',selectmode='browse',height=5);self.listing.column('#0',width=220)
        sy=ttk.Scrollbar(box,command=self.listing.yview);sy.pack(side='right',fill='y');self.listing.configure(yscrollcommand=sy.set);self.listing.pack(fill='both',expand=True)
        self.listing.bind('<<TreeviewSelect>>',lambda _:self.brush_changed());self.listing.bind('<Double-1>',lambda _:guard(self,self.edit_jigsaw))
        buttons=ttk.Frame(side);buttons.pack(fill='x')
        for title,cb in [('New',self.new_jigsaw),('Clone',self.clone_jigsaw),('Edit',self.edit_jigsaw)]:ttk.Button(buttons,text=title,command=lambda fn=cb:guard(self,fn)).pack(side='left')
        flow_toolbar(buttons)
        ttk.Label(side,text='Towns / islands',style='Section.TLabel').pack(anchor='w',pady=(6,2))
        self.towns=ttk.Treeview(side,show='tree',selectmode='browse',height=4);self.towns.column('#0',width=220);self.towns.pack(fill='x')
        self.towns.bind('<<TreeviewSelect>>',lambda _:self.select_town());self.towns.bind('<Double-1>',lambda _:guard(self,self.edit_town))
        self.canvas=tk.Canvas(view,background='#263842',highlightthickness=0)
        sx=ttk.Scrollbar(view,orient='horizontal',command=lambda *a:self.scroll('x',a));sy=ttk.Scrollbar(view,command=lambda *a:self.scroll('y',a))
        sx.pack(side='bottom',fill='x');sy.pack(side='right',fill='y');self.canvas.pack(fill='both',expand=True);self.canvas.configure(xscrollcommand=sx.set,yscrollcommand=sy.set)
        self.canvas.bind('<Configure>',lambda _:self.schedule());self.canvas.bind('<Button-1>',lambda e:guard(self,lambda:self.pointer(e,True)))
        self.canvas.bind('<B1-Motion>',lambda e:guard(self,lambda:self.pointer(e,False)));self.canvas.bind('<ButtonRelease-1>',lambda _:guard(self,self.finish))
        self.canvas.bind('<Motion>',self.motion);self.canvas.bind('<Leave>',lambda _:self.clear_hover())
        self.canvas.bind('<Button-3>',lambda e:guard(self,lambda:self.context(e)));self.canvas.bind('<Double-1>',lambda e:guard(self,lambda:self.open_town(e)))
        self.canvas.bind('<Button-2>',lambda e:self.canvas.scan_mark(e.x,e.y));self.canvas.bind('<B2-Motion>',self.pan)
        self.canvas.bind('<Escape>',lambda _:self.cancel())
        self.zoom_control.attach(self.canvas,self.schedule)
        self.draft=register(self,pending=lambda:self.stroke is not None or self.drag is not None,apply=self.finish,
            capture=self.capture_draft,restore=self.restore_draft,priority=30)
        self.refresh()
    @property
    def adventure(self):return self.document.adventure
    def guard(self,fn):return guard(self,fn)
    def choose_tool(self,_=None):
        self.finish()
        if self.tool.get()=='Tile':self.view.set('Detailed tiles');self.zoom_control.set(max(8,int(self.zoom.get())))
        self.brush_changed();self.draw()
    def change_view(self):
        if self.view.get()=='Detailed tiles':self.zoom_control.set(max(8,int(self.zoom.get())))
        self.draw()
    def choose_tile(self):return self.owner.graphic_picker(choose=self.set_tile,selected=self.tile_id.get())
    def set_tile(self,identity):self.tile_id.set(identity);self.tool.set('Tile');self.choose_tool()
    def refresh(self):
        value=data(self.document);self.value=value;chosen=self.listing.selection();position=self.listing.yview()
        self.towns.delete(*self.towns.get_children());self.listing.delete(*self.listing.get_children())
        for m in value['maps']:
            if m['slot']<=13 and m['slot']!=11:self.towns.insert('','end',iid=m['id'],text=f"{m['name']} ({m['origin'][0]}, {m['origin'][1]})")
        for j in value['world']['jigsaws']:self.listing.insert('','end',iid=j['id'],text=j['name'])
        if chosen and self.listing.exists(chosen[0]):self.listing.selection_set(chosen[0])
        elif value['world']['jigsaws']:self.listing.selection_set(value['world']['jigsaws'][0]['id'])
        if position:self.listing.yview_moveto(position[0])
        self.generation+=1;generation=self.generation;revision=self.document.revision;candidate=self.document.worker_copy()
        ruined=self.ruined.get();underlay=not self.show_towns.get()
        if self.job:self.job.cancelled.set()
        self.status.set('Updating actual terrain and TINYLAND from the game...')
        def ready(image):
            if generation!=self.generation or revision!=self.document.revision:return
            from PIL import Image
            self.image=image;self.job=None;self.tile_cache={};mini=image['mini'];self.mini=Image.frombytes('P',(mini['width'],mini['height']),mini['pixels'])
            self.mini.putpalette(mini['palette_bytes']);self.mini=self.mini.convert('RGB');self.brush_changed();self.draw()
            self.status.set('1,024 x 1,024 tiles. Terrain draws 8 x 8 blocks and automatically joins them; Tile edits detail. Changes affect gameplay. Towns remain above terrain.')
        from chi_resources import world_editor_preview
        def render(cancel):
            from chi_import import ImportCancelled
            try:return world_editor_preview(candidate,ruined,underlay,cancel)
            except ImportCancelled:
                # A newer edit replaced this preview. The task manager checks
                # cancellation after obtaining its future, so retire normally
                # rather than turning an expected stale job into an error box.
                if cancel.is_set():return None
                raise
        workspace=getattr(self.window,'workspace',None)
        if workspace:self.job=workspace.tasks.submit('Render editable CHI world',self,render,ready)
        else:ready(world_editor_preview(candidate,ruined,underlay))
    def schedule(self):
        if not self.pending:self.pending=True;self.window.after_idle(self.draw)
    def scroll(self,axis,args):getattr(self.canvas,axis+'view')(*args);self.schedule()
    def pan(self,e):self.canvas.scan_dragto(e.x,e.y,gain=1);self.schedule()
    def navigate(self,e):
        z=int(self.zoom.get());x=max(0,min(1023,e.x*1024/192));y=max(0,min(1023,e.y*1024/192))
        self.canvas.xview_moveto((x*z-self.canvas.winfo_width()/2)/(1024*z));self.canvas.yview_moveto((y*z-self.canvas.winfo_height()/2)/(1024*z));self.draw()
    def point(self,e):
        z=int(self.zoom.get());return int(self.canvas.canvasx(e.x)//z),int(self.canvas.canvasy(e.y)//z)
    def draw(self):
        self.pending=False
        if not self.canvas.winfo_exists():return
        self.canvas.delete('all');self.photos=[];z=int(self.zoom.get());self.canvas.configure(scrollregion=(0,0,1024*z,1024*z))
        if not self.image:return
        x0=max(0,int(self.canvas.canvasx(0)//z));y0=max(0,int(self.canvas.canvasy(0)//z))
        x1=min(1024,int(self.canvas.canvasx(self.canvas.winfo_width())//z)+2);y1=min(1024,int(self.canvas.canvasy(self.canvas.winfo_height())//z)+2)
        if x1<=x0 or y1<=y0:return
        if self.view.get()=='TINYLAND':
            from PIL import Image
            photo=raster_photo(self.window,self.mini.crop((x0,y0,x1,y1)).resize(((x1-x0)*z,(y1-y0)*z),Image.Resampling.NEAREST))
            self.photos.append(photo);self.canvas.create_image(x0*z,y0*z,image=photo,anchor='nw')
        else:
            # Render visible cells only. Zooming out still uses a single raster,
            # rather than creating a million Tk items for the full planet.
            from PIL import Image
            tiles=self.value['tiles'];grid=self.image['grid'];graphics=self.owner.graphics
            raster=Image.new('RGB',((x1-x0)*z,(y1-y0)*z))
            for y in range(y0,y1):
                for x in range(x0,x1):
                    handle=grid[y*1024+x];key=(handle,z)
                    if key not in self.tile_cache:
                        t=tiles[handle] if handle<len(tiles) else None
                        try:
                            colors=graphics[t['sheet']][t['graphic']]
                            raw=b''.join(bytes.fromhex(color.lstrip('#')[:6]) for row in colors for color in row)
                            tile=Image.frombytes('RGB',(16,16),raw).resize((z,z),Image.Resampling.NEAREST)
                        except (KeyError,IndexError,TypeError):tile=Image.new('RGB',(z,z),'magenta')
                        self.tile_cache[key]=tile
                    raster.paste(self.tile_cache[key],((x-x0)*z,(y-y0)*z))
            photo=raster_photo(self.window,raster)
            self.photos.append(photo);self.canvas.create_image(x0*z,y0*z,image=photo,anchor='nw')
        if z>=4:
            for x in range(x0//8*8,x1,8):self.canvas.create_line(x*z,y0*z,x*z,y1*z,fill='#56646c')
            for y in range(y0//8*8,y1,8):self.canvas.create_line(x0*z,y*z,x1*z,y*z,fill='#56646c')
        if self.show_towns.get():
            for m in self.value['maps']:
                if m['slot']>13 or m['slot']==(1 if self.ruined.get() else 11):continue
                x,y=m['origin'];color='#ffff66' if m['id']==self.selected else '#ffffff'
                if self.drag and self.drag['id']==m['id']:x,y=self.drag['at']
                self.canvas.create_rectangle(x*z,y*z,(x+m['width'])*z,(y+m['height'])*z,outline=color,width=2)
                self.canvas.create_text(x*z+3,y*z+3,text=m['name'],fill=color,anchor='nw')
        self.draw_stroke(z,x0,y0,x1,y1);self.draw_hover()
        if self.problem_location:
            x,y=self.problem_location;self.canvas.create_rectangle((x-.5)*z,(y-.5)*z,(x+.5)*z,(y+.5)*z,outline='#ffdb6e',width=3,tags='problem-location')
        from PIL import Image
        self.overview_photo=raster_photo(self.window,self.mini.resize((192,192),Image.Resampling.NEAREST))
        self.overview.delete('all');self.overview.create_image(0,0,image=self.overview_photo,anchor='nw')
        self.overview.create_rectangle(x0*192/1024,y0*192/1024,x1*192/1024,y1*192/1024,outline='#ffff00',width=2)
    def draw_stroke(self,z,x0,y0,x1,y1):
        if not self.stroke:return
        unit=self.stroke['unit'];kind=self.stroke['tool']
        for x,y in self.stroke['points']:
            x*=unit;y*=unit
            if x>=x1 or y>=y1 or x+unit<=x0 or y+unit<=y0:continue
            if kind=='Tile':
                t=find(self.value['tiles'],self.stroke['tile']);photo=self.owner.tile_image(t['sheet'],t['graphic'],z)
                if photo:self.canvas.create_image(x*z,y*z,image=photo,anchor='nw')
            elif kind=='Jigsaw' and self.view.get()=='Detailed tiles':
                from chi_spatial import resolved_jigsaw
                rows=resolved_jigsaw(self.value,self.stroke['jigsaw'],self.stroke['level'],self.stroke['flip'])
                for yy,row in enumerate(rows):
                    for xx,identity in enumerate(row):
                        t=find(self.value['tiles'],identity);photo=self.owner.tile_image(t['sheet'],t['graphic'],z)
                        if photo:self.canvas.create_image((x+xx)*z,(y+yy)*z,image=photo,anchor='nw')
            self.canvas.create_rectangle(x*z,y*z,(x+unit)*z,(y+unit)*z,outline='#ffe066',width=2)
    def town_at(self,p):
        if not self.show_towns.get():return None
        return next((m for m in self.value['maps'] if m['slot']<=13 and m['slot']!=(1 if self.ruined.get() else 11)
                     and m['origin'][0]<=p[0]<m['origin'][0]+m['width'] and m['origin'][1]<=p[1]<m['origin'][1]+m['height']),None)
    def pointer(self,e,start):
        p=self.point(e)
        if not self.image or not(0<=p[0]<1024 and 0<=p[1]<1024):return
        tool=self.tool.get()
        if start:self.canvas.focus_set()
        if tool=='Pick':
            if start:self.pick(p)
            return
        if tool=='Move town':
            if start:
                town=self.town_at(p)
                if town:self.selected=town['id'];self.towns.selection_set(town['id']);self.drag=dict(id=town['id'],at=town['origin'][:],offset=[p[i]-town['origin'][i] for i in range(2)])
            elif self.drag:self.drag['at']=[max(0,min(960,round((p[i]-self.drag['offset'][i])/64)*64)) for i in range(2)]
            self.draw();return
        unit=1 if tool=='Tile' else 8;point=(p[0]//unit,p[1]//unit)
        if start:
            j=self.selected_jigsaw()
            self.stroke=dict(tool=tool,unit=unit,points=set(),tile=self.tile_id.get(),jigsaw=j['id'] if j else None,level=int(self.level.get()),flip=int(self.flip.get()),skipped=False)
            self.last=self.start=point
        if self.stroke is None:return
        if self.shape.get() in ('Line','Rectangle'):self.stroke['points']=set()
        pts=((x,y) for y in range(min(self.start[1],point[1]),max(self.start[1],point[1])+1) for x in range(min(self.start[0],point[0]),max(self.start[0],point[0])+1)) if self.shape.get()=='Rectangle' else line(*(self.start if self.shape.get()=='Line' else self.last),*point)
        for x,y in pts:
            for dy in range(int(self.size.get())):
                for dx in range(int(self.size.get())):
                    xx,yy=x+dx,y+dy
                    if not(0<=xx<1024//unit and 0<=yy<1024//unit):continue
                    if self.town_at((xx*unit,yy*unit)):
                        self.stroke['skipped']=True;continue
                    self.stroke['points'].add((xx,yy))
        self.last=point;self.draw()
        self.status.set(f"{tool}: {len(self.stroke['points'])} {'tiles' if unit==1 else 'blocks'}; release to apply. Escape cancels."+(' Towns skipped; double-click to edit their map.' if self.stroke['skipped'] else ''))
    def finish(self):
        if self.drag:
            drag=self.drag;self.drag=None;change(self.document,lambda a:move_town(a,drag['id'],*drag['at']),'Move CHI town');self.owner.refresh();return
        if not self.stroke:return
        stroke=self.stroke;self.stroke=None
        if not stroke['points']:self.draw();return
        from chi_spatial import paint_world_terrain,place_world_jigsaw,paint_world_tiles,erase_world
        def edit(a):
            if stroke['tool']=='Terrain':paint_world_terrain(a,stroke['points'],stroke['level'])
            elif stroke['tool']=='Jigsaw':place_world_jigsaw(a,stroke['points'],stroke['jigsaw'],stroke['level'],stroke['flip'])
            elif stroke['tool']=='Tile':paint_world_tiles(a,stroke['points'],stroke['tile'])
            else:erase_world(a,stroke['points'],'all')
        change(self.document,edit,'Paint CHI world '+stroke['tool'].lower());self.owner.refresh()
    def cancel(self):self.stroke=None;self.drag=None;self.draw();return 'break'
    def capture_draft(self):
        stroke=copy.deepcopy(self.stroke)
        if stroke:stroke['points']=[list(p) for p in sorted(stroke['points'])]
        return dict(stroke=stroke,drag=copy.deepcopy(self.drag))
    def restore_draft(self,state):
        self.stroke=copy.deepcopy(state['stroke']);self.drag=copy.deepcopy(state['drag'])
        if self.stroke:self.stroke['points']={tuple(p) for p in self.stroke['points']}
        self.draw()
    def motion(self,e):
        self.hover=self.point(e);self.draw_hover()
        if self.image and 0<=self.hover[0]<1024 and 0<=self.hover[1]<1024:
            x,y=self.hover;idx=(y//8)*128+x//8;self.status.set(f'Tile ({x}, {y}) | jigsaw ({x//8}, {y//8}) | terrain level {self.image["levels"][idx]} | {self.tool.get()} brush. Right-click for tile editing.')
    def clear_hover(self):self.hover=None;self.canvas.delete('brush-hover')
    def draw_hover(self):
        self.canvas.delete('brush-hover')
        if self.hover:
            x,y=self.hover;u=1 if self.tool.get() in ('Tile','Pick') else 8;z=int(self.zoom.get());x=x//u*u;y=y//u*u
            self.canvas.create_rectangle(x*z,y*z,(x+u*int(self.size.get()))*z,(y+u*int(self.size.get()))*z,outline='#ffff88',width=2,tags='brush-hover')
    def pick(self,p):
        x,y=p;index=self.image['grid'][y*1024+x]
        if index<len(self.value['tiles']):self.tile_id.set(self.value['tiles'][index]['id'])
        self.level.set(str(self.image['levels'][(y//8)*128+x//8]))
        placed=next((v for v in self.value['world'].get('placements',[]) if v['at']==[x//8,y//8]),None)
        if placed:self.listing.selection_set(placed['jigsaw']);self.flip.set(str(placed.get('flip',0)))
        self.brush_changed();self.status.set('Picked '+self.tile_id.get()+'. Choose Tile or Jigsaw to paint.')
    def context(self,e):
        if not self.image:return
        p=self.point(e)
        if not(0<=p[0]<1024 and 0<=p[1]<1024):return
        self.finish();idx=self.image['grid'][p[1]*1024+p[0]]
        if idx>=len(self.value['tiles']):return
        current=self.value['tiles'][idx]['id']
        from construction_editor import tile_menu
        def assign(identity):
            town=self.town_at(p)
            if town:raise EditorError('This cell belongs to '+town['name']+'. Double-click the town to edit its visible tiles.')
            from chi_spatial import paint_world_tiles
            change(self.document,lambda a:paint_world_tiles(a,[p],identity),'Paint CHI world tile');self.owner.refresh()
        rows=[]
        for y in range(p[1]-1,p[1]+2):
            row=[]
            for x in range(p[0]-1,p[0]+2):
                n=self.image['grid'][y*1024+x] if 0<=x<1024 and 0<=y<1024 else 65535
                row.append(self.value['tiles'][n]['id'] if n<len(self.value['tiles']) else ' ')
            rows.append(row)
        tile_menu(self,self.owner,current,assign,e,lambda:dict(world_neighbourhood=rows,name='CHI world at '+str(p),at=[1,1]))
    def select_town(self):
        ids=self.towns.selection()
        if ids:self.selected=ids[0];self.draw()
    def open_town(self,e):
        town=self.town_at(self.point(e))
        if town:self.cancel();self.selected=town['id'];self.edit_town()
        else:self.pointer(e,True)
    def town(self):
        m=find(data(self.document)['maps'],self.selected or 'chi:map-01');f=Form(self,'Move native town / island')
        f.field('map',m['id'],[m['id'] for m in self.value['maps'] if m['slot']<=13 and m['slot']!=11]);f.field('x',m['origin'][0]);f.field('y',m['origin'][1])
        def apply(v):change(self.document,lambda a:move_town(a,v['map'],int(v['x']),int(v['y'])),'Move CHI town');self.owner.refresh()
        f.submit(apply);return f
    def edit_town(self):
        identity=self.selected or 'chi:map-01';self.owner.scene_index=next(i for i,m in enumerate(self.adventure['maps']) if m['id']==identity);self.owner.refresh();self.owner.window.lift()
    def show_location(self,world,at,message,coordinate_space='world_movement'):
        if world!='chi:world':raise EditorError('This native campaign has one world: chi:world.')
        x,y=at if coordinate_space=='world_tile' else [n/2 for n in at];self.problem_location=(x,y)
        z=int(self.zoom.get());self.canvas.xview_moveto((x*z-self.canvas.winfo_width()/2)/(1024*z));self.canvas.yview_moveto((y*z-self.canvas.winfo_height()/2)/(1024*z));self.status.set(message);self.draw();self.window.lift()
    def generator(self):
        w=data(self.document)['world'];f=Form(self,'Advanced native generator inputs')
        f.field('name',w['name']);f.field('seed',w['seed']);f.field('coarse',','.join(map(str,w['coarse'])),label='336 coarse heights (0-127)')
        f.field('flips',','.join(map(str,w['flips'])),label='96 tile / join flip entries');f.field('mini_colors',','.join(map(str,w['mini_colors'])),label='256 overhead colour indices')
        def apply(v):
            def edit(a):a['world'].update(name=v['name'],seed=int(v['seed']),**{k:[int(n.strip()) for n in v[k].split(',')] for k in ('coarse','flips','mini_colors')})
            change(self.document,edit,'Edit CHI generator inputs');self.owner.refresh()
        f.submit(apply);return f
    def selected_jigsaw(self):
        ids=self.listing.selection();return next((j for j in self.adventure['jigsaws'] if ids and j['id']==ids[0]),None)
    def brush_changed(self):
        if not hasattr(self,'brush_canvas'):return
        self.brush_canvas.delete('all');j=self.selected_jigsaw()
        if self.tool.get()=='Terrain' and self.image:
            from PIL import Image
            level=int(self.level.get());levels=self.image['levels'];towns=self.image['towns'];joins=self.image['joins']
            # Show the original miniature glyph for an actual block at this
            # level. Joining is computed by the game from neighbouring levels.
            candidate=next((i for i,v in enumerate(levels) if v==level and not towns[i] and not joins[i]),None)
            if candidate is None:candidate=next((i for i,v in enumerate(levels) if v==level and not towns[i]),None)
            if candidate is not None:
                x,y=candidate%128*8,candidate//128*8
                self.terrain_photo=raster_photo(self.window,self.mini.crop((x,y,x+8,y+8)).resize((128,128),Image.Resampling.NEAREST))
                self.brush_canvas.create_image(0,0,image=self.terrain_photo,anchor='nw');return
        if self.tool.get()=='Tile':rows=[[self.tile_id.get()]];z=64
        elif j:
            from chi_spatial import resolved_jigsaw
            rows=resolved_jigsaw(data(self.document),j['id'],int(self.level.get()),int(self.flip.get()));z=16
        else:return
        tiles={t['id']:t for t in self.adventure['tiles']}
        for y,row in enumerate(rows):
            for x,identity in enumerate(row):
                t=tiles.get(identity)
                if t:
                    photo=self.owner.tile_image(t['sheet'],t['graphic'],z)
                    if photo:self.brush_canvas.create_image(x*z,y*z,image=photo,anchor='nw')
    def edit_jigsaw(self):
        j=self.selected_jigsaw()
        if j:
            from world_editor import JigsawEditor
            return open_view(self,'jigsaw',lambda:JigsawEditor(self,j),j['id'])
    def new_jigsaw(self):
        from world_editing import add_jigsaw
        a=copy.deepcopy(self.adventure);identity=add_jigsaw(a,self.document.manifest['package_id'],name='New exact jigsaw')
        find(a['jigsaws'],identity)['mode']='absolute';self.owner.commit(a);self.listing.selection_set(identity);return self.edit_jigsaw()
    def clone_jigsaw(self):
        j=self.selected_jigsaw()
        if j:
            from world_editing import identity
            a=copy.deepcopy(self.adventure);clone=copy.deepcopy(j);clone['id']=identity(self.document.manifest['package_id'],a['jigsaws'],'jigsaw');clone['name']=(j['name']+' copy')[:95]
            a['jigsaws'].append(clone);self.owner.commit(a);self.listing.selection_set(clone['id'])
    def joins(self):
        w=data(self.document)['world'];f=Form(self,'Native terrain joining bindings');choices=[j['id'] for j in w['jigsaws']]
        for i,identity in enumerate(w['joins']):f.field(str(i),identity,choices,label='Join mask '+str(i) if i<16 else 'Level 16 terrain')
        def apply(v):change(self.document,lambda a:a['world'].update(joins=[v[str(i)] for i in range(17)]),'Bind CHI terrain joins');self.owner.refresh()
        f.submit(apply);return f
    def tinyland_art(self):
        from chi_resource_editor import open_resources
        view=open_resources(self.owner)
        item=next((str(i) for i,r in enumerate(view.rows) if r['resource']=='TINYLAND.CMP'),None)
        if item is not None:view.table.selection_set(item);view.select()
        return view
