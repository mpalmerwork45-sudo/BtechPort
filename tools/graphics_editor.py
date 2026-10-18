"""Package image library and non-destructive pixel/animation editor."""
from __future__ import annotations
import copy
import tkinter as tk
from tkinter import ttk, filedialog, colorchooser, messagebox
from adventure_editor import Form
from editor_model import EditorError
from art_editing import (new_image, clone_image, import_image, original_sprite,
                         display_rows, pixels, brush, bind, transform, editable_tile, SLOTS, DEFAULT_COLORS)
from world_editing import graphic_tile
from pixel_tools import begin_layers,target,flatten,export_layers,add_layer,selected_pixels,paste_selection,resize_canvas,export_sheet
from event_workbench import editor_data
from editor_model import encoded
from editor_session import guard, register, apply_draft, scope_of


def photo(parent, image, frame=0, zoom=1):
    result = tk.PhotoImage(master=parent, width=image['width'], height=image['height'])
    result.put(' '.join('{'+' '.join(row)+'}' for row in display_rows(image, frame)))
    return result.zoom(zoom) if zoom != 1 else result


def open_image_editor(owner, image):
    if image['kind']=='sprite':
        from sprite_editor import SpriteEditor
        return SpriteEditor(owner,image)
    return PixelEditor(owner,image)


