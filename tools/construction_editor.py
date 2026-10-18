"""Footprint/height drawing with live, editable building/wall/road previews."""
import copy
import tkinter as tk
from tkinter import ttk
from adventure_editor import Form,scroll_frame
from editor_workspace import view_window
from editor_session import guard,register
from editor_recovery import recoverable_forms
from editor_model import EditorError
from tile_editing import metadata,create_tile,edit_pixels,tile
from construction_editing import geometry,part_name,default_pixels,put_profile,new_profile,preset,compile_rows,prepare_road


def tile_menu(owner,maps,current,assign,event):
    """A preview cell can choose, create, clone or edit its actual tile."""
    menu=tk.Menu(owner.window,tearoff=False)
    def create(clone):
        value=create_tile(maps.document,maps.graphics,current if clone else None,'Construction tile',tile(maps.document,current)['terrain'] if current else 'clear')
        maps.refresh();assign(value);edit_pixels(maps,value)
    menu.add_command(label='Choose tile...',command=lambda:guard(owner,lambda:maps.graphic_picker(choose=assign,selected=current)))
    menu.add_command(label='New tile for this part',command=lambda:guard(owner,lambda:create(False)))
    menu.add_command(label='Clone tile for this part',command=lambda:guard(owner,lambda:create(True)),state='normal' if current else 'disabled')
    menu.add_command(label='Edit tile pixels',command=lambda:guard(owner,lambda:edit_pixels(maps,current)),state='normal' if current else 'disabled')
    def properties():
        from tile_editing import select_tile
        select_tile(maps,current);maps.edit_tile()
    menu.add_command(label='Tile properties',command=lambda:guard(owner,properties),state='normal' if current else 'disabled')
    try:menu.tk_popup(event.x_root,event.y_root)
    finally:menu.grab_release()