class GraphicsEditor:
    def __init__(self, owner):
        self.owner, self.document = owner, owner.document
        self.window = tk.Toplevel(owner.window)
        self.window.title('Graphics and sprites'); self.window.geometry('880x650')
        self.window.minsize(720, 500)
        self.selected = None; self.preview_image = None
        bar = ttk.Frame(self.window, padding=8); bar.pack(fill='x')
        for name, cb in [('New', self.new), ('Import', self.import_file), ('Clone', self.clone),
                         ('Edit pixels', self.edit), ('Copy map tile', self.map_tile), ('Copy original', self.original), ('Delete', self.delete)]:
            ttk.Button(bar, text=name, width=0, style='Toolbar.TButton', command=lambda f=cb: self.guard(f)).pack(side='left', padx=3)
        body = ttk.Panedwindow(self.window, orient='horizontal'); body.pack(fill='both', expand=True, padx=8)
        left = ttk.Frame(body); right = ttk.Frame(body, padding=12); body.add(left, weight=2); body.add(right, weight=3)
        self.search = tk.StringVar(); ttk.Entry(left, textvariable=self.search).pack(fill='x', pady=(0,8))
        self.search.trace_add('write', lambda *_: self.refresh())
        listing = ttk.Frame(left); listing.pack(fill='both', expand=True)
        self.listing = ttk.Treeview(listing, columns=('kind',), show='tree headings', selectmode='browse')
        self.listing.heading('#0', text='Image'); self.listing.heading('kind', text='Kind')
        self.listing.column('#0', width=200); self.listing.column('kind', width=65, stretch=False)
        scroll = ttk.Scrollbar(listing, command=self.listing.yview); self.listing.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y'); self.listing.pack(fill='both', expand=True)
        self.listing.bind('<<TreeviewSelect>>', lambda _: self.select())
        self.listing.bind('<Double-1>', lambda _: self.guard(self.edit))
        self.preview = tk.Canvas(right, background='#e1e1e1', height=320, highlightthickness=0)
        self.preview.pack(fill='both', expand=True)
        self.info = tk.StringVar(); ttk.Label(right, textvariable=self.info, wraplength=370).pack(fill='x', pady=12)
        actions = ttk.Frame(right); actions.pack(fill='x')
        ttk.Button(actions, text='Use as map tile', command=lambda: self.guard(self.use_tile)).pack(side='left')
        ttk.Button(actions, text='Assign sprite role', command=lambda: self.guard(self.binding)).pack(side='left', padx=8)
        ttk.Label(self.window, text='Images belong to this package. Changes share the map editor shared Save, Undo and Redo.',
                  style='Muted.TLabel', padding=10).pack(fill='x')
        self.refresh()
        self.window.protocol('WM_DELETE_WINDOW',lambda:self.guard(self.close))

    def guard(self, fn): return guard(self,fn)
    def close(self):
        if scope_of(self).confirm_close(self):self.window.destroy()
    def current(self):
        return next((i for i in self.document.art['images'] if i['id'] == self.selected), None)
    def refresh(self):
        self.listing.delete(*self.listing.get_children())
        query = self.search.get().lower()
        for im in self.document.art['images']:
            if query in (im['name']+' '+im['id']).lower():
                self.listing.insert('', 'end', iid=im['id'], text=im['name'], values=(im['kind'],))
        if self.selected and self.listing.exists(self.selected): self.listing.selection_set(self.selected)
        self.show()
    def select(self):
        if self.listing.selection(): self.selected = self.listing.selection()[0]
        self.show()
    def show(self):
        self.preview.delete('all'); im = self.current()
        if not im:
            self.info.set('Create, import or clone an image. RGBA transparency and up to 256 frames are supported.'); return
        z = max(1, min(6, 330//max(im['width'], im['height'])))
        self.preview_image = photo(self.window, im, zoom=z)
        self.preview.create_image(10,10, image=self.preview_image, anchor='nw')
        self.info.set(f"{im['name']}\n{im['id']}\n{im['width']} x {im['height']} | {len(im['frames'])} frame(s) | {im['kind']}")
    def put(self, im, old=None,metadata=None):
        art = copy.deepcopy(self.document.art)
        if old:
            current = self.current()
            if current != old: raise EditorError('This image changed while its pixel editor was open. Reopen it before applying.')
            art['images'][art['images'].index(current)] = im
        else: art['images'].append(im)
        self.selected = im['id']; self.document.replace_art(art,metadata=metadata); self.owner.refresh()
        parent=self.owner.parent
        if parent.current and parent.collection in ('mechs','people'):parent.stop_sprite();parent.start_sprite()
    def new(self):
        f=Form(self,'New graphic'); f.field('name','New image'); f.field('kind','tile',['tile','sprite','icon','screen'])
        f.field('width',16); f.field('height',16); f.field('frames',1,label='Images (unit movement: 32; character: 16)')
        def apply(v):
            im=new_image(self.document.content['package_id'],self.document.art['images'],v['name'],v['kind'],int(v['width']),int(v['height']),int(v['frames']))
            self.put(im); self.edit()
        f.submit(apply)
    def clone(self):
        if self.current(): self.put(clone_image(self.current(),self.document.content['package_id'],self.document.art['images']))
    def edit(self):
        if self.current(): return open_image_editor(self,self.current())
    def import_file(self):
        path=filedialog.askopenfilename(parent=self.window,title='Import image or sprite sheet',filetypes=[('Images','*.png *.jpg *.jpeg *.bmp *.gif'),('All files','*')])
        if not path:return
        f=Form(self,'Import graphic'); f.field('kind','screen',['tile','sprite','icon','screen','tile sheet'])
        f.field('frame_width',0,label='Frame width (0 = whole image)'); f.field('frame_height',0,label='Frame height (0 = whole image)')
        def apply(v):
            if v['kind']=='tile sheet':
                from art_editing import import_tiles
                art=copy.deepcopy(self.document.art)
                art['images'].extend(import_tiles(path,self.document.content['package_id'],art['images']))
                self.document.replace_art(art); self.owner.refresh()
            else:self.put(import_image(path,self.document.content['package_id'],self.document.art['images'],v['kind'],int(v['frame_width']) or None,int(v['frame_height']) or None))
        f.submit(apply)
    def original(self):
        f=Form(self,'Copy original sprite into package'); f.field('first',0,label='First sprite (Locust 0, Stinger 146, player 166, NPC 270)'); f.field('frames',16)
        def apply(v):
            im=original_sprite(self.document,self.owner.parent.settings,int(v['first']),int(v['frames']))
            self.put(clone_image(im,self.document.content['package_id'],self.document.art['images']))
        f.submit(apply)
    def map_tile(self):
        selected=self.owner.brush.curselection()
        if not selected:raise EditorError('Choose a map tile in the palette first.')
        tile=self.document.adventure['tiles'][selected[0]]
        if tile['sheet']=='package:art':
            source=next(i for i in self.document.art['images'] if i['id']==tile['graphic'])
            self.put(clone_image(source,self.document.content['package_id'],self.document.art['images']))
        else:
            try:colors=self.owner.graphics[tile['sheet']][tile['graphic']]
            except (KeyError,IndexError):raise EditorError('Wait for the map graphics preview to load first.')
            im=new_image(self.document.content['package_id'],self.document.art['images'],'Copied map tile')
            im['frames']=[[''.join(color.lstrip('#')+'ff' for color in row) for row in colors]]
            self.put(im)
        self.edit()
    def edit_map_tile(self):
        selected=self.owner.brush.curselection()
        if not selected or selected[0]>=len(self.document.adventure['tiles']):raise EditorError('Choose a map tile in the palette first.')
        art=copy.deepcopy(self.document.art);a=copy.deepcopy(self.document.adventure)
        im=editable_tile(art,a,selected[0],self.document.content['package_id'],self.owner.graphics)
        self.selected=im['id']
        if art!=self.document.art or a!=self.document.adventure:
            self.document.replace_art(art,a);self.owner.refresh()
        self.refresh();self.edit()
    def delete(self):
        if not self.current():return
        art=copy.deepcopy(self.document.art); art['images']=[i for i in art['images'] if i['id']!=self.selected]
        self.document.replace_art(art); self.selected=None; self.owner.refresh()
        self.owner.status.set('Image removed. Validate reports any remaining references; Undo restores it.')
    def use_tile(self):
        im=self.current()
        if not im or im['kind']!='tile':raise EditorError('Choose a 16x16 tile image first.')
        a=copy.deepcopy(self.document.adventure)
        value=graphic_tile(a,self.document.content['package_id'],'package:art',im['id'])
        self.owner.commit(a)
        index=next(i for i,t in enumerate(a['tiles']) if t['id']==value)
        self.owner.brush.selection_set(str(index)); self.owner.select_brush(); self.owner.window.lift()
    def binding(self):
        im=self.current()
        if not im or im['kind']!='sprite':raise EditorError('Choose a sprite image first.')
        f=Form(self,'Assign sprite role'); f.field('slot','player',SLOTS)
        def apply(v):
            art=copy.deepcopy(self.document.art); bind(art,v['slot'],im['id']); self.document.replace_art(art); self.owner.refresh()
        f.submit(apply)


class PixelEditor:
    """Stage an image independently; Apply produces one shared undo entry."""
    def __init__(self, owner, image):
        self.owner=owner; self.original=copy.deepcopy(image)
        self.image=begin_layers(image,editor_data(owner.document).get('pixel_layers',{}).get(image['id']))
        self.original_layers=copy.deepcopy(self.image);self.pixel_selection=None;self.pixel_clipboard=None
        self.window=tk.Toplevel(owner.window); self.window.title('Pixel editor - '+image['name']); self.window.geometry('920x730')
        self.history=[]; self.future=[]; self.before=None; self.last=None; self.playing=False
        bar=ttk.Frame(self.window,padding=8); bar.pack(fill='x')
        self.tool=tk.StringVar(value='Pencil'); ttk.Combobox(bar,textvariable=self.tool,values=['Pencil','Line','Rectangle','Fill','Erase','Eyedropper','Select','Paste selection'],state='readonly',width=15).pack(side='left')
        self.color=tk.StringVar(value='ffffffff'); ttk.Entry(bar,textvariable=self.color,width=10).pack(side='left',padx=5)
        ttk.Button(bar,text='Color...',command=self.choose_color).pack(side='left')
        self.zoom=tk.StringVar(value=str(min(16,max(2,512//max(image['width'],image['height'])))))
        z=ttk.Combobox(bar,textvariable=self.zoom,values=['1','2','4','8','16','24','32'],width=4,state='readonly'); z.pack(side='left',padx=8);z.bind('<<ComboboxSelected>>',lambda _:self.draw())
        for title,cb in [('Undo',self.undo),('Redo',self.redo),('Apply',self.apply)]:ttk.Button(bar,text=title,command=lambda f=cb:self.guard(f)).pack(side='left',padx=3)
        colors=ttk.Frame(self.window,padding=(8,0)); colors.pack(fill='x')
        swatches=tk.Canvas(colors,width=384,height=24,highlightthickness=0);swatches.pack(side='left')
        for i,c in enumerate(DEFAULT_COLORS):swatches.create_rectangle(i*24,0,i*24+23,23,fill='#'+c,outline='#999999')
        swatches.bind('<Button-1>',lambda e:self.color.set(DEFAULT_COLORS[max(0,min(15,e.x//24))]+'ff'))
        self.build_frames()
        transforms=ttk.Frame(self.window,padding=(8,0,8,8));transforms.pack(fill='x')
        for title in ('Flip X','Flip Y'):
            ttk.Button(transforms,text=title,command=lambda op=title:self.guard(lambda:self.transform(op))).pack(side='left',padx=3)
        more=ttk.Menubutton(transforms,text='Transform');menu=tk.Menu(more,tearoff=False)
        for title in ('Rotate right','Rotate left','Nudge left','Nudge right','Nudge up','Nudge down','Clear'):
            menu.add_command(label=title,command=lambda op=title:self.guard(lambda:self.transform(op)))
        more.configure(menu=menu);more.pack(side='left',padx=3)
        self.all_frames=tk.BooleanVar(value=False);self.wrap=tk.BooleanVar(value=False)
        ttk.Checkbutton(transforms,text='All frames',variable=self.all_frames).pack(side='left',padx=8)
        ttk.Checkbutton(transforms,text='Wrap nudged pixels',variable=self.wrap).pack(side='left')
        self.grid=tk.BooleanVar(value=True)
        ttk.Checkbutton(transforms,text='Grid',variable=self.grid,command=self.draw).pack(side='left',padx=8)
        extra=ttk.Menubutton(transforms,text='Selection / canvas');em=tk.Menu(extra,tearoff=False)
        for title,method in [('Copy selection',self.copy_pixels),('Cut selection',lambda:self.copy_pixels(True)),('Crop to selection',self.crop),('Resize canvas',self.resize_dialog),('Export PNG sheet',self.export_dialog)]:em.add_command(label=title,command=lambda f=method:self.guard(f))
        extra.configure(menu=em);extra.pack(side='left',padx=6)
        # Keep the extra controls in the palette row; the drawing canvas
        # retains its useful size on a 1024x768 desktop.
        ttk.Label(colors,text=' Layer').pack(side='left');self.layer=ttk.Combobox(colors,state='readonly',width=16);self.layer.pack(side='left',padx=4);self.layer.bind('<<ComboboxSelected>>',lambda _:self.change_layer())
        layers_button=ttk.Menubutton(colors,text='Layers');layers_menu=tk.Menu(layers_button,tearoff=False)
        for title,method in [('New layer',self.new_layer),('Rename',self.rename_layer),('Show / hide',self.toggle_layer),('Raise',lambda:self.reorder_layer(1)),('Lower',lambda:self.reorder_layer(-1)),('Delete',self.delete_layer)]:layers_menu.add_command(label=title,command=lambda f=method:self.guard(f))
        layers_button.configure(menu=layers_menu);layers_button.pack(side='left',padx=4)
        view=ttk.Frame(self.window);view.pack(fill='both',expand=True,padx=8,pady=(0,8));view.columnconfigure(0,weight=1);view.rowconfigure(0,weight=1)
        self.canvas=tk.Canvas(view,highlightthickness=0,background='#d6d6d6')
        sx=ttk.Scrollbar(view,orient='horizontal',command=self.canvas.xview);sy=ttk.Scrollbar(view,command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=sx.set,yscrollcommand=sy.set);self.canvas.grid(row=0,column=0,sticky='nsew');sx.grid(row=1,column=0,sticky='ew');sy.grid(row=0,column=1,sticky='ns')
        self.canvas.bind('<Button-1>',lambda e:self.guard(lambda:self.stroke(e,True)))
        self.canvas.bind('<B1-Motion>',lambda e:self.guard(lambda:self.stroke(e,False)))
        self.canvas.bind('<ButtonRelease-1>',lambda _:self.finish())
        self.window.bind('<Control-z>',lambda _:self.undo());self.window.bind('<Control-y>',lambda _:self.redo())
        self.canvas.bind('<Control-c>',lambda _:self.guard(self.copy_pixels));self.canvas.bind('<Control-v>',lambda _:self.tool.set('Paste selection'))
        self.window.protocol('WM_DELETE_WINDOW',self.close);self.refresh_frames();self.refresh_layers();self.draw()
        self.draft=register(self,pending=lambda:self.image!=self.original_layers,
            apply=self.apply_pending,capture=self.capture_draft,restore=self.restore_draft,
            accept=self.accept_draft,priority=50)
    @property
    def document(self):return self.owner.document
    def guard(self,fn):return guard(self,fn)
    def capture_draft(self):
        return dict(image=copy.deepcopy(self.image),original=copy.deepcopy(self.original),
            layers=copy.deepcopy(self.original_layers),history=copy.deepcopy(self.history),future=copy.deepcopy(self.future))
    def restore_draft(self,state):
        self.image=state['image'];self.original=state['original'];self.original_layers=state['layers']
        self.history=state['history'];self.future=state['future'];self.refresh_frames();self.refresh_layers();self.draw()
    def build_frames(self):
        frames=ttk.Frame(self.window,padding=8);frames.pack(fill='x')
        ttk.Label(frames,text='Frame').pack(side='left');self.frame=ttk.Combobox(frames,state='readonly',width=5);self.frame.pack(side='left',padx=6)
        self.frame.bind('<<ComboboxSelected>>',lambda _:self.draw())
        for title,cb in [('Clone frame',self.add_frame),('Delete frame',self.delete_frame),('Play / stop',self.play)]:ttk.Button(frames,text=title,command=lambda f=cb:self.guard(f)).pack(side='left',padx=4)
    def refresh_frames(self):
        current=max(0,self.frame.current());self.frame.configure(values=list(range(1,len(self.image['frames'])+1)));self.frame.current(min(current,len(self.image['frames'])-1))
    def draw(self):
        if not self.window.winfo_exists():return
        # Layered animation undo can otherwise retain hundreds of megabytes.
        # Bound history by pixels as well as stroke count on modest machines.
        def size(im):return im['width']*im['height']*8*len(im['frames'])*(1+len(im.get('_layers',[])))
        while len(self.history)>1 and sum(size(im) for im in self.history)>32*1024*1024:self.history.pop(0)
        self.canvas.delete('all');z=int(self.zoom.get());self.preview=self.edit_photo(z)
        self.canvas.create_image(0,0,image=self.preview,anchor='nw');w,h=self.image['width']*z,self.image['height']*z
        self.canvas.configure(scrollregion=(0,0,w,h))
        if z>=8 and self.grid.get():
            for x in range(0,w+1,z):self.canvas.create_line(x,0,x,h,fill='#888888')
            for y in range(0,h+1,z):self.canvas.create_line(0,y,w,y,fill='#888888')
        if self.pixel_selection:
            x0,y0,x1,y1=self.pixel_selection;self.canvas.create_rectangle(x0*z,y0*z,(x1+1)*z,(y1+1)*z,outline='#20a4ef',width=2)
    def edit_photo(self, zoom):
        return photo(self.window,self.image,max(0,self.frame.current()),zoom)
    def choose_color(self):
        chosen=colorchooser.askcolor('#'+self.color.get()[:6],parent=self.window)[1]
        if chosen:self.color.set(chosen[1:]+'ff')
    def stroke(self,e,start):
        self.playing=False;z=int(self.zoom.get());p=(int(self.canvas.canvasx(e.x)//z),int(self.canvas.canvasy(e.y)//z))
        if not (0<=p[0]<self.image['width'] and 0<=p[1]<self.image['height']):return
        if self.tool.get()=='Eyedropper':self.color.set(pixels(self.image,self.frame.current())[p[1]][p[0]]);return
        if self.tool.get()=='Select':
            if start:self.first=p
            x0,x1=sorted((self.first[0],p[0]));y0,y1=sorted((self.first[1],p[1]));self.pixel_selection=(x0,y0,x1,y1);self.draw();return
        if self.tool.get()=='Paste selection':
            if start and self.pixel_clipboard:
                self.before=copy.deepcopy(self.image);paste_selection(self.image,self.frame.current(),self.pixel_clipboard,*p);self.finish();self.draw()
            return
        if start:self.before=copy.deepcopy(self.image);self.first=self.last=p
        if self.before is None:return
        shape=self.tool.get() in ('Line','Rectangle')
        if shape:self.image=copy.deepcopy(self.before)
        brush(target(self.image),self.frame.current(),self.first if shape else self.last,p,'00000000' if self.tool.get()=='Erase' else self.color.get().lower(),self.tool.get())
        flatten(self.image,self.frame.current())
        self.last=p;self.draw()
    def finish(self):
        if self.before is not None and self.before!=self.image:self.history.append(self.before);self.history=self.history[-40:];self.future=[]
        self.before=None
    def undo(self):
        self.playing=False;self.finish()
        if self.history:self.future.append(self.image);self.image=self.history.pop();self.refresh_frames();self.refresh_layers();self.draw()
    def redo(self):
        self.playing=False
        if self.future:self.history.append(self.image);self.image=self.future.pop();self.refresh_frames();self.refresh_layers();self.draw()
    def transform(self, operation):
        self.playing=False;self.finish();candidate=copy.deepcopy(self.image)
        if operation.startswith('Rotate'):
            for layer in candidate['_layers']:
                im=dict(candidate,frames=layer['frames']);transform(im,operation,self.frame.current(),self.all_frames.get(),self.wrap.get())
            candidate['width'],candidate['height']=im['width'],im['height']
        else:transform(target(candidate),operation,self.frame.current(),self.all_frames.get(),self.wrap.get())
        flatten(candidate)
        if candidate!=self.image:
            self.history.append(self.image);self.history=self.history[-40:];self.future=[];self.image=candidate;self.draw()
    def add_frame(self):
        if len(self.image['frames'])==256:raise EditorError('An image can have at most 256 frames.')
        self.history.append(copy.deepcopy(self.image));self.future=[]
        for layer in self.image['_layers']:layer['frames'].append(copy.deepcopy(layer['frames'][self.frame.current()]))
        self.image['frames'].append(copy.deepcopy(self.image['frames'][self.frame.current()]));flatten(self.image);self.refresh_frames();self.frame.current(len(self.image['frames'])-1);self.draw()
    def delete_frame(self):
        if len(self.image['frames'])==1:raise EditorError('Keep at least one frame.')
        self.history.append(copy.deepcopy(self.image));self.future=[]
        for layer in self.image['_layers']:layer['frames'].pop(self.frame.current())
        self.image['frames'].pop(self.frame.current());self.refresh_frames();self.draw()
    def play(self):
        self.playing=not self.playing
        if self.playing:self.animate()
    def animate(self):
        if not self.window.winfo_exists() or not self.playing:return
        self.frame.current((self.frame.current()+1)%len(self.image['frames']));self.draw();self.window.after(120,self.animate)
    def apply_pending(self):
        self.finish();self.owner.selected=self.original['id'];clean,layers=export_layers(self.image)
        data=editor_data(self.owner.document);data.setdefault('pixel_layers',{})[clean['id']]=layers
        metadata=dict(self.owner.document.metadata);metadata['EDITOR.json']=encoded(data)
        self.owner.put(clean,self.original,metadata)
    def accept_draft(self):
        self.original=copy.deepcopy(next(i for i in self.document.art['images'] if i['id']==self.original['id']))
        self.original_layers=copy.deepcopy(self.image)
    def apply(self):
        apply_draft(self);self.window.destroy()
    def close(self):
        if self.image!=self.original_layers:
            answer=messagebox.askyesnocancel('Unfinished artwork','Apply pixel edits before closing?',parent=self.window)
            if answer is None:return
            if answer:apply_draft(self)
        self.window.destroy()

    def refresh_layers(self):
        self.layer.configure(values=[('' if l['visible'] else '[hidden] ')+l['name'] for l in self.image['_layers']]);self.layer.current(self.image['_layer'])
    def change_layer(self):self.finish();self.image['_layer']=self.layer.current();self.draw()
    def layer_edit(self,operation):
        self.finish();self.before=copy.deepcopy(self.image);operation();flatten(self.image);self.finish();self.refresh_layers();self.draw()
    def new_layer(self):self.layer_edit(lambda:add_layer(self.image,'Layer '+str(len(self.image['_layers'])+1)))
    def rename_layer(self):
        f=Form(self,'Layer name');f.field('name',self.image['_layers'][self.image['_layer']]['name'])
        def apply(v):
            if not v['name'] or len(v['name'])>48:raise EditorError('Layer names use 1..48 characters.')
            self.layer_edit(lambda:self.image['_layers'][self.image['_layer']].update(name=v['name']))
        f.submit(apply)
    def toggle_layer(self):
        def change():
            layer=self.image['_layers'][self.image['_layer']];layer['visible']=not layer['visible']
        self.layer_edit(change)
    def reorder_layer(self,delta):
        index=self.image['_layer'];new=index+delta
        if 0<=new<len(self.image['_layers']):
            def change():
                layers=self.image['_layers'];layers[index],layers[new]=layers[new],layers[index];self.image['_layer']=new
            self.layer_edit(change)
    def delete_layer(self):
        if len(self.image['_layers'])==1:raise EditorError('Keep at least one layer.')
        def change():self.image['_layers'].pop(self.image['_layer']);self.image['_layer']=max(0,self.image['_layer']-1)
        self.layer_edit(change)
    def copy_pixels(self,cut=False):
        if not self.pixel_selection:raise EditorError('Select a rectangle of pixels first.')
        self.pixel_clipboard=selected_pixels(self.image,self.frame.current(),self.pixel_selection)
        if cut:
            x0,y0,x1,y1=self.pixel_selection
            self.layer_edit(lambda:brush(target(self.image),self.frame.current(),(x0,y0),(x1,y1),'00000000','Rectangle'))
    def crop(self):
        if not self.pixel_selection:raise EditorError('Select a rectangle to crop first.')
        x0,y0,x1,y1=self.pixel_selection;self.layer_edit(lambda:resize_canvas(self.image,x1-x0+1,y1-y0+1,x0,y0));self.pixel_selection=None;self.draw()
    def resize_dialog(self):
        f=Form(self,'Resize canvas (crop / pad, all layers and frames)');f.field('width',self.image['width']);f.field('height',self.image['height']);f.field('x',0,label='Source left');f.field('y',0,label='Source top')
        f.submit(lambda v:self.layer_edit(lambda:resize_canvas(self.image,int(v['width']),int(v['height']),int(v['x']),int(v['y']))))
    def export_dialog(self):
        path=filedialog.asksaveasfilename(parent=self.window,title='Export sprite sheet',defaultextension='.png',filetypes=[('PNG','*.png')])
        if path:export_sheet(self.image,path,1 if len(self.image['frames'])%4 else 4)