@recoverable_forms
class ConstructionEditor:
    def __init__(self,owner,kind='Building'):
        self.owner=owner;self.document=owner.document;self.kind=kind;self.profile=None;self.stroke=None;self.last=None;self.selected_role=None;self.photos=[]
        self.window=view_window(self,owner,'construction',kind+' designer',kind);self.window.geometry('1080x760')
        bar=ttk.Frame(self.window,padding=8);bar.pack(fill='x')
        self.choice=ttk.Combobox(bar,state='readonly',width=24);self.choice.pack(side='left',padx=4);self.choice.bind('<<ComboboxSelected>>',lambda _:guard(self,self.change))
        for label,callback in [('New set',self.new),('Duplicate',self.duplicate),('Rename',self.rename),('Footprint...',self.reshape),('Save pattern',self.save_pattern),('Use on map',self.use)]:
            ttk.Button(bar,text=label,width=0,command=lambda f=callback:guard(self,f)).pack(side='left',padx=3)
        if kind=='Road':ttk.Button(bar,text='Draw connecting roads',command=lambda:guard(self,self.road_brush)).pack(side='left',padx=3)
        from editor_ui import flow_toolbar
        flow_toolbar(bar)
        self.status=tk.StringVar(value='Draw a footprint on the left; right-click a preview cell to choose, clone or edit its tile.')
        ttk.Label(self.window,textvariable=self.status,wraplength=1000,padding=8).pack(side='bottom',fill='x')
        body=ttk.Panedwindow(self.window,orient='horizontal');body.pack(fill='both',expand=True)
        left=ttk.Frame(body,padding=8);right=ttk.Frame(body,padding=8);body.add(left,weight=1);body.add(right,weight=2)
        controls=ttk.Frame(left);controls.pack(fill='x')
        ttk.Label(controls,text='Paint height (0 erases)').pack(side='left')
        self.height=tk.StringVar(value='1' if kind=='Road' else '2')
        ttk.Combobox(controls,textvariable=self.height,values=[str(i) for i in range(2 if kind=='Road' else 4 if kind=='Wall' else 9)],state='readonly',width=3).pack(side='left',padx=8)
        ttk.Label(left,text='Left-drag draws; right-drag erases.\nDifferent heights create stepped roofs.',wraplength=320,padding=(0,8)).pack(anchor='w')
        self.footprint=self.make_canvas(left);self.footprint.bind('<Button-1>',lambda e:guard(self,lambda:self.paint(e,True)))
        self.footprint.bind('<B1-Motion>',lambda e:guard(self,lambda:self.paint(e,False)))
        self.footprint.bind('<Button-3>',lambda e:guard(self,lambda:self.paint(e,True,True)))
        self.footprint.bind('<B3-Motion>',lambda e:guard(self,lambda:self.paint(e,False,True)))
        self.footprint.bind('<ButtonRelease-1>',lambda _:guard(self,self.finish));self.footprint.bind('<ButtonRelease-3>',lambda _:guard(self,self.finish))
        heading=ttk.Frame(right);heading.pack(fill='x')
        ttk.Label(heading,text='Building preview' if kind=='Building' else kind+' preview',style='Section.TLabel').pack(side='left')
        self.zoom=tk.StringVar(value='Fit');zoom=ttk.Combobox(heading,textvariable=self.zoom,values=['Fit','16','24','32','48'],state='readonly',width=4);zoom.pack(side='right');zoom.bind('<<ComboboxSelected>>',lambda _:self.draw())
        self.preview=self.make_canvas(right);self.preview_size=32;self.preview.bind('<Configure>',lambda _:self.draw())
        self.preview.bind('<Button-1>',self.select_preview);self.preview.bind('<Button-3>',self.context)
        # Reserve the part controls before the flexible preview, as in Form.
        # A narrow workspace must keep Edit/Clone reachable without scrolling
        # the entire application window.
        parts=ttk.Frame(right,padding=(0,8));parts.pack(side='bottom',fill='x',before=self.preview.master)
        self.part=ttk.Combobox(parts,state='readonly',width=38);self.part.pack(fill='x');self.part.bind('<<ComboboxSelected>>',self.select_part)
        buttons=ttk.Frame(parts);buttons.pack(fill='x')
        for label,callback in [('Choose tile',self.choose_part),('Edit pixels',self.edit_part),('Clone tile',self.clone_part)]:ttk.Button(buttons,text=label,command=lambda f=callback:guard(self,f)).pack(side='left',padx=3,pady=4)
        flow_toolbar(buttons)
        self.window.bind('<Escape>',lambda _:self.cancel_gesture())
        self.draft=register(self,pending=lambda:self.stroke is not None,apply=self.finish,
            capture=lambda:dict(profile=copy.deepcopy(self.profile),stroke=copy.deepcopy(self.stroke)),restore=self.restore_draft,priority=40)
        profiles=self.profiles()
        self.current=profiles[0]['id'] if profiles else new_profile(self.document,kind)
        self.refresh()
    def make_canvas(self,parent):
        shell=ttk.Frame(parent);shell.pack(fill='both',expand=True);canvas=tk.Canvas(shell,background='#273b45',highlightthickness=0,width=300,height=350)
        x=ttk.Scrollbar(shell,orient='horizontal',command=canvas.xview);y=ttk.Scrollbar(shell,command=canvas.yview)
        x.pack(side='bottom',fill='x');y.pack(side='right',fill='y');canvas.pack(fill='both',expand=True);canvas.configure(xscrollcommand=x.set,yscrollcommand=y.set);return canvas
    def profiles(self):return [p for p in metadata(self.document).get('construction_sets',[]) if p['kind']==self.kind]
    def refresh(self):
        if self.stroke is not None:return
        profiles=self.profiles();self.choice.configure(values=[p['name'] for p in profiles])
        self.profile=copy.deepcopy(next((p for p in profiles if p['id']==getattr(self,'current',None)),profiles[0] if profiles else None))
        if self.profile:self.current=self.profile['id'];self.choice.current(next(i for i,p in enumerate(profiles) if p['id']==self.current))
        self.owner.refresh();self.draw()
    def restore_draft(self,state):self.profile=state['profile'];self.stroke=state['stroke'];self.current=self.profile['id'];self.draw()
    def change(self):
        selected=self.profiles()[self.choice.current()]['id'];self.finish();self.current=selected;self.refresh()
    def new(self):self.current=new_profile(self.document,self.kind);self.refresh()
    def duplicate(self):
        if not self.profile:return
        from world_editing import identity
        value=copy.deepcopy(self.profile);value['id']=identity(self.document.manifest['package_id'],metadata(self.document).get('construction_sets',[]),'construction');value['name']=(value['name']+' copy')[:95]
        self.current=put_profile(self.document,value,'Duplicate construction set');self.refresh()
    def rename(self):
        if not self.profile:return
        f=Form(self,'Construction set name');f.field('name',self.profile['name'])
        def apply(v):
            if not v['name'].strip() or len(v['name'])>95:raise EditorError('Use a name of 1..95 characters.')
            value=copy.deepcopy(self.profile);value['name']=v['name'];put_profile(self.document,value);self.refresh()
        f.submit(apply);return f
    def reshape(self):
        if not self.profile:return
        f=Form(self,'Draw a new footprint');f.field('shape','Rectangle',['Rectangle','Cross','L shape','Courtyard','Line','Empty']);f.field('width',len(self.profile['footprint'][0]));f.field('height',len(self.profile['footprint']));f.field('stories',int(self.height.get()) or 1)
        def apply(v):
            value=copy.deepcopy(self.profile);value['footprint']=preset(self.kind,int(v['width']),int(v['height']),int(v['stories']),v['shape']);put_profile(self.document,value,'Reshape '+self.kind.lower());self.refresh()
        f.submit(apply);return f
    def paint(self,event,start,erase=False):
        if not self.profile:return
        from world_editing import line
        x,y=int(self.footprint.canvasx(event.x)//24),int(self.footprint.canvasy(event.y)//24)
        rows=self.profile['footprint']
        if not(0<=y<len(rows) and 0<=x<len(rows[0])):return
        if start:self.stroke=copy.deepcopy(self.profile);self.last=x,y
        if self.stroke is None:return
        for xx,yy in line(*self.last,x,y):rows[yy][xx]=0 if erase else int(self.height.get())
        self.last=x,y;self.draw()
    def finish(self):
        if self.stroke is None:return
        old=self.stroke;value=self.profile;self.stroke=None
        try:
            if value!=old:put_profile(self.document,value,'Draw '+self.kind.lower()+' footprint')
        except Exception:self.profile=old;raise
        self.refresh()
    def cancel_gesture(self):self.stroke=None;self.refresh()
    def draw(self):
        self.footprint.delete('all');self.preview.delete('all');self.photos=[]
        if not self.profile:return
        rows=self.profile['footprint'];self.footprint.configure(scrollregion=(0,0,len(rows[0])*24,len(rows)*24))
        for y,row in enumerate(rows):
            for x,height in enumerate(row):
                self.footprint.create_rectangle(x*24,y*24,x*24+24,y*24+24,fill=('#466575' if height else '#f0f2f4'),outline='#a9b3b9')
                if height:self.footprint.create_text(x*24+12,y*24+12,text=str(height),fill='white')
        self.roles=geometry(self.profile)
        size=min(32,max(8,min(max(1,self.preview.winfo_width()-4)//len(self.roles[0]),max(1,self.preview.winfo_height()-4)//len(self.roles)))) if self.zoom.get()=='Fit' else int(self.zoom.get())
        self.preview_size=size;self.preview.configure(scrollregion=(0,0,len(self.roles[0])*size,len(self.roles)*size))
        values={t['id']:t for t in self.document.adventure['tiles']}
        for y,row in enumerate(self.roles):
            for x,role in enumerate(row):
                if role==' ':continue
                value=values.get(self.profile['parts'].get(role));image=self.owner.tile_image(value['sheet'],value['graphic'],size) if value else None
                if image:self.preview.create_image(x*size,y*size,image=image,anchor='nw')
                else:
                    pixels=default_pixels(role,self.kind);im=tk.PhotoImage(master=self.window,width=size,height=size)
                    im.put(' '.join('{'+ ' '.join('#'+pixels[yy*16//size][xx*16//size][:6] for xx in range(size))+'}' for yy in range(size)));self.photos.append(im);self.preview.create_image(x*size,y*size,image=im,anchor='nw')
                if role==self.selected_role:self.preview.create_rectangle(x*size,y*size,(x+1)*size,(y+1)*size,outline='#ffd95a',width=2)
        self.role_ids=sorted(set(p for row in self.roles for p in row if p!=' ')|set(self.profile['parts']));self.part.configure(values=[part_name(p) for p in self.role_ids])
        if self.selected_role not in self.role_ids:self.selected_role=self.role_ids[0] if self.role_ids else None
        if self.selected_role:self.part.current(self.role_ids.index(self.selected_role))
    def select_preview(self,event):
        x,y=int(self.preview.canvasx(event.x)//self.preview_size),int(self.preview.canvasy(event.y)//self.preview_size)
        if 0<=y<len(self.roles) and 0<=x<len(self.roles[0]) and self.roles[y][x]!=' ':self.selected_role=self.roles[y][x];self.draw();self.status.set(part_name(self.selected_role)+' — right-click to change this part’s tile.')
    def select_part(self,_=None):
        if self.part.current()>=0:self.selected_role=self.role_ids[self.part.current()];self.draw()
    def assign(self,value):
        if not self.selected_role:return
        profile=copy.deepcopy(self.profile);profile['parts'][self.selected_role]=value;put_profile(self.document,profile,'Assign construction tile');self.refresh()
    def choose_part(self):
        if self.selected_role:return self.owner.graphic_picker(choose=self.assign,selected=self.profile['parts'].get(self.selected_role))
    def edit_part(self):
        if self.selected_role:edit_pixels(self.owner,self.profile['parts'][self.selected_role])
    def clone_part(self):
        if self.selected_role:
            value=create_tile(self.document,self.owner.graphics,self.profile['parts'][self.selected_role],part_name(self.selected_role)+' copy');self.assign(value);edit_pixels(self.owner,value)
    def context(self,event):
        self.select_preview(event)
        if self.selected_role:tile_menu(self,self.owner,self.profile['parts'].get(self.selected_role),self.assign,event)
    def use(self):
        self.finish()
        if self.profile:self.owner.use_pattern(compile_rows(self.profile),self.profile['name'],overlay=self.kind!='Road')
    def save_pattern(self):
        self.finish()
        if not self.profile:return
        from map_patterns import save_pattern
        save_pattern(self.document,compile_rows(self.profile),self.profile['name']);self.status.set('Saved in the Pattern Library. It stays with this project and can be exported.')
    def road_brush(self):
        self.finish();profile=prepare_road(self.document,self.profile);self.owner.road_profile=profile['id'];self.owner.road_width=1;self.owner.tool.set('Road');self.owner.window.lift();self.owner.tabs.select(self.owner.map_tab)
        self.owner.status.set('Drag to draw roads. Existing roads in this set join automatically; one stroke is one Undo.')
